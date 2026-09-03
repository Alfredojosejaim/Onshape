"""Pytest session initialization for Topologia Optimizada.

Registers the KratosMultiphysics ``.libs`` directory with ``os.add_dll_directory``
before any test module imports Kratos. This is required on Windows so that the
KratosCore.dll dependency graph can be resolved.
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
# La suite de tests vive en `tests/` (y los de diagnóstico histórico retirados en
# `tests_obsoletos/`). Los globs de abajo se mantienen como safety net en caso de
# que reaparezca algún test legacy de Kratos en la raíz.
collect_ignore_glob = [
    "test_kratos_*.py",
    "test_linear_solver_repro.py",
    "test_stage_i_integration.py",
]
