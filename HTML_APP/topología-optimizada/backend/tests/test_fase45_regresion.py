"""Regresión Fase 4.5c (auditoría scope-creep): 5 módulos sin test.

Orden por riesgo: simetría → térmico → ESO → level-set → animación.
Malla mínima de 2 tets no degenerados; ESO/level-set corren pocas
iteraciones (smoke + invariantes, no exactitud contra literatura).
"""

import numpy as np
import pytest

from core.topopt import SIMPSolver, TopOptError
from core.thermal import thermal_load_vector
from core.cae_studies import animate_mode_shape

NODES = np.array([
    [0.0, 0.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.0, 1.0, 1.0],
], dtype=float)
ELEMENTS = np.array([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=int)

E = 210e3
NU = 0.3


def _solver(**kw):
    s = SIMPSolver(nodes=NODES, elements=ELEMENTS, young_modulus=E,
                   poisson_ratio=NU, volfrac=0.5, filter_radius=0.5, **kw)
    f = np.zeros(NODES.shape[0] * 3)
    f[4 * 3 + 1] = -100.0  # carga en -Y sobre el nodo libre
    s.set_load(f)
    s.set_fixed_dofs(np.array([0, 1, 2, 3, 4, 5, 6, 7, 8], dtype=int))
    return s


# 1. Simetría — aislado, valida el pipeline primero.
def test_symmetry_pairs_and_validation():
    s = _solver()
    s.set_symmetry_planes([("x", 0.5)])
    assert s._sym_pairs is not None and len(s._sym_pairs) == 2
    v = np.array([0.2, 0.8])
    assert np.allclose(s._mirror_average(v), s._mirror_average(s._mirror_average(v)))
    s.set_symmetry_planes(None)
    assert s._sym_pairs is None
    with pytest.raises(TopOptError):
        s.set_symmetry_planes([("w", 0.5)])
    with pytest.raises(TopOptError):
        s.set_symmetry_planes([(0, float("nan"))])


def test_symmetry_vendored_rejects():
    """Fase 4.5b (revertir): vendored congelado, sin simetría (fail-loud)."""
    from vendored.simp import SIMPSolver as VendoredSIMP
    b = VendoredSIMP(nodes=NODES, elements=ELEMENTS, young_modulus=E,
                     poisson_ratio=NU)
    assert not hasattr(b, "set_symmetry_planes")
    assert not hasattr(b, "_mirror_average")
    assert not hasattr(b, "_mirror_min")


# 2. Térmico — ΔT uniforme ⇒ resultante auto-equilibrada ≈ 0.
def test_thermal_uniform_dT_self_equilibrated():
    T = np.full(NODES.shape[0], 293.15 + 50.0)
    F = thermal_load_vector(NODES, ELEMENTS, E, NU, 12e-6, T, reference_temperature=293.15)
    assert F.shape == (NODES.shape[0] * 3,)
    assert np.all(np.isfinite(F))
    assert np.linalg.norm(F.reshape(-1, 3).sum(axis=0)) < 1e-6 * max(np.linalg.norm(F), 1.0)


def test_thermal_zero_dT_exact_zero_and_bad_inputs():
    T0 = np.full(NODES.shape[0], 293.15)
    assert np.all(thermal_load_vector(NODES, ELEMENTS, E, NU, 12e-6, T0) == 0.0)
    with pytest.raises(Exception):
        thermal_load_vector(NODES, ELEMENTS, E, NU, -1.0, T0)
    with pytest.raises(Exception):
        thermal_load_vector(NODES, ELEMENTS, E, NU, 12e-6, T0[:-1])


# 3. ESO — smoke: binario 0/1, volumen en rango, corre sin excepción.
@pytest.mark.parametrize("criterion", ["compliance", "stress"])
def test_eso_binary_and_volume(criterion):
    s = _solver()
    r = s.optimize(max_iterations=4, optimizer="eso", eso_criterion=criterion)
    x = np.asarray(r["densities"], dtype=float)
    assert x.shape == (2,) and np.all(np.isfinite(x))
    assert set(np.round(x, 6)).issubset({s.rho_min, 1.0})
    assert 0.0 < r["final_volume_fraction"] <= 1.0


def test_eso_bad_evolutionary_rate():
    s = _solver()
    with pytest.raises(TopOptError):
        s.optimize(max_iterations=2, optimizer="eso", evolutionary_rate=0.0)
    with pytest.raises(TopOptError):
        s.optimize(max_iterations=2, optimizer="eso", eso_criterion="bogus")


# 4. Level-Set — estabilidad: sin NaN, volumen acotado, historial monótono-ish.
def test_level_set_stability():
    s = _solver()
    r = s.optimize(max_iterations=3, optimizer="level_set", ls_cfl=0.2, ls_hole_period=2)
    x = np.asarray(r["densities"], dtype=float)
    assert np.all(np.isfinite(x)) and np.all((x >= 0.0) & (x <= 1.0))
    vols = r.get("volume_fraction_history", [])
    assert len(vols) > 0
    assert all(0.0 < v <= 1.0 + 1e-9 for v in vols), vols
    with pytest.raises(TopOptError):
        s.optimize(max_iterations=2, optimizer="level_set", ls_cfl=0.0)


# 5. Animación modal — postproceso puro: forma/salida.
def test_animate_mode_shape_frames():
    phi = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
                    [1.0, 1.0, 0.0], [0.0, 1.0, 1.0]])
    out = animate_mode_shape(NODES, phi, amplitude="auto", n_frames=8)
    assert out["n_frames"] == 8 and len(out["frames"]) == 8
    assert all(np.asarray(f).shape == (5, 3) for f in out["frames"])
    assert np.allclose(out["frames"][0], 0.0)  # sin(0) = 0
    assert out["amplitude"] > 0 and out["max_displacement"] > 0
    with pytest.raises(ValueError):
        animate_mode_shape(NODES, np.zeros((5, 3)))
    with pytest.raises(ValueError):
        animate_mode_shape(NODES, phi, n_frames=1)
