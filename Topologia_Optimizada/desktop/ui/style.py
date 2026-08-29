"""Application-wide Qt stylesheet: professional, sober, CAD-oriented dark theme.

Styled to feel like an engineering application (not a web page): flat panes,
hierarchical navigation trees, native-looking controls, restrained accent color.
"""

ACCENT = "#2f7bf6"
ACCENT_HOVER = "#3d86ff"

DARK_QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: #e6e6ea;
}}
QMainWindow, QWidget {{
    background-color: #1b1c1e;
}}
QMenuBar {{
    background-color: #161719;
    border-bottom: 1px solid #2a2b2f;
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 5px 12px;
    background: transparent;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background: #2a2b2f;
}}
QMenu {{
    background-color: #232427;
    border: 1px solid #38393d;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: #ffffff;
}}
QToolBar {{
    background-color: #1b1c1e;
    border: none;
    border-bottom: 1px solid #2a2b2f;
    spacing: 6px;
    padding: 6px 8px;
}}
QToolBar QToolButton {{
    background: #2c2d31;
    border: 1px solid #38393d;
    border-radius: 6px;
    padding: 6px 4px;
    min-width: 34px;
    min-height: 30px;
}}
QToolBar QToolButton:hover {{
    background: #333438;
}}
QToolBar QToolButton:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
}}
QSplitter::handle {{
    background-color: #26272b;
    width: 4px;
}}
QDockWidget {{
    background: #1b1c1e;
    color: #cfd0d4;
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background: #202124;
    padding: 7px 10px;
    border-bottom: 1px solid #2a2b2f;
    font-weight: 600;
}}
QTreeWidget {{
    background: #1f2023;
    border: 1px solid #2a2b2f;
    border-radius: 6px;
    padding: 4px;
}}
QTreeWidget::item {{
    padding: 4px 2px;
    border-radius: 4px;
}}
QTreeWidget::item:selected {{
    background: {ACCENT};
    color: #ffffff;
}}
QTreeWidget::item:hover {{
    background: #2a2b2f;
}}
QListWidget {{
    background: #1f2023;
    border: 1px solid #2a2b2f;
    border-radius: 6px;
}}
QListWidget::item {{
    padding: 5px 8px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background: {ACCENT};
    color: #ffffff;
}}
QGroupBox {{
    background: #222326;
    border: 1px solid #2f3034;
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #cfd0d4;
}}
QLabel {{
    background: transparent;
}}
QPushButton {{
    background: #2c2d31;
    border: 1px solid #38393d;
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    background: #333438;
}}
QPushButton:pressed {{
    background: #2a2b2f;
}}
QPushButton:disabled {{
    color: #6f7075;
}}
QPushButton[primary="true"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[primary="true"]:hover {{
    background: {ACCENT_HOVER};
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: #2a2b2f;
    border: 1px solid #38393d;
    border-radius: 6px;
    padding: 5px 8px;
    min-height: 20px;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QComboBox QAbstractItemView {{
    background: #232427;
    border: 1px solid #38393d;
    selection-background-color: {ACCENT};
}}
QStatusBar {{
    background: #161719;
    border-top: 1px solid #2a2b2f;
    color: #9a9ba0;
}}
QTabWidget::pane {{
    border: 1px solid #2a2b2f;
    background: #1f2023;
    border-radius: 6px;
}}
QTabBar::tab {{
    background: #232427;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background: {ACCENT};
    color: #ffffff;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3a3b3f;
    border-radius: 6px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
}}
QScrollBar::handle:horizontal {{
    background: #3a3b3f;
    border-radius: 6px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QCheckBox {{
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid #38393d;
    border-radius: 4px;
    background: #2a2b2f;
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QProgressBar {{
    background: #2a2b2f;
    border: 1px solid #38393d;
    border-radius: 6px;
    text-align: center;
    color: #e6e6ea;
    height: 16px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 5px;
}}
"""
