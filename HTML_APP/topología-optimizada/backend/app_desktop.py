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
    "deleteCondition", "undo", "redo",
    "getLicense", "pollJob", "getMeshPreview", "getSurfaceMesh",
    "getSafetySummary", "compareStudies",
    "meshQualityReport", "repairMesh", "smoothMesh", "decimateMesh", "remeshMesh",
    "beginUpload", "uploadChunk",
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

    # BRIDGE-TIMEOUTS (reversible): llamadas científicas bloqueantes
    # (fit B-Rep + export + reimport de registerReconstruction, mallados
    # Gmsh, STEP grandes) superan los 120s base y el puente devolvía
    # "TimeoutError: timed out" aunque el cálculo iba bien. Presupuesto
    # amplio solo para ellas; el polling y el resto siguen en 120s.
    _LONG_TIMEOUT = 1200.0
    _LONG_METHODS = frozenset({
        "registerReconstruction", "exportStep", "importStep",
        "importStepBytes", "generateMesh", "generateAdaptiveMesh",
        "getSurfaceMesh", "getMeshPreview", "remeshMesh",
    })

    def _call(self, method: str, *args: object) -> dict:
        data = json.dumps({"method": method, "args": list(args)}).encode("utf-8")
        req = urllib.request.Request(
            self._base, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        # BRIDGE-ROBUST (reversible): si el backend no responde (proceso caido,
        # timeout), devolver un error legible en vez de propagar la excepcion de
        # urllib (que en la UI se veia como "error de url / falta de conexion"
        # y dejaba la app sin poder seguir). Para volver atras: quitar el try.
        timeout = (self._LONG_TIMEOUT if method in self._LONG_METHODS
                   else 120.0)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                body = json.loads(res.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - el error viaja al frontend
            logger.error("backend no responde en %s: %s", method, exc)
            return {"ok": False,
                    "error": f"backend no responde ({method}): {type(exc).__name__}: {exc}"}
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
    # SERVER-OUT-LOG (reversible): antes stdout/stderr del server iban a
    # DEVNULL y una muerte del proceso (segfault/OOM en OCC/Kratos durante
    # un solve pesado) no dejaba rastro: la UI solo mostraba "connection
    # refused" y el job se perdía sin diagnóstico. Ahora quedan en
    # backend/server_stdout.log (*.log está en .gitignore). Para volver
    # atrás: stdout/stderr=subprocess.DEVNULL.
    log_path = os.path.join(_HERE, "server_stdout.log")
    log_fh = open(log_path, "w", encoding="utf-8", errors="replace")
    logger.info("backend log: %s (puerto %d)", log_path, port)
    # UNBUFFERED (reversible): sin -u, stdout a archivo es block-buffered
    # (~4-8KB) y una muerte nativa pierde las últimas líneas: justo las que
    # ubican la fase del crash. Con -u cada registro llega a disco.
    # Para volver atrás: quitar "-u".
    server = subprocess.Popen(
        [sys.executable, "-u", os.path.join(_HERE, "server.py"), str(port)],
        cwd=_HERE,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
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
        try:
            log_fh.close()
        except Exception:  # noqa: BLE001 - cierre best-effort
            pass


if __name__ == "__main__":
    main(dev="--dev" in sys.argv)
