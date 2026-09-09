r"""Core geometric boundary condition mapping between CAD B-Rep faces and FEM mesh nodes.

CAD-agnostic algorithm mapping topological CAD faces to discretized node indices.
"""

from dataclasses import dataclass
import logging
import re
from typing import Any, Dict, List, Optional

import cadquery as cq
import numpy as np

from core.geometry import _robust_face_reference_point

logger = logging.getLogger(__name__)

# Matches identifiers used by the Core's CADFace.id ("face_0", "face0", "face-3") or a plain index.
_FACE_ID_RE = re.compile(r"^(?:face[_\-\s]?)?(\d+)$", re.IGNORECASE)

#: Unified face-id pattern (superset of the two historical variants):
#: "face_3", "face:3", "face3", "face-3", "face 3" or a plain index.
_FACE_ID_UNIFIED_RE = re.compile(r"^(?:face[_:\-\s]?)?(\d+)$", re.IGNORECASE)


def parse_face_id(face_id) -> Optional[int]:
    """Parse any CAD face identifier to its 0-based B-Rep face index.

    Single source of truth for ``face_<i>`` / ``face:<i>`` / ``<i>`` spellings
    (replaces the two incompatible regexes historically in ``boundary.py``
    and ``topo_problem.py``). Returns ``None`` when not parseable.
    """
    if face_id is None:
        return None
    m = _FACE_ID_UNIFIED_RE.fullmatch(str(face_id).strip())
    return int(m.group(1)) if m else None

#: Pressure units accepted for loads (→ force via Pa × area). Mesh geometry
#: is in millimetres, so areas come in mm² and are converted to m².
PRESSURE_UNITS_SI = {"Pa": 1.0, "kPa": 1e3, "MPa": 1e6}
_MM2_TO_M2 = 1e-6


def is_pressure_unit(unit: Optional[str]) -> bool:
    """Whether a load ``unit`` string denotes pressure (Pa/kPa/MPa)."""
    return str(unit or "").strip() in PRESSURE_UNITS_SI


def surface_area_mm2(nodes: np.ndarray, face_triangles) -> float:
    """Total area (mm²) of a surface triangulation on the FEM mesh."""
    nodes = np.asarray(nodes, dtype=float)
    total = 0.0
    for tri in face_triangles or []:
        tri = [int(t) for t in tri]
        if any(t < 0 or t >= len(nodes) for t in tri):
            continue
        p0, p1, p2 = nodes[tri[0]], nodes[tri[1]], nodes[tri[2]]
        total += 0.5 * float(np.linalg.norm(np.cross(p1 - p0, p2 - p0)))
    return total


def pressure_to_total_force_N(pressure_value: float, unit: str, area_mm2: float) -> float:
    """Convert pressure to total normal force: F[N] = p[Pa] × A[m²].

    Raises ValueError on unknown unit or non-positive area (explicit, never
    a silent Pa-as-N substitution).
    """
    key = str(unit or "").strip()
    if key not in PRESSURE_UNITS_SI:
        raise ValueError(f"Unidad de presión desconocida: {unit!r} (válidas: {sorted(PRESSURE_UNITS_SI)})")
    if not area_mm2 > 0.0:
        raise ValueError(f"Área de superficie no positiva ({area_mm2}); no se puede convertir Pa a N.")
    return float(pressure_value) * PRESSURE_UNITS_SI[key] * float(area_mm2) * _MM2_TO_M2


def resolve_face_index(face_id: Optional[str]) -> Optional[int]:
    """Resolve a CAD face identifier ("face_3", "3", "face0") to its B-Rep face index.
    Args:
        face_id: A face identifier string, e.g. the ``id``/``face_index`` of a
            Core ``CADFace``. ``None`` or non-index identifiers (e.g. "base")
            return ``None``.

    Returns:
        The zero-based face index into ``cq.Shape.Faces()`` if the identifier is
        resolvable, otherwise ``None``.
    """
    if not face_id:
        return None
    return parse_face_id(face_id)


@dataclass
class MappedFace:
    """A CAD face mapped to a set of FEM mesh node indices."""
    face_index: int
    matched_nodes_count: int
    node_indices: List[int]
    center: List[float]
    normal: List[float]
    area: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "face_index": self.face_index,
            "matched_nodes_count": self.matched_nodes_count,
            "node_indices": self.node_indices,
            "center": self.center,
            "normal": self.normal,
            "area": self.area,
        }


class BoundaryConditionMapper:
    """Agnostic boundary condition mapper for mapping CAD faces to finite element nodes."""

    @staticmethod
    def map_faces_to_nodes(
        shape: cq.Shape,
        nodes: List[List[float]],
        face_indices: Optional[List[int]] = None,
        tolerance: float = 0.5,
    ) -> List[MappedFace]:
        """Map specified CAD B-Rep faces to FEM mesh nodes using exact geometric distance."""
        cad_faces = shape.Faces()
        if not face_indices:
            face_indices = list(range(len(cad_faces)))

        mapped_faces: List[MappedFace] = []
        for face_idx in face_indices:
            if face_idx < 0 or face_idx >= len(cad_faces):
                continue
            face = cad_faces[face_idx]
            matching_node_indices: List[int] = []

            for n_idx, node_coord in enumerate(nodes):
                v = cq.Vertex.makeVertex(node_coord[0], node_coord[1], node_coord[2])
                dist = float(face.distance(v))
                if dist <= tolerance:
                    matching_node_indices.append(n_idx)

            center, normal = _robust_face_reference_point(face)
            if center is None or normal is None:
                center = cq.Vector(0.0, 0.0, 0.0)
                normal = cq.Vector(0.0, 0.0, 1.0)

            mapped_faces.append(
                MappedFace(
                    face_index=face_idx,
                    matched_nodes_count=len(matching_node_indices),
                    node_indices=matching_node_indices,
                    center=[float(center.x), float(center.y), float(center.z)],
                    normal=[float(normal.x), float(normal.y), float(normal.z)],
                    area=float(face.Area()),
                )
            )

        return mapped_faces


