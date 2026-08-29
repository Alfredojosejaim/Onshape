"""DesignTreePanel - the engineering model/manufacturing navigation tree
(similar to a CAD feature tree), filled dynamically from the project state.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QCheckBox, QPushButton, QHBoxLayout, QGroupBox,
)
from PySide6.QtCore import Qt, Signal


class DesignTreePanel(QWidget):
    entitiesChanged = Signal()   # emitted when show-mesh / show-solids toggles

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        title = QLabel("Navegador de Diseño")
        title.setStyleSheet("font-weight: 600; color: #f2f2f3;")
        root.addWidget(title)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        root.addWidget(self._tree, 1)

        # visibility group
        vis = QGroupBox("Visualización")
        vlay = QVBoxLayout(vis)

        self._cb_solids = QCheckBox("Superficie (CAD)")
        self._cb_solids.setChecked(True)
        self._cb_solids.setEnabled(False)
        self._cb_solids.stateChanged.connect(lambda _: self.entitiesChanged.emit())

        self._cb_mesh = QCheckBox("Malla FEM")
        self._cb_mesh.setEnabled(False)

        self._cb_density = QCheckBox("Densidad (resultado)")
        self._cb_density.setEnabled(False)

        for cb in (self._cb_solids, self._cb_mesh, self._cb_density):
            vlay.addWidget(cb)

        h = QHBoxLayout()
        self._btn_clear = QPushButton("Limpiar selección")
        self._btn_clear.setEnabled(False)
        h.addWidget(self._btn_clear)
        vlay.addLayout(h)
        root.addWidget(vis)

        self._model_item: QTreeWidgetItem | None = None
        self._mesh_item: QTreeWidgetItem | None = None
        self._result_item: QTreeWidgetItem | None = None

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #
    def set_context(self, model_name: str | None, has_mesh: bool, has_result: bool) -> None:
        self._tree.clear()
        self._model_item = self._mesh_item = self._result_item = None

        if model_name:
            self._model_item = QTreeWidgetItem([model_name])
            self._model_item.setData(0, Qt.UserRole, "model")
            icon = "🗂"
            self._tree.addTopLevelItem(self._model_item)
            self._model_item.addChildren([
                QTreeWidgetItem([f"Archivo: {model_name}"]),
                QTreeWidgetItem(["Malla importada (STEP/CadQuery)"]),
            ])
            self._cb_solids.setEnabled(True)
            self._cb_solids.setChecked(True)
        else:
            placeholder = QTreeWidgetItem(["Sin modelo cargado"])
            self._tree.addTopLevelItem(placeholder)
            self._cb_solids.setEnabled(False)

        if model_name:
            self._mesh_item = QTreeWidgetItem(["Caso de Estudio"])
            self._model_item.addChild(self._mesh_item)

        self._cb_mesh.setEnabled(has_mesh)
        self._cb_mesh.setChecked(has_mesh)

        if has_result:
            self._result_item = QTreeWidgetItem(["Optimización — Resultado"])
            self._model_item.addChild(self._result_item)
        self._cb_density.setEnabled(has_result)
        self._cb_density.setChecked(has_result)
        self._tree.expandAll()

    # ------------------------------------------------------------------ #
    # Getters used by the main window
    # ------------------------------------------------------------------ #
    def show_solids(self) -> bool:
        return self._cb_solids.isChecked()

    def show_mesh(self) -> bool:
        return self._cb_mesh.isChecked()

    def show_density(self) -> bool:
        return self._cb_density.isChecked()

    def set_selection_clearable(self, enabled: bool) -> None:
        self._btn_clear.setEnabled(enabled)

    def clear_button(self):
        return self._btn_clear
