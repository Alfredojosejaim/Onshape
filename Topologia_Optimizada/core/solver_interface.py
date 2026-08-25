"""Core Topological Optimization and FEA solver interfaces.

Provides a deterministic interface and refuses to run fake/synthetic engineering results
until a verified FEA adapter is supplied.
"""

import logging
from typing import Any, Callable, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

NOT_IMPLEMENTED_MSG = "A real FEA solver and mapped boundary conditions are required"


class TopOptSolver:
    """Core SIMP topology optimization interface; no fake analysis is performed."""

    def __init__(
        self,
        nelx: int,
        nely: int,
        nelz: Optional[int] = None,
        volfrac: float = 0.5,
        penalization: float = 3.0,
        rmin: float = 1.5,
        use_full_domain: bool = True,
        fea_solver: Optional[Callable[..., Any]] = None,
    ):
        if nelx <= 0 or nely <= 0 or (nelz is not None and nelz <= 0):
            raise ValueError("mesh dimensions must be positive")
        if not 0 < volfrac <= 1:
            raise ValueError("volfrac must be greater than 0 and at most 1")
        self.nelx, self.nely, self.nelz = nelx, nely, nelz
        self.volfrac = volfrac
        self.penalization = penalization
        self.rmin = rmin
        self.use_full_domain = use_full_domain
        self.nelem = nelx * nely * (nelz or 1)
        self.fea_solver = fea_solver
        self.x = np.full(self.nelem, volfrac, dtype=float)

    def solve(
        self,
        forces: Optional[np.ndarray] = None,
        supports: Optional[np.ndarray] = None,
        max_iterations: int = 100,
        tolerance: float = 0.01,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Run a configured real FEA/TopOpt adapter, or return explicit pending."""
        if max_iterations <= 0:
            return {
                "success": False,
                "status": "failed",
                "code": "INVALID_ITERATIONS",
                "error": "max_iterations must be positive",
            }
        if self.fea_solver is None:
            return {
                "success": False,
                "status": "not_implemented",
                "code": "FEA_SOLVER_REQUIRED",
                "error": NOT_IMPLEMENTED_MSG,
                "iterations": 0,
                "final_volume_fraction": self.volfrac,
            }
        try:
            result = self.fea_solver(
                densities=self.x.copy(),
                forces=forces,
                supports=supports,
                max_iterations=max_iterations,
                tolerance=tolerance,
                callback=callback,
            )
            if not isinstance(result, dict) or (result.get("status") == "completed" and not result.get("success")):
                raise ValueError("FEA adapter returned an invalid result")
            return result
        except Exception:
            logger.exception("Configured FEA adapter failed")
            return {
                "success": False,
                "status": "failed",
                "code": "FEA_SOLVER_FAILED",
                "error": "Configured FEA adapter failed",
            }


def run_topology_optimization(
    volume_fraction: float = 0.3,
    max_iterations: int = 100,
    nelx: int = 20,
    nely: int = 20,
    nelz: Optional[int] = None,
    callback=None,
    forces: Optional[np.ndarray] = None,
    supports: Optional[np.ndarray] = None,
    fea_solver: Optional[Callable[..., Any]] = None,
    tolerance: float = 0.01,
    penalization: float = 3.0,
    rmin: float = 1.5,
) -> Dict[str, Any]:
    """Convenience helper to run topology optimization with an explicit FEA adapter."""
    solver = TopOptSolver(
        nelx=nelx,
        nely=nely,
        nelz=nelz,
        volfrac=volume_fraction,
        penalization=penalization,
        rmin=rmin,
        fea_solver=fea_solver,
    )
    return solver.solve(
        forces=forces,
        supports=supports,
        max_iterations=max_iterations,
        tolerance=tolerance,
        callback=callback,
    )
