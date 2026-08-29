"""Core Topological Optimization and FEA solver interfaces.

Provides a deterministic interface and refuses to run fake/synthetic engineering results
until a verified FEA adapter is supplied.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

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
    cad_shape: Any = None,
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
        cad_shape: CadQuery/OpenCASCADE Shape of the CAD model. When provided,
            For each node definition, the application strategies follow this order:
            1. Named Kratos submodelpart (``submodelpart_name`` / ``boundary_name``).
            2. CAD face mapping (``location_face_id`` / ``application_face_id`` → real mesh nodes).
            3. Coordinate-based filtering (fallback, kept for backward compatibility).
        
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
            
            # Convert numpy arrays to list format for KratosAdapter.
            # Tolerant to both numpy arrays and plain python lists.
            nodes_arr = np.asarray(nodes, dtype=float)
            elements_arr = np.asarray(elements, dtype=int)
            nodes_list = nodes_arr.tolist()
            elements_list = elements_arr.tolist()
            
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
            # (1) named submodelpart, (2) CAD face mapping, (3) coordinate fallback.
            for constraint in constraints:
                _apply_constraint_geometrically(adapter, model_part, constraint, nodes_list, cad_shape)
            
            # Apply loads using geometric selection
            # CRITICAL FIX: No longer applies to ALL nodes
            # Instead, use geometric information to select load surface nodes
            for load in loads:
                _apply_load_geometrically(adapter, model_part, load, nodes_list, cad_shape)
            
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


def _face_mapping_failure_log(kind: str, cond_id: str, face_id: Any,
                              face_index: Any, matched_nodes: int,
                              tolerance: float, reason: str) -> None:
    """Emit the structured ``CAD FACE MAPPING FAILED`` diagnostic block.

    This is the single source of truth for reporting a failed CAD→node mapping.
    It is always emitted BEFORE any coordinate fallback is allowed so that a
    failure of the primary geometric mechanism is never silent.
    """
    raw_log = (
        f"CAD FACE MAPPING FAILED\n"
        f"{kind}: {cond_id}\n"
        f"face_id: {face_id}\n"
        f"face_index: {face_index}\n"
        f"matched_nodes: {matched_nodes}\n"
        f"tolerance: {tolerance}\n"
        f"reason: {reason}"
    )
    logger.warning(raw_log)


def _apply_constraint_by_face_mapping(adapter: Any, model_part: Any, constraint: Any,
                                      nodes_list: List[List[float]], cad_shape: Any) -> str:
    """Apply a constraint to the mesh nodes that lie on a real CAD face.

    Uses the Core ``BoundaryConditionMapper`` with the constraint's
    ``location_face_id`` resolved against the CAD shape. Physically anchored:
    it selects only the nodes on that B-Rep face, never an arbitrary region.

    Differentiates the five documented cases so a failure of the primary
    geometric mechanism is never hidden by calling to the coordinate fallback:

    * ``APPLIED``          (Case E): valid face + nodes found; default applied
                            exclusively to those nodes via CAD_FACE_MAPPING.
    * ``NO_FACE_ID``       (Case A): ``location_face_id``/``cad_shape`` absent;
                            the coordinate fallback is the documented mechanism.
    * ``INVALID_FACE_ID``  (Case B): identifier exists but is not resolvable;
                            reason documented; fallback NOT permitted (it would
                            mask the failure and select an unintended region).
    * ``OUT_OF_RANGE``     (Case C): identifier is a valid index but outside the
                            CAD face range; data error, documented; fallback
                            NOT permitted.
    * ``NO_NODES_MATCHED`` (Case D): valid face but zero matching mesh nodes;
                            CAD FACE MAPPING FAILED block emitted; fallback
                            NOT permitted.

    Returns a status string (never a bare bool). The caller only runs the
    coordinate fallback for ``NO_FACE_ID`` (Case A); every other non-APPLIED
    status means the user specified a face, so the condition is left unapplied
    rather than silently switched to a coordinate region.
    """
    from core.boundary import BoundaryConditionMapper, resolve_face_index

    face_id = getattr(constraint, "location_face_id", None)
    if cad_shape is None:
        logger.debug(
            f"Constraint {constraint.id}: no cad_shape available; CAD face mapping skipped"
        )
        return "NO_FACE_ID"

    face_index = resolve_face_index(face_id)
    if face_index is None:
        _face_mapping_failure_log(
            "constraint", constraint.id, face_id, face_index, 0, 0.0,
            f"location_face_id={face_id!r} is not a resolvable face index",
        )
        return "INVALID_FACE_ID"

    n_cad_faces = len(cad_shape.Faces())
    if face_index < 0 or face_index >= n_cad_faces:
        _face_mapping_failure_log(
            "constraint", constraint.id, face_id, face_index, 0, 0.0,
            f"face_index {face_index} out of range [0, {n_cad_faces})",
        )
        return "OUT_OF_RANGE"

    tolerance = getattr(constraint, "tolerance", 0.5)
    if not tolerance or tolerance <= 0:
        tolerance = 0.5

    try:
        mapped = BoundaryConditionMapper.map_faces_to_nodes(
            cad_shape, nodes_list, face_indices=[face_index], tolerance=tolerance
        )
    except Exception as e:
        _face_mapping_failure_log(
            "constraint", constraint.id, face_id, face_index, 0, tolerance,
            f"exception during mapping: {e}",
        )
        return "NO_NODES_MATCHED"

    if not mapped or not mapped[0].node_indices:
        _face_mapping_failure_log(
            "constraint", constraint.id, face_id, face_index, 0, tolerance,
            "no mesh nodes matched the CAD face",
        )
        return "NO_NODES_MATCHED"

    node_indices = mapped[0].node_indices
    adapter.apply_constraint_from_core(model_part, constraint, node_indices)
    logger.info(
        f"Constraint {constraint.id} applied to {len(node_indices)} nodes "
        f"via CAD face index {face_index} (face-based mapping) METHOD=CAD_FACE_MAPPING"
    )
    return "APPLIED"


def _apply_constraint_geometrically(adapter: Any, model_part: Any, constraint: Any,
                                    nodes_list: List[List[float]], cad_shape: Any = None) -> None:
    """Apply constraint using geometric node selection.

    ARCHITECTURE NOTE:
    This function implements proper geometric node selection for boundary conditions.
    Previously, constraints were applied to ALL nodes, creating an over-constrained system.

    Three strategies are attempted in order:
    1. Named submodelpart (exact, if the mesh was imported with physical groups)
    2. CAD face mapping (primary geometric mechanism): maps ``location_face_id``
       to the mesh nodes lying on that real CAD face using BoundaryConditionMapper
    3. Coordinate-based (fallback): filter nodes by coordinate (e.g., Z=0 for the
       fixed end). Kept only as a technical fallback.

    Args:
        adapter: KratosAdapter instance
        model_part: Kratos ModelPart
        constraint: ConstraintDefinition object
        nodes_list: Original node coordinates from Core
        cad_shape: CadQuery/OpenCASCADE Shape of the CAD model (or None)
    """
    try:
        from core.study import ConstraintType
        
        # Strategy 1: Try to use named submodelpart (e.g., from gmsh physical groups)
        submodelpart_name = getattr(constraint, 'submodelpart_name', None) or \
                           getattr(constraint, 'boundary_name', None)
        
        if submodelpart_name:
            node_indices = adapter.get_nodes_from_submodelpart(model_part, submodelpart_name)
            if node_indices:
                adapter.apply_constraint_from_core(model_part, constraint, node_indices)
                logger.info(f"Constraint {constraint.id} applied to {len(node_indices)} nodes "
                            f"via submodelpart '{submodelpart_name}'")
                return
            logger.warning(f"Submodelpart '{submodelpart_name}' has no nodes for constraint "
                           f"{constraint.id}; falling through to face mapping")
        
        # Strategy 2: CAD face mapping (primary geometric mechanism, physically anchored)
        status = _apply_constraint_by_face_mapping(adapter, model_part, constraint, nodes_list, cad_shape)
        if status == "APPLIED":
            return
        if status != "NO_FACE_ID":
            # Cases B (INVALID_FACE_ID), C (OUT_OF_RANGE) and D (NO_NODES_MATCHED)
            # all carry a face identifier. Per the REGLA FINAL, the coordinate
            # fallback must NOT run automatically when the user specified a CAD
            # face: doing so would silently mask the mapping failure and apply a
            # condition to the wrong region. The failure was already reported as
            # ``CAD FACE MAPPING FAILED``; stop here instead of papering over it.
            logger.warning(
                f"Constraint {constraint.id} specifies a CAD face that could not be "
                f"mapped (status={status}). Coordinate fallback NOT applied to avoid "
                f"silently selecting an unintended region."
            )
            return

        # Strategy 3: Fallback - use coordinate-based filtering
        # Only reached when NO face identifier was given (Case A: no cad_shape or
        # no location_face_id), where the coordinate filter is the documented
        # selection mechanism.
        logger.warning(f"No geometric face region resolved for constraint {constraint.id}. "
                      "Using coordinate-based selection (fallback).")
        
        # For a fixed constraint on a cantilever beam, typically fix the built-in end
        # Assumption: the fixed end is at Z=0 (this should be in constraint metadata)
        # Extract fixed end from constraint or default to Z=0
        fixed_coord = getattr(constraint, 'fixed_coordinate', 0.0)
        fixed_axis = getattr(constraint, 'fixed_axis', 2)  # Default Z axis
        tolerance = getattr(constraint, 'tolerance', 0.01)
        
        if fixed_coord is None:
            logger.warning(f"Constraint {constraint.id} has no coordinate or face information, cannot apply")
            return
        
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


def _apply_load_by_face_mapping(adapter: Any, model_part: Any, load: Any,
                                nodes_list: List[List[float]], cad_shape: Any) -> str:
    """Apply a load to the mesh nodes that lie on a real CAD face.

    Mirrors ``_apply_constraint_by_face_mapping`` using ``application_face_id``
    and the same case differentiation (A-E). Returns a status string.
    """
    from core.boundary import BoundaryConditionMapper, resolve_face_index

    face_id = getattr(load, "application_face_id", None)
    if cad_shape is None:
        logger.debug(
            f"Load {load.id}: no cad_shape available; CAD face mapping skipped"
        )
        return "NO_FACE_ID"

    face_index = resolve_face_index(face_id)
    if face_index is None:
        _face_mapping_failure_log(
            "load", load.id, face_id, face_index, 0, 0.0,
            f"application_face_id={face_id!r} is not a resolvable face index",
        )
        return "INVALID_FACE_ID"

    n_cad_faces = len(cad_shape.Faces())
    if face_index < 0 or face_index >= n_cad_faces:
        _face_mapping_failure_log(
            "load", load.id, face_id, face_index, 0, 0.0,
            f"face_index {face_index} out of range [0, {n_cad_faces})",
        )
        return "OUT_OF_RANGE"

    tolerance = getattr(load, "tolerance", 0.5)
    if not tolerance or tolerance <= 0:
        tolerance = 0.5

    try:
        mapped = BoundaryConditionMapper.map_faces_to_nodes(
            cad_shape, nodes_list, face_indices=[face_index], tolerance=tolerance
        )
    except Exception as e:
        _face_mapping_failure_log(
            "load", load.id, face_id, face_index, 0, tolerance,
            f"exception during mapping: {e}",
        )
        return "NO_NODES_MATCHED"

    if not mapped or not mapped[0].node_indices:
        _face_mapping_failure_log(
            "load", load.id, face_id, face_index, 0, tolerance,
            "no mesh nodes matched the CAD face",
        )
        return "NO_NODES_MATCHED"

    node_indices = mapped[0].node_indices
    adapter.apply_load_from_core(model_part, load, node_indices)
    logger.info(
        f"Load {load.id} applied to {len(node_indices)} nodes "
        f"via CAD face index {face_index} (face-based mapping) METHOD=CAD_FACE_MAPPING"
    )
    return "APPLIED"


def _apply_load_geometrically(adapter: Any, model_part: Any, load: Any,
                              nodes_list: List[List[float]], cad_shape: Any = None) -> None:
    """Apply load using geometric node selection.
    
    ARCHITECTURE NOTE:
    This function implements proper geometric node selection for loads.
    Previously, loads were applied to ALL nodes, creating an over-loaded system.
    
    Three strategies are attempted in order:
    1. Named submodelpart (exact, if the mesh was imported with physical groups)
    2. CAD face mapping (primary geometric mechanism): maps ``application_face_id``
       to the mesh nodes lying on that real CAD face using BoundaryConditionMapper
    3. Coordinate-based (fallback): filter nodes by coordinate (e.g., Z=L for the
       free end of a cantilever). Kept only as a technical fallback.

    Args:
        adapter: KratosAdapter instance
        model_part: Kratos ModelPart
        load: LoadDefinition object
        nodes_list: Original node coordinates from Core
        cad_shape: CadQuery/OpenCASCADE Shape of the CAD model (or None)
    """
    try:
        from core.study import LoadType
        
        # Strategy 1: Try to use named submodelpart (e.g., from gmsh physical groups)
        submodelpart_name = getattr(load, 'submodelpart_name', None) or \
                           getattr(load, 'boundary_name', None)
        
        if submodelpart_name:
            node_indices = adapter.get_nodes_from_submodelpart(model_part, submodelpart_name)
            if node_indices:
                adapter.apply_load_from_core(model_part, load, node_indices)
                logger.info(f"Load {load.id} applied to {len(node_indices)} nodes "
                            f"via submodelpart '{submodelpart_name}'")
                return
            logger.warning(f"Submodelpart '{submodelpart_name}' has no nodes for load "
                           f"{load.id}; falling through to face mapping")
        
        # Strategy 2: CAD face mapping (primary geometric mechanism, physically anchored)
        status = _apply_load_by_face_mapping(adapter, model_part, load, nodes_list, cad_shape)
        if status == "APPLIED":
            return
        if status != "NO_FACE_ID":
            # Cases B/C/D carry a face identifier. Coordinate fallback must NOT run
            # automatically: it would silently mask the mapping failure and select
            # an unintended region. The failure was already reported via
            # ``CAD FACE MAPPING FAILED``.
            logger.warning(
                f"Load {load.id} specifies a CAD face that could not be mapped "
                f"(status={status}). Coordinate fallback NOT applied to avoid "
                f"silently selecting an unintended region."
            )
            return

        # Strategy 3: Fallback - use coordinate-based filtering
        # Only reached when NO application face was given (Case A).
        logger.warning(f"No geometric face region resolved for load {load.id}. "
                      "Using coordinate-based selection (fallback).")
        
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
            logger.warning(f"Load {load.id} has no coordinate or face information, cannot apply")
            
    except Exception as e:
        logger.error(f"Failed to apply load geometrically: {e}")
        raise
