"""workspace - composición del workspace (barra superior, pestañas y cinta).

Extrae de MainWindow la construcción visual de:
  - barra superior (título, chip de estado, botón Importar STEP, avatar)
  - pestañas de workspace (Modelo / Optimización / Simulación / Fabricación)
  - cinta de herramientas (ribbon) con sus grupos y controles de vista

Los handlers del owner (MainWindow) y el viewport/properties se pasan para
conectar exactamente las mismas señales de antes; aquí solo se ensambla la
parte visual y se registran las referencias (chip_status, _tabs, rb_*, ...) en
el owner.

ANTES → DESPUÉS → CONEXIÓN PRESERVADA
  MainWindow._build_topbar (306-345)        → WorkspaceBuilder.build_topbar
  MainWindow._build_workspace_tabs (347-372)→ WorkspaceBuilder.build_tabs
  MainWindow._build_ribbon (379-507)        → WorkspaceBuilder.build_ribbon
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox,
)
from PySide6.QtCore import Qt

from desktop.viewport.camera import StandardView
from desktop.ui.style import TEXT_FAINT, PALETTE
from desktop.ui.components.widgets import glyph_label, mini_label, RibbonTool, repolish


class WorkspaceBuilder:
    """Ensambla la barra superior, pestañas y cinta del workspace.

    ``owner`` es MainWindow: provee los handlers (``_on_*``) y recibe las
    referencias de widgets (``chip_status``, ``rb_*``, ``doc_label``, ...).
    """

    def __init__(self, owner) -> None:
        self.owner = owner

    # ------------------------------------------------------------------ #
    # Barra superior
    # ------------------------------------------------------------------ #
    def build_topbar(self) -> QWidget:
        owner = self.owner
        tb = QWidget()
        tb.setFixedHeight(52)
        grid = QGridLayout(tb)
        grid.setContentsMargins(16, 0, 16, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        left = glyph_label("◱", 18)
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
        owner.chip_status = chip
        btn_import = QPushButton("📁 Importar STEP")
        btn_import.setProperty("htmlprimary", True)
        btn_import.setStyleSheet("padding: 5px 12px; font-size: 12px;")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.clicked.connect(owner._on_import)
        owner._btn_import_top = btn_import
        avatar = QLabel("JD")
        avatar.setProperty("avatar", True)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(chip)
        rl.addWidget(btn_import)
        rl.addWidget(avatar)
        grid.addWidget(right, 0, 2, Qt.AlignmentFlag.AlignRight)

        owner.topbar = tb
        return tb

    # ------------------------------------------------------------------ #
    # Pestañas de workspace
    # ------------------------------------------------------------------ #
    def build_tabs(self) -> QWidget:
        owner = self.owner
        w = QWidget()
        w.setFixedHeight(34)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(2)

        owner._tabs = []
        for idx, label in enumerate(["Modelo", "Optimización", "Simulación", "Fabricación"]):
            b = QPushButton(label)
            b.setProperty("tab", True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setCheckable(False)
            b.clicked.connect(lambda _=False, i=idx: owner._activate_tab(i))
            if idx == 1:
                b.setProperty("active", True)
                repolish(b)
            owner._tabs.append(b)
            lay.addWidget(b)

        doc = QLabel("📁 Sin documento cargado")
        doc.setStyleSheet(f"font-size: 12px; color: {TEXT_FAINT}; margin-left: 14px; padding-left: 12px;")
        doc.setProperty("faint", True)
        owner.doc_label = doc
        lay.addWidget(doc, 1)
        return w

    # ------------------------------------------------------------------ #
    # Cinta de herramientas (ribbon)
    # ------------------------------------------------------------------ #
    def build_ribbon(self) -> QWidget:
        owner = self.owner

        def group(rows, label: str) -> QWidget:
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
            d.setStyleSheet(f"color: {PALETTE['border_soft']}; margin: 2px 14px;")
            d.setFixedHeight(48)
            return d

        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 8, 16, 4)
        lay.setSpacing(0)

        # Modelo
        owner.rb_import = RibbonTool("📁", "Importar STEP", "Importar archivo STEP local")
        owner.rb_import.clicked.connect(owner._on_import)
        owner.rb_mesh = RibbonTool("📐", "Malla FEM", "Generar malla volumétrica FEM (Tet4)")
        owner.rb_mesh.clicked.connect(
            lambda: owner._on_generate_mesh(owner.properties._element_size.value()))
        owner.rb_mesh_adaptive = RibbonTool("▦", "Malla Adaptativa", "Refinar malla localmente según densidad")
        owner.rb_mesh_adaptive.clicked.connect(owner._on_generate_adaptive_mesh)
        owner.rb_fea = RibbonTool("📊", "Análisis FEM", "Structural Mechanics — análisis estático")
        owner.rb_fea.clicked.connect(owner._on_run_fea)
        lay.addWidget(group([owner.rb_import, owner.rb_mesh, owner.rb_mesh_adaptive,
                             owner.rb_fea], "Modelo"))

        lay.addWidget(divider())

        # Edición
        owner.rb_union = RibbonTool("⊕", "Unión", "Unión booleana de sólidos")
        owner.rb_union.clicked.connect(lambda: owner._on_boolean_op("union"))
        owner.rb_difference = RibbonTool("⊖", "Resta", "Resta booleana de sólidos")
        owner.rb_difference.clicked.connect(lambda: owner._on_boolean_op("difference"))
        owner.rb_intersect = RibbonTool("⊗", "Intersección", "Intersección booleana de sólidos")
        owner.rb_intersect.clicked.connect(lambda: owner._on_boolean_op("intersection"))
        owner.rb_transform = RibbonTool("↗", "Transformar", "Trasladar / rotar cuerpo")
        owner.rb_transform.clicked.connect(owner._on_transform_op)
        owner.rb_mirror = RibbonTool("◇", "Simetría", "Simetría respecto a plano")
        owner.rb_mirror.clicked.connect(owner._on_mirror_op)
        owner.rb_pattern = RibbonTool("❖", "Patrón", "Patrón lineal / rectangular / circular")
        owner.rb_pattern.clicked.connect(owner._on_pattern_op)
        lay.addWidget(group([owner.rb_union, owner.rb_difference, owner.rb_intersect,
                             owner.rb_transform, owner.rb_mirror, owner.rb_pattern], "Edición"))

        lay.addWidget(divider())

        # Optimización
        owner.rb_sens = RibbonTool("📈", "Sensibilidad", "Análisis de sensibilidad (adjoint)")
        owner.rb_sens.clicked.connect(lambda: owner.statusBar().showMessage(
            "Sensibilidad adjunto: computada internamente por el motor SIMP en cada iteración."))
        owner.rb_filtros = RibbonTool("⚙", "Filtros", "Radio de filtro de densidad")
        owner.rb_filtros.clicked.connect(owner._on_focus_filter)
        owner.rb_opt = RibbonTool("▶", "Optimizar SIMP", "Optimization Application — algoritmo SIMP")
        owner.rb_opt.clicked.connect(owner._on_run_optimization_default)
        owner.rb_design_space = RibbonTool("◆", "Espacio de Diseño", "Definir espacio de diseño para optimización")
        owner.rb_design_space.clicked.connect(lambda: owner.statusBar().showMessage(
            "Espacio de Diseño: seleccione cuerpos para definir el dominio de optimización."))
        owner.rb_generative = RibbonTool("✧", "Generativo", "Diseño generativo con escenarios")
        owner.rb_generative.clicked.connect(lambda: owner.statusBar().showMessage(
            "Diseño Generativo: configure escenarios y restricciones."))
        lay.addWidget(group([owner.rb_sens, owner.rb_filtros, owner.rb_opt,
                             owner.rb_design_space, owner.rb_generative], "Optimización"))

        lay.addWidget(divider())

        # Postproceso
        owner.rb_viz = RibbonTool("👁", "Visualizar", "Visualizar campo de densidad por elemento")
        owner.rb_viz.clicked.connect(owner._on_visualize_result)
        owner.rb_export = RibbonTool("📤", "Exportar", "Exportar resultado de la optimización")
        owner.rb_export.clicked.connect(owner._on_export)
        lay.addWidget(group([owner.rb_viz, owner.rb_export], "Postproceso"))

        lay.addWidget(divider())

        # Herramientas
        owner.rb_validate = RibbonTool("✓", "Validar", "Validar geometría y restricciones")
        owner.rb_validate.clicked.connect(owner._on_validate)
        owner.rb_export_step = RibbonTool("💾", "Exportar STEP", "Exportar resultado como archivo STEP")
        owner.rb_export_step.clicked.connect(owner._on_export_step)
        lay.addWidget(group([owner.rb_validate, owner.rb_export_step], "Herramientas"))

        lay.addStretch(1)

        # right side: view preset + axes/grid toggles
        right = QWidget()
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(QLabel("Vista:"))
        combo = QComboBox()
        for label, key in [
            ("Isométrica", StandardView.ISO), ("Frontal", StandardView.FRONT),
            ("Superior", StandardView.TOP), ("Lateral derecha", StandardView.RIGHT),
        ]:
            combo.addItem(label, key)
        combo.currentIndexChanged.connect(
            lambda i: owner.viewport.set_view(combo.itemData(i)) if i >= 0 else None
        )
        rl.addWidget(combo)
        owner._view_combo = combo

        cb_axes = QPushButton("Ejes")
        cb_axes.setCheckable(True)
        cb_axes.setChecked(True)
        cb_axes.setStyleSheet("padding: 5px 10px; font-size: 11.5px;")
        cb_axes.toggled.connect(lambda on: owner.viewport.toggle_axes(on))
        rl.addWidget(cb_axes)
        owner._cb_axes = cb_axes

        cb_grid = QPushButton("Rejilla")
        cb_grid.setCheckable(True)
        cb_grid.setChecked(True)
        cb_grid.setStyleSheet("padding: 5px 10px; font-size: 11.5px;")
        cb_grid.toggled.connect(lambda on: owner.viewport.toggle_grid(on))
        rl.addWidget(cb_grid)
        owner._cb_grid = cb_grid
        lay.addWidget(right)

        owner.ribbon = w
        return w


__all__ = ["WorkspaceBuilder"]
