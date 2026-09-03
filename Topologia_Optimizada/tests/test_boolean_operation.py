"""Validation tests for the Boolean CAD operation.

Covers the mandatory validation scenarios of the Boolean prompt (section 15):

    1.  Unión de dos cuerpos.
    2.  Unión de múltiples cuerpos.
    3.  Corte de dos cuerpos.
    4.  Corte con múltiples herramientas.
    5.  Intersección.
    6.  Conservar herramientas activado.
    7.  Conservar herramientas desactivado.
    10. Cancelación (no Feature / no cambio de modelo).
    11. Configuración inválida.
    12. Error geométrico / configuración inconsistente.
    13. Creación de Feature.
    14. Aparición en Timeline (feature history).
    16. Actualización del modelo.

These tests exercise the core: BooleanCommand + PipelineController + CADService,
which is where the geometric logic lives and is fully testable headless.
"""

import pytest

import cadquery as cq

from core.cad_entity import CadEntityRef
from core.commands import BooleanCommand
from desktop.pipeline.controller import PipelineController


# --------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------- #
def _two_body_model(ctrl, dx=16.0):
    """Return model_id of a compound with two disjoint boxes."""
    b1 = cq.Workplane("XY").box(10, 10, 10).translate((-dx / 2, 0, 0)).val()
    b2 = cq.Workplane("XY").box(10, 10, 10).translate((dx / 2, 0, 0)).val()
    comp = cq.Compound.makeCompound([b1, b2])
    return ctrl.cad.store_computed_shape(comp, "Dos cuerpos")


def _make_command(operation="union", target="solid_0", tools=("solid_1",),
                  keep_tools=False, model_id=None):
    cmd = BooleanCommand()
    cmd.set_parameter("operation", operation)
    cmd.set_parameter("keep_tools", keep_tools)
    target_ref = CadEntityRef.from_solid(target, model_id=model_id,
                                         index=int(target.split("_")[1]))
    cmd.set_target(target_ref)
    for i, t in enumerate(tools):
        cmd.add_tool(CadEntityRef.from_solid(t, model_id=model_id, index=i))
    return cmd


@pytest.fixture
def ctrl():
    c = PipelineController()
    c.model_id = _two_body_model(c)
    return c


def _solid_count(mid, ctrl):
    return len(list(ctrl.cad.get_model_shape(mid).Solids()))


