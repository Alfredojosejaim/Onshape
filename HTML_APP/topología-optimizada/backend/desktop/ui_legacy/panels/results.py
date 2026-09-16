"""ResultsPanel - mesh metrics, FEA/optimization summary and convergence log,
styled with the same HTML section language as the rest of the desktop UI.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QTextEdit,
    QComboBox, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Signal

from desktop.ui_legacy.style import PALETTE


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setProperty("section", True)
    return lbl


def _value_label() -> QLabel:
    lbl = QLabel("—")
    lbl.setProperty("infovalid", True)
    lbl.setStyleSheet("font-size: 12.5px;")
    return lbl


class ResultsPanel(QWidget):
    playAnimation = Signal()
    pauseAnimation = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        header = QLabel("Resultados")
        header.setStyleSheet("font-size: 13px; font-weight: 600;")
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(4, 0, 4, 4)
        col.setSpacing(8)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # ---- Malla ----
        col.addWidget(_section_title("Malla"))
        self._mesh_n = _value_label()
        self._mesh_e = _value_label()
        self._mesh_t = _value_label()
        col.addWidget(QLabel("Nodos"))
        col.addWidget(self._mesh_n)
        col.addWidget(QLabel("Elementos"))
        col.addWidget(self._mesh_e)
        col.addWidget(QLabel("Tipo"))
        col.addWidget(self._mesh_t)

        # ---- Optimización ----
        col.addWidget(_section_title("Optimización"))
        self._status = QLabel("—")
        self._status.setProperty("infovalid", True)
        self._iter = _value_label()
        self._vol = _value_label()
        self._compliance = _value_label()
        self._conv = _value_label()
        col.addWidget(QLabel("Estado"))
        col.addWidget(self._status)
        col.addWidget(QLabel("Iteraciones"))
        col.addWidget(self._iter)
        col.addWidget(QLabel("Volumen final"))
        col.addWidget(self._vol)
        col.addWidget(QLabel("Compliance"))
        col.addWidget(self._compliance)
        col.addWidget(QLabel("Convergencia"))
        col.addWidget(self._conv)

        # ---- Historial ----
        col.addWidget(_section_title("Historial de convergencia"))
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            f"background: {PALETTE['bg_panel2']}; border: 1px solid {PALETTE['border']}; border-radius: 4px;"
            "font-family: Consolas, monospace; font-size: 11px;"
        )
        col.addWidget(self._log)

        # ---- Animación modal (Fase 4.5d.5: solo estudio Modal corrido) ----
        self._anim_section = QWidget()
        anim = QVBoxLayout(self._anim_section)
        anim.setContentsMargins(0, 0, 0, 0)
        anim.setSpacing(6)
        anim.addWidget(_section_title("Animación modal"))
        self._mode_combo = QComboBox()
        self._mode_combo.setToolTip("Modo propio a animar")
        anim.addWidget(self._mode_combo)
        row = QHBoxLayout()
        self._btn_play = QPushButton("▶ Animar")
        self._btn_play.setToolTip(
            "Anima la malla FEA (picking deshabilitado mientras anima).")
        self._btn_play.clicked.connect(self._on_play_pause)
        row.addWidget(self._btn_play)
        self._speed_combo = QComboBox()
        self._speed_combo.addItems(["0.5×", "1×", "2×"])
        self._speed_combo.setCurrentIndex(1)
        self._speed_combo.setToolTip("Velocidad de reproducción")
        row.addWidget(self._speed_combo)
        anim.addLayout(row)
        self._anim_status = QLabel("")
        self._anim_status.setWordWrap(True)
        self._anim_status.setStyleSheet("font-size: 11px;")
        anim.addWidget(self._anim_status)
        col.addWidget(self._anim_section)
        self._anim_section.setVisible(False)
        self._playing = False
        col.addStretch(1)

    # ------------------------------------------------------------------ #
    # Public API (used by MainWindow / controller callbacks)
    # ------------------------------------------------------------------ #
    def set_mesh(self, num_nodes: int, num_elements: int, element_type: str, provisional: bool) -> None:
        self._mesh_n.setText(f"{num_nodes:,}")
        self._mesh_e.setText(f"{num_elements:,}")
        t = element_type.upper()
        if provisional:
            t += " (provisional)"
        self._mesh_t.setText(t)

    def set_result(self, result: dict, material_name: str | None = None) -> None:
        if not result or not result.get("success"):
            self._status.setText("Sin resultado")
            return
        state = "Convergido" if result.get("converged") else "Máx. iteraciones"
        self._status.setText(f"{state} · {material_name or ''}")
        self._iter.setText(str(result.get("iterations", "—")))
        vol = result.get("final_volume_fraction")
        self._vol.setText(f"{vol:.2%}" if isinstance(vol, float) else "—")
        comp = result.get("final_compliance")
        self._compliance.setText(f"{comp:.6e}" if isinstance(comp, float) else "—")
        delta = result.get("max_density_change")
        self._conv.setText(f"Δx = {delta:.4f}" if isinstance(delta, float) else "—")

    def append_history(self, iteration: int, vol: float, compliance: float) -> None:
        self._log.append(f"[iter {iteration:>3}]  V={vol:6.2%}   c={compliance:.4e}")

    def clear_history(self) -> None:
        self._log.clear()

    def reset_all(self) -> None:
        self._mesh_n.setText("—")
        self._mesh_e.setText("—")
        self._mesh_t.setText("—")
        self._status.setText("—")
        self._iter.setText("—")
        self._vol.setText("—")
        self._compliance.setText("—")
        self._conv.setText("—")
        self._log.clear()
        self.clear_modal_modes()

    # ---- Animación modal (Fase 4.5d.5) ----
    def set_modal_modes(self, labels: list) -> None:
        """Muestra la sección con un label por modo ("Modo 1 — 42.3 Hz")."""
        self._mode_combo.clear()
        for i, lab in enumerate(labels):
            self._mode_combo.addItem(str(lab), i)
        self._playing = False
        self._btn_play.setText("▶ Animar")
        self._anim_status.setText("")
        self._anim_section.setVisible(bool(labels))

    def clear_modal_modes(self) -> None:
        self._mode_combo.clear()
        self._playing = False
        self._btn_play.setText("▶ Animar")
        self._anim_status.setText("")
        self._anim_section.setVisible(False)

    def animation_mode_index(self) -> int:
        data = self._mode_combo.currentData()
        return int(data) if data is not None else 0

    def animation_speed(self) -> float:
        try:
            return float(self._speed_combo.currentText().replace("×", ""))
        except (TypeError, ValueError):
            return 1.0

    def set_animation_playing(self, playing: bool, message: str = "") -> None:
        self._playing = bool(playing)
        self._btn_play.setText("⏸ Pausar" if playing else "▶ Animar")
        self._anim_status.setText(message)

    def _on_play_pause(self) -> None:
        if self._playing:
            self.pauseAnimation.emit()
        else:
            self.playAnimation.emit()