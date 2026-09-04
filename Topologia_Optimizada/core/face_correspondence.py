"""Deterministic correspondence between CAD B-Rep faces and Gmsh surfaces.

The ORDER of ``cq.Shape.Faces()`` (OCCT ``TopExp_Explorer`` traversal) and the
order of ``gmsh.model.getEntities(2)`` after importing a STEP are two
independent enumerations that are NOT part of any public contract. Relying on
index-alignment between them is unsafe (it can break with seams, multiple
solids, shared faces, or across Gmsh/OCCT versions).

This module builds a deterministic 1:1 mapping between a CAD face index
(``face_<fi>``, the stable identifier used by :mod:`core.boundary` /
``CADFace.id``) and a Gmsh surface entity tag using a **geometric signature**
(centroid + normal + area). If two candidate Gmsh surfaces are within the
ambiguity tolerance, an explicit :class:`AmbiguousFaceCorrespondenceError` is
raised rather than silently choosing one.
"""

from dataclasses import dataclass
import logging
from typing import Dict, List, Optional, Tuple

import cadquery as cq
import numpy as np

from core.geometry import _robust_face_reference_point

logger = logging.getLogger(__name__)


class FaceCorrespondenceError(Exception):
    """Raised when a CAD face cannot be matched to a Gmsh surface."""


class AmbiguousFaceCorrespondenceError(FaceCorrespondenceError):
    """Raised when multiple Gmsh surfaces match a CAD face within tolerance."""


@dataclass(frozen=True)
class FaceSignature:
    """Geometric signature used to match a CAD face to a Gmsh surface."""
    center: Tuple[float, float, float]
    normal: Tuple[float, float, float]
    area: float


def _shape_face_signatures(shape: cq.Shape) -> List[FaceSignature]:
    """Build the geometric signature of every ``shape.Faces()[fi]``."""
    signatures: List[FaceSignature] = []
    faces = shape.Faces()
    for face in faces:
        center, normal = _robust_face_reference_point(face)
        if center is None or normal is None:
            md = np.array([0.0, 0.0, 0.0])
        else:
            c = np.array([float(center.x), float(center.y), float(center.z)])
            n = np.array([float(normal.x), float(normal.y), float(normal.z)])
            nlen = np.linalg.norm(n)
            n = n / nlen if nlen > 1e-12 else np.array([0.0, 0.0, 1.0])
        try:
            area = float(face.Area())
        except Exception:
            area = 0.0
        signatures.append(
            FaceSignature(
                center=(float(c[0]), float(c[1]), float(c[2])),
                normal=(float(n[0]), float(n[1]), float(n[2])),
                area=area,
            )
        )
    return signatures


def _gmsh_surface_signatures(gmsh, samples: int = 20) -> List[Tuple[int, FaceSignature]]:
    """Build the geometric signature of every Gmsh surface (dim=2).

    ``getCenterOfMass`` / ``getMassProperties`` return zeros on unmeshed
    geometry, so the centroid, area and normal are computed **numerically** by
    sampling the parametric (u, v) domain of each surface and mapping the grid
    to 3D with ``gmsh.model.getValue``. This is robust and works before meshing.
    """
    out: List[Tuple[int, FaceSignature]] = []
    for dim, tag in gmsh.model.getEntities(2):
        if dim != 2:
            continue
        try:
            # getParametrizationBounds returns ((umin, vmin), (umax, vmax)).
            uvmin, uvmax = gmsh.model.getParametrizationBounds(2, tag)
            umin, vmin = float(uvmin[0]), float(uvmin[1])
            umax, vmax = float(uvmax[0]), float(uvmax[1])
        except Exception:
            umin, umax, vmin, vmax = 0.0, 1.0, 0.0, 1.0

        if not (np.isfinite(umin) and np.isfinite(umax)):
            umin, umax = 0.0, 1.0
        if not (np.isfinite(vmin) and np.isfinite(vmax)):
            vmin, vmax = 0.0, 1.0

        us = np.linspace(umin, umax, samples)
        vs = np.linspace(vmin, vmax, samples)

        pts = []
        uv_center = None
        for u in us:
            for v in vs:
                try:
                    xyz = gmsh.model.getValue(2, tag, [float(u), float(v)])
                except Exception:
                    continue
                pts.append([float(xyz[0]), float(xyz[1]), float(xyz[2])])
                if abs(u - (umin + umax) / 2) < 1e-12 and abs(v - (vmin + vmax) / 2) < 1e-12:
                    uv_center = [float(u), float(v)]

        if len(pts) < 4:
            center = (0.0, 0.0, 0.0)
            area = 0.0
            normal = (0.0, 0.0, 1.0)
        else:
            pts_arr = np.asarray(pts, dtype=float)
            center = tuple(float(x) for x in pts_arr.mean(axis=0))
            # Surface area by triangulating the sampled 3D grid.
            gx, gy = samples, samples
            area = 0.0
            for i in range(samples - 1):
                for j in range(samples - 1):
                    p00 = pts_arr[i * samples + j]
                    p01 = pts_arr[i * samples + j + 1]
                    p10 = pts_arr[(i + 1) * samples + j]
                    # two triangles per grid cell
                    area += 0.5 * np.linalg.norm(
                        np.cross(p01 - p00, p10 - p00))
                    p11 = pts_arr[(i + 1) * samples + j + 1]
                    area += 0.5 * np.linalg.norm(
                        np.cross(p11 - p01, p10 - p01))
            # Normal evaluated at the center of the UV domain.
            if uv_center is None:
                uv_center = [(umin + umax) / 2, (vmin + vmax) / 2]
            try:
                nvec = gmsh.model.getNormal(tag, uv_center)
                n = np.array([float(nvec[0]), float(nvec[1]), float(nvec[2])])
            except Exception:
                n = None
            if n is not None and np.linalg.norm(n) > 1e-12:
                n = n / np.linalg.norm(n)
                normal = (float(n[0]), float(n[1]), float(n[2]))
            else:
                normal = (0.0, 0.0, 1.0)

        out.append((tag, FaceSignature(
            center=center,
            normal=normal,
            area=area,
        )))
    return out


