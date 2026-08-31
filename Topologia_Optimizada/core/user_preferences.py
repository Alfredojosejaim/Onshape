"""Lightweight local user preferences (stdlib only, no network / no web).

Used to persist user-level preferences such as the active navigation profile,
so they survive across application sessions.

This is intentionally minimal and dependency-free (just ``json`` + ``pathlib``).
Only coarse-grained, non-sensitive preferences are stored here.  Licensing
state is NOT stored here -- that lives in ``LicenseManager``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------- #
# Where preferences live
# ---------------------------------------------------------------------- #

def _config_dir(name: str = "TopologiaOptimizada") -> Path:
    """Return the per-user config directory, creating it if needed.

    Uses a standard per-user location and falls back gracefully.  No
    third-party library (e.g. platformdirs) is required.
    """
    env_dir = os.environ.get("TOPOOPT_CONFIG_DIR")
    if env_dir:
        base = Path(env_dir)
    else:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", str(Path.home())))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    path = base / name
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        path = Path.home() / f".{name.lower()}"
        path.mkdir(parents=True, exist_ok=True)
    return path


class UserPreferences:
    """Persist/restore simple key-value user preferences as JSON.

    ``get``/``set`` always work in-memory; ``save`` flushes to disk.  Loads are
    best-effort: a missing or corrupt file yields defaults and never raises.
    """

    def __init__(
        self,
        filename: str = "preferences.json",
        defaults: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._path = _config_dir() / filename
        self._data: Dict[str, Any] = dict(defaults or {})
        self.load()

    # ------------------------------------------------------------------ #
    def load(self) -> None:
        """Load persisted preferences (merging over, never discarding, defaults)."""
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as fh:
                    persisted = json.load(fh)
                if isinstance(persisted, dict):
                    self._data.update(persisted)
        except (OSError, ValueError, TypeError):
            # Corrupt or unreadable file -> keep in-memory defaults.
            pass

    def save(self) -> bool:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def remove(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    # ------------------------------------------------------------------ #
    # Convenience for the navigation profile (known preference)
    # ------------------------------------------------------------------ #
    @property
    def navigation_profile(self) -> str:
        return str(self.get("navigation_profile", "autocad"))

    @navigation_profile.setter
    def navigation_profile(self, name: str) -> None:
        self.set("navigation_profile", name)
        self.save()

    @property
    def path(self) -> Path:
        return self._path
