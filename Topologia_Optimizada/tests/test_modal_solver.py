"""Tests of the real modal solver (K*phi = w^2*M*phi).

Covers ``core.fea.solve_modal`` (Tet4 lumped mass + eigsh over free DOFs)
and the ``ModalAnalysis.execute_on_mesh`` bridge. No silent fallbacks:
every invalid configuration raises or reports explicitly.
"""

import numpy as np
import pytest

from core.cae_studies import ConstraintCase, ModalAnalysis, ModalParameters
from core.fea import FEAError, solve_modal


def _grid_mesh(nx, ny, nz, lx=1.0, ly=0.2, lz=0.2):
    """Structured (nx,ny,nz)-cell box mesh, each hex split into 6 Tet4.

    Returns (nodes, elements) with 0-based connectivity.
    """
    xs = np.linspace(0.0, lx, nx + 1)
    ys = np.linspace(0.0, ly, ny + 1)
    zs = np.linspace(0.0, lz, nz + 1)
    nid = lambda i, j, k: i * (ny + 1) * (nz + 1) + j * (nz + 1) + k  # noqa: E731
    nodes = np.array([[x, y, z] for x in xs for y in ys for z in zs], dtype=float)
    tets = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                n000 = nid(i, j, k)
                n100 = nid(i + 1, j, k)
                n010 = nid(i, j + 1, k)
                n110 = nid(i + 1, j + 1, k)
                n001 = nid(i, j, k + 1)
                n101 = nid(i + 1, j, k + 1)
                n011 = nid(i, j + 1, k + 1)
                n111 = nid(i + 1, j + 1, k + 1)
                # 6-tet split sharing the n000->n111 diagonal.
                tets += [
                    (n000, n100, n110, n111),
                    (n000, n110, n010, n111),
                    (n000, n010, n011, n111),
                    (n000, n011, n001, n111),
                    (n000, n001, n101, n111),
                    (n000, n101, n100, n111),
                ]
    return nodes, np.asarray(tets, dtype=int)


def _cantilever_dofs(nodes, tol=1e-12):
    """Fix all DOFs of nodes at the x=0 face (cantilever root)."""
    root = [i for i in range(nodes.shape[0]) if abs(nodes[i, 0]) <= tol]
    assert root, "no root nodes found"
    dofs = []
    for ni in root:
        dofs += [ni * 3, ni * 3 + 1, ni * 3 + 2]
    return dofs


STEEL = dict(young_modulus=210e9, poisson_ratio=0.30, density=7850.0)


def test_cantilever_frequencies_positive_and_sorted():
    nodes, elements = _grid_mesh(4, 1, 1)
    res = solve_modal(nodes, elements, mode_count=3,
                      fixed_dofs=_cantilever_dofs(nodes), **STEEL)
    assert res["success"] is True
    freqs = res["frequencies"]
    assert len(freqs) == 3
    assert all(f > 0.0 for f in freqs)
    assert freqs == sorted(freqs)
    assert res["num_free_dofs"] == 3 * nodes.shape[0] - len(_cantilever_dofs(nodes))


def test_mode_shapes_mass_normalized_and_constrained():
    nodes, elements = _grid_mesh(4, 1, 1)
    fixed = _cantilever_dofs(nodes)
    res = solve_modal(nodes, elements, mode_count=3, fixed_dofs=fixed, **STEEL)
    n = nodes.shape[0]
    # Rebuild the lumped-mass diagonal to check M-orthonormality.
    from core.fea import FEASolver
    solver = FEASolver(nodes, elements, STEEL["young_modulus"], STEEL["poisson_ratio"])
    mdiag = np.asarray(solver.assemble_global_mass(STEEL["density"]).diagonal())
    for phi_list in res["mode_shapes"]:
        phi = np.asarray(phi_list)
        assert phi.shape == (3 * n,)
        # Fixed DOFs stay exactly zero.
        assert np.all(phi[fixed] == 0.0)
        # M-normalized: phi^T M phi == 1.
        assert float(np.sum(mdiag * phi * phi)) == pytest.approx(1.0, rel=1e-6)


def test_no_constraints_fails_explicitly():
    nodes, elements = _grid_mesh(2, 1, 1)
    with pytest.raises(FEAError, match="[Cc]onstraint|fixed DOF|rigid"):
        solve_modal(nodes, elements, mode_count=2, fixed_dofs=[], **STEEL)


def test_invalid_mode_count_fails():
    nodes, elements = _grid_mesh(2, 1, 1)
    fixed = _cantilever_dofs(nodes)
    with pytest.raises(FEAError, match="mode_count"):
        solve_modal(nodes, elements, mode_count=0, fixed_dofs=fixed, **STEEL)
    with pytest.raises(FEAError, match="mode_count"):
        solve_modal(nodes, elements, mode_count=-3, fixed_dofs=fixed, **STEEL)


def test_frequency_window_filters_with_warning():
    nodes, elements = _grid_mesh(4, 1, 1)
    fixed = _cantilever_dofs(nodes)
    full = solve_modal(nodes, elements, mode_count=4, fixed_dofs=fixed, **STEEL)
    fmax = full["frequencies"][-1]
    # Narrow window keeping only the first mode.
    fmin = full["frequencies"][0] - 1.0
    fmax_win = 0.5 * (full["frequencies"][0] + full["frequencies"][1])
    assert fmax_win < fmax  # window really excludes modes
    res = solve_modal(nodes, elements, mode_count=4, fixed_dofs=fixed,
                      frequency_min=fmin, frequency_max=fmax_win, **STEEL)
    assert res["num_modes"] == 1
    assert res["num_modes_computed"] == 4
    assert res["warnings"], "excluded modes must be reported explicitly"
    assert all(fmin <= f <= fmax_win for f in res["frequencies"])


def test_study_execute_on_mesh_bridge():
    nodes, elements = _grid_mesh(3, 1, 1)
    s = ModalAnalysis(mode_count=2)
    s.model_id = "m1"
    s.add_constraint(ConstraintCase(name="Root", constraint_type="fixed"))
    assert s.validate() is True
    res = s.execute_on_mesh(nodes, elements, _cantilever_dofs(nodes))
    assert res.success is True
    assert len(res.data["frequencies"]) == 2
    assert all(f > 0.0 for f in res.data["frequencies"])


def test_study_execute_on_mesh_empty_dofs_validation_failed():
    s = ModalAnalysis(mode_count=2)
    s.model_id = "m1"
    s.add_constraint(ConstraintCase(name="Root", constraint_type="fixed"))
    nodes, elements = _grid_mesh(2, 1, 1)
    res = s.execute_on_mesh(nodes, elements, [])
    assert res.success is False
    assert res.status == "validation_failed"
