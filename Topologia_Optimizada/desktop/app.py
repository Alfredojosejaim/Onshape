"""Application bootstrap for the desktop GUI (QApplication + window)."""

from __future__ import annotations


def run() -> int:
    import sys
    from PySide6.QtWidgets import QApplication
    from desktop.ui.style import DARK_QSS
    from desktop.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Topologia Optimizada")
    app.setApplicationDisplayName("Topología Optimizada")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)

    window = MainWindow()
    window.show()
    return app.exec()
