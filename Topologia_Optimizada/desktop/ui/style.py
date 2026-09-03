"""Application-wide Qt stylesheet and palette for the native desktop UI.

The colors come from a single external source: ``theme.json`` in this folder.
Editing that file restyles the ENTIRE interface -- widgets created in Python
code and any ``.ui`` file loaded at runtime alike -- because every token is
referenced from both the QSS stylesheet and the ``PALETTE`` used by the code.

The QSS template below defines the dark engineering theme (app shell, panels,
ribbon, tabs, pills, chips, inputs, ...) using ``{token}`` placeholders. The
theme tokens are substituted in at import time.
"""

from __future__ import annotations

import json
import os

_THEME_PATH = os.path.join(os.path.dirname(__file__), "theme.json")

with open(_THEME_PATH, encoding="utf-8") as _fh:
    T: dict = json.load(_fh)

# Remove the informative "_comment" key (not a color token).
T.pop("_comment", None)

ACCENT = T["accent"]
ACCENT_HOVER = T["accent_hover"]
ACCENT_SOFT = T["accent_soft"]
ACCENT_BORDER = T["accent_border"]
ACCENT_BADGE_BG = T["accent_badge_bg"]
ACCENT_BADGE_BORDER = T["accent_badge_border"]
ACCENT_DISABLED_BG = T["accent_disabled_bg"]
ACCENT_DISABLED_BORDER = T["accent_disabled_border"]
ACCENT_TEXT = T["accent_text"]

BG_APP = T["bg_app"]
BG_PANEL = T["bg_panel"]
BG_PANEL2 = T["bg_panel2"]
BG_TOOLBTN = T["bg_toolbtn"]
BG_VIEWPORT = T["bg_viewport"]
BG_MENUBAR = T["bg_menubar"]
BG_STATUSBAR = T["bg_statusbar"]
BG_SCROLLBAR = T["bg_scrollbar"]
BG_SCROLLBAR_HOVER = T["bg_scrollbar_hover"]

BORDER = T["border"]
BORDER_SOFT = T["border_soft"]

TEXT_MAIN = T["text_main"]
TEXT_DIM = T["text_dim"]
TEXT_FAINT = T["text_faint"]
TEXT_WHITE = T["text_white"]

OK_TEXT = T["ok_text"]
OK_BG = T["ok_bg"]
OK_BORDER = T["ok_border"]
OK_DONE_BORDER = T["ok_done_border"]

AVATAR_GRAD_A = T["avatar_grad_a"]
AVATAR_GRAD_B = T["avatar_grad_b"]

OVERLAY_CONTROL_BG = T["overlay_control_bg"]

SOLID_CAD = T["solid_cad"]
FORCE = T["force"]
CONSTRAINT = T["constraint"]

ERROR = T["error"]


def hex_to_rgb_float(color: str) -> tuple[float, float, float]:
    """Convert a '#rrggbb' hex color into a 0..1 RGB float tuple (VTK uses floats)."""
    c = color.strip().lstrip("#")
    if len(c) != 6:
        raise ValueError(f"expected #rrggbb hex color, got {color!r}")
    return tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

