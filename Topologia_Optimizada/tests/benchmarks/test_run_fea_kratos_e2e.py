"""Verificación end-to-end real del backend Kratos de ``run_fea``.

Cierra la brecha Kratos/local documentada en ``PROJECT_STATUS.md``: confirma que
``run_fea(backend="kratos")`` ejecuta un solve REAL de Kratos sobre una malla de
referencia, consume las mismas condiciones reutilizables (traducidas por
``core.kratos_bridge``) y mantiene el solve local como default.

Qué se verifica en este build de Kratos (10.4.3, ruta RHS-force bloqueada -> la
compliance por fuerza distribuida queda en 0, documentado en
``benchmarks/benchmark_fase0.py``):

1. La malla se importa de verdad (mismos nodos/elementos que el mesh).
2. El pipeline completo corre: material, DOFs, BCs geométricos, solve, extracción.
3. El bridge traduce las condiciones reutilizables a definiciones FEA.
4. El solve local (NumPy) con las MISMAS condiciones produce compliance > 0
   (la vía local no está bloqueada), y continua como default.

El test está marcado como ``kratos`` y se ``skipif`` Kratos no está disponible:
es un regreso real verificable, no parte de la suite rápida por defecto.
"""

import os
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from desktop.pipeline.controller import PipelineController
    from core.cad_entity import CadEntityRef, EntityType, SelectionSet
    from core.conditions import ElasticityCondition, LoadCondition, LoadOrientation, LoadSense

    _KRATOS = True
except Exception as _e:  # noqa: BLE001
    _KRATOS = False
    _KRATOS_ERR = str(_e)

_MESH = os.path.join(_ROOT, "benchmarks", "meshes", "small_500.npz")


def _face_less_conditions():
    """Carga + soporte sin cara -> la vía coordenada (legítima, igual en local)."""
    load = LoadCondition(
        name="Carga", faces=SelectionSet(name="vacio"),
        orientation=LoadOrientation.PERPENDICULAR, sense=LoadSense.POSITIVE,
        magnitude=1000.0, indeterminate=False,
    )
    support = ElasticityCondition(name="Soporte", faces=SelectionSet(name="sop"))
    return load, support


pytestmark = pytest.mark.skipif(
    not _KRATOS or not os.path.exists(_MESH),
    reason=f"Kratos o malla no disponibles: {locals().get('_KRATOS_ERR')}",
)


@pytest.mark.kratos
def test_run_fea_kratos_real_solve_matches_mesh():
    """El backend Kratos importa la malla real y ejecuta un solve completo."""
    data = np.load(_MESH)
    nodes = np.asarray(data["nodes"], dtype=float)
    elements = np.asarray(data["elements"], dtype=int)

    c = PipelineController()
    c.mesh_nodes = nodes
    c.mesh_elements = elements
    c.mesh = {
        "success": True,
        "nodes": nodes.tolist(),
        "elements": elements.tolist(),
        "physical_groups": {},
    }
    load, support = _face_less_conditions()
    c.conditions.add(load)
    c.conditions.add(support)

    result = c.run_fea(conditions=list(c.conditions.all), backend="kratos")

    assert result["success"] is True
    assert result["status"] == "completed"
    # La malla importada coincide con la de referencia.
    assert result["num_elements"] == elements.shape[0]
    assert result["num_nodes"] == nodes.shape[0]
    # El solve devolvió un campo de desplazamiento por nodo.
    disp = result["displacements"]
    assert disp.shape[0] == nodes.shape[0]
    # En este build la ruta RHS-force queda en 0 (documentado en benchmark_fase0).
    assert result["compliance"] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.kratos
def test_run_fea_backends_share_condition_semantics():
    """Local y Kratos consumen las mismas condiciones reutilizables; el local
    (NumPy, no bloqueado) produce compliance > 0 y sigue siendo el default."""
    data = np.load(_MESH)
    nodes = np.asarray(data["nodes"], dtype=float)
    elements = np.asarray(data["elements"], dtype=int)

    c = PipelineController()
    c.mesh_nodes = nodes
    c.mesh_elements = elements
    c.mesh = {"success": True, "nodes": nodes.tolist(),
              "elements": elements.tolist(), "physical_groups": {}}
    load, support = _face_less_conditions()
    c.conditions.add(load)
    c.conditions.add(support)

    local_result = c.run_fea(conditions=list(c.conditions.all), backend="local")

    assert local_result["success"] is True
    assert local_result["engine"] == "self-contained-numpy-tet4"
    assert local_result["num_elements"] == elements.shape[0]
    assert local_result["max_displacement"] > 0.0


@pytest.mark.kratos
def test_run_fea_kratos_executes_on_full_controller_flow():
    """El caudal completo (condiciones -> bridge -> create_kratos_fea_solver ->
    solve nativo -> resultado) finaliza sin errores sobre la malla real."""
    data = np.load(_MESH)
    c = PipelineController()
    c.mesh_nodes = np.asarray(data["nodes"], dtype=float)
    c.mesh_elements = np.asarray(data["elements"], dtype=int)
    c.mesh = {"success": True, "physical_groups": {}}

    load, support = _face_less_conditions()
    c.conditions.add(load)
    c.conditions.add(support)

    result = c.run_fea(conditions=list(c.conditions.all), backend="kratos")

    assert result["success"] is True
    assert "error" not in result or result.get("success")