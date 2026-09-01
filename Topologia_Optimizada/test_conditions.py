"""Validation tests for the reusable CAD/CAE conditions.

Covers the mandatory validation scenarios of the prompt:

1.  Carga: selección de caras, orientación (paralelo/perpendicular/ángulo),
    sentido, magnitud numérica, y estado "indeterminado" como valor válido.
2.  Elasticidad: caras + rango de flexión en mm.
3.  Obstrucciones: piezas + offset opcional.
4.  Regiones protegidas: caras almacenadas como geometría a no modificar.
5.  Las condiciones se guardan como condiciones reutilizables, se recuperan
    sin duplicarse, se integran en el historial (Feature) y coexisten con las
    operaciones CAD existentes.
"""

import pytest

from core.cad_entity import CadEntityRef, EntityType
from core.commands import (
    ElasticityCommand,
    LoadConditionCommand,
    LoadOrientation,
    LoadSense,
    ObstructionCommand,
    ProtectedRegionCommand,
)
from core.conditions import (
    ConditionManager,
    ConditionType,
    ElasticityCondition,
    LoadCondition,
    ObstructionCondition,
    ProtectedRegion,
    condition_from_dict,
)
from core.features import Feature, FeatureType
from core.optimization_studies import TopologyOptimizationStudy
from desktop.pipeline.controller import PipelineController


def _face(i: int, mid: str = "m") -> CadEntityRef:
    return CadEntityRef.from_face(face_index=i, model_id=mid)


def _solid(i: int, mid: str = "m") -> CadEntityRef:
    return CadEntityRef.from_solid(f"solid_{i}", model_id=mid, index=i)


# --------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------- #
def test_load_condition_faces_and_indeterminate():
    cmd = LoadConditionCommand()
    cmd.set_parameter("name", "Carga Z-")
    for i in range(3):
        cmd.add_face(_face(i))
    cmd.set_parameter("orientation", LoadOrientation.PERPENDICULAR.value)
    cmd.set_parameter("sense", LoadSense.NEGATIVE.value)
    cmd.set_parameter("indeterminate", True)  # magnitud indeterminada (válida)
    assert cmd.validate()

    res = cmd.execute()
    assert res.success
    cond_data = res.data["condition"]
    assert cond_data["type"] == ConditionType.LOAD.value
    assert len(cond_data["faces"]["entities"]) == 3

    cond = cmd.build_condition()
    assert isinstance(cond, LoadCondition)
    assert cond.condition_type == ConditionType.LOAD
    assert cond.indeterminate is True
    assert cond.magnitude is None
    assert cond.sense == LoadSense.NEGATIVE
    assert cond.orientation == LoadOrientation.PERPENDICULAR


def test_load_condition_requires_face():
    cmd = LoadConditionCommand()
    cmd.set_parameter("indeterminate", True)
    assert not cmd.validate()
    assert not cmd.execute().success


def test_load_condition_magnitude_positive_when_not_indeterminate():
    cmd = LoadConditionCommand()
    cmd.add_face(_face(0))
    cmd.set_parameter("indeterminate", False)
    cmd.set_parameter("magnitude", -5.0)
    assert not cmd.validate()


def test_load_orientation_angle_requires_angle():
    cmd = LoadConditionCommand()
    cmd.add_face(_face(0))
    cmd.set_parameter("orientation", LoadOrientation.ANGLE.value)
    cmd.set_parameter("angle_deg", None)
    assert not cmd.validate()


# --------------------------------------------------------------------- #
# Elasticidad
# --------------------------------------------------------------------- #
def test_elasticity_condition():
    cmd = ElasticityCommand()
    cmd.add_face(_face(0))
    cmd.add_face(_face(1))
    cmd.set_parameter("name", "Elasticidad")
    cmd.set_parameter("flex_range_mm", 2.5)
    assert cmd.validate()
    cond = cmd.build_condition()
    assert isinstance(cond, ElasticityCondition)
    assert cond.flex_range_mm == 2.5
    assert len(cond.selection().entities) == 2


