"""PAT-FIT: ajuste real de parches B-spline sobre una malla curva.

Regresión del reporte "B-spline sigue facetado": antes solo se cambiaba la
representación (planos → B-spline grado 1). Ahora las caras planas se agrupan
en regiones y cada región se reemplaza por UNA cara B-spline suave
(BRepOffsetAPI_MakeFilling), con fallback estricto al sólido facetado.
"""
import math

import numpy as np
import pytest

from core.cad_reconstruction import (
    OCPBSplineFitter,
    OCPBRepFitter,
    ReconstructionStatus,
)


def _sphere(nu=40, nv=20, r=10.0):
    v = [(0.0, 0.0, r)]
    idx = {}
    for i in range(1, nv):
        th = math.pi * i / nv
        for j in range(nu):
            ph = 2 * math.pi * j / nu
            idx[(i, j)] = len(v)
            v.append((r * math.sin(th) * math.cos(ph),
                      r * math.sin(th) * math.sin(ph),
                      r * math.cos(th)))
    south = len(v)
    v.append((0.0, 0.0, -r))
    t = []
    for j in range(nu):
        t.append((0, idx[(1, j)], idx[(1, (j + 1) % nu)]))
    for i in range(1, nv - 1):
        for j in range(nu):
            a, b = idx[(i, j)], idx[(i, (j + 1) % nu)]
            c, d = idx[(i + 1, j)], idx[(i + 1, (j + 1) % nu)]
            t.append((a, b, d)); t.append((a, d, c))
    for j in range(nu):
        t.append((south, idx[(nv - 1, (j + 1) % nu)], idx[(nv - 1, j)]))
    return np.asarray(v, float), np.asarray(t, int)


def _face_count(shape):
    from OCP.TopAbs import TopAbs_ShapeEnum
    from OCP.TopExp import TopExp_Explorer
    exp = TopExp_Explorer(shape, TopAbs_ShapeEnum.TopAbs_FACE)
    n = 0
    while exp.More():
        n += 1
        exp.Next()
    return n


def _is_bspline_or_curved(shape):
    """Alguna cara con superficie no planar (b-spline real, no un plano)."""
    from OCP.TopAbs import TopAbs_ShapeEnum
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_SurfaceType
    exp = TopExp_Explorer(shape, TopAbs_ShapeEnum.TopAbs_FACE)
    while exp.More():
        s = BRepAdaptor_Surface(TopoDS.Face_s(exp.Current()))
        if s.GetType() == GeomAbs_SurfaceType.GeomAbs_BSplineSurface:
            return True
        exp.Next()
    return False


def test_patch_fit_reduces_faces_and_is_valid_bspline():
    v, t = _sphere()
    plain = OCPBRepFitter().fit(v, t)
    assert plain.status == ReconstructionStatus.COMPLETED, plain.error_message
    n_plain = _face_count(plain.data)
    assert n_plain == len(t)

    out = OCPBSplineFitter().fit(v, t)
    assert out.status == ReconstructionStatus.COMPLETED, out.error_message
    meta = out.metadata
    assert meta.get("brep_style") == "bspline"
    assert meta.get("bspline_fit") == "applied", meta
    n_fit = meta.get("bspline_faces_after")
    assert n_fit < 0.1 * n_plain, (n_fit, n_plain)
    # Una esfera cerrada debe cerrar en pocos parches.
    assert _face_count(out.data) <= 60
    assert meta.get("bspline_regions_applied") == meta.get("bspline_regions")
    assert _is_bspline_or_curved(out.data), "no hay superficie B-spline real"
    # VOL-GUARD: el ajuste no debe cambiar el volumen (ni colapsarlo a ~0).
    ratio = meta.get("bspline_volume_ratio")
    assert ratio is not None and 0.75 <= ratio <= 1.3333, meta
    from OCP.BRepCheck import BRepCheck_Analyzer
    assert BRepCheck_Analyzer(out.data).IsValid()


def test_patch_fit_can_be_disabled_falls_back_to_legacy_chain():
    v, t = _sphere(nu=12, nv=6)
    out = OCPBSplineFitter(fit_patches=False).fit(v, t)
    assert out.status == ReconstructionStatus.COMPLETED, out.error_message
    assert "bspline_fit" not in out.metadata
    assert out.metadata.get("brep_style") == "bspline"
    assert out.metadata.get("bspline_restriction") in (
        "applied", "not_done", "skipped_invalid", None)


def test_invalid_region_params_raise():
    with pytest.raises(ValueError):
        OCPBSplineFitter(region_angle_deg=0.0)
    with pytest.raises(ValueError):
        OCPBSplineFitter(region_angle_deg=90.0)
