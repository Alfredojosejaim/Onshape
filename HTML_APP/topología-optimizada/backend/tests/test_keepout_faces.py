"""Keep-out por caras + región preservada en generativa (escenario A).

Regresión del reporte: la herramienta keep-out quedaba solo local en la UI
y la optimización la ignoraba en silencio; la preservada debe mantener
rho=1 en sus elementos y el keep-out rho=xmin en los suyos.
"""
import json
import time

import numpy as np

from api import Api
from core.conditions import condition_from_dict


def _wait_done(api, jid, timeout_s=300):
    deadline = time.time() + timeout_s
    poll = None
    while time.time() < deadline:
        poll = api.pollJob(jid)
        if poll.get("state") in ("done", "error", "failed"):
            return poll
        time.sleep(0.2)
    raise TimeoutError(f"job {jid} sin terminar: {poll}")


def test_obstruction_faces_roundtrip_without_bodies():
    cond = condition_from_dict({
        "type": "obstruction", "name": "K",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": 1}], "mode": "multi"},
        "offset_mm": None, "metadata": {},
    })
    assert cond.condition_type.value == "obstruction"
    assert [int(e.face_index) for e in cond.faces.entities] == [1]
    d = cond.to_dict()
    assert d["faces"]["entities"][0]["face_index"] == 1
    assert condition_from_dict(d).faces.entities[0].face_index == 1


def test_all_faces_map_exactly_via_fse():
    """FSE-FIRST: TODA cara marcada mapea a sus nodos exactos de la malla.

    Sin depender de tolerancias geométricas ni del shape CAD: los nodos
    mapeados deben ser exactamente los de face_surface_elements.
    """
    from core.generative_engine import GenerativeDesignEngine
    from core.materials import STANDARD_MATERIALS

    api = Api()
    assert api.importStep("cono.step")["ok"]
    assert api.generateMesh(json.dumps({"target_element_size": 8.0}))["ok"]
    c = api._ctrl
    fse = c.mesh.get("face_surface_elements") or {}
    assert {"face_0", "face_1", "face_2"} <= set(fse)
    shape = c.cad.get_model_shape(c.model_id)
    for with_shape in (True, False):
        eng = GenerativeDesignEngine(
            model_id=c.model_id,
            mesh_nodes=c.mesh_nodes, mesh_elements=c.mesh_elements,
            material=c.material(), condition_manager=c.conditions,
            model_shape=shape if with_shape else None,
            face_surface_elements=fse,
        )
        for fi in (0, 1, 2):
            expected = sorted({int(n) for t in fse[f"face_{fi}"] for n in t})
            assert expected
            assert eng._select_nodes_for_faces([fi]) == expected
    # Multi-cara: unión exacta.
    eng = GenerativeDesignEngine(
        model_id=c.model_id,
        mesh_nodes=c.mesh_nodes, mesh_elements=c.mesh_elements,
        material=c.material(), condition_manager=c.conditions,
        model_shape=shape, face_surface_elements=fse)
    both = (set(int(n) for t in fse["face_0"] for n in t)
            | set(int(n) for t in fse["face_2"] for n in t))
    assert eng._select_nodes_for_faces([0, 2]) == sorted(both)


def test_keepout_faces_carve_void_and_protected_stays_solid():
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
    prot = api.createCondition(json.dumps({
        "type": "protected_region", "name": "P",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": 0}], "mode": "multi"},
        "geometry_refs": [], "metadata": {},
    }))
    keep = api.createCondition(json.dumps({
        "type": "obstruction", "name": "K",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": 2}], "mode": "multi"},
        "offset_mm": None, "metadata": {},
    }))
    for c in (load, supp, prot, keep):
        assert c.get("ok", True) and c.get("id"), c
    run = api.runGenerativeDesign(json.dumps({
        "scenario": "A",
        "condition_ids": [load["id"], supp["id"], prot["id"], keep["id"]],
        "volume_fraction": 0.4, "max_iterations": 3,
        "penalization": 3.0, "filter_radius": 2.0,
        "convergence_tolerance": 1e-3,
    }))
    assert run["ok"], run
    poll = _wait_done(api, run["jobId"])
    assert poll.get("state") == "done", poll
    res = poll.get("result") or {}
    assert res.get("_consumed_obstruction_conditions") == 1
    assert res.get("_consumed_protected_conditions") == 1
    assert "obstruction" not in res.get("_unsupported_conditions", [])

    nodes = np.asarray(api._ctrl.mesh_nodes, dtype=float)
    els = np.asarray(api._ctrl.mesh_elements, dtype=int)
    fse = api._ctrl.mesh.get("face_surface_elements") or {}
    assert "face_0" in fse and "face_2" in fse
    n0 = {int(n) for t in fse["face_0"] for n in t}
    n2 = {int(n) for t in fse["face_2"] for n in t}
    assert n0 and n2
    touch0 = {e for e in range(len(els)) if set(els[e].tolist()) & n0}
    touch2 = {e for e in range(len(els)) if set(els[e].tolist()) & n2}
    # Las caras comparten nodos de borde: el solape queda en vacío porque el
    # void se aplica después del preserved en el solver.
    e_prot = touch0 - touch2
    e_void = touch2  # incluye el solape (void gana)
    assert e_prot and e_void
    x = np.asarray(res["densities"], dtype=float)
    assert np.all(np.isfinite(x))
    assert all(x[e] == 1.0 for e in e_prot)
    assert all(x[e] <= 0.01 for e in e_void)
    assert "reconstruction" in res
    # MAP-REPORT: cada condición informa caras pedidas vs mapeo real.
    mapping = {m["type"]: m for m in res.get("_condition_mapping", [])}
    assert mapping["protected_region"]["faces"] == [0]
    assert mapping["protected_region"]["mapped_elements"] > 0
    assert mapping["protected_region"]["fallback"] is False
    assert mapping["obstruction"]["faces"] == [2]
    assert mapping["obstruction"]["mapped_elements"] > 0
    assert mapping["obstruction"]["fallback"] is False
