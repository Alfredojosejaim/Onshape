"""UI connection tests for the formerly-decorative "Validar" ribbon tool.

Regresión: ``rb_validate`` used to show a static status-bar message regardless
of the real model state. It is now wired to a real handler that reflects the
actual controller state (model / mesh / conditions / result).
"""

from __future__ import annotations

import os


def _make_window():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import desktop.ui.main_window as mw
    from desktop.viewport.software_viewport import SoftwareViewport, _SoftwareSelectionManager

    _Noop = lambda *a, **k: None
    _SoftwareSelectionManager.set_solid_resolver = _Noop

    class _FakeViewport(SoftwareViewport):
        def __init__(self, *a, **k):
            super().__init__()

        def finalize(self):
            pass

    mw.Viewport3D = _FakeViewport
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return mw.MainWindow()


def test_validate_button_connected_to_real_handler(monkeypatch):
    w = _make_window()
    try:
        # Clicking the ribbon tool must reach the real handler: it updates the
        # status bar with the live model state and raises the validation dialog,
        # instead of the former static "verificando geometría..." message.
        captured = {}
        import PySide6.QtWidgets as _qw
        monkeypatch.setattr(
            _qw.QMessageBox, "information",
            lambda parent, title, text: captured.update(title=title, text=text),
        )
        assert hasattr(w, "_on_validate")
        w.rb_validate.click()
        assert "Validación" in captured.get("title", "")
        assert "SIN MODELO" in captured["text"] or "Modelo: ninguno" in captured["text"]
    finally:
        w.close()


def test_validate_without_model_reports_state(monkeypatch):
    w = _make_window()
    try:
        captured = {}
        import PySide6.QtWidgets as _qw
        monkeypatch.setattr(
            _qw.QMessageBox, "information",
            lambda parent, title, text: captured.update(title=title, text=text),
        )
        assert not w.controller.model_id
        w._on_validate()
        assert "SIN MODELO" in captured["text"]
        assert captured["title"] == "Validación del modelo"
    finally:
        w.close()


def test_validate_loads_real_mesh_and_conditions(monkeypatch):
    """With a loaded model the state must come from the live controller, not a
    static string."""
    w = _make_window()
    try:
        # Fake an imported model + mesh so the validator reads real controller data.
        w.controller.model_id = "m1"
        w.controller.model_name = "prueba"
        w.controller.mesh_nodes = __import__("numpy").zeros((10, 3))
        w.controller.mesh_elements = __import__("numpy").zeros((5, 4), dtype=int)
        w.controller.forces = [{}]
        w.controller.constraints = [{}]

        captured = {}
        import PySide6.QtWidgets as _qw
        monkeypatch.setattr(
            _qw.QMessageBox, "information",
            lambda parent, title, text: captured.update(title=title, text=text),
        )

        def _fake_solids(mid):
            return ["solid1", "solid2"]

        monkeypatch.setattr(w.controller.cad, "list_solids", _fake_solids)

        w._on_validate()
        assert "Sólidos: 2" in captured["text"]
        assert "10 nodos, 5 elementos" in captured["text"]
    finally:
        w.close()
