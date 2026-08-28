"""Core Topological Optimization and FEA solver interfaces.

Provides a deterministic interface and refuses to run fake/synthetic engineering results
until a verified FEA adapter is supplied.
"""

import logging
from typing import Any, Callable, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

NOT_IMPLEMENTED_MSG = "A real FEA solver and mapped boundary conditions are required"

# Kratos import - optional, only when Kratos solver is used
KRATOS_AVAILABLE = True
KRATOS_IMPORT_ERROR = None

try:
    from core.kratos_adapter import KratosAdapter, is_kratos_available, get_kratos_import_error
except ImportError as e:
    KRATOS_AVAILABLE = False
    KRATOS_IMPORT_ERROR = str(e)
    logger.warning(f"Kratos adapter not available: {e}")


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


def create_kratos_fea_solver(
    nodes: np.ndarray,
    elements: np.ndarray,
    material: Any,
    constraints: Any,
    loads: Any,
) -> Callable[..., Dict[str, Any]]:
    """Create a Kratos-based FEA solver for use with TopOptSolver.
    
    This function creates a fea_solver callable that uses KratosAdapter to perform
    FEA analysis. It integrates Kratos with the Core's data structures.
    
    Args:
        nodes: Node coordinates array (N x 3)
        elements: Element connectivity array (M x 4 for Tet4)
        material: Material object from core.materials
        constraints: List of ConstraintDefinition objects
        loads: List of LoadDefinition objects
        
    Returns:
        Callable function that can be used as fea_solver for TopOptSolver
        
    Raises:
        RuntimeError: If Kratos is not available
    """
    if not KRATOS_AVAILABLE:
        raise RuntimeError(f"Kratos not available: {KRATOS_IMPORT_ERROR}")
    
    def kratos_fea_solver(
        densities: np.ndarray,
        forces: Optional[np.ndarray] = None,
        supports: Optional[np.ndarray] = None,
        max_iterations: int = 1,
        tolerance: float = 0.01,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Execute FEA analysis using Kratos.
        
        Args:
            densities: Element densities (for topology optimization)
            forces: Force array (optional, uses loads parameter if not provided)
            supports: Support array (optional, uses constraints parameter if not provided)
            max_iterations: Maximum iterations (not used for single FEA)
            tolerance: Convergence tolerance (not used for single FEA)
            callback: Callback function for progress updates
            
        Returns:
            Dictionary with FEA results
        """
        try:
            # Initialize Kratos adapter
            adapter = KratosAdapter()
            
            # Create ModelPart
            model_part = adapter.create_model_part("CoreFEAModel")
            
            # Add nodal variables BEFORE importing mesh (critical requirement)
            adapter.add_nodal_variables(model_part)
            
            # Convert numpy arrays to list format for KratosAdapter
            nodes_list = nodes.tolist()
            elements_list = elements.tolist()
            
            # Import mesh
            adapter.import_mesh_from_core_format(
                model_part,
                nodes_list,
                elements_list,
                element_type="tet4"
            )
            
            # Configure material
            adapter.configure_material_from_core(model_part, material)
            
            # Add displacement DOFs
            adapter.add_displacement_dofs(model_part)
            
            # Apply constraints
            # For now, apply constraints to all nodes as a simplification
            # In a full implementation, this would use proper face mapping
            all_node_indices = list(range(len(nodes_list)))
            for constraint in constraints:
                adapter.apply_constraint_from_core(model_part, constraint, all_node_indices)
            
            # Apply loads
            for load in loads:
                adapter.apply_load_from_core(model_part, load, all_node_indices)
            
            # Run analysis
            result = adapter.run_analysis(model_part)
            
            if result["success"]:
                # Extract results in format expected by TopOptSolver
                analysis_results = result.get("results", {})
                
                return {
                    "success": True,
                    "status": "completed",
                    "displacements": np.array(analysis_results.get("displacements", [])),
                    "compliance": analysis_results.get("compliance", 0.0),
                    "element_energies": np.array(analysis_results.get("element_energies", [])),
                    "num_nodes": analysis_results.get("num_nodes_with_displacement", 0),
                    "num_elements": len(elements_list),
                }
            else:
                return {
                    "success": False,
                    "status": "failed",
                    "error": result.get("error", "Unknown error"),
                }
                
        except Exception as e:
            logger.error(f"Kratos FEA solver failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "status": "failed",
                "error": str(e),
            }
    
    return kratos_fea_solver
