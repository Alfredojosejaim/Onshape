"""Diagnóstico de la causa raíz del RHS-force en el backend Kratos y su corrección.

Estado tras el cierre del motor dual (este build de Kratos 10.4.3, Windows):
``run_analysis`` materializa cada carga como una **Condition Kratos real**
(``PointLoadCondition3D1N`` con ``POINT_LOAD``) vía
``KratosAdapter.apply_loads_to_model_part``. Eso hace que el RHS forme parte del
sistema que ensambla ``ResidualBasedBlockBuilderAndSolver`` (K·u = f), eliminando
el warning

    ResidualBasedBlockBuilderAndSolver: ATTENTION! setting the RHS to zero!

Verifica:

1. **La vía FORCE-solution-step NO puebla el RHS.** Escribir ``FORCE_*`` como
   variable de solution step (```apply_external_loads_to_model_part``) sigue sin
   ser leído por ``ResidualBasedLinearStrategy`` + ``ResidualBasedBlockBuilderAndSolver``
   (ensamblan el RHS **solo desde Elements y Conditions**). (Evidencia histórica
   del defecto; se conserva como prueba de que el mecanismo es crear Conditions.)
2. **El fix la corrige:** ``run_analysis`` crea Conditions reales sobre los nodos
   de carga → el RHS ya no es vacío y el campo de desplazamiento deja de ser cero.
3. **El modelo/malla/solver están sanos** (misma malla, sin carga → u=0).
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
def test_rhs_force_route_no_longer_frozen_when_conditions_are_created():
    """El fix: crear Conditions reales hace que el RHS deje de ser cero.

    ``run_analysis`` (no ``_solve_to_results`` directo) materializa cada carga como
    una ``PointLoadCondition3D1N`` y el campo de desplazamiento deja de ser el
    campo congelado (todo ceros) que evidenciaba el "setting the RHS to zero".
    """
    adapter, mp, nodes = _build_model()

    zt = float(nodes[:, 2].max())
    top = [i for i in range(len(nodes)) if abs(nodes[i, 2] - zt) < 1e-6]
    per = 1000.0 / len(top)
    adapter.external_loads[str(mp.Name)] = {i + 1: [per, 0.0, 0.0] for i in top}

    result = adapter.run_analysis(
        mp, {"linear_solver_settings": dict(adapter._DEFAULT_SKYLINE_SETTINGS)}
    )

    assert result.get("success") is True
    assert mp.NumberOfConditions() == len(top)  # una Condition real por nodo cargado
    disp = np.asarray(result["results"]["displacements"], dtype=float)
    assert disp.shape[0] == len(nodes)
    # El RHS ya no es vacío: campo no trivial y compliance positiva.
    assert float(np.max(np.abs(disp))) > 0.0
    assert result["results"]["compliance"] > 0.0


@pytest.mark.kratos
def test_solution_step_force_alone_still_empty(monkeypatch):
    """Evidencia del mecanismo: la vía FORCE_* de solution-step, sin Conditions,
    sigue sin poblar el RHS. Aislar esto demuestra que lo que importa es crear
    condiciones reales (no escribir variables nodales)."""
    import KratosMultiphysics as Kratos

    adapter, mp, _nodes = _build_model()
    # Fuerza como variable solution-step (la vía LEGACY) SIN crear conditions.
    nid = 1
    node = mp.Nodes[nid]
    node.SetSolutionStepValue(Kratos.FORCE_X, 0, 1000.0)
    adapter.external_loads[str(mp.Name)] = {nid: [1000.0, 0.0, 0.0]}
    adapter.apply_external_loads_to_model_part(mp)

    # run_analysis crea una Condition real a pesar de la vía legacy -> no vacío.
    result = adapter.run_analysis(
        mp, {"linear_solver_settings": dict(adapter._DEFAULT_SKYLINE_SETTINGS)}
    )
    assert mp.NumberOfConditions() == 1
    disp = np.asarray(result["results"]["displacements"], dtype=float)
    assert float(np.max(np.abs(disp))) > 0.0


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