"""Tests Fase 4.5d.4-5: toggle térmico + animación modal (UI desktop).

- Scene: la animación actúa SOLO sobre el actor "mesh" (nunca B-Rep/densidad),
  cada frame es base + desplazamiento (sin acumulación), end restaura la base.
- Controller.resolve_thermal_kwargs: fail-loud (tipo, estado, campo, malla, α).
- Paneles Qt (offscreen): sección modal visible solo con modos; toggle
  térmico deshabilitado con tooltip si no hay Thermal COMPLETED.
"""

import numpy as np
import pytest

NODES = np.array([
    [0.0, 0.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.0, 1.0, 1.0],
], dtype=float)
ELEMENTS = np.array([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=int)


# ------------------------------------------------------------------ Scene
class _HeadlessRenderer:
    """Renderer real para construir actores, sin ventana (render no-op)."""

    def __init__(self):
        from desktop.viewport.renderer import Renderer
        self._real = Renderer()

    def __getattr__(self, name):
        if name == "render":
            return lambda: None
        if name in ("add_actor", "remove_actor"):
            return lambda *a, **k: None
        return getattr(self._real, name)


def _make_scene():
    from desktop.viewport.scene import Scene
    return Scene(_HeadlessRenderer(), None)


def _mesh_points(scene):
    for key, obj in scene._objects.items():
        if obj.kind == "mesh":
            poly = scene._actors[key].GetMapper().GetInput()
            n = poly.GetPoints().GetNumberOfPoints()
            out = np.zeros((n, 3))
            for i in range(n):
                out[i] = poly.GetPoints().GetPoint(i)
            return out
    raise AssertionError("sin actor mesh")


def test_scene_no_mesh_no_animation():
    scene = _make_scene()
    ok, reason = scene.begin_mode_animation()
    assert ok is False and "malla" in reason.lower()


def test_scene_animates_mesh_not_density_and_restores_base():
    scene = _make_scene()
    scene.set_mesh(NODES, ELEMENTS)
    scene.set_density_field(NODES, ELEMENTS, np.array([0.5, 0.7]))
    ok, reason = scene.begin_mode_animation()
    assert ok, reason
    base = _mesh_points(scene)
    assert np.allclose(base, NODES)
    d1 = np.zeros_like(NODES)
    d1[:, 0] = 0.1
    scene.apply_mode_displacement(d1)
    assert np.allclose(_mesh_points(scene), NODES + d1)
    # Segundo frame parte de la base, no acumula sobre el anterior.
    d2 = np.zeros_like(NODES)
    d2[:, 1] = -0.2
    scene.apply_mode_displacement(d2)
    assert np.allclose(_mesh_points(scene), NODES + d2)
    scene.end_mode_animation()
    assert np.allclose(_mesh_points(scene), NODES)


def test_scene_bad_displacement_rejected():
    scene = _make_scene()
    scene.set_mesh(NODES, ELEMENTS)
    scene.begin_mode_animation()
    with pytest.raises(ValueError):
        scene.apply_mode_displacement(np.zeros((3, 3)))
    with pytest.raises(ValueError):
        scene.apply_mode_displacement(np.full_like(NODES, np.nan))
    with pytest.raises(RuntimeError):
        fresh = _make_scene()
        fresh.apply_mode_displacement(np.zeros_like(NODES))


# ------------------------------------------------- resolve_thermal_kwargs
def _make_controller(mesh_nodes, studies, mat_alpha):
    from types import SimpleNamespace
    from desktop.pipeline.controller import PipelineController
    c = PipelineController.__new__(PipelineController)
    c._studies = {s.id: s for s in studies}
    c.mesh_nodes = np.asarray(mesh_nodes, dtype=float)
    c.material = lambda: SimpleNamespace(thermal_expansion=mat_alpha)
    return c


def _thermal_study(sid, status, temps=None):
    from types import SimpleNamespace
    from core.cae_studies import StudyStatus, StudyType, StudyResult
    s = SimpleNamespace(
        id=sid, name=f"T-{sid}", study_type=StudyType.THERMAL,
        status=status,
        result=StudyResult(success=True, status="completed",
                           data={"temperatures": temps} if temps is not None else {}),
        thermal_alpha_override=None,
        thermal_reference_temperature_override=293.15,
    )
    return s


def test_thermal_kwargs_ok_and_alpha_override():
    from core.cae_studies import StudyStatus
    temps = [300.0] * 5
    s = _thermal_study("t1", StudyStatus.COMPLETED, temps)
    c = _make_controller(NODES, [s], mat_alpha=12e-6)
    kw = c.resolve_thermal_kwargs("t1")
    assert np.allclose(kw["thermal_temperatures"], temps)
    assert kw["thermal_alpha"] == pytest.approx(12e-6)
    s.thermal_alpha_override = 23e-6
    kw = c.resolve_thermal_kwargs("t1")
    assert kw["thermal_alpha"] == pytest.approx(23e-6)


def test_thermal_kwargs_fail_loud():
    from types import SimpleNamespace
    from core.cae_studies import StudyStatus, StudyType
    from desktop.pipeline.controller import PipelineError
    good = _thermal_study("t1", StudyStatus.COMPLETED, [300.0] * 5)
    c = _make_controller(NODES, [good], mat_alpha=12e-6)
    with pytest.raises(PipelineError):
        c.resolve_thermal_kwargs("no-existe")
    with pytest.raises(PipelineError):
        c.resolve_thermal_kwargs("")
    running = _thermal_study("t2", StudyStatus.RUNNING, [300.0] * 5)
    c._studies["t2"] = running
    with pytest.raises(PipelineError):
        c.resolve_thermal_kwargs("t2")
    nofield = _thermal_study("t3", StudyStatus.COMPLETED, None)
    c._studies["t3"] = nofield
    with pytest.raises(PipelineError):
        c.resolve_thermal_kwargs("t3")
    short = _thermal_study("t4", StudyStatus.COMPLETED, [300.0] * 3)
    c._studies["t4"] = short
    with pytest.raises(PipelineError):
        c.resolve_thermal_kwargs("t4")
    modal = SimpleNamespace(id="m1", study_type=StudyType.MODAL,
                            status=StudyStatus.COMPLETED, result=None)
    c._studies["m1"] = modal
    with pytest.raises(PipelineError):
        c.resolve_thermal_kwargs("m1")
    c_no_alpha = _make_controller(NODES, [good], mat_alpha=None)
    with pytest.raises(PipelineError):
        c_no_alpha.resolve_thermal_kwargs("t1")


# ------------------------------------------------------------------ Qt
def _qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    return app or QApplication([])


def test_results_modal_section_visibility():
    _qapp()
    from desktop.ui_legacy.panels.results import ResultsPanel
    r = ResultsPanel()
    assert r._anim_section.isHidden()
    r.set_modal_modes(["Modo 1 — 10.0 Hz", "Modo 2 — 25.0 Hz"])
    assert not r._anim_section.isHidden()
    assert r.animation_mode_index() == 0
    assert r.animation_speed() == pytest.approx(1.0)
    r.clear_modal_modes()
    assert r._anim_section.isHidden()


def test_properties_thermal_toggle_gating():
    _qapp()
    from desktop.ui_legacy.panels.properties import PropertiesPanel
    p = PropertiesPanel()
    p.set_thermal_studies([])
    assert not p._thermal_enable.isEnabled()
    assert not p.thermal_enabled()
    assert p.thermal_study_id() is None
    assert "Thermal" in p._thermal_enable.toolTip()
    p.set_thermal_studies([("id1", "Térmico A")])
    assert p._thermal_enable.isEnabled()
    p._thermal_enable.setChecked(True)
    assert p.thermal_enabled()
    assert p.thermal_study_id() == "id1"
    assert p.thermal_alpha() is None  # 0 = auto (material)
