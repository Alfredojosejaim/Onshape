"""Estado minimo de los jobs, compartido entre procesos (stdlib puro).

Motivo (medido, ver `docs`/`prompt.md` addendum 6): el servidor HTTP
(`server.py`) y el `Api` pesado viven en el MISMO proceso, y la reconstruccion
B-Rep (OpenCASCADE via OCP, pybind11 sin `gil_scoped_release`) retiene el GIL
en llamadas nativas de varios segundos. Durante ese tramo el proceso NO puede
atender `pollJob` aunque el job siga avanzando: la UI agotaba su presupuesto de
reintentos y declaraba "La optimizacion termino con error" con el calculo sano
(la corrida del log termino bien 3.5 min despues del falso error).

Solucion: el proceso pesado publica aqui el estado minimo de cada job, y el
host de la UI (`app_desktop.py`, OTRO proceso stdlib que nunca importa
VTK/OCC/Kratos) responde `pollJob` leyendo este archivo. Asi el sondeo no
depende del GIL del proceso que calcula.

Que NO viaja aqui: el `result` del job (puede pesar MB y no hace falta para
saber si avanza). Cuando el job llega a estado terminal, el puente reenvia el
sondeo al proceso pesado -ya libre- para traer el resultado completo.

Archivo atomico (`tmp` + `os.replace`) para que el lector nunca vea un JSON a
medias. Stdlib puro a proposito: este modulo tambien lo importa el host ligero.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))

# Reintentos de lectura: en Windows reemplazar el archivo puede dejar una
# ventana en la que el nombre no existe, y el lector no debe confundirla con
# "no hay snapshot".
_READ_ATTEMPTS = 4
_READ_DELAY_S = 0.02


def status_dir() -> str:
    """Directorio del archivo de estado.

    `TOPOOPT_JOB_STATUS_DIR` permite a los tests usar un `tmp_path` y no
    ensuciar el arbol (mismo criterio que `TOPOOPT_UPLOADS` en `api.py`).
    """
    return os.environ.get("TOPOOPT_JOB_STATUS_DIR") or _HERE


def status_path(port: int) -> str:
    """Ruta del snapshot para un puerto concreto (una app = un puerto)."""
    return os.path.join(status_dir(), f"job_status_{int(port)}.json")


def write_snapshot(path: str, jobs: Dict[str, Dict[str, Any]],
                   port: Optional[int] = None) -> bool:
    """Publica el snapshot. Nunca lanza: el calculo no depende de esto.

    Dos publicadores simultaneos son normales (hilo del solver publicando
    progreso + hilo HTTP creando otro job), asi que el temporal es UNICO por
    escritura: con un nombre fijo compartirian el mismo archivo de trabajo y el
    `os.replace` podria publicar un JSON a medias. Para volver atrás: nombre fijo.
    """
    payload = {
        "written": time.time(),
        "port": int(port) if port else None,
        "jobs": jobs,
    }
    tmp = f"{path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return True
    except Exception:  # noqa: BLE001 - publicar estado es best-effort
        try:
            os.remove(tmp)
        except Exception:  # noqa: BLE001
            pass
        return False


def read_snapshot(path: str, attempts: int = _READ_ATTEMPTS) -> Optional[Dict[str, Any]]:
    """Lee el snapshot. Devuelve None si no existe o esta corrupto.

    WINDOWS-REPLACE (obligatorio): mientras otro hilo/proceso publica, `open`
    puede fallar transitoriamente con PermissionError (violacion de comparticion
    durante `os.replace`; medido: 381 fallos en 3 s con 3 publicadores y 3
    lectores) o el nombre puede faltar un instante. Sin reintentos el lector lo
    tomaba como "no hay snapshot", caia al camino HTTP y con el backend ocupado
    eso volvia a parecer "backend no responde". Para volver atrás: attempts=1.
    """
    for intento in range(max(1, int(attempts))):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # noqa: BLE001 - ausente/parcial = reintentar
            if intento + 1 < max(1, int(attempts)):
                time.sleep(_READ_DELAY_S)
                continue
            return None
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
            if intento + 1 < max(1, int(attempts)):
                time.sleep(_READ_DELAY_S)
                continue
            return None
        return data
    return None


def snapshot_age(data: Dict[str, Any]) -> Optional[float]:
    """Segundos desde la ultima publicacion (None si no hay marca valida).

    Es la senal de "sigue avanzando": si el proceso pesado queda dentro de una
    llamada nativa larga no puede publicar, y la edad crece aunque el job este
    vivo (por eso se usa para avisar, no para fallar).
    """
    try:
        return max(0.0, time.time() - float(data["written"]))
    except Exception:  # noqa: BLE001
        return None


def cleanup_stale(keep_path: str, max_age_s: float = 86400.0) -> int:
    """Borra snapshots de otras sesiones ya muertas (litter de cada arranque).

    Una app = un puerto = un archivo. El archivo propio se conserva siempre.
    Solo se borran los ajenos mas viejos que `max_age_s`: una sesion viva
    republica al lanzar cualquier job, asi que su archivo nunca queda viejo
    mientras tenga trabajo en curso. Devuelve cuantos borro.
    """
    borrados = 0
    try:
        d = os.path.dirname(keep_path) or "."
        keep = os.path.abspath(keep_path)
        for name in os.listdir(d):
            if not (name.startswith("job_status_") and name.endswith(".json")):
                continue
            full = os.path.abspath(os.path.join(d, name))
            if full == keep:
                continue
            try:
                if time.time() - os.path.getmtime(full) > max_age_s:
                    os.remove(full)
                    borrados += 1
            except Exception:  # noqa: BLE001 - best-effort
                continue
    except Exception:  # noqa: BLE001 - best-effort
        return borrados
    return borrados
