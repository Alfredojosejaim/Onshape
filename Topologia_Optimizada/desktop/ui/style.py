"""Application-wide Qt stylesheet for the native desktop UI.

The tokens define the dark engineering theme of the application:
app shell #1b1c1e, panels #232427 / #2a2b2f, accent #2f7bf6, borders
#38393d / #313236. Widgets are styled through custom dynamic properties
(ribbon, tab, pill, section, chip, avatar, ...).
"""

ACCENT = "#2f7bf6"
ACCENT_HOVER = "#3d86ff"

BG_APP = "#1b1c1e"
BG_PANEL = "#232427"
BG_PANEL2 = "#2a2b2f"
BG_TOOLBTN = "#2c2d31"
BORDER = "#38393d"
BORDER_SOFT = "#313236"
TEXT_MAIN = "#f2f2f3"
TEXT_DIM = "#9a9ba0"
TEXT_FAINT = "#6f7075"
ACCENT_TEXT = "#bcd8ff"

DARK_QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: {TEXT_MAIN};
}}

/* ---- Shell ---- */
QMainWindow, QWidget {{
    background-color: {BG_APP};
}}
QFrame#viewportContainer {{ background-color: transparent; }}
QFrame#timelinePanel, QFrame#treePanel, QFrame#propsPanel {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
}}

/* ---- Menu bar (Archivo · Editar · Diseño · Herramientas · Ayuda) ---- */
QMenuBar {{
    background-color: #1a1a1c;
    border-bottom: 1px solid {BORDER};
    padding: 2px 6px;
}}
QMenuBar::item {{
    padding: 6px 12px;
    background: transparent;
    border-radius: 4px;
    color: {TEXT_DIM};
    font-size: 13.5px;
}}
QMenuBar::item:selected {{
    background: {BG_PANEL2};
    color: {TEXT_MAIN};
}}
QMenu {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
    color: {TEXT_DIM};
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: #ffffff;
}}

/* ---- Buttons ---- */
QPushButton {{
    background: {BG_PANEL2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px 10px;
    color: {ACCENT_TEXT};
    font-weight: 600;
    font-size: 12.5px;
}}
QPushButton:hover {{ background: {BG_TOOLBTN}; color: {TEXT_MAIN}; }}
QPushButton:pressed {{ background: {BG_PANEL2}; }}
QPushButton:disabled {{ color: {TEXT_FAINT}; }}

QPushButton[htmlprimary="true"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[htmlprimary="true"]:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[htmlprimary="true"]:disabled {{ background: rgba(47,123,246,0.35); border-color: rgba(47,123,246,0.35); }}

/* Ribbon tool buttons (glyph on top, tiny label below) */
QPushButton[ribbon="true"] {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 0;
}}
QPushButton[ribbon="true"]:hover {{ background: {BG_PANEL2}; }}
QPushButton[ribbon="true"][active="true"] {{
    background: rgba(47,123,246,0.16);
    border: 1px solid rgba(47,123,246,0.5);
}}

/* Workspace tabs */
QPushButton[tab="true"] {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: {TEXT_DIM};
    padding: 0 14px;
    font-weight: 500;
    font-size: 12.5px;
}}
QPushButton[tab="true"]:hover {{ color: {TEXT_MAIN}; }}
QPushButton[tab="true"][active="true"] {{
    color: {TEXT_MAIN};
    border-bottom: 2px solid {ACCENT};
}}

/* Timeline step pills */
QPushButton[pill="true"] {{
    background: {BG_PANEL2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 12px;
    color: {TEXT_DIM};
    font-size: 12.5px;
    font-weight: 500;
}}
QPushButton[pill="true"]:hover {{ color: {TEXT_MAIN}; }}
QPushButton[pill="true"][active="true"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
}}
QPushButton[pill="true"][done="true"] {{
    border-color: rgba(90,200,120,0.4);
    color: #b9f2c4;
}}

/* Round play button */
QPushButton[play="true"] {{
    background: {ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 17px;
    font-size: 15px;
}}
QPushButton[play="true"]:hover {{ background: {ACCENT_HOVER}; }}

/* Viewer overlay control buttons (inside the 3D viewport) */
QPushButton[viewercontrol="true"] {{
    background: rgba(26,27,29,0.85);
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 10px;
    color: {TEXT_DIM};
    font-size: 11.5px;
    font-weight: 500;
    text-align: left;
}}
QPushButton[viewercontrol="true"]:hover {{ color: {TEXT_MAIN}; background: {BG_PANEL2}; }}
QPushButton[viewercontrol="true"][active="true"] {{
    color: {ACCENT_HOVER};
    border-color: rgba(47,123,246,0.5);
}}

/* ---- Inputs ---- */
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: {BG_PANEL2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 8px;
    min-height: 20px;
    color: {TEXT_MAIN};
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {BORDER};
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{
    image: none;
    border: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_DIM};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
    outline: 0;
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {TEXT_FAINT};
}}

