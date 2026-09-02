"""StudyPanel - a functional Qt dialog to create and run engineering studies.

The dialog lets the user close the end-to-end CAD/CAE flow without any
redesign of the existing desktop:

    name / type        (topology optimization only for now)
    objective part     (compulsory CAD part/piece to optimise)
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
    QDialogButtonBox,
)
from PySide6.QtCore import Qt

from core.conditions import Condition, ConditionManager
from core.optimization_studies import TopologyOptimizationStudy


class StudyPanel(QDialog):
    """Modal dialog that produces a configured TopologyOptimizationStudy."""

    def __init__(
        self,
        parent=None,
        condition_manager: Optional[ConditionManager] = None,
        condition_ids: Optional[List[str]] = None,
        available_conditions: Optional[List[Any]] = None,
        default_name: str = "",
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
        form.addRow("Tipo:", self._type)

        self._objective = QLineEdit("Pieza objetivo del modelo (sólido 1)")
        self._objective.setPlaceholderText("Se usa el primer sólido del modelo")
        form.addRow("Pieza objetivo:", self._objective)

        self._volfrac = QDoubleSpinBox()
        self._volfrac.setRange(0.01, 1.0)
        self._volfrac.setDecimals(2)
        self._volfrac.setSingleStep(0.05)
        self._volfrac.setValue(0.3)
        form.addRow("Fracción de volumen:", self._volfrac)

        self._max_iter = QSpinBox()
        self._max_iter.setRange(1, 500)
        self._max_iter.setValue(50)
        form.addRow("Iteraciones máx.:", self._max_iter)

        self._penal = QDoubleSpinBox()
        self._penal.setRange(1.0, 6.0)
        self._penal.setDecimals(1)
        self._penal.setValue(3.0)
        self._penal.setToolTip("Penalización SIMP")
        form.addRow("Penalización:", self._penal)

        self._radius = QDoubleSpinBox()
        self._radius.setRange(0.5, 10.0)
        self._radius.setDecimals(1)
        self._radius.setValue(1.5)
        form.addRow("Radio de filtro:", self._radius)

        self._tol = QDoubleSpinBox()
        self._tol.setDecimals(4)
        self._tol.setRange(1e-6, 1.0)
        self._tol.setSingleStep(0.0005)
        self._tol.setValue(1e-3)
        form.addRow("Tolerancia:", self._tol)
        root.addLayout(form)

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
        self._error.setStyleSheet("color: #e06c6c;")
        self._error.setWordWrap(True)
        root.addWidget(self._error)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _on_accept(self) -> None:
        chosen = [self._available[i] for i in range(self._cond_list.count())
                  if self._cond_list.item(i).isSelected()]
        try:
            study = TopologyOptimizationStudy(name=self._name.text().strip() or "Estudio")
            study.optimization_params.volume_fraction = float(self._volfrac.value())
            study.optimization_params.max_iterations = int(self._max_iter.value())
            study.optimization_params.penalization = float(self._penal.value())
            study.optimization_params.filter_radius = float(self._radius.value())
            study.optimization_params.convergence_tolerance = float(self._tol.value())
            for cond in chosen:
                study.add_condition(cond.id)
            if not study.conditions:
                self._error.setText("Seleccione al menos una condición (carga, soporte u obstrucción).")
                return
            self.study = study
            self.accept()
        except Exception as exc:  # pragma: no cover
            self._error.setText(f"No se pudo crear el estudio: {exc}")
