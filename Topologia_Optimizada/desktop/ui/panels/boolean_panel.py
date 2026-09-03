"""BooleanPanel - a functional Qt dialog for CAD boolean operations.

The panel configures a boolean operation without owning any geometric logic:

    Tipo de operación   (Unión / Corte / Intersección)
    Cuerpo objetivo      [Capturar desde selección]
    Cuerpos herramienta  [Capturar desde selección]
    [x] Conservar herramientas
        [Aceptar]  [Cancelar]

The dialog reuses the existing ``SelectionManager`` from the viewport: the
user picks bodies in the 3D view (the existing multi-entity selection) and
then captures them here as the target / tools.  It builds a
``core.commands.BooleanCommand`` and hands it back to the caller, which is
responsible for executing it through the pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QCheckBox, QDialogButtonBox,
)
from PySide6.QtCore import Qt

from desktop.ui.style import ERROR
from core.cad_entity import CadEntityRef, EntityType
from core.commands import BooleanCommand, BooleanOperation


def _display(ref: Optional[CadEntityRef]) -> str:
    if ref is None:
        return "(ninguno)"
    return ref.display_name


class BooleanPanel(QDialog):
    """Modal dialog that configures and produces a BooleanCommand."""

    def __init__(self, parent=None, operation: str = "union",
                 get_solid_selections=None) -> None:
        """``get_solid_selections`` is an optional callable returning the list
        of ``CadEntityRef`` (solids) currently selected in the viewport.  It
        lets the dialog reuse the existing SelectionManager without owning it.
        """
        super().__init__(parent)
        self.setWindowTitle("Operación Booleana")
        self.setMinimumWidth(380)
        self._get_solid_selections = get_solid_selections
        self._target: Optional[CadEntityRef] = None
        self._tools: List[CadEntityRef] = []
        self.command: Optional[BooleanCommand] = None

        self._build_ui()
        self._set_operation(operation)

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # Operation type ------------------------------------------------- #
        op_label = QLabel("Tipo de operación:")
        root.addWidget(op_label)
        self._op_group = QButtonGroup(self)
        op_row = QHBoxLayout()
        self._rb_union = QRadioButton("Unión")
        self._rb_cut = QRadioButton("Corte")
        self._rb_intersect = QRadioButton("Intersección")
        for rb in (self._rb_union, self._rb_cut, self._rb_intersect):
            self._op_group.addButton(rb)
            op_row.addWidget(rb)
        root.addLayout(op_row)

        # Target / tools ------------------------------------------------ #
        form = QFormLayout()
        self._target_label = QLabel(_display(None))
        btn_target = QPushButton("Capturar desde selección")
        btn_target.clicked.connect(self._capture_target)
        tl = QHBoxLayout()
        tl.addWidget(self._target_label, 1)
        tl.addWidget(btn_target)
        form.addRow("Cuerpo objetivo:", self._wrap(tl))

        self._tools_label = QLabel(_display(None))
        btn_tools = QPushButton("Capturar desde selección")
        btn_tools.clicked.connect(self._capture_tools)
        tll = QHBoxLayout()
        tll.addWidget(self._tools_label, 1)
        tll.addWidget(btn_tools)
        form.addRow("Cuerpos herramienta:", self._wrap(tll))
        root.addLayout(form)

        self._keep_tools = QCheckBox("Conservar herramientas")
        root.addWidget(self._keep_tools)

        # Buttons ---------------------------------------------------------
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

    def _wrap(self, layout) -> QLabel:
        # QFormLayout rows need a widget; wrap a layout in a QLabel container
        # by using an empty QWidget.  Return a QWidget for clarity.
        from PySide6.QtWidgets import QWidget
        w = QWidget()
        w.setLayout(layout)
        return w

    # ------------------------------------------------------------------ #
    # Getters / helpers
    # ------------------------------------------------------------------ #
    def _set_operation(self, operation: str) -> None:
        if operation == BooleanOperation.DIFFERENCE.value:
            self._rb_cut.setChecked(True)
        elif operation == BooleanOperation.INTERSECTION.value:
            self._rb_intersect.setChecked(True)
        else:
            self._rb_union.setChecked(True)

    def selected_operation(self) -> str:
        if self._rb_cut.isChecked():
            return BooleanOperation.DIFFERENCE.value
        if self._rb_intersect.isChecked():
            return BooleanOperation.INTERSECTION.value
        return BooleanOperation.UNION.value

    def keep_tools_enabled(self) -> bool:
        return self._keep_tools.isChecked()

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
        # The target is the first selected solid.
        self._set_target(solids[0])
        # Remaining solids go to the tools (if any).
        self._set_tools(solids[1:])
        self._refresh_labels()

    def _capture_tools(self) -> None:
        solids = self._solid_selections()
        if not solids:
            self._set_error("No hay cuerpos seleccionados en el viewport.")
            return
        self._set_tools(solids)
        self._refresh_labels()

    def _set_target(self, ref: CadEntityRef) -> None:
        self._target = ref
        if ref in self._tools:
            self._tools.remove(ref)

    def _set_tools(self, refs: List[CadEntityRef]) -> None:
        # A tool cannot be the target; drop it.
        self._tools = [r for r in refs if r != self._target]

    def _refresh_labels(self) -> None:
        self._target_label.setText(_display(self._target))
        if self._tools:
            names = ", ".join(_display(t) for t in self._tools)
            self._tools_label.setText(names)
        else:
            self._tools_label.setText(_display(None))
        self._error_label.setText("")

    def _set_error(self, msg: str) -> None:
        self._error_label.setText(msg)

    # ------------------------------------------------------------------ #
    # Validation + accept
    # ------------------------------------------------------------------ #
    def _validate(self) -> List[str]:
        errors = []
        if self._target is None:
            errors.append("Debe seleccionar un cuerpo objetivo.")
        if not self._tools:
            errors.append("Debe seleccionar al menos un cuerpo herramienta.")
        return errors

    def _on_accept(self) -> None:
        errors = self._validate()
        if errors:
            self._set_error(" ".join(errors))
            return
        # Build the command via the command pattern; the pipeline performs the
        # actual geometry operation.
        cmd = BooleanCommand()
        cmd.set_parameter("operation", self.selected_operation())
        cmd.set_parameter("keep_tools", self.keep_tools_enabled())
        cmd.set_target(self._target)
        for tool in self._tools:
            cmd.add_tool(tool)
        self.command = cmd
        self.accept()
