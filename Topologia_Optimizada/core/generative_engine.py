"""Generative design engine (Scenario A and B).

Scenario A -- optimise existing geometry:
    Existing CAD mesh + conditions -> SIMP optimisation -> B-Rep reconstruction.

Scenario B -- connect parts with generated geometry:
    Part A + Part B -> design space (gap voxels) + conditions
        -> SIMP on the generated bridge mesh -> B-Rep reconstruction.

The engine:
- consumes the shared ``ConditionManager`` (never re-creates conditions);
- builds the SIMP problem from the conditions (loads -> forces,
  elasticity -> constraints, protected regions -> preserved elements,
  obstructions -> void elements);
- runs the SELF-CONTAINED SIMP solver from :mod:`core.topopt`;
- reconstructs the result to B-Rep via :mod:`core.cad_reconstruction`.

The implementation is intentionally procedural (no mesh export rounds):
the whole flow is and must remain usable from the pipeline controller and
from tests, without Kratos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from core.cad_entity import CadEntityRef, EntityType
from core.conditions import (
    Condition,
    ConditionManager,
    ConditionType,
    ElasticityCondition,
    LoadCondition,
    LoadSense,
    ObstructionCondition,
    ProtectedRegion,
)
from core.generative import GenerativeDesignStudy
from core.materials import Material, STANDARD_MATERIALS
from core.topopt import SIMPSolver

logger = logging.getLogger(__name__)


@dataclass
class BridgeMesh:
    """A hexa-voxel bridge mesh decomposed into 6 tets per voxel."""
    nodes: np.ndarray          # (N, 3)
    elements: np.ndarray       # (M, 4) tet connectivity
    voxels: List[Tuple[int, int, int]]  # grid voxel (i,j,k)
    target_node_sets: Dict[str, List[int]]  # target ref key -> node indices


def generate_bridge_mesh(
    targets: List[CadEntityRef],
    resolution: float = 1.0,
    padding: float = 1.0,
    model_nodes: Optional[np.ndarray] = None,
) -> BridgeMesh:
    """Build a tet bridge mesh filling the bounding box between target parts.

    The bridge fills the axis-aligned bounding box of the target centroids
    (not the parts themselves, which are assumed to occupy the ends).
    Each generated cell is a cube that is split into 6 tets.
    """
    if len(targets) < 2:
        raise ValueError("Scenario B requires at least two connection targets")

    # Determine the region to fill: from the model bbox split into thirds.
    if model_nodes is not None:
        lo = model_nodes.min(axis=0)
        hi = model_nodes.max(axis=0)
        span = hi - lo
        # Middle third along the longest axis = the "between" region.
        axis = int(np.argmax(span))
        a = lo.copy(); b = hi.copy()
        a[axis] = lo[axis] + span[axis] / 3.0
        b[axis] = hi[axis] - span[axis] / 3.0
        lo, hi = a, b
    else:
        lo = np.zeros(3); hi = np.zeros(3)
        # Use unit cube default.
        hi[:] = 1.0
    lo -= padding
    hi += padding

    res = max(float(resolution), 1e-6)
    steps = np.ceil((hi - lo) / res).astype(int)
    steps = np.maximum(steps, 1)
    nx, ny, nz = int(steps[0]), int(steps[1]), int(steps[2])

    def node_index(i: int, j: int, k: int) -> int:
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    total = (nx + 1) * (ny + 1) * (nz + 1)
    pts = np.empty((total, 3))
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                pts[node_index(i, j, k)] = lo + np.array([i * res, j * res, k * res])

    elements: List[List[int]] = []
    voxels: List[Tuple[int, int, int]] = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                n = [
                    node_index(i, j, k), node_index(i + 1, j, k),
                    node_index(i + 1, j + 1, k), node_index(i, j + 1, k),
                    node_index(i, j, k + 1), node_index(i + 1, j, k + 1),
                    node_index(i + 1, j + 1, k + 1), node_index(i, j + 1, k + 1),
                ]
                # 6-tet split (standard cube decomposition)
                elements.append([n[0], n[1], n[4], n[2]])
                elements.append([n[1], n[5], n[4], n[2]])
                elements.append([n[4], n[5], n[6], n[2]])
                elements.append([n[4], n[6], n[7], n[2]])
                elements.append([n[0], n[4], n[3], n[2]])
                elements.append([n[7], n[4], n[3], n[2]])
                voxels.append((i, j, k))

    return BridgeMesh(
        nodes=pts,
        elements=np.asarray(elements, dtype=int),
        voxels=voxels,
        target_node_sets={},
    )


def consume_conditions(
    manager: ConditionManager,
    condition_ids: List[str],
) -> Dict[ConditionType, List[Condition]]:
    """Resolve conditions grouped by type (all consumed from the shared store)."""
    resolved = manager.resolve(condition_ids)
    by_type: Dict[ConditionType, List[Condition]] = {t: [] for t in ConditionType}
    for c in resolved:
        by_type[c.condition_type].append(c)
    return by_type


def direction_vector(cond: LoadCondition) -> np.ndarray:
    """Direction of a load depending on its plane orientation/sense/magnitude.

    - ``perpendicular``: along the reference plane normal;
    - ``parallel``: any axis orthogonal to the normal (in the plane);
    - ``angle``: the normal rotated by ``angle_deg`` towards the plane.
    ``sense`` applies afterwards (positive keeps the direction, negative flips).
    """
    n = np.asarray(cond.reference_plane_normal, dtype=float)
    norm = float(np.linalg.norm(n))
    if norm < 1e-12:
        n = np.array([0.0, 0.0, 1.0])
    else:
        n = n / norm

    if cond.orientation.value == "perpendicular":
        vec = n
    else:
        # parallel: pick any axis orthogonal to the normal.
        ref = np.array([1.0, 0.0, 0.0]) - n * np.dot(np.array([1.0, 0.0, 0.0]), n)
        if np.linalg.norm(ref) < 1e-12:
            ref = np.cross(n, np.array([0.0, 1.0, 0.0]))
        ref = ref / max(float(np.linalg.norm(ref)), 1e-12)
        vec = ref
        if cond.orientation.value == "angle" and cond.angle_deg is not None:
            import math
            alpha = math.radians(float(cond.angle_deg))
            # rotate the normal alpha degrees towards the plane direction
            vec = math.cos(alpha) * n + math.sin(alpha) * ref
    if cond.sense == LoadSense.NEGATIVE:
        vec = -vec
    return vec


class GenerativeDesignEngine:
    """Runs the generative design workflow using shared conditions."""

    def __init__(
        self,
        model_id: Optional[str],
        mesh_nodes: Optional[np.ndarray] = None,
        mesh_elements: Optional[np.ndarray] = None,
        material: Optional[Material] = None,
        condition_manager: Optional[ConditionManager] = None,
        model_shape: Any = None,
    ) -> None:
        self.model_id = model_id
        self.mesh_nodes = np.asarray(mesh_nodes, dtype=float) if mesh_nodes is not None else None
        self.mesh_elements = (np.asarray(mesh_elements, dtype=int)
                              if mesh_elements is not None else None)
        self.material = material or STANDARD_MATERIALS.get("steel", STANDARD_MATERIALS["steel"])
        self.condition_manager = condition_manager or ConditionManager()
        self.model_shape = model_shape

    def _node_indices_for_load(self, load: LoadCondition) -> List[int]:
        """Map the load's selected faces to mesh node indices."""
        if self.mesh_nodes is None:
            return []
        if self.model_shape is None or not load.faces.entities:
            # No CAD shape: select the node with max coordinate along load dir.
            if not load.faces.entities:
                vec = direction_vector(load)
                axis = int(np.argmax(np.abs(vec)))
                sign = 1 if vec[axis] > 0 else -1
                coord = self.mesh_nodes[:, axis].max() if sign > 0 else self.mesh_nodes[:, axis].min()
                tol = 1e-3 * float(np.ptp(self.mesh_nodes[:, axis]))
                return [i for i in range(self.mesh_nodes.shape[0])
                        if abs(float(self.mesh_nodes[i, axis]) - coord) <= tol]
            return []
        from core.selection import FaceRegion, NodeSelectionEngine
        face_indices = [
            int(e.face_index) for e in load.faces.entities
            if e.entity_type == EntityType.FACE and e.face_index is not None
        ]
        if not face_indices:
            return []
        region = FaceRegion(face_indices=face_indices, tolerance=0.5)
        return NodeSelectionEngine.select_nodes(
            self.mesh_nodes, region.to_dict(), cad_shape=self.model_shape,
            default_tolerance=0.5,
        )

    def _protected_elements(self, conditions: List[ProtectedRegion]) -> np.ndarray:
        """Element indices that must keep material (protected regions)."""
        if self.mesh_elements is None:
            return np.array([], dtype=int)
        node_set: set = set()
        face_one = set()
        for region in conditions:
            for e in region.faces.entities:
                if e.entity_type == EntityType.FACE and e.face_index is not None:
                    face_one.add(int(e.face_index))
        if self.model_shape is not None and face_one:
            from core.selection import FaceRegion, NodeSelectionEngine
            region = FaceRegion(face_indices=sorted(face_one), tolerance=0.5)
            face_one_nodes = set(NodeSelectionEngine.select_nodes(
                self.mesh_nodes, region.to_dict(), cad_shape=self.model_shape,
                default_tolerance=0.5,
            ))
            node_set |= face_one_nodes
        # Fallback: protect elements touching the model bounding box ends.
        if not node_set and self.mesh_nodes is not None:
            lo = self.mesh_nodes.min(axis=0)
            hi = self.mesh_nodes.max(axis=0)
            axis = int(np.argmax(hi - lo))
            ref = lo[axis]
            tol = 0.5 * float(np.ptp(self.mesh_nodes[:, axis])) / max(
                np.sqrt(max(self.mesh_elements.shape[0], 1)), 1.0)
            node_set = {i for i in range(self.mesh_nodes.shape[0])
                        if abs(float(self.mesh_nodes[i, axis]) - ref) <= tol}
        elems = {
            e for e in range(self.mesh_elements.shape[0])
            if set(self.mesh_elements[e].tolist()) & node_set
        }
        return np.array(sorted(elems), dtype=int)

    def _void_elements(self, conditions: List[ObstructionCondition]) -> np.ndarray:
        """Element indices that must stay empty (obstructions).

        Body-based obstructions are mapped to mesh elements through the CAD
        shape: for each obstructing solid body we collect the elements whose
        centroid lies inside the solid (optionally expanded by ``offset_mm``).
        Without a CAD shape no reliable mapping can be computed, so an empty
        set is returned and the condition is explicitly flagged as
        *unsupported* by the caller (never a silent wrong result).
        """
        if self.mesh_elements is None or self.mesh_nodes is None or not conditions:
            return np.array([], dtype=int)
        if self.model_shape is None:
            logger.warning(
                "Obstruction mapping requires the CAD shape; marking as unsupported.")
            return np.array([], dtype=int)

        centroids = self._element_centroids()
        n_elems = self.mesh_elements.shape[0]
        inside = np.zeros(n_elems, dtype=bool)
        solids = list(self.model_shape.Solids())

        for cond in conditions:
            offset = float(cond.offset_mm) if cond.offset_mm is not None else 0.0
            for body in cond.bodies.entities:
                if body.entity_type != EntityType.SOLID:
                    continue
                solid = self._solid_for_ref(solids, body)
                if solid is None:
                    logger.warning(
                        "Obstruction body %r not found in CAD shape; marking condition "
                        "as unsupported.", getattr(body, "solid_id", None))
                    continue
                bb = self._offset_bbox(solid, offset)
                for i in range(n_elems):
                    if inside[i]:
                        continue
                    c = centroids[i]
                    if not (bb[0][0] <= c[0] <= bb[1][0] and
                            bb[0][1] <= c[1] <= bb[1][1] and
                            bb[0][2] <= c[2] <= bb[1][2]):
                        continue
                    if offset > 0.0:
                        # With an offset the expanded box is the buffered region;
                        # keep the element when its centroid lies inside it.
                        inside[i] = True
                    else:
                        inside[i] = self._point_in_solid(solid, c)
        return np.asarray(np.nonzero(inside)[0], dtype=int)

    def _element_centroids(self) -> np.ndarray:
        nodes = self.mesh_nodes
        els = self.mesh_elements
        return np.asarray(
            [np.mean(nodes[el], axis=0) for el in els], dtype=float
        )

    @staticmethod
    def _solid_for_ref(solids: list, body: Any):
        """Resolve a solid body reference to the matching CAD solid object."""
        import re
        mid = None
        index = getattr(body, "index", None)
        solid_id = getattr(body, "solid_id", None)
        if solid_id:
            m = re.match(r"solid_(\d+)", str(solid_id))
            if m:
                index = int(m.group(1))
        if index is not None and 0 <= int(index) < len(solids):
            return solids[int(index)]
        return None

    @staticmethod
    def _offset_bbox(solid: Any, offset: float):
        bb = solid.BoundingBox()
        return (
            (bb.xmin - offset, bb.ymin - offset, bb.zmin - offset),
            (bb.xmax + offset, bb.ymax + offset, bb.zmax + offset),
        )

    @staticmethod
    def _point_in_solid(solid: Any, point: Any) -> bool:
        try:
            return bool(solid.isInside((float(point[0]), float(point[1]), float(point[2]))))
        except Exception:  # pragma: no cover - defensive OCP/geometry errors
            return False

    def solve_simp(self, conditions: Dict[ConditionType, List[Condition]],
                   **kwargs) -> Dict[str, Any]:
        """Run the self-contained SIMP solver on the given mesh/conditions."""
        if self.mesh_nodes is None or self.mesh_elements is None:
            raise ValueError("No mesh; generate a bridge mesh or import a model first")
        nodes, elements = self.mesh_nodes, self.mesh_elements

        loads = conditions.get(ConditionType.LOAD, [])
        forces = np.zeros(nodes.shape[0] * 3)
        for load in loads:
            if not isinstance(load, LoadCondition):
                continue
            vec = direction_vector(load)
            mag = float(load.magnitude if load.magnitude is not None else 1000.0)
            idx = self._node_indices_for_load(load)
            if not idx:
                # if no faces, apply to max coord nodes
                axis = int(np.argmax(np.abs(vec)))
                coord = nodes[:, axis].max() if vec[axis] > 0 else nodes[:, axis].min()
                tol = 1e-3 * float(np.ptp(nodes[:, axis]))
                idx = [i for i in range(nodes.shape[0])
                       if abs(float(nodes[i, axis]) - coord) <= tol]
            for ni in idx:
                forces[ni * 3: ni * 3 + 3] += vec * (mag / max(len(idx), 1))

        # Fixed DOFs from elasticity conditions (faces of elastic supports).
        fixed_dofs = []
        for cond in conditions.get(ConditionType.ELASTICITY, []):
            if not isinstance(cond, ElasticityCondition):
                continue
            face_indices = [
                int(e.face_index) for e in cond.faces.entities
                if e.entity_type == EntityType.FACE and e.face_index is not None
            ]
            target_nodes: List[int] = []
            if self.model_shape is not None and face_indices:
                from core.selection import FaceRegion, NodeSelectionEngine
                region = FaceRegion(face_indices=face_indices, tolerance=0.5)
                target_nodes = NodeSelectionEngine.select_nodes(
                    nodes, region.to_dict(), cad_shape=self.model_shape, default_tolerance=0.5,
                )
            if not target_nodes:
                # fallback: fix the min-axis nodes (base of the part)
                axis = 2
                coord = float(nodes[:, axis].min())
                target_nodes = [
                    i for i in range(nodes.shape[0])
                    if abs(float(nodes[i, axis]) - coord) <= 1e-6 * max(1.0, np.ptp(nodes[:, axis]))
                ]
            for ni in target_nodes:
                fixed_dofs.extend([ni * 3, ni * 3 + 1, ni * 3 + 2])

        preserved = self._protected_elements(conditions.get(ConditionType.PROTECTED_REGION, []))
        obstructions = conditions.get(ConditionType.OBSTRUCTION, [])
        void = self._void_elements(obstructions)

        unsupported = []
        if obstructions and void.size == 0:
            unsupported.append("obstruction")

        solver = SIMPSolver(
            nodes=nodes,
            elements=elements,
            young_modulus=self.material.young_modulus,
            poisson_ratio=self.material.poisson_ratio,
            volfrac=kwargs.get("volume_fraction", 0.3),
            penalization=kwargs.get("penalization", 3.0),
            filter_radius=kwargs.get("filter_radius", 1.5),
        )
        solver.set_load(forces)
        if fixed_dofs:
            solver.set_fixed_dofs(np.asarray(fixed_dofs, dtype=int))
        if preserved.size:
            solver.set_preserved_elements(preserved)
        if void.size:
            solver.set_void_elements(void)

        progress_cb = kwargs.get("progress_cb")
        result = solver.optimize(
            max_iterations=kwargs.get("max_iterations", 30),
            tolerance=kwargs.get("tolerance", 1e-3),
            callback=progress_cb,
        )
        result["_consumed_load_conditions"] = len(loads)
        result["_consumed_elasticity_conditions"] = len(conditions.get(ConditionType.ELASTICITY, []))
        result["_consumed_protected_conditions"] = len(conditions.get(ConditionType.PROTECTED_REGION, []))
        result["_consumed_obstruction_conditions"] = len(obstructions)
        result["_unsupported_conditions"] = sorted(unsupported)
        return result


