"""TransformPanel - a functional Qt dialog for CAD transform operations.

The panel configures a transform (translate / rotate / scale) without owning
any geometric logic:

    Tipo de transformación  (Trasladar / Rotar / Escalar)
    Cuerpo                   [Capturar desde selección]
    Parámetros específicos por tipo
        [Aceptar]  [Cancelar]

It reuses the existing ``SelectionManager`` from the viewport via the
``get_solid_selections`` callback, builds a ``core.commands.TransformCommand``
and hands it back to the caller, which executes it through the pipeline.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QDoubleSpinBox,
    QDialogButtonBox, QWidget,
)
from PySide6.QtCore import Qt

from desktop.ui.style import ERROR
from core.cad_entity import CadEntityRef, EntityType
from core.commands import TransformCommand, TransformType


def _display(ref: Optional[CadEntityRef]) -> str:
    if ref is None:
        return "(ninguno)"
    return ref.display_name


class TransformPanel(QDialog):
    """Modal dialog that configures and produces a TransformCommand."""

    def __init__(self, parent=None, get_solid_selections: Optional[Callable[[], List[CadEntityRef]]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Transformar cuerpo")
        self.setMinimumWidth(420)
        self._get_solid_selections = get_solid_selections
        self._target: Optional[CadEntityRef] = None
        self.command: Optional[TransformCommand] = None
        self._build_ui()
        self._on_type_changed()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # Transform type ------------------------------------------------- #
        type_label = QLabel("Tipo de transformación:")
        root.addWidget(type_label)
        self._type_group = QButtonGroup(self)
        type_row = QHBoxLayout()
        self._rb_translate = QRadioButton("Trasladar")
        self._rb_rotate = QRadioButton("Rotar")
        self._rb_scale = QRadioButton("Escalar")
        for rb in (self._rb_translate, self._rb_rotate, self._rb_scale):
            self._type_group.addButton(rb)
            type_row.addWidget(rb)
        for rb in (self._rb_translate, self._rb_rotate, self._rb_scale):
            rb.toggled.connect(lambda _=False: self._on_type_changed())
        self._rb_translate.setChecked(True)
        root.addLayout(type_row)

        # Target body ---------------------------------------------------- #
        form = QFormLayout()
        self._target_label = QLabel(_display(None))
        btn_target = QPushButton("Capturar desde selección")
        btn_target.clicked.connect(self._capture_target)
        tl = QHBoxLayout()
        tl.addWidget(self._target_label, 1)
        tl.addWidget(btn_target)
        form.addRow("Cuerpo:", self._wrap(tl))
        root.addLayout(form)

        # Parameter form ------------------------------------------------- #
        self._param_widget = QWidget()
        self._param_form = QFormLayout(self._param_widget)
        self._param_form.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._param_widget)

        # Buttons --------------------------------------------------------- #
        bb = QDialogButtonBox()
        self._btn_accept = bb.addButton("Aceptar", QDialogButtonBox.ButtonRole.AcceptRole)
        self._btn_cancel = bb.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        self._btn_accept.clicked.connect(self._on_accept)
        self._btn_cancel.clicked.connect(self.reject)
        root.addWidget(bb)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet(f"color: {ERROR};")
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

    def _wrap(self, layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    # ------------------------------------------------------------------ #
    # Parameter widgets per type
    # ------------------------------------------------------------------ #
    def _on_type_changed(self) -> None:
        # Clear the previous parameter widgets.
        while self._param_form.count():
            item = self._param_form.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

        if self._rb_translate.isChecked():
            self._dx = QDoubleSpinBox(); self._dx.setRange(-1e6, 1e6); self._dx.setValue(10.0)
            self._dy = QDoubleSpinBox(); self._dy.setRange(-1e6, 1e6); self._dy.setValue(0.0)
            self._dz = QDoubleSpinBox(); self._dz.setRange(-1e6, 1e6); self._dz.setValue(0.0)
            row = QHBoxLayout()
            row.addWidget(self._dx); row.addWidget(self._dy); row.addWidget(self._dz)
            self._param_form.addRow("Traslación (x, y, z):", self._wrap(row))
        elif self._rb_rotate.isChecked():
            self._ra_x = QDoubleSpinBox(); self._ra_x.setRange(-1e6, 1e6); self._ra_x.setValue(0.0)
            self._ra_y = QDoubleSpinBox(); self._ra_y.setRange(-1e6, 1e6); self._ra_y.setValue(0.0)
            self._ra_z = QDoubleSpinBox(); self._ra_z.setRange(-1e6, 1e6); self._ra_z.setValue(1.0)
            row = QHBoxLayout()
            row.addWidget(self._ra_x); row.addWidget(self._ra_y); row.addWidget(self._ra_z)
            self._param_form.addRow("Eje de rotación (x, y, z):", self._wrap(row))
            self._r_angle = QDoubleSpinBox(); self._r_angle.setRange(0.0, 720.0); self._r_angle.setValue(90.0)
            self._param_form.addRow("Ángulo (°):", self._r_angle)
        elif self._rb_scale.isChecked():
            self._s_factor = QDoubleSpinBox(); self._s_factor.setRange(0.01, 100.0); self._s_factor.setValue(1.0)
            self._param_form.addRow("Factor de escala:", self._s_factor)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    # ------------------------------------------------------------------ #
    # Selection capture (reuses the SelectionManager via the callback)
    # ------------------------------------------------------------------ #
    def _solid_selections(self) -> List[CadEntityRef]:
        if self._get_solid_selections is None:
            return []
        refs = self._get_solid_selections()
        return [r for r in refs if r is not None and r.entity_type == EntityType.SOLID]

    def _capture_target(self) -> None:
        solids = self._solid_selections()
        if not solids:
            self._set_error("No hay cuerpos seleccionados en el viewport.")
            return
        self._target = solids[0]
        self._target_label.setText(_display(self._target))
        self._error_label.setText("")

    def _set_error(self, msg: str) -> None:
        self._error_label.setText(msg)

    # ------------------------------------------------------------------ #
    # Validation + accept
    # ------------------------------------------------------------------ #
    def selected_type(self) -> str:
        if self._rb_rotate.isChecked():
            return TransformType.ROTATE.value
        if self._rb_scale.isChecked():
            return TransformType.SCALE.value
        return TransformType.TRANSLATE.value

    def _param_dict(self) -> dict:
        if self._rb_translate.isChecked():
            return {"translation": f"{self._dx.value()}, {self._dy.value()}, {self._dz.value()}"}
        if self._rb_rotate.isChecked():
            return {"rotation_axis": f"{self._ra_x.value()}, {self._ra_y.value()}, {self._ra_z.value()}",
                    "rotation_angle": self._r_angle.value()}
        return {"scale_factor": self._s_factor.value()}

    def _validate(self) -> List[str]:
        errors = []
        if self._target is None:
            errors.append("Debe seleccionar un cuerpo.")
        if self._rb_scale.isChecked() and self._s_factor.value() <= 0:
            errors.append("El factor de escala debe ser mayor que 0.")
        return errors

    def _on_accept(self) -> None:
        errors = self._validate()
        if errors:
            self._set_error(" ".join(errors))
            return
        cmd = TransformCommand()
        cmd.set_parameter("transform_type", self.selected_type())
        for k, v in self._param_dict().items():
            cmd.set_parameter(k, v)
        cmd.set_target(self._target)
        self.command = cmd
        self.accept()
