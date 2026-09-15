"""Regresión UNDO-REDO (reversible): deleteCondition/removeModel con
deshacer/rehacer a nivel Api (sin CAD: condiciones + entrada simulada).
"""
import json

from api import Api


def _load_dict(name="L1"):
    return {
        "type": "load", "name": name,
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "orientation": "perpendicular", "reference_plane_normal": [0, 0, 1],
        "angle_deg": None, "sense": "positive", "magnitude": 100.0,
        "indeterminate": False, "unit": "N", "metadata": {},
        "direction": [0, 0, 1],
    }


def test_delete_condition_undo_redo():
    api = Api()
    c = api.createCondition(json.dumps(_load_dict()))
    assert c["ok"]
    cid = c["id"]
    d = api.deleteCondition(cid)
    assert d["ok"] and d["conditions"] == []
    assert d["canUndo"] is not None
    assert api.deleteCondition(cid)["ok"] is False
    u = api.undo()
    assert u["ok"] and [x["id"] for x in u["conditions"]] == [cid]
    r = api.redo()
    assert r["ok"] and r["conditions"] == []
    assert api.undo()["ok"] is True
    assert api.redo()["ok"] is True


def test_remove_model_undo_redo():
    api = Api()
    api._library["k1"] = {"filename": "a.step", "displayName": "A",
                          "path": "/no/existe/a.step"}
    api._active_key = "k1"
    rm = api.removeModel("k1")
    assert rm["ok"] and rm["library"] == [] and rm["activeKey"] is None
    u = api.undo()
    assert u["ok"] and [e["key"] for e in u["library"]] == ["k1"]
    # La ruta no existe: entra pero no puede activarse (honesto, sin malla).
    assert u["activeKey"] is None
    r = api.redo()
    assert r["ok"] and r["library"] == []
