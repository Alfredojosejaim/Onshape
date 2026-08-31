"""Pytest session initialization for Topologia Optimizada.

Registers the KratosMultiphysics ``.libs`` directory with ``os.add_dll_directory``
before any test module imports Kratos. This is required on Windows so that the
KratosCore.dll dependency graph can be resolved (see ``dependencias.md``).
"""

import importlib.util
import logging
import os

logger = logging.getLogger(__name__)


def register_kratos_dll_directory() -> None:
    """Register the KratosMultiphysics native DLL directory on Windows."""
    if os.name != "nt":
        return
    spec = importlib.util.find_spec("KratosMultiphysics")
    if spec is None or not spec.submodule_search_locations:
        return
    package_dir = list(spec.submodule_search_locations)[0]
    libs_dir = os.path.join(package_dir, ".libs")
    if os.path.isdir(libs_dir):
        os.add_dll_directory(libs_dir)
        logger.info("Kratos DLL directory registered: %s", libs_dir)

register_kratos_dll_directory()


# ---------------------------------------------------------------------------
# Legacy Kratos experiments
# ---------------------------------------------------------------------------
# The self-contained application no longer depends on KratosMultiphysics (see
# ``dependencias.md``). The legacy ``test_kratos_*.py`` harnesses (that require the
# native Kratos libraries) were moved to ``experimentos/test_kratos_legacy/``, which
# is already excluded from test discovery via ``norecursedirs`` in pyproject.toml.
# The glob below is kept as a safety net in case any such file reappears at the root.
collect_ignore_glob = [
    "test_kratos_*.py",
    "test_linear_solver_repro.py",
    "test_stage_i_integration.py",
]
