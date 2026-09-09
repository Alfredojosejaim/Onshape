"""Licensing abstraction for Topologia Optimizada.

The application is a commercial desktop CAD/CAE product distributed by
subscription.  By design:

- Internet is NOT required to use the normal CAD/CAE features.
- Internet is used ONLY to validate the license/subscription.
- A temporary Internet outage must not destroy the working state nor needlessly
  block local operations.

To keep this clean we expose a single ``LicenseManager`` to the rest of the
application.  The rest of the code knows NOTHING about HTTP, URLs, tokens or
license servers -- it only observes coarse-grained license states.

    Application
        ↓
    LicenseManager
        ↓
    LicenseServer   (future commercial backend)

The exact offline policy is encapsulated *inside* ``LicenseManager``.  We never
scatter ``if internet: ...`` checks across the application.  CAD/CAE features
never query the network state directly.

No commercial license backend is implemented yet; only the local architecture
needed to integrate one later is provided.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class LicenseState(str, Enum):
    """Coarse-grained license states the rest of the app may observe."""

    LICENSED = "licensed"
    TRIAL = "trial"
    EXPIRED = "expired"
    INVALID = "invalid"
    OFFLINE_GRACE_PERIOD = "offline_grace_period"


class LicenseServerProtocol(ABC):
    """Abstract contract for a license/validation backend.

    A future commercial backend implements this.  The rest of the application
    depends only on this protocol, never on HTTP details.

    Implementations are expected to be *best-effort*: they must never raise on
    network failures.  They return an outcome and let ``LicenseManager`` decide
    how to handle it (e.g. offline grace period).
    """

    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to validate the license.

        Returns a dict with at least ``{"state": <LicenseState>}`` plus any
        backend-specific metadata (e.g. trial days remaining).  Must not raise;
        on any failure it returns ``{"state": LicenseState.INVALID}`` or a
        state the manager can interpret as offline.
        """


class NoOpLicenseServer(LicenseServerProtocol):
    """Development/no-backend placeholder.

    There is no commercial license server yet, so this server always reports
    a valid license.  It never performs any network I/O, which is what makes
    the desktop app fully offline-capable today.
    """

    def validate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"state": LicenseState.LICENSED, "backend": "noop"}
        # NOTE: swap this for a real ``LicenseServerProtocol`` implementation
        # once a commercial backend exists.  Nothing else in the codebase must
        # change -- the manager, UI and CAD/CAE layers only see the state.


@dataclass
class LicenseConfig:
    """Local configuration for the ``LicenseManager``.

    These values + the backend decide the offline/grace behaviour.
    """

    grace_period_seconds: float = 7 * 24 * 3600  # default: 7 days offline grace
    enabled: bool = True  # master switch (dev: set to False to bypass checks)
    server: Optional[LicenseServerProtocol] = field(
        default_factory=NoOpLicenseServer
    )


