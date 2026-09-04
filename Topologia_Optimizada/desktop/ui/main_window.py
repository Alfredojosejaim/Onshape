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
from typing import Any, Dict

import numpy as np
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFileDialog, QMessageBox, QInputDialog,
)

from desktop.pipeline.controller import PipelineController, launch_qt
from desktop.ui.components.menus import MenuBuilder
from desktop.ui.components.workspace import WorkspaceBuilder
from desktop.ui.components.overlays import OverlayBuilder
from desktop.ui.components.main_workspace import MainWorkspaceBuilder
from desktop.ui.components.widgets import repolish
from core.user_preferences import UserPreferences
from core.navigation import NavigationManager
from core.cad_entity import EntityType


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
        _, self._actions_view = MenuBuilder(self).build()

    # ------------------------------------------------------------------ #
    # Top bar, workspace tabs and ribbon
    # ------------------------------------------------------------------ #
    def _build_topbar(self) -> QWidget:
        return WorkspaceBuilder(self).build_topbar()

    def _build_workspace_tabs(self) -> QWidget:
        return WorkspaceBuilder(self).build_tabs()

    def _activate_tab(self, index: int) -> None:
        for i, b in enumerate(self._tabs):
            b.setProperty("active", i == index)
            repolish(b)

    def _build_ribbon(self) -> QWidget:
        return WorkspaceBuilder(self).build_ribbon()

    # ------------------------------------------------------------------ #
    # Central layout
    # ------------------------------------------------------------------ #
    def _build_central(self) -> None:
        # Composición física del workspace (sidebar, viewport, timeline, results)
        # delegada a MainWorkspaceBuilder; aquí solo queda la coordinación funcional.
        central = MainWorkspaceBuilder(self).build()

        # Viewport: selección (promote cara → sólido padre vía CAD service, Fase 2)
        self.viewport.selectionChanged.connect(self._on_selection)
        self.viewport.selection_manager.set_solid_resolver(
            lambda model_id, face_index: self.controller.cad.resolve_solid_for_face(model_id, face_index)
            if model_id and self.controller.cad.get_model_shape(model_id) else None
        )

        # Timeline
        self.timeline.playRequested.connect(self._on_play_next)
        self.timeline.resetRequested.connect(self._on_reset_flow)

        # ---- Viewport overlays (HTML chrome) ----
        self._build_viewport_overlays()

        self.setCentralWidget(central)

        # wire panel signals
        self.properties.generateMesh.connect(self._on_generate_mesh)
        self.properties.runFEA.connect(self._on_run_fea)
        self.properties.runOptimization.connect(self._on_run_optimization)
        self.properties.forceAdded.connect(self._on_add_force)
        self.properties.constraintAdded.connect(self._on_add_constraint)
        self.design_tree.clear_button().clicked.connect(self._on_clear_selection)
        self.controller_reset_after_model()

    def _build_viewport_overlays(self) -> None:
        OverlayBuilder(self, self.host).build()

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
        studies = list(self.controller.studies)
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

        studies = list(self.controller.studies)
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
    # Transform / Mirror / Pattern entry points
    # ------------------------------------------------------------------ #
    def _on_transform_op(self) -> None:
        """Handle the Transform entry points (menu + ribbon).

        Opens a functional TransformPanel that reuses the existing
        SelectionManager for capturing the body from the viewport.  Only on
        *Aceptar* is a TransformCommand built and executed through the
        pipeline; *Cancelar* leaves the model untouched.
        """
        from desktop.ui.panels.transform_panel import TransformPanel
        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importe un modelo STEP primero.")
            return
        panel = TransformPanel(parent=self,
                               get_solid_selections=self._current_solid_selections)
        result = panel.exec()
        if result != TransformPanel.Accepted or panel.command is None:
            self.statusBar().showMessage("Transformación cancelada.")
            return
        cmd = panel.command
        self._set_busy(True, f"Ejecutando transformación ({cmd.get_parameter('transform_type')})...")
        self.statusBar().showMessage("Ejecutando transformación...")
        self.controller.run_in_background(
            lambda: self.controller.execute_command(cmd),
            on_done=self._on_cad_edit_done,
            on_error=lambda e: self._on_error("Transformación", e),
        )

    def _on_mirror_op(self) -> None:
        from desktop.ui.panels.mirror_panel import MirrorPanel
        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importe un modelo STEP primero.")
            return
        panel = MirrorPanel(parent=self,
                            get_solid_selections=self._current_solid_selections)
        result = panel.exec()
        if result != MirrorPanel.Accepted or panel.command is None:
            self.statusBar().showMessage("Simetría cancelada.")
            return
        cmd = panel.command
        self._set_busy(True, "Ejecutando simetría (espejo)...")
        self.statusBar().showMessage("Ejecutando simetría...")
        self.controller.run_in_background(
            lambda: self.controller.execute_command(cmd),
            on_done=self._on_cad_edit_done,
            on_error=lambda e: self._on_error("Simetría", e),
        )

    def _on_pattern_op(self) -> None:
        from desktop.ui.panels.pattern_panel import PatternPanel
        if not self.controller.model_id:
            QMessageBox.warning(self, "Sin modelo", "Importe un modelo STEP primero.")
            return
        panel = PatternPanel(parent=self,
                             get_solid_selections=self._current_solid_selections)
        result = panel.exec()
        if result != PatternPanel.Accepted or panel.command is None:
            self.statusBar().showMessage("Patrón cancelado.")
            return
        cmd = panel.command
        self._set_busy(True, f"Ejecutando patrón ({cmd.get_parameter('pattern_type')})...")
        self.statusBar().showMessage("Ejecutando patrón...")
        self.controller.run_in_background(
            lambda: self.controller.execute_command(cmd),
            on_done=self._on_cad_edit_done,
            on_error=lambda e: self._on_error("Patrón", e),
        )

    def _on_cad_edit_done(self, result) -> None:
        """Common post-processing for transform/mirror/pattern results."""
        if not result.success:
            self.statusBar().showMessage(f"Error: {result.error_message}")
            QMessageBox.warning(self, "Operación CAD",
                                f"No se pudo completar la operación:\n{result.error_message}")
            return
        self._set_busy(False)
        self.statusBar().showMessage(
            f"Operación completada: {result.feature_id[:8]}...")
        # Re-render the CAD result model in the viewport.
        tess = self.controller.current_tessellation
        if tess and tess.get("vertices"):
            self._show_tessellation(tess)
            self.placeholder.hide()
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

    # ------------------------------------------------------------------ #
    # "Agregar Fuerza" / "Agregar Restricción" from the Properties panel
    # ------------------------------------------------------------------ #
    def _on_add_force(self, magnitude: float, dx: float, dy: float, dz: float) -> None:
        """Persist a force configured in the Properties panel into the shared
        boundary state consumed by FEA / SIMP."""
        if not self.controller.forces:
            self.controller.forces = [{}]
        self.controller.forces[0].update({
            "magnitude": magnitude, "direction_x": dx, "direction_y": dy, "direction_z": dz,
        })
        self.statusBar().showMessage(
            f"Fuerza registrada: {magnitude:g} N en ({dx:g}, {dy:g}, {dz:g})")

    def _on_add_constraint(self, constraint_type: str) -> None:
        """Persist a constraint configured in the Properties panel into the
        controller so the next FEA / SIMP run applies it."""
        dof = {"ux": True, "uy": True, "uz": True}
        constraint = {"constraint_type": constraint_type, "location": "",
                      "degrees_of_freedom": dof}
        csel = self.properties.constraint_selection()
        if csel:
            constraint["selection"] = csel
        self.controller.constraints = [constraint]
        self.statusBar().showMessage(f"Restricción registrada: {constraint_type}")

    def _on_validate(self) -> None:
        """Validate the current model state and report the real pipeline status.

        This replaces the former decorative button: it reflects the actual
        controller state (model, solids, mesh, boundary conditions, result)
        instead of printing a static message.
        """
        c = self.controller
        lines = []

        if not c.model_id:
            lines.append("• Modelo: ninguno (importe un STEP).")
            model_state = "SIN MODELO"
        else:
            lines.append(f"• Modelo: {c.model_name or c.model_id}")
            try:
                solids = c.cad.list_solids(c.model_id)
                lines.append(f"• Sólidos: {len(solids)}")
            except Exception:
                lines.append("• Sólidos: (no disponible)")
            model_state = "OK"

        if c.mesh_nodes is not None:
            lines.append(f"• Malla: {len(c.mesh_nodes)} nodos, {len(c.mesh_elements)} elementos.")
            mesh_state = "OK"
        else:
            lines.append("• Malla: no generada.")
            mesh_state = "SIN MALLA"

        lines.append(f"• Fuerzas: {len(c.forces)} · Restricciones: {len(c.constraints)}")
        conds = list(c.conditions.all) if hasattr(c.conditions, "all") else []
        lines.append(f"• Condiciones CAE: {len(conds)}")
        studies = list(c.document.studies) if c.document else []
        lines.append(f"• Estudios: {len(studies)}")

        if getattr(c, "result_densities", None) is not None:
            lines.append("• Resultado de optimización: disponible.")
            opt_state = "OK"
        else:
            lines.append("• Resultado de optimización: pendiente.")
            opt_state = "PENDIENTE"

        summary = " | ".join(
            s for s in (model_state, mesh_state, opt_state)
            if s not in ("OK",)
        ) or "TODO OK"
        lines.insert(0, f"[Validación] {summary}")
        self.statusBar().showMessage(f"Validación: {summary}")
        QMessageBox.information(self, "Validación del modelo", "\n".join(lines))

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
                fid = payload.get("id") or f"face_{payload.get('face_index')}"
                self.statusBar().showMessage(
                    f"Cara {payload.get('face_index')} seleccionada ({fid})"
                    f" · normal ({nstr}) · área {payload.get('area', 0.0):.2f} mm² · "
                    f"Ctrl+clic para añadir/quitar")
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