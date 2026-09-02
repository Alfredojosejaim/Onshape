"""PatternPanel - a functional Qt dialog for CAD pattern operations.

The panel configures a linear / rectangular / circular pattern of a solid
body without owning any geometric logic:

    Tipo de patrón        (Lineal / Rectangular / Circular)
    Cuerpo                 [Capturar desde selección]
    Parámetros según tipo
        [Aceptar]  [Cancelar]

It reuses the existing ``SelectionManager`` via ``get_solid_selections``,
builds a ``core.commands.PatternCommand`` and hands it back to the caller,
which executes it through the pipeline.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QDoubleSpinBox, QSpinBox,
    QDialogButtonBox, QWidget,
)

from core.cad_entity import CadEntityRef, EntityType
from core.commands import PatternCommand, PatternType


def _display(ref: Optional[CadEntityRef]) -> str:
    if ref is None:
        return "(ninguno)"
    return ref.display_name


class PatternPanel(QDialog):
    """Modal dialog that configures and produces a PatternCommand."""

    def __init__(self, parent=None, get_solid_selections: Optional[Callable[[], List[CadEntityRef]]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Patrón")
        self.setMinimumWidth(440)
        self._get_solid_selections = get_solid_selections
        self._target: Optional[CadEntityRef] = None
        self.command: Optional[PatternCommand] = None
        self._build_ui()
        self._on_type_changed()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        type_label = QLabel("Tipo de patrón:")
        root.addWidget(type_label)
        self._type_group = QButtonGroup(self)
        type_row = QHBoxLayout()
        self._rb_linear = QRadioButton("Lineal")
        self._rb_rect = QRadioButton("Rectangular")
        self._rb_circ = QRadioButton("Circular")
        for rb in (self._rb_linear, self._rb_rect, self._rb_circ):
            self._type_group.addButton(rb)
            type_row.addWidget(rb)
            rb.toggled.connect(lambda _=False: self._on_type_changed())
        self._rb_linear.setChecked(True)
        root.addLayout(type_row)

        form = QFormLayout()
        self._target_label = QLabel(_display(None))
        btn_target = QPushButton("Capturar desde selección")
        btn_target.clicked.connect(self._capture_target)
        tl = QHBoxLayout()
        tl.addWidget(self._target_label, 1)
        tl.addWidget(btn_target)
        form.addRow("Cuerpo:", self._wrap(tl))
        root.addLayout(form)

        self._param_widget = QWidget()
        self._param_form = QFormLayout(self._param_widget)
        self._param_form.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._param_widget)

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

    def _wrap(self, layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    # ------------------------------------------------------------------ #
    # Parameter widgets per type
    # ------------------------------------------------------------------ #
    def _on_type_changed(self) -> None:
        while self._param_form.count():
            item = self._param_form.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

        if self._rb_linear.isChecked():
            self._count = QSpinBox(); self._count.setRange(2, 100); self._count.setValue(3)
            self._spacing = QDoubleSpinBox(); self._spacing.setRange(0.0, 1e6); self._spacing.setValue(10.0)
            self._dirx = self._vec_spin(1.0); self._diry = self._vec_spin(0.0); self._dirz = self._vec_spin(0.0)
            drow = QHBoxLayout()
            drow.addWidget(self._dirx); drow.addWidget(self._diry); drow.addWidget(self._dirz)
            self._param_form.addRow("Dirección (x, y, z):", self._wrap(drow))
            self._param_form.addRow("Cantidad:", self._count)
            self._param_form.addRow("Separación:", self._spacing)
        elif self._rb_rect.isChecked():
            self._count = QSpinBox(); self._count.setRange(2, 100); self._count.setValue(3)
            self._count2 = QSpinBox(); self._count2.setRange(1, 100); self._count2.setValue(2)
            self._spacing = QDoubleSpinBox(); self._spacing.setRange(0.0, 1e6); self._spacing.setValue(10.0)
            self._dirx = self._vec_spin(1.0); self._diry = self._vec_spin(0.0); self._dirz = self._vec_spin(0.0)
            drow = QHBoxLayout()
            drow.addWidget(self._dirx); drow.addWidget(self._diry); drow.addWidget(self._dirz)
            self._param_form.addRow("Dirección 1 (x, y, z):", self._wrap(drow))
            self._dir2x = self._vec_spin(0.0); self._dir2y = self._vec_spin(1.0); self._dir2z = self._vec_spin(0.0)
            d2row = QHBoxLayout()
            d2row.addWidget(self._dir2x); d2row.addWidget(self._dir2y); d2row.addWidget(self._dir2z)
            self._param_form.addRow("Dirección 2 (x, y, z):", self._wrap(d2row))
            self._param_form.addRow("Cantidad (dir. 1):", self._count)
            self._param_form.addRow("Cantidad (dir. 2):", self._count2)
            self._param_form.addRow("Separación:", self._spacing)
        elif self._rb_circ.isChecked():
            self._count = QSpinBox(); self._count.setRange(2, 100); self._count.setValue(6)
            self._angle = QDoubleSpinBox(); self._angle.setRange(1.0, 360.0); self._angle.setValue(360.0)
            self._axx = self._vec_spin(0.0); self._axy = self._vec_spin(0.0); self._axz = self._vec_spin(1.0)
            arow = QHBoxLayout()
            arow.addWidget(self._axx); arow.addWidget(self._axy); arow.addWidget(self._axz)
            self._param_form.addRow("Eje (x, y, z):", self._wrap(arow))
            self._cx = self._vec_spin(0.0); self._cy = self._vec_spin(0.0); self._cz = self._vec_spin(0.0)
            crow = QHBoxLayout()
            crow.addWidget(self._cx); crow.addWidget(self._cy); crow.addWidget(self._cz)
            self._param_form.addRow("Centro (x, y, z):", self._wrap(crow))
            self._param_form.addRow("Cantidad:", self._count)
            self._param_form.addRow("Ángulo total (°):", self._angle)

    def _vec_spin(self, value: float = 0.0) -> QDoubleSpinBox:
        s = QDoubleSpinBox(); s.setRange(-1e6, 1e6); s.setValue(value)
        return s

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    # ------------------------------------------------------------------ #
    # Selection capture
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
        if self._rb_rect.isChecked():
            return PatternType.RECTANGULAR.value
        if self._rb_circ.isChecked():
            return PatternType.CIRCULAR.value
        return PatternType.LINEAR.value

    def _param_dict(self) -> dict:
        if self._rb_linear.isChecked():
            return {"pattern_type": PatternType.LINEAR.value,
                    "direction": f"{self._dirx.value()}, {self._diry.value()}, {self._dirz.value()}",
                    "count": self._count.value(), "spacing": self._spacing.value()}
        if self._rb_rect.isChecked():
            return {"pattern_type": PatternType.RECTANGULAR.value,
                    "direction": f"{self._dirx.value()}, {self._diry.value()}, {self._dirz.value()}",
                    "direction2": f"{self._dir2x.value()}, {self._dir2y.value()}, {self._dir2z.value()}",
                    "count": self._count.value(), "count2": self._count2.value(),
                    "spacing": self._spacing.value()}
        return {"pattern_type": PatternType.CIRCULAR.value,
                "axis": f"{self._axx.value()}, {self._axy.value()}, {self._axz.value()}",
                "center": f"{self._cx.value()}, {self._cy.value()}, {self._cz.value()}",
                "count": self._count.value(), "angle": self._angle.value()}

    def _validate(self) -> List[str]:
        errors = []
        if self._target is None:
            errors.append("Debe seleccionar un cuerpo.")
        if hasattr(self, "_count") and self._count.value() < 2:
            errors.append("La cantidad del patrón debe ser al menos 2.")
        return errors

    def _on_accept(self) -> None:
        errors = self._validate()
        if errors:
            self._set_error(" ".join(errors))
            return
        cmd = PatternCommand()
        for k, v in self._param_dict().items():
            cmd.set_parameter(k, v)
        cmd.set_target(self._target)
        self.command = cmd
        self.accept()
