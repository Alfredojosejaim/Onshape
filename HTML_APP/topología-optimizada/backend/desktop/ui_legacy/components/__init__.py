"""desktop.ui_legacy.components - componentes visuales reutilizables de la UI.

Divide la construcción visual de MainWindow en componentes de presentación
independientes de la lógica CAD/CAE:
  - widgets: primitivas visuales (repolish, glyph, mini, RibbonTool)
  - menus:   barra de menú (Archivo · Editar · Operaciones · ...)
  - workspace: barra superior, pestañas y cinta (ribbon)
  - overlays:  overlays del viewport (badge, controles, leyenda, placeholder)
  - main_workspace: composición física del workspace principal (sidebar,
    viewport via ViewportHost, timeline, results)

MainWindow queda como coordinador: construye el grafo central, conecta las
señales de los paneles e implementa los handlers (_on_*); la composición visual
se delega en estos componentes.
"""

from desktop.ui_legacy.components.widgets import repolish, glyph_label, mini_label, RibbonTool
from desktop.ui_legacy.components.menus import MenuBuilder
from desktop.ui_legacy.components.workspace import WorkspaceBuilder
from desktop.ui_legacy.components.overlays import OverlayBuilder, viewer_button
from desktop.ui_legacy.components.main_workspace import MainWorkspaceBuilder, ViewportHost

__all__ = [
    "repolish",
    "glyph_label",
    "mini_label",
    "RibbonTool",
    "MenuBuilder",
    "WorkspaceBuilder",
    "OverlayBuilder",
    "viewer_button",
    "MainWorkspaceBuilder",
    "ViewportHost",
]