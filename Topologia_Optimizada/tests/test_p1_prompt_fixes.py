"""Tests P1 (prompts.md): multi-select clic normal, picking, cierre, mallador."""

from __future__ import annotations


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
        self.highlighted = []
        self.cleared = 0

    def face_index_for_cell(self, cell_id):
        return {0: 0, 1: 1, 2: 2}.get(cell_id)

    def face_meta(self, fi):
        return {"id": f"face_{fi}", "center": [0, 0, 0],
                "normal": [0, 0, 1], "area": 1.0}

    def highlight_faces(self, faces):
        self.highlighted = list(faces)

    def clear_highlight(self):
        self.highlighted = []
        self.cleared += 1


def _manager():
    from desktop.viewport.selection import SelectionManager
    m = SelectionManager(_FakeRenderer())
    m.attach(_FakeScene())
    return m


def _payload(face):
    return {"key": "m", "kind": "face", "face_index": face,
            "cad_entity": None, "actor": None}


def test_pick_tolerance_not_ultrastrict():
    from desktop.viewport import selection as selmod
    assert selmod.PICK_TOLERANCE >= 0.01


def test_click_normal_accumulates_multiple_faces():
    m = _manager()
    emitted = []
    m.set_selection_callback(emitted.append)
    m._toggle_multi(_payload(0))
    m._toggle_multi(_payload(1))
    m._toggle_multi(_payload(2))
    assert len(m.multi_selection) == 3
    # callback emits dict (not list) for MainWindow compat
    assert isinstance(emitted[-1], dict)
    assert emitted[-1]["face_index"] == 2


def test_click_again_toggles_off():
    m = _manager()
    m._toggle_multi(_payload(0))
    m._toggle_multi(_payload(1))
    m._toggle_multi(_payload(0))  # quitar
    faces = sorted(s["face_index"] for s in m.multi_selection)
    assert faces == [1]


def test_toggle_last_off_emits_none():
    m = _manager()
    emitted = []
    m.set_selection_callback(emitted.append)
    m._toggle_multi(_payload(0))
    m._toggle_multi(_payload(0))
    assert m.multi_selection == []
    assert emitted[-1] is None


def test_renderer_keeps_cell_count_with_face_index():
    import numpy as np
    from desktop.viewport.renderer import Renderer
    r = Renderer.__new__(Renderer)
    verts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
    tris = np.array([[0, 1, 2], [0, 2, 3]])
    poly = r._build_polydata(verts, tris, compute_normals=True,
                             cell_data={"face_index": np.array([0, 1])})
    assert poly.GetNumberOfCells() == 2
    arr = poly.GetCellData().GetArray("face_index")
    assert arr is not None
    assert [arr.GetValue(i) for i in range(2)] == [0, 1]


def test_close_model_clears_controller_state():
    from desktop.pipeline.controller import PipelineController
    c = PipelineController.__new__(PipelineController)
    from core.document import Document
    from core.features import FeatureHistory, Feature
    from core.conditions import ConditionManager
    from services.cad_service import CADService
    c.cad = CADService()
    c.model_id = "mid"
    c.model_name = "m"
    c.current_tessellation = {"vertices": [1]}
    c.mesh = {"success": True}
    import numpy as np
    c.mesh_nodes = np.zeros((2, 3))
    c.mesh_elements = np.zeros((1, 4), dtype=int)
    c.result = {"success": True}
    c.result_densities = np.zeros(1)
    c.forces = [{"a": 1}]
    c.constraints = [{"b": 2}]
    c._bot_nodes = [1]
    c._load_nodes = [2]
    c._studies = {"s": object()}
    c.conditions = ConditionManager()
    c.feature_history = FeatureHistory()
    c.document = Document()
    c.cad._model_cache["mid"] = object()
    closed = c.close_model()
    assert closed == "mid"
    assert c.model_id is None
    assert c.mesh is None and c.mesh_nodes is None
    assert c.forces == [] and c.constraints == []
    assert c._studies == {}
    assert len(c.conditions) == 0 and len(c.feature_history) == 0
    assert "mid" not in c.cad._model_cache


def test_second_step_after_close_starts_clean():
    from services.cad_service import CADService
    svc = CADService()
    svc._model_cache["A"] = object()
    svc.step_adapter.cache_shape("A", object())
    svc.close_model("A")
    assert "A" not in svc._model_cache
    assert svc.step_adapter.get_shape("A") is None


def test_mesher_diagnostics_keys_present():
    from services.cad_service import CADService
    from core.meshing import MeshResult
    svc = CADService()
    calls = {}

    class _Prov:
        def generate_mesh(self, shape, target_element_size=2.0, element_type="tet4"):
            calls["tgt"] = target_element_size
            return MeshResult(nodes=[[0, 0, 0]], elements=[[0, 0, 0, 0]],
                              num_nodes=1, num_elements=1,
                              is_provisional=True,
                              metadata={"mesher": "ProvisionalTet4Mesher"})
    svc.provisional_mesher = _Prov()
    d = svc.generate_mesh_for_shape(object(), target_element_size=3.0,
                                    element_type="hex8")
    assert d["success"] is True
    assert d["mesher"] == "ProvisionalTet4Mesher"
    assert d["fallback"] is True
    assert d["fallback_reason"]
    assert d["target_element_size"] == 3.0
    assert d["num_nodes"] == 1 and d["num_elements"] == 1


def test_gmsh_failure_fallback_reports_reason():
    from services.cad_service import CADService
    from core.meshing import MeshResult
    svc = CADService()

    class _Gmsh:
        def generate_mesh(self, *a, **k):
            raise RuntimeError("no gmsh here")

    class _Prov:
        def generate_mesh(self, shape, target_element_size=2.0, element_type="tet4"):
            return MeshResult(nodes=[[0, 0, 0]], elements=[[0, 0, 0, 0]],
                              num_nodes=1, num_elements=1,
                              is_provisional=True,
                              metadata={"mesher": "ProvisionalTet4Mesher"})
    svc.gmsh_mesher = _Gmsh()
    svc.provisional_mesher = _Prov()
    d = svc.generate_mesh_for_shape(object(), target_element_size=2.0,
                                    element_type="tet4")
    assert d["fallback"] is True
    assert "no gmsh here" in d["fallback_reason"]
