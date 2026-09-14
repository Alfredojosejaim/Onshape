"""Fase B (mallas): herramientas expuestas en el Api real.

Tetraedro cerrado via importStepBytes (base64 .stl) -> quality / repair /
smooth / decimate / remesh + validaciones fail-loud + preview vigente.
"""

import base64
import json
import struct

import pytest

from api import Api

TET_V = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
TET_T = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


def _tet_stl() -> bytes:
    buf = bytearray(84 + 50 * len(TET_T))
    struct.pack_into("<I", buf, 80, len(TET_T))
    for i, (a, b, c) in enumerate(TET_T):
        struct.pack_into("<12fH", buf, 84 + 50 * i,
                         0, 0, 1, *TET_V[a], *TET_V[b], *TET_V[c], 0)
    return bytes(buf)


@pytest.fixture(scope="module")
def api_with_tet():
    api = Api()
    payload = json.dumps({"filename": "tet.stl",
                          "base64": base64.b64encode(_tet_stl()).decode()})
    r = api.importStepBytes(payload)
    assert r["ok"] is True, r
    return api


def test_quality_reports_closed_tet(api_with_tet):
    r = api_with_tet.meshQualityReport("{}")
    assert r["ok"] is True, r
    rep = r["report"]
    assert rep["triangles"] == 4
    # Crudo (soup STL sin soldar): todo borde -> abierto. Es lo que debe
    # detectar; tras repairMesh debe cerrar.
    assert rep["open"] is True and rep["boundary_loops"] > 0
    assert abs(rep["volume"] - 1.0 / 6.0) < 1e-9


def test_repair_welds_soup(api_with_tet):
    r = api_with_tet.repairMesh("{}")
    assert r["ok"] is True, r
    assert r["stats"]["triangles_after"] == 4
    assert r["stats"]["vertices_welded"] == 8  # 12 soup -> 4
    assert r["mesh"]["triangles"] == 4
    # Tras soldar, el tetra cierra (0 loops de borde).
    rep = api_with_tet.meshQualityReport("{}")["report"]
    assert rep["open"] is False and rep["boundary_loops"] == 0
    assert rep["non_manifold_edges"] == 0


def _grid_cube_stl(n: int = 4) -> bytes:
    """Cubo subdividido n x n por cara (6*2*n*n tris) para decimar."""
    verts, tris = [], []
    def quad(p00, p10, p11, p01):
        base = len(verts)
        for iu in range(n + 1):
            for iv in range(n + 1):
                u, v = iu / n, iv / n
                verts.append(tuple(p00[i] * (1 - u) * (1 - v)
                                   + p10[i] * u * (1 - v)
                                   + p11[i] * u * v
                                   + p01[i] * (1 - u) * v for i in range(3)))
        for iu in range(n):
            for iv in range(n):
                a = base + iu * (n + 1) + iv
                b = base + (iu + 1) * (n + 1) + iv
                tris.append((a, a + 1, b))
                tris.append((b, a + 1, b + 1))
    c = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
         (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    quad(c[0], c[1], c[2], c[3]); quad(c[4], c[5], c[6], c[7])
    quad(c[0], c[1], c[5], c[4]); quad(c[2], c[3], c[7], c[6])
    quad(c[0], c[3], c[7], c[4]); quad(c[1], c[2], c[6], c[5])
    buf = bytearray(84 + 50 * len(tris))
    struct.pack_into("<I", buf, 80, len(tris))
    for i, (a, b, c_) in enumerate(tris):
        struct.pack_into("<12fH", buf, 84 + 50 * i,
                         0, 0, 1, *verts[a], *verts[b], *verts[c_], 0)
    return bytes(buf)


def test_smooth_decimate_remesh(api_with_tet):
    r = api_with_tet.smoothMesh(json.dumps({"iterations": 2, "alpha": 0.5}))
    assert r["ok"] is True, r
    assert r["mesh"]["triangles"] == 4
    # Decimar el tetra (4 tris) se rechaza explicito; con malla real reduce.
    r = api_with_tet.decimateMesh(json.dumps({"target_fraction": 0.5}))
    assert r["ok"] is False and "toda la malla" in r["error"]
    payload = json.dumps({"filename": "grid.stl",
                          "base64": base64.b64encode(_grid_cube_stl()).decode()})
    assert api_with_tet.importStepBytes(payload)["ok"] is True
    before = api_with_tet.meshQualityReport("{}")["report"]["triangles"]
    assert before == 192
    r = api_with_tet.decimateMesh(json.dumps({"target_fraction": 0.5}))
    assert r["ok"] is True, r
    assert r["mesh"]["triangles"] < before
    # Remalla sobre el tetra: re-importa para partir de 4 tris.
    payload = json.dumps({"filename": "tet2.stl",
                          "base64": base64.b64encode(_tet_stl()).decode()})
    assert api_with_tet.importStepBytes(payload)["ok"] is True
    r = api_with_tet.remeshMesh(json.dumps({"target_length": 0.5,
                                            "iterations": 1}))
    assert r["ok"] is True, r
    assert r["mesh"]["triangles"] >= 4
    # El preview sigue vigente tras las operaciones.
    pv = api_with_tet.getMeshPreview()
    assert pv["ok"] is True and pv["snapshot"]["has_mesh"] in (True, False)


def test_tools_reject_bad_params(api_with_tet):
    assert api_with_tet.smoothMesh(
        json.dumps({"iterations": 0}))["ok"] is False
    assert api_with_tet.smoothMesh(
        json.dumps({"alpha": 5.0}))["ok"] is False
    assert api_with_tet.decimateMesh(
        json.dumps({"target_fraction": 2.0}))["ok"] is False
    assert api_with_tet.decimateMesh(
        json.dumps({"target_triangles": 0}))["ok"] is False
    assert api_with_tet.remeshMesh("{}")["ok"] is False
    assert api_with_tet.remeshMesh(
        json.dumps({"target_length": -1.0}))["ok"] is False
    assert api_with_tet.repairMesh(
        json.dumps({"weld_tolerance_decimals": 99}))["ok"] is False


def test_tools_reject_without_mesh_model():
    api = Api()
    assert api.meshQualityReport("{}")["ok"] is False
    assert api.repairMesh("{}")["ok"] is False


def test_chunked_upload_roundtrip():
    import base64 as _b64
    import json as _json
    api = Api()
    raw = _tet_stl()
    b = api.beginUpload(_json.dumps({"filename": "chunk.stl"}))
    assert b["ok"] is True, b
    uid = b["upload_id"]
    half = len(raw) // 2
    c1 = api.uploadChunk(_json.dumps({"upload_id": uid,
                                      "base64": _b64.b64encode(raw[:half]).decode(),
                                      "last": False}))
    assert c1["ok"] is True and c1["received"] == half, c1
    c2 = api.uploadChunk(_json.dumps({"upload_id": uid,
                                      "base64": _b64.b64encode(raw[half:]).decode(),
                                      "last": True}))
    assert c2["ok"] is True, c2
    assert c2["result"]["name"] == "chunk"
    # Upload desconocido se rechaza limpio.
    bad = api.uploadChunk(_json.dumps({"upload_id": "nope",
                                       "base64": "", "last": True}))
    assert bad["ok"] is False