class LicenseManager:
    """Single entry point the rest of the application uses for licensing.

    Responsibilities:
    - Own the current ``LicenseState``.
    - Encapsulate the offline/grace-period policy.
    - Never raise to callers, even if the backend is unreachable.
    - Notify listeners when the state changes (so the UI can react without
      CAD/CAE code polling the network).

    Construction is cheap and non-blocking; no network call happens in the
    constructor.
    """

    def __init__(self, config: Optional[LicenseConfig] = None) -> None:
        self._config = config or LicenseConfig()
        self._state: LicenseState = LicenseState.LICENSED
        self._last_validation: Optional[float] = None
        self._offline_since: Optional[float] = None
        self._listeners: list[Callable[[LicenseState], None]] = []
        self._metadata: Dict[str, Any] = {}
        if self._config.enabled and self._config.server is not None:
            # Best-effort initial validation (non-blocking backend).
            self.validate()

    # ------------------------------------------------------------------ #
    # Observation API (used by UI / app layer)
    # ------------------------------------------------------------------ #
    @property
    def state(self) -> LicenseState:
        return self._state

    @property
    def is_licensed(self) -> bool:
        """True when the user may use the full product.

        ``LICENSED``, ``TRIAL`` and ``OFFLINE_GRACE_PERIOD`` all count as usable
        so that a temporary Internet interruption does not block local work.
        """
        return self._state in (
            LicenseState.LICENSED,
            LicenseState.TRIAL,
            LicenseState.OFFLINE_GRACE_PERIOD,
        )

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    def add_listener(self, cb: Callable[[LicenseState], None]) -> None:
        """Register a callback invoked with the new state on changes."""
        if cb not in self._listeners:
            self._listeners.append(cb)

    def remove_listener(self, cb: Callable[[LicenseState], None]) -> None:
        if cb in self._listeners:
            self._listeners.remove(cb)

    # ------------------------------------------------------------------ #
    # Validation entry points
    # ------------------------------------------------------------------ #
    def validate(self, context: Optional[Dict[str, Any]] = None) -> LicenseState:
        """(Re)validate the license.  Called on demand by the app layer.

        This is the ONLY method that talks to the backend.  It never raises and
        never blocks CAD/CAE indefinitely; on failure it falls back to the
        offline grace-period policy.
        """
        if not self._config.enabled or self._config.server is None:
            return self._state

        ctx = dict(context or {})
        ctx.setdefault("app_started_at", self._last_validation)

        result, reachable = self._safe_validate(ctx)
        backend_state = result.get("state")
        self._metadata = {k: v for k, v in result.items() if k != "state"}

        now = time.time()
        self._last_validation = now

        if not reachable:
            # Backend could not be reached (network outage) -> offline policy.
            self._handle_offline(now)
        elif backend_state == LicenseState.LICENSED:
            self._offline_since = None
            self._set_state(LicenseState.LICENSED)
        elif backend_state == LicenseState.TRIAL:
            self._offline_since = None
            self._set_state(LicenseState.TRIAL)
        elif backend_state in (LicenseState.EXPIRED, LicenseState.INVALID):
            # A definitive denial from a reachable backend.
            if self._offline_since is not None and self._within_grace(now):
                self._set_state(LicenseState.OFFLINE_GRACE_PERIOD)
            else:
                self._set_state(backend_state)
        else:
            # Unknown outcome -> treat as offline.
            self._handle_offline(now)

        return self._state

    # ------------------------------------------------------------------ #
    # Offline/grace policy (encapsulated here, nowhere else)
    # ------------------------------------------------------------------ #
    def _handle_offline(self, now: float) -> None:
        """Apply the offline grace-period policy."""
        if self._offline_since is None:
            self._offline_since = now
            # First sign of trouble -> grant a grace period.
            self._set_state(LicenseState.OFFLINE_GRACE_PERIOD)
            return

        # Already offline.  Stay in the grace period while it lasts.  A future
        # commercial policy may tighten this (e.g. drop to a degraded mode once
        # the grace window is exhausted); that logic belongs HERE, not in CAD/CAE.
        self._set_state(LicenseState.OFFLINE_GRACE_PERIOD)

    def _within_grace(self, now: float) -> bool:
        if self._offline_since is None:
            return True
        return (now - self._offline_since) <= self._config.grace_period_seconds

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _safe_validate(self, ctx: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
        """Wrap backend validation so it can never raise.

        Returns ``(result, reachable)``.  ``reachable`` is False when the
        backend raised or could not be contacted, so the caller can apply the
        offline grace-period policy instead of a definitive denial.
        """
        try:
            result = self._config.server.validate(ctx)  # type: ignore[union-attr]
            return result, True
        except Exception:
            return {"state": LicenseState.INVALID}, False

    def _set_state(self, new_state: LicenseState) -> None:
        if new_state == self._state:
            return
        old = self._state
        self._state = new_state
        for cb in list(self._listeners):
            try:
                cb(new_state)
            except Exception:
                pass  # never let a listener break licensing

    def __repr__(self) -> str:
        return f"LicenseManager(state={self._state.value!r})"
