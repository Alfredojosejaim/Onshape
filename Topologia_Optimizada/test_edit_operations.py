"""End-to-end tests for the Transform / Mirror / Pattern CAD operations.

Covers the full flow requested in ``prompts.md``:

    Command -> PipelineController -> CADService -> real geometry
    -> active model -> FeatureHistory -> Document -> DesignTree sync

Transform
    - validation
    - real CAD execution
    - geometric result
    - active-model update
    - FeatureHistory

Mirror
    - validation
    - real CAD execution
    - geometric result
    - history

Pattern
    - linear
    - rectangular
    - circular (especially center != origin)

Integration
    - the active model changes
    - the previous FE mesh / results are invalidated
    - the DesignTree reflects the operation
"""

import pytest

import cadquery as cq

from core.cad_entity import CadEntityRef
from core.commands import (
    TransformCommand, TransformType,
    MirrorCommand,
    PatternCommand, PatternType,
)
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


@pytest.fixture
def ctrl():
    c = PipelineController()
    c.model_id = _two_body_model(c)
    return c


def _ref(mid, target):
    return CadEntityRef.from_solid(target, model_id=mid,
                                   index=int(target.split("_")[1]))


def _solid_count(mid, ctrl):
    return len(list(ctrl.cad.get_model_shape(mid).Solids()))


def _body_centers(mid, ctrl):
    out = []
    for s in ctrl.cad.get_model_shape(mid).Solids():
        bb = s.BoundingBox()
        out.append(((bb.xmin + bb.xmax) / 2.0,
                    (bb.ymin + bb.ymax) / 2.0,
                    (bb.zmin + bb.zmax) / 2.0))
    return out


# --------------------------------------------------------------------- #
# Transform: validation
# --------------------------------------------------------------------- #
def test_transform_requires_target(ctrl):
    cmd = TransformCommand()
    cmd.set_parameter("transform_type", "translate")
    cmd.set_parameter("translation", "5, 0, 0")
    assert not cmd.validate()
    res = ctrl.execute_command(cmd)
    assert not res.success
    assert len(ctrl.feature_history.features) == 0


def test_transform_invalid_type(ctrl):
    cmd = TransformCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("transform_type", "bogus")
    assert not cmd.validate()
    assert not ctrl.execute_command(cmd).success


def test_transform_scale_factor_must_be_positive(ctrl):
    cmd = TransformCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("transform_type", "scale")
    cmd.set_parameter("scale_factor", 0)
    assert not cmd.validate()


# --------------------------------------------------------------------- #
# Transform: execution + geometry + model + history
# --------------------------------------------------------------------- #
def test_transform_translate_executes(ctrl):
    before = _body_centers(ctrl.model_id, ctrl)[0]
    cmd = TransformCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("transform_type", "translate")
    cmd.set_parameter("translation", "20, 0, 0")
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    # The translated solid's center moved by (20, 0, 0).
    centers = _body_centers(ctrl.model_id, ctrl)
    moved = [c for c in centers if c[0] > 10]
    assert moved, "translated solid not found"
    assert abs(moved[0][0] - (before[0] + 20)) < 1e-6


def test_transform_rotate_executes(ctrl):
    cmd = TransformCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("transform_type", "rotate")
    cmd.set_parameter("rotation_axis", "0, 0, 1")
    cmd.set_parameter("rotation_angle", 90.0)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    assert res.data["transform_type"] == "rotate"


def test_transform_scale_executes(ctrl):
    cmd = TransformCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("transform_type", "scale")
    cmd.set_parameter("scale_factor", 2.0)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    assert res.data["transform_type"] == "scale"


def test_transform_creates_feature_and_updates_model(ctrl):
    before_model = ctrl.model_id
    cmd = TransformCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("transform_type", "translate")
    cmd.set_parameter("translation", "15, 0, 0")
    res = ctrl.execute_command(cmd)
    assert res.success
    assert res.result_model_id is not None
    assert ctrl.model_id == res.result_model_id
    assert ctrl.model_id != before_model
    feature = ctrl.feature_history.features[-1]
    assert feature.feature_type.value == "transform"
    assert feature.name == "Transform translate"
    assert res.feature_id == feature.id
    assert len(ctrl.document.features) == 1


# --------------------------------------------------------------------- #
# Mirror: validation
# --------------------------------------------------------------------- #
def test_mirror_requires_target(ctrl):
    cmd = MirrorCommand()
    cmd.set_parameter("plane_normal", "0, 1, 0")
    assert not cmd.validate()
    assert not ctrl.execute_command(cmd).success


def test_mirror_zero_normal_rejected(ctrl):
    cmd = MirrorCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("plane_normal", "0, 0, 0")
    assert not cmd.validate()