def build_face_correspondence(
    shape: cq.Shape,
    gmsh,
    tol: float = 1e-3,
) -> Dict[int, int]:
    """Match each CAD face ``fi`` to its Gmsh surface tag by geometry.

    The matching is based on the distance between (centroid, normal, area)
    signatures. For each CAD face the closest Gmsh surface is chosen only if it
    is unambiguous: the second-best candidate must fall outside the ambiguity
    tolerance (relative on area, absolute-plus-relative on centroid/normal),
    otherwise :class:`AmbiguousFaceCorrespondenceError` is raised.

    Args:
        shape: The CadQuery shape whose faces are the reference.
        gmsh: Initialized Gmsh module (model already synchronized). Faces are
            queried via ``gmsh.model.getEntities(2)``.
        tol: Relative tolerance used to declare a candidate ambiguous.

    Returns:
        ``{cad_face_index: gmsh_surface_tag}``.
    """
    cad_sigs = _shape_face_signatures(shape)
    gmsh_sigs = _gmsh_surface_signatures(gmsh)

    if len(cad_sigs) != len(gmsh_sigs):
        raise FaceCorrespondenceError(
            f"Count mismatch between CAD faces ({len(cad_sigs)}) and "
            f"Gmsh surfaces ({len(gmsh_sigs)}); cannot build a 1:1 mapping."
        )

    mapping: Dict[int, int] = {}
    for fi, csig in enumerate(cad_sigs):
        best_tag = None
        best_score = float("inf")
        second_score = float("inf")
        for tag, gsig in gmsh_sigs:
            score = _signature_distance(csig, gsig)
            if score < best_score:
                second_score = best_score
                best_score = score
                best_tag = tag
            elif score < second_score:
                second_score = score
        if second_score <= best_score * (1.0 + tol):
            raise AmbiguousFaceCorrespondenceError(
                f"CAD face {fi} ({csig}) is ambiguous: two Gmsh surfaces match "
                f"within tolerance (best={best_score:.3g}, second={second_score:.3g}). "
                "Refusing to guess the correspondence."
            )
        mapping[fi] = best_tag
    return mapping


def _signature_distance(a: FaceSignature, b: FaceSignature) -> float:
    """Combined scalar distance between two face signatures."""
    dc = np.array(a.center) - np.array(b.center)
    d_c = float(np.linalg.norm(dc))
    # Use the max face dimension scale so area magnitude doesn't dominate.
    scale = max(float(a.area) ** 0.5, float(b.area) ** 0.5, 1e-6)
    d_n = 1.0 - abs(float(np.dot(np.array(a.normal), np.array(b.normal))))
    d_a = abs(a.area - b.area) / max(scale * scale, 1e-9)
    # Weight centroid distance by the face scale; keep normal/area as
    # multiplicative discriminates so near-parallel opposites still differ.
    return d_c / scale + 0.5 * d_n + 0.5 * d_a
