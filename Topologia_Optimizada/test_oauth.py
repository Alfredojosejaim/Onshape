import time

import requests

from onshape_client import OnshapeClient


class MemoryStore:
    def __init__(self):
        self.tokens = {}

    def get_token(self, session_id):
        return self.tokens.get(session_id)

    def save_token(self, session_id, token):
        self.tokens[session_id] = token


def response(status, payload):
    result = requests.Response()
    result.status_code = status
    result._content = __import__("json").dumps(payload).encode()
    return result


def test_exchange_and_refresh(monkeypatch):
    store = MemoryStore()
    client = OnshapeClient(store, "session", "client", "secret")
    token_responses = iter(
        [
            response(200, {"access_token": "first", "refresh_token": "refresh", "expires_in": 0}),
            response(200, {"access_token": "second", "expires_in": 3600}),
        ]
    )
    monkeypatch.setattr(client.session, "post", lambda *args, **kwargs: next(token_responses))
    client.exchange_code("code", "http://localhost/callback")
    assert store.tokens["session"]["access_token"] == "first"
    refreshed = client._refresh(store.tokens["session"])
    assert refreshed["access_token"] == "second"
    assert refreshed["refresh_token"] == "refresh"


def test_request_retries_after_401(monkeypatch):
    store = MemoryStore()
    store.tokens["session"] = {
        "access_token": "old",
        "refresh_token": "refresh",
        "expires_at": time.time() + 3600,
        "token_type": "Bearer",
    }
    client = OnshapeClient(store, "session", "client", "secret")
    monkeypatch.setattr(
        client.session,
        "post",
        lambda *args, **kwargs: response(200, {"access_token": "new", "expires_in": 3600}),
    )
    calls = iter([response(401, {}), response(200, {"ok": True})])
    monkeypatch.setattr(client.session, "request", lambda *args, **kwargs: next(calls))
    result = client.request("GET", "/documents")
    assert result.status_code == 200
    assert store.tokens["session"]["access_token"] == "new"