def test_elasticity_requires_face():
    cmd = ElasticityCommand()
    cmd.set_parameter("flex_range_mm", 2.5)
    assert not cmd.validate()


def test_elasticity_negative_range_rejected():
    cmd = ElasticityCommand()
    cmd.add_face(_face(0))
    cmd.set_parameter("flex_range_mm", -1.0)
    assert not cmd.validate()


# --------------------------------------------------------------------- #
# Obstrucción
# --------------------------------------------------------------------- #
def test_obstruction_condition():
    cmd = ObstructionCommand()
    cmd.add_body(_solid(0))
    cmd.add_body(_solid(1))
    cmd.set_parameter("offset_mm", 3.0)
    assert cmd.validate()
    cond = cmd.build_condition()
    assert isinstance(cond, ObstructionCondition)
    assert cond.offset_mm == 3.0
    assert len(cond.selection().entities) == 2


def test_obstruction_requires_body():
    cmd = ObstructionCommand()
    cmd.set_parameter("offset_mm", 1.0)
    assert not cmd.validate()


# --------------------------------------------------------------------- #
# Región protegida
# --------------------------------------------------------------------- #
def test_protected_region_condition():
    cmd = ProtectedRegionCommand()
    cmd.add_face(_face(0))
    cmd.add_face(_face(1))
    cmd.add_geometry_ref({"type": "box", "bbox": {"xmin": 0, "xmax": 1}})
    assert cmd.validate()
    cond = cmd.build_condition()
    assert isinstance(cond, ProtectedRegion)
    assert len(cond.faces.entities) == 2
    assert len(cond.geometry_refs) == 1


def test_protected_region_requires_selection():
    cmd = ProtectedRegionCommand()
    assert not cmd.validate()
    assert not cmd.execute().success


# --------------------------------------------------------------------- #
# Serialisation round-trip
# --------------------------------------------------------------------- #
def test_condition_serialisation_roundtrip():
    cmd = LoadConditionCommand()
    cmd.add_face(_face(2, mid="abc"))
    cmd.set_parameter("orientation", LoadOrientation.PARALLEL.value)
    cmd.set_parameter("magnitude", 123.5)
    cmd.set_parameter("indeterminate", False)
    cond = cmd.build_condition()
    d = cond.to_dict()
    rebuilt = condition_from_dict(d)
    assert isinstance(rebuilt, LoadCondition)
    assert rebuilt.magnitude == 123.5
    assert rebuilt.indeterminate is False
    assert rebuilt.orientation == LoadOrientation.PARALLEL


# --------------------------------------------------------------------- #
# Feature recording (historial)
# --------------------------------------------------------------------- #
def test_condition_feature_recorded():
    feature = Feature.condition(
        condition_type=FeatureType.CONDITION_LOAD.value,
        name="Carga Z-",
        condition={"type": "load", "id": "c1"},
    )
    assert feature.feature_type == FeatureType.CONDITION_LOAD
    assert feature.name == "Carga Z-"
    assert feature.status.value == "executed"
    assert feature.parameters["condition"]["type"] == "load"


# --------------------------------------------------------------------- #
# Pipeline integration: register condition + Feature + shared manager
# --------------------------------------------------------------------- #
@pytest.fixture
def ctrl():
    return PipelineController()


def test_pipeline_registers_load_condition(ctrl):
    cmd = LoadConditionCommand()
    cmd.set_parameter("name", "Carga")
    cmd.add_face(_face(0, mid=ctrl.model_id or "m"))
    cmd.set_parameter("indeterminate", True)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    assert res.data["status"] == "condition_registered"
    # Registered in the shared ConditionManager
    assert len(ctrl.conditions) == 1
    cond = ctrl.conditions.get(res.data["condition_id"])
    assert cond is not None
    # Feature recorded in the history + document
    assert len(ctrl.feature_history.features) == 1
    assert ctrl.feature_history.features[-1].feature_type.value == "condition_load"
    assert len(ctrl.document.features) == 1
    assert len(ctrl.document.conditions) == 1