_QSS_TEMPLATE = """
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: {text_main};
}}

/* ---- Shell ---- */
QMainWindow, QWidget {{
    background-color: {bg_app};
}}
QFrame#viewportContainer {{ background-color: transparent; }}
QFrame#timelinePanel, QFrame#treePanel, QFrame#propsPanel {{
    background-color: {bg_panel};
    border: 1px solid {border_soft};
    border-radius: 6px;
}}

/* ---- Menu bar (Archivo · Editar · Diseño · Herramientas · Ayuda) ---- */
QMenuBar {{
    background-color: {bg_menubar};
    border-bottom: 1px solid {border};
    padding: 2px 6px;
}}
QMenuBar::item {{
    padding: 6px 12px;
    background: transparent;
    border-radius: 4px;
    color: {text_dim};
    font-size: 13.5px;
}}
QMenuBar::item:selected {{
    background: {bg_panel2};
    color: {text_main};
}}
QMenu {{
    background-color: {bg_panel};
    border: 1px solid {border};
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    color: {text_dim};
}}
QMenu::item:selected {{
    background: {accent};
    color: {text_white};
}}

/* ---- Buttons ---- */
QPushButton {{
    background: {bg_panel2};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 8px 10px;
    color: {accent_text};
    font-weight: 600;
    font-size: 12.5px;
}}
QPushButton:hover {{ background: {bg_toolbtn}; color: {text_main}; }}
QPushButton:pressed {{ background: {bg_panel2}; }}
QPushButton:disabled {{ color: {text_faint}; }}

QPushButton[htmlprimary="true"] {{
    background: {accent};
    border-color: {accent};
    color: {text_white};
    font-weight: 600;
}}
QPushButton[htmlprimary="true"]:hover {{ background: {accent_hover}; }}
QPushButton[htmlprimary="true"]:disabled {{ background: {accent_disabled_bg}; border-color: {accent_disabled_border}; }}

/* Ribbon tool buttons (glyph on top, tiny label below) */
QPushButton[ribbon="true"] {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 0;
}}
QPushButton[ribbon="true"]:hover {{ background: {bg_panel2}; }}
QPushButton[ribbon="true"][active="true"] {{
    background: {accent_soft};
    border: 1px solid {accent_border};
}}

/* Workspace tabs */
QPushButton[tab="true"] {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: {text_dim};
    padding: 0 14px;
    font-weight: 500;
    font-size: 12.5px;
}}
QPushButton[tab="true"]:hover {{ color: {text_main}; }}
QPushButton[tab="true"][active="true"] {{
    color: {text_main};
    border-bottom: 2px solid {accent};
}}

/* Timeline step pills */
QPushButton[pill="true"] {{
    background: {bg_panel2};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 6px 12px;
    color: {text_dim};
    font-size: 12.5px;
    font-weight: 500;
}}
QPushButton[pill="true"]:hover {{ color: {text_main}; }}
QPushButton[pill="true"][active="true"] {{
    background: {accent};
    border-color: {accent};
    color: {text_white};
}}
QPushButton[pill="true"][done="true"] {{
    border-color: {ok_done_border};
    color: {ok_text};
}}

/* Round play button */
QPushButton[play="true"] {{
    background: {accent};
    color: {text_white};
    border: none;
    border-radius: 17px;
    font-size: 15px;
}}
QPushButton[play="true"]:hover {{ background: {accent_hover}; }}

/* Viewer overlay control buttons (inside the 3D viewport) */
QPushButton[viewercontrol="true"] {{
    background: {overlay_control_bg};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 5px 10px;
    color: {text_dim};
    font-size: 11.5px;
    font-weight: 500;
    text-align: left;
}}
QPushButton[viewercontrol="true"]:hover {{ color: {text_main}; background: {bg_panel2}; }}
QPushButton[viewercontrol="true"][active="true"] {{
    color: {accent_hover};
    border-color: {accent_border};
}}

/* ---- Inputs ---- */
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: {bg_panel2};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 6px 8px;
    min-height: 20px;
    color: {text_main};
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {border};
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {accent};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{
    image: none;
    border: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text_dim};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {bg_panel};
    border: 1px solid {border};
    selection-background-color: {accent};
    selection-color: {text_white};
    outline: 0;
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {text_faint};
}}

/* Slider (HTML range input: thin track + round accent thumb) */
QSlider::groove:horizontal {{
    height: 4px;
    background: {border};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    height: 4px;
    background: {accent};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
    background: {accent};
    border: 2px solid {text_white};
}}

/* ---- Tree ---- */
QTreeWidget {{
    background: transparent;
    border: none;
    outline: 0;
}}
QTreeWidget::item {{
    padding: 6px 4px;
    border-radius: 4px;
    color: {text_dim};
}}
QTreeWidget::item:hover {{ background: {bg_panel2}; }}
QTreeWidget::item:selected {{
    background: {accent};
    color: {text_white};
}}
QTreeWidget::branch {{ background: transparent; }}

/* ---- GroupBox / misc ---- */
QGroupBox {{
    background: {bg_panel};
    border: 1px solid {border_soft};
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 10px;
    font-weight: 600;
    color: {text_main};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {text_dim};
}}

QLabel[section="true"] {{
    font-size: 10px;
    letter-spacing: 0.7px;
    text-transform: uppercase;
    color: {accent_hover};
    border-top: 1px solid {border_soft};
    padding-top: 8px;
    margin-top: 6px;
}}
QLabel[info="true"] {{ color: {text_dim}; font-size: 11.5px; }}
QLabel[infovalid="true"] {{ color: {accent_text}; font-size: 11.5px; }}
QLabel[dim="true"] {{ color: {text_dim}; }}
QLabel[faint="true"] {{ color: {text_faint}; }}
QLabel[title="true"] {{
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: {text_main};
}}
QLabel[chip="true"] {{
    color: {text_dim};
    font-size: 13px;
}}
QLabel[avatar="true"] {{
    font-size: 12px;
    font-weight: 700;
    color: {text_white};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {avatar_grad_a}, stop:1 {avatar_grad_b});
    border-radius: 14px;
    padding: 4px 7px;
}}
QLabel[badge="true"] {{
    color: {accent_text};
    background: {accent_badge_bg};
    border: 1px solid {accent_badge_border};
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 500;
}}
QLabel[chipok="true"] {{
    color: {ok_text};
    background: {ok_bg};
    border: 1px solid {ok_border};
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
}}
QLabel[legend="true"] {{ color: {text_dim}; font-size: 11px; }}
QLabel[viewinfo="true"] {{ color: {text_dim}; font-size: 11.5px; }}

/* CheckBox */
QCheckBox {{ spacing: 7px; color: {text_dim}; font-size: 12.5px; }}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {border};
    border-radius: 4px;
    background: {bg_panel2};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
}}

/* Status bar / progressbar */
QStatusBar {{
    background: {bg_statusbar};
    border-top: 1px solid {border_soft};
    color: {text_dim};
}}
QStatusBar::item {{ border: none; }}
QProgressBar {{
    background: {bg_panel2};
    border: 1px solid {border};
    border-radius: 3px;
    text-align: center;
    color: {text_main};
    height: 6px;
    font-size: 0px;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {bg_scrollbar};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: {bg_scrollbar};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{ background: {bg_scrollbar_hover}; }}

/* QTabWidget fallback (kept styled for the results page if reused) */
QTabWidget::pane {{
    border: 1px solid {border_soft};
    background: {bg_panel};
    border-radius: 6px;
}}
QTabBar::tab {{
    background: {bg_panel2};
    border: 1px solid {border};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 6px 14px;
    margin-right: 2px;
    color: {text_dim};
}}
QTabBar::tab:selected {{ background: {bg_panel}; color: {text_main}; }}
"""

DARK_QSS = _QSS_TEMPLATE.format_map(T)

# Palette exported for the Python UI code (overlay colors, viewport bg, ...).
# Kept in sync with the QSS source (same theme.json tokens).
PALETTE = {
    "bg_app": BG_APP,
    "bg_panel": BG_PANEL,
    "bg_panel2": BG_PANEL2,
    "bg_viewport": BG_VIEWPORT,
    "bg_viewport_top": T["viewport_bg_top"],
    "bg_viewport_bottom": T["viewport_bg_bottom"],
    "border": BORDER,
    "border_soft": BORDER_SOFT,
    "text_main": TEXT_MAIN,
    "text_dim": TEXT_DIM,
    "text_faint": TEXT_FAINT,
    "accent": ACCENT,
    "accent_hover": ACCENT_HOVER,
    "accent_text": ACCENT_TEXT,
    "solid_cad": SOLID_CAD,
    "force": FORCE,
    "constraint": CONSTRAINT,
    "grid": T["grid_color"],
    "error": T["error"],
    "overlay_center_bg": T["overlay_center_bg"],
    "placeholder_border": T["placeholder_border"],
}