# --------------------------------------------------------------------- #
# 1-5: Core operations
# --------------------------------------------------------------------- #
def test_union_two_bodies(ctrl):
    cmd = _make_command("union", model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    assert len(ctrl.feature_history.features) == 1


def test_union_multiple_bodies(ctrl):
    # Add a third body to make a multi-tool union.
    b3 = cq.Workplane("XY").box(10, 10, 10).translate((0, 20, 0)).val()
    comp = cq.Compound.makeCompound([
        cq.Workplane("XY").box(10, 10, 10).translate((-8, 0, 0)).val(),
        cq.Workplane("XY").box(10, 10, 10).translate((8, 0, 0)).val(),
        b3,
    ])
    mid = ctrl.cad.store_computed_shape(comp, "Tres cuerpos")
    ctrl.model_id = mid
    cmd = _make_command("union", target="solid_0",
                        tools=("solid_1", "solid_2"), model_id=mid)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    assert res.data["tool_body_ids"] == ["1", "2"]


def test_difference_two_bodies(ctrl):
    cmd = _make_command("difference", model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    # Disjoint boxes -> cut leaves only the target.
    assert _solid_count(ctrl.model_id, ctrl) == 1


def test_difference_multiple_tools(ctrl):
    b3 = cq.Workplane("XY").box(10, 10, 10).translate((0, 20, 0)).val()
    comp = cq.Compound.makeCompound([
        cq.Workplane("XY").box(10, 10, 10).translate((-8, 0, 0)).val(),
        cq.Workplane("XY").box(10, 10, 10).translate((8, 0, 0)).val(),
        b3,
    ])
    mid = ctrl.cad.store_computed_shape(comp, "Tres cuerpos")
    ctrl.model_id = mid
    cmd = _make_command("difference", target="solid_0",
                        tools=("solid_1", "solid_2"), model_id=mid)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    assert res.data["tool_body_ids"] == ["1", "2"]


def test_intersection(ctrl):
    cmd = _make_command("intersection", model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    # Disjoint boxes -> empty intersection.
    assert _solid_count(ctrl.model_id, ctrl) == 0


# --------------------------------------------------------------------- #
# 6-7: Keep tools semantics
# --------------------------------------------------------------------- #
def test_keep_tools_false_consumes_tools(ctrl):
    cmd = _make_command("difference", keep_tools=False, model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert res.success
    assert res.data["keep_tools"] is False
    # Tool consumed: only the target solid remains.
    assert _solid_count(ctrl.model_id, ctrl) == 1


def test_keep_tools_true_retains_tools(ctrl):
    cmd = _make_command("difference", keep_tools=True, model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert res.success
    assert res.data["keep_tools"] is True
    # Tool kept: target + untouched tool body.
    assert _solid_count(ctrl.model_id, ctrl) == 2
    # keep_tools is recorded on the feature.
    feature = ctrl.feature_history.features[-1]
    assert feature.parameters["keep_tools"] is True


# --------------------------------------------------------------------- #
# 10: Cancellation (command not validated / not executed)
# --------------------------------------------------------------------- #
def test_cancel_creates_no_feature(ctrl):
    """A command that is not executed (validation rejects) must not record a
    Feature nor change the model."""
    before = len(ctrl.feature_history.features)
    before_model = ctrl.model_id
    # Missing tools -> validation fails -> no execution.
    cmd = _make_command("union", target="solid_0", tools=(), model_id=ctrl.model_id)
    assert not cmd.validate()
    res = ctrl.execute_command(cmd)
    assert not res.success
    assert len(ctrl.feature_history.features) == before
    assert ctrl.model_id == before_model


# --------------------------------------------------------------------- #
# 11: Invalid configuration
# --------------------------------------------------------------------- #
def test_invalid_no_target(ctrl):
    cmd = BooleanCommand()
    cmd.set_parameter("operation", "union")
    cmd.add_tool(CadEntityRef.from_solid("solid_1", model_id=ctrl.model_id, index=1))
    assert not cmd.validate()
    res = ctrl.execute_command(cmd)
    assert not res.success
    assert "objetivo" in (res.error_message or "").lower() or "target" in (res.error_message or "").lower()


def test_invalid_no_tools(ctrl):
    cmd = BooleanCommand()
    cmd.set_parameter("operation", "union")
    cmd.set_target(CadEntityRef.from_solid("solid_0", model_id=ctrl.model_id, index=0))
    assert not cmd.validate()
    res = ctrl.execute_command(cmd)
    assert not res.success


def test_invalid_operation(ctrl):
    cmd = _make_command("bogus", model_id=ctrl.model_id)
    assert not cmd.validate()
    res = ctrl.execute_command(cmd)
    assert not res.success


def test_tool_cannot_be_target(ctrl):
    cmd = _make_command("union", target="solid_0", tools=("solid_0",), model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert not res.success


# --------------------------------------------------------------------- #
# 12: Geometric / inconsistency errors leave the model intact
# --------------------------------------------------------------------- #
def test_out_of_range_tool_error_leaves_model(ctrl):
    before = ctrl.model_id
    cmd = _make_command("union", target="solid_0", tools=("solid_9",),
                        model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert not res.success
    assert res.error_message
    assert ctrl.model_id == before
    assert len(ctrl.feature_history.features) == 0


# --------------------------------------------------------------------- #
# 13-16: Feature / history / model update
# --------------------------------------------------------------------- #
def test_feature_created_and_named(ctrl):
    cmd = _make_command("difference", model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert res.success
    feature = ctrl.feature_history.features[-1]
    assert feature.feature_type.value == "boolean"
    assert feature.name == "Boolean difference"
    assert res.feature_id == feature.id


def test_feature_in_timeline_history(ctrl):
    cmd = _make_command("union", keep_tools=True, model_id=ctrl.model_id)
    ctrl.execute_command(cmd)
    names = [f.name for f in ctrl.feature_history.features]
    assert names == ["Boolean union"]
    assert len(ctrl.document.features) == 1


def test_model_updated_after_operation(ctrl):
    old_shape = ctrl.cad.get_model_shape(ctrl.model_id)
    cmd = _make_command("difference", model_id=ctrl.model_id)
    res = ctrl.execute_command(cmd)
    assert res.success
    new_shape = ctrl.cad.get_model_shape(ctrl.model_id)
    assert new_shape is not None
    # Disjoint cut removes the tool body, leaving only the target (1000).
    assert abs(new_shape.Volume() - 1000.0) < 1e-6


# --------------------------------------------------------------------- #
# BooleanPanel (Qt dialog) logic — cancellation / validation
# --------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app


def _panel_refs():
    return [
        CadEntityRef.from_solid("solid_0", model_id="m", index=0),
        CadEntityRef.from_solid("solid_1", model_id="m", index=1),
    ]


def test_panel_cancel_builds_no_command(qapp):
    from desktop.ui.panels.boolean_panel import BooleanPanel
    panel = BooleanPanel(operation="union", get_solid_selections=_panel_refs)
    # Mimic the user cancelling: no capture, no accept.
    assert panel.command is None
    panel.reject()
    assert panel.command is None


def test_panel_accept_requires_target_and_tools(qapp):
    from desktop.ui.panels.boolean_panel import BooleanPanel
    panel = BooleanPanel(operation="union", get_solid_selections=_panel_refs)
    panel._on_accept()
    assert panel.command is None  # nothing captured -> validation failed
    panel._capture_target()
    panel._set_tools([])          # no tools -> still invalid
    panel._on_accept()
    assert panel.command is None


def test_panel_accept_builds_command(qapp):
    from desktop.ui.panels.boolean_panel import BooleanPanel
    panel = BooleanPanel(operation="difference", get_solid_selections=_panel_refs)
    panel._capture_target()
    panel._keep_tools.setChecked(True)
    panel._on_accept()
    assert panel.command is not None
    assert panel.command.get_parameter("operation") == "difference"
    assert panel.command.get_parameter("keep_tools") is True
    assert panel.command.target_body_id() == "solid_0"
    assert panel.command.tool_body_ids() == ["solid_1"]
    assert panel.command.validate()

