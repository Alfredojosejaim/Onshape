"""PropertiesPanel - topology optimization study parameters + run controls.

The fields mirror the reference engineering mockup (ejemplo_interfaz_grafica.html):
objective, target volume fraction, material, max iterations, penalization,
filter radius. Values feed the SIMP engine through the controller.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QGroupBox, QFormLayout, QProgressBar,
    QCheckBox,
)
from PySide6.QtCore import Signal


class PropertiesPanel(QWidget):
    runOptimization = Signal(dict)   # {volume_fraction, max_iterations, penalization, filter_radius}
    runFEA = Signal()
    generateMesh = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        title = QLabel("Panel de Propiedades")
        title.setStyleSheet("font-weight: 600; color: #f2f2f3;")
        root.addWidget(title)

        grp = QGroupBox("Optimización topológica")
        form = QFormLayout(grp)
        form.setLabelAlignment(form.labelAlignment())

        self._objective = QComboBox()
        self._objective.addItems(["Minimizar masa", "Maximizar rigidez"])

        self._volume = QDoubleSpinBox()
        self._volume.setRange(0.05, 1.0)
        self._volume.setDecimals(2)
        self._volume.setSingleStep(0.05)
        self._volume.setValue(0.35)
        self._volume.setSuffix(" (fracción)")

        self._material = QComboBox()

        self._iterations = QSpinBox()
        self._iterations.setRange(1, 200)
        self._iterations.setValue(30)

        self._penalization = QDoubleSpinBox()
        self._penalization.setRange(1.0, 6.0)
        self._penalization.setDecimals(1)
        self._penalization.setValue(3.0)
        self._penalization.setSingleStep(0.5)

        self._filter = QDoubleSpinBox()
        self._filter.setRange(0.1, 10.0)
        self._filter.setDecimals(2)
        self._filter.setValue(1.5)

        form.addRow("Objetivo", self._objective)
        form.addRow("Fracción de volumen", self._volume)
        form.addRow("Material", self._material)
        form.addRow("Iteraciones máx.", self._iterations)
        form.addRow("Penalización", self._penalization)
        form.addRow("Radio de filtro", self._filter)
        root.addWidget(grp)

        # Element size
        mesh_grp = QGroupBox("Malla")
        mform = QFormLayout(mesh_grp)
        self._element_size = QDoubleSpinBox()
        self._element_size.setRange(0.0, 100.0)
        self._element_size.setDecimals(2)
        self._element_size.setValue(0.0)  # 0 => auto
        self._element_size.setSpecialValueText("Automática")
        mform.addRow("Tamaño elemento", self._element_size)
        root.addWidget(mesh_grp)

        # boundary defaults
        bc_grp = QGroupBox("Condiciones de contorno")
        bform = QFormLayout(bc_grp)
        self._fixed_axis = QComboBox()
        self._fixed_axis.addItems(["Z mín (base)", "Y mín", "X mín"])
        bform.addRow("Plano fijado", self._fixed_axis)
        root.addWidget(bc_grp)

        self._btn_mesh = QPushButton("Generar malla")
        self._btn_mesh.setEnabled(False)

        self._btn_fea = QPushButton("Resolver FEA estática")
        self._btn_fea.setEnabled(False)

        self._btn_run = QPushButton("Ejecutar optimización")
        self._btn_run.setProperty("primary", True)
        self._btn_run.setEnabled(False)

        root.addWidget(self._btn_mesh)
        root.addWidget(self._btn_fea)
        root.addWidget(self._btn_run)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color: #9a9ba0;")
        root.addWidget(self._status, 1)

        self._btn_mesh.clicked.connect(lambda: self.generateMesh.emit(self._element_size.value()))
        self._btn_fea.clicked.connect(self.runFEA.emit)
        self._btn_run.clicked.connect(self._on_run)

    def _on_run(self):
        params = {
            "volume_fraction": self._volume.value(),
            "max_iterations": self._iterations.value(),
            "penalization": self._penalization.value(),
            "filter_radius": self._filter.value(),
            "tolerance": 1e-3,
            "material": self._material.currentText(),
        }
        self.runOptimization.emit(params)

    # ------------------------------------------------------------------ #
    # Controller wiring
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

    def fixed_axis(self) -> int:
        return self._fixed_axis.currentIndex()  # 0=z,1=y,2=x -> our code uses 2 for z

    def set_fixed_axis_code(self) -> int:
        idx = self._fixed_axis.currentIndex()
        return {0: 2, 1: 1, 2: 0}[idx]
