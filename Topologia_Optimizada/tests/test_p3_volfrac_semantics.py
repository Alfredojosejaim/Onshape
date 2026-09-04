"""P3 validation: definitive volfrac semantics with protected/void regions.

Semantics (decision, see traceback.md "PROBLEMA 3"):
  volfrac = fraction of the ACTIVE (optimizable) subdomain only
            (Option A), V_active = V_total - V_preserved - V_void.
  Protected/halo elements are pinned at rho=1, void at rho_min, neither
  participates in the OC volume constraint. Therefore when protected regions
  exist, the physical (total-mesh) volume fraction is necessarily >= volfrac.
  The solver reports both numbers so the user is not misled.
"""

import numpy as np
import pytest

from core.topopt import SIMPSolver, TopOptError


def _grid(nx=4, ny=2, nz=2):
    """Regular hex grid split into 6 non-degenerate tets per cube. Returned
    mesh is a stable cantilever under the boundary conditions below."""
    nodes = []
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                nodes.append([float(i), float(j), float(k)])
    nodes = np.asarray(nodes, dtype=float)

    def ni(i, j, k):
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    els = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                a = ni(i, j, k); b = ni(i + 1, j, k)
                c = ni(i + 1, j + 1, k); d = ni(i, j + 1, k)
                e = ni(i, j, k + 1); f = ni(i + 1, j, k + 1)
                g = ni(i + 1, j + 1, k + 1); h = ni(i, j + 1, k + 1)
                els.append([a, b, e, c]); els.append([b, f, e, c])
                els.append([e, f, g, c]); els.append([e, g, h, c])
                els.append([a, e, d, c]); els.append([h, e, d, c])
    return nodes, np.asarray(els, dtype=int)


def _solver(volfrac=0.5, **kw):
    nodes, els = _grid()
    return SIMPSolver(nodes, els, 210e9, 0.3, volfrac=volfrac,
                      filter_radius=0.5, **kw)


def _run(solver, iters=10):
    nodes = solver.nodes
    nx, ny, nz = 4, 2, 2
    # Clamp the whole base face (z=0)...
    base = [i * (ny + 1) * (nz + 1) + j * (nz + 1) + 0
            for i in range(nx + 1) for j in range(ny + 1)]
    solver.set_fixed_dofs(np.ravel([[n * 3 + d for d in (0, 1, 2)] for n in base]))
    # ...and pull down on the whole top face (z=nz): stable cantilever.
    f = np.zeros(solver.fea.num_dofs)
    top = [i * (ny + 1) * (nz + 1) + j * (nz + 1) + nz
           for i in range(nx + 1) for j in range(ny + 1)]
    for n in top:
        f[n * 3 + 2] = -100.0
    solver.set_load(f)
    return solver.optimize(max_iterations=iters)


# ------------------------------------------------------------------ #
# 1. No protected/void: physical fraction == active fraction == volfrac.
# ------------------------------------------------------------------ #
def test_no_protected_regions_physical_eq_active():
    r = _run(_solver(volfrac=0.5))
    assert r["final_volume_fraction"] == pytest.approx(0.5, abs=1e-3)
    assert r["physical_volume_fraction"] == pytest.approx(
        r["final_volume_fraction"], abs=1e-9
    ), "sin regiones protegidas, fisica total == fraccion activa"


# ------------------------------------------------------------------ #
# 2. With a protected subset: physical fraction > volfrac, exactly the
#    closed-form value, while the ACTIVE fraction still meets volfrac.
# ------------------------------------------------------------------ #
def test_protected_region_raises_physical_fraction():
    s = _solver(volfrac=0.4)
    vols = s._volumes
    s.set_preserved_elements([0, 1, 2, 3])
    v_p = float(vols[[0, 1, 2, 3]].sum())
    v_t = float(vols.sum())
    v_active = v_t - v_p
    r = _run(s)
    # Active subdomain still honours volfrac...
    assert r["final_volume_fraction"] == pytest.approx(0.4, abs=1e-3)
    # ...but the physical total is strictly above volfrac and matches the
    # closed form: preserved at rho=1 + volfrac of the free active domain.
    expected_physical = (v_p + 0.4 * v_active) / v_t
    assert r["physical_volume_fraction"] == pytest.approx(expected_physical, abs=1e-6)
    assert r["physical_volume_fraction"] > 0.4
    assert r["physical_volume_fraction"] > r["final_volume_fraction"]


# ------------------------------------------------------------------ #
# 3. Preserved elements stay pinned at rho=1 in the result.
# ------------------------------------------------------------------ #
def test_preserved_stays_at_full_density_in_result():
    s = _solver(volfrac=0.5)
    s.set_preserved_elements([5, 6, 7])
    r = _run(s)
    x = np.asarray(r["densities"])
    assert np.all(x[[5, 6, 7]] == 1.0), "preserved elements must keep rho=1"
    mask = np.asarray(r["preserved_elements"], dtype=bool)
    assert np.nonzero(mask)[0].tolist() == [5, 6, 7]


# ------------------------------------------------------------------ #
# 4. Void elements stay pinned at rho_min in the result.
# ------------------------------------------------------------------ #
def test_void_stays_at_minimum_density_in_result():
    s = _solver(volfrac=0.5)
    s.set_void_elements([9, 10])
    r = _run(s)
    x = np.asarray(r["densities"])
    assert np.allclose(x[[9, 10]], s.rho_min), "void elements must stay at rho_min"


# ------------------------------------------------------------------ #
# 5. Infeasible volfrac (below the rho_min floor) is rejected loudly.
# ------------------------------------------------------------------ #
def test_infeasible_volfrac_raises():
    s = _solver(volfrac=0.5)
    n = s.num_elements
    s.set_preserved_elements(list(range(1, n)))  # active domain ~ 1 element
    s.volfrac = 1e-9  # target << rho_min * V_active
    with pytest.raises(TopOptError):
        s._finalize_active()


# ------------------------------------------------------------------ #
# 6. The constraint targets the ACTIVE domain; the physical total only
#    reports (>=) it. This is the documented semantics.
# ------------------------------------------------------------------ #
def test_volfrac_constrains_active_not_total():
    s = _solver(volfrac=0.3)
    s.set_preserved_elements([0, 1, 2, 3])  # a protected subset
    r = _run(s)
    assert r["final_volume_fraction"] == pytest.approx(0.3, abs=1e-3)
    assert r["physical_volume_fraction"] >= r["final_volume_fraction"] - 1e-9
    assert r["physical_volume_fraction"] >= 0.3