"""DesignTreePanel - the "Navegador de Diseño" tree, styled like the HTML
sidebar. It reflects the active model / mesh / optimization result and keeps
the selection-clear affordance used by the main window.

Architecture integration (Phase 1):
    The tree now follows the Section 13 specification:

        Modelo
        ├── Cuerpos
        ├── Operaciones (Feature History)
        ├── Estudios
        └── Resultados

    New methods ``set_features``, ``set_studies``,
    ``set_bodies`` are added.  The existing ``set_context`` API is
    preserved for backward compatibility.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from desktop.ui.panels.condition_groups import (
    condition_color_hex,
    condition_label,
    group_conditions_by_part,
)


def _labeled_item(obj) -> str:
    """Etiqueta ``nombre [tipo] (estado)`` para Feature/Study (obj o dict)."""
    if isinstance(obj, dict):
        name = obj.get("name", "?")
        ftype = obj.get("feature_type", obj.get("study_type", "?"))
        ftype = getattr(ftype, "value", ftype)
        status = obj.get("status")
    else:
        name = getattr(obj, "name", "?")
        ftype = getattr(obj, "feature_type", getattr(obj, "study_type", "?"))
        ftype = getattr(ftype, "value", ftype)
        status = getattr(obj, "status", None)
    label = f"{name}  [{ftype}]"
    if status is not None:
        label += f"  ({getattr(status, 'value', status)})"
    return label


class DesignTreePanel(QWidget):

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
        self._bodies_item: QTreeWidgetItem | None = None
        self._features_item: QTreeWidgetItem | None = None
        self._conditions_item: QTreeWidgetItem | None = None
        self._studies_item: QTreeWidgetItem | None = None
        self._results_item: QTreeWidgetItem | None = None
        self._mesh_item: QTreeWidgetItem | None = None

    # ------------------------------------------------------------------ #
    # State (backward compatible)
    # ------------------------------------------------------------------ #
    def set_context(self, model_name: str | None, has_mesh: bool, has_result: bool) -> None:
        self._tree.clear()
        self._model_item = None
        self._bodies_item = None
        self._features_item = None
        self._conditions_item = None
        self._studies_item = None
        self._results_item = None
        self._mesh_item = None

        if model_name:
            model = QTreeWidgetItem([model_name.upper() if len(model_name) else model_name])
            model.setData(0, Qt.UserRole, "model")
            model.setIcon(0, self._empty_icon())
            self._tree.addTopLevelItem(model)
            self._model_item = model

            # Bodies node
            bodies = QTreeWidgetItem(["Cuerpos"])
            bodies.setData(0, Qt.UserRole, "bodies")
            model.addChild(bodies)
            self._bodies_item = bodies
            bodies.addChild(QTreeWidgetItem(["Geometría CAD (STEP)"]))

            # Features node (empty until features are set)
            features = QTreeWidgetItem(["Operaciones"])
            features.setData(0, Qt.UserRole, "features")
            model.addChild(features)
            self._features_item = features

            # Conditions node (empty until conditions are set)
            conditions = QTreeWidgetItem(["Condiciones"])
            conditions.setData(0, Qt.UserRole, "conditions")
            model.addChild(conditions)
            self._conditions_item = conditions

            # Mesh node
            if has_mesh:
                mesh = QTreeWidgetItem(["Malla FEM"])
                mesh.setData(0, Qt.UserRole, "mesh")
                model.addChild(mesh)
                self._mesh_item = mesh

            # Studies node (empty until studies are set)
            studies = QTreeWidgetItem(["Estudios"])
            studies.setData(0, Qt.UserRole, "studies")
            model.addChild(studies)
            self._studies_item = studies

            # Results node
            results = QTreeWidgetItem(["Resultados"])
            results.setData(0, Qt.UserRole, "results")
            model.addChild(results)
            self._results_item = results
            if has_result:
                results.addChild(QTreeWidgetItem(["Optimización — Resultado"]))
        else:
            placeholder = QTreeWidgetItem(["Modelo sin importar"])
            self._tree.addTopLevelItem(placeholder)

        self._tree.expandAll()

    @staticmethod
    def _empty_icon():
        from desktop.ui.style import ACCENT
        from PySide6.QtGui import QIcon, QPixmap, QColor

        pm = QPixmap(10, 10)
        pm.fill(QColor(ACCENT))
        return QIcon(pm)

    # ------------------------------------------------------------------ #
    # Getters (API kept for compatibility)
    # ------------------------------------------------------------------ #
    def set_selection_clearable(self, enabled: bool) -> None:
        self._btn_clear.setEnabled(enabled)

    def clear_button(self):
        return self._btn_clear

    # ------------------------------------------------------------------ #
    # Bodies display (architecture layer)
    # ------------------------------------------------------------------ #
    def set_bodies(self, bodies: list) -> None:
        """Display CAD bodies/solids in the tree.

        ``bodies`` is a list of dicts with at least ``name`` and
        optionally ``volume``, ``faces_count``.
        """
        if self._bodies_item is None:
            return
        # Remove old body children (keep the header)
        while self._bodies_item.childCount() > 0:
            self._bodies_item.removeChild(self._bodies_item.child(0))
        if not bodies:
            self._bodies_item.addChild(QTreeWidgetItem(["Geometría CAD (STEP)"]))
            return
        for body in bodies:
            name = body.get("name", "Cuerpo")
            vol = body.get("volume")
            label = name
            if vol is not None:
                label = f"{name}  (V={vol:.1f})"
            child = QTreeWidgetItem([label])
            child.setData(0, Qt.UserRole, "body")
            self._bodies_item.addChild(child)
        self._tree.expandAll()

    # ------------------------------------------------------------------ #
    # Feature history display (architecture layer)
    # ------------------------------------------------------------------ #
    def set_features(self, features: list) -> None:
        """Display the feature history under the Operaciones node.

        ``features`` is a list of Feature objects (or dicts) from
        ``core.features.FeatureHistory``.
        """
        if self._features_item is None:
            return
        # Clear old children
        while self._features_item.childCount() > 0:
            self._features_item.removeChild(self._features_item.child(0))
        if not features:
            self._features_item.addChild(QTreeWidgetItem(["(vacío)"]))
            self._tree.expandAll()
            return
        for feat in features:
            child = QTreeWidgetItem([_labeled_item(feat)])
            child.setData(0, Qt.UserRole, "feature")
            self._features_item.addChild(child)
        self._tree.expandAll()

    # ------------------------------------------------------------------ #
    # Conditions display (architecture layer)
    # ------------------------------------------------------------------ #
    def set_conditions(self, conditions: list, part_resolver=None, ref_resolver=None) -> None:
        """Display reusable conditions under the Condiciones node.

        grouped by part (``Condiciones — <pieza>``) with a value badge per
        instance. ``ref_resolver`` maps a full CadEntityRef to a part label
        (preferred, covers solids); ``part_resolver`` maps
        ``(face_index, model_id)`` for faces. Backward compatible: both
        optional; without resolvers the previous flat behaviour degrades
        to model/general groups.
        """
        if self._conditions_item is None:
            return
        while self._conditions_item.childCount() > 0:
            self._conditions_item.removeChild(self._conditions_item.child(0))
        if not conditions:
            self._conditions_item.addChild(QTreeWidgetItem(["(vacío)"]))
            self._tree.expandAll()
            return
        for part_label, conds in group_conditions_by_part(
                conditions, ref_resolver=ref_resolver,
                part_resolver=part_resolver):
            part_item = QTreeWidgetItem([f"Condiciones — {part_label}"])
            part_item.setData(0, Qt.UserRole, "condition_group")
            self._conditions_item.addChild(part_item)
            for cond in conds:
                child = QTreeWidgetItem([condition_label(cond)])
                child.setData(0, Qt.UserRole, "condition")
                color = condition_color_hex(cond)
                if color:
                    child.setForeground(0, QColor(color))
                part_item.addChild(child)
        self._tree.expandAll()

    # ------------------------------------------------------------------ #
    # Studies display (architecture layer)
    # ------------------------------------------------------------------ #
    def set_studies(self, studies: list) -> None:
        """Display the study list under the Estudios node.

        ``studies`` is a list of Study objects (or dicts) from
        ``core.cae_studies`` / ``core.optimization_studies``.
        """
        if self._studies_item is None:
            return
        while self._studies_item.childCount() > 0:
            self._studies_item.removeChild(self._studies_item.child(0))
        if not studies:
            self._studies_item.addChild(QTreeWidgetItem(["(vacío)"]))
            self._tree.expandAll()
            return
        for stud in studies:
            child = QTreeWidgetItem([_labeled_item(stud)])
            child.setData(0, Qt.UserRole, "study")
            self._studies_item.addChild(child)
        self._tree.expandAll()
