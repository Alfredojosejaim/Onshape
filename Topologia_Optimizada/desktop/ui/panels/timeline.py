"""TimelinePanel - native "Progreso del estudio" playhead widget:
five numbered step pills, a convergence chip, a scrub track and playback
buttons (Reiniciar / ▶ / Ejecutar). The play actions are forwarded to the
main window through signals.

Architecture integration (Phase 1):
    The timeline now supports two modes:

    1. Pipeline mode (default): the fixed 5-step optimization pipeline.
       Controlled via ``set_pipeline_step()`` — backward compatible.

    2. Feature mode: the step pills dynamically reflect the feature history
       from the Document model.  Controlled via ``set_features()``.
       When features are set, the timeline title changes to "Historial de
       Operaciones" and each feature becomes a step pill.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar,
)
from PySide6.QtCore import Qt, Signal

DEFAULT_STEPS = [
    "Importar STEP",
    "Cargas y Restricciones",
    "Generar Malla",
    "Optimizar SIMP",
    "Resultado",
]


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class TimelinePanel(QWidget):
    playRequested = Signal()     # next step of the guided flow
    resetRequested = Signal()    # rewind the playhead

    def __init__(self, steps: list[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._steps = list(steps or DEFAULT_STEPS)
        self._step_widgets: list[QPushButton] = []
        self._feature_mode = False
        self._branch_mode = False

        frame = QFrame()
        frame.setObjectName("timelinePanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(frame)

        col = QVBoxLayout(frame)
        col.setContentsMargins(16, 12, 16, 14)
        col.setSpacing(12)

        # ---- Header ---- (title + convergence chip)
        header = QHBoxLayout()
        self._title = QLabel("Progreso del estudio")
        self._title.setStyleSheet("font-size: 13px; font-weight: 600;")
        header.addWidget(self._title)
        header.addStretch(1)
        self._chip = QLabel("✔ Convergido")
        self._chip.setProperty("chipok", True)
        self._chip.hide()
        header.addWidget(self._chip)
        self._chip_iter = QLabel("")
        self._chip_iter.setProperty("faint", True)
        self._chip_iter.setStyleSheet("font-size: 11px;")
        header.addWidget(self._chip_iter)
        col.addLayout(header)

        # ---- Step pills ----
        self._steps_layout = QHBoxLayout()
        self._steps_layout.setSpacing(10)
        col.addLayout(self._steps_layout)
        self._build_step_pills(self._steps)

        # ---- Scrub track ----
        self._scrub = QProgressBar()
        self._scrub.setRange(0, len(self._steps))
        self._scrub.setValue(0)
        self._scrub.setTextVisible(False)
        self._scrub.setFixedHeight(4)
        col.addWidget(self._scrub)

        # ---- Playback ----
        play = QHBoxLayout()
        play.setSpacing(14)
        self._btn_prev = QPushButton("⏮ Reiniciar")
        self._btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_prev.clicked.connect(self.resetRequested.emit)

        self._btn_play = QPushButton("▶")
        self._btn_play.setProperty("play", True)
        self._btn_play.setFixedSize(34, 34)
        self._btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_play.setToolTip("Continuar con el siguiente paso del flujo")
        self._btn_play.clicked.connect(self.playRequested.emit)

        self._btn_next = QPushButton("Ejecutar ▶")
        self._btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_next.clicked.connect(self.playRequested.emit)

        play.addWidget(self._btn_prev)
        play.addStretch(1)
        play.addWidget(self._btn_play)
        play.addStretch(1)
        play.addWidget(self._btn_next)
        col.addLayout(play)

        self.set_pipeline_step(0)

    # ------------------------------------------------------------------ #
    # Step pill builder
    # ------------------------------------------------------------------ #
    def _clear_steps_area(self) -> None:
        """Vacía el área de pills (pills, columnas y stretches residuales)."""
        self._step_widgets.clear()
        while self._steps_layout.count():
            item = self._steps_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
                continue
            layout = item.layout()
            if layout is not None:
                # Columnas del modo ramificado: soltar sus pills hijas.
                while layout.count():
                    sub = layout.takeAt(0)
                    sub_w = sub.widget()
                    if sub_w is not None:
                        sub_w.setParent(None)
                        sub_w.deleteLater()
        self._step_widgets.clear()

    def _build_step_pills(self, labels: list[str]) -> None:
        """Remove old pills and create new ones for the given labels."""
        self._clear_steps_area()
        for i, label in enumerate(labels, start=1):
            pill = QPushButton(f"{i}  {label}")
            pill.setProperty("pill", True)
            pill.setCursor(Qt.CursorShape.PointingHandCursor)
            self._step_widgets.append(pill)
            self._steps_layout.addWidget(pill)
        self._steps_layout.addStretch(1)

    # ------------------------------------------------------------------ #
    # Pipeline mode (backward compatible)
    # ------------------------------------------------------------------ #
    def set_pipeline_step(self, index: int) -> None:
        """Mark steps [0..index] as active/completed (0 = nothing done yet)."""
        self._exit_branch_mode()
        for k, pill in enumerate(self._step_widgets, start=1):
            pill.setProperty("active", k <= index)
            pill.setProperty("done", k < index)
            _repolish(pill)
        self._scrub.setValue(index)
        if index >= len(self._steps):
            self._chip.show()
        else:
            self._chip.hide()

    def set_iteration(self, iteration: int, volume_fraction: float) -> None:
        self._chip_iter.setText(f"Iter {iteration} · V={volume_fraction:.0%}")

    def reset(self) -> None:
        if self._feature_mode:
            self._feature_mode = False
            self._title.setText("Progreso del estudio")
            self._build_step_pills(self._steps)
            self._scrub.setRange(0, len(self._steps))
        self._exit_branch_mode()
        self.set_pipeline_step(0)
        self._chip_iter.setText("")

    # ------------------------------------------------------------------ #
    # Feature mode (architecture layer)
    # ------------------------------------------------------------------ #
    def set_features(self, features: list) -> None:
        """Switch to feature mode and display the feature history as step pills.

        ``features`` is a list of Feature objects (or dicts) from
        ``core.features.FeatureHistory``.  Each feature becomes a step pill.
        The status of each feature determines its visual state.
        """
        self._exit_branch_mode()
        self._feature_mode = True
        self._title.setText("Historial de Operaciones")

        if not features:
            self._build_step_pills(["(sin operaciones)"])
            self._scrub.setRange(0, 0)
            self._scrub.setValue(0)
            return

        labels = []
        completed_count = 0
        for feat in features:
            name = getattr(feat, "name", None) or (feat.get("name", "?") if isinstance(feat, dict) else "?")
            ftype = getattr(feat, "feature_type", None)
            status = getattr(feat, "status", None) if hasattr(feat, "status") else None
            if ftype is not None:
                label = f"{name}  [{ftype.value if hasattr(ftype, 'value') else ftype}]"
            else:
                ftype_val = feat.get("feature_type", "?") if isinstance(feat, dict) else "?"
                label = f"{name}  [{ftype_val}]"
            labels.append(label)
            # Count completed/executed features
            if status is not None:
                status_val = status.value if hasattr(status, "value") else str(status)
                if status_val == "executed":
                    completed_count += 1

        self._build_step_pills(labels)
        self._scrub.setRange(0, len(labels))
        self._scrub.setValue(completed_count)

        # Mark pills by status
        for k, pill in enumerate(self._step_widgets):
            if k < completed_count:
                pill.setProperty("active", True)
                pill.setProperty("done", True)
            elif k == completed_count:
                pill.setProperty("active", True)
                pill.setProperty("done", False)
            else:
                pill.setProperty("active", False)
                pill.setProperty("done", False)
            _repolish(pill)

    def is_feature_mode(self) -> bool:
        return self._feature_mode

    # ------------------------------------------------------------------ #
    # Branch mode: one column per part, converging on a shared node
    # ------------------------------------------------------------------ #
    def set_branch_view(self, part_groups: list, converge_label: str = "Optimizar") -> None:
        """Dibuja una columna por pieza con sus condiciones propias.

        ``part_groups`` es ``[(etiqueta_pieza, [etiquetas_condición]), ...]``
        y converge en un nodo compartido (``converge_label``). Sin grupos,
        vuelve al modo pipeline. Los modos pipeline/feature salen de este
        modo automáticamente (ver ``_exit_branch_mode``).
        """
        if not part_groups:
            self._exit_branch_mode()
            return
        self._branch_mode = True
        self._feature_mode = False
        self._title.setText("Flujo por pieza")
        self._clear_steps_area()
        total = 0
        for part_label, labels in part_groups:
            col = QVBoxLayout()
            col.setSpacing(6)
            header = QPushButton(str(part_label))
            header.setProperty("pill", True)
            header.setProperty("active", True)
            header.setCursor(Qt.CursorShape.PointingHandCursor)
            _repolish(header)
            col.addWidget(header)
            for lab in labels or []:
                pill = QPushButton(str(lab))
                pill.setProperty("pill", True)
                pill.setProperty("active", True)
                pill.setCursor(Qt.CursorShape.PointingHandCursor)
                _repolish(pill)
                col.addWidget(pill)
                total += 1
            col.addStretch(1)
            wrap = QWidget()
            wrap.setLayout(col)
            self._steps_layout.addWidget(wrap)
        conv_col = QVBoxLayout()
        conv_col.setSpacing(6)
        conv_col.addStretch(1)
        conv = QPushButton(f"⚙  {converge_label}")
        conv.setProperty("pill", True)
        conv.setProperty("active", True)
        conv.setCursor(Qt.CursorShape.PointingHandCursor)
        _repolish(conv)
        conv_col.addWidget(conv)
        conv_col.addStretch(1)
        conv_wrap = QWidget()
        conv_wrap.setLayout(conv_col)
        self._steps_layout.addWidget(conv_wrap)
        self._steps_layout.addStretch(1)
        self._scrub.setRange(0, max(total, 1))
        self._scrub.setValue(total)
        self._chip.hide()

    def is_branch_mode(self) -> bool:
        return self._branch_mode

    def _exit_branch_mode(self) -> None:
        """Vuelve al modo pipeline si el ramificado estaba activo."""
        if not self._branch_mode:
            return
        self._branch_mode = False
        self._title.setText("Progreso del estudio")
        self._build_step_pills(self._steps)
        self._scrub.setRange(0, len(self._steps))
