"""Actor-pick: el picker golpea TODOS los actores del renderer (grid, ejes,
overlays), no solo el modelo. Sin validar el actor, un click sobre el grid
(de cell_id valido en ESA malla) se indexaba ciegamente como triangulo del
modelo -> cara arbitraria ("desmarca una pero marca otra").

Cubre: resolve_pick_entity, SetPickable(False) en grid/ejes/outline/overlay,
y el escenario reportado (click en grid limpia, no selecciona cara aleatoria).
Sin GPU: logica pura + construccion VTK headless (sin render).
"""

from __future__ import annotations

import numpy as np


MODEL = object()
GRID = object()
AXES = object()
OVERLAY = object()
UNKNOWN = object()


class _StubScene:
    _model_actor_key = "model:m"
    _actors = {"model:m": MODEL, "grid": GRID, "axes": AXES,
               "selection_highlight": OVERLAY}

    def __init__(self, cell_to_face):
        self._cell_to_face = dict(cell_to_face)

    def actor_key_for(self, actor):
        # Misma implementacion que Scene.actor_key_for (contrato).
        from desktop.viewport.scene import Scene
        return Scene.actor_key_for(self, actor)

    def face_index_for_cell(self, cell_id):
        return self._cell_to_face.get(int(cell_id))

    def face_meta(self, fi):
        return {"id": f"face_{fi}", "center": [0, 0, 0],
                "normal": [0, 0, 1], "area": 1.0}


def _scene():
    return _StubScene({0: 3, 1: 7})


# --------------------------------------------------------------------------- #
# resolve_pick_entity
# --------------------------------------------------------------------------- #

def test_grid_hit_resolves_to_empty_not_random_face():
    from desktop.viewport.viewport_3d import resolve_pick_entity
    # cell_id 1 existe en el modelo (cara 7): sobre el GRID debe ser vacio.
    assert resolve_pick_entity(GRID, 1, _scene()) is None
    assert resolve_pick_entity(AXES, 0, _scene()) is None
    assert resolve_pick_entity(OVERLAY, 0, _scene()) is None
    assert resolve_pick_entity(UNKNOWN, 0, _scene()) is None


def test_model_hit_resolves_to_face():
    from desktop.viewport.viewport_3d import resolve_pick_entity
    ent = resolve_pick_entity(MODEL, 0, _scene())
    assert ent is not None
    assert ent.face_index == 3


def test_miss_and_gap():
    from desktop.viewport.viewport_3d import KEEP_SELECTION, resolve_pick_entity
    s = _scene()
    assert resolve_pick_entity(None, -1, s) is None
    assert resolve_pick_entity(None, 5, s) is None
    assert resolve_pick_entity(MODEL, -1, s) is None
    # Modelo golpeado pero celda sin cara (hueco): conservar seleccion.
    assert resolve_pick_entity(MODEL, 99, s) is KEEP_SELECTION


def test_click_on_grid_clears_instead_of_selecting_random_face():
    """Escenario reportado: cara 3 seleccionada, click en grid (vacio
    aparente) -> seleccion vacia, no una cara arbitraria."""
    from desktop.viewport.selection import SelectionManager
    from desktop.viewport.viewport_3d import resolve_pick_entity
    from core.cad_entity import CadEntityRef

    class _R:
        def GetSize(self):
            return (800, 600)

        def AddActor(self, a):
            pass

        def RemoveActor(self, a):
            pass

        def Render(self):
            pass

    m = SelectionManager(_R())
    m.attach(_scene())
    m.handle_pick(CadEntityRef.from_face(3, model_id="model:m"), False)
    assert {e.face_index for e in m.selected} == {3}

    entity = resolve_pick_entity(GRID, 1, m._scene)  # grid bajo el cursor
    assert entity is None
    m.handle_pick(entity, additive=False)
    assert m.selected == frozenset()


def test_scene_actor_key_for_contract():
    from desktop.viewport.scene import Scene
    s = _StubScene({})
    assert Scene.actor_key_for(s, MODEL) == "model:m"
    assert Scene.actor_key_for(s, GRID) == "grid"
    assert Scene.actor_key_for(s, UNKNOWN) is None
    assert Scene.actor_key_for(s, None) is None


# --------------------------------------------------------------------------- #
# Defensa en profundidad: decoradores no pickeables (construccion headless)
# --------------------------------------------------------------------------- #

def test_grid_and_axes_not_pickable():
    from desktop.viewport.renderer import Renderer
    r = Renderer.__new__(Renderer)
    assert r.create_grid(10.0, 5).GetPickable() == 0
    assert r.create_axes(2.0).GetPickable() == 0


def test_identification_outline_not_pickable():
    from vtkmodules.vtkFiltersSources import vtkCubeSource
    from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
    from desktop.viewport.selection import SelectionManager

    class _R:
        def AddActor(self, a):
            pass

        def RemoveActor(self, a):
            pass

        def Render(self):
            pass

    box = vtkCubeSource()
    box.SetBounds(0, 1, 0, 1, 0, 1)
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(box.GetOutputPort())
    actor = vtkActor()
    actor.SetMapper(mapper)

    m = SelectionManager(_R())
    m._build_identification(actor)
    assert m._multi_identifications[-1].GetPickable() == 0


def test_highlight_overlay_not_pickable():
    from desktop.viewport.scene import Scene

    calls = {}

    class _Actor:
        def GetProperty(self):
            class _P:
                def __getattr__(self, name):
                    return lambda *a, **k: None
            return _P()

        def SetPickable(self, v):
            calls["pickable"] = v

        def GetMapper(self):
            return None

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
                             face_index_map=np.array([2, 2], dtype=np.int64))
    scene.highlight_faces([2])
    assert calls.get("pickable") is False
