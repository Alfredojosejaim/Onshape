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
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

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


def _voxel_tet_mesh(lo, hi, resolution):
    """Rejilla de voxels (caja lo..hi) partida en 6 tets cada uno."""
    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    res = max(float(resolution), 1e-6)
    steps = np.maximum(np.ceil((hi - lo) / res).astype(int), 1)
    nx, ny, nz = int(steps[0]), int(steps[1]), int(steps[2])

    def node_index(i, j, k):
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
                elements.append([n[0], n[1], n[4], n[2]])
                elements.append([n[1], n[5], n[4], n[2]])
                elements.append([n[4], n[5], n[6], n[2]])
                elements.append([n[4], n[6], n[7], n[2]])
                elements.append([n[0], n[4], n[3], n[2]])
                elements.append([n[7], n[4], n[3], n[2]])
                voxels.append((i, j, k))
    return pts, np.asarray(elements, dtype=int), voxels


def generate_design_space_mesh(
    model_nodes: np.ndarray,
    resolution: Optional[float] = None,
    padding: Optional[float] = None,
    max_voxels: int = 12000,
) -> BridgeMesh:
    """Envelope de diseño (design space) para escenario A.

    Caja que encierra la malla del modelo + padding, mallada en voxels->6 tets.
    Es el dominio donde el optimizador puede **crecer** material (a diferencia
    de la pieza original, donde solo puede vaciar por dentro) — la diferencia
    entre "esculpir" y diseño generativo orgánico.

    ``resolution`` (tamaño de voxel, mm): por defecto ``max(span)/30``. Si la
    rejilla supera ``max_voxels`` se engrosa automáticamente para acotar el
    costo del solver (el valor efectivo se reporta en ``target_node_sets``).
    """
    nodes = np.asarray(model_nodes, dtype=float)
    lo = nodes.min(axis=0)
    hi = nodes.max(axis=0)
    span = hi - lo
    smax = float(np.max(span)) if span.size else 1.0
    if padding is None:
        padding = 0.10 * smax if smax > 0 else 1.0
    pad = max(float(padding), 0.0)
    lo = lo - pad
    hi = hi + pad
    res = float(resolution) if resolution and float(resolution) > 0 else smax / 30.0
    res = max(res, 1e-6)
    # Acotar el número de voxels (cada uno = 6 tets) para no colgar el solver.
    while True:
        steps = np.maximum(np.ceil((hi - lo) / res).astype(int), 1)
        n_vox = int(steps[0]) * int(steps[1]) * int(steps[2])
        if n_vox <= max_voxels:
            break
        res *= 1.25
    pts, els, vox = _voxel_tet_mesh(lo, hi, res)
    return BridgeMesh(
        nodes=pts, elements=els, voxels=vox,
        target_node_sets={"resolution": [res], "padding": [pad],
                          "voxels": [len(vox)]},
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

    - Explicit ``cond.direction`` (unit, sense already baked by the sender,
      e.g. the parametric web UI) has priority and is used as-is.
    - ``perpendicular``: along the reference plane normal;
    - ``parallel``: any axis orthogonal to the normal (in the plane);
    - ``angle``: the normal rotated by ``angle_deg`` towards the plane.
    ``sense`` applies afterwards, EXCEPT with explicit direction (final).
    """
    _exp = getattr(cond, "direction", None)
    if _exp is not None:
        v = np.asarray(_exp, dtype=float).ravel()
        if v.shape[0] == 3 and np.isfinite(v).all() and float(np.linalg.norm(v)) > 1e-12:
            return v / float(np.linalg.norm(v))
        raise ValueError(f"LoadCondition.direction={_exp!r} inválida (unitaria, finita).")
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
        face_tolerance: float = 0.5,
        surface_matches_mesh: bool = True,
    ) -> None:
        self.model_id = model_id
        self.mesh_nodes = np.asarray(mesh_nodes, dtype=float) if mesh_nodes is not None else None
        self.mesh_elements = (np.asarray(mesh_elements, dtype=int)
                              if mesh_elements is not None else None)
        self.material = material or STANDARD_MATERIALS.get("steel", STANDARD_MATERIALS["steel"])
        self.condition_manager = condition_manager or ConditionManager()
        self.model_shape = model_shape
        self.face_surface_elements = face_surface_elements or {}
        # TOL-MESH-ADAPTIVE (P4/halo, decisión diferida en plan.md): tolerancia
        # cara->nodo de malla. 0.5mm es el default histórico para la malla del
        # modelo; con un design space (envelope) de malla regular se sube a
        # ~1.5·h para que las caras del sólido mapeen a la rejilla.
        self._face_tolerance = float(face_tolerance)
        # SURFACE-MATCH: los face_surface_elements referencian los nodos de la
        # malla del MODELO. Con un envelope (malla distinta) dejan de ser
        # válidos y se cae a distribución uniforme en vez de indexar mal.
        self._surface_matches_mesh = bool(surface_matches_mesh)
        self._face_index_to_groups: Dict[int, List[str]] = {}
        if physical_groups:
            for grp_name, face_indices in physical_groups.items():
                for fi in face_indices:
                    self._face_index_to_groups.setdefault(int(fi), []).append(grp_name)

    def _node_indices_for_load(self, load: LoadCondition) -> List[int]:
        """Map the load's selected faces to mesh node indices."""
        if self.mesh_nodes is None:
            return []
        face_indices = [
            int(e.face_index) for e in load.faces.entities
            if e.entity_type == EntityType.FACE and e.face_index is not None
        ]
        if face_indices:
            # FSE-FIRST: nodos exactos sin necesidad del shape CAD.
            exact = self._fse_nodes_for_faces(face_indices)
            if exact:
                return exact
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
        if not face_indices:
            return []
        return self._select_nodes_for_faces(face_indices)

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
        if not self._surface_matches_mesh:
            # Design space/envelope: los triángulos de superficie referencian
            # los nodos de la malla del modelo, no los del envelope. Devolver
            # [] fuerza distribución uniforme (correcta en índices) en vez de
            # indexar nodos equivocados.
            return []
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

    def _mean_edge_length(self) -> float:
        """Longitud media de arista de los tets (para tolerancia adaptativa)."""
        if self.mesh_nodes is None or self.mesh_elements is None \
                or len(self.mesh_elements) == 0:
            return 1.0
        p = np.asarray(self.mesh_nodes, dtype=float)[np.asarray(self.mesh_elements, dtype=int)]
        edges = [np.linalg.norm(p[:, i] - p[:, j], axis=1)
                 for i in range(4) for j in range(i + 1, 4)]
        h = float(np.mean(np.concatenate(edges))) if edges else 1.0
        return h if np.isfinite(h) and h > 0 else 1.0

    def _map_faces_with_tolerance(self, face_indices: List[int], tol: float) -> List[int]:
        from core.selection import FaceRegion, NodeSelectionEngine
        region = FaceRegion(face_indices=sorted(int(f) for f in face_indices),
                            tolerance=tol)
        return list(NodeSelectionEngine.select_nodes(
            self.mesh_nodes, region.to_dict(),
            cad_shape=self.model_shape, default_tolerance=tol))

    def _fse_nodes_for_faces(self, face_indices: List[int]) -> List[int]:
        """Nodos exactos de la malla para caras CAD (vía face_surface_elements).

        FSE-FIRST: la malla Gmsh trae la triangulación de superficie por cara
        (grupos físicos nombrados + claves deterministas ``face_<i>``) con
        los índices de nodo REALES de esta malla. Es exacta y no depende de
        tolerancias geométricas, así que TODA cara marcada en las
        herramientas mapea a sus nodos verdaderos sin heurísticos.

        Solo válida cuando la malla es la del modelo
        (``_surface_matches_mesh``); con envelope/puente se devuelve [] para
        no indexar nodos de otra malla (ahí rige el fallback declarado).
        """
        if not self._surface_matches_mesh or not self.face_surface_elements:
            return []
        if self.mesh_nodes is None:
            return []
        n = int(np.asarray(self.mesh_nodes).shape[0])
        out: set = set()
        groups = getattr(self, "_face_index_to_groups", None) or {}
        for fi in face_indices or []:
            fi = int(fi)
            for grp in groups.get(fi, []):
                for tri in self.face_surface_elements.get(grp, []):
                    for t in tri:
                        t = int(t)
                        if 0 <= t < n:
                            out.add(t)
            for tri in self.face_surface_elements.get(f"face_{fi}", []):
                for t in tri:
                    t = int(t)
                    if 0 <= t < n:
                        out.add(t)
        return sorted(out)

    def _select_nodes_for_faces(self, face_indices: List[int]) -> List[int]:
        """Mapea caras CAD a nodos con tolerancia adaptativa + reintento.

        Con malla conforme (Gmsh) los nodos están SOBRE la cara y 0.5mm basta.
        Con malla NO conforme (provisional/voxel) los nodos quedan a ~h/2 de la
        cara y 0.5mm mapea 0-1 nodos: la condición se "degradaba" y la
        optimización colapsaba. Aquí, si el mapeo estricto es DISPERSO (menos de
        la mitad de los nodos esperados por área = A/h²), se reintenta con
        `2·h_elemento` y se conserva el que más nodos mapea.

        FSE-FIRST: antes de cualquier tolerancia se prueban los nodos
        exactos de face_surface_elements (misma malla). Si existen, TODA
        cara marcada mapea sin error geométrico.
        """
        if not face_indices:
            return []
        exact = self._fse_nodes_for_faces(face_indices)
        if exact:
            return exact
        if self.model_shape is None:
            return []
        strict = self._map_faces_with_tolerance(face_indices, self._face_tolerance)
        h = self._mean_edge_length()
        try:
            area = sum(float(self.model_shape.Faces()[int(fi)].Area())
                       for fi in face_indices)
        except Exception:  # noqa: BLE001 - defensivo
            area = 0.0
        expected = max(1.0, area / max(h * h, 1e-9))
        if not strict or len(strict) < 0.5 * expected:
            alt = self._map_faces_with_tolerance(
                face_indices, max(self._face_tolerance, 2.0 * h))
            if len(alt) > len(strict):
                return alt
        return strict

    def _resolved_load_nodes(self, load: LoadCondition) -> List[int]:
        """Nodos donde la carga se aplica REALMENTE (mismo fallback que la BC).

        HALO-CONSISTENTE: `_map_conditions_to_problem` cae al extremo del eje
        cuando una cara real no mapea (modo permisivo). El halo debe proteger
        esos mismos nodos, no un conjunto vacío.
        """
        idx = self._node_indices_for_load(load)
        if idx:
            return list(idx)
        nodes = self.mesh_nodes
        vec = direction_vector(load)
        axis = int(np.argmax(np.abs(vec)))
        coord = nodes[:, axis].max() if vec[axis] > 0 else nodes[:, axis].min()
        tol = 1e-3 * float(np.ptp(nodes[:, axis]))
        return [i for i in range(nodes.shape[0])
                if abs(float(nodes[i, axis]) - coord) <= tol]

    def _resolved_support_nodes(self, cond: ElasticityCondition) -> List[int]:
        """Nodos donde la fijación se aplica REALMENTE (mismo fallback base-Z)."""
        face_indices = [
            int(e.face_index) for e in cond.faces.entities
            if e.entity_type == EntityType.FACE and e.face_index is not None
        ]
        target: List[int] = []
        if self.model_shape is not None and face_indices:
            target = self._select_nodes_for_faces(face_indices)
        if not target:
            axis = 2
            coord = float(self.mesh_nodes[:, axis].min())
            target = [i for i in range(self.mesh_nodes.shape[0])
                      if abs(float(self.mesh_nodes[i, axis]) - coord)
                      <= 1e-6 * max(1.0, np.ptp(self.mesh_nodes[:, axis]))]
        return target

    def _load_node_indices(self, conditions: Dict) -> List[int]:
        """Collect all mesh node indices targeted by load conditions.

        Usa la resolución REAL (con fallback) para que el halo de preservación
        coincida exactamente con dónde se aplica la carga.
        """
        nodes: set = set()
        for load in conditions.get(ConditionType.LOAD, []):
            if isinstance(load, LoadCondition):
                nodes |= set(self._resolved_load_nodes(load))
        return sorted(nodes)

    def _support_node_indices(self, conditions: Dict) -> List[int]:
        """Collect all mesh node indices targeted by elasticity (support) conditions.

        Usa la resolución REAL (con fallback base-Z) para que el halo de
        preservación coincida exactamente con dónde se fija la pieza.
        """
        nodes: set = set()
        for cond in conditions.get(ConditionType.ELASTICITY, []):
            if isinstance(cond, ElasticityCondition):
                nodes |= set(self._resolved_support_nodes(cond))
        return sorted(nodes)

    def _protected_elements(self, conditions: List[ProtectedRegion],
                             ) -> Tuple[np.ndarray, bool]:
        """Element indices that must keep material (protected regions).

        Returns ``(elements, used_bbox_fallback)``. ``used_bbox_fallback`` is
        True when at least one face was selected but NONE resolved to mesh
        nodes within tolerance (i.e. the geometric heuristic below was used
        instead of the actual selected faces) -- the caller must surface this
        as an unsupported/degraded condition, never silently.
        """
        if self.mesh_elements is None:
            return np.array([], dtype=int), False
        if not conditions:
            return np.array([], dtype=int), False
        node_set: set = set()
        face_one = set()
        for region in conditions:
            for e in region.faces.entities:
                if e.entity_type == EntityType.FACE and e.face_index is not None:
                    face_one.add(int(e.face_index))
        if self.model_shape is not None and face_one:
            node_set |= set(self._select_nodes_for_faces(sorted(face_one)))
        # Fallback: protect elements touching the model bounding box ends.
        # Explicit heuristic (not a CAD-face mapping): only applies when no
        # protected-region face resolved to nodes.
        used_fallback = False
        if not node_set and self.mesh_nodes is not None:
            used_fallback = bool(face_one)
            logger.warning(
                "ProtectedRegion: no face mapped to mesh nodes (caras=%s, "
                "tolerance=0.5mm); protecting bbox-end elements explicitly "
                "(heuristic fallback, NOT the CAD faces the user selected). "
                "Likely cause: mesh element size too coarse relative to the "
                "0.5mm tolerance on a curved/small face.", sorted(face_one))
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
        return np.array(sorted(elems), dtype=int), used_fallback

    def _void_elements(self, conditions: List[ObstructionCondition]) -> np.ndarray:
        """Element indices that must stay empty (obstructions).

        Body-based obstructions are mapped to mesh elements through the CAD
        shape: for each obstructing solid body we collect the elements whose
        centroid lies inside the solid (optionally expanded by ``offset_mm``).
        Face-based obstructions (keep-out por caras de la UI) se mapean a los
        elementos que tocan los nodos de esas caras (misma tolerancia
        adaptativa que la región protegida) y se unen al conjunto void.
        Without a CAD shape no reliable mapping can be computed, so an empty
        set is returned and the condition is explicitly flagged as
        *unsupported* by the caller (never a silent wrong result).
        """
        if self.mesh_elements is None or self.mesh_nodes is None or not conditions:
            return np.array([], dtype=int)
        face_elems: set = set()
        for cond in conditions:
            face_indices = [
                int(e.face_index) for e in cond.faces.entities
                if e.entity_type == EntityType.FACE and e.face_index is not None
            ]
            if face_indices and self.model_shape is not None:
                nodes = set(self._select_nodes_for_faces(face_indices))
                if nodes:
                    for e in range(self.mesh_elements.shape[0]):
                        if set(self.mesh_elements[e].tolist()) & nodes:
                            face_elems.add(int(e))
                else:
                    logger.warning(
                        "Obstruction: caras %s no mapearon a nodos de malla; "
                        "esas caras keep-out no generan vacío.", face_indices)
        if self.model_shape is None:
            logger.warning(
                "Obstruction mapping requires the CAD shape; marking as unsupported.")
            return np.asarray(sorted(face_elems), dtype=int)

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
        body_void = set(int(i) for i in np.nonzero(inside)[0].tolist())
        return np.asarray(sorted(body_void | face_elems), dtype=int)

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
        fallback_flag = None
        if not idx and load.faces.entities:
            # Cara real seleccionada sin nodos (tolerance 0.5mm): en modo
            # permisivo se aplica el fallback de extremo del eje pero se
            # marca explícito (misma familia que elasticity(fallback_base_Z)).
            logger.warning(
                "LoadCondition %s: caras %s no mapearon a ningun nodo de "
                "malla (tolerance=0.5mm); usando fallback de extremo del eje "
                "en su lugar. La carga real seleccionada por el usuario NO "
                "fue aplicada donde corresponde.",
                getattr(load, "name", "?"),
                [int(e.face_index) for e in load.faces.entities
                 if e.face_index is not None])
            fallback_flag = "load(fallback_bbox)"
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
        return single, idx, fallback_flag

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
                # Flags duros ("load", presión sin área) descartan el caso;
                # los de fallback ("load(fallback_bbox)") conservan el caso
                # aplicado (modo permisivo) pero quedan registrados.
                if "fallback" not in uns:
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
                region = FaceRegion(face_indices=face_indices, tolerance=self._face_tolerance)
                target_nodes = NodeSelectionEngine.select_nodes(
                    nodes, region.to_dict(), cad_shape=self.model_shape,
                    default_tolerance=self._face_tolerance,
                )
            if not target_nodes and face_indices and raise_on_unmapped_face:
                unsupported.append("elasticity")
                continue
            if not target_nodes and face_indices:
                # A real face WAS selected but mapped to zero mesh nodes
                # (likely: 0.5mm tolerance too tight for the mesh element
                # size on this face). Never substitute the base of the part
                # in silence -- flag it explicitly so the UI/study result
                # shows it, even though we still proceed with the fallback
                # below in permissive SIMP mode.
                logger.warning(
                    "ElasticityCondition: caras %s no mapearon a ningun nodo "
                    "de malla (tolerance=0.5mm); usando fallback de base del "
                    "eje Z en su lugar. La fijacion real seleccionada por el "
                    "usuario NO fue aplicada.", face_indices)
                unsupported.append("elasticity(fallback_base_Z)")
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

        preserved, preserved_fallback = self._protected_elements(
            conditions.get(ConditionType.PROTECTED_REGION, []))
        if preserved_fallback:
            unsupported.append("protected_region(fallback_bbox)")
        obstructions = conditions.get(ConditionType.OBSTRUCTION, [])
        void = self._void_elements(obstructions)

        if obstructions and void.size == 0:
            unsupported.append("obstruction")

        return forces, fixed_dofs, preserved, void, sorted(set(unsupported))

    def _condition_mapping_report(self, conditions) -> List[Dict[str, Any]]:
        """Por condición: caras pedidas vs nodos/elementos mapeados reales."""
        report: List[Dict[str, Any]] = []

        def _face_ids(selection) -> List[int]:
            return [int(e.face_index) for e in selection.entities
                    if e.entity_type == EntityType.FACE
                    and e.face_index is not None]

        def _touching_elements(node_ids) -> int:
            ns = set(int(i) for i in node_ids)
            if not ns or self.mesh_elements is None:
                return 0
            return sum(1 for e in range(self.mesh_elements.shape[0])
                       if ns.intersection(self.mesh_elements[e].tolist()))

        for load in conditions.get(ConditionType.LOAD, []):
            if not isinstance(load, LoadCondition):
                continue
            fi = _face_ids(load.faces)
            idx = self._node_indices_for_load(load)
            report.append({"id": load.id, "name": getattr(load, "name", "?"),
                           "type": "load", "faces": fi,
                           "mapped_nodes": len(idx),
                           "fallback": bool(fi) and not idx})
        for cond in conditions.get(ConditionType.ELASTICITY, []):
            if not isinstance(cond, ElasticityCondition):
                continue
            fi = _face_ids(cond.faces)
            idx = self._select_nodes_for_faces(fi) if fi else []
            report.append({"id": cond.id, "name": getattr(cond, "name", "?"),
                           "type": "elasticity", "faces": fi,
                           "mapped_nodes": len(idx),
                           "fallback": bool(fi) and not idx})
        for region in conditions.get(ConditionType.PROTECTED_REGION, []):
            fi = _face_ids(region.faces)
            els, fb = self._protected_elements([region])
            report.append({"id": region.id,
                           "name": getattr(region, "name", "?"),
                           "type": "protected_region", "faces": fi,
                           "mapped_nodes": 0, "mapped_elements": int(len(els)),
                           "fallback": bool(fb)})
        for cond in conditions.get(ConditionType.OBSTRUCTION, []):
            sel = getattr(cond, "faces", None)
            fi = _face_ids(sel) if sel is not None else []
            nb = sum(1 for b in cond.bodies.entities
                     if b.entity_type == EntityType.SOLID)
            els = self._void_elements([cond])
            report.append({"id": cond.id, "name": getattr(cond, "name", "?"),
                           "type": "obstruction", "faces": fi,
                           "bodies": int(nb),
                           "mapped_elements": int(len(els)),
                           "fallback": bool(fi or nb) and not len(els)})
        return report

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
        # ENV-SKIN: capa de vacío en el borde del dominio de diseño. Sin ella
        # el material del envelope crece HASTA la pared de la caja, el
        # isosuperficie queda ABIERTO y la reconstrucción B-Rep falla
        # ("isosuperficie abierta/degenerada"). Forzar el borde a vacío
        # garantiza una superficie cerrada. La calcula run_generative_design
        # para el envelope; con 'part' no interviene.
        _skin = kwargs.get("void_skin")
        if _skin is not None:
            _s = np.asarray(_skin, dtype=int).ravel()
            if _s.size:
                void = np.union1d(np.asarray(void, dtype=int), _s)
        # MULTICARGA: casos separados (misma fisica que el vector sumado).
        cases, weights, unsupported_cases = \
            self._map_conditions_to_load_cases(conditions, raise_on_unmapped_face=False)
        for u in unsupported_cases:
            if u not in unsupported:
                unsupported.append(u)
        # GEN-LEGACY (reversible): si no llego ninguna condicion de carga/soporte
        # (p. ej. la UI solo mando las BC legacy por setBoundaries), usar esas
        # BC en vez de resolver con carga cero (que producia un no-op silencioso:
        # el job terminaba "bien" pero sin cambiar nada). Mismo contrato que
        # controller.run_optimization en su rama legacy. Para volver atras:
        # quitar legacy_force/legacy_fixed_dofs y volver al vector nulo.
        legacy_force = kwargs.get("legacy_force")
        legacy_fixed = kwargs.get("legacy_fixed_dofs")
        if legacy_force is not None and not any(
                float(np.linalg.norm(np.asarray(c, dtype=float))) > 0.0 for c in cases):
            cases, weights = [np.asarray(legacy_force, dtype=float)], [1.0]
        if legacy_fixed is not None and not fixed_dofs:
            fixed_dofs = [int(d) for d in np.asarray(legacy_fixed, dtype=int).ravel()]
        if not cases:
            # Sin casos (p.ej. todo unsupported en modo permisivo): vector nulo
            # único para no romper el contrato del solver.
            cases, weights = [forces], [1.0]
        # Fase 6d: acoplamiento térmico one-way (misma actuación simultánea:
        # el vector térmico se suma a cada caso mecánico).
        if kwargs.get("thermal_temperatures") is not None:
            from core.thermal import ThermalError, thermal_load_vector

            _alpha = kwargs.get("thermal_alpha", None)
            if _alpha is None:
                _alpha = getattr(self.material, "thermal_expansion", None)
            if _alpha is None:
                raise ValueError(
                    "Acoplamiento térmico sin α: pase thermal_alpha o asigne "
                    "thermal_expansion al material.")
            try:
                _fth = thermal_load_vector(
                    np.asarray(nodes, dtype=float),
                    np.asarray(elements, dtype=int),
                    self.material.young_modulus, self.material.poisson_ratio,
                    float(_alpha),
                    np.asarray(kwargs.get("thermal_temperatures"), dtype=float),
                    reference_temperature=float(
                        kwargs.get("thermal_reference_temperature", 293.15)))
            except ThermalError as exc:
                raise ValueError(f"Carga térmica inválida: {exc}")
            cases = [np.asarray(c, dtype=float) + _fth for c in cases]

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
        if kwargs.get("symmetry_planes") is not None:
            solver.set_symmetry_planes(kwargs.get("symmetry_planes"))
        if preserved.size:
            solver.set_preserved_elements(preserved)
        if void.size:
            solver.set_void_elements(void)
        # Proyección Heaviside + extrusión 2D (opt-in, fail-loud en el setter).
        if kwargs.get("heaviside_projection"):
            solver.set_heaviside_projection(
                beta=kwargs.get("heaviside_beta", 1.0),
                eta=kwargs.get("heaviside_eta", 0.5),
                continuation=kwargs.get("heaviside_continuation", False),
            )
        if kwargs.get("extrusion_axis") is not None:
            solver.set_extrusion_filter(kwargs.get("extrusion_axis"))

        # Halo alrededor de nodos de carga/soporte (Punto 1 auditoría
        # prompt.md): las cargas/fijaciones solo generaban forces/fixed_dofs,
        # sin preservación geométrica, así que el optimizador vaciaba justo
        # la zona de aplicación. El halo une esos elementos a `preserved`
        # (rho=1, no optimizables).
        # Convención: ausente o <= 0 = AUTO topológico (una capa: elementos
        # que tocan un nodo BC; independiente del tamaño de malla y nunca
        # más grueso de lo necesario para materializar la zona), > 0 =
        # manual geométrico (radio en unidades de malla, vía
        # protect_elements_near_nodes), None explícito = opt-out.
        # (El auto geométrico 2x h_element se descartó: con caras grandes
        # preservaba la pieza entera —cono 1012/1047— y el SIMP no tenía
        # dominio que optimizar: densidades ~1, sin isosuperficie, B-Rep
        # fallido y volumen sin reducir.)
        _halo_sentinel = object()
        halo_radius = kwargs.get("halo_radius", _halo_sentinel)
        if halo_radius is _halo_sentinel:
            halo_radius = 0.0
        halo_nodes: List[int] = []
        halo_skipped: Optional[str] = None
        halo_mode: Optional[str] = None
        if halo_radius is not None:
            halo_nodes = sorted(set(self._load_node_indices(conditions))
                                | set(self._support_node_indices(conditions)))
            if halo_nodes:
                import numpy as _np
                _pre = (None if solver._preserved is None
                        else _np.asarray(solver._preserved).copy())
                if float(halo_radius) <= 0:
                    halo_mode = "topological_1layer"
                    _hn = set(int(i) for i in halo_nodes)
                    _layer = np.array([
                        e for e in range(self.mesh_elements.shape[0])
                        if _hn.intersection(self.mesh_elements[e].tolist())
                    ], dtype=int)
                    _union = (np.union1d(
                        _layer, np.nonzero(_pre)[0])
                        if _pre is not None else _layer)
                    solver.set_preserved_elements(_union)
                else:
                    halo_mode = "geometric_radius"
                    solver.protect_elements_near_nodes(
                        halo_nodes, radius=float(halo_radius))
                if not bool(_np.asarray(solver._active).any()):
                    # Guarda degenerate: el halo cubriría TODA la malla
                    # dejando dominio activo vacío y volfrac final 0.0.
                    # Se revierte al preserved previo y se declara explícito.
                    solver._preserved = _pre
                    solver._finalize_active()
                    halo_skipped = "full_coverage"

        progress_cb = kwargs.get("progress_cb")
        result = solver.optimize(
            max_iterations=kwargs.get("max_iterations", 30),
            tolerance=kwargs.get("tolerance", 1e-3),
            callback=progress_cb,
            optimizer=kwargs.get("optimizer", "oc"),
            eso_criterion=kwargs.get("eso_criterion", "compliance"),
            evolutionary_rate=kwargs.get("evolutionary_rate", 0.02),
            ls_cfl=kwargs.get("ls_cfl", 0.5),
            ls_hole_period=kwargs.get("ls_hole_period", 3),
            min_thickness=kwargs.get("min_thickness", None),
            overhang_constraint=kwargs.get("overhang_constraint", False),
            build_direction=kwargs.get("build_direction", (0.0, 0.0, 1.0)),
            overhang_angle_deg=kwargs.get("overhang_angle_deg", 45.0),
            overhang_penalty=kwargs.get("overhang_penalty", 0.5),
            objective=kwargs.get("objective", "min_compliance"),
            compliance_limit=kwargs.get("compliance_limit", None),
        )
        result["_consumed_load_conditions"] = len(conditions.get(ConditionType.LOAD, []))
        result["_consumed_elasticity_conditions"] = len(conditions.get(ConditionType.ELASTICITY, []))
        result["_consumed_protected_conditions"] = len(conditions.get(ConditionType.PROTECTED_REGION, []))
        result["_consumed_obstruction_conditions"] = len(conditions.get(ConditionType.OBSTRUCTION, []))
        result["_unsupported_conditions"] = sorted(unsupported)
        # MAP-REPORT (diagnóstico fail-loud): por cada condición, caras
        # pedidas vs nodos/elementos mapeados REALMENTE. Si una cara mapea
        # 0 nodos, el solver usó un fallback (ver _unsupported_conditions)
        # y la zona preservada/vaciada NO es la seleccionada: esto explica
        # un resultado "al revés". La UI lo muestra junto al aviso.
        try:
            result["_condition_mapping"] = self._condition_mapping_report(conditions)
        except Exception:  # noqa: BLE001 - diagnóstico, nunca rompe el solve
            result["_condition_mapping"] = []
        # Snapshot real de preserved DESPUÉS del halo (el solver une el
        # halo con lo previo; reportar `preserved` pre-halo ocultaría la
        # preservación de cargas/soportes en la reconstrucción).
        _solver_preserved = getattr(solver, "_preserved", None)
        if _solver_preserved is not None and np.asarray(_solver_preserved).any():
            _final_preserved = np.nonzero(np.asarray(_solver_preserved))[0]
        else:
            _final_preserved = np.asarray(preserved, dtype=int).ravel()
        result["_preserved_elements"] = [int(i) for i in _final_preserved.tolist()]
        result["_halo_nodes"] = [int(i) for i in halo_nodes]
        result["_halo_radius"] = (None if halo_radius is None
                                  else float(halo_radius))
        if halo_mode is not None:
            result["_halo_mode"] = halo_mode
        if halo_skipped is not None:
            result["_halo_skipped"] = halo_skipped
        result["_frozen_elements"] = []
        return result


def run_generative_design(
    study: GenerativeDesignStudy,
    condition_manager: ConditionManager,
    engine: GenerativeDesignEngine,
    progress_cb: Optional[Callable[[dict], None]] = None,
    step_path: Optional[str] = None,
    legacy_force: Optional[np.ndarray] = None,
    legacy_fixed_dofs: Optional[np.ndarray] = None,
    halo_radius: Optional[float] = 0.0,
    heaviside_projection: bool = False,
    heaviside_beta: float = 1.0,
    heaviside_eta: float = 0.5,
    heaviside_continuation: bool = False,
    extrusion_axis=None,
    smoothing_method: str = "laplacian",
    brep_style: str = "faceted",
    design_space: str = "part",
    design_space_resolution: Optional[float] = None,
    design_space_padding: Optional[float] = None,
    max_hole_edges: Optional[Union[int, str]] = None,
) -> Dict[str, Any]:
    """High-level entry: run the generative design pipeline (A or B).

    ``design_space``: "part" (default, histórico: se optimiza la pieza
    importada, solo se puede vaciar) o "box"/"envelope" (se malla una caja
    que encierra la pieza y el optimizador puede CRECER una estructura
    orgánica). Con envelope, la tolerancia cara->nodo se vuelve adaptativa
    (~1.5·h) y los triángulos de superficie del modelo se desactivan.

    Returns a dict with the SIMP result plus the B-Rep reconstruction.
    ``legacy_force``/``legacy_fixed_dofs`` (GEN-LEGACY) permiten correr sin
    condiciones reutilizables usando las BC clásicas del controller.
    ``halo_radius``: 0.0/auto topológico (defecto, una capa de elementos
    que tocan nodos de carga/soporte), > 0 manual geométrico (radio en
    unidades de malla), None desactiva la preservación (opt-out).
    ``max_hole_edges``: tope de aristas por loop abierto para
    ``fill_holes()`` en la reconstrucción B-Rep. ``None`` (default,
    histórico) tapa todos los loops -- incluye agujeros de diseño
    intencionales (anclajes, keep-out) junto con el ruido del marching-tets.
    Un entero >= 3 tapa solo loops con esa cantidad de aristas o menos.
    ``"auto"`` deriva el tope de la mediana de loops de la malla resultante
    (ver ``MeshHoleFiller.AUTO_FACTOR``); no es el default todavía porque no
    tiene backfill test contra una pieza real con agujero de anclaje (Fase
    4.5c). Lo no tapado queda explícito en ``reconstruction.metadata``
    (``holes_skipped``, ``max_hole_edges_resolved``).
    """
    conditions = consume_conditions(condition_manager, study.conditions)

    # GEN-NOCOND (reversible): fail-loud en vez de no-op silencioso. Si no hay
    # condiciones reutilizables NI BC legacy, el solver correria con carga cero
    # y devolveria un resultado vacio que la UI mostraba como "no hizo nada".
    # Para volver atras: quitar este bloque.
    has_reusable = any(conditions.get(t) for t in
                       (ConditionType.LOAD, ConditionType.ELASTICITY))
    if not has_reusable and legacy_force is None:
        raise ValueError(
            "Diseño generativo sin condiciones: no hay cargas ni fijaciones "
            "reutilizables (condition_ids) ni BC clásicas. Cargá/sincronizá las "
            "condiciones del estudio antes de ejecutar (fail-loud, sin no-op)."
        )

    # Pass the study's optimisation parameters into the SIMP solve so the
    # user-configured settings (volume fraction, iterations, penalization,
    # filter radius, tolerance) are honoured instead of fixed defaults.
    p = study.optimization_params
    _opt = str(getattr(getattr(p, "optimizer", None), "value", "simp")).lower()
    # Mapeo honesto OptimizerType -> solver (Fase 6a/6f/6): sin coerción
    # silenciosa; GCMMA implementado en core (Fase 6).
    _opt_map = {"simp": "oc", "oc": "oc", "mma": "mma", "gcmma": "gcmma",
                "eso": "eso", "level_set": "level_set"}
    if _opt not in _opt_map:
        raise ValueError(
            f"optimizer={_opt!r} sin motor implementado (usar 'simp', 'mma', 'gcmma', 'eso' o 'level_set')."
        )
    solve_kwargs = dict(
        volume_fraction=p.volume_fraction,
        max_iterations=p.max_iterations,
        penalization=p.penalization,
        filter_radius=p.filter_radius,
        tolerance=p.convergence_tolerance,
        progress_cb=progress_cb,
        halo_radius=halo_radius,  # 0.0 = auto desde la malla (Punto 1); None = opt-out
        optimizer=_opt_map[_opt],
        legacy_force=legacy_force,
        legacy_fixed_dofs=legacy_fixed_dofs,
        heaviside_projection=heaviside_projection,
        heaviside_beta=heaviside_beta,
        heaviside_eta=heaviside_eta,
        heaviside_continuation=heaviside_continuation,
        extrusion_axis=extrusion_axis,
    )

    if study.scenario == "A":
        env_meta = None
        if design_space in ("box", "envelope"):
            model_nodes = engine.mesh_nodes
            if model_nodes is None:
                raise ValueError("design_space='box' requiere la malla del modelo.")
            res = design_space_resolution
            if res is None:
                ds = getattr(study, "design_space", None)
                ds_res = getattr(ds, "resolution", None) if ds is not None else None
                # 1.0 es el default de DesignSpace (demasiado fino para una
                # pieza real): sólo se honra si el usuario lo subió.
                res = float(ds_res) if ds_res and float(ds_res) > 1.0 else None
            env = generate_design_space_mesh(
                model_nodes, resolution=res, padding=design_space_padding)
            eff_res = float(env.target_node_sets["resolution"][0])
            engine.mesh_nodes = env.nodes
            engine.mesh_elements = env.elements
            # Los triángulos de superficie del modelo NO pertenecen a esta malla
            # y la tolerancia debe ser mesh-adaptativa para mapear las caras.
            engine._surface_matches_mesh = False
            engine._face_tolerance = 1.5 * eff_res
            # ENV-SKIN: elementos que tocan la pared de la caja de diseño se
            # fuerzan a vacío (una capa) para que el isosuperficie cierre.
            _en = np.asarray(env.nodes, dtype=float)
            _lo = _en.min(axis=0)
            _hi = _en.max(axis=0)
            _skin_tol = float(eff_res)
            _cent = np.asarray(
                [_en[el].mean(axis=0) for el in np.asarray(env.elements, dtype=int)],
                dtype=float)
            _skin_mask = np.any(
                (_cent <= (_lo + _skin_tol)) | (_cent >= (_hi - _skin_tol)), axis=1)
            # ENV-SKIN-BC-GUARD: si una cara de carga/fijación del modelo
            # queda cerca de la pared de la caja (padding chico), el skin
            # geométrico la vaciaba (rho ~= rho_min) sin distinguir su rol.
            # Con penalización SIMP, la rigidez local cae a ~rho_min**p y la
            # carga/fijación queda apoyada en material casi inexistente:
            # el sistema K_ff·u=F puede quedar mal condicionado o singular
            # y `apply_bc_and_solve` (core/fea.py) no tiene try/except propio,
            # así que la excepción de scipy sube como error genérico del job
            # (ver sesion-2026-09-16-generativa-envelope-bspline-error.md).
            # Fix: los elementos que tocan un nodo de carga o soporte NUNCA
            # entran al skin, aunque toquen la pared del envelope (mismo
            # criterio que ya usa el halo topológico con `preserved`).
            _bc_nodes = set(engine._load_node_indices(conditions)) | \
                set(engine._support_node_indices(conditions))
            _bc_element_mask = np.zeros(env.elements.shape[0], dtype=bool)
            if _bc_nodes:
                _elems_arr = np.asarray(env.elements, dtype=int)
                _bc_element_mask = np.array(
                    [bool(_bc_nodes.intersection(e.tolist())) for e in _elems_arr],
                    dtype=bool)
                _skin_mask = _skin_mask & ~_bc_element_mask
            _skin = np.nonzero(_skin_mask)[0]
            solve_kwargs["void_skin"] = _skin
            # ORGANIC-FILTER: el filtro debe cubrir ~1.5 voxels para ramificar
            # suave (hueso) en vez de fragmentar en checkerboard. Si el usuario
            # pidió menos, se sube al mínimo y se declara en el meta.
            req_filter = float(solve_kwargs.get("filter_radius", 1.5) or 1.5)
            auto_filter = max(req_filter, 1.5 * eff_res)
            solve_kwargs["filter_radius"] = auto_filter
            env_meta = {
                "design_space": "envelope",
                "resolution": eff_res,
                "voxels": int(env.target_node_sets["voxels"][0]),
                "num_elements": int(env.elements.shape[0]),
                "filter_radius": auto_filter,
                "filter_auto": bool(auto_filter > req_filter),
                "filter_requested": req_filter,
                "void_skin_elements": int(_skin.size),
                "void_skin_bc_excluded": int(_bc_element_mask.sum()),
            }
        elif design_space != "part":
            raise ValueError(
                f"design_space={design_space!r} no soportado (usar 'part' o 'box').")
        result = engine.solve_simp(conditions, **solve_kwargs)
        if env_meta is not None:
            result["_design_space"] = env_meta
    elif study.scenario == "B":
        # GEN-B (reversible): el escenario B genera el espacio de diseño entre
        # las piezas objetivo; la malla base del modelo NO es la malla puente.
        # Antes se comprobaba `engine.mesh_nodes is None` (siempre False porque
        # el controller inyecta la malla), así que la puente nunca se construía
        # y B optimizaba la pieza A en silencio. Para volver atras: restaurar
        # el `if engine.mesh_nodes is None`.
        model_nodes = engine.mesh_nodes
        bridge = generate_bridge_mesh(
            study.connection_targets,
            resolution=study.design_space.resolution,
            model_nodes=model_nodes,
        )
        engine.mesh_nodes = bridge.nodes
        engine.mesh_elements = bridge.elements
        # GEN-B-MAP: la triangulación de superficie original referencia la
        # malla del modelo, no la puente. Se invalida explícitamente para no
        # indexar nodos/triángulos de otra malla (cae a fallback uniforme, que
        # es correcto en índices). Además se ancla cada target a los nodos
        # puente de sus extremos para un mapeo determinista.
        engine._surface_matches_mesh = False
        try:
            engine._face_tolerance = 1.5 * float(engine._mean_edge_length())
        except Exception:  # noqa: BLE001 - defensivo
            pass
        try:
            bnodes = np.asarray(bridge.nodes, dtype=float)
            span = bnodes.max(axis=0) - bnodes.min(axis=0)
            axis = int(np.argmax(span))
            lo_c = float(bnodes[:, axis].min())
            hi_c = float(bnodes[:, axis].max())
            tol = 1e-3 * max(float(np.ptp(bnodes[:, axis])), 1e-9)
            lo_set = [i for i in range(bnodes.shape[0])
                      if abs(float(bnodes[i, axis]) - lo_c) <= tol]
            hi_set = [i for i in range(bnodes.shape[0])
                      if abs(float(bnodes[i, axis]) - hi_c) <= tol]
            bridge.target_node_sets = {
                f"target_{i}": (lo_set if i == 0 else hi_set if i == len(study.connection_targets) - 1 else hi_set)
                for i in range(len(study.connection_targets))
            }
        except Exception:  # noqa: BLE001 - defensivo
            bridge.target_node_sets = {}
        result = engine.solve_simp(conditions, **solve_kwargs)
        try:
            result["_bridge"] = {
                "num_nodes": int(np.asarray(bridge.nodes).shape[0]),
                "num_elements": int(np.asarray(bridge.elements).shape[0]),
                "surface_matches_mesh": False,
                "target_node_sets": {k: len(v) for k, v in bridge.target_node_sets.items()},
            }
        except Exception:  # noqa: BLE001 - defensivo
            pass
    else:  # pragma: no cover
        raise ValueError(f"Unsupported scenario '{study.scenario}'")

    reconstruction = _reconstruct(
        result, engine, step_path=step_path,
        smoothing_method=smoothing_method, brep_style=brep_style,
        max_hole_edges=max_hole_edges)
    result["reconstruction"] = reconstruction
    return result


def _reconstruct(
    result: Dict[str, Any],
    engine: GenerativeDesignEngine,
    step_path: Optional[str] = None,
    frozen_elements: Optional[List[int]] = None,
    preserved_elements: Optional[List[int]] = None,
    smoothing_method: str = "laplacian",
    brep_style: str = "faceted",
    max_brep_triangles: Optional[int] = 6000,
    max_hole_edges: Optional[Union[int, str]] = None,
):
    from core.cad_reconstruction import (
        ReconstructionPipeline,
        ReconstructionStage,
        ReconstructionStatus,
        MarchingTetrahedraExtractor,
    )
    densities = np.asarray(result.get("densities", []), dtype=float)
    frozen = list(frozen_elements) if frozen_elements is not None else list(
        result.get("_frozen_elements", []) or [])
    preserved = (list(preserved_elements) if preserved_elements is not None
                 else list(result.get("_preserved_elements", []) or []))
    fitter = None
    if brep_style == "bspline":
        from core.cad_reconstruction import OCPBSplineFitter
        fitter = OCPBSplineFitter(step_path=step_path)
    elif brep_style != "faceted":
        raise ValueError(
            f"brep_style={brep_style!r} no soportado (usar 'faceted' o 'bspline').")
    pipe = ReconstructionPipeline(
        surface_extractor=MarchingTetrahedraExtractor(),
        brep_fitter=fitter,
        step_path=step_path,
        smoothing_method=smoothing_method,
        max_brep_triangles=max_brep_triangles,
        max_hole_edges=max_hole_edges,
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
    # Motivo explícito cuando no se llegó a sólido: el dict final solo trae
    # la mejor etapa disponible (stage/status/error_message); el error de la
    # etapa BREP se perdería y la UI diría "sin detalle". Se expone aparte.
    if final.stage != ReconstructionStage.BREP_SOLID:
        brep_res = pipe._stages.get(ReconstructionStage.BREP_SOLID)
        if brep_res is not None and brep_res.error_message:
            out["brep_error"] = brep_res.error_message
        elif final.error_message:
            out["brep_error"] = final.error_message
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
