"""UI integration connection tests.

Validate the functional connections that were (re-)wired so that a button or
signal is not merely visual: the panel must carry the real payload through to
the shared state that FEA / SIMP consume.
"""

from __future__ import annotations

import os


def _qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# --------------------------------------------------------------------------- #
# TimelinePanel: the center play button must advance the guided flow.
# --------------------------------------------------------------------------- #
def test_timeline_play_button_emits_play_requested():
    from PySide6.QtTest import QSignalSpy
    _qapp()
    from desktop.ui.panels.timeline import TimelinePanel

    panel = TimelinePanel()
    spy = QSignalSpy(panel.playRequested)
    assert spy.isValid()
    # The previously-orphaned center play button must emit playRequested.
    panel._btn_play.click()
    assert spy.count() == 1
    # "Ejecutar" (next) also emits the same signal.
    panel._btn_next.click()
    assert spy.count() == 2


def test_timeline_reset_emits_reset_requested():
    from PySide6.QtTest import QSignalSpy
    _qapp()
    from desktop.ui.panels.timeline import TimelinePanel

    panel = TimelinePanel()
    spy = QSignalSpy(panel.resetRequested)
    panel._btn_prev.click()
    assert spy.count() == 1


# --------------------------------------------------------------------------- #
# PropertiesPanel: "+ Agregar Fuerza" / "+ Agregar Restricción" emit the
# configured boundary values so MainWindow persists them into the controller.
# --------------------------------------------------------------------------- #
def test_properties_add_force_emits_values():
    from PySide6.QtTest import QSignalSpy
    _qapp()
    from desktop.ui.panels.properties import PropertiesPanel

    panel = PropertiesPanel()
    spy = QSignalSpy(panel.forceAdded)
    assert spy.isValid()

    panel._force_mag.setValue(2500.0)
    panel._force_dx.setValue(1.0)
    panel._force_dy.setValue(2.0)
    panel._force_dz.setValue(3.0)
    panel._btn_add_force.click()

    assert spy.count() == 1
    args = spy.at(0)
    assert [float(a) for a in args] == [2500.0, 1.0, 2.0, 3.0]


def test_properties_add_constraint_emits_type():
    from PySide6.QtTest import QSignalSpy
    _qapp()
    from desktop.ui.panels.properties import PropertiesPanel

    panel = PropertiesPanel()
    spy = QSignalSpy(panel.constraintAdded)
    assert spy.isValid()

    panel._constraint.setCurrentIndex(0)  # Fija (Empotramiento) -> "fixed"
    panel._btn_add_constraint.click()
    assert spy.count() == 1
    assert spy.at(0)[0] == "fixed"


# --------------------------------------------------------------------------- #
# End-to-end contract: the panel signals reach the shared controller boundary
# state exactly as MainWindow._on_add_force / _on_add_constraint do.
# --------------------------------------------------------------------------- #
def test_force_added_reaches_shared_boundary_state():
    _qapp()
    from desktop.ui.panels.properties import PropertiesPanel

    class _FakeController:
        def __init__(self):
            self.forces = []
            self.constraints = []

    ctrl = _FakeController()
    panel = PropertiesPanel()

    # Mirror MainWindow's handler wiring.
    def _on_add_force(magnitude, dx, dy, dz):
        if not ctrl.forces:
            ctrl.forces = [{}]
        ctrl.forces[0].update(
            {"magnitude": magnitude, "direction_x": dx,
             "direction_y": dy, "direction_z": dz})

    panel.forceAdded.connect(_on_add_force)

    panel._force_mag.setValue(500.0)
    panel._force_dx.setValue(0.5)
    panel._force_dy.setValue(-1.0)
    panel._force_dz.setValue(0.0)
    panel._btn_add_force.click()

    assert ctrl.forces and ctrl.forces[0] == {
        "magnitude": 500.0, "direction_x": 0.5,
        "direction_y": -1.0, "direction_z": 0.0,
    }


def test_constraint_added_reaches_shared_boundary_state():
    _qapp()
    from desktop.ui.panels.properties import PropertiesPanel

    ctrl = type("C", (), {"constraints": []})()
    panel = PropertiesPanel()

    def _on_add_constraint(constraint_type):
        ctrl.constraints = [{
            "constraint_type": constraint_type,
            "location": "",
            "degrees_of_freedom": {"ux": True, "uy": True, "uz": True},
        }]

    panel.constraintAdded.connect(_on_add_constraint)

    panel._constraint.setCurrentIndex(1)  # Pinnada -> "pinned"
    panel._btn_add_constraint.click()

    assert len(ctrl.constraints) == 1
    assert ctrl.constraints[0]["constraint_type"] == "pinned"
