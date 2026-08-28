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
            
            # Apply constraints using geometric selection
            # CRITICAL FIX: No longer applies to ALL nodes
            # Instead, use geometric information to select boundary nodes
            for constraint in constraints:
                _apply_constraint_geometrically(adapter, model_part, constraint, nodes_list)
            
            # Apply loads using geometric selection
            # CRITICAL FIX: No longer applies to ALL nodes
            # Instead, use geometric information to select load surface nodes
            for load in loads:
                _apply_load_geometrically(adapter, model_part, load, nodes_list)
            
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


def _apply_constraint_geometrically(adapter: Any, model_part: Any, constraint: Any, 
                                   nodes_list: List[List[float]]) -> None:
    """Apply constraint using geometric node selection.
    
    ARCHITECTURE NOTE:
    This function implements proper geometric node selection for boundary conditions.
    Previously, constraints were applied to ALL nodes, creating an over-constrained system.
    
    Two approaches are supported:
    1. Submodelpart-based (recommended): If .mdpa has named submodelparts from gmsh 
       physical groups, use those (e.g., "Structure.FixedFace")
    2. Coordinate-based (fallback): If no submodelpart, filter nodes by coordinate 
       (e.g., Z=0 for fixed end)
       
    Args:
        adapter: KratosAdapter instance
        model_part: Kratos ModelPart
        constraint: ConstraintDefinition object
        nodes_list: Original node coordinates from Core
    """
    try:
        from core.study import ConstraintType
        
        # Strategy 1: Try to use named submodelpart (e.g., from gmsh physical groups)
        submodelpart_name = getattr(constraint, 'submodelpart_name', None) or \
                           getattr(constraint, 'boundary_name', None)
        
        if submodelpart_name:
            logger.info(f"Applying constraint using submodelpart: {submodelpart_name}")
            adapter.apply_constraint_to_submodelpart(model_part, constraint, submodelpart_name)
            return
        
        # Strategy 2: Fallback - use coordinate-based filtering
        # This is a temporary solution until gmsh physical groups are properly integrated
        logger.warning(f"No submodelpart specified for constraint {constraint.id}. "
                      "Using coordinate-based selection (temporary workaround).")
        
        # For a fixed constraint on a cantilever beam, typically fix the built-in end
        # Assumption: the fixed end is at Z=0 (this should be in constraint metadata)
        # Extract fixed end from constraint or default to Z=0
        fixed_coord = getattr(constraint, 'fixed_coordinate', 0.0)
        fixed_axis = getattr(constraint, 'fixed_axis', 2)  # Default Z axis
        tolerance = getattr(constraint, 'tolerance', 0.01)
        
        node_indices = adapter.get_nodes_by_coordinate_filter(
            model_part, 
            coordinate=fixed_axis,
            value=fixed_coord,
            tolerance=tolerance
        )
        
        if node_indices:
            adapter.apply_constraint_from_core(model_part, constraint, node_indices)
            logger.info(f"Constraint applied to {len(node_indices)} nodes by coordinate filter")
        else:
            logger.warning(f"No nodes found matching constraint criteria for {constraint.id}")
            
    except Exception as e:
        logger.error(f"Failed to apply constraint geometrically: {e}")
        raise


def _apply_load_geometrically(adapter: Any, model_part: Any, load: Any, 
                             nodes_list: List[List[float]]) -> None:
    """Apply load using geometric node selection.
    
    ARCHITECTURE NOTE:
    This function implements proper geometric node selection for loads.
    Previously, loads were applied to ALL nodes, creating an over-loaded system.
    
    Similar to constraints, two approaches are supported:
    1. Submodelpart-based (recommended): Use named submodelparts from gmsh physical groups
    2. Coordinate-based (fallback): Filter nodes by coordinate
    
    For a cantilever beam with a point load at the free end, this would select only
    the nodes at the free end (e.g., Z=L).
    
    Args:
        adapter: KratosAdapter instance
        model_part: Kratos ModelPart
        load: LoadDefinition object
        nodes_list: Original node coordinates from Core
    """
    try:
        from core.study import LoadType
        
        # Strategy 1: Try to use named submodelpart
        submodelpart_name = getattr(load, 'submodelpart_name', None) or \
                           getattr(load, 'boundary_name', None)
        
        if submodelpart_name:
            logger.info(f"Applying load using submodelpart: {submodelpart_name}")
            adapter.apply_load_to_submodelpart(model_part, load, submodelpart_name)
            return
        
        # Strategy 2: Fallback - use coordinate-based filtering
        logger.warning(f"No submodelpart specified for load {load.id}. "
                      "Using coordinate-based selection (temporary workaround).")
        
        # For a point load on a cantilever, typically at the free end
        # Assumption: load is applied at Z=L or at a specific coordinate
        load_coord = getattr(load, 'load_coordinate', None)
        load_axis = getattr(load, 'load_axis', 2)  # Default Z axis
        tolerance = getattr(load, 'tolerance', 0.01)
        
        if load_coord is not None:
            node_indices = adapter.get_nodes_by_coordinate_filter(
                model_part,
                coordinate=load_axis,
                value=load_coord,
                tolerance=tolerance
            )
            
            if node_indices:
                adapter.apply_load_from_core(model_part, load, node_indices)
                logger.info(f"Load applied to {len(node_indices)} nodes by coordinate filter")
            else:
                logger.warning(f"No nodes found matching load criteria for {load.id}")
        else:
            logger.warning(f"Load {load.id} has no coordinate information, cannot apply")
            
    except Exception as e:
        logger.error(f"Failed to apply load geometrically: {e}")
        raise
