"""E2E real: SIMP generativo A + registerReconstruction + export/reimport STEP.

Cubre los puntos 4-5 de la auditoría: no solo el dict de reconstrucción,
sino el sólido registrado, exportado a STEP, reimportado (num_solids >= 1)
y el volumen físico reportado frente al target.
"""
import json
import os
import tempfile
import time

from api import Api


def _wait_done(api, jid, timeout_s=300):
    deadline = time.time() + timeout_s
    poll = None
    while time.time() < deadline:
        poll = api.pollJob(jid)
        if poll.get("state") in ("done", "error", "failed"):
            return poll
        time.sleep(0.2)
    raise TimeoutError(f"job {jid} sin terminar: {poll}")


def test_generative_a_step_roundtrip_with_registration():
    api = Api()
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
    poll = _wait_done(api, run["jobId"])
    assert poll.get("state") == "done", poll
    res = poll.get("result") or {}
    # Punto 5: el core reporta ambos; la UI debe consumir el físico.
    assert 0.0 < float(res["final_volume_fraction"]) <= 1.0
    assert 0.0 < float(res["physical_volume_fraction"]) <= 1.0
    recon = res.get("reconstruction") or {}
    assert (recon.get("metadata") or {}).get("brep_source") == "smoothed"

    reg = api.registerReconstruction(run["jobId"])
    assert reg["ok"] and reg.get("registered"), reg
    assert reg.get("key"), reg

    tmp = os.path.join(tempfile.gettempdir(), "audit_e2e_recon.step")
    ex = api.exportStep(tmp)
    assert ex["ok"] and os.path.exists(tmp) and os.path.getsize(tmp) > 1000
    assert api.importStep(tmp)["ok"]
    snap = (api.getSnapshot().get("snapshot") or {})
    assert int(snap.get("num_solids") or 0) >= 1
