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
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# JOB-STATUS (reversible): snapshot de jobs que publica el proceso pesado
# (backend/job_status.py, stdlib puro). Este host NO importa VTK/OCC/Kratos, asi
# que puede leerlo aunque el backend este bloqueado en una llamada nativa.
# Para volver atrás: quitar este import + Bridge._job_snapshot/pollJob.
import job_status  # noqa: E402  (depende del sys.path de arriba)

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


# JOB-STATUS (reversible): segundos sin publicar avance a partir de los cuales
# el sondeo local marca `stale` (el backend está dentro de una llamada nativa
# larga). Es un AVISO, nunca un fallo. Para volver atrás: 10**9.
_STALE_AFTER_S = 45.0


class Bridge:
    """Forwarder ligero: cada metodo POSTea al server.py y devuelve el dict."""

    def __init__(self, base_url: str, is_alive=None) -> None:
        self._base = base_url
        # DEAD-SERVER (reversible): callable que devuelve None si el proceso
        # server.py sigue vivo o su exit code si terminó. Permite distinguir
        # "proceso muerto (crash nativo/OOM)" de "proceso ocupado". Para
        # volver atrás: __init__(self, base_url) e is_alive=None siempre.
        self._is_alive = is_alive
        # JOB-STATUS (reversible): puerto del backend -> ruta del snapshot de
        # jobs. Para volver atrás: quitar este bloque y _job_snapshot/pollJob.
        try:
            from urllib.parse import urlsplit
            self._port = urlsplit(base_url).port
        except Exception:  # noqa: BLE001 - sin puerto no hay via rapida
            self._port = None
        # Ultimo snapshot de jobs leido con exito (ver _job_snapshot).
        self._last_snap = None

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
            # DEAD-SERVER (reversible): connection refused = nada escucha en
            # el puerto = el proceso server.py murió (crash nativo/OOM: no
            # deja traceback, solo se corta server_stdout.log). Antes viajaba
            # el texto crudo de urllib ("WinError 10061") y la UI no podía
            # distinguirlo de un timeout con el proceso ocupado. Para volver
            # atrás: devolver siempre el mensaje genérico de abajo.
            dead_code = None
            refused = (isinstance(exc, ConnectionRefusedError)
                       or "10061" in str(exc) or "refused" in str(exc).lower())
            if refused:
                try:
                    dead_code = self._is_alive() if self._is_alive else "desconocido"
                except Exception:  # noqa: BLE001 - best-effort
                    dead_code = "desconocido"
                if dead_code is None:
                    # Proceso VIVO pero no acepta: handler bloqueante (register/
                    # export, minutos) con la cola llena. No es un fallo del
                    # job: la UI debe seguir sondeando (ver jobs.ts).
                    return {"ok": False,
                            "error": f"backend ocupado (proceso vivo, {method} en curso) — reintentando sondeo"}
                return self._dead_payload(method, dead_code)
            return {"ok": False,
                    "error": f"backend no responde ({method}): {type(exc).__name__}: {exc}"}
        if isinstance(body, dict) and body.get("ok") and "result" in body:
            result = body["result"]
            return result if isinstance(result, dict) else {"ok": True, "value": result}
        return body if isinstance(body, dict) else {"ok": False, "error": str(body)}

    # -- JOB-STATUS (reversible): sondeo sin depender del GIL del backend ----
    def _dead_payload(self, method: str, exit_code) -> dict:
        """Error accionable cuando el proceso backend ya no existe."""
        return {"ok": False,
                "error": f"el proceso backend terminó (exit {exit_code}) durante {method}. "
                         "Crash nativo u OOM probable: revisa backend/server_stdout.log "
                         "(últimas líneas) y backend/server_error.log. El job en curso se perdió; "
                         "reabre la app y reintenta con malla más gruesa si se repite."}

    def _process_exit_code(self):
        """None si el proceso sigue vivo; su exit code si terminó."""
        if self._is_alive is None:
            return None
        try:
            return self._is_alive()
        except Exception:  # noqa: BLE001 - best-effort
            return None

    def _job_snapshot(self, job_id: str):
        """(registro, edad_s) del job publicado por el backend, o None.

        SNAP-CACHE (reversible): si una lectura falla (en Windows el publicador
        reemplaza el archivo y `open` puede dar PermissionError transitorio
        aunque se reintente), se responde con el ULTIMO snapshot valido. La edad
        se calcula de la marca `written` que trae el propio snapshot, asi que
        sigue creciendo con el tiempo real y la señal `stale` no se falsea. Sin
        esto, un fallo de lectura caia al camino HTTP y con el backend ocupado
        reaparecia el falso "backend no responde". Para volver atrás: quitar
        `_last_snap` y devolver None cuando la lectura falla.
        """
        snap = None
        if self._port:
            try:
                snap = job_status.read_snapshot(job_status.status_path(self._port))
            except Exception:  # noqa: BLE001 - se usa el cache
                snap = None
        if snap is None:
            snap = self._last_snap
        else:
            self._last_snap = snap
        if not snap:
            return None
        rec = (snap.get("jobs") or {}).get(job_id)
        if not isinstance(rec, dict):
            return None
        return rec, job_status.snapshot_age(snap)

    def pollJob(self, job_id: str) -> dict:
        """Sondeo del job con vía rápida local (JOB-STATUS).

        El backend pesado publica estado/progreso en `job_status_<puerto>.json`
        mientras el job avanza. Mientras siga `running` se contesta con ese
        snapshot: el backend puede estar dentro de una llamada nativa con el GIL
        retenido (reconstrucción B-Rep/OCP, minutos) sin poder atender HTTP, y
        eso NO es un fallo — antes la UI lo interpretaba como "la optimización
        terminó con error" con el cálculo sano (prompt.md addendum 6).

        Con estado terminal se reenvía al backend: el `result` completo solo
        existe allí (y en ese momento el proceso ya está libre). Si no hay
        snapshot (arranque, test, sesión vieja) todo sigue por el camino normal.
        Para volver atrás: `def pollJob(self, job_id): return self._call("pollJob", job_id)`.
        """
        snap = self._job_snapshot(str(job_id))
        if snap is not None:
            rec, age = snap
            state = rec.get("state")
            if state == "running":
                dead = self._process_exit_code()
                if dead is not None:
                    return self._dead_payload("pollJob", dead)
                out = {"ok": True, "state": "running",
                       "progress": rec.get("progress"), "result": None,
                       "error": None}
                if age is not None and age > _STALE_AFTER_S:
                    # Señal honesta: el backend no publica avance (llamada
                    # nativa larga). No es error: la UI avisa y sigue sondeando.
                    out["stale"] = True
                    out["stale_sec"] = round(float(age), 1)
                return out
            if state in ("error", "failed"):
                return {"ok": True, "state": state,
                        "progress": rec.get("progress"), "result": None,
                        "error": rec.get("error") or "el job terminó con error"}
        return self._call("pollJob", job_id)


def _make_bridge(base_url: str, is_alive=None) -> Bridge:
    bridge = Bridge(base_url, is_alive=is_alive)

    def _wrap(name: str):
        def _fn(*args: object) -> dict:
            return bridge._call(name, *args)
        _fn.__name__ = name
        return _fn

    for _name in _METHODS:
        # JOB-STATUS (reversible): `pollJob` NO se envuelve: tiene método propio
        # con vía rápida local (snapshot) para no depender del GIL del backend.
        # Para volver atrás: quitar el `if` (el wrapper genérico lo cubría).
        if _name == "pollJob":
            continue
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
            # DEAD-SERVER: server.poll() -> None (vivo) o exit code (muerto).
            js_api=_make_bridge(base, is_alive=server.poll),
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
