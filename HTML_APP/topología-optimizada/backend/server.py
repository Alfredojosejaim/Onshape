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

from http.server import BaseHTTPRequestHandler, HTTPServer

from api import Api

_API = Api()


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
            fn = getattr(_API, str(req.get("method", "")))
            args = req.get("args", [])
            if not isinstance(args, list):
                args = [args]
            payload = {"ok": True, "result": fn(*args)}
        except Exception as exc:  # noqa: BLE001
            payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
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
    HTTPServer(("127.0.0.1", port), _Handler).serve_forever()
