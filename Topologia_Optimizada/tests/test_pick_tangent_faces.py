"""Regression test: picking desambigua caras tangentes/fillets (prompt nuevo §4).

Caso que origino el reporte: cerca de la arista compartida entre una cara
plana y un fillet tangente, el pick devolvia la cara vecina. Cubre lo que
`test_tessellation_face_mapping_ranges_cover_all_triangles` no cubre:
precision geometrica del mapeo triangulo->cara sobre geometria real con
tangencia, sin GPU (ray-pick por CPU con Moller-Trumbore sobre la misma
tessellation OCCT que alimenta a `vtkCellPicker`).
"""

from __future__ import annotations

import numpy as np
import pytest

import cadquery as cq

from core.geometry import GeometryEngine


# --------------------------------------------------------------------------- #
# Ray-pick por CPU (equivalente funcional al vtkCellPicker, double-sided
# como el renderer con BackfaceCullingOff).
# --------------------------------------------------------------------------- #

def _ray_pick(verts: np.ndarray, tris: np.ndarray, origin: np.ndarray,
              direction: np.ndarray, min_t: float = 1e-9) -> int:
    """Indice del triangulo golpeado mas cercano, o -1 si no hay hit."""
    v0 = verts[tris[:, 0]]
    e1 = verts[tris[:, 1]] - v0
    e2 = verts[tris[:, 2]] - v0
    p = np.cross(direction, e2)
    det = np.einsum("ij,ij->i", e1, p)
    valid = np.abs(det) > 1e-12
    inv = np.zeros_like(det)
    inv[valid] = 1.0 / det[valid]
    tvec = origin - v0
    u = np.einsum("ij,ij->i", tvec, p) * inv
    q = np.cross(tvec, e1)
    v = np.dot(q, direction) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    hit = valid & (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0) & (t > min_t)
    if not np.any(hit):
        return -1
    t_masked = np.where(hit, t, np.inf)
    return int(np.argmin(t_masked))


def _tessellate_box_with_fillet():
    """Caja 10^3 con aristas verticales redondeadas (fillet r=1.5 tangente)."""
    shape = cq.Workplane("XY").box(10, 10, 10).edges("|Z").fillet(1.5).val()
    tess = GeometryEngine.tessellate_shape(shape, face_mapping=True)
    d = tess.to_dict()
    verts = np.asarray(d["vertices"], dtype=float).reshape(-1, 3)
    tris = np.asarray(d["indices"], dtype=np.int64).reshape(-1, 3)
    n_tri = tris.shape[0]
    face_of_tri = np.full(n_tri, -1, dtype=np.int64)
    for rng in d.get("face_triangles", []):
        s, c = int(rng["start"]), int(rng["count"])
        face_of_tri[s:s + c] = int(rng["face_index"])
    return verts, tris, face_of_tri, float(np.ptp(verts, axis=0).max())


def _tri_normals_centroids(verts, tris):
    v0, v1, v2 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    n = np.cross(v1 - v0, v2 - v0)
    norm = np.linalg.norm(n, axis=1, keepdims=True)
    norm[norm < 1e-12] = 1.0
    return n / norm, (v0 + v1 + v2) / 3.0


