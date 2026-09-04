"""overlays - overlay del viewport (badge, controles de vista, leyenda, placeholder).

Extrae de MainWindow la construcción de los widgets superpuestos sobre el
viewport (HTML chrome): badge superior, controles de centrado/wireframe/ejes/
fuerzas/fijaciones, barra de estado inferior con leyenda, y el placeholder
central. Se colocan a través de ``host.place(slot, widget)``.

ANTES → DESPUÉS → CONEXIÓN PRESERVADA
  MainWindow._build_viewport_overlays (602-671) → OverlayBuilder.build(owner, host)
  MainWindow._viewer_button /_set_viewer_active/_legend_dot (673-707)
      → viewers helpers de este módulo.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

from desktop.ui.style import PALETTE, TEXT_FAINT
from desktop.ui.components.widgets import repolish


def viewer_button(text: str, checked: bool = False, command=None) -> QPushButton:
    """Botón de control del visor (viewercontrol): checkable o de comando."""
    b = QPushButton(text)
    b.setProperty("viewercontrol", True)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if command is not None:
        b.setCheckable(False)
        b.clicked.connect(command)
        b.setProperty("active", False)
        repolish(b)
    else:
        b.setCheckable(True)
        b.setChecked(checked)
        b.toggled.connect(lambda on, btn=b: set_viewer_active(btn, on))
        set_viewer_active(b, checked)
    return b


def set_viewer_active(btn: QPushButton, active: bool) -> None:
    btn.setProperty("active", active)
    repolish(btn)


def legend_dot(text: str, color: str) -> QWidget:
    """Punto de color + etiqueta (leyenda de la barra de estado del visor)."""
    w = QWidget()
    hl = QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(5)
    dot = QLabel()
    dot.setFixedSize(10, 10)
    dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
    lab = QLabel(text)
    lab.setProperty("legend", True)
    hl.addWidget(dot)
    hl.addWidget(lab)
    return w


class OverlayBuilder:
    """Construye los overlays del viewport sobre un host.

    ``owner`` es MainWindow (provee handlers ``_on_*`` y referencia al viewport).
    ``host`` es el ViewportHost (desktop.ui.components.main_workspace) que
    expone .place() y .viewport.
    Las referencias resultantes (ctrl_*, _viewer_info, placeholder) se
    registran en el owner.
    """

    def __init__(self, owner, host) -> None:
        self.owner = owner
        self.host = host

    def build(self) -> None:
        owner, host = self.owner, self.host
        viewport = host.viewport

        # Badge (top-left)
        badge = QWidget()
        bl = QHBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(10)
        t1 = QLabel("Optimización")
        t1.setStyleSheet("font-size: 13px; font-weight: 600;")
        t2 = QLabel("SIMP · Standalone")
        t2.setProperty("badge", True)
        bl.addWidget(t1)
        bl.addWidget(t2)
        host.place("badge", badge)

        # View controls (top-right)
        controls = QWidget()
        cl = QVBoxLayout(controls)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(6)
        owner.ctrl_center = viewer_button(
            "📷 Centrar Vista", command=lambda: viewport.fit_to_view())
        owner.ctrl_wire = viewer_button("🔲 Wireframe", checked=True)
        owner.ctrl_wire.toggled.connect(
            lambda on: viewport.set_display_mode("wireframe" if on else "surfaced"))
        owner.ctrl_axes = viewer_button("📐 Ejes", checked=True)
        owner.ctrl_axes.toggled.connect(viewport.toggle_axes)
        owner.ctrl_forces = viewer_button("⚡ Fuerzas", checked=True)
        owner.ctrl_forces.toggled.connect(lambda on: owner._sync_sidebar_vis("forces", on))
        owner.ctrl_constraints = viewer_button("🔒 Fijaciones", checked=True)
        owner.ctrl_constraints.toggled.connect(lambda on: owner._sync_sidebar_vis("constraints", on))
        for b in (owner.ctrl_center, owner.ctrl_wire, owner.ctrl_axes,
                  owner.ctrl_forces, owner.ctrl_constraints):
            cl.addWidget(b)
        host.place("controls", controls)

        # Status bar overlay (bottom)
        status = QWidget()
        sl = QHBoxLayout(status)
        sl.setContentsMargins(14, 0, 14, 0)
        sl.setSpacing(14)
        sl.addWidget(legend_dot("Sólido CAD Real", PALETTE["solid_cad"]))
        sl.addWidget(legend_dot("Fuerzas (Vectores)", PALETTE["force"]))
        sl.addWidget(legend_dot("Fijaciones", PALETTE["constraint"]))
        sl.addStretch(1)
        info = QLabel("Visor 3D inicializando...")
        info.setProperty("viewinfo", True)
        sl.addWidget(info, 1)
        status.setStyleSheet(
            f"background: {PALETTE['overlay_center_bg']}; border: 1px solid {PALETTE['border_soft']};"
            "border-top-left-radius: 6px; border-top-right-radius: 6px;")
        owner._viewer_info = info
        host.place("status", status)

        # Placeholder (center) while no model is loaded
        ph = QWidget()
        pl = QVBoxLayout(ph)
        pl.setContentsMargins(18, 18, 18, 18)
        pl.setSpacing(10)
        box = QLabel("🔲")
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.setFixedSize(90, 90)
        box.setStyleSheet(
            f"border: 2px dashed {PALETTE['placeholder_border']}; border-radius: 10px; font-size: 26px;")
        hint = QLabel("Importe un archivo STEP para cargar el modelo 3D")
        hint.setStyleSheet(f"font-size: 11.5px; color: {TEXT_FAINT};")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pl.addStretch(1)
        pl.addWidget(box, 0, Qt.AlignmentFlag.AlignCenter)
        pl.addWidget(hint, 0, Qt.AlignmentFlag.AlignCenter)
        pl.addStretch(1)
        owner.placeholder = ph
        host.place("placeholder", ph)


__all__ = ["OverlayBuilder", "viewer_button", "set_viewer_active", "legend_dot"]