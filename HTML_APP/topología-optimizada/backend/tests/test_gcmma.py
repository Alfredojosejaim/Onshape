"""Tests Fase 6 (GCMMA Svanberg 2002, solo núcleo).

- Smoke en malla mínima (2 tets): corre, finito, volumen en rango,
  historial con inner_iters + bandera inner_capped explícita.
- Benchmark barra Kuhn 4x1x1 (24 tets, cantilever): volumen exacto,
  mejora monótona vs iteración 1, compliance en rango MMA (estilo
  Fase 4: MMA 0.7506 vs OC 0.7856 en cantilever 30 iters).
- Vendored congelado (Fase 4.5b): optimizer="gcmma" falla explícito.
"""

import itertools

import numpy as np
import pytest

from core.topopt import SIMPSolver, TopOptError

E = 210e3
NU = 0.3


def kuhn_bar(nx=4):
    """Barra nx*1x1 con triangulación de Kuhn (conforme, 6 tets/cubo)."""
    nid, nodes = {}, []
    for i in range(nx + 1):
        for j in range(2):
            for k in range(2):
                nid[(i, j, k)] = len(nodes)
                nodes.append([float(i), float(j), float(k)])
    nodes = np.array(nodes)
    els = []
    for i in range(nx):
        for perm in itertools.permutations([0, 1, 2]):
            p1 = [0, 0, 0]
            p1[perm[0]] = 1
            p2 = list(p1)
            p2[perm[1]] = 1
            els.append([nid[(i + a, b, c)]
                        for (a, b, c) in [(0, 0, 0), tuple(p1), tuple(p2), (1, 1, 1)]])
    return nodes, np.array(els), nid


def _cantilever(nx=4, volfrac=0.4):
    nodes, els, nid = kuhn_bar(nx)
    fixed = []
    for j in range(2):
        for k in range(2):
            n0 = nid[(0, j, k)]
            fixed += [n0 * 3, n0 * 3 + 1, n0 * 3 + 2]
    f = np.zeros(len(nodes) * 3)
    for j in range(2):
        for k in range(2):
            f[nid[(nx, j, k)] * 3 + 1] = -50.0
    s = SIMPSolver(nodes=nodes, elements=els, young_modulus=E,
                   poisson_ratio=NU, volfrac=volfrac, filter_radius=0.6)
    s.set_load(f)
    s.set_fixed_dofs(np.array(fixed, dtype=int))
    return s


def _tiny():
    nodes = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 1.0, 1.0]])
    els = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])
    s = SIMPSolver(nodes=nodes, elements=els, young_modulus=E,
                   poisson_ratio=NU, volfrac=0.5, filter_radius=0.5)
    f = np.zeros(15)
    f[13] = -100.0
    s.set_load(f)
    s.set_fixed_dofs(np.arange(9))
    return s


def test_gcmma_smoke():
    r = _tiny().optimize(max_iterations=3, optimizer="gcmma")
    x = np.asarray(r["densities"], dtype=float)
    assert np.all(np.isfinite(x)) and np.all((x >= 0.0) & (x <= 1.0))
    assert 0.0 < r["final_volume_fraction"] <= 1.0
    assert len(r["gcmma_inner_iters"]) == r["iterations"]
    assert all(isinstance(v, int) and v >= 0 for v in r["gcmma_inner_iters"])
    assert isinstance(r["gcmma_inner_capped"], bool)


def test_gcmma_benchmark_vs_mma_oc():
    results = {}
    for opt in ("oc", "mma", "gcmma"):
        r = _cantilever().optimize(max_iterations=10, optimizer=opt)
        results[opt] = r
        assert r["final_volume_fraction"] == pytest.approx(0.4, abs=5e-3), opt
        hist = r["compliance_history"]
        assert hist[-1] < hist[0], opt  # mejora real
    cg, cm, co = (results[o]["final_compliance"] for o in ("gcmma", "mma", "oc"))
    print(f"\nbenchmark Kuhn 24 tets: OC={co:.4g} MMA={cm:.4g} GCMMA={cg:.4g}")
    assert cg <= co  # GCMMA supera a OC en este caso
    assert cg <= cm * 1.25  # en rango MMA (medido: ~1.11x)


def test_gcmma_vendored_rejects():
    from vendored.simp import SIMPSolver as VendoredSIMP
    from vendored.simp import TopOptError as VendoredTopOptError
    nodes = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0], [1.0, 1.0, 1.0]])
    els = np.array([[0, 1, 2, 3], [1, 2, 3, 4]])
    s = VendoredSIMP(nodes=nodes, elements=els, young_modulus=E, poisson_ratio=NU)
    with pytest.raises(VendoredTopOptError):
        s.optimize(max_iterations=2, optimizer="gcmma")


def test_core_still_rejects_bogus():
    with pytest.raises(TopOptError):
        _tiny().optimize(max_iterations=2, optimizer="bogus")
