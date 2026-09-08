"""GenerativeStudyPanel: scenario A/B creation wiring (Fase 3a).

The generative engine existed without any UI scenario flow. This covers the
minimal panel: scenario A (existing geometry), scenario B (≥2 solid targets),
conditions referenced by id, and rejection paths.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _make_panel(parts=None, scenario="A", select_conditions=True):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from desktop.ui.panels.study_panel import GenerativeStudyPanel
    from core.conditions import ConditionManager, LoadCondition
    from core.cad_entity import CadEntityRef, EntityType

    mgr = ConditionManager()
    cond = LoadCondition(name="Carga test", magnitude=100.0)
    mgr.add(cond)
    panel = GenerativeStudyPanel(
        parent=None,
        condition_manager=mgr,
        default_name="GD test",
        parts=list(parts or []),
        model_id="model_1",
        get_solid_selections=lambda: list(parts or []),
    )
    idx = 0 if scenario == "A" else 1
    panel._scenario.setCurrentIndex(idx)
    if select_conditions:
        panel._cond_list.item(0).setSelected(True)
    panel._refresh_parts_list()
    return panel


def _solid(sid):
    from core.cad_entity import CadEntityRef, EntityType
    return CadEntityRef(entity_type=EntityType.SOLID, solid_id=sid, model_id="model_1")


def test_scenario_a_accepts_without_targets():
    panel = _make_panel(scenario="A")
    try:
        panel._on_accept()
        assert panel.study is not None
        assert panel.study.scenario == "A"
        assert panel.study.validate()
    finally:
        panel.close()


def test_scenario_b_requires_two_solids():
    panel = _make_panel(parts=[_solid("s1")], scenario="B")
    try:
        assert not panel._btn_ok.isEnabled()
        panel._on_accept()
        assert panel.study is None
        assert "2 sólidos" in panel._error.text()
    finally:
        panel.close()


def test_scenario_b_accepts_with_two_solids():
    panel = _make_panel(parts=[_solid("s1"), _solid("s2")], scenario="B")
    try:
        assert panel._btn_ok.isEnabled()
        panel._on_accept()
        assert panel.study is not None
        assert panel.study.scenario == "B"
        assert len(panel.study.connection_targets) == 2
        assert panel.study.validate()
    finally:
        panel.close()


def test_rejects_without_conditions():
    panel = _make_panel(scenario="A", select_conditions=False)
    try:
        panel._on_accept()
        assert panel.study is None
    finally:
        panel.close()
