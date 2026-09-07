"""Vistas de condiciones: agrupación por pieza, badges y timeline ramificado."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton

from core.cad_entity import CadEntityRef, EntityType, SelectionSet
from core.conditions import (
    ElasticityCondition,
    LoadCondition,
    ObstructionCondition,
    ProtectedRegion,
)
from desktop.ui.panels.condition_groups import (
    UNGROUPED_LABEL,
    condition_badge,
    condition_color_hex,
    condition_label,
    group_conditions_by_part,
)


def _faces(*idx, model="m1"):
    sel = SelectionSet(name="s")
    for i in idx:
        sel.add(CadEntityRef(entity_type=EntityType.FACE, model_id=model,
                             face_index=i))
    return sel


def _solids(*ids):
    sel = SelectionSet(name="s")
    for i in ids:
        sel.add(CadEntityRef(entity_type=EntityType.SOLID, solid_id=i))
    return sel


def _app():
    return QApplication.instance() or QApplication([])


# ------------------------------------------------------------------ #
# Helper puro (sin Qt)
# ------------------------------------------------------------------ #

def test_group_solids_by_solid_id_without_resolver():
    conds = [
        LoadCondition(name="F1", faces=_faces(0)),
        ObstructionCondition(name="O1", bodies=_solids("solid_0")),
        ObstructionCondition(name="O2", bodies=_solids("solid_1")),
    ]
    groups = group_conditions_by_part(conds)
    labels = [g for g, _ in groups]
    assert "solid_0" in labels and "solid_1" in labels
    # Caras sin resolvedor caen a model_id.
    assert "m1" in labels


def test_group_faces_via_part_resolver_and_order():
    conds = [
        LoadCondition(name="F1", faces=_faces(0)),
        LoadCondition(name="F2", faces=_faces(5)),
        ElasticityCondition(name="E1", faces=_faces(1)),
    ]
    resolver = lambda fi, mid: "Pieza_A" if fi < 3 else "Pieza_B"
    groups = group_conditions_by_part(conds, part_resolver=resolver)
    assert [g for g, _ in groups] == ["Pieza_A", "Pieza_B"]
    assert [c.name for c in groups[0][1]] == ["F1", "E1"]
    assert [c.name for c in groups[1][1]] == ["F2"]


def test_empty_selection_goes_to_general():
    conds = [LoadCondition(name="F1", faces=SelectionSet(name="vacia"))]
    groups = group_conditions_by_part(conds)
    assert groups == [(UNGROUPED_LABEL, conds)]


def test_badges_per_instance():
    assert condition_badge(LoadCondition(
        name="F", faces=_faces(0), magnitude=100.0,
        indeterminate=False, unit="N")) == "100 N"
    assert condition_badge(LoadCondition(
        name="F", faces=_faces(0))) == "s/valor"
    assert condition_badge(ElasticityCondition(
        name="E", faces=_faces(0), flex_range_mm=2.5)) == "2.5 mm"
    assert condition_badge(ElasticityCondition(
        name="E", faces=_faces(0))) == "s/valor"
    assert condition_badge(ObstructionCondition(
        name="O", bodies=_solids("solid_0"), offset_mm=1.0)) == "offset 1 mm"
    assert condition_badge(ObstructionCondition(
        name="O", bodies=_solids("solid_0", "solid_1"))) == "2 cuerpos"
    assert condition_badge(ProtectedRegion(
        name="P", faces=_faces(0, 1, 2))) == "3 caras"
    lab = condition_label(LoadCondition(
        name="F1", faces=_faces(0), magnitude=50.0,
        indeterminate=False, unit="N"))
    assert lab == "F1  [load]  ·  50 N"


def test_type_colors_from_theme():
    assert condition_color_hex(LoadCondition(
        name="F", faces=_faces(0))) == "#f59e0b"
    assert condition_color_hex(ElasticityCondition(
        name="E", faces=_faces(0))) == "#8b5cf6"
    assert condition_color_hex(ObstructionCondition(
        name="O", bodies=_solids("solid_0"))) is None
    assert condition_color_hex(ProtectedRegion(
        name="P", faces=_faces(0))) is None


# ------------------------------------------------------------------ #
# DesignTree (Qt offscreen)
# ------------------------------------------------------------------ #

def test_tree_groups_by_part_with_badges_and_colors():
    _app()
    from desktop.ui.panels.design_tree import DesignTreePanel
    tree = DesignTreePanel()
    tree.set_context("pieza", has_mesh=False, has_result=False)
    conds = [
        LoadCondition(name="F1", faces=_faces(0), magnitude=100.0,
                      indeterminate=False, unit="N"),
        ObstructionCondition(name="O1", bodies=_solids("solid_0")),
        ObstructionCondition(name="O2", bodies=_solids("solid_1")),
    ]
    tree.set_conditions(conds)
    root = tree._conditions_item
    groups = [root.child(i).text(0) for i in range(root.childCount())]
    assert groups == ["Condiciones — m1", "Condiciones — solid_0",
                      "Condiciones — solid_1"]
    first = root.child(0).child(0)  # F1 (carga) bajo el grupo m1
    assert "100 N" in first.text(0)
    assert first.foreground(0).color().name() == "#f59e0b"


def test_tree_empty_and_backward_compat():
    _app()
    from desktop.ui.panels.design_tree import DesignTreePanel
    tree = DesignTreePanel()
    tree.set_context("pieza", has_mesh=False, has_result=False)
    tree.set_conditions([])
    assert tree._conditions_item.child(0).text(0) == "(vacío)"
    # Sin resolver sigue agrupando (por defecto) sin romper.
    tree.set_conditions([LoadCondition(name="F", faces=_faces(0))])
    assert tree._conditions_item.childCount() == 1


# ------------------------------------------------------------------ #
# Timeline ramificado (Qt offscreen)
# ------------------------------------------------------------------ #

def test_timeline_branch_columns_and_converge():
    _app()
    from desktop.ui.panels.timeline import TimelinePanel
    tl = TimelinePanel()
    assert not tl.is_branch_mode()
    tl.set_branch_view([
        ("Pieza_A", ["F1  [load]  ·  100 N", "E1  [elasticity]"]),
        ("Pieza_B", ["O1  [obstruction]"]),
    ])
    assert tl.is_branch_mode()
    texts = [w.text() for w in tl.findChildren(QPushButton)]
    assert "Pieza_A" in texts and "Pieza_B" in texts
    assert any("Optimizar" in t for t in texts)
    assert "F1  [load]  ·  100 N" in texts


def test_timeline_exits_branch_on_pipeline_step():
    _app()
    from desktop.ui.panels.timeline import TimelinePanel
    tl = TimelinePanel()
    tl.set_branch_view([("A", ["x"]), ("B", ["y"])])
    assert tl.is_branch_mode()
    tl.set_pipeline_step(2)
    assert not tl.is_branch_mode()
    assert len(tl._step_widgets) == 5  # pills pipeline restauradas
    # Vista vacía no entra en modo ramificado.
    tl.set_branch_view([])
    assert not tl.is_branch_mode()