def test_pick_disambiguates_tangent_faces():
    verts, tris, face_of_tri, diag = _tessellate_box_with_fillet()
    n_tri = tris.shape[0]

    # Contrato de indexacion: una entrada por TRIANGULO (prompt §4.3).
    assert len(face_of_tri) == n_tri
    assert set(np.unique(face_of_tri)) - {-1} != set()
    assert not np.any(face_of_tri < 0), "triangulos sin cara asignada"

    normals, centroids = _tri_normals_centroids(verts, tris)

    # Detectar caras curvas (fillets) por dispersion de normales intra-cara.
    curved, planar = set(), set()
    for f in np.unique(face_of_tri):
        fn = normals[face_of_tri == int(f)]
        mean = fn.mean(axis=0) / max(np.linalg.norm(fn.mean(axis=0)), 1e-12)
        spread = float(np.degrees(np.arccos(np.clip(fn @ mean, -1.0, 1.0))).max())
        (curved if spread > 8.0 else planar).add(int(f))
    assert curved, "la geometria debe incluir fillets (caras curvas)"
    assert planar, "la geometria debe incluir caras planas"

    # Puntos de prueba SOBRE la cara plana junto a la arista compartida con
    # el fillet: la cara plana se tessela en 2 triangulos enormes (es plana)
    # mientras el fillet queda fino; el centroide no sirve (esta lejos de la
    # arista). Se detecta la arista compartida por proximidad de vertices
    # (tessellation por cara: vertices duplicados, no compartidos) y se
    # muestrea dentro del triangulo plano pegado a ella.
    fillet_verts = np.unique(tris[np.isin(face_of_tri, list(curved))].ravel())
    fcoords = verts[fillet_verts]
    planar_idx = np.nonzero(np.isin(face_of_tri, list(planar)))[0]
    vtol = 1e-3 * diag
    eps = 1e-4 * diag
    tested = 0
    for ti in planar_idx:
        tv = tris[ti]
        near = [vi for vi in tv if np.linalg.norm(
            fcoords - verts[vi], axis=1).min() < vtol]
        if len(near) < 2:
            continue  # triangulo plano sin arista sobre el fillet
        edge_mid = verts[near].mean(axis=0)
        # Punto dentro del triangulo plano, pegado a la arista compartida.
        p = 0.9 * edge_mid + 0.1 * centroids[ti]
        origin = p + normals[ti] * eps
        hit = _ray_pick(verts, tris, origin, -normals[ti], min_t=eps * 0.5)
        assert hit >= 0, f"rayo sin hit junto a arista (tri {ti})"
        assert int(face_of_tri[hit]) == int(face_of_tri[ti]), (
            f"punto junto a tangencia del tri {ti} (cara {face_of_tri[ti]}) "
            f"pickeo cara {face_of_tri[hit]} (fillet vecino)"
        )
        tested += 1
    assert tested > 0, "debe haber triangulos planos con arista sobre el fillet"


def test_pick_spot_check_all_faces():
    """Chequeo global: rayos sobre todas las caras resuelven su propia cara."""
    verts, tris, face_of_tri, diag = _tessellate_box_with_fillet()
    normals, centroids = _tri_normals_centroids(verts, tris)
    eps = 1e-4 * diag
    rng = np.random.default_rng(7)
    for f in np.unique(face_of_tri):
        members = np.nonzero(face_of_tri == int(f))[0]
        for ti in rng.choice(members, size=min(4, len(members)), replace=False):
            origin = centroids[ti] + normals[ti] * eps
            hit = _ray_pick(verts, tris, origin, -normals[ti], min_t=eps * 0.5)
            assert hit >= 0
            assert int(face_of_tri[hit]) == int(f)


def test_highlight_vectorized_update_matches_selection():
    """HighlightRenderer vectorizado: celdas seleccionadas en naranja,
    hover en azul, resto en base (incluye multi-cara)."""
    from desktop.viewport.highlight import HighlightRenderer
    from desktop.viewport.renderer import Renderer

    r = Renderer.__new__(Renderer)
    verts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                      [2, 0, 0], [2, 1, 0]], float)
    tris = np.array([[0, 1, 2], [0, 2, 3], [1, 4, 5], [1, 5, 2]])
    poly = r._build_polydata(verts, tris, compute_normals=True,
                             cell_data={"face_index": np.array([0, 0, 1, 1])})
    hr = HighlightRenderer(poly)
    assert hr.base_colors_np.shape == (4, 3)
    assert hr.base_colors_np.dtype == np.uint8

    hr.update({0, 2, 3}, hovered_cell_id=1)
    from vtkmodules.util.numpy_support import vtk_to_numpy

    got = vtk_to_numpy(poly.GetCellData().GetArray("Colors"))
    assert got.shape == (4, 3)
    np.testing.assert_array_equal(got[0], (255, 165, 0))
    np.testing.assert_array_equal(got[2], (255, 165, 0))
    np.testing.assert_array_equal(got[3], (255, 165, 0))
    np.testing.assert_array_equal(got[1], (120, 190, 255))

    hr.update(set())
    got = vtk_to_numpy(poly.GetCellData().GetArray("Colors"))
    np.testing.assert_array_equal(got, hr.base_colors_np)
