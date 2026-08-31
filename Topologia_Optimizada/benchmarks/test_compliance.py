"""Tests del instrumento de compliance 0.5·uᵀ·K·u (benchmarks/compliance.py).

Regresión: campos de desplazamiento de cuerpo rígido deben producir energía de
deformación nula (≈0). Atrapa errores de orden de DOFs / apilado de ``ue``, como
el que se corrigió (traslación rígida daba energía absurda por un reshape que
mezclaba componente y nodo).
"""

import numpy as np
import pytest

from benchmarks.compliance import tet4_strain_energy

_HERE = "benchmarks/meshes/small_500.npz"

E = 68.9e9
NU = 0.33


@pytest.fixture(scope="module")
def small_mesh():
    data = np.load(_HERE)
    return data["nodes"].astype(float), data["elements"].astype(int)


def test_zero_displacement_small_mesh(small_mesh):
    nodes, elems = small_mesh
    assert tet4_strain_energy(nodes, elems, np.zeros_like(nodes), E, NU) == 0.0


def _roundoff_scale(nodes, elems, E):
    """Cota superior del ruido numérico esperado en una cancelación de cuerpo
    rígido: ~eps_machine × E × L² × N_elementos (rigidez típica × norm² de u)."""
    span = (nodes.max(axis=0) - nodes.min(axis=0)).max()
    return np.finfo(float).eps * E * span**2 * len(elems)


def test_rigid_translation_zero_energy(small_mesh):
    nodes, elems = small_mesh
    c = np.array([5.0, -3.0, 2.0])
    u = np.ones_like(nodes) * c
    tol = _roundoff_scale(nodes, elems, E) * 1e3
    assert abs(tet4_strain_energy(nodes, elems, u, E, NU)) < tol


def test_rigid_rotation_zero_energy(small_mesh):
    nodes, elems = small_mesh
    theta = 1e-6
    u = np.zeros_like(nodes)
    u[:, 0] = -theta * nodes[:, 1]
    u[:, 1] = theta * nodes[:, 0]
    tol = _roundoff_scale(nodes, elems, E) * 1e3
    assert abs(tet4_strain_energy(nodes, elems, u, E, NU)) < tol


def test_strain_positive_and_finite(small_mesh):
    nodes, elems = small_mesh
    rng = np.random.default_rng(0)
    u = rng.normal(size=nodes.shape) * 0.001
    e = tet4_strain_energy(nodes, elems, u, E, NU)
    assert np.isfinite(e)
    assert e > 0.0


def test_strain_energy_with_nan_is_tolerated(small_mesh):
    nodes, elems = small_mesh
    u = np.random.default_rng(1).normal(size=nodes.shape) * 0.001
    u[0, :] = np.nan
    e = tet4_strain_energy(nodes, elems, u, E, NU)
    assert np.isfinite(e)
