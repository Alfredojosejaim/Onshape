"""Iterative local solver (CG) + numeric Kratos-migration threshold (Fase 3c, D4).

Default stays "direct" (spsolve, unchanged). "cg" must agree with direct
within tolerance and report diagnostics; the Kratos suggestion threshold is
numeric (elements / seconds), not subjective.
"""

import numpy as np


def _hex_grid(nx=2, ny=1, nz=1):
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


def _cantilever():
    from core.materials import STANDARD_MATERIALS
    nodes, elems = _hex_grid()
    mat = STANDARD_MATERIALS["steel"]
    base = np.nonzero(np.isclose(nodes[:, 0], 0.0))[0]
    top = np.nonzero(nodes[:, 0] == nodes[:, 0].max())[0]
    fixed = [int(i) * 3 + d for i in base for d in (0, 1, 2)]
    forces = [(int(i) * 3 + 2, -100.0) for i in top]
    return nodes, elems, mat, forces, fixed


def test_default_solver_unchanged_direct():
    from core.fea import solve_fea
    nodes, elems, mat, forces, fixed = _cantilever()
    r = solve_fea(nodes, elems, mat.young_modulus, mat.poisson_ratio, forces, fixed)
    assert r["linear_solver"] == "direct"
    assert r["solver_fallback"] is False
    assert r["kratos_suggestion"] is None
    assert r["compliance"] > 0.0


def test_cg_agrees_with_direct():
    from core.fea import solve_fea
    nodes, elems, mat, forces, fixed = _cantilever()
    kw = dict(young_modulus=mat.young_modulus, poisson_ratio=mat.poisson_ratio)
    r_d = solve_fea(nodes, elems, forces_dofs=forces, fixed_dofs=fixed, **kw)
    r_c = solve_fea(nodes, elems, forces_dofs=forces, fixed_dofs=fixed,
                    linear_solver="cg", **kw)
    assert r_c["linear_solver"] == "cg"
    assert r_c["solver_fallback"] is False
    assert r_c["cg_iterations"] > 0
    u_d = np.asarray(r_d["displacements"])
    u_c = np.asarray(r_c["displacements"])
    rel = np.linalg.norm(u_d - u_c) / np.linalg.norm(u_d)
    assert rel <= 1e-6
    assert abs(r_d["compliance"] - r_c["compliance"]) / abs(r_d["compliance"]) <= 1e-6


def test_cg_falls_back_explicitly_on_nonconvergence():
    from core.fea import FEASolver
    from core.materials import STANDARD_MATERIALS
    nodes, elems, mat, forces, fixed = _cantilever()
    solver = FEASolver(nodes, elems, mat.young_modulus, mat.poisson_ratio,
                       linear_solver="cg", cg_tol=1e-16, cg_maxiter=1)
    F = np.zeros(solver.num_dofs)
    for dof, val in forces:
        F[dof] += val
    u = solver.apply_bc_and_solve(F, np.sort(np.asarray(fixed)))
    assert solver.solver_fallback is True
    assert solver.linear_solver_used == "direct"
    assert np.linalg.norm(u) > 0.0


def test_kratos_threshold_is_numeric():
    from core.fea import kratos_suggestion, FEASolver
    assert kratos_suggestion(100, 0.5) is None
    assert kratos_suggestion(FEASolver.KRATOS_SUGGEST_MIN_ELEMENTS, 0.1) is not None
    assert kratos_suggestion(100, FEASolver.KRATOS_SUGGEST_MIN_SECONDS) is not None
