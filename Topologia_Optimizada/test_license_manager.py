"""Tests for the LicenseManager licensing abstraction.

Verifies that the desktop CAD/CAE application can operate with a licensing
object that is fully decoupled from HTTP/network: CAD/CAE layers observe only
coarse-grained states (licensed / trial / expired / invalid / offline grace),
and the offline policy is encapsulated entirely inside LicenseManager.
"""

import unittest

from core.license import (
    LicenseConfig,
    LicenseManager,
    LicenseServerProtocol,
    LicenseState,
    NoOpLicenseServer,
)


class _FlakyServer(LicenseServerProtocol):
    """Simulates a backend that sometimes cannot be reached (offline)."""

    def __init__(self) -> None:
        self.offline = False
        self.deny = False
        self.trial = False

    def validate(self, context):
        if self.deny:
            return {"state": LicenseState.EXPIRED}
        if self.trial:
            return {"state": LicenseState.TRIAL}
        if self.offline:
            raise ConnectionError("offline")
        return {"state": LicenseState.LICENSED}


class _RaisingServer(LicenseServerProtocol):
    """Backend that always raises (worst case network failure)."""

    def validate(self, context):
        raise ConnectionError("boom")


class TestLicenseManager(unittest.TestCase):
    def test_default_is_licensed(self):
        """With no backend error the state should be LICENSED."""
        lm = LicenseManager()
        self.assertEqual(lm.state, LicenseState.LICENSED)
        self.assertTrue(lm.is_licensed)

    def test_noop_server_is_fully_offline(self):
        """The default NoOp server performs no network I/O."""
        self.assertIsInstance(LicenseConfig().server, NoOpLicenseServer)
        self.assertEqual(NoOpLicenseServer().validate({})["state"], LicenseState.LICENSED)

    def test_trial_state(self):
        server = _FlakyServer()
        server.trial = True
        lm = LicenseManager(LicenseConfig(server=server))
        self.assertEqual(lm.state, LicenseState.TRIAL)
        self.assertTrue(lm.is_licensed)

    def test_expired_denial(self):
        server = _FlakyServer()
        server.deny = True
        lm = LicenseManager(LicenseConfig(server=server, grace_period_seconds=0))
        self.assertEqual(lm.state, LicenseState.EXPIRED)
        self.assertFalse(lm.is_licensed)

    def test_offline_grants_grace_period(self):
        """A temporary outage should NOT hard-fail local work."""
        server = _FlakyServer()
        lm = LicenseManager(LicenseConfig(server=server))
        self.assertEqual(lm.state, LicenseState.LICENSED)
        server.offline = True
        new_state = lm.validate()
        self.assertEqual(new_state, LicenseState.OFFLINE_GRACE_PERIOD)
        self.assertTrue(lm.is_licensed)
        server.offline = False
        self.assertEqual(lm.validate(), LicenseState.LICENSED)
        self.assertTrue(lm.is_licensed)

    def test_raising_backend_never_raises_to_caller(self):
        """LicenseManager must never raise, even if the backend does."""
        lm = LicenseManager(LicenseConfig(server=_RaisingServer()))
        state = lm.validate()
        self.assertIn(state, (LicenseState.OFFLINE_GRACE_PERIOD, LicenseState.INVALID))
        # usable while in grace period
        self.assertTrue(lm.is_licensed)

    def test_disabled_bypasses_validation(self):
        lm = LicenseManager(LicenseConfig(enabled=False, server=_RaisingServer()))
        self.assertEqual(lm.state, LicenseState.LICENSED)
        self.assertEqual(lm.validate(), LicenseState.LICENSED)

    def test_listeners_receive_state_changes(self):
        server = _FlakyServer()
        lm = LicenseManager(LicenseConfig(server=server))
        seen = []
        lm.add_listener(lambda st: seen.append(st))
        server.offline = True
        lm.validate()
        self.assertIn(LicenseState.OFFLINE_GRACE_PERIOD, seen)


if __name__ == "__main__":
    unittest.main()
