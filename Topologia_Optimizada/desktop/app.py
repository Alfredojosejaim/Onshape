"""Application bootstrap for the desktop GUI (QApplication + window)."""

from __future__ import annotations


def run() -> int:
    import logging
    import sys

    # Configure logging before importing any desktop module so that optional
    # backend warnings are formatted cleanly and don't look like errors. The
    # self-contained build deliberately ships WITHOUT Kratos Multiphysics (the
    # app uses its own embedded FEA/SIMP solvers), so the missing-module notice
    # is expected and must not be shown as a scary CRITICAL/WARNING line.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("core.kratos_adapter").setLevel(logging.CRITICAL)

    from PySide6.QtWidgets import QApplication, QMessageBox
    from desktop.ui.style import DARK_QSS
    from desktop.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Topologia Optimizada")
    app.setApplicationDisplayName("Topología Optimizada")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)

    try:
        window = MainWindow()
    except Exception as exc:  # e.g. VTK/OpenGL unavailable (VM, RDP, sin GPU)
        QMessageBox.critical(
            None,
            "No se pudo iniciar la interfaz 3D",
            "Ocurrió un error al crear la ventana principal (posiblemente el "
            "entorno no tiene soporte OpenGL para VTK):\n\n"
            f"{exc}\n\n"
            "Verifique que dispone de una GPU con OpenGL o ejecute la "
            "aplicación en una máquina con renderizado 3D disponible.",
        )
        return 1

    window.show()
    return app.exec()
