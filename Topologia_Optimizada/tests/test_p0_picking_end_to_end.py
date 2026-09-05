"""P0 (picking real + multi-selección end-to-end, prompts P0-§1-§4).

Flujo ejercitado (el más cercano posible al evento real sin GPU):

    script CellId → SelectionManager.pick(x, y, ctrl=False) → VTK-CellId →
    face_index_map → CadEntityRef → _toggle_multi → callback → highlight

Qué queda fuera de automatización (documentado): el widget Qt real
(``Viewport3D._on_left_release`` → ``QVTKInteractor.GetControlKey``) y el
``vtkCellPicker`` nativo requieren render GPU/ventana; aquí se sustituye
únicamente el picker por un doble programable que devuelve ``CellId`` por
clic, igual que haría VTK bajo el cursor. Todo lo demás (``pick``,
``face_index_for_cell``, ``_toggle_multi``, callback, highlight) es código
real sin mocks.
"""

from __future__ import annotations

import pytest


ACTOR = object()


class ScriptedPicker:
    """Doble de vtkCellPicker: programa qué (actor, CellId) hay bajo el cursor."""

    def __init__(self):
        self.script = []  # [(actor|None, cell_id|None)] o [None] = miss
        self._actor = None
        self._cell = None

    def queue_click(self, actor=ACTOR, cell_id=None):
        self.script.append((actor, cell_id))

    def queue_miss(self):
        self.script.append(None)

    def Pick(self, x, y, z, renderer):
        if not self.script:
            raise AssertionError("click sin CellId programado en el script")
        hit = self.script.pop(0)
        if hit is None:
            self._actor, self._cell = None, None
            return False
        self._actor, self._cell = hit
        return True

    def GetActor(self):
        return self._actor

    def GetCellId(self):
        return self._cell


class FakeRenderer:
    def GetSize(self):
        return (800, 600)

    def AddActor(self, a):
        pass

    def RemoveActor(self, a):
        pass

    def Render(self):
        pass


class FakeScene:
    """Escena con N caras; CellIds deliberadamente != face_index."""

    _model_actor_key = "model_A"

    def __init__(self, cell_to_face):
        self._cell_to_face = dict(cell_to_face)
        self._actors = {"model_A": ACTOR}
        self.highlight_calls = []

    def face_index_for_cell(self, cell_id):
        return self._cell_to_face.get(int(cell_id))

    def face_meta(self, fi):
        return {"id": f"face_{fi}", "center": [fi, 0, 0],
                "normal": [0, 0, 1], "area": float(fi + 1)}

    def highlight_faces(self, faces):
        self.highlight_calls.append(sorted(int(f) for f in faces))

    def clear_highlight(self):
        self.highlight_calls.append([])


def _manager(cell_to_face):
    from desktop.viewport.selection import SelectionManager
    m = SelectionManager(FakeRenderer())
    m.attach(FakeScene(cell_to_face))
    picker = ScriptedPicker()
    m._picker = picker
    return m, picker


def _faces(m):
    return sorted(s["face_index"] for s in m.multi_selection)


def test_1_real_click_selects_one_face():
    m, picker = _manager({10: 3, 11: 7, 12: 9})
    emitted = []
    m.set_selection_callback(emitted.append)
    picker.queue_click(cell_id=10)
    m.pick(100, 100, ctrl=False)  # clic NORMAL, sin modificadores
    assert _faces(m) == [3]
    # El face_index coincide con la cara clickeada, no con el CellId.
    assert emitted[-1]["face_index"] == 3
    assert emitted[-1]["cad_entity"].face_index == 3
    # Feedback visual == selección real.
    assert m._scene.highlight_calls[-1] == [3]


def test_2_second_normal_click_accumulates():
    m, picker = _manager({10: 3, 11: 7, 12: 9})
    emitted = []
    m.set_selection_callback(emitted.append)
    picker.queue_click(cell_id=10)
    m.pick(100, 100, ctrl=False)
    picker.queue_click(cell_id=11)
    m.pick(150, 120, ctrl=False)
    assert _faces(m) == [3, 7]
    # Callback entrega la selección completa actualizada, no solo la última.
    assert sorted(s["face_index"] for s in emitted[-1]["selection"]) == [3, 7]
    assert emitted[-1]["selection_count"] == 2
    # Todas las caras acumuladas siguen resaltadas.
    assert m._scene.highlight_calls[-1] == [3, 7]


