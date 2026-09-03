"""Validación cross-engine: el MISMO problema físico en motor local y Kratos.

Cierra la sección 6 del prompt (CIERRE DEL MOTOR DUAL FEA): ambos backends deben
ser capaces de resolver el *mismo* caso físicamente válido y el resultado debe
compararse con tolerancias explícitas sin exigir igualdad exacta.

Problema de referencia (malla ``benchmarks/meshes/small_500.npz``):
- soporte: todos los nodos de la base (min Z) fijos;
- carga: 1000 N en +X distribuida uniformemente entre los nodos del plano superior
  (max Z), como cargas puntuales por nodo.

Se construye el problema de forma idéntica en ambos motores:

- Motor local (``core.fea.solve_fea``): ``forces_dofs`` con la misma magnitud por
  nodo y ``fixed_dofs`` de la base.
- Motor Kratos (``KratosAdapter``): las cargas se aplican a los mismos nodos
  superiores y **se materializan como Conditions reales** (``PointLoadCondition3D1N``)
  ⇒ el RHS que ensambla Kratos ya no es vacío.

Comparaciones (tolerancias explícitas, no igualdad exacta):
- norma relativa del campo de desplazamiento ‖u_l − u_k‖/‖u_l‖ ≤ 1e-8;
- compliance dentro de un factor relativo 1e-6;
- energía elemental acumulada finita y consistente entre motores.

El test detecta una regresión real del bridge, de las cargas, de las restricciones
o del ensamblado: si la carga Kratos vuelve a perder el RHS (u=0) o el mapeo de
restricciones cambia, la comparación falla.
"""

import os
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    import importlib.util
    _KRATOS = importlib.util.find_spec("KratosMultiphysics") is not None
except Exception:  # noqa: BLE001
    _KRATOS = False

_MESH = os.path.join(_ROOT, "benchmarks", "meshes", "small_500.npz")

pytestmark = pytest.mark.skipif(
    not _KRATOS or not os.path.exists(_MESH),
    reason="Kratos o malla de referencia no disponibles",
)

# Tolerancias explícitas del cross-engine (métodos numéricos distintos ⇒ no
# exigir igualdad exacta, pero sí que el mismo problema físico coincida).
_DISP_REL_TOL = 1e-8   # ‖u_l − u_k‖/‖u_l‖
_COMPLIANCE_REL_TOL = 1e-6


def _load_mesh():
    data = np.load(_MESH)
    return (np.asarray(data["nodes"], dtype=float),
            np.asarray(data["elements"], dtype=int))


def _solve_local(nodes, elems, top_indices, zmin_indices, per):
    from core.fea import solve_fea
    from core.materials import STANDARD_MATERIALS

    mat = STANDARD_MATERIALS["steel"]
    forces_dofs = [(int(i) * 3 + 0, float(per)) for i in top_indices]
    fixed_dofs = [d for i in zmin_indices for d in (int(i) * 3, int(i) * 3 + 1, int(i) * 3 + 2)]
    result = solve_fea(
        nodes=nodes,
        elements=elems,
        young_modulus=mat.young_modulus,
        poisson_ratio=mat.poisson_ratio,
        forces_dofs=forces_dofs,
        fixed_dofs=fixed_dofs,
    )
    return result


def _solve_kratos(nodes, elems, top_indices, zmin_indices, per):
    import KratosMultiphysics as Kratos

    from core.kratos_adapter import KratosAdapter
    from core.materials import STANDARD_MATERIALS

    adapter = KratosAdapter()
    mp = adapter.create_model_part("CrossEngine")
    adapter.add_nodal_variables(mp)
    adapter.import_mesh_from_core_format(mp, nodes.tolist(), elems.tolist(), "tet4")
    adapter.configure_material_from_core(mp, STANDARD_MATERIALS["steel"])
    adapter.add_displacement_dofs(mp)

    for i in zmin_indices:
        node = mp.Nodes[i + 1]
        node.Fix(Kratos.DISPLACEMENT_X)
        node.Fix(Kratos.DISPLACEMENT_Y)
        node.Fix(Kratos.DISPLACEMENT_Z)

    # Carga real como Conditions (fix del RHS en cero).
    adapter.external_loads[str(mp.Name)] = {
        int(i) + 1: [float(per), 0.0, 0.0] for i in top_indices
    }

    result = adapter.run_analysis(
        mp, {"linear_solver_settings": dict(adapter._DEFAULT_SKYLINE_SETTINGS)}
    )
    return result, mp


