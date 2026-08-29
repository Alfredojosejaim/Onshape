"""MainWindow - native desktop window with CAD-like layout:

  menu bar | toolbar | [ left panel | viewport | right panel ] | status bar

The viewport is visually dominant and the side panels are resizable splitters.
This window is the single integration point between the UI panels, the
PipelineController, and the Viewport3D.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QDockWidget,
    QToolBar, QFileDialog, QMessageBox, QLabel, QComboBox,
    QCheckBox, QTabWidget,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

import numpy as np

from desktop.viewport.viewport_3d import Viewport3D, StandardView
from desktop.pipeline.controller import PipelineController, PipelineError
from desktop.ui.panels.design_tree import DesignTreePanel
from desktop.ui.panels.properties import PropertiesPanel
from desktop.ui.panels.results import ResultsPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Topología Optimizada — CAD/CAE Desktop")
        self.resize(1400, 900)
        self.setMinimumSize(900, 600)

        self.controller = PipelineController()

        self._build_central()
        self._build_menus()
        self._build_toolbar()

        self.statusBar().showMessage("Listo. Archivo → Importar STEP (paso 1)")

    # ------------------------------------------------------------------ #
    # Central layout
    # ------------------------------------------------------------------ #
    def _build_central(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        split = QSplitter(Qt.Horizontal)

        # left dock panel
        self.left_dock = QWidget()
        left_layout = QVBoxLayout(self.left_dock)
        left_layout.setContentsMargins(4, 4, 4, 4)
        self.design_tree = DesignTreePanel()
        left_layout.addWidget(self.design_tree)

        # center viewport
        self.viewport = Viewport3D()
        self.viewport.selectionChanged.connect(self._on_selection)

        # right dock panel
        self.right_dock = QWidget()
        right_layout = QVBoxLayout(self.right_dock)
        right_layout.setContentsMargins(4, 4, 4, 4)
        self.properties = PropertiesPanel()
        self.results = ResultsPanel()

        tabs = self._make_right_tabs()
        right_layout.addWidget(tabs)

        split.addWidget(self.left_dock)
        split.addWidget(self.viewport)
        split.addWidget(self.right_dock)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([260, 900, 330])

        layout.addWidget(split)
        self.setCentralWidget(central)

        # wire signals
        self.properties.generateMesh.connect(self._on_generate_mesh)
        self.properties.runFEA.connect(self._on_run_fea)
        self.properties.runOptimization.connect(self._on_run_optimization)
        self.controller_reset_after_model()

    def _make_right_tabs(self):
        tabs = QTabWidget()
        tabs.addTab(self.properties, "Propiedades")
        tabs.addTab(self.results, "Resultados")
        return tabs

    # ------------------------------------------------------------------ #
    # Menus
    # ------------------------------------------------------------------ #
    def _build_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&Archivo")
        act_open = QAction("&Importar STEP...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._on_import)
        file_menu.addAction(act_open)

        file_menu.addSeparator()
        act_exit = QAction("&Salir", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = menubar.addMenu("&Vista")
        self._actions_view = {}
        presets = [
            ("Isométrica", StandardView.ISO),
            ("Frontal", StandardView.FRONT),
            ("Posterior", StandardView.BACK),
            ("Superior", StandardView.TOP),
            ("Inferior", StandardView.BOTTOM),
            ("Izquierda", StandardView.LEFT),
            ("Derecha", StandardView.RIGHT),
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

        disp_menu = menubar.addMenu("&Representación")
        for label, mode in [
            ("Sombreado", "surfaced"),
            ("Sombreado + aristas", "surfaced_edges"),
            ("Wireframe", "wireframe"),
            ("Transparencia", "transparent"),
        ]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.triggered.connect(lambda _=False, m=mode: self._on_display(m))
            disp_menu.addAction(act)

        help_menu = menubar.addMenu("Ay")
        act_about = QAction("Acerca de", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------ #
    # Toolbar
    # ------------------------------------------------------------------ #
    def _build_toolbar(self) -> None:
        tb = QToolBar("Herramientas")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(tb)

        self.act_import = QAction("Importar", self)
        self.act_import.triggered.connect(self._on_import)
        tb.addAction(self.act_import)

        self.act_mesh = QAction("Mallar", self)
        self.act_mesh.setEnabled(False)
        self.act_mesh.triggered.connect(lambda: self._on_generate_mesh(self.properties._element_size.value()))
        tb.addAction(self.act_mesh)

        self.act_fea = QAction("FEA", self)
        self.act_fea.setEnabled(False)
        self.act_fea.triggered.connect(self._on_run_fea)
        tb.addAction(self.act_fea)

        self.act_run = QAction("Ejecutar", self)
        self.act_run.setEnabled(False)
        self.act_run.triggered.connect(self._on_run_optimization_default)
        tb.addAction(self.act_run)

        tb.addSeparator()

        # view preset + display mode combos on toolbar
        self._view_combo = QComboBox()
        self._view_combo.addItem("Isométrica", StandardView.ISO)
        self._view_combo.addItem("Frontal", StandardView.FRONT)
        self._view_combo.addItem("Posterior", StandardView.BACK)
        self._view_combo.addItem("Superior", StandardView.TOP)
        self._view_combo.addItem("Inferior", StandardView.BOTTOM)
        self._view_combo.addItem("Izquierda", StandardView.LEFT)
        self._view_combo.addItem("Derecha", StandardView.RIGHT)
        self._view_combo.currentIndexChanged.connect(
            lambda i: self.viewport.set_view(self._view_combo.itemData(i)) if i >= 0 else None
        )
        tb.addWidget(QLabel("  Vista:"))
        tb.addWidget(self._view_combo)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Sombreado", "surfaced")
        self._mode_combo.addItem("Sombreado + aristas", "surfaced_edges")
        self._mode_combo.addItem("Wireframe", "wireframe")
        self._mode_combo.addItem("Transparencia", "transparent")
        self._mode_combo.currentIndexChanged.connect(
            lambda i: self.viewport.set_display_mode(self._mode_combo.itemData(i)) if i >= 0 else None
        )
        tb.addWidget(QLabel("  Modo:"))
        tb.addWidget(self._mode_combo)

        self._cb_axes = QCheckBox("Ejes")
        self._cb_axes.setChecked(True)
        self._cb_axes.toggled.connect(self.viewport.toggle_axes)
        tb.addWidget(self._cb_axes)

        self._cb_grid = QCheckBox("Rejilla")
        self._cb_grid.setChecked(True)
        self._cb_grid.toggled.connect(self.viewport.toggle_grid)
        tb.addWidget(self._cb_grid)

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar modelo STEP", "", "STEP (*.step *.stp);;Todos (*)"
        )
        if not path:
            return
        self._set_busy(True, "Importando geometría STEP...")
        self.statusBar().showMessage(f"Importando {os.path.basename(path)}...")

        def task():
            return self.controller.import_model(path)

        self.controller.run_in_background(
            task,
            on_done=self._on_import_done,
            on_error=lambda e: self._on_error("Importación", e),
        )

    def _on_import_done(self, payload) -> None:
        self.controller_reset_after_model()
        tess = payload["tessellation"]
        self._show_tessellation(tess)
        self._set_busy(False, f"Modelo importado: {payload['name']}")
        self.statusBar().showMessage(
            f"Modelo {payload['name']} cargado. Paso 2: generar malla."
        )

    def controller_reset_after_model(self) -> None:
        has_model = self.controller.model_id is not None
        self.properties.set_enabled(has_model, False)
        self.properties.set_materials(self.controller.material_names(),
                                      self.controller.material_name())
        _mesh = getattr(self, "act_mesh", None)
        _fea = getattr(self, "act_fea", None)
        _run = getattr(self, "act_run", None)
        if _mesh is not None:
            _mesh.setEnabled(has_model)
            _fea.setEnabled(False)
            _run.setEnabled(False)
        self.design_tree.set_context(
            self.controller.model_name if has_model else None,
            has_mesh=False,
            has_result=False,
        )
        self.results.reset_all()
        self.design_tree.clear_button().setEnabled(False)

    def _show_tessellation(self, tess: Dict[str, Any]) -> None:
        vertices = np.asarray(tess.get("vertices", []), dtype=float).reshape(-1, 3)
        indices = np.asarray(tess.get("indices", []), dtype=int)
        bbox_dict = tess.get("bbox")
        if bbox_dict is None:
            return
        # rebuild a lightweight bbox object for scene bounds
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
        # Scene stores bounds from bbox
        self._attach_bounds(bbox)
        self.viewport.load_model(vertices, triangles, bbox)

    # ------------------------------------------------------------------ #
    # Mesh
    # ------------------------------------------------------------------ #
    def _on_generate_mesh(self, element_size: float) -> None:
        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importa primero un STEP.")
            return
        self._set_busy(True, "Generando malla FEM (Gmsh / provisional)...")
        self.statusBar().showMessage("Generando malla volumétrica...")

        def task():
            return self.controller.generate_mesh(element_size)

        self.controller.run_in_background(task, on_done=self._on_mesh_done,
                                          on_error=lambda e: self._on_error("Mallado", e))

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
        self.act_fea.setEnabled(True)
        self.act_run.setEnabled(True)
        self.results.set_mesh(
            mesh.get("num_nodes", nodes.shape[0]),
            mesh.get("num_elements", elements.shape[0]),
            mesh.get("element_type", "tet4"),
            mesh.get("is_provisional", True),
        )
        self.statusBar().showMessage(
            f"Malla: {nodes.shape[0]} nodos, {elements.shape[0]} elementos."
        )
        self._set_busy(False, "Malla generada.")

    # ------------------------------------------------------------------ #
    # FEA
    # ------------------------------------------------------------------ #
    def _on_run_fea(self) -> None:
        if not self.controller.mesh:
            QMessageBox.warning(self, "Sin malla", "Genera la malla primero.")
            return
        self._configure_boundaries()
        self._set_busy(True, "Resolviendo análisis estático (FEA)...")

        def task():
            return self.controller.run_fea()

        self.controller.run_in_background(task, on_done=self._on_fea_done,
                                          on_error=lambda e: self._on_error("FEA", e))

    def _on_fea_done(self, result) -> None:
        self.results.set_result(result, self.properties.material_name())
        ok = bool(result.get("success"))
        self._set_busy(False, "FEA completado." if ok else "FEA con errores.")
        self.statusBar().showMessage(
            f"FEA: compliance = {result.get('final_compliance', result.get('compliance', '—')):.4e}"
        )

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
        self._set_busy(True, "Ejecutando optimización topológica (SIMP)...")

        def progress_cb(info: dict):
            self.results.append_history(info["iteration"], info["volume_fraction"], info["compliance"])
            pct = int(100 * info["iteration"] / max(1, params["max_iterations"]))
            self.results.set_result(
                {"success": True, "converged": False, "iterations": info["iteration"],
                 "final_volume_fraction": info["volume_fraction"],
                 "final_compliance": info["compliance"], "max_density_change": info["max_change"]},
                params["material"],
            )
            # update progress on the Qt thread via singleShot
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: (self.properties._progress.setValue(pct),
                                          self.properties._status.setText(
                                              f"Iteración {info['iteration']}: V={info['volume_fraction']:.2%}")))

        def task():
            return self.controller.run_optimization(
                volume_fraction=params["volume_fraction"],
                max_iterations=params["max_iterations"],
                penalization=params["penalization"],
                filter_radius=params["filter_radius"],
                tolerance=params["tolerance"],
                progress_cb=progress_cb,
            )

        self.controller.run_in_background(task, on_done=self._on_optimization_done,
                                          on_error=lambda e: self._on_error("Optimización", e))

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
            self.statusBar().showMessage(
                f"Optimización: V={result.get('final_volume_fraction', 0):.2%}, "
                f"c={result.get('final_compliance', 0):.4e}, iter={result.get('iterations')}"
            )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _configure_boundaries(self) -> None:
        """Push axis + material selections into the controller before solving."""
        axis_code = self.properties.set_fixed_axis_code()  # 0/1/2 for x/y/z
        material = self.properties.material_name()
        self.controller.set_material(material)
        self.controller.constraints = [{"constraint_type": "fixed", "location": "",
                                        "fixed_axis": axis_code}]
        # default distributed load along +Z at the free extreme
        if not self.controller.forces:
            self.controller.forces = [{"magnitude": 1000.0, "direction_x": 0, "direction_y": 0,
                                       "direction_z": 1.0}]

    def _set_busy(self, busy: bool, message: str) -> None:
        self.properties.set_busy(busy, message)

    def _on_selection(self, key: Optional[str]) -> None:
        self.design_tree.clear_button().setEnabled(key is not None)
        if key:
            self.statusBar().showMessage(f"Seleccionado: {key}")
        else:
            self.statusBar().showMessage("Nada seleccionado. Paso 2: generar malla.")

    def _on_view(self, key: str) -> None:
        self.viewport.set_view(key)
        for k, act in self._actions_view.items():
            act.setChecked(k == key)
        # sync combo
        idx = self._view_combo.findData(key)
        if idx >= 0 and self._view_combo.currentIndex() != idx:
            self._view_combo.blockSignals(True)
            self._view_combo.setCurrentIndex(idx)
            self._view_combo.blockSignals(False)

    def _on_display(self, mode: str) -> None:
        self.viewport.set_display_mode(mode)
        idx = self._mode_combo.findData(mode)
        if idx >= 0 and self._mode_combo.currentIndex() != idx:
            self._mode_combo.blockSignals(True)
            self._mode_combo.setCurrentIndex(idx)
            self._mode_combo.blockSignals(False)

    def _on_error(self, what: str, exc: Exception) -> None:
        self._set_busy(False, f"Error en {what}.")
        self.statusBar().showMessage(f"Error: {exc}")
        QMessageBox.critical(self, f"Error en {what}", str(exc))

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "Topología Optimizada — Desktop",
            "Interfaz desktop nativa (PySide6 + VTK) para optimización topológica.\n\n"
            "Flujo: Importar STEP → Generar malla → FEA → Optimización SIMP.\n"
            "Navegación: órbita [botón medio], pan [izquierdo], zoom [rueda].\n"
            "La CAD y solvers reutilizan el core existente.",
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