# --------------------------------------------------------------------- #
# Mirror: execution + geometry + history
# --------------------------------------------------------------------- #
def test_mirror_executes_and_keeps_original(ctrl):
    before = _solid_count(ctrl.model_id, ctrl)
    cmd = MirrorCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("plane_normal", "1, 0, 0")
    cmd.set_parameter("plane_point", "0, 0, 0")
    cmd.set_parameter("keep_original", True)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    # Original kept + mirrored copy added.
    assert _solid_count(ctrl.model_id, ctrl) == before + 1


def test_mirror_geometry_reflected_across_plane(ctrl):
    # solid_0 is centered at x = -8. Mirroring across the YZ plane (normal X)
    # puts the mirrored copy at x = +8.
    cmd = MirrorCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("plane_normal", "1, 0, 0")
    cmd.set_parameter("plane_point", "0, 0, 0")
    cmd.set_parameter("keep_original", True)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    centers = _body_centers(ctrl.model_id, ctrl)
    xs = sorted(round(c[0], 3) for c in centers)
    # solid_0 (-8) mirrored to +8; untouched b2 stays at +8 -> [-8, 8, 8].
    assert xs == [-8.0, 8.0, 8.0]


def test_mirror_creates_feature(ctrl):
    cmd = MirrorCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("plane_normal", "0, 1, 0")
    res = ctrl.execute_command(cmd)
    assert res.success
    feature = ctrl.feature_history.features[-1]
    assert feature.feature_type.value == "mirror"
    assert feature.name == "Mirror"


# --------------------------------------------------------------------- #
# Pattern
# --------------------------------------------------------------------- #
def test_pattern_requires_target(ctrl):
    cmd = PatternCommand()
    cmd.set_parameter("pattern_type", "linear")
    cmd.set_parameter("count", 3)
    cmd.set_parameter("spacing", 20.0)
    assert not cmd.validate()
    assert not ctrl.execute_command(cmd).success


def test_pattern_linear_executes(ctrl):
    cmd = PatternCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("pattern_type", "linear")
    cmd.set_parameter("direction", "1, 0, 0")
    cmd.set_parameter("count", 3)
    cmd.set_parameter("spacing", 20.0)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    # target body becomes 3 instances (count) + the untouched b2 body.
    assert _solid_count(ctrl.model_id, ctrl) == 4


def test_pattern_linear_positions(ctrl):
    # solid_0 centered at x=-8. Instances at -8, 12, 32 (spacing 20).
    cmd = PatternCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("pattern_type", "linear")
    cmd.set_parameter("direction", "1, 0, 0")
    cmd.set_parameter("count", 3)
    cmd.set_parameter("spacing", 20.0)
    res = ctrl.execute_command(cmd)
    assert res.success
    xs = sorted(round(c[0], 3) for c in _body_centers(ctrl.model_id, ctrl))
    assert -8.0 in xs and 12.0 in xs and 32.0 in xs and 8.0 in xs


def test_pattern_rectangular_executes(ctrl):
    before = _solid_count(ctrl.model_id, ctrl)
    cmd = PatternCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("pattern_type", "rectangular")
    cmd.set_parameter("direction", "1, 0, 0")
    cmd.set_parameter("direction2", "0, 1, 0")
    cmd.set_parameter("count", 3)
    cmd.set_parameter("count2", 2)
    cmd.set_parameter("spacing", 20.0)
    res = ctrl.execute_command(cmd)
    assert res.success, res.error_message
    # 3x2 = 6 instances minus the origin position = 5 new copies.
    assert _solid_count(ctrl.model_id, ctrl) == before + 5


def test_pattern_circular_uses_center_not_origin(ctrl):
    """A circular pattern whose center is NOT the origin must rotate the
    bodies around that user-defined center (prompts.md finding C)."""
    b = cq.Workplane("XY").box(20, 20, 20).translate((0, 0, 0)).val()
    c = PipelineController()
    c.model_id = c.cad.store_computed_shape(b, "caja-origen")
    cmd = PatternCommand()
    cmd.set_target(_ref(c.model_id, "solid_0"))
    cmd.set_parameter("pattern_type", "circular")
    cmd.set_parameter("count", 4)
    cmd.set_parameter("angle", 360.0)
    cmd.set_parameter("axis", "0, 0, 1")
    cmd.set_parameter("center", "50, 0, 0")
    res = c.execute_command(cmd)
    assert res.success, res.error_message
    assert _solid_count(c.model_id, c) == 4
    # The box (center at origin) rotated 90/180/270 deg around axis at x=50:
    # centers land at radius 50 (90/270) and 100 (180) from the origin.
    radii = sorted(round((x * x + y * y) ** 0.5, 1) for x, y, _ in _body_centers(c.model_id, c))
    assert radii == [0.0, 70.7, 70.7, 100.0]


