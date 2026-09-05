"""Indicador de backend del viewport (prompts.md): log al arranque + pill en
el badge + aviso en status bar si cae al fallback. Sin GPU real: OverlayBuilder
con host stub, Qt offscreen.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from desktop.ui.components.overlays import OverlayBuilder


@pytest.fixture(scope="module")
def _app():
    app = QApplication.instance() or QApplication([])
    return app


class _StubViewport:
    def fit_to_view(self):
        pass

    def set_display_mode(self, mode):
        pass

    def toggle_axes(self, visible):
        pass


class _StubHost:
    def __init__(self, use_vtk: bool):
        self._use_vtk = use_vtk
        self.viewport = _StubViewport()
        self.placed = {}

    def place(self, slot, widget):
        self.placed[slot] = widget


class _StubOwner:
    def _sync_sidebar_vis(self, kind, on):
        pass


def _badge_texts(_app, use_vtk: bool):
    host = _StubHost(use_vtk)
    OverlayBuilder(_StubOwner(), host).build()
    badge = host.placed["badge"]
    return [w.text() for w in badge.findChildren(QLabel)], badge


def test_badge_shows_vtk_backend(_app):
    texts, _badge = _badge_texts(_app, True)
    assert "GPU · VTK" in texts


def test_badge_shows_software_fallback_with_warning(_app):
    texts, badge = _badge_texts(_app, False)
    assert "Software · sin GPU" in texts
    pills = [w for w in badge.findChildren(QLabel)
             if w.text() == "Software · sin GPU"]
    assert pills and "#e0a030" in pills[0].styleSheet()


def test_main_window_logs_backend():
    import inspect
    import desktop.ui.main_window as mw
    src = inspect.getsource(mw.MainWindow._build_central)
    assert "Viewport backend:" in src
    assert "_use_vtk" in src
    init_src = inspect.getsource(mw.MainWindow.__init__)
    assert "renderer por software" in init_src
