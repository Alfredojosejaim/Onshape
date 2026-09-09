"""Host nativo: pywebview (WebView2) + core vendorizado (copia de Topologia_Optimizada).

Uso:
    python app_desktop.py            # sirve dist/ empaquetado (npm run build)
    python app_desktop.py --dev      # apunta a vite en http://localhost:3000/

El React llama a window.pywebview.api.* (ver api.py y src/lib/backend.ts).
Sin Qt, sin servidor HTTP, offline. Estetica app-main intacta.
"""
from __future__ import annotations

import logging
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DIST_INDEX = os.path.join(_HERE, "dist", "index.html")
DEV_URL = "http://localhost:3000/"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("app.host")


def main(dev: bool = False) -> None:
    import webview
    from api import Api

    api = Api()
    if dev:
        url = DEV_URL
    elif os.path.exists(DIST_INDEX):
        url = DIST_INDEX
    else:
        logger.warning("dist/ no existe; usa --dev o corre npm run build")
        url = DEV_URL

    window = webview.create_window(
        "Topologia Optimizada",
        url=url,
        js_api=api,
        width=1500,
        height=900,
    )
    webview.start(debug=dev)


if __name__ == "__main__":
    import sys
    main(dev="--dev" in sys.argv)
