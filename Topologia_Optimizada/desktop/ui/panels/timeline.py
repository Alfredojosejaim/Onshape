"""TimelinePanel - the "Progreso del estudio" playhead from optimization-app.html:
five numbered step pills, a convergence chip, a scrub track and playback
buttons (Reiniciar / ▶ / Ejecutar). The play actions are forwarded to the
main window through signals.
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
        title = QLabel("Progreso del estudio")
        title.setStyleSheet("font-size: 13px; font-weight: 600;")
        header.addWidget(title)
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
        steps_h = QHBoxLayout()
        steps_h.setSpacing(10)
        for i, label in enumerate(self._steps, start=1):
            pill = QPushButton(f"{i}  {label}")
            pill.setProperty("pill", True)
            pill.setCursor(Qt.CursorShape.PointingHandCursor)
            self._step_widgets.append(pill)
            steps_h.addWidget(pill)
        steps_h.addStretch(1)
        col.addLayout(steps_h)

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
    # Pipeline state
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
        self.set_pipeline_step(0)
        self._chip_iter.setText("")