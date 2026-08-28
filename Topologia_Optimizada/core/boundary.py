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
    match = _FACE_ID_RE.fullmatch(str(face_id).strip())
    return int(match.group(1)) if match else None


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
