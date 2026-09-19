"""VOLFRAC-MODE: volfrac sobre el dominio activo vs el volumen total.

Regresion del reporte del usuario (19-sep-2026): marca 35% y espera que quede
el 35% del volumen de la pieza, pero con regiones preservadas/keep-out el modo
historico 'active_domain' deja mas material que el pedido (el OC solo controla
V_active y lo preservado se suma). 'total_volume' descuenta lo fijado para que
el volumen fisico TOTAL coincida con volfrac.
"""

import itertools

import numpy as np
import pytest

from core.topopt import SIMPSolver, TopOptError

E = 210e3
NU = 0.3


def kuhn_bar(nx=4):
    """Barra nx*1x1 con triangulacion de Kuhn (6 tets/cubo, volumen uniforme)."""
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


def _cantilever(volfrac, mode, preserve_frac=0.25):
    nodes, els, nid = kuhn_bar(4)
    s = SIMPSolver(nodes=nodes, elements=els, young_modulus=E, poisson_ratio=NU,
                   volfrac=volfrac, filter_radius=0.6, volfrac_mode=mode)
    fixed = []
    for j in range(2):
        for k in range(2):
            n0 = nid[(0, j, k)]
            fixed += [n0 * 3, n0 * 3 + 1, n0 * 3 + 2]
    f = np.zeros(len(nodes) * 3)
    for j in range(2):
        for k in range(2):
            f[nid[(4, j, k)] * 3 + 1] = -50.0
    s.set_load(f)
    s.set_fixed_dofs(np.array(fixed, dtype=int))
    n_pres = int(round(preserve_frac * s.num_elements))
    s.set_preserved_elements(np.arange(s.num_elements - n_pres, s.num_elements))
    return s


def test_volfrac_mode_invalido_falla_explicito():
    nodes, els, _ = kuhn_bar(4)
    with pytest.raises(TopOptError):
        SIMPSolver(nodes=nodes, elements=els, young_modulus=E, poisson_ratio=NU,
                   volfrac=0.4, filter_radius=0.6, volfrac_mode="bogus")


def test_active_domain_deja_mas_material_que_el_pedido():
    volfrac = 0.4
    s = _cantilever(volfrac, "active_domain")
    p = s._preserved_volume() / s._vol0  # fraccion preservada (~0.25)
    r = s.optimize(max_iterations=12, tolerance=1e-5)
    assert r["volfrac_mode"] == "active_domain"
    # el activo si respeta volfrac...
    assert r["final_volume_fraction"] == pytest.approx(volfrac, abs=0.02)
    # ...pero el fisico TOTAL queda por encima (preservado + volfrac*activo)
    assert r["physical_volume_fraction"] == pytest.approx(
        p + volfrac * (1.0 - p), abs=0.03)
    assert r["physical_volume_fraction"] > volfrac + 0.05


def test_total_volume_respeta_el_volumen_de_la_pieza():
    volfrac = 0.4
    s = _cantilever(volfrac, "total_volume")
    p = s._preserved_volume() / s._vol0
    r = s.optimize(max_iterations=12, tolerance=1e-5)
    assert r["volfrac_mode"] == "total_volume"
    # el fisico TOTAL (preservado + activo) queda en el 40% pedido
    assert r["physical_volume_fraction"] == pytest.approx(volfrac, abs=0.03)
    # el activo solo aporta volfrac - preservado, normalizado sobre V_active
    activo_esperado = (volfrac - p) / (1.0 - p)
    assert r["target_active_volume_fraction"] == pytest.approx(activo_esperado, abs=0.02)
    assert r["final_volume_fraction"] == pytest.approx(activo_esperado, abs=0.03)


def test_total_volume_infeasible_si_volfrac_menor_que_preservado():
    nodes, els, _ = kuhn_bar(4)
    s = SIMPSolver(nodes=nodes, elements=els, young_modulus=E, poisson_ratio=NU,
                   volfrac=0.1, filter_radius=0.6, volfrac_mode="total_volume")
    n_pres = int(round(0.4 * s.num_elements))
    with pytest.raises(TopOptError):
        s.set_preserved_elements(np.arange(s.num_elements - n_pres, s.num_elements))