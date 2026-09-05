"""Core geometric analysis and manipulation utilities.

Agnostic geometry engine operating on 3D geometric shapes and B-Reps.
Does NOT depend on any specific CAD platform.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import cadquery as cq
import numpy as np

from core.models import BoundingBox3D, CADFace, TessellatedMesh

logger = logging.getLogger(__name__)


def _robust_face_reference_point(face: cq.Face) -> Tuple[Optional[cq.Vector], Optional[cq.Vector]]:
    """Return a reference point on the face and an outward-ish normal.

    The primary path uses the OCC face center + ``normalAt``. Some surfaces
    (e.g. conical/cylindrical faces whose geometric center lies on the axis,
    outside the surface) make the projection degenerate and raise
    ``StdFail_NotDone``. In that case the point and normal are derived from a
    tessellation of the face so that no real B-Rep face is silently dropped.

    Returns:
        Tuple of (point_on_face, normal) as ``cq.Vector``, or ``(None, None)``
        if the face cannot be evaluated at all.
    """
    try:
        center = face.Center()
        normal = face.normalAt(center)
        return center, normal
    except Exception:
        pass

    try:
        points, triangles = face.tessellate(tolerance=0.1, angularTolerance=0.1)
    except Exception as ex:
        logger.debug("Face tessellation failed for reference point: %s", ex)
        return None, None

    if not triangles:
        return None, None

    for tri in triangles:
        p0, p1, p2 = points[tri[0]], points[tri[1]], points[tri[2]]
        u = p1 - p0
        v = p2 - p0
        n = u.cross(v)
        ln = n.Length
        if ln > 1e-12:
            n = n.multiply(1.0 / ln)
            center = cq.Vector(
                (p0.x + p1.x + p2.x) / 3.0,
                (p0.y + p1.y + p2.y) / 3.0,
                (p0.z + p1.z + p2.z) / 3.0,
            )
            return center, n

    return None, None


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
                center, normal = _robust_face_reference_point(face)
                bbox = face.BoundingBox()
                if center is None or normal is None:
                    logger.debug("Failed to extract a reference point for face %d", idx)
                    continue
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
    def _faces_metadata(faces: Any) -> List[Dict[str, Any]]:
        """Per-face metadata (index/id/area/center/normal/bbox) for highlighting."""
        faces_meta: List[Dict[str, Any]] = []
        for idx, face in enumerate(faces):
            try:
                center, normal = _robust_face_reference_point(face)
                bbox = face.BoundingBox()
                if center is None or normal is None:
                    logger.debug("Tessellation face metadata error for face %d (no reference point)", idx)
                    continue
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
        return faces_meta

    @staticmethod
    def _relative_deflection(shape: cq.Shape,
                             linear_deflection: Optional[float]) -> float:
        """Deflection relativa a la diagonal del bbox (prompts.md nuevo §4.1).

        Una deflection absoluta fija sub-tessela caras pequenas/muy curvas
        (fillets, B-splines) y puede dejar caras mas pequenas que la
        deflection con CERO triangulos. ``None`` (nuevo default) =>
        ``diag * 0.001``. Un valor explicito se respeta tal cual.
        """
        if linear_deflection is not None:
            return float(linear_deflection)
        try:
            bbox = shape.BoundingBox()
            import math
            dx = float(bbox.xmax) - float(bbox.xmin)
            dy = float(bbox.ymax) - float(bbox.ymin)
            dz = float(bbox.zmax) - float(bbox.zmin)
            diag = math.sqrt(dx * dx + dy * dy + dz * dz)
            if diag > 1e-12:
                return max(diag * 0.001, 1e-4)
        except Exception as ex:
            logger.debug("Relative deflection fallback: %s", ex)
        return 0.1

    @staticmethod
    def tessellate_shape(
        shape: cq.Shape,
        linear_deflection: Optional[float] = None,
        angular_deflection: float = 0.1,
        face_mapping: bool = False,
    ) -> TessellatedMesh:
        """Tessellate 3D B-Rep shape into triangular mesh for 3D visualization.

        When ``face_mapping`` is True the combined mesh is built by accumulating
        the per-face tessellations, so every triangle range can be attributed to
        the covering B-Rep face. The output ``face_triangles`` field lists
        ``{"face_index", "start", "count"}`` ranges into ``indices`` — used by
        the desktop viewport for entity-level (face) picking. The default path
        (``face_mapping=False``) is byte-for-byte the previous behavior.

        ``linear_deflection=None`` (default) usa deflection relativa
        (diag_bbox * 0.001); un valor explicito conserva el comportamiento
        anterior para callers que lo fijan (p. ej. tests de regresion).
        """
        linear_deflection = GeometryEngine._relative_deflection(shape, linear_deflection)
        if face_mapping:
            return GeometryEngine._tessellate_with_face_mapping(
                shape, linear_deflection, angular_deflection
            )

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
        faces_meta = GeometryEngine._faces_metadata(faces)

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

    @staticmethod
    def _tessellate_with_face_mapping(
        shape: cq.Shape,
        linear_deflection: Optional[float],
        angular_deflection: float,
    ) -> TessellatedMesh:
        """Accumulate per-face tessellations so triangles map exactly to faces.

        Contrato de indexacion (prompts.md nuevo §4.2): UN `face_index_map`
        por TRIANGULO (``face_triangles`` como rangos start/count), con
        ``vertex_offset`` acumulado por cara. ``face.tessellate()`` de CadQuery
        ya devuelve vertices en coordenadas globales (aplica
        ``loc.Transformation()`` internamente). Una cara sin triangulacion se
        loguea con WARNING explicito y NO desplaza offsets (el append solo
        ocurre tras tessellar con exito), para no corromper el mapeo de las
        caras siguientes.
        """
        linear_deflection = GeometryEngine._relative_deflection(shape, linear_deflection)
        faces = shape.Faces()
        vertices: List[float] = []
        indices: List[int] = []
        face_triangles: List[Dict[str, Any]] = []
        vertex_offset = 0
        triangle_offset = 0
        for idx, face in enumerate(faces):
            try:
                pts, tris = face.tessellate(
                    tolerance=linear_deflection,
                    angularTolerance=angular_deflection,
                )
            except Exception as ex:
                logger.warning("Face %d produced no triangulation (exception: %s)", idx, ex)
                continue
            if not pts or not tris:
                logger.warning(
                    "Face %d produced no triangulation (%s pts, %s tris) "
                    "with linear_deflection=%s — cara no seleccionable hasta "
                    "re-tessellar con deflection menor",
                    idx, len(pts) if pts else 0, len(tris) if tris else 0,
                    linear_deflection,
                )
                continue
            base = vertex_offset
            for p in pts:
                vertices.extend([float(p.x), float(p.y), float(p.z)])
            for tri in tris:
                indices.extend([int(tri[0]) + base, int(tri[1]) + base, int(tri[2]) + base])
            face_triangles.append({
                "face_index": idx,
                "start": triangle_offset,
                "count": len(tris),
            })
            vertex_offset += len(pts)
            triangle_offset += len(tris)

        bbox = shape.BoundingBox()
        return TessellatedMesh(
            vertices=vertices,
            indices=indices,
            num_vertices=vertex_offset,
            num_triangles=triangle_offset,
            faces_metadata=GeometryEngine._faces_metadata(faces),
            bbox=BoundingBox3D(
                xmin=float(bbox.xmin), xmax=float(bbox.xmax),
                ymin=float(bbox.ymin), ymax=float(bbox.ymax),
                zmin=float(bbox.zmin), zmax=float(bbox.zmax),
            ),
            face_triangles=face_triangles,
        )
