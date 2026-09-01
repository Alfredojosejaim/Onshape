"""ConditionPanel - a functional Qt dialog for CAD/CAE reusable conditions.

The panel configures one reusable Condition without owning any geometric logic:

    Carga            (sentido / orientación / magnitud o indeterminada)
    Elasticidad      (rango de flexión en mm)
    Obstrucción      (offset en mm)
    Región protegida (caras / referencias geométricas)

The dialog reuses the existing ``SelectionManager`` from the viewport: the
user picks faces / bodies in the 3D view and then captures them here.  It
builds a condition ``Command`` and hands it back to the caller, which is
responsible for executing it through the pipeline (registering the condition
and recording a Feature in the history).
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QDoubleSpinBox, QDialogButtonBox,
)
from PySide6.QtCore import Qt

from core.cad_entity import CadEntityRef, EntityType
from core.commands import (
    Command,
    ElasticityCommand,
    LoadConditionCommand,
    ObstructionCommand,
    ProtectedRegionCommand,
)


def _display(ref: Optional[CadEntityRef]) -> str:
    if ref is None:
        return "(ninguno)"
    return ref.display_name


class ConditionPanel(QDialog):
    """Modal dialog that configures and produces a condition Command.
    Set ``condition_kind`` to ``load | elasticity | obstruction | protected``.
    """

    def __init__(
        self,
        parent=None,
        condition_kind: str = "load",
        condition_name: str = "",
        get_face_selections: Optional[Callable[[], List[CadEntityRef]]] = None,
        get_solid_selections: Optional[Callable[[], List[CadEntityRef]]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self._title_for(condition_kind))
        self.setMinimumWidth(420)
        self._kind = condition_kind
        self._condition_name = condition_name
        self._get_faces = get_face_selections
        self._get_solids = get_solid_selections
        self.command: Optional[Command] = None
        self._body_mode = condition_kind == "obstruction"

        self._build_ui()
        self._build_kind_fields()

    # ------------------------------------------------------------------ #
    # Titles / labels
    # ------------------------------------------------------------------ #
    @staticmethod
    def _title_for(kind: str) -> str:
        return {
            "load": "Condición: Carga",
            "elasticity": "Condición: Elasticidad",
            "obstruction": "Condición: Obstrucción",
            "protected": "Condición: Región protegida",
        }.get(kind, "Condición")

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # Name
        form = QFormLayout()
        from PySide6.QtWidgets import QLineEdit
        self._name_edit = QLineEdit(self._condition_name)
        form.addRow("Nombre:", self._name_edit)
        root.addLayout(form)

        # Selection capture
        self._selection_label = QLabel(_display(None))
        btn = QPushButton("Capturar desde selección")
        btn.clicked.connect(self._capture)
        row = QHBoxLayout()
        self._selection_text = self._selection_label
        row.addWidget(self._selection_label, 1)
        row.addWidget(btn)
        root.addLayout(row)

        # Kind-specific fields (filled by _build_kind_fields)
        self._kind_form = QFormLayout()
        root.addLayout(self._kind_form)

        # Buttons
        bb = QDialogButtonBox()
        self._btn_accept = bb.addButton("Aceptar", QDialogButtonBox.ButtonRole.AcceptRole)
        self._btn_cancel = bb.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        self._btn_accept.clicked.connect(self._on_accept)
        self._btn_cancel.clicked.connect(self.reject)
        root.addWidget(bb)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e06c6c;")
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

    def _build_kind_fields(self) -> None:
        # load fields
        if self._kind == "load":
            self._orient_combo = QComboBox()
            self._orient_combo.addItem("Perpendicular", "perpendicular")
            self._orient_combo.addItem("Paralela", "parallel")
            self._orient_combo.addItem("Ángulo", "angle")
            self._kind_form.addRow("Orientación:", self._orient_combo)

            self._angle_spin = QDoubleSpinBox()
            self._angle_spin.setRange(0.0, 360.0)
            self._angle_spin.setValue(90.0)
            self._angle_spin.setEnabled(False)
            self._orient_combo.currentIndexChanged.connect(
                lambda i: self._angle_spin.setEnabled(self._orient_combo.itemData(i) == "angle"))
            self._kind_form.addRow("Ángulo (º):", self._angle_spin)

            self._mag_spin = QDoubleSpinBox()
            self._mag_spin.setRange(0.0, 1e12)
            self._mag_spin.setValue(1000.0)
            self._mag_spin.setDecimals(3)
            self._kind_form.addRow("Magnitud (N):", self._mag_spin)

            self._indet_check = QCheckBox("Magnitud indeterminada")
            self._indet_check.toggled.connect(lambda on: self._mag_spin.setEnabled(not on))
            self._kind_form.addRow("", self._indet_check)

        elif self._kind == "elasticity":
            self._flex_spin = QDoubleSpinBox()
            self._flex_spin.setRange(0.0, 1e6)
            self._flex_spin.setValue(1.0)
            self._flex_spin.setDecimals(3)
            self._kind_form.addRow("Rango de flexión (mm):", self._flex_spin)

        elif self._kind == "obstruction":
            self._offset_spin = QDoubleSpinBox()
            self._offset_spin.setRange(0.0, 1e6)
            self._offset_spin.setValue(0.0)
            self._offset_spin.setDecimals(3)
            self._kind_form.addRow("Offset (mm):", self._offset_spin)

    # ------------------------------------------------------------------ #
    # Selection capture (reuses the SelectionManager via the callback)
    # ------------------------------------------------------------------ #
    def _capture(self) -> None:
        if self._body_mode:
            refs = self._solid_selections()
            if not refs:
                self._set_error("No hay cuerpos seleccionados en el viewport.")
                return
            self._selection_label.setText(", ".join(_display(r) for r in refs))
            self._captured = refs
            self._error_label.setText("")
        else:
            refs = self._face_selections()
            if not refs:
                self._set_error("No hay caras seleccionadas en el viewport.")
                return
            self._selection_label.setText(", ".join(_display(r) for r in refs))
            self._captured = refs
            self._error_label.setText("")

    def _face_selections(self) -> List[CadEntityRef]:
        if self._get_faces is None:
            return []
        refs = self._get_faces()
        return [r for r in refs if r is not None and r.entity_type == EntityType.FACE]

    def _solid_selections(self) -> List[CadEntityRef]:
        if self._get_solids is None:
            return []
        refs = self._get_solids()
        return [r for r in refs if r is not None]

    # ------------------------------------------------------------------ #
    # Validation + accept
    # ------------------------------------------------------------------ #
    def _validate(self) -> List[str]:
        errors = []
        if not self._condition_name:
            pass  # name optional
        if not getattr(self, "_captured", None):
            errors.append("Debe capturar la selección (caras/cuerpos).")
        return errors

    def _on_accept(self) -> None:
        errors = self._validate()
        if errors:
            self._set_error(" ".join(errors))
            return
        cmd = self._build_command()
        if cmd is None:
            self._set_error("No se pudo configurar la condición.")
            return
        self.command = cmd
        self.accept()

    def _build_command(self) -> Optional[Command]:
        name = self._name_edit.text().strip() or self._condition_name
        refs = getattr(self, "_captured", [])
        if self._kind == "load":
            cmd = LoadConditionCommand()
            cmd.set_parameter("name", name)
            for r in refs:
                cmd.add_face(r)
            cmd.set_parameter("orientation", self._orient_combo.currentData())
            cmd.set_parameter("angle_deg", float(self._angle_spin.value()))
            cmd.set_parameter("magnitude", float(self._mag_spin.value()))
            cmd.set_parameter("indeterminate", bool(self._indet_check.isChecked()))
            return cmd
        if self._kind == "elasticity":
            cmd = ElasticityCommand()
            cmd.set_parameter("name", name)
            for r in refs:
                cmd.add_face(r)
            cmd.set_parameter("flex_range_mm", float(self._flex_spin.value()))
            return cmd
        if self._kind == "obstruction":
            cmd = ObstructionCommand()
            cmd.set_parameter("name", name)
            for r in refs:
                cmd.add_body(r)
            cmd.set_parameter("offset_mm", float(self._offset_spin.value()))
            return cmd
        if self._kind == "protected":
            cmd = ProtectedRegionCommand()
            cmd.set_parameter("name", name)
            for r in refs:
                cmd.add_face(r)
            return cmd
        return None

    def _set_error(self, msg: str) -> None:
        self._error_label.setText(msg)