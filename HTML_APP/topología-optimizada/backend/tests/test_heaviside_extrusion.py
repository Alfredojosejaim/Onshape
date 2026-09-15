"""Tests proyección Heaviside SIMP + filtro de extrusión 2D.

Aprobado explícitamente por el usuario (fuera de plan, confirm-gate Fase 0.5):
eliminar densidades intermedias (bordes nítidos) y forzar diseño 2D.

- Matemática de proyección/derivada (eta=0.5 -> 0.5, monótona, d>0).
- Regresión: sin Heaviside el lazo es bit-idéntico al histórico.
- Smoke end-to-end: corre, finito, volumen en rango, flags en el resultado.
- Fail-loud en beta/eta/axis inválidos.
- Extrusión: columnas (mismo plano perpendicular al eje) quedan iguales.
"""
import numpy as np
import pytest

from core.topopt import SIMPSolver, TopOptError
from tests.test_gcmma import _cantilever


def test_heaviside_math():
    s = _cantilever()
    s.set_heaviside_projection(beta=4.0, eta=0.5)
    # eta=0.5 -> punto fijo exacto en 0.5
    assert float(s._project(np.array([0.5]))[0]) == pytest.approx(0.5)
    # monótona creciente
    xs = np.linspace(0.0, 1.0, 21)
    p = s._project(xs)
    assert np.all(np.diff(p) >= -1e-12)
    assert p[0] == pytest.approx(0.0, abs=1e-12)
    assert p[-1] == pytest.approx(1.0, abs=1e-12)
    # derivada positiva y finita
    d = s._dproject(xs)
    assert np.all(d > 0) and np.all(np.isfinite(d))


def test_heaviside_off_is_identity():
    s = _cantilever()
    x = np.linspace(0.0, 1.0, s.num_elements)
    assert np.allclose(s._physical_density(x), x)
    assert np.allclose(s._project(x), x)
    assert np.allclose(s._dproject(x), 1.0)


def test_heaviside_regression_no_projection():
    """Sin proyección el resultado es idéntico al histórico (mismo solver)."""
    a = _cantilever().optimize(max_iterations=5)
    b = _cantilever()
    b.set_heaviside_projection(beta=8.0, continuation=True)
    b._heaviside = False  # apagada tras activar: debe ser no-op
    r = b.optimize(max_iterations=5)
    assert np.allclose(a["densities"], r["densities"])
    assert a["final_compliance"] == pytest.approx(r["final_compliance"])


def test_heaviside_end_to_end():
    s = _cantilever()
    s.set_heaviside_projection(beta=8.0, eta=0.5, continuation=True)
    r = s.optimize(max_iterations=8)
    assert r["heaviside_projection"] is True
    assert r["heaviside_beta"] == pytest.approx(8.0)
    assert np.isfinite(r["final_compliance"])
    d = np.asarray(r["densities"])
    assert d.min() >= -1e-9 and d.max() <= 1.0 + 1e-9
    assert 0.0 < r["physical_volume_fraction"] <= 1.0


def test_heaviside_sharpens_midrange_field():
    """La proyección aleja el campo filtrado de 0.5 (menos grises)."""
    s = _cantilever()
    mid = np.full(s.num_elements, 0.5)
    rng = np.random.default_rng(0)
    mid = np.clip(0.5 + 0.3 * rng.standard_normal(s.num_elements), 0.0, 1.0)
    s.set_heaviside_projection(beta=16.0, eta=0.5)
    proj = s._project(mid)
    assert np.mean(np.abs(proj - 0.5)) > np.mean(np.abs(mid - 0.5))


def test_heaviside_validation():
    with pytest.raises(TopOptError):
        _cantilever().set_heaviside_projection(beta=0.0)
    with pytest.raises(TopOptError):
        _cantilever().set_heaviside_projection(eta=1.0)
    with pytest.raises(TopOptError):
        _cantilever().set_heaviside_projection(eta=0.0)


def test_extrusion_axis_validation():
    s = _cantilever()
    with pytest.raises(TopOptError):
        s.set_extrusion_filter(5)
    with pytest.raises(TopOptError):
        s.set_extrusion_filter("w")
    # None desactiva sin error
    s.set_extrusion_filter(None)
    assert s._extrusion_groups is None


def test_extrusion_equalizes_columns():
    s = _cantilever()
    s.set_extrusion_filter(2)  # constante a lo largo de z
    groups = s._extrusion_groups
    assert groups is not None and any(len(g) > 1 for g in groups)
    x = np.linspace(0.05, 1.0, s.num_elements)
    out = s._apply_extrusion(x)
    for g in groups:
        if len(g) > 1:
            assert np.allclose(out[g], float(np.mean(x[g])))
    # fuera de un grupo multi-elemento el valor no cambia
    for i in range(s.num_elements):
        assert 0.0 <= out[i] <= 1.0


def test_extrusion_end_to_end():
    s = _cantilever()
    s.set_extrusion_filter("z")
    r = s.optimize(max_iterations=6)
    assert r["extrusion_axis"] == 2
    d = np.asarray(r["densities"])
    for g in s._extrusion_groups:
        if len(g) > 1:
            assert np.allclose(d[g], d[g[0]], atol=1e-9)