def test_3_three_faces_and_middle_toggle_off():
    m, picker = _manager({10: 3, 11: 7, 12: 9})
    m.set_selection_callback(lambda p: None)
    for cell in (10, 11, 12):
        picker.queue_click(cell_id=cell)
        m.pick(0, 0, ctrl=False)
    assert _faces(m) == [3, 7, 9]
    assert m._scene.highlight_calls[-1] == [3, 7, 9]
    # Toggle sobre la cara intermedia la elimina; el resto sigue.
    picker.queue_click(cell_id=11)
    m.pick(0, 0, ctrl=False)
    assert _faces(m) == [3, 9]
    assert m._scene.highlight_calls[-1] == [3, 9]


def test_4_removing_last_face_yields_empty_selection():
    m, picker = _manager({10: 3, 11: 7})
    emitted = []
    m.set_selection_callback(emitted.append)
    picker.queue_click(cell_id=10)
    m.pick(0, 0, ctrl=False)
    picker.queue_click(cell_id=11)
    m.pick(0, 0, ctrl=False)
    picker.queue_click(cell_id=10)
    m.pick(0, 0, ctrl=False)
    assert _faces(m) == [7]
    picker.queue_click(cell_id=11)
    m.pick(0, 0, ctrl=False)
    assert m.multi_selection == []
    assert emitted[-1] is None
    assert m._scene.highlight_calls[-1] == []


def test_5_callback_full_state_matches_manager_state_each_click():
    m, picker = _manager({10: 3, 11: 7, 12: 9})
    emitted = []
    m.set_selection_callback(emitted.append)
    for cell in (10, 11, 12, 11):  # añade 3, quita la intermedia
        picker.queue_click(cell_id=cell)
        m.pick(0, 0, ctrl=False)
        last = emitted[-1]
        if not m.multi_selection:
            assert last is None
        else:
            assert sorted(s["face_index"] for s in last["selection"]) == _faces(m)
            assert last["selection_count"] == len(m.multi_selection)


def test_7_condition_panel_receives_complete_selection():
    """Lo que ConditionPanel captura (vía _current_face_selections: filtra
    cad_entity FACE de multi_selection) == selección completa acumulada,
    y no se contamina entre condiciones (capturas sucesivas)."""
    from core.cad_entity import EntityType
    m, picker = _manager({10: 3, 11: 7, 12: 9})
    m.set_selection_callback(lambda p: None)
    for cell in (10, 11):
        picker.queue_click(cell_id=cell)
        m.pick(0, 0, ctrl=False)

    def current_face_selections():  # misma lógica que MainWindow
        refs = []
        src = m.multi_selection if m.multi_selection else []
        for item in src:
            ce = item.get("cad_entity")
            if ce is not None and ce.entity_type == EntityType.FACE:
                refs.append(ce)
        return refs

    first_capture = current_face_selections()
    assert sorted(r.face_index for r in first_capture) == [3, 7]
    # Segunda condición tras añadir otra cara: ve el estado completo nuevo.
    picker.queue_click(cell_id=12)
    m.pick(0, 0, ctrl=False)
    second_capture = current_face_selections()
    assert sorted(r.face_index for r in second_capture) == [3, 7, 9]
    assert len(first_capture) == 2  # la captura anterior no mutó


def test_9_many_faces_no_wrong_index_from_cellid():
    # 12 caras; CellIds 100..111 mapean a faces 0..11 en orden inverso.
    mapping = {100 + i: 11 - i for i in range(12)}
    m, picker = _manager(mapping)
    m.set_selection_callback(lambda p: None)
    for i in range(12):
        picker.queue_click(cell_id=100 + i)
        out = m.pick(i, i, ctrl=False)
        assert out["face_index"] == 11 - i
    assert _faces(m) == list(range(12))
    assert m._scene.highlight_calls[-1] == list(range(12))


def test_click_miss_keeps_nothing_and_clears():
    m, picker = _manager({10: 3})
    emitted = []
    m.set_selection_callback(emitted.append)
    picker.queue_click(cell_id=10)
    m.pick(0, 0, ctrl=False)
    assert _faces(m) == [3]
    picker.queue_miss()  # clic al vacío con botón normal
    assert m.pick(500, 500, ctrl=False) is None
    assert m.multi_selection == []
    assert emitted[-1] is None
