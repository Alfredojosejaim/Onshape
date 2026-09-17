"""JOB-STATUS: el sondeo sobrevive a un backend bloqueado en código nativo.

Regresión del falso "La optimización terminó con error: backend no responde
tras ~2.5 min" (prompt.md addendum 6): durante la reconstrucción B-Rep el
proceso pesado retiene el GIL en llamadas OCP de varios segundos y no puede
atender `pollJob` aunque el job siga vivo.

Mecanismo bajo prueba:
1. `Api._publish_jobs` publica estado/progreso mínimo (sin `result`) en
   `job_status_<puerto>.json`; los callbacks de progreso lo refrescan.
2. `Bridge.pollJob` (host ligero, otro proceso) responde mientras el estado sea
   `running` LEYENDO ese archivo: no toca la red, así que funciona aunque el
   backend esté congelado. Con estado terminal reenvía (el `result` vive allí).
3. Si el proceso murió, se informa igual (fail-loud, nunca "ocupado" eterno).
"""
import sys
import time

import pytest

import job_status
from api import Api
from app_desktop import _make_bridge

PORT = 9  # puerto sin nada escuchando: la vía rápida NO debe necesitar red


@pytest.fixture()
def status_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TOPOOPT_JOB_STATUS_DIR", str(tmp_path))
    return tmp_path


def _publish(jobs, port=PORT):
    assert job_status.write_snapshot(job_status.status_path(port), jobs, port=port)


def _bridge(is_alive=None):
    return _make_bridge(f"http://127.0.0.1:{PORT}/", is_alive=is_alive)


def test_running_job_answered_locally_without_network(status_dir):
    """Backend bloqueado (puerto muerto) + snapshot running = sigue sondeando."""
    _publish({"gen_1": {"state": "running", "progress": 0.42, "error": None}})
    r = _bridge(is_alive=lambda: None).pollJob("gen_1")
    assert r["ok"] is True
    assert r["state"] == "running"
    assert r["progress"] == 0.42
    assert r["result"] is None
    assert not r.get("stale")  # recién publicado: avance fresco


def test_stale_running_job_is_flagged_not_failed(status_dir):
    """Sin publicar avance > umbral: aviso `stale`, nunca error."""
    _publish({"gen_1": {"state": "running", "progress": 0.9, "error": None}})
    # Envejecer el snapshot (el backend está dentro de una llamada nativa).
    path = job_status.status_path(PORT)
    data = job_status.read_snapshot(path)
    data["written"] = time.time() - 120.0
    import json
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)

    r = _bridge(is_alive=lambda: None).pollJob("gen_1")
    assert r["ok"] is True and r["state"] == "running"
    assert r.get("stale") is True
    assert r["stale_sec"] >= 100.0


def test_running_job_with_dead_process_reports_exit_code(status_dir):
    """Proceso muerto durante el job: fail-loud, no "ocupado" eterno."""
    _publish({"gen_1": {"state": "running", "progress": 0.5, "error": None}})
    r = _bridge(is_alive=lambda: -1073741819).pollJob("gen_1")
    assert r["ok"] is False
    assert "el proceso backend terminó" in r["error"]
    assert "-1073741819" in r["error"]


def test_failed_job_answered_locally_with_real_error(status_dir):
    """Estado terminal de error: el detalle llega sin reenviar (backend ocupado)."""
    _publish({"gen_1": {"state": "error", "progress": 0.5,
                        "error": "RuntimeError: isosuperficie abierta"}})
    r = _bridge(is_alive=lambda: None).pollJob("gen_1")
    assert r["ok"] is True and r["state"] == "error"
    assert "isosuperficie abierta" in r["error"]


def test_done_job_is_forwarded_for_full_result(status_dir):
    """`done` se reenvía: el resultado completo solo existe en el backend."""
    _publish({"gen_1": {"state": "done", "progress": 1.0, "error": None}})
    r = _bridge(is_alive=lambda: None).pollJob("gen_1")
    # Puerto 9: nada escucha -> viaja el fallo de transporte, no un done vacío.
    assert r["ok"] is False
    assert "backend" in r["error"]


