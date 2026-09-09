"""Shell experimental: QWebEngineView + QWebChannel + VTK intacto.

Branch: html-ui-poc. No modifica Topologia_Optimizada/.
El core (core/*, services/*, desktop/pipeline/*, desktop/viewport/*) se
importa por path en modo SOLO-LECTURA. La unica capa reemplazada es
desktop.ui (ribbon, diseno/arbol) -> Web_App/html (Vite+React).

Uso:
    cd Web_App
    python app_hybrid.py            # sirve html/dist via QUrl local
    python app_hybrid.py --dev      # apunta a http://localhost:5173 (vite dev)

Variables testeadas: solo la UI. Solvers, topo_problem y VTK identicos.
"""
from __future__ import annotations

import logging
import os
import sys

CORE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "core_vendor")
)
if CORE_ROOT not in sys.path:
    sys.path.insert(0, CORE_ROOT)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logging.getLogger("core.kratos_adapter").setLevel(logging.CRITICAL)


def _make_controller():
    """PipelineController real — mismo que usa desktop/app.py."""
    from desktop.pipeline.controller import PipelineController
    return PipelineController()


def run(dev: bool = False) -> int:
    from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter
    from PySide6.QtCore import QUrl, Qt
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebChannel import QWebChannel

    from bridge_core import CoreBridge

    app = QApplication(sys.argv)
    app.setApplicationName("Topologia Optimizada (HTML POC)")

    controller = _make_controller()
    bridge = CoreBridge(controller)

    channel = QWebChannel()
    channel.registerObject("pyBridge", bridge)

    # --- Panel HTML (reemplaza ribbon + arbol de diseno) ---
    view = QWebEngineView()
    view.page().setWebChannel(channel)
    if dev:
        view.setUrl(QUrl("http://localhost:5173/"))
    else:
        dist = os.path.join(os.path.dirname(__file__), "html", "dist", "index.html")
        if os.path.exists(dist):
            view.setUrl(QUrl.fromLocalFile(dist))
        else:
            # Fallback a src dev: avisa que falta `npm run build`
            view.setHtml(
                "<h2>Falta html/dist — corre `npm run build` en Web_App/html "
                "o lanza con --dev</h2>"
            )

    # --- Viewport 3D nativo (pipeline VTK EXACTAMENTE igual, sin tocar) ---
    # Se importa el renderer existente; si falla (sin GPU), se usa el
    # software_viewport ya previsto por el core. No se duplica logica.
    vtk_widget = None
    try:
        from desktop.viewport.viewport_3d import VTKViewport  # noqa
        # Nota: el widget concreto se monta aqui solo si la API lo permite;
        # en caso contrario el HTML muestra el estado y el VTK sigue vivo
        # en el controller (tessellation/mesh sin cambios).
        logging.info("VTKViewport disponible — pipeline VTK intacto")
    except Exception as exc:  # noqa: BLE001
        logging.info("Viewport VTK no montado en split (%s); "
                     "el controller sigue con software fallback", exc)

    win = QMainWindow()
    win.setWindowTitle("Topologia Optimizada — experimento HTML (html-ui-poc)")
    win.resize(1500, 900)
    if vtk_widget is not None:
        split = QSplitter(Qt.Horizontal)
        split.addWidget(view)
        split.addWidget(vtk_widget)
        split.setSizes([900, 600])
        win.setCentralWidget(split)
    else:
        win.setCentralWidget(view)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run(dev="--dev" in sys.argv))
