"""Tests for the local user preferences persistence.

Verifies preferences can be persisted and restored locally without any network
or web dependency (stdlib ``json``/``pathlib`` only).
"""

import os
import tempfile
import unittest
from pathlib import Path

from core.user_preferences import UserPreferences


class TestUserPreferences(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self._old = os.environ.get("TOPOOPT_CONFIG_DIR")
        os.environ["TOPOOPT_CONFIG_DIR"] = self._tmp

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop("TOPOOPT_CONFIG_DIR", None)
        else:
            os.environ["TOPOOPT_CONFIG_DIR"] = self._old

    def test_default_navigation_profile(self):
        prefs = UserPreferences()
        self.assertEqual(prefs.navigation_profile, "autocad")

    def test_persist_and_restore_navigation_profile(self):
        prefs = UserPreferences()
        prefs.navigation_profile = "onshape"
        self.assertTrue(Path(prefs.path).exists())
        # A fresh instance (reloads from disk) must see the saved value.
        prefs2 = UserPreferences()
        self.assertEqual(prefs2.navigation_profile, "onshape")

    def test_corrupt_file_does_not_raise(self):
        cfg = UserPreferences().path
        cfg.write_text("{ not valid json", encoding="utf-8")
        fresh = UserPreferences()
        # Falls back to defaults without raising.
        self.assertEqual(fresh.navigation_profile, "autocad")

    def test_get_set_remove(self):
        prefs = UserPreferences()
        prefs.set("theme", "dark")
        self.assertEqual(prefs.get("theme"), "dark")
        self.assertTrue(prefs.remove("theme"))
        self.assertIsNone(prefs.get("theme"))


if __name__ == "__main__":
    unittest.main()