@pytest.mark.kratos
def test_cross_engine_same_physical_case_agrees():
    """El mismo caso (soporte + carga) coinciden en local y Kratos."""
    nodes, elems = _load_mesh()
    zmin = float(nodes[:, 2].min())
    zmax = float(nodes[:, 2].max())
    zmin_idx = [i for i in range(len(nodes)) if abs(nodes[i, 2] - zmin) < 1e-6]
    top_idx = [i for i in range(len(nodes)) if abs(nodes[i, 2] - zmax) < 1e-6]

    assert len(zmin_idx) > 0 and len(top_idx) > 0
    per = 1000.0 / len(top_idx)

    local = _solve_local(nodes, elems, top_idx, zmin_idx, per)
    kratos, mp = _solve_kratos(nodes, elems, top_idx, zmin_idx, per)

    assert local["success"] is True
    assert kratos.get("success") is True

    u_l = np.asarray(local["displacements"], dtype=float)
    u_k = np.asarray(kratos["results"]["displacements"], dtype=float)

    # Estructuras compatibles: mismo nº de nodos y un vector por nodo.
    assert u_l.shape == u_k.shape == (len(nodes), 3)
    # El fix: Kratos crea una Condition real por nodo cargado (RHS no vacío).
    assert mp.NumberOfConditions() == len(top_idx)

    # Ningún motor quedó "congelado" (u=0) — ambos resuelven la carga.
    norm_u_k = float(np.linalg.norm(u_k))
    assert norm_u_k > 0.0
    assert float(np.linalg.norm(u_l)) > 0.0

    # Comparación de desplazamientos (norma relativa).
    rel = float(np.linalg.norm(u_l - u_k) / norm_u_k)
    assert rel <= _DISP_REL_TOL, f"desplazamientos divergen: rel={rel:.3e}"

    # Comparación de compliance.
    c_l = float(local["compliance"])
    c_k = float(kratos["results"]["compliance"])
    assert abs(c_l - c_k) / abs(c_l) <= _COMPLIANCE_REL_TOL, (
        f"compliance diverge: local={c_l:.6e} kratos={c_k:.6e}"
    )

    # Energía elemental: ambas finitas y del mismo orden de magnitud.
    e_l = np.asarray(local["element_strain_energy"], dtype=float)
    e_k = np.asarray(kratos["results"]["element_energies"], dtype=float)
    assert np.isfinite(e_l).all() and np.isfinite(e_k).all()
    assert e_l.size == elems.shape[0]
    if e_k.size:
        assert abs(e_k.sum() - e_l.sum()) / e_l.sum() <= _COMPLIANCE_REL_TOL


@pytest.mark.kratos
def test_cross_engine_detects_regression_when_load_rhs_is_zero():
    """Regresión del bridge: si la carga Kratos pierde el RHS (u=0), se detecta.

    Fuerza el defecto histórico aplicando la carga SOLO como variable solution-step
    ``FORCE_*`` (sin materializar Conditions) y comprobando que el campo queda
    congelado, que es exactamente el fallo que la validación cross-engine debe
    prevenir en el flujo normal.
    """
    import KratosMultiphysics as Kratos

    from core.kratos_adapter import KratosAdapter
    from core.materials import STANDARD_MATERIALS

    nodes, elems = _load_mesh()
    zmax = float(nodes[:, 2].max())
    top_idx = [i for i in range(len(nodes)) if abs(nodes[i, 2] - zmax) < 1e-6]

    adapter = KratosAdapter()
    mp = adapter.create_model_part("CrossEngineLegacy")
    adapter.add_nodal_variables(mp)
    adapter.import_mesh_from_core_format(mp, nodes.tolist(), elems.tolist(), "tet4")
    adapter.configure_material_from_core(mp, STANDARD_MATERIALS["steel"])
    adapter.add_displacement_dofs(mp)
    zmin = float(nodes[:, 2].min())
    for i in range(len(nodes)):
        if abs(nodes[i, 2] - zmin) < 1e-6:
            n = mp.Nodes[i + 1]
            n.Fix(Kratos.DISPLACEMENT_X)
            n.Fix(Kratos.DISPLACEMENT_Y)
            n.Fix(Kratos.DISPLACEMENT_Z)

    # Sólo la vía legacy: variables solution-step FORCE_*, SIN Conditions.
    nid = top_idx[0] + 1
    node = mp.Nodes[nid]
    node.SetSolutionStepValue(Kratos.FORCE_X, 0, 1000.0)
    adapter.external_loads[str(mp.Name)] = {nid: [1000.0, 0.0, 0.0]}

    # Al NO crear conditions no debe quedar RHS; el solve es trivial.
    r = adapter._solve_to_results(mp, dict(adapter._DEFAULT_SKYLINE_SETTINGS))
    disp = np.asarray(r["results"]["displacements"], dtype=float)
    assert float(np.max(np.abs(disp))) == pytest.approx(0.0, abs=1e-12)