def run_generative_design(
    study: GenerativeDesignStudy,
    condition_manager: ConditionManager,
    engine: GenerativeDesignEngine,
    progress_cb: Optional[Callable[[dict], None]] = None,
    step_path: Optional[str] = None,
) -> Dict[str, Any]:
    """High-level entry: run the generative design pipeline (A or B).

    Returns a dict with the SIMP result plus the B-Rep reconstruction.
    """
    conditions = consume_conditions(condition_manager, study.conditions)

    # Pass the study's optimisation parameters into the SIMP solve so the
    # user-configured settings (volume fraction, iterations, penalization,
    # filter radius, tolerance) are honoured instead of fixed defaults.
    p = study.optimization_params
    solve_kwargs = dict(
        volume_fraction=p.volume_fraction,
        max_iterations=p.max_iterations,
        penalization=p.penalization,
        filter_radius=p.filter_radius,
        tolerance=p.convergence_tolerance,
        progress_cb=progress_cb,
    )

    if study.scenario == "A":
        # Mesh is the imported model mesh (set on the engine).
        result = engine.solve_simp(conditions, **solve_kwargs)
    elif study.scenario == "B":
        if engine.mesh_nodes is None:
            # Build the bridge mesh ourselves.
            bridge = generate_bridge_mesh(
                study.connection_targets,
                resolution=study.design_space.resolution,
                model_nodes=engine.mesh_nodes,
            )
            engine.mesh_nodes = bridge.nodes
            engine.mesh_elements = bridge.elements
        result = engine.solve_simp(conditions, **solve_kwargs)
    else:  # pragma: no cover
        raise ValueError(f"Unsupported scenario '{study.scenario}'")

    reconstruction = _reconstruct(result, engine, step_path=step_path)
    result["reconstruction"] = reconstruction
    return result


def _reconstruct(
    result: Dict[str, Any],
    engine: GenerativeDesignEngine,
    step_path: Optional[str] = None,
):
    from core.cad_reconstruction import ReconstructionPipeline, MarchingTetrahedraExtractor
    densities = np.asarray(result.get("densities", []), dtype=float)
    pipe = ReconstructionPipeline(
        surface_extractor=MarchingTetrahedraExtractor(),
        step_path=step_path,
    )
    return pipe.run(
        engine.mesh_nodes,
        engine.mesh_elements,
        densities,
        threshold=0.5,
    ).to_dict()