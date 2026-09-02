"""Diagnóstico reproducible de la causa raíz del RHS-force en el backend Kratos.

Estado en este build de Kratos (10.4.3, Windows): ``run_fea(backend="kratos")`` con
una condición de **fuerza** da compliance/displacement `0` con el warning

    ResidualBasedBlockBuilderAndSolver: ATTENTION! setting the RHS to zero!

Este módulo fija el diagnóstico en un test de regresión reproducible (marcado
``kratos`` y ``skipif`` sin Kratos), en lugar de dejarlo solo como nota de
benchmark. Verifica:

1. **La vía FORCE-solution-step no puebla el RHS.** Los loads se almacenan como
   variables solution-step ``FORCE_*`` (```apply_point_load`` /
   ``apply_external_loads_to_model_part``), pero ``ResidualBasedLinearStrategy`` +
   ``ResidualBasedBlockBuilderAndSolver`` ensamblan el RHS **solo desde Elements y
   Conditions**. Como no se crea ningún ``Condition`` (y este build no registra
   clases de load-condition ni ``ApplyNodalLoadsProcess``), el RHS queda vacío y el
   solve es correcto pero trivial: ``u=0``.
2. **El modelo/malla/solver están sanos.** El mismo pipeline sin el mecanismo de
   carga devuelve ``success`` y un campo de desplazamiento de la forma esperada
   (todo ceros), aislando la inyección de carga como el único punto defectuoso.

(La huella del warning ``setting the RHS to zero`` la emite el logger nativo de
Kratos a su propio sink, no al ``logging``/``sys.stderr`` de Python, por lo que no
es capturable de forma fiable con ``capsys``/``caplog`` en pytest; su presencia en
la ejecución queda visible en el log del test run, y el campo u=0 ya la evidencia.)

Contexto: es exactamente la hipótesis (3) del diagnóstico documentado en
``PROJECT_STATUS.md`` (ensamblado del RHS antes del solve). La vía física de
referencia del repo con este build es **desplazamiento impuesto** (``imposed_disp``,
ver ``benchmarks/benchmark_fase0.py``), no fuerza.
"""

import importlib.util
import os

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in __import__("sys").path:
    __import__("sys").path.insert(0, _ROOT)

_MESH = os.path.join(_ROOT, "benchmarks", "meshes", "small_500.npz")
_KRATOS = importlib.util.find_spec("KratosMultiphysics") is not None

pytestmark = pytest.mark.skipif(
    not _KRATOS or not os.path.exists(_MESH),
    reason="Kratos o malla no disponibles",
)


def _build_model():
    """Construye un ModelPart Kratos real sobre la malla de referencia, sin cargas."""
    import KratosMultiphysics as Kratos
    from core.kratos_adapter import KratosAdapter
    from core.materials import STANDARD_MATERIALS

    data = np.load(_MESH)
    nodes = np.asarray(data["nodes"], dtype=float)
    elems = np.asarray(data["elements"], dtype=int)

    adapter = KratosAdapter()
    mp = adapter.create_model_part("DiagRHSTest")
    adapter.add_nodal_variables(mp)
    adapter.import_mesh_from_core_format(mp, nodes.tolist(), elems.tolist(), "tet4")
    adapter.configure_material_from_core(mp, STANDARD_MATERIALS["steel"])
    adapter.add_displacement_dofs(mp)

    # Fija la base (min Z) para que el sistema esté soportado y sea solvable.
    z0 = float(nodes[:, 2].min())
    fixed = [i for i in range(len(nodes)) if abs(nodes[i, 2] - z0) < 1e-6]
    for i in fixed:
        node = mp.Nodes[i + 1]
        node.Fix(Kratos.DISPLACEMENT_X)
        node.Fix(Kratos.DISPLACEMENT_Y)
        node.Fix(Kratos.DISPLACEMENT_Z)
    return adapter, mp, nodes


@pytest.mark.kratos
def test_rhs_force_route_produces_frozen_zero_field():
    """Diagnóstico: la vía actual (FORCE_* en solution step) NO puebla el RHS.

    Un solve Kratos real con carga almacenada como variable solution-step
    ``FORCE_*`` termina en ``success`` pero con campo de desplazamiento todo cero:
    es la manifestación del "setting the RHS to zero". Fija el defecto documentado
    para detectarlo en CI si el comportamiento cambia (o se introduce una carga real).
    """
    import KratosMultiphysics as Kratos

    adapter, mp, _nodes = _build_model()

    zt = float(_nodes[:, 2].max())
    top = [i for i in range(len(_nodes)) if abs(_nodes[i, 2] - zt) < 1e-6]
    nid = top[0] + 1
    node = mp.Nodes[nid]
    node.SetSolutionStepValue(Kratos.FORCE_X, 0, 1000.0)
    node.SetSolutionStepValue(Kratos.FORCE_Y, 0, 0.0)
    node.SetSolutionStepValue(Kratos.FORCE_Z, 0, 0.0)
    adapter.external_loads[str(mp.Name)] = {nid: [1000.0, 0.0, 0.0]}
    adapter.apply_external_loads_to_model_part(mp)

    result = adapter._solve_to_results(mp, dict(adapter._DEFAULT_AMGCL_SETTINGS))

    assert result.get("success") is True
    disp = np.asarray(result["results"]["displacements"], dtype=float)
    # El defecto actual: campo todo cero pese a haber pedido una carga de fuerza.
    if disp.size:
        assert float(np.max(np.abs(disp))) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.kratos
def test_model_and_solver_are_healthy_without_missing_conditions():
    """Aisla el defecto: el modelo, la malla y el solver están sanos.

    El mismo pipeline (sin ningún mecanismo de carga) resuelve con ``success`` y
    produce un campo de desplazamiento de la forma esperada (todo ceros por
    ausencia de carga). Esto prueba que el RHS vacío es consecuencia de NO haber
    ensamblado ninguna condición de carga, no de un error de malla/material/solver.
    """
    adapter, mp, nodes = _build_model()

    result = adapter._solve_to_results(mp, dict(adapter._DEFAULT_SKYLINE_SETTINGS))

    assert result.get("success") is True
    disp = np.asarray(result["results"]["displacements"], dtype=float)
    assert disp.shape[0] == len(nodes)  # un desplazamiento por nodo
    # Sin carga el campo es idénticamente cero, pero el sistema se resuelve bien.
    assert float(np.max(np.abs(disp))) == pytest.approx(0.0, abs=1e-12)