"""main_workspace - composición física del workspace principal de MainWindow.

Extrae de MainWindow exclusivamente la parte **de presentación** de
`_build_central()`: la disposición de paneles del workspace (sidebar izquierdo,
área central viewport+timeline, panel derecho de resultados), los frames, los
márgenes/márgenes, los tamaños y proporciones.

La **coordinación** (conexión de señales de paneles/viewport/timeline, resolver
de selección, handlers `_on_*`, PipelineController y estado) siguen viviendo en
MainWindow, que recibe aquí un resultado con todas las referencias de widgets
para poder cablearlas después.

ANTES → DESPUÉS → CONEXIÓN PRESERVADA
  MainWindow._build_central (165-253)
      → MainWorkspaceBuilder(owner).build()  (solo composición + instancia de paneles)
      → MainWindow conserva el cableado funcional (conecta propiedades/timeline/
        viewport/design_tree) y setCentralWidget(central).

Referencias públicas preservadas (asignadas sobre el owner):
  self.design_tree / self.properties / self.results / self.timeline
  self.host / self.viewport
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
)
from PySide6.QtCore import Qt

from desktop.viewport.viewport_3d import Viewport3D, is_gl_available
from desktop.viewport.software_viewport import SoftwareViewport
from desktop.ui.panels.design_tree import DesignTreePanel
from desktop.ui.panels.properties import PropertiesPanel
from desktop.ui.panels.results import ResultsPanel
from desktop.ui.panels.timeline import TimelinePanel


class ViewportHost(QFrame):
    """Frames a Viewport3D (VTK) or SoftwareViewport (QPainter) with an inset
    margin and positions overlay widgets on top of the 3D area.

    Auto-selects the backend at construction time: tries VTK first, falls back
    to the software renderer if GL is unavailable or VTK fails to initialize.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("viewportContainer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 0)

        self._use_vtk = False
        self.viewport = None
        try:
            if is_gl_available():
                self.viewport = Viewport3D()
                self._use_vtk = True
        except Exception:
            self.viewport = None

        if self.viewport is None:
            self.viewport = SoftwareViewport()
            self._use_vtk = False

        lay.addWidget(self.viewport)
        self._slots: dict[str, QWidget] = {}
        self._pad = 12

    def place(self, slot: str, widget: QWidget) -> None:
        widget.setParent(self)
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._slots[slot] = widget
        self._layout_overlays()

    def _layout_overlays(self) -> None:
        r = self.rect()
        m = self._pad

        badge = self._slots.get("badge")
        if badge:
            badge.adjustSize()
            badge.move(m + 14, m + 12)

        controls = self._slots.get("controls")
        if controls:
            controls.adjustSize()
            controls.move(r.width() - m - controls.width() - 12, m + 70)

        pholder = self._slots.get("placeholder")
        if pholder and pholder.isVisible():
            pholder.adjustSize()
            pholder.move((r.width() - pholder.width()) // 2, (r.height() - pholder.height()) // 2)

        status = self._slots.get("status")
        if status:
            status.adjustSize()
            status.setFixedWidth(r.width() - m * 2)
            status.move(m, r.height() - status.height())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_overlays()


class MainWorkspaceBuilder:
    """Ensambla la composición física del workspace principal.

    ``owner`` es MainWindow: recibe las referencias de widgets que necesita
    para coordinar la lógica (``design_tree``, ``properties``, ``results``,
    ``timeline``, ``host``, ``viewport``).

    Este builder NO conecta señales ni toca estado: solo construye y devuelve
    el widget central con sus paneles colocados.
    """

    def __init__(self, owner) -> None:
        self.owner = owner

    @staticmethod
    def _panel_frame(panel: QWidget, object_name: str, margins) -> QFrame:
        frame = QFrame()
        frame.setObjectName(object_name)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(*margins)
        fl.addWidget(panel)
        return frame

    def build(self) -> QWidget:
        owner = self.owner

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(owner._build_topbar())
        layout.addWidget(owner._build_workspace_tabs())
        layout.addWidget(owner._build_ribbon())

        main_row = QHBoxLayout()
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(0)

        # ---- Left sidebar (Navegador de Diseño + Panel de Propiedades) ----
        left = QWidget()
        left.setFixedWidth(265)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 0, 12)
        ll.setSpacing(10)

        owner.design_tree = DesignTreePanel()
        ll.addWidget(self._panel_frame(owner.design_tree, "treePanel", (12, 10, 12, 10)))

        owner.properties = PropertiesPanel()
        ll.addWidget(self._panel_frame(owner.properties, "propsPanel", (4, 8, 4, 8)), 1)
        main_row.addWidget(left)

        # ---- Center: viewport + timeline ----
        center = QWidget()
        cv = QVBoxLayout(center)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        owner.host = ViewportHost()
        owner.viewport = owner.host.viewport
        cv.addWidget(owner.host, 1)

        owner.timeline = TimelinePanel()
        cv.addWidget(owner.timeline)
        main_row.addWidget(center, 1)

        # ---- Right: Resultados ----
        right = QWidget()
        right.setFixedWidth(250)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 12, 12, 12)
        owner.results = ResultsPanel()
        rl.addWidget(self._panel_frame(owner.results, "resultsPanel", (12, 10, 12, 10)))
        main_row.addWidget(right)

        layout.addLayout(main_row, 1)
        return central


__all__ = ["MainWorkspaceBuilder", "ViewportHost"]