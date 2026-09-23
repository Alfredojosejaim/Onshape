"""UNITS-MM: el material esta en SI (Pa, kg/m^3) pero el solver de malla
trabaja en mm (N/mm^2, tonne/mm^3).

Regresion del "Complimiento: 0.0 mJ" (19-sep-2026): se pasaba E=210e9 Pa crudo
al FEASolver con coordenadas en mm, dejando la estructura 1e6 veces mas rigida
(compliance y sensibilidades ~1e-6 de lo real). Eso empujaba el OC a los pisos
numericos y colapsaba el diseno. El material debe convertirse al construir el
solver (core.materials.young_modulus_mm / density_mm).
"""

import itertools

import numpy as np
import pytest

from core.materials import STANDARD_MATERIALS, young_modulus_mm, density_mm
from core.topopt import SIMPSolver

E_TEST = 210e3  # N/mm^2 (sistema mm-N)


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


def _bc(nodes, nid):
    fixed = []
    for j in range(2):
        for k in range(2):
            n0 = nid[(0, j, k)]
            fixed += [n0 * 3, n0 * 3 + 1, n0 * 3 + 2]
    f = np.zeros(len(nodes) * 3)
    for j in range(2):
        for k in range(2):
            f[nid[(4, j, k)] * 3 + 1] = -50.0
    return f, np.array(fixed, dtype=int)


def _compliance(young):
    nodes, els, nid = kuhn_bar(4)
    s = SIMPSolver(nodes=nodes, elements=els, young_modulus=young,
                   poisson_ratio=0.3, volfrac=0.4, filter_radius=0.6)
    f, fixed = _bc(nodes, nid)
    s.set_load(f)
    s.set_fixed_dofs(fixed)
    return s.optimize(max_iterations=1, tolerance=1e-9)["final_compliance"]


def test_factores_de_conversion():
    steel = STANDARD_MATERIALS["steel"]
    assert young_modulus_mm(steel.young_modulus) == pytest.approx(210e3)
    assert density_mm(7850.0) == pytest.approx(7.85e-9)
    assert density_mm(steel.density) == pytest.approx(7.85e-9)


def test_solver_trabaja_en_mm_no_en_pa():
    """Con E en Pa crudo la compliance sale 1e6 veces menor (el bug)."""
    c_pa = _compliance(210e9)
    c_mm = _compliance(E_TEST)
    assert c_mm / c_pa == pytest.approx(1e6, rel=1e-6)
    # valor fisico esperable para 50 N sobre esta barra: O(100) mJ
    assert c_mm > 1.0


def test_kratos_recibe_material_en_mm():
    """FASE-3: configure_material_from_core convierte SI->mm (malla en mm).

    Kratos es unitariamente consistente: con nodos en mm, E va en N/mm^2 y
    rho en tonne/mm^3. Pasar SI crudo dejaba la rigidez x1e6 (mismo bug que
    el motor local). Requiere Kratos instalado; si no, se salta.
    """
    Kratos = pytest.importorskip("KratosMultiphysics")
    from KratosMultiphysics import StructuralMechanicsApplication as SMA
    from core.kratos_adapter import KratosAdapter

    steel = STANDARD_MATERIALS["steel"]
    adapter = KratosAdapter()
    mp = adapter.create_model_part("UnitsMM")
    adapter.add_nodal_variables(mp)
    for i, p in enumerate([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]):
        mp.CreateNewNode(i + 1, *p)
    # un Tet4 para que configure_material_from_core tenga donde colgar props
    tmp = Kratos.Properties(999)
    tmp.SetValue(Kratos.CONSTITUTIVE_LAW, SMA.LinearElastic3DLaw())
    mp.CreateNewElement("SmallDisplacementElement3D4N", 1, [1, 2, 3, 4], tmp)
    adapter.configure_material_from_core(mp, steel)
    got = mp.Elements[1].Properties
    assert got[Kratos.YOUNG_MODULUS] == pytest.approx(210e3)
    assert got[Kratos.DENSITY] == pytest.approx(7.85e-9)


def test_motor_generativo_convierte_el_material():
    """GenerativeDesignEngine pasa el E del material ya en N/mm^2 al solver."""
    from core.generative_engine import GenerativeDesignEngine

    nodes, els, nid = kuhn_bar(4)
    engine = GenerativeDesignEngine(
        model_id=None, mesh_nodes=nodes, mesh_elements=els,
        material=STANDARD_MATERIALS["steel"])
    f, fixed = _bc(nodes, nid)
    result = engine.solve_simp(
        {}, legacy_force=f, legacy_fixed_dofs=fixed,
        volume_fraction=0.4, max_iterations=1, tolerance=1e-9,
        penalization=3.0, filter_radius=0.6, halo_radius=None)
    comp = float(result["final_compliance"])
    assert np.isfinite(comp)
    # con unidades correctas es O(1e2) mJ, no 1e-4 (Pa crudo)
    assert comp > 1.0
    assert comp == pytest.approx(_compliance(E_TEST), rel=1e-3)