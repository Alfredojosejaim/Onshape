"""TimelinePanel - the "Progreso del estudio" playhead from optimization-app.html:
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
    def _build_step_pills(self, labels: list[str]) -> None:
        """Remove old pills and create new ones for the given labels."""
        for pill in self._step_widgets:
            pill.setParent(None)
            pill.deleteLater()
        self._step_widgets.clear()
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
