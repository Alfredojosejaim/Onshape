"""widgets - primitivas visuales reutilizables de la UI desktop.

Componentes visuales genéricos (sin dependencia de MainWindow) usados por el
resto de componentes y por la composición del workspace:
  - repolish(): fuerza el re-polish del estilo de un widget (utilitario).
  - glyph_label() / mini_label(): etiquetas de glifo y micro-etiqueta.
  - RibbonTool: botón de cinta 64x52 con glifo arriba y etiqueta abajo.

Estos helpers se extrajeron de MainWindow para que la construcción visual sea
reutilizable, sin tocar la lógica CAD/CAE.
"""

from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from desktop.ui.style import TEXT_DIM


def repolish(widget) -> None:
    """Fuerza a Qt a re-aplicar la hoja de estilos a un widget (y repintarlo)."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def glyph_label(text: str, size: int = 15) -> QLabel:
    """Etiqueta centrada de glifo (emojis/símbolos) con fondo transparente."""
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"background: transparent; font-size: {size}px; color: {TEXT_DIM};")
    return lbl


def mini_label(text: str) -> QLabel:
    """Micro-etiqueta centrada (texto pequeño, tenue) bajo un glifo."""
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"background: transparent; font-size: 9px; color: {TEXT_DIM};")
    return lbl


class RibbonTool(QPushButton):
    """Un botón de cinta 64x52: glifo arriba y etiqueta diminuta debajo (HTML .tool-btn)."""

    def __init__(self, glyph: str, label: str, tooltip: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setProperty("ribbon", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(64, 52)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 4, 3, 3)
        lay.setSpacing(2)
        lay.addStretch(1)
        lay.addWidget(glyph_label(glyph))
        lay.addWidget(mini_label(label))
        lay.addStretch(1)
        if tooltip:
            self.setToolTip(tooltip)


__all__ = [
    "repolish",
    "glyph_label",
    "mini_label",
    "RibbonTool",
]
