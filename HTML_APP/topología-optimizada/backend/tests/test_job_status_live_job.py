"""E2E del JOB-STATUS: sondeo durante un job generativo REAL.

Complementa `test_job_status_bridge.py` (unitario): aquí corre el pipeline
generativo completo (`runGenerativeDesign` con solve + reconstrucción OCP) y se
sondea con el MISMO `Bridge` que usa la app, contra un puerto donde NO hay nada
escuchando — es decir, simulando exactamente el backend congelado en una llamada
nativa que retiene el GIL (prompt.md addendum 6).

Contrato que se protege: mientras el job está vivo, el sondeo NUNCA devuelve
error de transporte (antes: "backend no responde tras ~2.5 min" y la UI daba la
optimización por fallida con el cálculo sano).
"""
import json
import os
import sys
import time

import pytest

import job_status
from api import Api
from app_desktop import _make_bridge

DEAD_PORT = 9  # nada escuchando: "backend congelado" para el sondeo local


def test_poll_survives_real_job_with_unreachable_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("TOPOOPT_JOB_STATUS_DIR", str(tmp_path))
    api = Api()
    api.status_port = DEAD_PORT

    assert api.importStep("cono.step")["ok"]
    assert api.generateMesh(json.dumps({"target_element_size": 8.0}))["ok"]
    load = api.createCondition(json.dumps({
        "type": "load", "name": "L",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "orientation": "perpendicular", "reference_plane_normal": [0, 0, 1],
        "angle_deg": None, "sense": "positive", "magnitude": 1000.0,
        "indeterminate": False, "unit": "N", "metadata": {},
        "direction": [0, 0, 1],
    }))
    supp = api.createCondition(json.dumps({
        "type": "elasticity", "name": "S",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
    }))
    run = api.runGenerativeDesign(json.dumps({
        "scenario": "A", "condition_ids": [load["id"], supp["id"]],
        "volume_fraction": 0.4, "max_iterations": 3,
        "penalization": 3.0, "filter_radius": 2.0,
        "convergence_tolerance": 1e-3,
    }))
    assert run["ok"], run
    jid = run["jobId"]

    # El host ligero sondea por su cuenta, sin tocar la red.
    bridge = _make_bridge(f"http://127.0.0.1:{DEAD_PORT}/", is_alive=lambda: None)

    first = bridge.pollJob(jid)
    assert first["ok"] is True, first
    assert first["state"] == "running"
    assert first["result"] is None

    seen = 0
    progress_seen = None
    deadline = time.time() + 300
    while time.time() < deadline:
        r = bridge.pollJob(jid)
        if not r.get("ok"):
            # Un fallo de transporte solo es aceptable si el job YA terminó: en
            # ese caso el puente reenvía para traer el `result` (y contra un
            # puerto muerto el reenvío falla, como debe). Mientras el job siga
            # vivo, un fallo de sondeo es exactamente el bug reportado.
            estado = api.pollJob(jid).get("state")
            if estado in ("done", "error", "failed"):
                break
            path = job_status.status_path(DEAD_PORT)
            existe = os.path.exists(path)
            pytest.fail(f"sondeo con error durante el job (estado={estado}, "
                        f"snapshot_existe={existe}): {r}")
        assert r["state"] == "running", r
        seen += 1
        if isinstance(r.get("progress"), (int, float)) and r["progress"] > 0:
            progress_seen = r["progress"]
        if api.pollJob(jid).get("state") in ("done", "error", "failed"):
            break
        time.sleep(0.2)

    assert seen > 0
    assert progress_seen is not None, "el snapshot debe publicar progreso real"

    # El job terminó bien: el estado terminal queda publicado para el reenvío.
    # La publicación es asíncrona y best-effort (la hace el hilo del solver al
    # cerrar el future), así que se espera acotadamente a que llegue: el sondeo
    # de la UI simplemente reintenta y ve `done` un instante después.
    poll = api.pollJob(jid)
    assert poll.get("state") == "done", poll
    path = job_status.status_path(DEAD_PORT)
    deadline = time.time() + 10
    snap = None
    while time.time() < deadline:
        snap = job_status.read_snapshot(path)
        rec = ((snap or {}).get("jobs") or {}).get(jid) or {}
        if rec.get("state") == "done":
            break
        time.sleep(0.05)
    rec = ((snap or {}).get("jobs") or {}).get(jid) or {}
    assert rec.get("state") == "done", rec
    # El snapshot NO lleva el resultado (puede pesar MB): se reenvía.
    assert "result" not in rec


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
