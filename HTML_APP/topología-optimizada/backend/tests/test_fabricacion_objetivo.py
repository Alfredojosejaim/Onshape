"""Tests fabricación activa + objetivo min-volumen + Tet10/Hex8 + reparación.

Cubre prompt.md (alta + alcance, con aprobación explícita 14-sep-2026):
espesor mínimo, overhang activo, soportes, reparación self-intersections,
minimizar volumen sujeto a compliance, Tet10, Hex8.
"""
import numpy as np
import pytest

from core.topopt import SIMPSolver, TopOptError
from tests.test_gcmma import _cantilever


def test_min_thickness_runs_and_rejects():
    s = _cantilever()
    r = s.optimize(max_iterations=3, min_thickness=0.5)
    assert np.isfinite(r["final_compliance"])
    with pytest.raises(TopOptError):
        _cantilever().optimize(max_iterations=2, min_thickness=-1.0)


def test_overhang_active_runs_and_rejects():
    s = _cantilever()
    r = s.optimize(max_iterations=3, overhang_constraint=True,
                   overhang_angle_deg=45.0, overhang_penalty=0.5)
    assert np.isfinite(r["final_compliance"])
    with pytest.raises(TopOptError):
        _cantilever().optimize(max_iterations=2, overhang_constraint=True,
                               overhang_angle_deg=0.0)


def test_min_volume_bisection():
    base = _cantilever().optimize(max_iterations=3)
    lim = float(base["final_compliance"]) * 3.0
    r = _cantilever().optimize(max_iterations=3, objective="min_volume",
                               compliance_limit=lim)
    assert r.get("objective") == "min_volume"
    assert r["final_compliance"] <= lim * 1.001
    assert 0.0 < r["final_volume_fraction"] <= 0.4 + 1e-9
    with pytest.raises(TopOptError):
        _cantilever().optimize(max_iterations=2, objective="min_volume")
    with pytest.raises(TopOptError):
        _cantilever().optimize(max_iterations=2, objective="bogus")


def test_tet10_conversion_and_hex8():
    from core.fea import tet4_to_tet10, solve_fea_hex8
    nodes, els = _cantilever().nodes, _cantilever().elements
    n10, e10 = tet4_to_tet10(np.asarray(nodes), np.asarray(els))
    assert e10.shape == (len(els), 10)
    assert len(n10) > len(nodes)
    hN = np.array([[x, y, z] for z in (0, 1) for y in (0, 1) for x in (0, 1)], float)
    hE = np.array([[0, 1, 3, 2, 4, 5, 7, 6]])
    fixed = [d for n in (0, 1, 2, 3) for d in (3 * n, 3 * n + 1, 3 * n + 2)]
    r = solve_fea_hex8(hN, hE, 1000., 0.3, [(4 * 3 + 2, -1.0)], fixed)
    assert r["compliance"] > 0


def test_repair_and_supports():    from core.cad_reconstruction import repair_self_intersections, generate_supports
    sv = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    st = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]])
    rep = repair_self_intersections(sv, st)
    assert rep["final_pairs"] == 0 and rep["repaired"] is True
    s = _cantilever()
    nodes, els = np.asarray(s.nodes), np.asarray(s.elements)
    out = generate_supports(nodes, els, np.ones(len(els)))
    assert out["num_pillars"] >= 0 and "overhang" in out


def test_explicit_load_direction():
    """La direction explícita (UI paramétrica) manda sobre orientation."""
    from core.conditions import condition_from_dict
    from core.generative_engine import direction_vector
    base = {'type': 'load', 'name': 'L', 'faces': {'name': 'f', 'entities': [], 'mode': 'multi'},
            'orientation': 'perpendicular', 'reference_plane_normal': [0, 0, 1],
            'angle_deg': None, 'sense': 'positive', 'magnitude': 1000.0,
            'indeterminate': False, 'unit': 'N', 'metadata': {}}
    c_exp = condition_from_dict({**base, 'direction': [1, 0, 0]})
    assert list(direction_vector(c_exp)) == pytest.approx([1, 0, 0])
    # Roundtrip con direction.
    c_rt = condition_from_dict(c_exp.to_dict())
    assert list(direction_vector(c_rt)) == pytest.approx([1, 0, 0])
    # Sin direction: modelo clásico.
    c_old = condition_from_dict(base)
    assert list(direction_vector(c_old)) == pytest.approx([0, 0, 1])
    # Direction inválida: fail-loud al usarla, no silencio.
    c_bad = condition_from_dict({**base, 'direction': [0, 0, 0]})
    with pytest.raises(ValueError):
        direction_vector(c_bad)
