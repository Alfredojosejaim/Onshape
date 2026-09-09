"""Suite del experimento standalone: api.py contra core_vendor + fixtures.

Corre con el .venv del proyecto original (no lo modifica, solo lo usa):
    ..\\Topologia_Optimizada\\.venv\\Scripts\\python.exe -m pytest tests/ -v
"""
import json
import os
import time

import pytest

import api

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "cono.step")


@pytest.fixture(scope="module")
def client():
    return api.Api()


def test_snapshot_initial(client):
    r = client.getSnapshot()
    assert r["ok"] and r["snapshot"]["has_mesh"] is False


def test_materials(client):
    r = client.getMaterials()
    assert r["ok"] and "steel" in r["names"]


def test_validate_problem_rejects_garbage(client):
    r = client.validateProblem(json.dumps({"nonsense": 1}))
    assert r["ok"] is False and "error" in r


def test_import_step_fixture(client):
    assert os.path.exists(FIX), "falta fixtures/prueba.step"
    r = client.importStep(FIX)
    assert r["ok"], r
    assert r["snapshot"]["model_name"] is not None


def test_generate_mesh(client):
    client.importStep(FIX)
    r = client.generateMesh(json.dumps({"target_element_size": 5.0}))
    assert r["ok"], r
    assert r["snapshot"]["has_mesh"] is True


def test_boundaries_and_preview(client):
    client.importStep(FIX)
    client.generateMesh(json.dumps({"target_element_size": 5.0}))
    b = client.setBoundaries(json.dumps(
        {"bottom_axis": 2, "load_dir": [0, 0, 1], "magnitude": 1000.0}))
    assert b["ok"], b
    p = client.getMeshPreview()
    assert p["ok"], p


def test_nav_profiles(client):
    r = client.getNavProfiles()
    assert r["ok"] and r["current"] == "autocad"
    assert {p["name"] for p in r["profiles"]} == {"autocad", "onshape", "fusion360", "blender"}
    assert client.setNavProfile("onshape")["ok"] is True
    assert client.setNavProfile("autocad")["ok"] is True
    assert client.setNavProfile("zzz")["ok"] is False


def test_surface_mesh_fields(client):
    client.importStep(FIX)
    client.generateMesh(json.dumps({"target_element_size": 5.0}))
    g = client.getSurfaceMesh(json.dumps({"field": "none"}))
    assert g["ok"], g
    assert g["num_vertices"] > 100 and g["num_triangles"] > 100
    assert g["values"] is None
    no_fea = client.getSurfaceMesh(json.dumps({"field": "vonmises"}))
    assert no_fea["ok"] is False  # sin FEA aun -> error controlado


def _wait_job(client, jid, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = client.pollJob(jid)
        assert s["ok"], s
        if s["state"] in ("done", "error"):
            return s
        time.sleep(2.0)
    raise TimeoutError(f"job {jid} sin terminar en {timeout}s")


@pytest.mark.slow
def test_run_fea_kratos_job(client):
    pytest.importorskip("KratosMultiphysics")
    client.importStep(FIX)
    client.generateMesh(json.dumps({"target_element_size": 5.0}))
    client.setBoundaries(json.dumps(
        {"bottom_axis": 2, "load_dir": [0, 0, 1], "magnitude": 1000.0}))
    r = client.runFea(json.dumps({"backend": "kratos"}))
    assert r["ok"], r
    s = _wait_job(client, r["jobId"], timeout=1500)
    assert s["state"] == "done", s
    assert s["result"]["success"] is True


@pytest.mark.slow
def test_run_fea_job(client):
    client.importStep(FIX)
    client.generateMesh(json.dumps({"target_element_size": 5.0}))
    client.setBoundaries(json.dumps(
        {"bottom_axis": 2, "load_dir": [0, 0, 1], "magnitude": 1000.0}))
    r = client.runFea(json.dumps({"backend": "local"}))
    assert r["ok"], r
    s = _wait_job(client, r["jobId"])
    assert s["state"] == "done", s
    assert s["result"] is not None
