"""Host nativo de la nueva app: pywebview (WebView2) + Topologia_Optimizada.

Uso:
    python backend/app_desktop.py         # sirve dist/ empaquetado (sin navegador)
    python backend/app_desktop.py --dev   # apunta a vite en http://localhost:3000

El HTML llama a window.pywebview.api.* (ver src/lib/bridge.ts). El Bridge de
aqui es ligero (solo stdlib) y reenvia cada llamada al backend/server.py, que
corre en un proceso aparte porque las DLL nativas del core (VTK/Qt/OCC)
corrompen el heap si comparten proceso con WebView2/.NET.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
DIST_INDEX = os.path.abspath(os.path.join(_HERE, "..", "dist", "index.html"))
DEV_URL = "http://localhost:3000/"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("webapp.host")

# Metodos que expone el frontend (src/lib/bridge.ts) via window.pywebview.api.
# WHITELIST-FIX (reversible): se agregaron los endpoints nuevos del backend;
# sin ellos el frontend recibe undefined y cae a fallbacks (p. ej. un solo
# objeto en el arbol). Para volver atras: recortar la tupla.
_METHODS = (
    "getSnapshot", "getMaterials", "setMaterial", "validateProblem",
    "importStep", "importStepBytes", "listFixtures", "listLibrary",
    "switchModel", "removeModel", "getSolids", "generateMesh",    "generateAdaptiveMesh", "setBoundaries", "runFea", "runFeaIterative",
    "runOptimization", "runSimpLoop", "runSimpKratosVerified",
    "runGenerativeDesign", "registerReconstruction", "runThermal", "runModal",
    "runCrossCheck", "cadOperation", "validateState",
    "createCondition", "listConditions", "clearConditions",
    "getLicense", "pollJob", "getMeshPreview", "getSurfaceMesh",
    "exportStep", "getNavProfiles", "setNavProfile",
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Bridge:
    """Forwarder ligero: cada metodo POSTea al server.py y devuelve el dict."""

    def __init__(self, base_url: str) -> None:
        self._base = base_url

    def _call(self, method: str, *args: object) -> dict:
        data = json.dumps({"method": method, "args": list(args)}).encode("utf-8")
        req = urllib.request.Request(
            self._base, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as res:
            body = json.loads(res.read().decode("utf-8"))
        if isinstance(body, dict) and body.get("ok") and "result" in body:
            result = body["result"]
            return result if isinstance(result, dict) else {"ok": True, "value": result}
        return body if isinstance(body, dict) else {"ok": False, "error": str(body)}


def _make_bridge(base_url: str) -> Bridge:
    bridge = Bridge(base_url)

    def _wrap(name: str):
        def _fn(*args: object) -> dict:
            return bridge._call(name, *args)
        _fn.__name__ = name
        return _fn

    for _name in _METHODS:
        setattr(bridge, _name, _wrap(_name))
    return bridge


def main(dev: bool = False) -> None:
    import webview

    port = _free_port()
    server = subprocess.Popen(
        [sys.executable, os.path.join(_HERE, "server.py"), str(port)],
        cwd=_HERE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}/"
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(
                    urllib.request.Request(
                        base,
                        data=b"{}",
                        headers={"Content-Type": "application/json"},
                        method="POST"),
                    timeout=2)
                break
            except Exception:  # noqa: BLE001 - el server aun arranca
                if server.poll() is not None:
                    raise RuntimeError("backend/server.py no arranco")
                time.sleep(0.3)
        else:
            raise RuntimeError("backend/server.py no respondio a tiempo")

        if dev:
            url = DEV_URL
        elif os.path.exists(DIST_INDEX):
            url = DIST_INDEX
        else:
            logger.warning("dist no existe; usa --dev o corre npm run build")
            url = DEV_URL

        webview.create_window(
            "Topología Optimizada",
            url=url,
            js_api=_make_bridge(base),
            width=1500,
            height=900,
        )
        webview.start(debug=dev)
    finally:
        server.terminate()


if __name__ == "__main__":
    main(dev="--dev" in sys.argv)
