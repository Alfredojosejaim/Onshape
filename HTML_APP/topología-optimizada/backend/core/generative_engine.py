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
from core.boundary import is_pressure_unit
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
        face_surface_elements: Optional[Dict[str, List[List[int]]]] = None,
        physical_groups: Optional[Dict[str, List[int]]] = None,
    ) -> None:
        self.model_id = model_id
        self.mesh_nodes = np.asarray(mesh_nodes, dtype=float) if mesh_nodes is not None else None
        self.mesh_elements = (np.asarray(mesh_elements, dtype=int)
                              if mesh_elements is not None else None)
        self.material = material or STANDARD_MATERIALS.get("steel", STANDARD_MATERIALS["steel"])
        self.condition_manager = condition_manager or ConditionManager()
        self.model_shape = model_shape
        self.face_surface_elements = face_surface_elements or {}
        self._face_index_to_groups: Dict[int, List[str]] = {}
        if physical_groups:
            for grp_name, face_indices in physical_groups.items():
                for fi in face_indices:
                    self._face_index_to_groups.setdefault(int(fi), []).append(grp_name)

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

    def _face_triangles_for_load(self, load: LoadCondition,
                                   node_indices: Optional[List[int]] = None,
                                   allow_boundary_fallback: bool = True) -> List[List[int]]:
        """Collect surface triangles for the faces referenced by *load*.

        Delegates to :func:`core.boundary.face_triangles_for_indices` (single
        source of truth, shared with the Kratos path). Empty list when no
        surface triangulation is available (triggers uniform fallback). The
        undifferentiated ``"boundary"`` bucket is strictly a LAST RESORT
        (explicit warning inside the helper); pass
        ``allow_boundary_fallback=False`` to disable it.
        """
        from core.boundary import face_triangles_for_indices
        if not self.face_surface_elements:
            return []
        face_indices = [
            int(e.face_index) for e in load.faces.entities
            if e.entity_type == EntityType.FACE and e.face_index is not None
        ]
        if node_indices is None and "boundary" in self.face_surface_elements:
            node_indices = self._node_indices_for_load(load)
        tris, _ = face_triangles_for_indices(
            face_indices, self.face_surface_elements,
            group_index=getattr(self, "_face_index_to_groups", None),
            node_indices=node_indices,
            allow_boundary_fallback=allow_boundary_fallback,
        )
        return tris

    def _load_node_indices(self, conditions: Dict) -> List[int]:
        """Collect all mesh node indices targeted by load conditions."""
        nodes: set = set()
        for load in conditions.get(ConditionType.LOAD, []):
            if isinstance(load, LoadCondition):
                nodes |= set(self._node_indices_for_load(load))
        return sorted(nodes)

    def _support_node_indices(self, conditions: Dict) -> List[int]:
        """Collect all mesh node indices targeted by elasticity (support) conditions."""
        nodes: set = set()
        for cond in conditions.get(ConditionType.ELASTICITY, []):
            if not isinstance(cond, ElasticityCondition):
                continue
            face_indices = [
                int(e.face_index) for e in cond.faces.entities
                if e.entity_type == EntityType.FACE and e.face_index is not None
            ]
            if self.model_shape is not None and face_indices:
                from core.selection import FaceRegion, NodeSelectionEngine
                region = FaceRegion(face_indices=face_indices, tolerance=0.5)
                nodes |= set(NodeSelectionEngine.select_nodes(
                    self.mesh_nodes, region.to_dict(),
                    cad_shape=self.model_shape, default_tolerance=0.5,
                ))
        return sorted(nodes)

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
        # Explicit heuristic (not a CAD-face mapping): only applies when no
        # protected-region face resolved to nodes.
        if not node_set and self.mesh_nodes is not None:
            logger.warning(
                "ProtectedRegion: no face mapped to mesh nodes; protecting "
                "bbox-end elements explicitly (heuristic fallback, not a "
                "CAD-face mapping).")
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

    def _force_vector_for_load(self, load, raise_on_unmapped_face=True):
        """Vector de fuerza de UNA LoadCondition (un caso de carga).

        Devuelve ``(vec, node_idx, unsupported_flag)``. Extrae la logica de
        distribucion de ``_map_conditions_to_problem`` para reutilizarla en
        el camino multicarga sin duplicar fisica.
        """
        from core.boundary import nodal_area_weights
        nodes = self.mesh_nodes
        vec = direction_vector(load)
        mag = float(load.magnitude if load.magnitude is not None else 1000.0)
        idx = self._node_indices_for_load(load)
        if not idx and load.faces.entities and raise_on_unmapped_face:
            return None, [], "load"
        if not idx:
            axis = int(np.argmax(np.abs(vec)))
            coord = nodes[:, axis].max() if vec[axis] > 0 else nodes[:, axis].min()
            tol = 1e-3 * float(np.ptp(nodes[:, axis]))
            idx = [i for i in range(nodes.shape[0])
                   if abs(float(nodes[i, axis]) - coord) <= tol]
        single = np.zeros(nodes.shape[0] * 3)
        face_tris = self._face_triangles_for_load(load, node_indices=idx)
        if is_pressure_unit(getattr(load, "unit", "N")):
            from core.boundary import surface_area_mm2, pressure_to_total_force_N
            area = surface_area_mm2(nodes, face_tris)
            if area <= 0.0:
                if raise_on_unmapped_face:
                    return None, [], "load(pressure: sin área)"
                return single, idx, None
            mag = pressure_to_total_force_N(mag, load.unit, area)
        if face_tris:
            weights = nodal_area_weights(nodes, face_tris, idx)
            for ni in idx:
                single[ni * 3: ni * 3 + 3] += vec * (mag * weights.get(ni, 1.0 / max(len(idx), 1)))
        else:
            for ni in idx:
                single[ni * 3: ni * 3 + 3] += vec * (mag / max(len(idx), 1))
        return single, idx, None

    def _map_conditions_to_load_cases(self, conditions, raise_on_unmapped_face=True):
        """MULTICARGA: una entrada por LoadCondition (o grupo load_case_id).

        Agrupa por ``load.metadata["load_case_id"]`` cuando existe (varias
        cargas fisicas en el mismo caso se suman); si no, cada condicion es
        su propio caso. Peso por caso desde ``metadata["load_weight"]``
        (default 1.0). Devuelve ``(cases, weights, unsupported)`` con cases
        como lista de vectores de fuerza.
        """
        loads = conditions.get(ConditionType.LOAD, [])
        grouped: Dict[str, np.ndarray] = {}
        group_weight: Dict[str, float] = {}
        order: List[str] = []
        unsupported = []
        for n, load in enumerate(loads):
            if not isinstance(load, LoadCondition):
                continue
            meta = getattr(load, "metadata", None) or {}
            gid = str(meta.get("load_case_id", f"__single_{n}_{load.id}"))
            w = float(meta.get("load_weight", 1.0))
            single, _idx, uns = self._force_vector_for_load(load, raise_on_unmapped_face)
            if uns:
                unsupported.append(uns)
                continue
            if gid not in grouped:
                grouped[gid] = single
                group_weight[gid] = w
                order.append(gid)
            else:
                grouped[gid] = grouped[gid] + single
        cases = [grouped[g] for g in order]
        weights = [group_weight[g] for g in order]
        return cases, weights, sorted(set(unsupported))

    def _map_conditions_to_problem(self, conditions, raise_on_unmapped_face=True):
        """Translate reusable conditions into a quasi-static FE problem.

        Returns ``(force_vector, fixed_dofs, preserved, void, unsupported)``
        where ``unsupported`` is a list of condition kinds that were selected on
        real CAD faces but could not be mapped to mesh nodes.

        A coordinate-based fallback (max/min axis nodes) is only applied when a
        load/support has **no** selected face: that is a legitimate default.  If a
        real face was selected but the mapping fails, the condition is reported as
        unsupported instead of silently substituting arbitrary nodes.
        """
        nodes = self.mesh_nodes
        elements = self.mesh_elements

        loads = conditions.get(ConditionType.LOAD, [])
        forces = np.zeros(nodes.shape[0] * 3)
        unsupported = []
        for load in loads:
            if not isinstance(load, LoadCondition):
                continue
            vec = direction_vector(load)
            mag = float(load.magnitude if load.magnitude is not None else 1000.0)
            idx = self._node_indices_for_load(load)
            if not idx and load.faces.entities and raise_on_unmapped_face:
                unsupported.append("load")
                continue
            if not idx:
                axis = int(np.argmax(np.abs(vec)))
                coord = nodes[:, axis].max() if vec[axis] > 0 else nodes[:, axis].min()
                tol = 1e-3 * float(np.ptp(nodes[:, axis]))
                idx = [i for i in range(nodes.shape[0])
                       if abs(float(nodes[i, axis]) - coord) <= tol]
            # Tributary-area weighting: distribute total magnitude proportionally
            # to each node's tributary surface area when face triangulation is
            # available; fall back to uniform distribution otherwise.
            face_tris = self._face_triangles_for_load(load, node_indices=idx)
            # PRESSURE units (Pa/kPa/MPa): total force = p × face area (mm²→m²).
            # Without triangulation there is no area → honest unsupported, never
            # a silent Pa-as-N substitution.
            if is_pressure_unit(getattr(load, "unit", "N")):
                from core.boundary import surface_area_mm2, pressure_to_total_force_N
                area = surface_area_mm2(nodes, face_tris)
                if area <= 0.0:
                    if raise_on_unmapped_face:
                        unsupported.append("load(pressure: sin área)")
                    continue
                mag = pressure_to_total_force_N(mag, load.unit, area)
                logger.info("Load %s: presión %s %s sobre %.3f mm² → %.6f N totales.",
                            getattr(load, "name", "?"), load.magnitude, load.unit, area, mag)
            if face_tris:
                from core.boundary import nodal_area_weights
                weights = nodal_area_weights(nodes, face_tris, idx)
                for ni in idx:
                    forces[ni * 3: ni * 3 + 3] += vec * (mag * weights.get(ni, 1.0 / max(len(idx), 1)))
            else:
                if len(idx) > 1:
                    logger.warning(
                        "Load %s: no surface triangulation available for its "
                        "face -- falling back to UNIFORM per-node force "
                        "distribution across %d nodes. Total force resultant is "
                        "conserved but the spatial distribution is likely "
                        "physically inaccurate.",
                        getattr(load, "name", "?"), len(idx),
                    )
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
            if not target_nodes and face_indices and raise_on_unmapped_face:
                unsupported.append("elasticity")
                continue
            if not target_nodes:
                # no face selected (or permissive SIMP mode): default to the
                # min-axis nodes (base of the part).
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

        if obstructions and void.size == 0:
            unsupported.append("obstruction")

        return forces, fixed_dofs, preserved, void, sorted(set(unsupported))

    def build_fea_problem(self, conditions):
        """Build a quasi-static FE problem from reusable conditions.

        Returns ``(force_vector, fixed_dofs_array)`` suitable for
        ``core.fea.solve_fea``.  Raises if a selected CAD face cannot be mapped
        to mesh nodes so a support/load is never silently relocated.
        """
        if self.mesh_nodes is None or self.mesh_elements is None:
            raise ValueError("No mesh; generate a bridge mesh or import a model first")
        forces, fixed_dofs, _preserved, _void, unsupported = \
            self._map_conditions_to_problem(conditions, raise_on_unmapped_face=True)
        if unsupported:
            raise ValueError(
                "No se pudieron mapear caras seleccionadas a nodos de la malla: "
                + ", ".join(unsupported)
            )
        return forces, np.asarray(fixed_dofs, dtype=int)

    def solve_simp(self, conditions: Dict[ConditionType, List[Condition]],
                   **kwargs) -> Dict[str, Any]:
        """Run the self-contained SIMP solver on the given mesh/conditions."""
        if self.mesh_nodes is None or self.mesh_elements is None:
            raise ValueError("No mesh; generate a bridge mesh or import a model first")
        nodes, elements = self.mesh_nodes, self.mesh_elements

        forces, fixed_dofs, preserved, void, unsupported = \
            self._map_conditions_to_problem(conditions, raise_on_unmapped_face=False)
        # MULTICARGA: casos separados (misma fisica que el vector sumado).
        cases, weights, unsupported_cases = \
            self._map_conditions_to_load_cases(conditions, raise_on_unmapped_face=False)
        for u in unsupported_cases:
            if u not in unsupported:
                unsupported.append(u)
        if not cases:
            # Sin casos (p.ej. todo unsupported en modo permisivo): vector nulo
            # unico para no romper el contrato del solver.
            cases, weights = [forces], [1.0]

        solver = SIMPSolver(
            nodes=nodes,
            elements=elements,
            young_modulus=self.material.young_modulus,
            poisson_ratio=self.material.poisson_ratio,
            volfrac=kwargs.get("volume_fraction", 0.3),
            penalization=kwargs.get("penalization", 3.0),
            filter_radius=kwargs.get("filter_radius", 1.5),
        )
        solver.set_loads(cases, weights)
        if fixed_dofs:
            solver.set_fixed_dofs(np.asarray(fixed_dofs, dtype=int))
        if preserved.size:
            solver.set_preserved_elements(preserved)
        if void.size:
            solver.set_void_elements(void)

        # Automatic halo around load / support nodes (opt-in via halo_radius;
        # None means disabled for backward compatibility with existing tests).
        halo_radius = kwargs.get("halo_radius")
        if halo_radius is not None:
            halo_nodes = set(self._load_node_indices(conditions))
            halo_nodes |= set(self._support_node_indices(conditions))
            if halo_nodes:
                solver.protect_elements_near_nodes(
                    list(halo_nodes), radius=float(halo_radius),
                )

        progress_cb = kwargs.get("progress_cb")
        result = solver.optimize(
            max_iterations=kwargs.get("max_iterations", 30),
            tolerance=kwargs.get("tolerance", 1e-3),
            callback=progress_cb,
        )
        result["_consumed_load_conditions"] = len(conditions.get(ConditionType.LOAD, []))
        result["_consumed_elasticity_conditions"] = len(conditions.get(ConditionType.ELASTICITY, []))
        result["_consumed_protected_conditions"] = len(conditions.get(ConditionType.PROTECTED_REGION, []))
        result["_consumed_obstruction_conditions"] = len(conditions.get(ConditionType.OBSTRUCTION, []))
        result["_unsupported_conditions"] = sorted(unsupported)
        result["_preserved_elements"] = [int(i) for i in np.asarray(
            preserved, dtype=int).ravel().tolist()] if preserved.size else []
        result["_frozen_elements"] = []
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
        halo_radius=None,  # Solver computes from actual mesh element size
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
    frozen_elements: Optional[List[int]] = None,
    preserved_elements: Optional[List[int]] = None,
):
    from core.cad_reconstruction import (
        ReconstructionPipeline,
        ReconstructionStage,
        MarchingTetrahedraExtractor,
    )
    densities = np.asarray(result.get("densities", []), dtype=float)
    frozen = list(frozen_elements) if frozen_elements is not None else list(
        result.get("_frozen_elements", []) or [])
    preserved = (list(preserved_elements) if preserved_elements is not None
                 else list(result.get("_preserved_elements", []) or []))
    pipe = ReconstructionPipeline(
        surface_extractor=MarchingTetrahedraExtractor(),
        step_path=step_path,
    )
    final = pipe.run(
        engine.mesh_nodes,
        engine.mesh_elements,
        densities,
        threshold=0.5,
        frozen_elements=frozen or None,
        preserved_elements=preserved or None,
    )
    out = final.to_dict()
    if frozen:
        out["metadata"] = {**(out.get("metadata", {}) or {}),
                           "frozen_elements": sorted(int(i) for i in frozen),
                           "frozen_passthrough": "frozen_face_as_keep_in@1.0"}
    # Expose the reconstructed OCP solid so the layer above can register it as
    # a real CADModel (Document / viewport / history / Design Tree).  It is only
    # present when the B-Rep stage actually completed.
    if final.data is not None and final.stage == ReconstructionStage.BREP_SOLID:
        out["data"] = final.data
    return out