def test_pattern_circular_center_origin(ctrl):
    """"Center at the origin produces the classic origin-rotation result."""
    b = cq.Workplane("XY").box(20, 20, 20).translate((0, 0, 0)).val()
    c = PipelineController()
    c.model_id = c.cad.store_computed_shape(b, "caja-origen")
    cmd = PatternCommand()
    cmd.set_target(_ref(c.model_id, "solid_0"))
    cmd.set_parameter("pattern_type", "circular")
    cmd.set_parameter("count", 4)
    cmd.set_parameter("angle", 360.0)
    cmd.set_parameter("axis", "0, 0, 1")
    cmd.set_parameter("center", "0, 0, 0")
    res = c.execute_command(cmd)
    assert res.success
    radii = sorted(round((x * x + y * y) ** 0.5, 1) for x, y, _ in _body_centers(c.model_id, c))
    assert radii == [0.0, 0.0, 0.0, 0.0]


def test_pattern_creates_feature(ctrl):
    cmd = PatternCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("pattern_type", "linear")
    cmd.set_parameter("count", 3)
    cmd.set_parameter("spacing", 10.0)
    res = ctrl.execute_command(cmd)
    assert res.success
    feature = ctrl.feature_history.features[-1]
    assert feature.feature_type.value == "pattern"
    assert feature.name == "Pattern (linear)"


# --------------------------------------------------------------------- #
# Integration: model invalidation / DesignTree sync
# --------------------------------------------------------------------- #
def test_operation_invalidates_mesh_and_results(ctrl):
    # Simulate a pre-existing mesh + result that must be invalidated.
    ctrl.mesh = {"nodes": [], "elements": []}
    ctrl.mesh_nodes = ctrl.mesh_elements = []
    ctrl.result = {"success": True}
    ctrl.result_densities = []

    cmd = TransformCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("transform_type", "translate")
    cmd.set_parameter("translation", "5, 0, 0")
    res = ctrl.execute_command(cmd)
    assert res.success
    # Geometry changed => downstream state cleared.
    assert ctrl.mesh is None
    assert ctrl.mesh_nodes is None
    assert ctrl.result is None
    assert ctrl.result_densities is None
    assert ctrl.current_tessellation is not None  # re-tessellated


def test_design_tree_reflects_operation(ctrl):
    """The feature list consumed by the DesignTree panel reflects the op."""
    cmd = MirrorCommand()
    cmd.set_target(_ref(ctrl.model_id, "solid_0"))
    cmd.set_parameter("plane_normal", "0, 1, 0")
    res = ctrl.execute_command(cmd)
    assert res.success
    # DesignTree reads the feature history; it must include the operation.
    names = [f.name for f in ctrl.feature_history.features]
    assert "Mirror" in names


# --------------------------------------------------------------------- #
# Panels (Qt) — cancel / accept logic
# --------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app


def _panel_refs():
    return [CadEntityRef.from_solid("solid_0", model_id="m", index=0)]


def test_transform_panel_cancel_builds_no_command(qapp):
    from desktop.ui.panels.transform_panel import TransformPanel
    panel = TransformPanel(get_solid_selections=_panel_refs)
    assert panel.command is None
    panel.reject()
    assert panel.command is None


def test_transform_panel_accept_requires_target(qapp):
    from desktop.ui.panels.transform_panel import TransformPanel
    panel = TransformPanel(get_solid_selections=_panel_refs)
    panel._on_accept()
    assert panel.command is None  # no target captured


def test_transform_panel_accept_builds_command(qapp):
    from desktop.ui.panels.transform_panel import TransformPanel
    panel = TransformPanel(get_solid_selections=_panel_refs)
    panel._capture_target()
    panel._on_accept()
    assert panel.command is not None
    assert panel.command.get_parameter("transform_type") == "translate"
    assert panel.command.validate()


def test_mirror_panel_accept_requires_target(qapp):
    from desktop.ui.panels.mirror_panel import MirrorPanel
    panel = MirrorPanel(get_solid_selections=_panel_refs)
    panel._on_accept()
    assert panel.command is None


def test_mirror_panel_accept_builds_command(qapp):
    from desktop.ui.panels.mirror_panel import MirrorPanel
    panel = MirrorPanel(get_solid_selections=_panel_refs)
    panel._capture_target()
    panel._on_accept()
    assert panel.command is not None
    assert panel.command.validate()
    assert panel.command.get_parameter("keep_original") is True


def test_pattern_panel_accept_builds_command(qapp):
    from desktop.ui.panels.pattern_panel import PatternPanel
    panel = PatternPanel(get_solid_selections=_panel_refs)
    panel._capture_target()
    panel._on_accept()
    assert panel.command is not None
    assert panel.command.get_parameter("pattern_type") == "linear"
    assert panel.command.validate()
