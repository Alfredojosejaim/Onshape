"""MainWindow - native desktop window for the CAD/CAE application:

  menu bar (Archivo · Editar · Diseño · Herramientas · Ayuda)
  top bar (app title centered · ⛁ Standalone chip · Importar STEP · avatar)
  workspace tabs (Modelo / Optimización / Simulación / Fabricación)
  ribbon toolbar (Modelo · Optimización · Postproceso tool groups)
  [ Navegador de Diseño + Panel de Propiedades | viewport 3D + timeline | Resultados ]

The viewport keeps the GPU-accelerated VTK widget with HTML-style overlays
(optimization badge, view controls, legend status bar, import placeholder).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import numpy as np
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QPushButton, QFileDialog, QMessageBox, QComboBox, QInputDialog,
)

from desktop.viewport.viewport_3d import Viewport3D, StandardView
from desktop.pipeline.controller import PipelineController, launch_qt
from desktop.ui.panels.design_tree import DesignTreePanel
from desktop.ui.panels.properties import PropertiesPanel
from desktop.ui.panels.results import ResultsPanel
from desktop.ui.panels.timeline import TimelinePanel
from desktop.ui.style import PALETTE
from core.user_preferences import UserPreferences
from core.navigation import NavigationManager
from core.cad_entity import EntityType

ACCENT = PALETTE["accent"]
TEXT_DIM = PALETTE["text_dim"]
TEXT_FAINT = PALETTE["text_faint"]


def _repolish(widget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def _glyph_label(text: str, size: int = 15) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"background: transparent; font-size: {size}px; color: {TEXT_DIM};")
    return lbl


def _mini_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("background: transparent; font-size: 9px; color: #9a9ba0;")
    return lbl


class RibbonTool(QPushButton):
    """A 62x50 tool button with a glyph on top and a tiny label below (HTML .tool-btn)."""

    def __init__(self, glyph: str, label: str, tooltip: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setProperty("ribbon", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(64, 52)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 4, 3, 3)
        lay.setSpacing(2)
        lay.addStretch(1)
        lay.addWidget(_glyph_label(glyph))
        lay.addWidget(_mini_label(label))
        lay.addStretch(1)
        if tooltip:
            self.setToolTip(tooltip)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        _repolish(self)


class _ViewportHost(QFrame):
    """Frames a Viewport3D with an inset margin and positions overlay widgets
    (badge / view controls / status bar / placeholder) on top of the 3D area."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("viewportContainer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 0)
        self.viewport = Viewport3D()
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Topología Optimizada — CAD/CAE Desktop")
        self.resize(1440, 900)
        self.setMinimumSize(980, 640)

        self.controller = PipelineController()
        # Local user preferences (persisted locally; no network involvement).
        self.preferences = UserPreferences()

        self._build_menus()
        self._build_central()

        # Restore the user's saved navigation profile onto the viewport
        # (profiles come from the existing NavigationManager; only the
        # preference is persisted locally here).
        saved_profile = self.preferences.navigation_profile
        if saved_profile in {p["name"] for p in NavigationManager.available_profiles()}:
            self.viewport.set_navigation_profile(saved_profile)

        # Reflect license state and stay in sync when it changes.  Only the
        # state string is consumed here -- no HTTP/network logic in the UI.
        self._sync_license_status()
        self.controller.license.add_listener(
            lambda st: self.chip_status.setText(f"☁ {st.value.replace('_', ' ')}")
        )

        self.statusBar().showMessage("Listo. Importe un archivo STEP local (paso 1 de 5).")

    # ------------------------------------------------------------------ #
    # Menus (Archivo · Editar · Diseño · Herramientas · Ayuda)
    # ------------------------------------------------------------------ #
    def _build_menus(self) -> None:
        menubar = self.menuBar()
        self._actions_view: dict[str, QAction] = {}

        # Archivo
        file_menu = menubar.addMenu("&Archivo")
        act_open = QAction("Importar archivo STEP...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._on_import)
        file_menu.addAction(act_open)
        act_exp = QAction("Exportar resultado...", self)
        act_exp.triggered.connect(self._on_export)
        file_menu.addAction(act_exp)
        file_menu.addSeparator()
        act_quit = QAction("Salir", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Editar
        edit_menu = menubar.addMenu("&Editar")
        act_clr = QAction("Limpiar selección", self)
        act_clr.triggered.connect(self._on_clear_selection)
        edit_menu.addAction(act_clr)
        act_reset = QAction("Reiniciar flujo", self)
        act_reset.triggered.connect(self._on_reset_flow)
        edit_menu.addAction(act_reset)

        # Operaciones (CAD operations; extensible to future ops)
        ops_menu = menubar.addMenu("&Operaciones")
        boolean_sub = ops_menu.addMenu("Boolean")
        act_bool_union = QAction("Unión", self)
        act_bool_union.triggered.connect(lambda: self._on_boolean_op("union"))
        boolean_sub.addAction(act_bool_union)
        act_bool_cut = QAction("Corte", self)
        act_bool_cut.triggered.connect(lambda: self._on_boolean_op("difference"))
        boolean_sub.addAction(act_bool_cut)
        act_bool_intersect = QAction("Intersección", self)
        act_bool_intersect.triggered.connect(lambda: self._on_boolean_op("intersection"))
        boolean_sub.addAction(act_bool_intersect)

        # Condiciones (reusable CAD/CAE conditions)
        cond_menu = menubar.addMenu("&Condiciones")
        act_cond_load = QAction("Carga", self)
        act_cond_load.triggered.connect(lambda: self._on_condition_op("load"))
        cond_menu.addAction(act_cond_load)
        act_cond_elast = QAction("Elasticidad", self)
        act_cond_elast.triggered.connect(lambda: self._on_condition_op("elasticity"))
        cond_menu.addAction(act_cond_elast)
        act_cond_obstr = QAction("Obstrucción", self)
        act_cond_obstr.triggered.connect(lambda: self._on_condition_op("obstruction"))
        cond_menu.addAction(act_cond_obstr)
        act_cond_prot = QAction("Región protegida", self)
        act_cond_prot.triggered.connect(lambda: self._on_condition_op("protected"))
        cond_menu.addAction(act_cond_prot)

        # Estudio (architecture layer: create & run a topology study)
        study_menu = menubar.addMenu("&Estudio")
        act_study_new = QAction("Nuevo estudio de optimización...", self)
        act_study_new.triggered.connect(self._on_create_study)
        study_menu.addAction(act_study_new)
        act_study_run = QAction("Ejecutar estudio (topología)", self)
        act_study_run.triggered.connect(self._on_run_study)
        study_menu.addAction(act_study_run)

        # Diseño (vistas + representación)
        view_menu = menubar.addMenu("&Diseño")
        presets = [
            ("Isométrica", StandardView.ISO),
            ("Frontal", StandardView.FRONT),
            ("Superior", StandardView.TOP),
            ("Lateral derecha", StandardView.RIGHT),
        ]
        for label, key in presets:
            act = QAction(label, self)
            act.setCheckable(True)
            act.triggered.connect(lambda _=False, k=key: self._on_view(k))
            view_menu.addAction(act)
            self._actions_view[key] = act
        view_menu.addSeparator()
        act_fit = QAction("Ajustar a pantalla", self)
        act_fit.setShortcut("F")
        act_fit.triggered.connect(lambda: self.viewport.fit_to_view())
        view_menu.addAction(act_fit)
        act_center = QAction("Centrar modelo", self)
        act_center.triggered.connect(lambda: self.viewport.center_model())
        view_menu.addAction(act_center)

        # Herramientas
        tools_menu = menubar.addMenu("&Herramientas")
        act_gm = QAction("Generar malla", self)
        act_gm.triggered.connect(lambda: self._on_generate_mesh(self.properties._element_size.value()))
        tools_menu.addAction(act_gm)
        act_fea = QAction("Análisis FEM", self)
        act_fea.triggered.connect(self._on_run_fea)
        tools_menu.addAction(act_fea)
        act_opt = QAction("Optimizar SIMP", self)
        act_opt.triggered.connect(self._on_run_optimization_default)
        tools_menu.addAction(act_opt)

        # Ayuda
        help_menu = menubar.addMenu("Ay&uda")
        act_about = QAction("Acerca de", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------ #
    # Top bar, workspace tabs and ribbon
    # ------------------------------------------------------------------ #
    def _build_topbar(self) -> QWidget:
        tb = QWidget()
        tb.setFixedHeight(52)
        grid = QGridLayout(tb)
        grid.setContentsMargins(16, 0, 16, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        left = _glyph_label("◱", 18)
        left.setStyleSheet(f"background: transparent; font-size: 18px; color: {TEXT_FAINT};")
        grid.addWidget(left, 0, 0, Qt.AlignmentFlag.AlignLeft)

        title = QLabel("OPTIMIZACIÓN TOPOLÓGICA")
        title.setProperty("title", True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(title, 0, 1, Qt.AlignmentFlag.AlignCenter)

        right = QWidget()
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)
        chip = QLabel("☁ Standalone")
        chip.setProperty("chip", True)
        self.chip_status = chip
        self._btn_import_top = QPushButton("📁 Importar STEP")
        self._btn_import_top.setProperty("htmlprimary", True)
        self._btn_import_top.setStyleSheet("padding: 5px 12px; font-size: 12px;")
        self._btn_import_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_import_top.clicked.connect(self._on_import)
        avatar = QLabel("JD")
        avatar.setProperty("avatar", True)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(chip)
        rl.addWidget(self._btn_import_top)
        rl.addWidget(avatar)
        grid.addWidget(right, 0, 2, Qt.AlignmentFlag.AlignRight)

        self.topbar = tb
        return tb

    def _build_workspace_tabs(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(34)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(2)

        self._tabs: list[QPushButton] = []
        for idx, label in enumerate(["Modelo", "Optimización", "Simulación", "Fabricación"]):
            b = QPushButton(label)
            b.setProperty("tab", True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setCheckable(False)
            b.clicked.connect(lambda _=False, i=idx: self._activate_tab(i))
            if idx == 1:
                b.setProperty("active", True)
                _repolish(b)
            self._tabs.append(b)
            lay.addWidget(b)

        doc = QLabel("📁 Sin documento cargado")
        doc.setStyleSheet(f"font-size: 12px; color: {TEXT_FAINT}; margin-left: 14px; padding-left: 12px;")
        doc.setProperty("faint", True)
        self.doc_label = doc
        lay.addWidget(doc, 1)
        return w

    def _activate_tab(self, index: int) -> None:
        for i, b in enumerate(self._tabs):
            b.setProperty("active", i == index)
            _repolish(b)

    def _build_ribbon(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 8, 16, 4)
        lay.setSpacing(0)

        def group(rows: list[tuple[RibbonTool]], label: str) -> QWidget:
            g = QWidget()
            gl = QVBoxLayout(g)
            gl.setContentsMargins(0, 0, 0, 0)
            gl.setSpacing(4)
            row = QHBoxLayout()
            row.setSpacing(4)
            for tool in rows:
                row.addWidget(tool)
            row.addStretch(1)
            cap = QLabel(label.upper())
            cap.setStyleSheet(f"font-size: 9.5px; letter-spacing: 0.6px; color: {TEXT_FAINT};")
            gl.addLayout(row)
            gl.addWidget(cap)
            return g

        def divider() -> QFrame:
            d = QFrame()
            d.setFrameShape(QFrame.Shape.VLine)
            d.setStyleSheet("color: #313236; margin: 2px 14px;")
            d.setFixedHeight(48)
            return d

        # Modelo
        self.rb_import = RibbonTool("📁", "Importar STEP", "Importar archivo STEP local")
        self.rb_import.clicked.connect(self._on_import)
        self.rb_mesh = RibbonTool("📐", "Malla FEM", "Generar malla volumétrica FEM (Tet4)")
        self.rb_mesh.clicked.connect(lambda: self._on_generate_mesh(self.properties._element_size.value()))
        self.rb_mesh_adaptive = RibbonTool("▦", "Malla Adaptativa", "Refinar malla localmente según densidad")
        self.rb_mesh_adaptive.clicked.connect(self._on_generate_adaptive_mesh)
        self.rb_fea = RibbonTool("📊", "Análisis FEM", "Structural Mechanics — análisis estático")
        self.rb_fea.clicked.connect(self._on_run_fea)
        lay.addWidget(group([self.rb_import, self.rb_mesh, self.rb_mesh_adaptive, self.rb_fea], "Modelo"))

        lay.addWidget(divider())

        # Edición
        self.rb_union = RibbonTool("⊕", "Unión", "Unión booleana de sólidos")
        self.rb_union.clicked.connect(lambda: self._on_boolean_op("union"))
        self.rb_difference = RibbonTool("⊖", "Resta", "Resta booleana de sólidos")
        self.rb_difference.clicked.connect(lambda: self._on_boolean_op("difference"))
        self.rb_intersect = RibbonTool("⊗", "Intersección", "Intersección booleana de sólidos")
        self.rb_intersect.clicked.connect(lambda: self._on_boolean_op("intersection"))
        self.rb_transform = RibbonTool("↗", "Transformar", "Trasladar / rotar cuerpo")
        self.rb_transform.clicked.connect(lambda: self.statusBar().showMessage(
            "Transformar: seleccione cuerpo y arrastre para trasladar/rotar."))
        self.rb_mirror = RibbonTool("◇", "Simetría", "Simetría respecto a plano")
        self.rb_mirror.clicked.connect(lambda: self.statusBar().showMessage(
            "Simetría: seleccione cuerpo y un plano para crear la simetría."))
        lay.addWidget(group([self.rb_union, self.rb_difference, self.rb_intersect,
                             self.rb_transform, self.rb_mirror], "Edición"))

        lay.addWidget(divider())

        # Optimización
        self.rb_sens = RibbonTool("📈", "Sensibilidad", "Análisis de sensibilidad (adjoint)")
        self.rb_sens.clicked.connect(lambda: self.statusBar().showMessage(
            "Sensibilidad adjunto: computada internamente por el motor SIMP en cada iteración."))
        self.rb_filtros = RibbonTool("⚙", "Filtros", "Radio de filtro de densidad")
        self.rb_filtros.clicked.connect(self._on_focus_filter)
        self.rb_opt = RibbonTool("▶", "Optimizar SIMP", "Optimization Application — algoritmo SIMP")
        self.rb_opt.clicked.connect(self._on_run_optimization_default)
        self.rb_design_space = RibbonTool("◆", "Espacio de Diseño", "Definir espacio de diseño para optimización")
        self.rb_design_space.clicked.connect(lambda: self.statusBar().showMessage(
            "Espacio de Diseño: seleccione cuerpos para definir el dominio de optimización."))
        self.rb_generative = RibbonTool("✧", "Generativo", "Diseño generativo con escenarios")
        self.rb_generative.clicked.connect(lambda: self.statusBar().showMessage(
            "Diseño Generativo: configure escenarios y restricciones."))
        lay.addWidget(group([self.rb_sens, self.rb_filtros, self.rb_opt,
                             self.rb_design_space, self.rb_generative], "Optimización"))

        lay.addWidget(divider())

        # Postproceso
        self.rb_viz = RibbonTool("👁", "Visualizar", "Visualizar campo de densidad por elemento")
        self.rb_viz.clicked.connect(self._on_visualize_result)
        self.rb_export = RibbonTool("📤", "Exportar", "Exportar resultado de la optimización")
        self.rb_export.clicked.connect(self._on_export)
        lay.addWidget(group([self.rb_viz, self.rb_export], "Postproceso"))

        lay.addWidget(divider())

        # Herramientas
        self.rb_validate = RibbonTool("✓", "Validar", "Validar geometría y restricciones")
        self.rb_validate.clicked.connect(lambda: self.statusBar().showMessage(
            "Validar: verificando geometría y restricciones..."))
        self.rb_export_step = RibbonTool("💾", "Exportar STEP", "Exportar resultado como archivo STEP")
        self.rb_export_step.clicked.connect(self._on_export_step)
        lay.addWidget(group([self.rb_validate, self.rb_export_step], "Herramientas"))

        lay.addStretch(1)

        # right side: view preset + axes/grid toggles (native conveniences)
        right = QWidget()
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(QLabel("Vista:"))
        self._view_combo = QComboBox()
        for label, key in [
            ("Isométrica", StandardView.ISO), ("Frontal", StandardView.FRONT),
            ("Superior", StandardView.TOP), ("Lateral derecha", StandardView.RIGHT),
        ]:
            self._view_combo.addItem(label, key)
        self._view_combo.currentIndexChanged.connect(
            lambda i: self.viewport.set_view(self._view_combo.itemData(i)) if i >= 0 else None
        )
        rl.addWidget(self._view_combo)
        self._cb_axes = QPushButton("Ejes")
        self._cb_axes.setCheckable(True)
        self._cb_axes.setChecked(True)
        self._cb_axes.setStyleSheet("padding: 5px 10px; font-size: 11.5px;")
        self._cb_axes.toggled.connect(lambda on: self.viewport.toggle_axes(on))
        rl.addWidget(self._cb_axes)
        self._cb_grid = QPushButton("Rejilla")
        self._cb_grid.setCheckable(True)
        self._cb_grid.setChecked(True)
        self._cb_grid.setStyleSheet("padding: 5px 10px; font-size: 11.5px;")
        self._cb_grid.toggled.connect(lambda on: self.viewport.toggle_grid(on))
        rl.addWidget(self._cb_grid)
        lay.addWidget(right)

        self.ribbon = w
        return w

    # ------------------------------------------------------------------ #
    # Central layout
    # ------------------------------------------------------------------ #
    def _build_central(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_topbar())
        layout.addWidget(self._build_workspace_tabs())
        layout.addWidget(self._build_ribbon())

        main_row = QHBoxLayout()
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(0)

        # ---- Left sidebar (Navegador de Diseño + Panel de Propiedades) ----
        left = QWidget()
        left.setFixedWidth(265)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 0, 12)
        ll.setSpacing(10)

        tree_frame = QFrame()
        tree_frame.setObjectName("treePanel")
        tf = QVBoxLayout(tree_frame)
        tf.setContentsMargins(12, 10, 12, 10)
        self.design_tree = DesignTreePanel()
        tf.addWidget(self.design_tree)
        ll.addWidget(tree_frame)

        props_frame = QFrame()
        props_frame.setObjectName("propsPanel")
        pf = QVBoxLayout(props_frame)
        pf.setContentsMargins(4, 8, 4, 8)
        self.properties = PropertiesPanel()
        pf.addWidget(self.properties)
        ll.addWidget(props_frame, 1)
        main_row.addWidget(left)

        # ---- Center: viewport + timeline ----
        center = QWidget()
        cv = QVBoxLayout(center)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        self.host = _ViewportHost()
        self.viewport = self.host.viewport
        self.viewport.selectionChanged.connect(self._on_selection)
        # Body-level selection: promote a picked face to its parent solid using
        # the CAD service (Fase 2).
        self.viewport.selection_manager.set_solid_resolver(
            lambda model_id, face_index: self.controller.cad.resolve_solid_for_face(model_id, face_index)
            if model_id and self.controller.cad.get_model_shape(model_id) else None
        )
        cv.addWidget(self.host, 1)

        self.timeline = TimelinePanel()
        self.timeline.playRequested.connect(self._on_play_next)
        self.timeline.resetRequested.connect(self._on_reset_flow)
        cv.addWidget(self.timeline)
        main_row.addWidget(center, 1)

        # ---- Right: Resultados ----
        right = QWidget()
        right.setFixedWidth(250)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 12, 12, 12)
        res_frame = QFrame()
        res_frame.setObjectName("propsPanel")
        rf = QVBoxLayout(res_frame)
        rf.setContentsMargins(12, 10, 12, 10)
        self.results = ResultsPanel()
        rf.addWidget(self.results)
        rl.addWidget(res_frame)
        main_row.addWidget(right)

        layout.addLayout(main_row, 1)

        # ---- Viewport overlays (HTML chrome) ----
        self._build_viewport_overlays()

        self.setCentralWidget(central)

        # wire panel signals
        self.properties.generateMesh.connect(self._on_generate_mesh)
        self.properties.runFEA.connect(self._on_run_fea)
        self.properties.runOptimization.connect(self._on_run_optimization)
        self.design_tree.clear_button().clicked.connect(self._on_clear_selection)
        self.controller_reset_after_model()

    def _build_viewport_overlays(self) -> None:
        # Badge (top-left)
        badge = QWidget()
        bl = QHBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(10)
        t1 = QLabel("Optimización")
        t1.setStyleSheet("font-size: 13px; font-weight: 600;")
        t2 = QLabel("SIMP · Standalone")
        t2.setProperty("badge", True)
        bl.addWidget(t1)
        bl.addWidget(t2)
        self.host.place("badge", badge)

        # View controls (top-right)
        controls = QWidget()
        cl = QVBoxLayout(controls)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)
        self.ctrl_center = self._viewer_button("📷 Centrar Vista", command=lambda: self.viewport.fit_to_view())
        self.ctrl_wire = self._viewer_button("🔲 Wireframe", checked=True)
        self.ctrl_wire.toggled.connect(
            lambda on: self.viewport.set_display_mode("wireframe" if on else "surfaced"))
        self.ctrl_axes = self._viewer_button("📐 Ejes", checked=True)
        self.ctrl_axes.toggled.connect(self.viewport.toggle_axes)
        self.ctrl_forces = self._viewer_button("⚡ Fuerzas", checked=True)
        self.ctrl_forces.toggled.connect(lambda on: self._sync_sidebar_vis("forces", on))
        self.ctrl_constraints = self._viewer_button("🔒 Fijaciones", checked=True)
        self.ctrl_constraints.toggled.connect(lambda on: self._sync_sidebar_vis("constraints", on))
        for b in (self.ctrl_center, self.ctrl_wire, self.ctrl_axes,
                  self.ctrl_forces, self.ctrl_constraints):
            cl.addWidget(b)
        self.host.place("controls", controls)

        # Status bar overlay (bottom)
        status = QWidget()
        sl = QHBoxLayout(status)
        sl.setContentsMargins(14, 0, 14, 0)
        sl.setSpacing(14)
        sl.addWidget(self._legend_dot("Sólido CAD Real", PALETTE["solid_cad"]))
        sl.addWidget(self._legend_dot("Fuerzas (Vectores)", PALETTE["force"]))
        sl.addWidget(self._legend_dot("Fijaciones", PALETTE["constraint"]))
        sl.addStretch(1)
        self._viewer_info = QLabel("Visor 3D inicializando...")
        self._viewer_info.setProperty("viewinfo", True)
        sl.addWidget(self._viewer_info, 1)
        status.setStyleSheet(
            "background: rgba(14,14,16,0.9); border: 1px solid #313236;"
            "border-top-left-radius: 6px; border-top-right-radius: 6px;")
        self.host.place("status", status)

        # Placeholder (center) while no model is loaded
        ph = QWidget()
        pl = QVBoxLayout(ph)
        pl.setContentsMargins(18, 18, 18, 18)
        pl.setSpacing(10)
        box = QLabel("🔲")
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.setFixedSize(90, 90)
        box.setStyleSheet(
            "border: 2px dashed #5b5c60; border-radius: 10px; font-size: 26px;")
        hint = QLabel("Importe un archivo STEP para cargar el modelo 3D")
        hint.setStyleSheet("font-size: 11.5px; color: #6f7075;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pl.addStretch(1)
        pl.addWidget(box, 0, Qt.AlignmentFlag.AlignCenter)
        pl.addWidget(hint, 0, Qt.AlignmentFlag.AlignCenter)
        pl.addStretch(1)
        self.placeholder = ph
        self.host.place("placeholder", ph)

    def _viewer_button(self, text: str, checked: bool = False,
                       command=None) -> QPushButton:
        b = QPushButton(text)
        b.setProperty("viewercontrol", True)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if command is not None:
            b.setCheckable(False)
            b.clicked.connect(command)
            b.setProperty("active", False)
            _repolish(b)
        else:
            b.setCheckable(True)
            b.setChecked(checked)
            b.toggled.connect(lambda on, btn=b: self._set_viewer_active(btn, on))
            self._set_viewer_active(b, checked)
        return b

    @staticmethod
    def _set_viewer_active(btn: QPushButton, active: bool) -> None:
        btn.setProperty("active", active)
        _repolish(btn)

    def _legend_dot(self, text: str, color: str) -> QWidget:
        w = QWidget()
        hl = QHBoxLayout(w)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(5)
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
        lab = QLabel(text)
        lab.setProperty("legend", True)
        hl.addWidget(dot)
        hl.addWidget(lab)
        return w

    def _sync_sidebar_vis(self, which: str, checked: bool) -> None:
        cb = {"forces": self.properties._cb_forces,
              "constraints": self.properties._cb_constraints}[which]
        blocker = QSignalBlocker(cb)
        cb.setChecked(checked)
        del blocker
        self.statusBar().showMessage(
            f"Visibilidad {'activada' if checked else 'desactivada'}: {which}")

    # ------------------------------------------------------------------ #
    # Import
    # ------------------------------------------------------------------ #
    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar modelo STEP", "", "STEP (*.step *.stp);;Todos (*)"
        )
        if not path:
            return
        self._set_busy(True, "Importando geometría STEP...")
        self.statusBar().showMessage(f"Importando {os.path.basename(path)}...")

        self.controller.run_in_background(
            lambda: self.controller.import_model(path),
            on_done=self._on_import_done,
            on_error=lambda e: self._on_error("Importación", e),
        )

    def _on_import_done(self, payload) -> None:
        self.controller_reset_after_model()
        tess = payload["tessellation"]
        self._show_tessellation(tess)
        self.placeholder.hide()
        name = payload["name"]
        self.doc_label.setText(f"📁 {name}.step")
        vol = tess.get("total_volume") or tess.get("volume")
        if vol is not None:
            self.properties.set_cad_meta(f"Volumen: {vol:.2f} mm³")
        self.timeline.set_pipeline_step(1)
        self._set_busy(False, f"Modelo importado: {name}")
        self.statusBar().showMessage(
            f"Modelo {name} cargado. Paso 2: definir cargas/restricciones.")
        # Architecture layer: refresh feature history in tree
        self._sync_architecture_tree()

    def controller_reset_after_model(self) -> None:
        has_model = self.controller.model_id is not None
        self.properties.set_enabled(has_model, False)
        self.properties.set_materials(self.controller.material_names(),
                                      self.controller.material_name())
        self.rb_mesh.setEnabled(has_model)
        self.rb_fea.setEnabled(False)
        self.rb_opt.setEnabled(False)
        self.rb_viz.setEnabled(False)
        self.rb_export.setEnabled(False)
        self.design_tree.set_context(
            self.controller.model_name if has_model else None,
            has_mesh=False,
            has_result=False,
        )
        self.results.reset_all()
        self.timeline.set_pipeline_step(1 if has_model else 0)
        self.design_tree.clear_button().setEnabled(False)
        # Architecture layer: sync features/studies into tree
        self._sync_architecture_tree()

    def _sync_architecture_tree(self) -> None:
        """Push the feature history, conditions and study list into the design tree panel."""
        features = self.controller.feature_history.features
        self.design_tree.set_features(features)
        conditions = self.controller.conditions.all
        self.design_tree.set_conditions(conditions)
        studies = list(self.controller._studies.values())
        self.design_tree.set_studies(studies)

    def _show_tessellation(self, tess: Dict[str, Any]) -> None:
        vertices = np.asarray(tess.get("vertices", []), dtype=float).reshape(-1, 3)
        indices = np.asarray(tess.get("indices", []), dtype=int)
        bbox_dict = tess.get("bbox")
        if bbox_dict is None:
            return
        bbox = _BBox(
            bbox_dict.get("xmin", vertices[:, 0].min()),
            bbox_dict.get("xmax", vertices[:, 0].max()),
            bbox_dict.get("ymin", vertices[:, 1].min()),
            bbox_dict.get("ymax", vertices[:, 1].max()),
            bbox_dict.get("zmin", vertices[:, 2].min()),
            bbox_dict.get("zmax", vertices[:, 2].max()),
        )
        n_tri = len(indices) // 3
        triangles = indices.reshape(n_tri, 3) if n_tri else np.empty((0, 3), dtype=int)
        # Per-triangle B-Rep face index derived from the face_triangles ranges.
        face_index_map = None
        face_ranges = tess.get("face_triangles") or []
        if face_ranges and n_tri:
            face_index_map = np.full(n_tri, -1, dtype=np.int64)
            for rng in face_ranges:
                start, count = int(rng.get("start", 0)), int(rng.get("count", 0))
                if 0 <= start < n_tri:
                    face_index_map[start:start + count] = int(rng.get("face_index", -1))
        self._attach_bounds(bbox)
        self.viewport.load_model(vertices, triangles, bbox,
                                 face_index_map=face_index_map,
                                 faces_meta=tess.get("faces"))
        self._viewer_info.setText(
            f"Geometría: {tess.get('num_vertices', vertices.shape[0])} vértices · "
            f"{tess.get('num_triangles', n_tri)} triángulos")

    # ------------------------------------------------------------------ #
    # Mesh
    # ------------------------------------------------------------------ #
    def _on_generate_mesh(self, element_size: float) -> None:
        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importa primero un STEP.")
            return
        self._set_busy(True, "Generando malla FEM (Gmsh / provisional)...")
        self.statusBar().showMessage("Generando malla volumétrica...")
        self.controller.run_in_background(
            lambda: self.controller.generate_mesh(element_size),
            on_done=self._on_mesh_done,
            on_error=lambda e: self._on_error("Mallado", e),
        )

    def _on_mesh_done(self, mesh) -> None:
        nodes = self.controller.mesh_nodes
        elements = self.controller.mesh_elements
        self.viewport.show_mesh(nodes, elements)
        self.design_tree.set_context(
            self.controller.model_name,
            has_mesh=True,
            has_result=self.controller.result is not None,
        )
        self.properties.set_enabled(True, True)
        self.rb_fea.setEnabled(True)
        self.rb_opt.setEnabled(True)
        self.results.set_mesh(
            mesh.get("num_nodes", nodes.shape[0]),
            mesh.get("num_elements", elements.shape[0]),
            mesh.get("element_type", "tet4"),
            mesh.get("is_provisional", True),
        )
        self.timeline.set_pipeline_step(3)
        self.statusBar().showMessage(
            f"Malla: {nodes.shape[0]} nodos, {elements.shape[0]} elementos.")
        self._set_busy(False, "Malla generada.")

    # ------------------------------------------------------------------ #
    # Licensing status (read-only; policy lives in LicenseManager)
    # ------------------------------------------------------------------ #
    def _sync_license_status(self) -> None:
        """Reflect the license state in the top-bar chip.

        The UI merely *displays* the state produced by ``controller.license``;
        it does not perform any network check itself.  The offline/grace
        policy stays fully encapsulated inside LicenseManager.
        """
        st = self.controller.license.state
        self.chip_status.setText(f"☁ {st.value.replace('_', ' ')}")

    def _on_generate_adaptive_mesh(self) -> None:
        """Generate an adaptively refined mesh (density-driven if possible)."""
        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importa primero un STEP.")
            return
        base = self.properties._element_size.value() if hasattr(self.properties, "_element_size") else 5.0
        self._set_busy(True, "Generando malla adaptativa según densidad...")
        self.statusBar().showMessage("Generando malla adaptativa (refinamiento por densidad)...")
        self.controller.run_in_background(
            lambda: self.controller.generate_adaptive_mesh(base_size=base, min_size=max(0.2, base * 0.1)),
            on_done=self._on_mesh_done,
            on_error=lambda e: self._on_error("Mallado adaptativo", e),
        )

    # ------------------------------------------------------------------ #
    # FEA
    # ------------------------------------------------------------------ #
    def _on_run_fea(self) -> None:
        if not self.controller.mesh:
            QMessageBox.warning(self, "Sin malla", "Genera la malla primero.")
            return
        self._configure_boundaries()
        self._set_busy(True, "Resolviendo análisis estático (FEA)...")
        self.controller.run_in_background(
            lambda: self.controller.run_fea(),
            on_done=self._on_fea_done,
            on_error=lambda e: self._on_error("FEA", e),
        )

    def _on_fea_done(self, result) -> None:
        self.results.set_result(result, self.properties.material_name())
        ok = bool(result.get("success"))
        self._set_busy(False, "FEA completado." if ok else "FEA con errores.")
        self.statusBar().showMessage(
            f"FEA: compliance = {result.get('final_compliance', result.get('compliance', '—')):.4e}")

    # ------------------------------------------------------------------ #
    # Optimization
    # ------------------------------------------------------------------ #
    def _on_run_optimization_default(self) -> None:
        self._on_run_optimization({
            "volume_fraction": 0.35,
            "max_iterations": 30,
            "penalization": 3.0,
            "filter_radius": 1.5,
            "tolerance": 1e-3,
            "material": self.properties.material_name(),
        })

    def _on_run_optimization(self, params: dict) -> None:
        if not self.controller.mesh:
            QMessageBox.warning(self, "Sin malla", "Genera la malla primero.")
            return
        self._configure_boundaries()
        self.results.clear_history()
        self.timeline.set_pipeline_step(4)
        self._set_busy(True, "Ejecutando optimización topológica (SIMP)...")

        def progress_cb(info: dict):
            def upd():
                self.results.append_history(info["iteration"], info["volume_fraction"], info["compliance"])
                pct = int(100 * info["iteration"] / max(1, params["max_iterations"]))
                self.results.set_result(
                    {"success": True, "converged": False, "iterations": info["iteration"],
                     "final_volume_fraction": info["volume_fraction"],
                     "final_compliance": info["compliance"], "max_density_change": info["max_change"]},
                    params["material"],
                )
                self.properties.set_progress(pct, f"Iteración {info['iteration']}")
                self.timeline.set_iteration(info["iteration"], info["volume_fraction"])
            launch_qt(upd)

        self.controller.run_in_background(
            lambda: self.controller.run_optimization(
                volume_fraction=params["volume_fraction"],
                max_iterations=params["max_iterations"],
                penalization=params["penalization"],
                filter_radius=params["filter_radius"],
                tolerance=params["tolerance"],
                progress_cb=progress_cb,
            ),
            on_done=self._on_optimization_done,
            on_error=lambda e: self._on_error("Optimización", e),
        )

    def _on_optimization_done(self, result) -> None:
        ok = bool(result.get("success"))
        self.results.set_result(result, self.properties.material_name())
        self._set_busy(False, "Optimización completada." if ok else "Optimización con errores.")
        if ok:
            densities = self.controller.result_densities
            self.viewport.show_density(
                self.controller.mesh_nodes, self.controller.mesh_elements, densities
            )
            self.design_tree.set_context(
                self.controller.model_name,
                has_mesh=True,
                has_result=True,
            )
            self.rb_viz.setEnabled(True)
            self.rb_export.setEnabled(True)
            self.timeline.set_pipeline_step(5)
            self.statusBar().showMessage(
                f"Optimización: V={result.get('final_volume_fraction', 0):.2%}, "
                f"c={result.get('final_compliance', 0):.4e}, iter={result.get('iterations')}")

    # ------------------------------------------------------------------ #
    # Studies (architecture layer)
    # ------------------------------------------------------------------ #
    def _on_create_study(self) -> None:
        """Open the StudyPanel to build a fully configured topology study."""
        from desktop.ui.panels.study_panel import StudyPanel

        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importe un modelo STEP primero.")
            return
        parts = self._current_solid_selections()
        panel = StudyPanel(
            parent=self,
            condition_manager=self.controller.conditions,
            default_name="Estudio de optimización",
            parts=parts,
            model_id=self.controller.model_id,
            get_solid_selections=self._current_solid_selections,
        )
        result = panel.exec()
        if result != StudyPanel.Accepted or panel.study is None:
            self.statusBar().showMessage("Estudio cancelado.")
            return
        study = panel.study
        sid = self.controller.register_study(study)
        self._sync_architecture_tree()
        self.statusBar().showMessage(
            f"Estudio creado: {study.name} ({sid[:8]}...) con {len(study.parts)} pieza(s), "
            f"{len(study.conditions)} condición(es).")

    def _on_run_study(self) -> None:
        """Execute the selected / last topology study in the background."""
        from core.cae_studies import StudyStatus

        studies = list(self.controller._studies.values())
        if not studies:
            QMessageBox.information(
                self, "Sin estudio",
                "Cree primero un estudio desde Estudio → Nuevo estudio de optimización.")
            return
        study = studies[-1]
        if not study.validate():
            parts_info = f", {len(study.parts)} pieza(s)" if study.parts else ""
            conds_info = f", {len(study.conditions)} condición(es)" if study.conditions else ""
            QMessageBox.warning(self, "Estudio incompleto",
                                f"El estudio no está configurado correctamente.{parts_info}{conds_info}.")
            return
        self._configure_boundaries()
        self.results.clear_history()
        self._set_busy(True, f"Ejecutando estudio '{study.name}' (SIMP)...")

        def worker():
            sr = self.controller.execute_study(study)
            return sr

        def done(sr) -> None:
            self._set_busy(False)
            self._sync_architecture_tree()
            if not sr.success:
                self.statusBar().showMessage(f"Estudio con errores: {sr.error_message}")
                QMessageBox.warning(self, "Estudio", sr.error_message or "Error de ejecución.")
                return
            data = sr.data or {}
            unsupported = data.get("_unsupported_conditions") or []
            self.results.set_result(data, self.properties.material_name())
            densities = self.controller.result_densities
            if densities is not None and densities.size:
                self.viewport.show_density(
                    self.controller.mesh_nodes, self.controller.mesh_elements, densities
                )
                self.rb_viz.setEnabled(True)
                self.rb_export.setEnabled(True)
            msg = f"Estudio '{study.name}' completado."
            if unsupported:
                msg += f" Condiciones no soportadas: {', '.join(unsupported)}."
                QMessageBox.warning(
                    self, "Condiciones no soportadas",
                    "El estudio se completó, pero algunas condiciones no pudieron "
                    "mapearse a la geometría y se ignoraron:\n\n"
                    + ", ".join(unsupported)
                    + "\n\nRevise que las cargas/soportes/obstrucciones "
                      "referencien caras o cuerpos válidos.",
                )
            self.statusBar().showMessage(msg)

        self.controller.run_in_background(
            worker,
            on_done=done,
            on_error=lambda e: self._on_error("Estudio", e),
        )

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def _on_export(self) -> None:
        if not self.controller.result:
            self.statusBar().showMessage("Sin resultado para exportar. Ejecute primero la optimización.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar resultado", "resultado_optimizacion.json", "JSON (*.json)"
        )
        if not path:
            return
        r = self.controller.result
        payload = {
            "estudio": "Optimización Topológica (Standalone)",
            "material": self.properties.material_name(),
            "volumen_fraccion": self.properties.volume_fraction(),
            "iteraciones": r.get("iterations"),
            "volumen_final": r.get("final_volume_fraction"),
            "compliance_final": r.get("final_compliance"),
            "densidades": (r.get("densities") or [])[:20000],
            "num_elementos": len(r.get("densities") or []),
        }
        try:
            import json
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            self.statusBar().showMessage(f"Resultado exportado: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Exportar", f"No se pudo escribir el archivo:\n{exc}")

    def _on_export_step(self) -> None:
        """Export the current CAD model (or boolean/reconstruction result) as STEP."""
        if not self.controller.model_id:
            self.statusBar().showMessage("No hay modelo para exportar. Importe un STEP primero.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar STEP", "modelo_cad.step", "STEP (*.step *.stp)"
        )
        if not path:
            return
        self._set_busy(True, "Exportando STEP...")
        self.controller.run_in_background(
            lambda: self.controller.cad.export_step(self.controller.model_id, path),
            on_done=lambda ok: self._on_export_step_done(ok, path),
            on_error=lambda e: self._on_error("Exportar STEP", e),
        )

    def _on_export_step_done(self, ok: bool, path: str) -> None:
        self._set_busy(False)
        if ok:
            self.statusBar().showMessage(f"STEP exportado: {path}")
        else:
            QMessageBox.critical(self, "Exportar STEP", "No se pudo exportar el modelo a STEP.")

    def _on_visualize_result(self) -> None:
        if not (self.controller.result and self.controller.result_densities is not None):
            self.statusBar().showMessage("Ejecute la optimización para visualizar el campo de densidad.")
            return
        colormaps = ["jet", "viridis", "coolwarm", "inferno"]
        choice, ok = QInputDialog.getItem(
            self, "Visualizar densidad", "Mapa de color:", colormaps, 0, False,
        )
        if not ok:
            return
        self.viewport.show_density(
            self.controller.mesh_nodes, self.controller.mesh_elements,
            self.controller.result_densities, colormap=choice,
        )
        self.statusBar().showMessage(f"Campo de densidad (SIMP) mostrado con colormap '{choice}'.")

    def _on_focus_filter(self) -> None:
        self.statusBar().showMessage("Configure el radio de filtro de densidad en el panel de propiedades.")

    def _on_boolean_op(self, operation: str) -> None:
        """Handle boolean operation entry points (menu + ribbon).

        Opens the functional BooleanPanel dialog, which reuses the existing
        SelectionManager for capturing the target / tool bodies from the
        viewport.  Only on *Aceptar* is a BooleanCommand built and executed
        through the pipeline; *Cancelar* leaves the model untouched.
        """
        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importe un modelo STEP primero.")
            return
        if len(self.controller.cad.list_solids(self.controller.model_id)) < 1:
            QMessageBox.warning(self, "Boolean", "El modelo no contiene cuerpos seleccionables.")
            return

        from desktop.ui.panels.boolean_panel import BooleanPanel

        panel = BooleanPanel(
            parent=self,
            operation=operation,
            get_solid_selections=self._current_solid_selections,
        )
        result = panel.exec()
        if result != BooleanPanel.Accepted or panel.command is None:
            # Cancellation: no Feature, no model change.  Just restore/keep
            # the viewport selection state.
            self.statusBar().showMessage("Operación booleana cancelada.")
            return

        cmd = panel.command
        self._set_busy(True, f"Ejecutando boolean {cmd.get_parameter('operation', 'union')}...")
        self.statusBar().showMessage("Ejecutando operación booleana...")
        self.controller.run_in_background(
            lambda: self.controller.execute_command(cmd),
            on_done=self._on_boolean_done,
            on_error=lambda e: self._on_error("Operación booleana", e),
        )

    def _current_solid_selections(self):
        """Return the solid CadEntityRefs currently selected in the viewport.

        Reuses the existing SelectionManager: faces are promoted to their
        parent solid (``solid_entity``) when available, otherwise the solid
        reference is derived from the picked entity.
        """
        sel = self.viewport.selection_manager
        refs = []
        source = sel.multi_selection if sel.multi_selection else ([sel.last_payload] if sel.last_payload else [])
        for item in source:
            if item is None:
                continue
            solid = item.get("solid_entity")
            if solid is not None:
                refs.append(solid)
                continue
            ce = item.get("cad_entity")
            if ce is not None and ce.entity_type == EntityType.SOLID:
                refs.append(ce)
        # De-duplicate while preserving order.
        seen = set()
        out = []
        for r in refs:
            key = (r.solid_id, r.model_id)
            if key not in seen:
                seen.add(key)
                out.append(r)
        return out

    def _on_condition_op(self, kind: str) -> None:
        """Handle condition entry points (menu).

        Opens the functional ConditionPanel dialog, which reuses the existing
        SelectionManager for capturing faces/bodies from the viewport.  Only on
        *Aceptar* is a condition Command built and executed through the
        pipeline (registering the reusable condition + recording a Feature).
        """
        from desktop.ui.panels.condition_panel import ConditionPanel

        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importe un modelo STEP primero.")
            return

        panel = ConditionPanel(
            parent=self,
            condition_kind=kind,
            get_face_selections=self._current_face_selections,
            get_solid_selections=self._current_solid_selections,
        )
        result = panel.exec()
        if result != ConditionPanel.Accepted or panel.command is None:
            self.statusBar().showMessage("Condición cancelada.")
            return

        cmd = panel.command
        self._set_busy(True, f"Configurando {cmd.display_name}...")
        self.statusBar().showMessage("Registrando condición reutilizable...")
        self.controller.run_in_background(
            lambda: self.controller.execute_command(cmd),
            on_done=self._on_condition_done,
            on_error=lambda e: self._on_error("Condición", e),
        )

    def _current_face_selections(self):
        """Return the face CadEntityRefs currently selected in the viewport."""
        sel = self.viewport.selection_manager
        refs = []
        source = sel.multi_selection if sel.multi_selection else ([sel.last_payload] if sel.last_payload else [])
        for item in source:
            if item is None:
                continue
            ce = item.get("cad_entity")
            if ce is not None and ce.entity_type == EntityType.FACE:
                refs.append(ce)
        return refs

    def _on_condition_done(self, result) -> None:
        self._set_busy(False)
        if not result.success:
            self.statusBar().showMessage(f"Error: {result.error_message}")
            QMessageBox.warning(self, "Condición",
                                f"No se pudo registrar la condición:\n{result.error_message}")
            return
        self.timeline.set_features(self.controller.feature_history.features)
        self._sync_architecture_tree()
        kind = result.data.get("condition_type", "condición")
        self.statusBar().showMessage(
            f"Condición registrada ({kind}): {result.data.get('condition_id', '')[:8]}...")

    def _on_boolean_done(self, result) -> None:
        if not result.success:
            # CAD error: keep the previous model and surface the reason.
            self.statusBar().showMessage(f"Error: {result.error_message}")
            QMessageBox.warning(self, "Operación booleana",
                                f"No se pudo completar la operación:\n{result.error_message}")
            return

        self.statusBar().showMessage(
            f"Operación booleana completada: {result.feature_id[:8]}...")
        # Re-render the boolean result model in the viewport.
        tess = self.controller.current_tessellation
        if tess and tess.get("vertices"):
            self._show_tessellation(tess)
            self.placeholder.hide()
            self.design_tree.set_context(
                self.controller.model_name if self.controller.model_id else None,
                has_mesh=False, has_result=False,
            )
        self.design_tree.set_bodies(self.controller.cad.list_solids(self.controller.model_id))
        self.timeline.set_features(self.controller.feature_history.features)
        self._sync_architecture_tree()

    # ------------------------------------------------------------------ #
    # Guided flow (timeline playback)
    # ------------------------------------------------------------------ #
    def _on_play_next(self) -> None:
        if not self.controller.model_id:
            self._on_import()
            return
        if not self.controller.mesh:
            self._on_generate_mesh(self.properties._element_size.value())
            return
        if not self.controller.result:
            self._on_run_optimization_default()
            return
        self.statusBar().showMessage("Flujo completado. Modifique parámetros y vuelva a ejecutar.")

    def _on_reset_flow(self) -> None:
        self.timeline.reset()
        self.results.clear_history()
        self.statusBar().showMessage("Flujo reiniciado. Importe o vuelva a ejecutar los pasos.")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _configure_boundaries(self) -> None:
        """Push material + constraint type + load values into the controller."""
        material = self.properties.material_name()
        self.controller.set_material(material)
        ctype = self.properties.constraint_type()
        dof = {"ux": True, "uy": True, "uz": True}
        constraint = {"constraint_type": ctype, "location": "", "degrees_of_freedom": dof}
        csel = self.properties.constraint_selection()
        if csel:
            constraint["selection"] = csel
        self.controller.constraints = [constraint]
        mag = self.properties.force_magnitude()
        dx, dy, dz = self.properties.force_direction()
        fsel = self.properties.force_selection()
        if not self.controller.forces:
            self.controller.forces = [{"magnitude": mag, "direction_x": dx,
                                       "direction_y": dy, "direction_z": dz}]
        else:
            self.controller.forces[0].update({"magnitude": mag, "direction_x": dx,
                                              "direction_y": dy, "direction_z": dz})
        if fsel:
            self.controller.forces[0]["selection"] = fsel
        else:
            self.controller.forces[0].pop("selection", None)

    def _set_busy(self, busy: bool, message: str) -> None:
        self.properties.set_busy(busy, message)

    def _on_clear_selection(self) -> None:
        self.viewport.clear_selection()
        self.design_tree.set_selection_clearable(False)

    def _on_selection(self, payload) -> None:
        if payload is None:
            self.design_tree.set_selection_clearable(False)
            self.statusBar().showMessage("Nada seleccionado.")
        else:
            self.design_tree.set_selection_clearable(True)
            if payload.get("kind") == "face":
                normal = payload.get("normal") or []
                nstr = ", ".join(f"{v:+.3f}" for v in normal)
                self.statusBar().showMessage(
                    f"Cara {payload.get('face_index')} de '{payload.get('key')}' "
                    f"· normal ({nstr}) · área {payload.get('area', 0.0):.2f} mm²")
            else:
                self.statusBar().showMessage(f"Seleccionado: {payload.get('key')}")
        # Keep the properties panel's advanced-selection controls in sync.
        view_sel = payload
        if view_sel is not None and "actor" in view_sel:
            view_sel = {k: v for k, v in view_sel.items() if k != "actor"}
        self.properties.set_viewport_selection(view_sel)

    def _on_view(self, key: str) -> None:
        self.viewport.set_view(key)
        for k, act in self._actions_view.items():
            act.setChecked(k == key)
        idx = self._view_combo.findData(key)
        if idx >= 0 and self._view_combo.currentIndex() != idx:
            self._view_combo.blockSignals(True)
            self._view_combo.setCurrentIndex(idx)
            self._view_combo.blockSignals(False)

    def _on_error(self, what: str, exc: Exception) -> None:
        self._set_busy(False, f"Error en {what}.")
        self.statusBar().showMessage(f"Error: {exc}")
        QMessageBox.critical(self, f"Error en {what}", str(exc))

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "Topología Optimizada — Desktop",
            "Interfaz desktop nativa (PySide6 + VTK).\n\n"
            "Flujo: Importar STEP → Cargas/Restricciones → Malla → FEA → "
            "Optimización SIMP.\n"
            "Navegación (estilo AutoCAD): zoom [rueda], pan [rueda pulsada], "
            "órbita [Shift + rueda pulsada], selección [clic izquierdo], "
            "ajustar vista al modelo [N].",
        )

    def _attach_bounds(self, bbox) -> None:
        self._bounds = bbox

    def closeEvent(self, event) -> None:
        try:
            self.viewport.finalize()
        except Exception:
            pass
        super().closeEvent(event)


class _BBox:
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax) -> None:
        self.xmin, self.xmax = xmin, xmax
        self.ymin, self.ymax = ymin, ymax
        self.zmin, self.zmax = zmin, zmax

    @property
    def dx(self) -> float:
        return self.xmax - self.xmin

    @property
    def dy(self) -> float:
        return self.ymax - self.ymin

    @property
    def dz(self) -> float:
        return self.zmax - self.zmin

    @property
    def center(self):
        return (0.5 * (self.xmin + self.xmax),
                0.5 * (self.ymin + self.ymax),
                0.5 * (self.zmin + self.zmax))