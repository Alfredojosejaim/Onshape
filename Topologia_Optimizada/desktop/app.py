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
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        QMessageBox.critical(
            None,
            "No se pudo iniciar la interfaz",
            "Ocurrió un error al crear la ventana principal.\n\n"
            f"{detail}\n\n"
            "Si el error menciona OpenGL / pixel format / GPU, la aplicación "
            "intentará usar el renderizador por software. Si el error persiste, "
            "revise el mensaje indicado (puede tratarse de un problema interno "
            "del programa, no de la tarjeta gráfica).",
        )
        return 1

    window.show()

    # Informar al usuario si se está usando el renderizador por software
    host = getattr(window, "host", None)
    if host and not getattr(host, "_use_vtk", True):
        logging.getLogger("desktop.app").info(
            "Renderizador por software activo (sin aceleración GPU). "
            "El rendimiento puede ser menor que con GPU dedicada."
        )

    return app.exec()