def nodal_area_weights(    nodes: np.ndarray,
    face_triangles,
    node_indices,
):
    """Tributary-area weights for distributing a total force over mesh nodes
    on a triangulated CAD face.

    Uses the ``lumped mass`` approach: 1/3 of each triangle's area is assigned
    to each of its 3 vertices, then normalised so all weights sum to 1.

    * ``nodes`` — (N, 3) mesh node coordinates.
    * ``face_triangles`` — list of ``[n0, n1, n2]`` (0-based mesh node indices)
      representing the surface triangulation of the face on the FEM mesh.
    * ``node_indices`` — list of 0-based mesh node indices on this face (the
      same nodes the load/support is mapped to).

    Returns ``{node_index: weight}`` where each weight is in ``(0, 1]`` and
    ``sum(weights) == 1``.

    **Fallback:** when ``face_triangles`` is ``None``, empty, or produces zero
    total area (degenerate triangles), returns a uniform distribution
    ``{n: 1/len(node_indices) for n in node_indices}`` — the original
    behaviour — so existing code that lacks surface triangulation is never
    broken.
    """
    nodes = np.asarray(nodes, dtype=float)
    node_indices = list(node_indices)
    if not node_indices:
        return {}

    if not face_triangles:
        n = len(node_indices)
        logger.warning(
            "nodal_area_weights: no surface triangulation for %d nodes -- "
            "falling back to UNIFORM distribution (resultant conserved, "
            "spatial distribution likely inaccurate).", n)
        return {ni: 1.0 / n for ni in node_indices}

    idx_set = set(node_indices)
    area_per_node = {n: 0.0 for n in node_indices}

    for tri in face_triangles:
        tri = [int(t) for t in tri]
        if not any(t in idx_set for t in tri):
            continue
        p0, p1, p2 = nodes[tri[0]], nodes[tri[1]], nodes[tri[2]]
        tri_area = 0.5 * float(np.linalg.norm(np.cross(p1 - p0, p2 - p0)))
        for t in tri:
            if t in idx_set:
                area_per_node[t] += tri_area / 3.0

    total = sum(area_per_node.values())
    if total <= 0.0:
        n = len(node_indices)
        logger.warning(
            "nodal_area_weights: zero total area (degenerate triangles) -- "
            "falling back to UNIFORM distribution.")
        return {ni: 1.0 / n for ni in node_indices}
    return {ni: a / total for ni, a in area_per_node.items()}


def face_triangles_for_indices(
    face_indices,
    face_surface_elements,
    group_index=None,
    node_indices=None,
    allow_boundary_fallback: bool = True,
):
    """Single source of truth for face → surface-triangle lookup (P2/D1).

    Collects ``[n0, n1, n2]`` triangles (0-based mesh node indices) covering
    the given 0-based CAD face indices, trying in order:

    1. named physical groups (via ``group_index``: ``{face_index: [names]}``)
       — exact per-condition submodelparts (productive path);
    2. per-face ``face_<fi>`` keys (deterministic Gmsh path);
    3. node-label propagation from the undifferentiated ``"boundary"`` bucket
       (provisional-mesher leftovers; approximate staircase at ~h/2).

    Step 3 is strictly a LAST RESORT: it only fires when no named group or
    ``face_<fi>`` key matched, requires ``node_indices``, emits an explicit
    ``logger.warning`` (never silent), and is skipped entirely when
    ``allow_boundary_fallback`` is ``False``.

    Returns ``(tris, matched_specific)``. ``matched_specific`` is True only
    when step 1 or 2 matched; the ``"boundary"`` propagation never sets it.
    Empty list when no surface triangulation exists at all (caller decides
    uniform fallback vs error).
    """
    tris = []
    matched_specific = False
    if not face_surface_elements:
        return tris, matched_specific
    group_index = group_index or {}
    for fi in face_indices or []:
        fi = int(fi)
        for grp_name in group_index.get(fi, []):
            tris.extend(face_surface_elements.get(grp_name, []))
            matched_specific = True
        face_key = f"face_{fi}"
        if face_key in face_surface_elements:
            tris.extend(face_surface_elements[face_key])
            matched_specific = True
    if (
        not matched_specific
        and allow_boundary_fallback
        and "boundary" in face_surface_elements
    ):
        node_set = set(node_indices or [])
        if node_set:
            boundary_tris = face_surface_elements["boundary"]
            propagated = [tri for tri in boundary_tris if all(n in node_set for n in tri)]
            if propagated:
                logger.warning(
                    "faces %s: no named group / face_<id> key found; using "
                    "LAST-RESORT 'boundary'-bucket propagation (%d/%d "
                    "triangles, approximate staircase at ~h/2, NOT exact).",
                    list(face_indices or []), len(propagated), len(boundary_tris),
                )
                tris.extend(propagated)
    return tris, matched_specific
