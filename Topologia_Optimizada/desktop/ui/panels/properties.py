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
    QPushButton, QSlider, QCheckBox, QProgressBar, QScrollArea,
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

    _OBJECTIVES = [
        "Compliance mínima (SIMP)",
        "Masa mínima",
        "Desplazamiento máx. nodal",
    ]
    _ALGORITHMS = [
        "MMA (Method of Moving Asymptotes)",
        "GCMMA",
        "Steepest descent",
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
        root.addWidget(scroll)

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

        self._btn_add_force = QPushButton("+ Agregar Fuerza")
        col.addWidget(self._btn_add_force)

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
        params = {
            "volume_fraction": self._volume.value() / 100.0,
            "max_iterations": self._iterations.value(),
            "penalization": self._penalization.value(),
            "filter_radius": self._filter.value(),
            "tolerance": 1e-3,
            "material": self._material.currentText(),
        }
        self.runOptimization.emit(params)

    def _on_add_force(self) -> None:
        self.set_status(
            f"Fuerza registrada: {self._force_mag.value():g} N "
            f"en ({self._force_dx.value():g}, {self._force_dy.value():g}, {self._force_dz.value():g})"
        )

    def _on_add_constraint(self) -> None:
        kind = self._CONSTRAINT_TYPES[self._constraint.currentIndex()][0]
        self.set_status(f"Restricción registrada: {kind}")

    def _toggle_vis(self, which: str, checked: bool) -> None:
        self.set_status(f"Visibilidad {'Activada' if checked else 'Desactivada'}: {which}")

    # ------------------------------------------------------------------ #
    # Advanced geometric selection (viewport -> fuerza / restricción)
    # ------------------------------------------------------------------ #
    def set_viewport_selection(self, payload: dict | None) -> None:
        """Receive the entity picked in the viewport and update the controls."""
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

    def constraint_type(self) -> str:
        return self._CONSTRAINT_TYPES[self._constraint.currentIndex()][1]

    def fixed_axis(self) -> int:
        return 2  # default base plane; preserved for API compatibility

    def set_fixed_axis_code(self) -> int:
        return 2  # default downstream constraint fixes the Z-extreme nodes