/* Slider (HTML range input: thin track + round accent thumb) */
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    height: 4px;
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
    background: {ACCENT};
    border: 2px solid #ffffff;
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
    color: {TEXT_DIM};
}}
QTreeWidget::item:hover {{ background: {BG_PANEL2}; }}
QTreeWidget::item:selected {{
    background: {ACCENT};
    color: #ffffff;
}}
QTreeWidget::branch {{ background: transparent; }}

/* ---- GroupBox / misc ---- */
QGroupBox {{
    background: {BG_PANEL};
    border: 1px solid {BORDER_SOFT};
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 10px;
    font-weight: 600;
    color: {TEXT_MAIN};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {TEXT_DIM};
}}

QLabel[section="true"] {{
    font-size: 10px;
    letter-spacing: 0.7px;
    text-transform: uppercase;
    color: {ACCENT_HOVER};
    border-top: 1px solid {BORDER_SOFT};
    padding-top: 8px;
    margin-top: 6px;
}}
QLabel[info="true"] {{ color: {TEXT_DIM}; font-size: 11.5px; }}
QLabel[infovalid="true"] {{ color: {ACCENT_TEXT}; font-size: 11.5px; }}
QLabel[dim="true"] {{ color: {TEXT_DIM}; }}
QLabel[faint="true"] {{ color: {TEXT_FAINT}; }}
QLabel[title="true"] {{
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: {TEXT_MAIN};
}}
QLabel[chip="true"] {{
    color: {TEXT_DIM};
    font-size: 13px;
}}
QLabel[avatar="true"] {{
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5b6cff, stop:1 #8a5bff);
    border-radius: 14px;
    padding: 4px 7px;
}}
QLabel[badge="true"] {{
    color: {ACCENT_TEXT};
    background: rgba(47,123,246,0.18);
    border: 1px solid rgba(47,123,246,0.4);
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 500;
}}
QLabel[chipok="true"] {{
    color: #b9f2c4;
    background: rgba(90,200,120,0.14);
    border: 1px solid rgba(90,200,120,0.35);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
}}
QLabel[legend="true"] {{ color: {TEXT_DIM}; font-size: 11px; }}
QLabel[viewinfo="true"] {{ color: {TEXT_DIM}; font-size: 11.5px; }}

/* CheckBox */
QCheckBox {{ spacing: 7px; color: {TEXT_DIM}; font-size: 12.5px; }}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {BG_PANEL2};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* Status bar / progressbar */
QStatusBar {{
    background: #161719;
    border-top: 1px solid {BORDER_SOFT};
    color: {TEXT_DIM};
}}
QStatusBar::item {{ border: none; }}
QProgressBar {{
    background: {BG_PANEL2};
    border: 1px solid {BORDER};
    border-radius: 3px;
    text-align: center;
    color: {TEXT_MAIN};
    height: 6px;
    font-size: 0px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3a3b3f;
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: #3a3b3f;
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{ background: #56575d; }}

/* QTabWidget fallback (kept styled for the results page if reused) */
QTabWidget::pane {{
    border: 1px solid {BORDER_SOFT};
    background: {BG_PANEL};
    border-radius: 6px;
}}
QTabBar::tab {{
    background: {BG_PANEL2};
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 6px 14px;
    margin-right: 2px;
    color: {TEXT_DIM};
}}
QTabBar::tab:selected {{ background: {BG_PANEL}; color: {TEXT_MAIN}; }}
"""

# Palette exported for the Python UI code (overlay colors, viewport bg, ...)
PALETTE = {
    "bg_app": BG_APP,
    "bg_panel": BG_PANEL,
    "bg_panel2": BG_PANEL2,
    "bg_viewport": "#3c3d41",
    "border": BORDER,
    "border_soft": BORDER_SOFT,
    "text_main": TEXT_MAIN,
    "text_dim": TEXT_DIM,
    "text_faint": TEXT_FAINT,
    "accent": ACCENT,
    "accent_hover": ACCENT_HOVER,
    "accent_text": ACCENT_TEXT,
    "solid_cad": "#3b82f6",
    "force": "#f59e0b",
    "constraint": "#8b5cf6",
}