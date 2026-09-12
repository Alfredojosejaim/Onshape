"""StudyPanel - a functional Qt dialog to create and run engineering studies.

The dialog lets the user close the end-to-end CAD/CAE flow without any
redesign of the existing desktop:

    name / type        (topology optimization only for now)
    objective part     (real solids selected from the viewport)
    reusable conditions (shared by id, never duplicated)
    objective / parameters (volume fraction, iterations, penalization, ...)

The result is a fully configured study object handed back to the caller, which
registers it and runs it in the background through the pipeline.
"""

from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, QListWidget,
    QDialogButtonBox, QWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt

from desktop.ui.style import ERROR
from core.cad_entity import CadEntityRef, EntityType
from core.conditions import Condition, ConditionManager
from core.optimization_studies import TopologyOptimizationStudy

class StudyPanel(QDialog):
    """Modal dialog that produces a configured engineering study.

    Fase 1 (plan.md): expone lo que ya funciona en backend —
    Topology (SIMP), Thermal (execute_on_mesh) y Modal (execute_on_mesh).
    El controller ya ejecuta los tres (execute_study); aquí solo se
    configuran y se devuelven en ``self.study``.
    """

    def __init__(
        self,
        parent=None,
        condition_manager: Optional[ConditionManager] = None,
        condition_ids: Optional[List[str]] = None,
        available_conditions: Optional[List[Any]] = None,
        default_name: str = "",
        parts: Optional[List[CadEntityRef]] = None,
        model_id: Optional[str] = None,
        get_solid_selections: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Estudio de optimización")
        self.setMinimumWidth(460)
        self._conditions = condition_manager
        self._condition_ids = list(condition_ids or [])
        self._available = list(available_conditions or [])
        if self._conditions is not None and not self._available:
            self._available = self._conditions.all
        self._default_name = default_name
        self._model_id = model_id
        self._get_solid_selections = get_solid_selections
        self._parts = list(parts or [])
        self.study: Optional[TopologyOptimizationStudy] = None
        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
        from PySide6.QtWidgets import QLineEdit

        self._name = QLineEdit(self._default_name or "Estudio de optimización")
        form.addRow("Nombre:", self._name)

        self._type = QComboBox()
        self._type.addItem("Topology Optimization (SIMP)", "topology")
        self._type.addItem("Thermal (estacionario)", "thermal")
        self._type.addItem("Modal (frecuencias propias)", "modal")
        self._type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Tipo:", self._type)
        root.addLayout(form)

        # --- Part selection display ---
        parts_row = QHBoxLayout()
        parts_row.addWidget(QLabel("Pieza(s) objetivo:"), 1)
        btn_capture = QPushButton("Capturar desde selección")
        btn_capture.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_capture.clicked.connect(self._capture_parts)
        parts_row.addWidget(btn_capture)
        root.addLayout(parts_row)

        self._parts_list = QListWidget()
        self._parts_list.setMaximumHeight(100)
        self._parts_list.setFrameShape(QListWidget.Shape.NoFrame)
        root.addWidget(self._parts_list)

        # --- Optimization parameters ---
        params_group = QFormLayout()

        self._volfrac = QDoubleSpinBox()
        self._volfrac.setRange(0.01, 1.0)
        self._volfrac.setDecimals(2)
        self._volfrac.setSingleStep(0.05)
        self._volfrac.setValue(0.3)
        params_group.addRow("Fracción de volumen:", self._volfrac)

        self._max_iter = QSpinBox()
        self._max_iter.setRange(1, 500)
        self._max_iter.setValue(50)
        params_group.addRow("Iteraciones máx.:", self._max_iter)

        self._penal = QDoubleSpinBox()
        self._penal.setRange(1.0, 6.0)
        self._penal.setDecimals(1)
        self._penal.setValue(3.0)
        self._penal.setToolTip("Penalización SIMP")
        params_group.addRow("Penalización:", self._penal)

        self._radius = QDoubleSpinBox()
        self._radius.setRange(0.5, 10.0)
        self._radius.setDecimals(1)
        self._radius.setValue(1.5)
        params_group.addRow("Radio de filtro:", self._radius)

        self._tol = QDoubleSpinBox()
        self._tol.setDecimals(4)
        self._tol.setRange(1e-6, 1.0)
        self._tol.setSingleStep(0.0005)
        self._tol.setValue(1e-3)
        params_group.addRow("Tolerancia:", self._tol)
        root.addLayout(params_group)

        # --- Fase 1: parámetros Modal (solo visibles con tipo modal) ---
        self._modal_modes = QSpinBox()
        self._modal_modes.setRange(1, 50)
        self._modal_modes.setValue(5)
        self._modal_modes.setToolTip("Cantidad de modos (ModalParameters.mode_count)")
        params_group.addRow("Modos:", self._modal_modes)
        self._modal_fmin = QDoubleSpinBox()
        self._modal_fmin.setRange(0.0, 1.0e6)
        self._modal_fmin.setValue(0.0)
        self._modal_fmin.setSpecialValueText("Sin mín")
        params_group.addRow("Frec. mín (Hz):", self._modal_fmin)
        self._modal_fmax = QDoubleSpinBox()
        self._modal_fmax.setRange(0.0, 1.0e6)
        self._modal_fmax.setValue(0.0)
        self._modal_fmax.setSpecialValueText("Sin máx")
        params_group.addRow("Frec. máx (Hz):", self._modal_fmax)

        # --- Fase 1: nota Térmico (usa ThermalBoundary del backend) ---
        self._thermal_note = QLabel(
            "Térmico: define las condiciones de temperatura con la "
            "herramienta de condiciones; el solve usa execute_on_mesh().")
        self._thermal_note.setWordWrap(True)
        root.addWidget(self._thermal_note)

        # --- Conditions ---
        root.addWidget(QLabel("Condiciones reutilizables (carga / soporte / obstrucción):"))

        self._cond_list = QListWidget()
        for cond in self._available:
            bit = f"{cond.id}  —  {cond.name}"
            self._cond_list.addItem(bit)
            item = self._cond_list.item(self._cond_list.count() - 1)
            item.setSelected(str(cond.id) in self._condition_ids)
        root.addWidget(self._cond_list)

        bb = QDialogButtonBox()
        self._btn_ok = bb.addButton("Crear estudio", QDialogButtonBox.ButtonRole.AcceptRole)
        self._btn_cancel = bb.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        self._btn_ok.clicked.connect(self._on_accept)
        self._btn_cancel.clicked.connect(self.reject)
        root.addWidget(bb)

        self._error = QLabel("")
        self._error.setStyleSheet(f"color: {ERROR};")
        self._error.setWordWrap(True)
        root.addWidget(self._error)

        # Populate the parts list and disable OK if no parts selected.
        self._on_type_changed()

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _study_kind(self) -> str:
        return self._type.currentData() or "topology"

    def _on_type_changed(self) -> None:
        kind = self._study_kind()
        is_topo = kind == "topology"
        is_modal = kind == "modal"
        is_thermal = kind == "thermal"
        for w in (self._volfrac, self._max_iter, self._penal,
                  self._radius, self._tol):
            w.setEnabled(is_topo)
        for w in (self._modal_modes, self._modal_fmin, self._modal_fmax):
            w.setEnabled(is_modal)
        self._thermal_note.setVisible(is_thermal)
        self._refresh_parts_list()

    def _refresh_parts_list(self) -> None:
        """Rebuild the parts list widget from ``self._parts``."""
        self._parts_list.clear()
        if self._parts:
            for ref in self._parts:
                item = QListWidgetItem(ref.display_name)
                item.setData(Qt.ItemDataRole.UserRole, ref)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._parts_list.addItem(item)
        else:
            item = QListWidgetItem("(ninguna pieza seleccionada)")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._parts_list.addItem(item)
        # Fase 1: thermal/modal operan sobre la malla completa, no exigen pieza.
        self._btn_ok.setEnabled(self._study_kind() != "topology" or bool(self._parts))

    def _capture_parts(self) -> None:
        """Capture the solid(s) selected in the viewport (reuses the existing
        SelectionManager via the ``get_solid_selections`` callback)."""
        if self._get_solid_selections is None:
            self._error.setText("No hay sistema de selección disponible.")
            return
        refs = self._get_solid_selections() or []
        valid = []
        for ref in refs:
            if ref is None:
                continue
            if ref.entity_type != EntityType.SOLID:
                self._error.setText(
                    f"Solo se aceptan sólidos. Entidad inválida: {ref.display_name}")
                continue
            if self._model_id and ref.model_id and ref.model_id != self._model_id:
                self._error.setText(f"La pieza {ref.display_name} no pertenece al modelo actual.")
                continue
            if ref not in valid:
                valid.append(ref)
        if not valid:
            self._error.setText("No hay sólidos seleccionados en el viewport.")
            return
        self._parts = valid
        self._error.setText("")
        self._refresh_parts_list()

    def _on_accept(self) -> None:
        kind = self._study_kind()
        # Validate parts (solo topology exige pieza; thermal/modal usan la malla)
        if kind == "topology" and not self._parts:
            self._error.setText("Seleccione al menos una pieza sólida en el viewport antes de crear el estudio.")
            return
        for ref in self._parts:
            if ref.entity_type != EntityType.SOLID:
                self._error.setText(f"Solo se aceptan sólidos. Entidad inválida: {ref.display_name}")
                return
            if self._model_id and ref.model_id and ref.model_id != self._model_id:
                self._error.setText(f"La pieza {ref.display_name} no pertenece al modelo actual.")
                return

        chosen = [self._available[i] for i in range(self._cond_list.count())
                  if self._cond_list.item(i).isSelected()]
        try:
            if kind == "thermal":
                from core.cae_studies import ThermalAnalysis
                study = ThermalAnalysis(name=self._name.text().strip() or "Estudio térmico")
                study.model_id = self._model_id
                for cond in chosen:
                    # ThermalAnalysis no usa condition-ids: se resuelven como
                    # ThermalBoundary en el pipeline; se guardan los ids en
                    # metadata para no perder la selección del usuario.
                    study.metadata.setdefault("condition_ids", []).append(cond.id)
                if not chosen:
                    self._error.setText("Seleccione al menos una condición térmica (temperatura/flujo/convección).")
                    return
                self.study = study
                self.accept()
                return
            if kind == "modal":
                from core.cae_studies import ConstraintCase, ModalAnalysis
                study = ModalAnalysis(
                    name=self._name.text().strip() or "Estudio modal",
                    mode_count=int(self._modal_modes.value()))
                study.model_id = self._model_id
                fmin = float(self._modal_fmin.value())
                fmax = float(self._modal_fmax.value())
                study.modal.frequency_min = fmin if fmin > 0 else None
                study.modal.frequency_max = fmax if fmax > 0 else None
                for cond in chosen:
                    study.constraints.append(ConstraintCase(
                        name=getattr(cond, "name", str(cond.id)),
                        constraint_type="fixed",
                        metadata={"condition_id": cond.id}))
                if not study.constraints:
                    self._error.setText("Seleccione al menos una fijación (constraint) para el estudio modal.")
                    return
                self.study = study
                self.accept()
                return
            study = TopologyOptimizationStudy(name=self._name.text().strip() or "Estudio")
            study.model_id = self._model_id
            study.optimization_params.volume_fraction = float(self._volfrac.value())
            study.optimization_params.max_iterations = int(self._max_iter.value())
            study.optimization_params.penalization = float(self._penal.value())
            study.optimization_params.filter_radius = float(self._radius.value())
            study.optimization_params.convergence_tolerance = float(self._tol.value())
            for ref in self._parts:
                study.add_part(ref)
            for cond in chosen:
                study.add_condition(cond.id)
            if not study.conditions:
                self._error.setText("Seleccione al menos una condición (carga, soporte u obstrucción).")
                return
            self.study = study
            self.accept()
        except Exception as exc:  # pragma: no cover
            self._error.setText(f"No se pudo crear el estudio: {exc}")


class GenerativeStudyPanel(QDialog):
    """Modal dialog that produces a configured GenerativeDesignStudy.

    Scenario A optimises the existing imported geometry; scenario B
    generates geometry between ≥2 selected solid targets. Conditions are
    referenced by id from the shared ConditionManager (never duplicated).
    """

    def __init__(
        self,
        parent=None,
        condition_manager: Optional[ConditionManager] = None,
        default_name: str = "",
        parts: Optional[List[CadEntityRef]] = None,
        model_id: Optional[str] = None,
        get_solid_selections: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Diseño generativo")
        self.setMinimumWidth(460)
        self._conditions = condition_manager
        self._available = list(condition_manager.all) if condition_manager is not None else []
        self._default_name = default_name
        self._model_id = model_id
        self._get_solid_selections = get_solid_selections
        self._parts = list(parts or [])
        self.study = None
        self._build_ui()

    def _build_ui(self) -> None:
        from PySide6.QtWidgets import QLineEdit
        from core.generative import GenerativeDesignStudy  # noqa: F401 (used on accept)

        root = QVBoxLayout(self)
        root.setSpacing(12)
        form = QFormLayout()
        self._name = QLineEdit(self._default_name or "Diseño generativo")
        form.addRow("Nombre:", self._name)
        self._scenario = QComboBox()
        self._scenario.addItem("A — Optimizar geometría existente", "A")
        self._scenario.addItem("B — Conectar piezas (≥2 sólidos)", "B")
        self._scenario.currentIndexChanged.connect(self._refresh_parts_list)
        form.addRow("Escenario:", self._scenario)
        root.addLayout(form)

        parts_row = QHBoxLayout()
        parts_row.addWidget(QLabel("Pieza(s) / objetivos:"), 1)
        btn_capture = QPushButton("Capturar desde selección")
        btn_capture.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_capture.clicked.connect(self._capture_parts)
        parts_row.addWidget(btn_capture)
        root.addLayout(parts_row)

        self._parts_list = QListWidget()
        self._parts_list.setMaximumHeight(100)
        self._parts_list.setFrameShape(QListWidget.Shape.NoFrame)
        root.addWidget(self._parts_list)

        params = QFormLayout()
        self._resolution = QDoubleSpinBox()
        self._resolution.setRange(0.1, 20.0)
        self._resolution.setDecimals(1)
        self._resolution.setValue(1.0)
        self._resolution.setToolTip("Tamaño de voxel del espacio de diseño (escenario B)")
        params.addRow("Resolución:", self._resolution)
        root.addLayout(params)

        root.addWidget(QLabel("Condiciones reutilizables:"))
        self._cond_list = QListWidget()
        for cond in self._available:
            self._cond_list.addItem(f"{cond.id}  —  {cond.name}")
        root.addWidget(self._cond_list)

        bb = QDialogButtonBox()
        self._btn_ok = bb.addButton("Crear diseño", QDialogButtonBox.ButtonRole.AcceptRole)
        self._btn_cancel = bb.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        self._btn_ok.clicked.connect(self._on_accept)
        self._btn_cancel.clicked.connect(self.reject)
        root.addWidget(bb)

        self._error = QLabel("")
        self._error.setStyleSheet(f"color: {ERROR};")
        self._error.setWordWrap(True)
        root.addWidget(self._error)
        self._refresh_parts_list()

    def _scenario_key(self) -> str:
        return self._scenario.currentData()

    def _refresh_parts_list(self) -> None:
        self._parts_list.clear()
        for ref in self._parts:
            item = QListWidgetItem(ref.display_name)
            item.setData(Qt.ItemDataRole.UserRole, ref)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._parts_list.addItem(item)
        if not self._parts:
            item = QListWidgetItem("(ninguna pieza seleccionada)")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._parts_list.addItem(item)
        # Scenario A needs no targets (uses the imported model mesh);
        # scenario B needs at least 2 solid targets.
        self._btn_ok.setEnabled(self._scenario_key() == "A" or len(self._parts) >= 2)

    def _capture_parts(self) -> None:
        if self._get_solid_selections is None:
            self._error.setText("No hay sistema de selección disponible.")
            return
        valid = []
        for ref in self._get_solid_selections() or []:
            if ref is None:
                continue
            if ref.entity_type != EntityType.SOLID:
                self._error.setText(f"Solo se aceptan sólidos: {ref.display_name}")
                continue
            if self._model_id and ref.model_id and ref.model_id != self._model_id:
                self._error.setText(f"La pieza {ref.display_name} no pertenece al modelo actual.")
                continue
            if ref not in valid:
                valid.append(ref)
        if not valid:
            self._error.setText("No hay sólidos seleccionados en el viewport.")
            return
        self._parts = valid
        self._error.setText("")
        self._refresh_parts_list()

    def _on_accept(self) -> None:
        from core.generative import GenerativeDesignStudy

        scenario = self._scenario_key()
        chosen = [self._available[i] for i in range(self._cond_list.count())
                  if self._cond_list.item(i).isSelected()]
        if not chosen:
            self._error.setText("Seleccione al menos una condición.")
            return
        try:
            study = GenerativeDesignStudy(name=self._name.text().strip() or "Diseño generativo")
            study.design_space.resolution = float(self._resolution.value())
            for cond in chosen:
                study.add_condition(cond.id)
            if scenario == "A":
                if not self._model_id:
                    self._error.setText("El escenario A requiere un modelo STEP importado.")
                    return
                study.set_scenario_a(self._model_id)
            else:
                solids = [r for r in self._parts if r.entity_type == EntityType.SOLID]
                if len(solids) < 2:
                    self._error.setText("El escenario B requiere al menos 2 sólidos objetivo.")
                    return
                study.set_scenario_b(solids)
            self.study = study
            self.accept()
        except Exception as exc:  # pragma: no cover
            self._error.setText(f"No se pudo crear el diseño: {exc}")
