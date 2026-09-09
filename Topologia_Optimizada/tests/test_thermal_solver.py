"""Tests of the real steady-state thermal solver (core.thermal).

Mesh: a 2x1x1 bar (x in {0,1,2}, y,z in {0,1}) split into 12 Tet4 via the
Kuhn-Freudenthal triangulation of each unit cube. The 1D steady solution
T(x) = a*x + b is exactly representable in Tet4, so Dirichlet/Neumann cases
have known closed-form solutions.
"""

import numpy as np
import pytest

from core.cae_studies import (
    StudyStatus,
    ThermalAnalysis,
    ThermalBoundary,
    ThermalBoundaryType,
)
from core.materials import STANDARD_MATERIALS
from core.thermal import (
    ThermalError,
    ThermalSolver,
    _tet_conductivity,
    solve_steady_thermal,
    solve_thermal_study,
)


def _bar_mesh():
    coords = np.array(
        [[float(ix), float(iy), float(iz)] for ix in (0, 1, 2) for iy in (0, 1) for iz in (0, 1)]
    )
    assert coords.shape == (12, 3)

    def idx(ix, iy, iz):
        return ix * 4 + iy * 2 + iz

    kuhn = [
        [0, 1, 2, 6],
        [0, 1, 5, 6],
        [0, 4, 5, 6],
        [0, 4, 7, 6],
        [0, 3, 7, 6],
        [0, 3, 2, 6],
    ]
    # Local Kuhn vertex -> (dx, dy, dz) within a unit cube.
    local = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
             (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    elements = []
    for base_ix in (0, 1):
        for tet in kuhn:
            elements.append(
                [idx(base_ix + dx, dy, dz) for (dx, dy, dz) in (local[v] for v in tet)]
            )
    return coords, np.asarray(elements, dtype=int)


NODES, ELEMENTS = _bar_mesh()
X0 = [0, 1, 2, 3]      # x = 0 face
X1 = [4, 5, 6, 7]      # x = 1 plane (interior)
X2 = [8, 9, 10, 11]    # x = 2 face
K = 50.0


def _thermal_material():
    return STANDARD_MATERIALS["steel"].with_thermal_properties(
        thermal_conductivity=K, specific_heat=490.0
    )


def _study_with(*boundaries):
    s = ThermalAnalysis()
    s.model_id = "m1"
    s.material = _thermal_material()
    for b in boundaries:
        s.add_thermal_boundary(b)
    return s


# ====================================================================== #
# Element matrix sanity
# ====================================================================== #

def test_element_conductivity_symmetric_psd():
    coords = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    vol, ke, _ = _tet_conductivity(coords, K)
    assert vol == pytest.approx(1.0 / 6.0)
    assert ke.shape == (4, 4)
    np.testing.assert_allclose(ke, ke.T, rtol=1e-12)
    assert np.all(np.linalg.eigvalsh(ke) >= -1e-9)
    # Constant field carries no flux: rows sum to zero.
    np.testing.assert_allclose(ke.sum(axis=1), 0.0, atol=1e-9)


def test_global_matrix_symmetric():
    solver = ThermalSolver(NODES, ELEMENTS, K)
    Kc = solver.assemble_conductivity()
    assert Kc.shape == (12, 12)
    assert abs((Kc - Kc.T).max()) < 1e-9


# ====================================================================== #
# Dirichlet with known solution T(x) = 100*x
# ====================================================================== #

def test_dirichlet_bar_matches_analytic_solution():
    dirichlet = {n: 0.0 for n in X0} | {n: 200.0 for n in X2}
    res = solve_steady_thermal(NODES, ELEMENTS, K, dirichlet)
    assert res["success"] is True
    T = res["temperatures"]
    assert T[X0].tolist() == pytest.approx([0.0] * 4)
    assert T[X2].tolist() == pytest.approx([200.0] * 4)
    # Interior plane x=1 must be exactly 100 (linear field is exact in Tet4).
    np.testing.assert_allclose(T[X1], 100.0, rtol=1e-9, atol=1e-9)
    assert res["heat_flux"].shape == (12, 3)
    # Uniform flux q = -k*dT/dx = -50*100 along x.
    np.testing.assert_allclose(
        res["heat_flux"][:, 0], -K * 100.0, rtol=1e-6
    )
    np.testing.assert_allclose(res["heat_flux"][:, 1:], 0.0, atol=1e-6)


def test_study_execute_on_mesh_dirichlet():
    s = _study_with(
        ThermalBoundary(name="T0", boundary_type=ThermalBoundaryType.TEMPERATURE,
                        magnitude=0.0, metadata={"nodes": X0}),
        ThermalBoundary(name="T1", boundary_type=ThermalBoundaryType.TEMPERATURE,
                        magnitude=200.0, metadata={"nodes": X2}),
    )
    res = s.execute_on_mesh(NODES, ELEMENTS)
    assert res.success is True
    assert res.status == "completed"
    assert s.status == StudyStatus.COMPLETED
    T = np.asarray(res.data["temperatures"])
    np.testing.assert_allclose(T[X1], 100.0, rtol=1e-9, atol=1e-9)
    assert "heat_flux" in res.data


# ====================================================================== #
# Neumann: T=0 at x=0, influx q at x=2 -> T(x) = q*x/k
# ====================================================================== #

def test_neumann_bar_matches_analytic_solution():
    q = 1000.0  # W/m^2 inflow on the x=2 face (area = 1 m^2)
    faces = [((8, 10, 11), q), ((8, 11, 9), q)]
    dirichlet = {n: 0.0 for n in X0}
    res = solve_steady_thermal(NODES, ELEMENTS, K, dirichlet, neumann_faces=faces)
    T = res["temperatures"]
    np.testing.assert_allclose(T[X1], q * 1.0 / K, rtol=1e-6)
    np.testing.assert_allclose(T[X2], q * 2.0 / K, rtol=1e-6)


# ====================================================================== #
# Convection sanity: solution bounded between T_fixed and T_inf
# ====================================================================== #

def test_convection_bounded_and_flux_present():
    faces = [((8, 10, 11), 10.0, 20.0), ((8, 11, 9), 10.0, 20.0)]
    dirichlet = {n: 100.0 for n in X0}
    res = solve_steady_thermal(NODES, ELEMENTS, K, dirichlet, convection_faces=faces)
    T = res["temperatures"]
    assert T.min() >= 20.0 - 1e-9
    assert T.max() <= 100.0 + 1e-9
    assert T[X2].mean() < 100.0  # cooling actually happened
    assert res["heat_flux"].shape == (12, 3)


# ====================================================================== #
# Explicit validation failures (no silent fallback)
# ====================================================================== #

def test_no_thermal_material_fails_clearly():
    s = ThermalAnalysis()
    s.model_id = "m1"  # default steel has NO thermal conductivity
    s.add_thermal_boundary(
        ThermalBoundary(boundary_type=ThermalBoundaryType.TEMPERATURE,
                        magnitude=0.0, metadata={"nodes": X0})
    )
    res = s.execute_on_mesh(NODES, ELEMENTS)
    assert res.success is False
    assert res.status == "validation_failed"
    assert "conductividad" in res.error_message
    with pytest.raises(ThermalError, match="conductividad"):
        solve_thermal_study(s, NODES, ELEMENTS)


def test_no_boundaries_fails_clearly():
    s = ThermalAnalysis()
    s.model_id = "m1"
    s.material = _thermal_material()
    res = s.execute_on_mesh(NODES, ELEMENTS)
    assert res.success is False
    assert res.status == "validation_failed"
    assert "condici" in res.error_message


def test_pure_neumann_without_dirichlet_fails_clearly():
    faces = [((8, 10, 11), 1000.0), ((8, 11, 9), 1000.0)]
    with pytest.raises(ThermalError, match="TEMPERATURE"):
        solve_steady_thermal(NODES, ELEMENTS, K, {}, neumann_faces=faces)


def test_cad_selection_without_mesh_mapping_fails_clearly():
    from core.cad_entity import CadEntityRef, EntityType, SelectionSet

    sel = SelectionSet(name="cara")
    sel.add(CadEntityRef(entity_type=EntityType.FACE, face_index=0))
    s = _study_with(
        ThermalBoundary(name="T0", boundary_type=ThermalBoundaryType.TEMPERATURE,
                        magnitude=0.0, metadata={"nodes": X0}),
        ThermalBoundary(name="SinMapeo", boundary_type=ThermalBoundaryType.HEAT_FLUX,
                        magnitude=500.0, selection=sel),
    )
    with pytest.raises(ThermalError, match="metadata\\['faces'\\]"):
        solve_thermal_study(s, NODES, ELEMENTS)


def test_invalid_conductivity_rejected():
    with pytest.raises(ThermalError, match="conductividad"):
        ThermalSolver(NODES, ELEMENTS, 0.0)
    with pytest.raises(ThermalError, match="conductividad"):
        solve_steady_thermal(NODES, ELEMENTS, -5.0, {0: 0.0})
