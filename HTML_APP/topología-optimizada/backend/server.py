"""Servidor local del backend pesado (proceso aislado).

El Api real importa VTK/Qt(OCC/Kratos) cuyas DLL nativas corrompen el heap
(0xc0000374) si conviven con WebView2/.NET en el mismo proceso. Por eso el
Api vive aqui, en un subprocess, y la ventana pywebview solo usa un Bridge
ligero (stdlib) que reenvia por HTTP a 127.0.0.1. Sin navegador externo.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

from api import Api

_API = Api()

# PROMPT-FIX (reversible): whitelist de metodos permitidos. Espejo de
# _METHODS en app_desktop.py: solo estos nombres pueden resolverse via
# getattr. Cualquier otro se rechaza limpiamente sin tocar el Api.
ALLOWED_METHODS = frozenset({
    "getSnapshot", "getMaterials", "setMaterial", "validateProblem",
    "importStep", "importStepBytes", "listFixtures", "listLibrary",
    "switchModel", "removeModel", "getSolids", "generateMesh",
    "generateAdaptiveMesh", "setBoundaries", "runFea", "runFeaIterative",
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
})


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
            method = str(req.get("method", ""))
            if method not in ALLOWED_METHODS:
                payload = {"ok": False, "error": f"ValueError: metodo no permitido: {method!r}"}
            else:
                fn = getattr(_API, method)
                args = req.get("args", [])
                if not isinstance(args, list):
                    args = [args]
                payload = {"ok": True, "result": fn(*args)}
        except Exception as exc:  # noqa: BLE001
            payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            # SERVER-LOG (reversible): dejar rastro del fallo en disco. Si el
            # proceso muere por DLL nativa, este log es lo unico que sobrevive
            # para diagnosticar (antes solo se veia "url/conexion" en la UI).
            try:
                with open(os.path.join(_HERE, "server_error.log"), "a",
                          encoding="utf-8") as _fh:
                    _fh.write(f"method={locals().get('method')!r} "
                              f"exc={type(exc).__name__}: {exc}\n")
                    _fh.write(traceback.format_exc())
                    _fh.write("-" * 60 + "\n")
            except Exception:  # noqa: BLE001
                pass
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    # HTTPServer MONO-HILO (reversible/obligatorio): Gmsh usa `signal`, que
    # solo funciona en el hilo principal. Con ThreadingHTTPServer los handlers
    # corren en hilos y `generateMesh` fallaba con "signal only works in main
    # thread", cayendo al ProvisionalTet4Mesher (malla NO conforme) -> BCs
    # degradadas y resultado colapsado (85 cm3 -> 1.7 cm3). NO volver a
    # ThreadingHTTPServer sin sacar gmsh del handler. Ver server_error.log.
    HTTPServer(("127.0.0.1", port), _Handler).serve_forever()
