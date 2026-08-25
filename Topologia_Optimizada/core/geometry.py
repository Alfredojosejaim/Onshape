"""Core geometric analysis and manipulation utilities.

Agnostic geometry engine operating on 3D geometric shapes and B-Reps.
Does NOT depend on any specific CAD platform.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import cadquery as cq
import numpy as np

from core.models import BoundingBox3D, CADFace, CADSolid, TessellatedMesh

logger = logging.getLogger(__name__)


class GeometryEngine:
    """Core geometry analysis engine for evaluating B-Rep topology and geometry."""

    @staticmethod
    def calculate_bounding_box(shape: cq.Shape) -> BoundingBox3D:
        """Calculate axis-aligned bounding box from CadQuery/OpenCASCADE Shape."""
        bbox = shape.BoundingBox()
        return BoundingBox3D(
            xmin=float(bbox.xmin),
            xmax=float(bbox.xmax),
            ymin=float(bbox.ymin),
            ymax=float(bbox.ymax),
            zmin=float(bbox.zmin),
            zmax=float(bbox.zmax),
        )

    @staticmethod
    def extract_faces_metadata(shape: cq.Shape) -> List[CADFace]:
        """Extract CADFace domain models with normal, area, and center from a B-Rep Shape."""
        faces = shape.Faces()
        cad_faces: List[CADFace] = []
        for idx, face in enumerate(faces):
            try:
                center = face.Center()
                normal = face.normalAt(center)
                bbox = face.BoundingBox()
                cad_faces.append(
                    CADFace(
                        id=f"face_{idx}",
                        face_index=idx,
                        area=float(face.Area()),
                        center=(float(center.x), float(center.y), float(center.z)),
                        normal=(float(normal.x), float(normal.y), float(normal.z)),
                        bbox=BoundingBox3D(
                            xmin=float(bbox.xmin),
                            xmax=float(bbox.xmax),
                            ymin=float(bbox.ymin),
                            ymax=float(bbox.ymax),
                            zmin=float(bbox.zmin),
                            zmax=float(bbox.zmax),
                        ),
                        surface_type=type(face).__name__,
                    )
                )
            except Exception as ex:
                logger.debug("Failed to extract metadata for face %d: %s", idx, ex)
        return cad_faces

    @staticmethod
    def tessellate_shape(
        shape: cq.Shape,
        linear_deflection: float = 0.1,
        angular_deflection: float = 0.1,
    ) -> TessellatedMesh:
        """Tessellate 3D B-Rep shape into triangular mesh for 3D visualization."""
        points, triangles = shape.tessellate(
            tolerance=linear_deflection,
            angularTolerance=angular_deflection,
        )

        vertices: List[float] = []
        for p in points:
            vertices.extend([float(p.x), float(p.y), float(p.z)])

        indices: List[int] = []
        for tri in triangles:
            indices.extend([int(tri[0]), int(tri[1]), int(tri[2])])

        # Per-face metadata for highlighting and selection
        faces = shape.Faces()
        faces_meta: List[Dict[str, Any]] = []
        for idx, face in enumerate(faces):
            try:
                center = face.Center()
                normal = face.normalAt(center)
                bbox = face.BoundingBox()
                faces_meta.append({
                    "face_index": idx,
                    "id": f"face_{idx}",
                    "area": float(face.Area()),
                    "center": [float(center.x), float(center.y), float(center.z)],
                    "normal": [float(normal.x), float(normal.y), float(normal.z)],
                    "bbox": {
                        "xmin": float(bbox.xmin), "xmax": float(bbox.xmax),
                        "ymin": float(bbox.ymin), "ymax": float(bbox.ymax),
                        "zmin": float(bbox.zmin), "zmax": float(bbox.zmax),
                    }
                })
            except Exception as ex:
                logger.debug("Tessellation face metadata error for face %d: %s", idx, ex)

        bbox = shape.BoundingBox()
        bbox_3d = BoundingBox3D(
            xmin=float(bbox.xmin),
            xmax=float(bbox.xmax),
            ymin=float(bbox.ymin),
            ymax=float(bbox.ymax),
            zmin=float(bbox.zmin),
            zmax=float(bbox.zmax),
        )

        return TessellatedMesh(
            vertices=vertices,
            indices=indices,
            num_vertices=len(points),
            num_triangles=len(triangles),
            faces_metadata=faces_meta,
            bbox=bbox_3d,
        )
