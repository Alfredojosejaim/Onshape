"""DesignTreePanel - the "Navegador de Diseño" tree, styled like the HTML
sidebar. It reflects the active model / mesh / optimization result and keeps
the selection-clear affordance used by the main window.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt, Signal


class DesignTreePanel(QWidget):
    entitiesChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        header = QLabel("Navegador de Diseño")
        header.setStyleSheet("font-size: 13px; font-weight: 600;")
        root.addWidget(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(14)
        root.addWidget(self._tree, 1)

        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        self._btn_clear = QPushButton("Limpiar selección")
        self._btn_clear.setEnabled(False)
        h.addWidget(self._btn_clear)
        h.addStretch(1)
        root.addLayout(h)

        self._model_item: QTreeWidgetItem | None = None

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #
    def set_context(self, model_name: str | None, has_mesh: bool, has_result: bool) -> None:
        self._tree.clear()
        self._model_item = None

        if model_name:
            model = QTreeWidgetItem([model_name.upper() if len(model_name) else model_name])
            model.setData(0, Qt.UserRole, "model")
            model.setIcon(0, self._empty_icon())
            self._tree.addTopLevelItem(model)
            self._model_item = model
            model.addChild(QTreeWidgetItem(["Archivo: " + model_name]))
            model.addChild(QTreeWidgetItem(["Geometría CAD (STEP)"]))

            if has_mesh:
                mesh = QTreeWidgetItem(["Malla FEM"])
                model.addChild(mesh)
            if has_result:
                model.addChild(QTreeWidgetItem(["Optimización — Resultado"]))
        else:
            placeholder = QTreeWidgetItem(["Modelo sin importar"])
            self._tree.addTopLevelItem(placeholder)

        self._tree.expandAll()

    @staticmethod
    def _empty_icon():
        from PySide6.QtGui import QIcon, QPixmap, QColor

        pm = QPixmap(10, 10)
        pm.fill(QColor("#2f7bf6"))
        return QIcon(pm)

    # ------------------------------------------------------------------ #
    # Getters (API kept for compatibility)
    # ------------------------------------------------------------------ #
    def show_solids(self) -> bool:
        return True

    def show_mesh(self) -> bool:
        return True

    def show_density(self) -> bool:
        return True

    def set_selection_clearable(self, enabled: bool) -> None:
        self._btn_clear.setEnabled(enabled)

    def clear_button(self):
        return self._btn_clear