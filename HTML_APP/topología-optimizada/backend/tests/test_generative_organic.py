"""Envelope: filtro auto + skin de vacío => sólido cerrado y reconstruible.

Regresión de dos reportes: "envelope hace cajas/fragmenta" (filter_radius
menor que el voxel => checkerboard) y "el envelope no cierra STEP" (el
material crecía hasta la pared de la caja y el isosuperficie quedaba ABIERTO;
la reconstrucción B-Rep fallaba). El envelope ahora sube el filtro a
1.5×voxel, propaga heaviside_eta y fuerza una capa de vacío en la pared
(void_skin) para garantizar superficie cerrada.
"""
import json
import time

import numpy as np

from api import Api


def _run_envelope(api, cond_ids, extra):
    params = {"scenario": "A", "condition_ids": cond_ids,
              "volume_fraction": 0.35, "max_iterations": 8,
              "penalization": 3.0, "filter_radius": 2.5,
              "convergence_tolerance": 1e-3,
              "design_space": "envelope"}
    params.update(extra)
    run = api.runGenerativeDesign(json.dumps(params))
    assert run["ok"], run
    poll = None
    for _ in range(1800):
        poll = api.pollJob(run["jobId"])
        if poll.get("state") in ("done", "error", "failed"):
            break
        time.sleep(0.5)
    assert poll.get("state") == "done", poll
    return poll.get("result") or {}


def test_envelope_closes_solid_with_void_skin_and_autotunes_filter():
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
    ids = [load["id"], supp["id"]]

    res = _run_envelope(api, ids, {})
    meta = res.get("_design_space") or {}
    assert meta.get("design_space") == "envelope"
    # El filtro pedido (2.5) era menor que el voxel: sube a 1.5×res.
    assert meta.get("filter_auto") is True
    assert meta["filter_radius"] >= 1.5 * meta["resolution"] - 1e-9
    # ENV-SKIN: hay capa de vacío en la pared del dominio.
    assert int(meta.get("void_skin_elements") or 0) > 0
    x = np.asarray(res["densities"], dtype=float)
    assert x.size > 0 and np.all(np.isfinite(x))
    # La reconstrucción debe llegar a sólido B-Rep (superficie cerrada),
    # no quedarse en surface_mesh con error de isosuperficie abierta.
    rec = res.get("reconstruction") or {}
    assert rec.get("stage") == "brep_solid", (rec.get("stage"),
                                              rec.get("brep_error"))
    assert not rec.get("brep_error")