def _build_kratos_for_surface():
    """ModelPart Kratos preparado (malla + material + DOFs + base fija) para
    aplicar una carga superficial distribuida sobre la cara superior."""
    import KratosMultiphysics as Kratos

    from core.kratos_adapter import KratosAdapter
    from core.materials import STANDARD_MATERIALS

    nodes, elems = _load_mesh()
    adapter = KratosAdapter()
    mp = adapter.create_model_part("CrossEngineSurface")
    adapter.add_nodal_variables(mp)
    adapter.import_mesh_from_core_format(mp, nodes.tolist(), elems.tolist(), "tet4")
    adapter.configure_material_from_core(mp, STANDARD_MATERIALS["steel"])
    adapter.add_displacement_dofs(mp)

    zmin = float(nodes[:, 2].min())
    zmax = float(nodes[:, 2].max())
    base_idx = [i for i in range(len(nodes)) if abs(nodes[i, 2] - zmin) < 1e-6]
    top_idx = [i for i in range(len(nodes)) if abs(nodes[i, 2] - zmax) < 1e-6]
    for i in base_idx:
        node = mp.Nodes[i + 1]
        node.Fix(Kratos.DISPLACEMENT_X)
        node.Fix(Kratos.DISPLACEMENT_Y)
        node.Fix(Kratos.DISPLACEMENT_Z)
    return adapter, mp, nodes, elems, base_idx, top_idx


@pytest.mark.kratos
def test_cross_engine_distributed_surface_load_agrees():
    """Carga superficial distribuida (LoadType.DISTRIBUTED) coinciden en local y Kratos.

    Ejercita el camino real del bridge: ``LoadCondition`` → ``LoadDefinition``
    (siempre ``LoadType.DISTRIBUTED``) → ``apply_load_from_core`` (reparte la
    magnitud TOTAL por nodo) → ``apply_loads_to_model_part`` (materializa cada
    nodo como ``PointLoadCondition3D1N``). La semántica por nodo es la misma que el
    motor local (``mag / len(nodos)``), así que ambos motores deben coincidir.
    """
    from core.study import LoadDefinition, LoadType

    adapter, mp, nodes, elems, base_idx, top_idx = _build_kratos_for_surface()

    total = 2000.0
    per = total / len(top_idx)
    # LoadDefinition DISTRIBUTED (igual que emite el bridge).
    load = LoadDefinition(
        id="surface_load", magnitude=total,
        direction=(1.0, 0.0, 0.0), load_type=LoadType.DISTRIBUTED,
    )
    adapter.apply_load_from_core(mp, load, top_idx)
    # Se materializan condiciones reales (RHS no vacío).
    n_created = adapter.apply_loads_to_model_part(mp)
    kratos = adapter.run_analysis(
        mp, {"linear_solver_settings": dict(adapter._DEFAULT_SKYLINE_SETTINGS)}
    )

    assert kratos.get("success") is True
    assert n_created == len(top_idx)
    assert mp.NumberOfConditions() == len(top_idx)

    u_k = np.asarray(kratos["results"]["displacements"], dtype=float)
    assert float(np.linalg.norm(u_k)) > 0.0

    # Mismo problema en local: misma magnitud TOTAL repartida por nodo.
    from core.fea import solve_fea
    from core.materials import STANDARD_MATERIALS

    mat = STANDARD_MATERIALS["steel"]
    local = solve_fea(
        nodes=nodes,
        elements=elems,
        young_modulus=mat.young_modulus,
        poisson_ratio=mat.poisson_ratio,
        forces_dofs=[(int(i) * 3 + 0, float(per)) for i in top_idx],
        fixed_dofs=[d for i in base_idx for d in (int(i) * 3, int(i) * 3 + 1, int(i) * 3 + 2)],
    )
    u_l = np.asarray(local["displacements"], dtype=float)

    rel = float(np.linalg.norm(u_l - u_k) / np.linalg.norm(u_k))
    assert rel <= _DISP_REL_TOL, f"carga superficial diverge: rel={rel:.3e}"
    c_l = float(local["compliance"])
    c_k = float(kratos["results"]["compliance"])
    assert abs(c_l - c_k) / abs(c_l) <= _COMPLIANCE_REL_TOL


@pytest.mark.kratos
def test_pressure_load_without_area_fails_clearly():
    """LoadType.PRESSURE sin modelo de área falla con error claro, no silencioso.

    El sistema no integra área de superficie: convertir Pa a fuerza (Pa × área)
    requeriría un modelo de área inexistente. Tratar Pa como N sería un error
    físico silencioso; se rechaza con ``ValueError`` (REGLA FUNDAMENTAL).
    """
    from core.study import LoadDefinition, LoadType

    adapter, mp, _nodes, _elems, _base_idx, top_idx = _build_kratos_for_surface()
    load = LoadDefinition(
        id="pressure", magnitude=1e6,
        direction=(0.0, 0.0, -1.0), load_type=LoadType.PRESSURE,
    )
    with pytest.raises(ValueError, match="PRESSURE"):
        adapter.apply_load_from_core(mp, load, top_idx)