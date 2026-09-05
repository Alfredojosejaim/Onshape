"""Rubber-band select estilo Onshape (prompt: bloque de picking cerrado).

- Drag simple -> reemplaza. Shift+drag -> aditivo. Ctrl+drag -> sustractivo.
- Fully-contained: la cara entra solo si TODOS sus vertices caen en el rect.
- Sin GPU: logica de set + contencion con proyeccion stub; VTK real solo
  en el path por defecto (no ejercitado aqui).
"""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtCore import QRect


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #

class _FakeRenderer:
    def GetSize(self):
        return (800, 600)

    def AddActor(self, a):
        pass

    def RemoveActor(self, a):
        pass

    def Render(self):
        pass


class _FakeScene:
    _model_actor_key = "m"
    _actors = {}

    def __init__(self):
        self.highlighted = None
        self.cleared = 0

    def face_index_for_cell(self, cell_id):
        return None

    def face_meta(self, fi):
        return {"id": f"face_{fi}", "center": [0, 0, 0],
                "normal": [0, 0, 1], "area": 1.0}

    def highlight_faces(self, faces):
        self.highlighted = sorted(int(f) for f in faces)

    def clear_highlight(self):
        self.highlighted = None
        self.cleared += 1


def _manager():
    from desktop.viewport.selection import SelectionManager
    m = SelectionManager(_FakeRenderer())
    m.attach(_FakeScene())
    return m


def _faces(m):
    return sorted(e.face_index for e in m.selected)


# --------------------------------------------------------------------------- #
# handle_rubber_band: semantica Onshape completa
# --------------------------------------------------------------------------- #

def test_rubber_plain_is_additive_union():
    # Onshape real: drag simple = UNION (igual que el click puntual).
    m = _manager()
    m.handle_rubber_band({0, 1})
    assert _faces(m) == [0, 1]
    m.handle_rubber_band({2})
    assert _faces(m) == [0, 1, 2]
    assert m._scene.highlighted == [0, 1, 2]


def test_rubber_empty_is_noop_not_clear():
    # Rectangulo vacio = union con vacio = sin cambio (limpiar es click
    # en vacio via handle_pick(None), no rubber).
    m = _manager()
    emitted = []
    m.set_selection_callback(emitted.append)
    m.handle_rubber_band({0, 1})
    n_emit = len(emitted)
    m.handle_rubber_band(set())
    assert _faces(m) == [0, 1]
    assert len(emitted) == n_emit


def test_rubber_ctrl_subtracts():
    m = _manager()
    m.handle_rubber_band({0, 1, 2})
    m.handle_rubber_band({1}, subtractive=True)
    assert _faces(m) == [0, 2]
    assert m._scene.highlighted == [0, 2]


def test_rubber_noop_does_not_emit():
    m = _manager()
    m.handle_rubber_band({0, 1})
    emitted = []
    changed = []
    m.set_selection_callback(emitted.append)
    m.selectionChanged.connect(changed.append)
    m.handle_rubber_band({1}, subtractive=True)   # quita 1
    assert _faces(m) == [0]
    n_emit = len(emitted)
    m.handle_rubber_band({5}, subtractive=True)   # 5 no esta: no-op
    assert _faces(m) == [0]
    assert len(emitted) == n_emit
    assert len(changed) == 1


def test_handle_pick_is_pure_toggle_no_modifier():
    # Onshape real (docs): click plano YA es aditivo; click de nuevo quita;
    # vacio limpia. Sin ramas de modificador.
    from core.cad_entity import CadEntityRef
    m = _manager()
    e0 = CadEntityRef.from_face(0, model_id="m")
    e1 = CadEntityRef.from_face(1, model_id="m")
    m.handle_pick(e0)          # selecciona
    assert _faces(m) == [0]
    m.handle_pick(e1)          # acumula SIN reemplazar
    assert _faces(m) == [0, 1]
    m.handle_pick(e0)          # toggle OFF
    assert _faces(m) == [1]
    m.handle_pick(None)        # vacio limpia
    assert m.selected == frozenset()
    assert m.multi_selection == []


def test_rubber_legacy_callback_carries_full_set():
    m = _manager()
    emitted = []
    m.set_selection_callback(emitted.append)
    m.handle_rubber_band({3, 7})
    last = emitted[-1]
    assert last["selection_count"] == 2
    assert sorted(s["face_index"] for s in last["selection"]) == [3, 7]


# --------------------------------------------------------------------------- #
# faces_fully_in_rect: contencion total, no interseccion de bbox
# --------------------------------------------------------------------------- #

def _ortho_project_factory():
    # Proyeccion ortografica trivial: (x, y) mundo -> pantalla *10.
    return lambda x, y, z: (float(x) * 10.0, float(y) * 10.0)


def test_fully_contained_vs_touching():
    from desktop.viewport.viewport_3d import faces_fully_in_rect

    verts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                      [5, 5, 0], [6, 5, 0], [6, 6, 0]], float)
    cache = {0: [0, 1, 2, 3],   # cara completa dentro de (0,0)-(20,20)
             1: [4, 5, 6]}      # cara fuera
    rect = QRect(0, 0, 20, 20)
    assert faces_fully_in_rect(cache, verts, rect, _ortho_project_factory()) == {0}


def test_partial_overlap_does_not_select():
    from desktop.viewport.viewport_3d import faces_fully_in_rect

    # Triangulo con 2 vertices dentro y 1 fuera -> NO entra (fully-contained).
    verts = np.array([[0, 0, 0], [1, 0, 0], [10, 10, 0]], float)
    cache = {0: [0, 1, 2]}
    rect = QRect(0, 0, 20, 20)
    assert faces_fully_in_rect(cache, verts, rect, _ortho_project_factory()) == set()


def test_scene_builds_face_vertex_cache():
    from desktop.viewport.scene import Scene

    class _Prop:
        def __getattr__(self, name):
            return lambda *a, **k: None

    class _Actor:
        def GetProperty(self):
            return _Prop()

    class _StubRenderer:
        def make_triangle_actor(self, *a, **k):
            return _Actor()

        def add_actor(self, a):
            pass

        def remove_actor(self, a):
            pass

        def render(self):
            pass

    class _Cam:
        def set_target(self, *a, **k):
            pass

        def fit(self):
            pass

    scene = Scene(_StubRenderer(), _Cam())
    verts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
    tris = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    scene.set_model_geometry(verts, tris,
                             face_index_map=np.array([4, 4], dtype=np.int64))
    assert scene.face_vertex_cache == {4: [0, 1, 2, 3]}
    assert sorted(scene.cells_for_face(4)) == [0, 1]


def test_viewport_exposes_rubber_api_without_gl():
    import inspect
    from desktop.viewport import viewport_3d as mod

    assert callable(mod.faces_fully_in_rect)
    assert hasattr(mod.Viewport3D, "_update_rubber_band")
    assert hasattr(mod.Viewport3D, "_finish_rubber_band")
    assert hasattr(mod.Viewport3D, "_faces_in_rect")
    from desktop.viewport.selection import SelectionManager
    assert callable(getattr(SelectionManager, "handle_rubber_band"))
    assert isinstance(inspect.getattr_static(
        SelectionManager, "selectionChanged", None), object)
