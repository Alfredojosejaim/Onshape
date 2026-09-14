"""PropertiesPanel - parameters + run controls for the native desktop UI.

Sections: "Optimizar (SIMP)" fields (objective, target volume fraction,
algorithm, penalization, filter radius, max iterations), Material,
Cargas / Fuerzas, Restricciones, Visibilidad and Estado. All the values feed
the SIMP engine through the controller; the public API used by MainWindow is
preserved (signals, set_enabled, set_busy, material_name, fixed axis helpers,
_element_size, _progress, _status).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QSlider, QCheckBox, QProgressBar, QScrollArea, QLineEdit,
)
from PySide6.QtCore import Qt, Signal


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setProperty("section", True)
    return lbl


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("dim", True)
    lbl.setStyleSheet("font-size: 11.5px;")
    return lbl


def _info_label(text: str, valid: bool = False) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setProperty("infovalid" if valid else "info", True)
    return lbl


class PropertiesPanel(QWidget):
    runOptimization = Signal(dict)   # {volume_fraction, max_iterations, penalization, filter_radius,...}
    runFEA = Signal()
    generateMesh = Signal(float)
    forceAdded = Signal(float, float, float, float, str, float)   # (magnitude, dx, dy, dz, load_case_id, weight)
    constraintAdded = Signal(str)                      # constraint_type ("fixed"/"pinned"/"roller")

    # Fase 0 (higiene): solo opciones con motor real detrás.
    # - Objetivo: el solver solo acepta MINIMIZE_COMPLIANCE
    #   (topo_problem.py::problem_to_solver_inputs rechaza el resto).
    # - Algoritmo: OC (SIMP), MMA propio (Fase 4), GCMMA Svanberg 2002
    #   (Fase 6, solo núcleo), ESO hard-kill (Fase 6a) y Level-Set HJ
    #   (Fase 6f).
    _OBJECTIVES = [
        "Compliance mínima (SIMP)",
    ]
    _ALGORITHMS = [
        "SIMP (Optimality Criteria)",
        "MMA (Moving Asymptotes)",
        "GCMMA (Globally Convergent MMA)",
        "ESO (Evolutionary)",
        "Level-Set",
    ]
    _CONSTRAINT_TYPES = [
        ("Fija (Empotramiento)", "fixed"),
        ("Pinnada (Rotación libre)", "pinned"),
        ("Rodillo (Desplazamiento guiado)", "roller"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # The whole property sheet lives inside a scroll area (the HTML sidebar
        # is scrollable; "Estado" stays at the bottom of the flow).
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        self._inner = inner
        col = QVBoxLayout(inner)
        col.setContentsMargins(14, 12, 14, 14)
        col.setSpacing(10)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # ---- Progress / status (kept out of the scroll flow, pinned) ----
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._status = _info_label("Listo para configurar optimización")
        self._status.setProperty("info", True)
        root.addWidget(self._status)

        # ============ "Optimizar (SIMP)" ============
        self._prop_title = QLabel("Optimizar (SIMP)")
        self._prop_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        col.addWidget(self._prop_title)

        col.addWidget(_field_label("Respuesta objetivo"))
        self._objective = QComboBox()
        self._objective.addItems(self._OBJECTIVES)
        col.addWidget(self._objective)

        col.addWidget(_field_label("Fracción de volumen objetivo"))
        self._volume = QSlider(Qt.Orientation.Horizontal)
        self._volume.setRange(10, 90)
        self._volume.setValue(35)
        self._volume.sliderMoved.connect(lambda _v: self._sync_volume_label())
        self._volume.valueChanged.connect(lambda _v: self._sync_volume_label())
        col.addWidget(self._volume)
        self._volume_info = _info_label("35% volumen retenido", valid=True)
        self._volume_info.setProperty("infovalid", True)
        self._volume_info.setStyleSheet("font-size: 11.5px;")
        col.addWidget(self._volume_info)

        col.addWidget(_field_label("Algoritmo"))
        self._algorithm = QComboBox()
        self._algorithm.addItems(self._ALGORITHMS)
        col.addWidget(self._algorithm)

        col.addWidget(_field_label("Criterio ESO"))
        self._eso_criterion = QComboBox()
        self._eso_criterion.addItems([
            "Compliance (energía de deformación)",
            "Tensión (von Mises)",
        ])
        col.addWidget(self._eso_criterion)

        # Fase 4.5d: parámetros finos antes fijos en defaults.
        col.addWidget(_field_label("Tasa evolutiva ESO (ER)"))
        self._evolutionary_rate = QDoubleSpinBox()
        self._evolutionary_rate.setRange(0.001, 0.5)
        self._evolutionary_rate.setDecimals(3)
        self._evolutionary_rate.setSingleStep(0.01)
        self._evolutionary_rate.setValue(0.02)
        col.addWidget(self._evolutionary_rate)

        col.addWidget(_field_label("CFL Level-Set"))
        self._ls_cfl = QDoubleSpinBox()
        self._ls_cfl.setRange(0.01, 1.0)
        self._ls_cfl.setDecimals(2)
        self._ls_cfl.setSingleStep(0.05)
        self._ls_cfl.setValue(0.5)
        col.addWidget(self._ls_cfl)

        col.addWidget(_field_label("Periodo redistancing Level-Set"))
        self._ls_hole_period = QSpinBox()
        self._ls_hole_period.setRange(1, 50)
        self._ls_hole_period.setValue(3)
        col.addWidget(self._ls_hole_period)

        # Fase 4.5d.3: plano de simetría opcional (eje + valor).
        self._sym_enable = QCheckBox("Forzar simetría del diseño")
        self._sym_enable.setChecked(False)
        col.addWidget(self._sym_enable)
        col.addWidget(_field_label("Eje del plano de simetría"))
        self._sym_axis = QComboBox()
        self._sym_axis.addItems(["x", "y", "z"])
        col.addWidget(self._sym_axis)
        col.addWidget(_field_label("Coordenada del plano (mm)"))
        self._sym_value = QDoubleSpinBox()
        self._sym_value.setRange(-1.0e6, 1.0e6)
        self._sym_value.setDecimals(3)
        self._sym_value.setValue(0.0)
        col.addWidget(self._sym_value)

        col.addWidget(_field_label("Penalización SIMP (p)"))
        self._penalization = QDoubleSpinBox()
        self._penalization.setRange(1.0, 6.0)
        self._penalization.setDecimals(1)
        self._penalization.setSingleStep(0.5)
        self._penalization.setValue(3.0)
        col.addWidget(self._penalization)

        col.addWidget(_field_label("Radio de filtro (mm)"))
        self._filter = QDoubleSpinBox()
        self._filter.setRange(0.1, 10.0)
        self._filter.setDecimals(2)
        self._filter.setSingleStep(0.1)
        self._filter.setValue(1.5)
        col.addWidget(self._filter)

        col.addWidget(_field_label("Iteraciones máximas"))
        self._iterations = QSpinBox()
        self._iterations.setRange(5, 500)
        self._iterations.setSingleStep(5)
        self._iterations.setValue(50)
        col.addWidget(self._iterations)

        # Fabricación activa + objetivo (prompt.md alta/alcance, con aprobación).
        self._min_thickness_enable = QCheckBox("Espesor mínimo explícito (mm)")
        self._min_thickness_enable.setChecked(False)
        col.addWidget(self._min_thickness_enable)
        self._min_thickness = QDoubleSpinBox()
        self._min_thickness.setRange(0.01, 100.0)
        self._min_thickness.setDecimals(2)
        self._min_thickness.setValue(0.6)
        col.addWidget(self._min_thickness)
        self._overhang_enable = QCheckBox("Restricción activa de overhang")
        self._overhang_enable.setChecked(False)
        col.addWidget(self._overhang_enable)
        col.addWidget(_field_label("Ángulo overhang (° desde vertical)"))
        self._overhang_angle = QDoubleSpinBox()
        self._overhang_angle.setRange(1.0, 89.0)
        self._overhang_angle.setValue(45.0)
        col.addWidget(self._overhang_angle)
        self._objective_minvol = QCheckBox("Minimizar volumen sujeto a compliance")
        self._objective_minvol.setChecked(False)
        col.addWidget(self._objective_minvol)
        col.addWidget(_field_label("Límite de compliance"))
        self._compliance_limit = QDoubleSpinBox()
        self._compliance_limit.setRange(0.001, 1.0e12)
        self._compliance_limit.setDecimals(3)
        self._compliance_limit.setValue(1000.0)
        col.addWidget(self._compliance_limit)

        self._btn_mesh = QPushButton("📐 Generar Malla FEM")
        self._btn_mesh.setEnabled(False)
        self._btn_fea = QPushButton("⚡ Análisis FEM")
        self._btn_fea.setEnabled(False)
        self._btn_run = QPushButton("▶ Ejecutar Optimización")
        self._btn_run.setProperty("htmlprimary", True)
        self._btn_run.setEnabled(False)
        col.addWidget(self._btn_mesh)
        col.addWidget(self._btn_fea)
        col.addWidget(self._btn_run)

        # ============ Material ============
        col.addWidget(_section_title("Material"))
        self._material = QComboBox()
        col.addWidget(self._material)

        # Hidden element-size control (kept for the malla toolbar action API).
        self._element_size = QDoubleSpinBox()
        self._element_size.setRange(0.0, 100.0)
        self._element_size.setDecimals(2)
        self._element_size.setValue(0.0)  # 0 => auto
        self._element_size.setSpecialValueText("Automática")
        self._element_size.setVisible(False)
        col.addWidget(self._element_size)

        # ============ Cargas / Fuerzas ============
        col.addWidget(_section_title("Cargas / Fuerzas"))
        col.addWidget(_field_label("Magnitud (N)"))
        self._force_mag = QDoubleSpinBox()
        self._force_mag.setRange(1.0, 1.0e9)
        self._force_mag.setDecimals(1)
        self._force_mag.setValue(1000.0)
        col.addWidget(self._force_mag)

        col.addWidget(_field_label("Dirección X"))
        self._force_dx = QDoubleSpinBox()
        self._force_dx.setRange(-1.0e6, 1.0e6)
        self._force_dx.setValue(0.0)
        col.addWidget(self._force_dx)
        col.addWidget(_field_label("Dirección Y"))
        self._force_dy = QDoubleSpinBox()
        self._force_dy.setRange(-1.0e6, 1.0e6)
        self._force_dy.setValue(-1.0)
        col.addWidget(self._force_dy)
        col.addWidget(_field_label("Dirección Z"))
        self._force_dz = QDoubleSpinBox()
        self._force_dz.setRange(-1.0e6, 1.0e6)
        self._force_dz.setValue(0.0)
        col.addWidget(self._force_dz)

        # Fase 4.5a: agrupador multicarga + peso (controller._load_case_vectors
        # agrupa por "load_case_id" y pondera con "weight"; vacío = caso único).
        col.addWidget(_field_label("Caso de carga (ID, opcional)"))
        self._load_case_id = QLineEdit()
        self._load_case_id.setPlaceholderText("p.ej. flexion (vacío = caso único)")
        col.addWidget(self._load_case_id)
        col.addWidget(_field_label("Peso del caso"))
        self._load_weight = QDoubleSpinBox()
        self._load_weight.setRange(0.01, 100.0)
        self._load_weight.setDecimals(3)
        self._load_weight.setSingleStep(0.1)
        self._load_weight.setValue(1.0)
        col.addWidget(self._load_weight)

        self._btn_add_force = QPushButton("+ Agregar Fuerza")
        col.addWidget(self._btn_add_force)

        # ============ Acoplamiento térmico (Fase 4.5d.4, opt-in) ============
        col.addWidget(_section_title("Acoplamiento térmico"))
        self._thermal_enable = QCheckBox("Usar acoplamiento térmico")
        self._thermal_enable.setChecked(False)
        self._thermal_enable.setEnabled(False)
        self._thermal_enable.setToolTip(
            "Sin estudio térmico resuelto: ejecute un estudio Thermal primero.")
        col.addWidget(self._thermal_enable)
        col.addWidget(_field_label("Estudio térmico fuente"))
        self._thermal_study = QComboBox()
        self._thermal_study.setEnabled(False)
        col.addWidget(self._thermal_study)
        col.addWidget(_field_label("α manual (1/K, 0 = del material)"))
        self._thermal_alpha = QDoubleSpinBox()
        self._thermal_alpha.setRange(0.0, 1.0e-3)
        self._thermal_alpha.setDecimals(9)
        self._thermal_alpha.setSingleStep(1e-6)
        self._thermal_alpha.setValue(0.0)
        self._thermal_alpha.setSpecialValueText("Auto (material)")
        col.addWidget(self._thermal_alpha)

        # ============ Restricciones ============
        col.addWidget(_section_title("Restricciones"))
        col.addWidget(_field_label("Tipo de fijación"))
        self._constraint = QComboBox()
        for label, _value in self._CONSTRAINT_TYPES:
            self._constraint.addItem(label)
        col.addWidget(self._constraint)
        self._btn_add_constraint = QPushButton("+ Agregar Restricción")
        col.addWidget(self._btn_add_constraint)

        # ============ Selección geométrica avanzada ============
        col.addWidget(_section_title("Selección avanzada"))
        self._sel_info = _info_label(
            "Haz clic sobre una cara del sólido en el visor para usarla como "
            "región de carga o restricción.")
        col.addWidget(self._sel_info)
        self._btn_sel_force = QPushButton("⚡ Usar cara como Fuerza")
        self._btn_sel_force.setEnabled(False)
        self._btn_sel_constraint = QPushButton("🔒 Usar cara como Restricción")
        self._btn_sel_constraint.setEnabled(False)
        self._btn_sel_clear = QPushButton("✕ Limpiar selección")
        self._btn_sel_clear.setEnabled(False)
        col.addWidget(self._btn_sel_force)
        col.addWidget(self._btn_sel_constraint)
        col.addWidget(self._btn_sel_clear)

        # ============ Visibilidad ============
        col.addWidget(_section_title("Visibilidad"))
        self._cb_geom = QCheckBox("Geometría Real (CAD)")
        self._cb_geom.setChecked(True)
        self._cb_forces = QCheckBox("Cargas / Fuerzas")
        self._cb_forces.setChecked(True)
        self._cb_constraints = QCheckBox("Restricciones")
        self._cb_constraints.setChecked(True)
        col.addWidget(self._cb_geom)
        col.addWidget(self._cb_forces)
        col.addWidget(self._cb_constraints)

        # ============ Estado ============
        col.addWidget(_section_title("Estado"))
        self._cad_meta = _info_label("", valid=True)
        self._file_info = _info_label("")
        col.addWidget(self._cad_meta)
        col.addWidget(self._file_info)
        col.addStretch(1)

        # Advanced-selection state (entity payload from the viewport)
        self._viewport_selection: dict | None = None
        self._pending_force_selection: dict | None = None
        self._pending_constraint_selection: dict | None = None

        # ---- Wiring ----
        self._btn_mesh.clicked.connect(lambda: self.generateMesh.emit(self._element_size.value()))
        self._btn_fea.clicked.connect(self.runFEA.emit)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_add_force.clicked.connect(self._on_add_force)
        self._btn_add_constraint.clicked.connect(self._on_add_constraint)
        self._cb_geom.toggled.connect(lambda checked: self._toggle_vis("geometry", checked))
        self._cb_forces.toggled.connect(lambda checked: self._toggle_vis("forces", checked))
        self._cb_constraints.toggled.connect(lambda checked: self._toggle_vis("constraints", checked))
        self._thermal_enable.toggled.connect(
            lambda checked: self._thermal_study.setEnabled(
                checked and self._thermal_study.count() > 0))
        self._btn_sel_force.clicked.connect(lambda: self._use_selection("force"))
        self._btn_sel_constraint.clicked.connect(lambda: self._use_selection("constraint"))
        self._btn_sel_clear.clicked.connect(self.clear_selection)

    # ------------------------------------------------------------------ #
    # Volume label helper
    # ------------------------------------------------------------------ #
    def _sync_volume_label(self) -> None:
        self._volume_info.setText(f"{self._volume.value()}% volumen retenido")

    # ------------------------------------------------------------------ #
    # Signals / interactions
    # ------------------------------------------------------------------ #
    def _on_run(self):
        algo_text = self._algorithm.currentText().upper()
        if "GCMMA" in algo_text:
            optimizer = "gcmma"
        elif "MMA" in algo_text:
            optimizer = "mma"
        elif "ESO" in algo_text:
            optimizer = "eso"
        elif "LEVEL" in algo_text:
            optimizer = "level_set"
        else:
            optimizer = "oc"
        crit_text = self._eso_criterion.currentText().upper()
        eso_criterion = "stress" if "TENSI" in crit_text else "compliance"
        params = {
            "volume_fraction": self._volume.value() / 100.0,
            "max_iterations": self._iterations.value(),
            "penalization": self._penalization.value(),
            "filter_radius": self._filter.value(),
            "tolerance": 1e-3,
            "material": self._material.currentText(),
            "optimizer": optimizer,
            "eso_criterion": eso_criterion,
            "evolutionary_rate": self._evolutionary_rate.value(),
            "ls_cfl": self._ls_cfl.value(),
            "ls_hole_period": self._ls_hole_period.value(),
            "symmetry_planes": (
                [[self._sym_axis.currentText(), self._sym_value.value()]]
                if self._sym_enable.isChecked() else None
            ),
            "min_thickness": (self._min_thickness.value()
                              if self._min_thickness_enable.isChecked() else None),
            "overhang_constraint": self._overhang_enable.isChecked(),
            "overhang_angle_deg": self._overhang_angle.value(),
            "objective": ("min_volume" if self._objective_minvol.isChecked()
                          else "min_compliance"),
            "compliance_limit": (self._compliance_limit.value()
                                 if self._objective_minvol.isChecked() else None),
        }
        self.runOptimization.emit(params)

    def _on_add_force(self) -> None:
        # Persist the configured force into the shared boundary state used by
        # FEA / SIMP: emit the values so MainWindow stores them in the
        # controller (force magnitude + direction + load case). This is not
        # a visual-only no-op: the force genuinely registers for the next
        # analysis run.
        self.forceAdded.emit(
            self._force_mag.value(),
            self._force_dx.value(),
            self._force_dy.value(),
            self._force_dz.value(),
            self.load_case_id(),
            self.load_weight(),
        )

    def _on_add_constraint(self) -> None:
        kind = self.constraint_type()
        # Persist the configured constraint type into the controller so the
        # next FEA / SIMP run applies it (not just a statusbar message).
        self.constraintAdded.emit(kind)
        label = self._CONSTRAINT_TYPES[self._constraint.currentIndex()][0]
        self.set_status(f"Restricción registrada: {label}")

    def _toggle_vis(self, which: str, checked: bool) -> None:
        self.set_status(f"Visibilidad {'Activada' if checked else 'Desactivada'}: {which}")

    # ------------------------------------------------------------------ #
    # Advanced geometric selection (viewport -> fuerza / restricción)
    # ------------------------------------------------------------------ #
    def set_viewport_selection(self, payload: dict | list | None) -> None:
        """Receive the entity picked in the viewport and update the controls."""
        # Backward compat: a list means an older multi-selection payload.
        if isinstance(payload, list):
            payload = payload[-1] if payload else None
        self._viewport_selection = payload
        is_face = bool(payload and payload.get("kind") == "face")
        self._btn_sel_force.setEnabled(is_face)
        self._btn_sel_constraint.setEnabled(is_face)
        if is_face:
            idx = payload["face_index"]
            meta = f"""Cara {idx} seleccionada en el visor:
normal ({', '.join(f'{v:+.3f}' for v in payload.get('normal', []))}) · 
área {payload.get('area', 0.0):.2f} mm²"""
            self._sel_info.setProperty("infovalid", True)
            self._sel_info.setStyleSheet("font-size: 11.5px;")
            self._sel_info.setText(meta)
            self._sel_info.setToolTip(meta)
        else:
            self._sel_info.setProperty("info", True)
            self._sel_info.setStyleSheet("")
            self._sel_info.setText(
                "Haz clic sobre una cara del sólido en el visor para usarla como "
                "región de carga o restricción.")

    def clear_selection(self) -> None:
        """Drop both pending advanced selections."""
        self._pending_force_selection = None
        self._pending_constraint_selection = None
        self.set_status("Selección geométrica avanzada limpiada.")

    def _use_selection(self, target: str) -> None:
        payload = self._viewport_selection
        if not payload or payload.get("kind") != "face":
            self.set_status("Selecciona primero una cara en el visor.")
            return
        idx = int(payload["face_index"])
        sel = {"type": "face", "face_indices": [idx], "tolerance": 0.5}
        if target == "force":
            self._pending_force_selection = sel
            name = "Fuerza"
        else:
            self._pending_constraint_selection = sel
            name = "Restricción"
        self.set_status(
            f"{name} → cara {idx} del sólido (selección avanzada activa). "
            f"Se aplicará a los nodos FEM sobre esa cara.")

    def force_selection(self) -> dict | None:
        return self._pending_force_selection

    def constraint_selection(self) -> dict | None:
        return self._pending_constraint_selection

    # ------------------------------------------------------------------ #
    # Controller wiring (public API used by MainWindow)
    # ------------------------------------------------------------------ #
    def set_materials(self, names: list[str], current: str | None = None) -> None:
        self._material.clear()
        self._material.addItems(names)
        if current and current in names:
            self._material.setCurrentText(current)

    def material_name(self) -> str:
        return self._material.currentText()

    def set_enabled(self, has_model: bool, has_mesh: bool) -> None:
        self._btn_mesh.setEnabled(has_model)
        self._btn_fea.setEnabled(has_mesh)
        self._btn_run.setEnabled(has_mesh)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self._progress.setVisible(busy)
        if busy:
            self._progress.setValue(0)
            self._btn_run.setEnabled(False)
            self._btn_fea.setEnabled(False)
            self._btn_mesh.setEnabled(False)
            self._status.setText(message)
        else:
            self._status.setText(message)

    def set_progress(self, value: int, message: str | None = None) -> None:
        self._progress.setValue(value)
        if message:
            self._status.setText(message)

    def set_status(self, message: str) -> None:
        self._status.setText(message)

    def set_cad_meta(self, message: str) -> None:
        self._cad_meta.setText(message)

    def set_file_info(self, message: str) -> None:
        self._file_info.setText(message)

    def volume_fraction(self) -> float:
        return self._volume.value() / 100.0

    def force_magnitude(self) -> float:
        return self._force_mag.value()

    def force_direction(self) -> list[float]:
        return [self._force_dx.value(), self._force_dy.value(), self._force_dz.value()]

    def load_case_id(self) -> str:
        """Agrupador multicarga (Fase 4.5a); "" = caso único."""
        return self._load_case_id.text().strip()

    def load_weight(self) -> float:
        """Peso relativo del caso de carga (Fase 4.5a)."""
        return self._load_weight.value()

    # ---- Acoplamiento térmico (Fase 4.5d.4) ----
    def set_thermal_studies(self, studies: list) -> None:
        """Puebla el selector con [(id, nombre)] de Thermal COMPLETED.

        Sin estudios: checkbox deshabilitado con tooltip explícito (nunca
        clickeable-para-fallar-después).
        """
        self._thermal_study.clear()
        for sid, name in studies:
            self._thermal_study.addItem(str(name), str(sid))
        has = bool(studies)
        self._thermal_enable.setEnabled(has)
        self._thermal_study.setEnabled(has and self._thermal_enable.isChecked())
        if has:
            self._thermal_enable.setToolTip(
                "Suma cargas de dilatación del estudio térmico al análisis.")
        else:
            self._thermal_enable.setChecked(False)
            self._thermal_enable.setToolTip(
                "Sin estudio térmico resuelto: ejecute un estudio Thermal primero.")

    def thermal_enabled(self) -> bool:
        return self._thermal_enable.isChecked() and self._thermal_enable.isEnabled()

    def thermal_study_id(self) -> str | None:
        if not self.thermal_enabled():
            return None
        return self._thermal_study.currentData()

    def thermal_alpha(self) -> float | None:
        """α manual o None (= usar thermal_expansion del material)."""
        if not self.thermal_enabled():
            return None
        v = self._thermal_alpha.value()
        return v if v > 0 else None

    def constraint_type(self) -> str:
        return self._CONSTRAINT_TYPES[self._constraint.currentIndex()][1]

    def fixed_axis(self) -> int:
        return 2  # default base plane; preserved for API compatibility

    def set_fixed_axis_code(self) -> int:
        return 2  # default downstream constraint fixes the Z-extreme nodes