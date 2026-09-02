"""MirrorPanel - a functional Qt dialog for CAD mirror (symmetry) operations.

The panel configures a mirror across a plane without owning any geometric
logic:

    Cuerpo                    [Capturar desde selección]
    Punto del plano (x, y, z)
    Normal del plano (x, y, z)
    [x] Conservar original
        [Aceptar]  [Cancelar]

It reuses the existing ``SelectionManager`` via ``get_solid_selections``,
builds a ``core.commands.MirrorCommand`` and hands it back to the caller,
which executes it through the pipeline.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QDoubleSpinBox, QCheckBox, QDialogButtonBox, QWidget,
)

from core.cad_entity import CadEntityRef, EntityType
from core.commands import MirrorCommand


def _display(ref: Optional[CadEntityRef]) -> str:
    if ref is None:
        return "(ninguno)"
    return ref.display_name


class MirrorPanel(QDialog):
    """Modal dialog that configures and produces a MirrorCommand."""

    def __init__(self, parent=None, get_solid_selections: Optional[Callable[[], List[CadEntityRef]]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Simetría (espejo)")
        self.setMinimumWidth(420)
        self._get_solid_selections = get_solid_selections
        self._target: Optional[CadEntityRef] = None
        self.command: Optional[MirrorCommand] = None
        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
        self._target_label = QLabel(_display(None))
        btn_target = QPushButton("Capturar desde selección")
        btn_target.clicked.connect(self._capture_target)
        tl = QHBoxLayout()
        tl.addWidget(self._target_label, 1)
        tl.addWidget(btn_target)
        form.addRow("Cuerpo:", self._wrap(tl))
        root.addLayout(form)

        param_form = QFormLayout()
        self._px = QDoubleSpinBox(); self._px.setRange(-1e6, 1e6); self._px.setValue(0.0)
        self._py = QDoubleSpinBox(); self._py.setRange(-1e6, 1e6); self._py.setValue(0.0)
        self._pz = QDoubleSpinBox(); self._pz.setRange(-1e6, 1e6); self._pz.setValue(0.0)
        prow = QHBoxLayout()
        prow.addWidget(self._px); prow.addWidget(self._py); prow.addWidget(self._pz)
        param_form.addRow("Punto del plano (x, y, z):", self._wrap(prow))

        self._nx = QDoubleSpinBox(); self._nx.setRange(-1e6, 1e6); self._nx.setValue(0.0)
        self._ny = QDoubleSpinBox(); self._ny.setRange(-1e6, 1e6); self._ny.setValue(1.0)
        self._nz = QDoubleSpinBox(); self._nz.setRange(-1e6, 1e6); self._nz.setValue(0.0)
        nrow = QHBoxLayout()
        nrow.addWidget(self._nx); nrow.addWidget(self._ny); nrow.addWidget(self._nz)
        param_form.addRow("Normal del plano (x, y, z):", self._wrap(nrow))
        root.addLayout(param_form)

        self._keep_original = QCheckBox("Conservar original")
        self._keep_original.setChecked(True)
        root.addWidget(self._keep_original)

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

    def _normal(self) -> List[float]:
        return [self._nx.value(), self._ny.value(), self._nz.value()]

    def _plane_point(self) -> List[float]:
        return [self._px.value(), self._py.value(), self._pz.value()]

    def _validate(self) -> List[str]:
        errors = []
        if self._target is None:
            errors.append("Debe seleccionar un cuerpo.")
        n = self._normal()
        if n == [0.0, 0.0, 0.0]:
            errors.append("La normal del plano no puede ser cero.")
        return errors

    def _on_accept(self) -> None:
        errors = self._validate()
        if errors:
            self._set_error(" ".join(errors))
            return
        cmd = MirrorCommand()
        cmd.set_parameter("plane_point", ", ".join(str(v) for v in self._plane_point()))
        cmd.set_parameter("plane_normal", ", ".join(str(v) for v in self._normal()))
        cmd.set_parameter("keep_original", self._keep_original.isChecked())
        cmd.set_target(self._target)
        self.command = cmd
        self.accept()
