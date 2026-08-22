"""OAuth-backed Onshape API client with centralized token refresh."""

import threading
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class OnshapeAPIError(RuntimeError):
    """A non-success response from the Onshape API."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class OAuthTokenStore:
    """Persistence contract required by the OAuth client."""

    def get_token(self, session_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def save_token(self, session_id: str, token: Dict[str, Any]) -> None:
        raise NotImplementedError


class OnshapeClient:
    """Authenticated REST client; callers never manage OAuth tokens directly."""

    def __init__(
        self,
        token_store: OAuthTokenStore,
        session_id: str,
        client_id: str,
        client_secret: str,
        token_url: str = "https://oauth.onshape.com/oauth/token",
        api_url: str = "https://cad.onshape.com/api",
        timeout: float = 20.0,
    ):
        self.token_store = token_store
        self.session_id = session_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self._refresh_lock = threading.Lock()

    @staticmethod
    def _error(status_code: int) -> str:
        return {
            400: "ONSHAPE_BAD_REQUEST",
            401: "ONSHAPE_UNAUTHORIZED",
            403: "ONSHAPE_FORBIDDEN",
            404: "ONSHAPE_NOT_FOUND",
            409: "ONSHAPE_CONFLICT",
            429: "ONSHAPE_RATE_LIMITED",
        }.get(status_code, "ONSHAPE_HTTP_ERROR")

    def _token_request(self, data: Dict[str, str]) -> Dict[str, Any]:
        response = self.session.post(
            self.token_url,
            data=data,
            auth=(self.client_id, self.client_secret),
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise OnshapeAPIError(
                response.status_code,
                "OAUTH_TOKEN_EXCHANGE_FAILED",
                "Onshape OAuth token exchange failed",
            )
        try:
            token = response.json()
        except ValueError as exc:
            raise OnshapeAPIError(502, "OAUTH_INVALID_RESPONSE", "Invalid OAuth response") from exc
        if not token.get("access_token"):
            raise OnshapeAPIError(502, "OAUTH_ACCESS_TOKEN_MISSING", "OAuth response has no access token")
        return token

    def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        token = self._token_request(
            {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
        )
        self.token_store.save_token(self.session_id, self._normalized_token(token))
        return token

    def _refresh(self, token: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            raise OnshapeAPIError(401, "ONSHAPE_REAUTH_REQUIRED", "Onshape session requires re-authentication")
        with self._refresh_lock:
            current = self.token_store.get_token(self.session_id) or token
            if not force and current.get("expires_at", 0) > time.time() + 30:
                return current
            refreshed = self._token_request(
                {"grant_type": "refresh_token", "refresh_token": current["refresh_token"]}
            )
            if "refresh_token" not in refreshed:
                refreshed["refresh_token"] = current["refresh_token"]
            normalized = self._normalized_token(refreshed)
            self.token_store.save_token(self.session_id, normalized)
            return normalized

    @staticmethod
    def _normalized_token(token: Dict[str, Any]) -> Dict[str, Any]:
        expires_in = int(token.get("expires_in", 3600))
        return {
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "expires_at": time.time() + expires_in,
            "token_type": token.get("token_type", "Bearer"),
            "scope": token.get("scope"),
        }

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        token = self.token_store.get_token(self.session_id)
        if not token:
            raise OnshapeAPIError(401, "ONSHAPE_AUTH_REQUIRED", "Onshape authentication is required")
        if token.get("expires_at", 0) <= time.time() + 30:
            token = self._refresh(token)
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {token['access_token']}"
        headers.setdefault("Accept", "application/vnd.onshape.v2+json")
        headers.setdefault("Content-Type", "application/json")
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.request(method, f"{self.api_url}/{path.lstrip('/')}", headers=headers, **kwargs)
        if response.status_code == 401:
            token = self._refresh(token, force=True)
            headers["Authorization"] = f"Bearer {token['access_token']}"
            response = self.session.request(
                method, f"{self.api_url}/{path.lstrip('/')}", headers=headers, **kwargs
            )
        if response.status_code >= 400:
            raise OnshapeAPIError(
                response.status_code,
                self._error(response.status_code),
                f"Onshape API request failed with HTTP {response.status_code}",
            )
        return response

    def get_json(self, path: str, **kwargs: Any) -> Any:
        response = self.request("GET", path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise OnshapeAPIError(502, "ONSHAPE_INVALID_RESPONSE", "Onshape returned invalid JSON") from exc
