"""Host nativo del experimento: pywebview (WebView2) + core vendorizado.

Uso:
    python app_desktop.py            # sirve html/dist empaquetado
    python app_desktop.py --dev      # apunta a vite en http://localhost:5173

El HTML llama a window.pywebview.api.* (ver api.py y html/src/lib/bridge.ts).
Sin Qt, sin servidor HTTP, offline.
"""
from __future__ import annotations

import logging
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
DIST_INDEX = os.path.join(_HERE, "html", "dist", "index.html")
DEV_URL = "http://localhost:3000/"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("webapp.host")


def main(dev: bool = False) -> None:
    import webview
    from api import Api

    api = Api()
    if dev:
        url = DEV_URL
    elif os.path.exists(DIST_INDEX):
        url = DIST_INDEX
    else:
        logger.warning("html/dist no existe; usa --dev o corre npm run build en html/")
        url = DEV_URL

    window = webview.create_window(
        "Topologia Optimizada — experimento HTML",
        url=url,
        js_api=api,
        width=1500,
        height=900,
    )
    webview.start(debug=dev)


if __name__ == "__main__":
    main(dev="--dev" in sys.argv)
