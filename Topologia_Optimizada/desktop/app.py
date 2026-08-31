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
    except Exception as exc:  # any error during window/viewport construction
        detail = f"{type(exc).__name__}: {exc}"
        # A common real-world cause is lack of GPU/OpenGL support (VM, RDP,
        # integrated graphics without a GL driver), but we never guess: the
        # actual error is always shown so code bugs are not masked as a
        # hardware problem.
        QMessageBox.critical(
            None,
            "No se pudo iniciar la interfaz 3D",
            "Ocurrió un error al crear la ventana principal.\n\n"
            f"{detail}\n\n"
            "Si el error menciona OpenGL / pixel format / GPU, ejecute la "
            "aplicación en una máquina con renderizado 3D disponible o "
            "habilite el renderizado por software. En otro caso, revise el "
            "error indicado (puede tratarse de un problema interno del "
            "programa, no de la tarjeta gráfica).",
        )
        return 1

    window.show()
    return app.exec()
