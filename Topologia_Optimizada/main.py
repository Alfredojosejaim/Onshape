"""Desktop entry point for Topologia Optimizada.

Launches the native GUI (PySide6 + VTK) directly — no browser required.

Run with:  python main.py
"""

from __future__ import annotations

import os
import sys


def _ensure_project_on_path() -> None:
    """Make the project root importable regardless of the CWD the app is run from."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


def main() -> int:
    _ensure_project_on_path()
    from desktop.app import run
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