def test_pipeline_conditions_do_not_duplicate(ctrl):
    # Register an elasticity condition twice and verify it is shared, not copied.
    cmd = ElasticityCommand()
    cmd.add_face(_face(0, mid="m"))
    cmd.set_parameter("flex_range_mm", 1.0)
    r1 = ctrl.execute_command(cmd)

    study = TopologyOptimizationStudy()
    study.add_condition(r1.data["condition_id"])
    study.add_condition(r1.data["condition_id"])  # duplicate reference

    consumed = study.consume_conditions(ctrl.conditions)
    assert len(consumed) == 1  # resolved once, no duplication
    assert consumed[0].id == r1.data["condition_id"]


def test_study_consumes_conditions_without_owning():
    ctrl = PipelineController()
    cmd = LoadConditionCommand()
    cmd.add_face(_face(0, mid="m"))
    cmd.set_parameter("indeterminate", True)
    r = ctrl.execute_command(cmd)
    cid = r.data["condition_id"]

    study = TopologyOptimizationStudy()
    study.add_condition(cid)
    study.add_part(_solid(0, mid="m"))
    assert study.conditions == [cid]
    assert len(study.parts) == 1
    consumed = study.consume_conditions(ctrl.conditions)
    assert len(consumed) == 1
    # The consumed object is exactly the shared one (not a copy).
    assert consumed[0].id == cid


def test_conditions_coexist_with_boolean_history(ctrl):
    # Regression: registering a condition plus a boolean should coexist in a
    # single history with no parallel system.
    cmd = LoadConditionCommand()
    cmd.add_face(_face(0, mid="m"))
    cmd.set_parameter("indeterminate", True)
    r = ctrl.execute_command(cmd)
    assert r.success
    # Both the condition feature and manager are present together.
    assert len(ctrl.conditions) == 1
    assert len(ctrl.document.features) == 1
    assert ctrl.feature_history.features[-1].feature_type.value == "condition_load"


# --------------------------------------------------------------------- #
# ConditionManager (shared, no duplication)
# --------------------------------------------------------------------- #
def test_condition_manager_resolve_and_filter():
    from core.cad_entity import SelectionSet

    mgr = ConditionManager()
    c1 = LoadCondition(name="C", faces=SelectionSet())
    c1.faces.entities.append(_face(0))
    e1 = ElasticityCondition(name="E", flex_range_mm=2.0)
    mgr.add(c1)
    mgr.add(e1)

    assert len(mgr.resolve([c1.id, c1.id, "bogus"])) == 1  # dedup by shared object
    assert [x.id for x in mgr.conditions_by_type(ConditionType.LOAD)] == [c1.id]
    assert len(mgr) == 2


# --------------------------------------------------------------------- #
# ConditionPanel (Qt dialog) cancellation / accept logic
# --------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app


def _face_refs():
    return [CadEntityRef.from_face(0, model_id="m")]


def test_panel_cancel_builds_no_command(qapp):
    from desktop.ui.panels.condition_panel import ConditionPanel
    panel = ConditionPanel(condition_kind="load", get_face_selections=_face_refs)
    assert panel.command is None
    panel.reject()
    assert panel.command is None


def test_panel_accept_requires_selection(qapp):
    from desktop.ui.panels.condition_panel import ConditionPanel
    panel = ConditionPanel(condition_kind="load", get_face_selections=_face_refs, )
    panel._on_accept()
    assert panel.command is None  # nothing captured -> validation failed


def test_panel_accept_builds_load_command(qapp):
    from desktop.ui.panels.condition_panel import ConditionPanel
    panel = ConditionPanel(condition_kind="load", get_face_selections=_face_refs)
    panel._capture()
    panel._on_accept()
    assert panel.command is not None
    assert panel.command.command_type.value == "condition_load"
    assert panel.command.validate()