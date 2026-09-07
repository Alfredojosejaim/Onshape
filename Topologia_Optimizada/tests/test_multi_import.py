"""Multi-import y multi-sólido: segundo STEP parte limpio; STEP con N
sólidos expone N cuerpos (viewport, árbol y CADModel)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _step_files(tmp_path):
    import cadquery as cq

    a = str(tmp_path / "a.step")
    b = str(tmp_path / "b.step")
    two = str(tmp_path / "two.step")
    cq.Workplane("XY").box(10, 10, 10).val().exportStep(a)
    cq.Workplane("XY").cylinder(20, 5).val().exportStep(b)
    s1 = cq.Solid.makeBox(10, 10, 10)
    s2 = cq.Solid.makeBox(10, 10, 10, cq.Vector(30, 0, 0))
    cq.Compound.makeCompound([s1, s2]).exportStep(two)
    return a, b, two


# ------------------------------------------------------------------ #
# Backend / controller
# ------------------------------------------------------------------ #

def test_second_import_starts_clean(tmp_path):
    from desktop.pipeline.controller import PipelineController
    from core.conditions import LoadCondition

    a, b, _ = _step_files(tmp_path)
    c = PipelineController()
    c.import_model(a)
    c.conditions.add(LoadCondition(name="F-vieja"))
    assert len(c.conditions) == 1
    assert len(c.feature_history.features) == 1

    c.import_model(b)
    # Nada del modelo anterior sobrevive: ni condiciones, ni historial
    # mezclado, ni estudios/documentos viejos.
    assert len(c.conditions) == 0
    assert len(c.feature_history.features) == 1
    assert c.feature_history.features[0].result_model_id == c.model_id
    assert c.model_name == "b"
    assert c.mesh is None and c.forces == [] and c.constraints == []


def test_multi_solid_cadmodel_split(tmp_path):
    from services.cad_service import CADService

    _, _, two = _step_files(tmp_path)
    svc = CADService()
    m = svc.import_step_from_file(two)
    assert len(m.solids) == 2
    assert [s.id for s in m.solids] == ["solid_0", "solid_1"]
    counts = sorted(len(s.faces) for s in m.solids)
    assert counts == [6, 6]
    # Los face_index globales se conservan (0..11, picking intacto).
    all_idx = sorted(f.face_index for s in m.solids for f in s.faces)
    assert all_idx == list(range(12))
    assert m.solids[0].volume == m.solids[1].volume > 0
    # Coherente con list_solids (shape).
    listed = svc.list_solids(m.id)
    assert len(listed) == 2


def test_single_solid_unchanged(tmp_path):
    from services.cad_service import CADService

    a, _, _ = _step_files(tmp_path)
    svc = CADService()
    m = svc.import_step_from_file(a)
    assert len(m.solids) == 1
    assert m.solids[0].id == "solid_0"
    assert m.solids[0].name == "a"
    assert len(m.solids[0].faces) == 6


# ------------------------------------------------------------------ #
# UI headless (viewport software; patrón de test_ui_validate_connection)
# ------------------------------------------------------------------ #

def _make_window():
    import desktop.ui.main_window as mw
    from desktop.viewport.software_viewport import (
        SoftwareViewport, _SoftwareSelectionManager)

    _Noop = lambda *a, **k: None
    _SoftwareSelectionManager.set_solid_resolver = _Noop

    class _FakeViewport(SoftwareViewport):
        def __init__(self, *a, **k):
            super().__init__()

        def finalize(self):
            pass

    import desktop.ui.components.main_workspace as _mwcomp
    _mwcomp.Viewport3D = _FakeViewport
    mw.Viewport3D = _FakeViewport
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return mw.MainWindow()


def _body_labels(w):
    root = w.design_tree._bodies_item
    return [root.child(i).text(0) for i in range(root.childCount())]


def test_ui_second_import_replaces_viewport(tmp_path):
    w = _make_window()
    try:
        a, b, _ = _step_files(tmp_path)
        p1 = w.controller.import_model(a)
        w._on_import_done(p1)
        tris_a = w.viewport._scene._triangles
        assert tris_a is not None and len(tris_a) > 0
        assert "a" in w.doc_label.text()

        p2 = w.controller.import_model(b)
        w._on_import_done(p2)
        tris_b = w.viewport._scene._triangles
        assert tris_b is not None and len(tris_b) != len(tris_a)
        assert "b" in w.doc_label.text()
        # La cara mapeada pertenece al modelo nuevo: todo face_index >= 0
        # resuelve metadatos (lookup propio de la escena).
        fm = w.viewport._scene._face_index_map
        scene = w.viewport._scene
        assert fm is not None
        assert all(scene.face_meta(int(f)) is not None
                   for f in fm if int(f) >= 0)
    finally:
        w.close()


def test_ui_multi_solid_shows_bodies(tmp_path):
    w = _make_window()
    try:
        _, _, two = _step_files(tmp_path)
        p = w.controller.import_model(two)
        w._on_import_done(p)
        labels = _body_labels(w)
        assert len(labels) == 2
        assert all("Cuerpo" in lab for lab in labels)
    finally:
        w.close()