def test_unknown_job_without_snapshot_uses_normal_path(status_dir):
    _publish({"otro": {"state": "running", "progress": 0.1, "error": None}})
    r = _bridge(is_alive=lambda: None).pollJob("no_existe")
    assert r["ok"] is False
    assert "backend" in r["error"]


def test_api_publishes_snapshot_without_result(status_dir):
    """El Api publica estado/progreso mínimo y jamás el `result` (pesado)."""
    api = Api()
    api.status_port = PORT
    jid = api._submit("test", lambda: {"datos": list(range(1000))})
    # Esperar a que termine (job trivial) y ver el estado terminal publicado.
    for _ in range(200):
        rec = job_status.read_snapshot(job_status.status_path(PORT)) or {}
        job = (rec.get("jobs") or {}).get(jid) or {}
        if job.get("state") == "done":
            break
        time.sleep(0.05)

    assert job.get("state") == "done"
    assert job.get("progress") == 1.0
    assert "result" not in job
    assert "datos" not in str(job)


def test_api_without_port_does_not_publish(status_dir):
    """Sin puerto asignado (tests/CLI) el Api no escribe nada."""
    api = Api()
    assert api.status_port is None
    api._publish_jobs()
    assert job_status.read_snapshot(job_status.status_path(PORT)) is None


def test_read_snapshot_survives_concurrent_publishers(status_dir):
    """WINDOWS-REPLACE: publicar mientras se lee no debe dar "sin snapshot".

    Regresión real: `open` falla transitoriamente con PermissionError durante el
    `os.replace` del publicador (medido: 381 fallos en 3 s con 3 publicadores y 3
    lectores). Sin reintentos el lector lo tomaba por "no hay snapshot", caía al
    camino HTTP y con el backend ocupado volvía el falso "backend no responde"
    (así falló esta suite antes del arreglo: `105 passed, 1 failed`).
    """
    import threading

    path = job_status.status_path(PORT)
    _publish({"gen_1": {"state": "running", "progress": 0.1, "error": None}})
    stop = threading.Event()
    faltantes = []

    def publisher():
        i = 0
        while not stop.is_set():
            _publish({"gen_1": {"state": "running", "progress": i % 100 / 100.0,
                                "error": None}})
            i += 1

    def reader():
        while not stop.is_set():
            snap = job_status.read_snapshot(path)
            if snap is None or "gen_1" not in (snap.get("jobs") or {}):
                faltantes.append(1)

    hilos = [threading.Thread(target=publisher) for _ in range(2)]
    hilos += [threading.Thread(target=reader) for _ in range(2)]
    for h in hilos:
        h.start()
    tiempo_limite = time.time() + 1.5
    while time.time() < tiempo_limite:
        time.sleep(0.05)
    stop.set()
    for h in hilos:
        h.join()

    assert not faltantes, f"{len(faltantes)} lecturas sin snapshot válido"


def test_transient_read_failure_uses_last_valid_snapshot(status_dir):
    """SNAP-CACHE: un fallo de lectura no debe devolver "backend no responde".

    En Windows el publicador reemplaza el archivo y `open` puede fallar
    transitoriamente; con el backend ocupado ese fallo caía al camino HTTP y
    reaparecía el falso error. El puente responde con el último snapshot válido
    y la edad sigue calculándose de su marca `written`.
    """
    import json

    path = job_status.status_path(PORT)
    _publish({"gen_1": {"state": "running", "progress": 0.3, "error": None}})
    # Envejecer el snapshot ANTES de sondear: el cache guarda esa marca.
    data = job_status.read_snapshot(path)
    data["written"] = time.time() - 90.0
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)

    bridge = _bridge(is_alive=lambda: None)
    first = bridge.pollJob("gen_1")
    assert first["ok"] is True and first["progress"] == 0.3
    assert first.get("stale") is True  # 90 s sin publicar avance

    # Ahora se rompe la lectura (ventana de reemplazo): debe seguir contestando
    # con el último snapshot válido, no caer al camino HTTP.
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{no es json")

    r = bridge.pollJob("gen_1")
    assert r["ok"] is True and r["state"] == "running", r
    assert r["progress"] == 0.3  # viene del cache
    assert r.get("stale") is True
    assert r["stale_sec"] >= first["stale_sec"] - 1.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
