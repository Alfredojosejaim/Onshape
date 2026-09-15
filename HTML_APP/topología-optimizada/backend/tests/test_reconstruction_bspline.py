"""Tests suavizado Taubin + reconstrucción B-spline (NURBS) vía OCC.

Aprobado explícitamente por el usuario (fuera de plan, confirm-gate Fase 0.5):
geometría CAD limpia y suave en lugar de malla facetada/serruchada.

- Taubin (λ|μ) preserva volumen mucho mejor que el Laplaciano puro.
- ``MeshSmoother`` mantiene "laplacian" como default (regresión).
- ``OCPBSplineFitter`` une caras coplanares, convierte a B-spline y exporta
  STEP, con metadatos explícitos por paso.
"""
import math

import numpy as np
import pytest

from core.cad_reconstruction import (
    MeshSmoother,
    OCPBSplineFitter,
    ReconstructionPipeline,
    ReconstructionStatus,
    smooth_surface_mesh,
    taubin_smooth,
)


def _icosphere(subdiv=1):
    t = (1.0 + math.sqrt(5.0)) / 2.0
    verts = [
        (-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
        (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
        (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1),
    ]
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    v = [list(p) for p in verts]
    f = [list(tri) for tri in faces]
    for _ in range(subdiv):
        cache = {}
        new_f = []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                p = [(v[a][i] + v[b][i]) / 2.0 for i in range(3)]
                n = math.sqrt(sum(x * x for x in p)) or 1.0
                v.append([x / n for x in p])
                cache[key] = len(v) - 1
            return cache[key]

        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            new_f += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        f = new_f
    return np.array(v, dtype=float), np.array(f, dtype=int)


def _mesh_volume(verts, tris):
    v0 = verts[tris[:, 0]]
    v1 = verts[tris[:, 1]]
    v2 = verts[tris[:, 2]]
    return float(np.sum(np.einsum("ij,ij->i", v0, np.cross(v1, v2))) / 6.0)


def test_taubin_preserves_volume_better_than_laplacian():
    v, t = _icosphere(2)
    vol0 = _mesh_volume(v, t)
    lv, lt = smooth_surface_mesh(v, t, iterations=25, alpha=0.5)
    tv, tt = taubin_smooth(v, t, iterations=25, lambda_=0.5, mu=-0.53)
    assert lt.shape == t.shape and tt.shape == t.shape
    vol_l = _mesh_volume(lv, lt)
    vol_t = _mesh_volume(tv, tt)
    assert abs(vol_t - vol0) < abs(vol_l - vol0)


def test_taubin_validation_and_smoother_methods():
    v, t = _icosphere(1)
    with pytest.raises(ValueError):
        taubin_smooth(v, t, lambda_=0.0)
    with pytest.raises(ValueError):
        taubin_smooth(v, t, mu=0.1)
    r_lap = MeshSmoother().smooth(v, t, iterations=2)
    assert r_lap.metadata["method"] == "laplacian"
    r_tau = MeshSmoother().smooth(v, t, iterations=2, method="taubin")
    assert r_tau.metadata["method"] == "taubin"
    with pytest.raises(ValueError):
        MeshSmoother().smooth(v, t, method="bogus")
    with pytest.raises(ValueError):
        ReconstructionPipeline(smoothing_method="bogus")


def _box_tris(origin, size):
    ox, oy, oz = origin
    s = size
    v = np.array([
        [ox, oy, oz], [ox + s, oy, oz], [ox + s, oy + s, oz], [ox, oy + s, oz],
        [ox, oy, oz + s], [ox + s, oy, oz + s], [ox + s, oy + s, oz + s],
        [ox, oy + s, oz + s],
    ], dtype=float)
    f = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
         (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
         (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2)]
    return v, f


def test_bspline_fitter_unifies_and_exports_step(tmp_path):
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_ShapeEnum

    v, f = _box_tris((0.0, 0.0, 0.0), 10.0)
    out = OCPBSplineFitter(step_path=str(tmp_path / "out.step")).fit(v, np.array(f))
    assert out.status == ReconstructionStatus.COMPLETED, out.error_message
    assert out.metadata.get("brep_style") == "bspline"
    # UnifySameDomain debe fusionar los 2 triángulos coplanares de cada cara.
    assert out.metadata.get("unify_same_domain") == "applied"
    exp = TopExp_Explorer(out.data, TopAbs_ShapeEnum.TopAbs_FACE)
    n_faces = 0
    while exp.More():
        n_faces += 1
        exp.Next()
    assert n_faces <= 6
    step = tmp_path / "out.step"
    assert step.exists() and step.stat().st_size > 0


def test_bspline_fitter_falls_back_on_garbage():
    """Malla degenerada -> FAILED explícito, nunca crash."""
    v = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    t = np.array([[0, 1, 2]])
    out = OCPBSplineFitter().fit(v, t)
    assert out.status == ReconstructionStatus.FAILED
