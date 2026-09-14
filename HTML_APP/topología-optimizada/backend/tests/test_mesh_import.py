"""Fase A (mallas): lectores STL/OBJ/PLY/3MF + import como modelo MESH.

Cubo unitario sintetico por formato; verifica deteccion por contenido,
conteos, volumen == 1.0 y fail-loud (vacio / desconocido / STEP por el
path de malla). El import a CADModel usa CADService real (sin OCC).
"""

import io
import struct
import zipfile

import numpy as np
import pytest

from core.mesh_io import (
    MeshIOError,
    coherent_stride_preview,
    detect_mesh_format,
    mesh_area,
    mesh_signed_volume,
    read_mesh,
)

# Cubo [0,1]^3: 8 vertices, 12 triangulos (2 por cara).
CUBE_V = np.array([
    [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
    [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
], dtype=float)
CUBE_T = np.array([
    [0, 2, 1], [0, 3, 2],  # z=0
    [4, 5, 6], [4, 6, 7],  # z=1
    [0, 1, 5], [0, 5, 4],  # y=0
    [2, 3, 7], [2, 7, 6],  # y=1
    [0, 4, 7], [0, 7, 3],  # x=0
    [1, 2, 6], [1, 6, 5],  # x=1
], dtype=int)


def _stl_binary():
    buf = bytearray(84 + 50 * len(CUBE_T))
    struct.pack_into("<I", buf, 80, len(CUBE_T))
    for i, (a, b, c) in enumerate(CUBE_T):
        off = 84 + 50 * i
        struct.pack_into("<12fH", buf, off,
                         0, 0, 1,
                         *CUBE_V[a], *CUBE_V[b], *CUBE_V[c], 0)
    return bytes(buf)


def _stl_ascii():
    out = ["solid cube"]
    for a, b, c in CUBE_T:
        out.append("  facet normal 0 0 1")
        out.append("    outer loop")
        for v in (CUBE_V[a], CUBE_V[b], CUBE_V[c]):
            out.append(f"      vertex {v[0]} {v[1]} {v[2]}")
        out.append("    endloop")
        out.append("  endfacet")
    out.append("endsolid cube")
    return ("\n".join(out)).encode("ascii")


def _obj():
    out = []
    for v in CUBE_V:
        out.append(f"v {v[0]} {v[1]} {v[2]}")
    # Una cara como quad (fan -> 2 tris) para probar n-gonos.
    out.append("f 1 2 3 4")
    for a, b, c in CUBE_T[2:]:
        out.append(f"f {a + 1} {b + 1} {c + 1}")
    return ("\n".join(out)).encode("ascii")


def _ply_ascii():
    out = ["ply", "format ascii 1.0",
           "element vertex 8",
           "property float x", "property float y", "property float z",
           "element face 12",
           "property list uchar int vertex_indices",
           "end_header"]
    for v in CUBE_V:
        out.append(f"{v[0]} {v[1]} {v[2]}")
    for a, b, c in CUBE_T:
        out.append(f"3 {a} {b} {c}")
    return ("\n".join(out)).encode("ascii")


def _ply_binary():
    head = ("\n".join(["ply", "format binary_little_endian 1.0",
                       "element vertex 8",
                       "property float x", "property float y", "property float z",
                       "element face 12",
                       "property list uchar int vertex_indices",
                       "end_header", ""])).encode("ascii")
    body = bytearray()
    for v in CUBE_V:
        body += struct.pack("<3f", *v)
    for a, b, c in CUBE_T:
        body += struct.pack("<B3i", 3, a, b, c)
    return head + bytes(body)


def _3mf():
    verts = "\n".join(
        f'<vertex x="{v[0]}" y="{v[1]}" z="{v[2]}"/>' for v in CUBE_V)
    tris = "\n".join(
        f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in CUBE_T)
    model = ("""<?xml version="1.0"?>
<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
<resources><object id="1" type="model"><mesh><vertices>""" + verts +
             "</vertices><triangles>" + tris +
             "</triangles></mesh></object></resources>"
             "<build><item objectid=\"1\"/></build></model>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("3D/3dmodel.model", model)
        zf.writestr("[Content_Types].xml", "<Types/>")
    return buf.getvalue()


_CASES = [
    # STL = soup (sin vertices compartidos): 36 verts / 12 tris.
    ("cubo.stl", _stl_binary(), "stl", 36, 12),
    ("cubo.stl", _stl_ascii(), "stl", 36, 12),
    ("cubo.obj", _obj(), "obj", 8, 12),
    ("cubo.ply", _ply_ascii(), "ply", 8, 12),
    ("cubo.ply", _ply_binary(), "ply", 8, 12),
    ("cubo.3mf", _3mf(), "3mf", 8, 12),
]


@pytest.mark.parametrize("filename,data,fmt,nv,nt", _CASES)
def test_detect_and_read(filename, data, fmt, nv, nt):
    assert detect_mesh_format(data, filename) == fmt
    m = read_mesh(data, filename)
    assert m["format"] == fmt
    assert m["num_vertices"] == nv and m["num_triangles"] == nt
    assert abs(mesh_signed_volume(m["vertices"], m["triangles"]) - 1.0) < 1e-9
    assert abs(mesh_area(m["vertices"], m["triangles"]) - 6.0) < 1e-9


def test_detect_step_and_unknown():
    step = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
    assert detect_mesh_format(step, "p.step") == "step"
    with pytest.raises(MeshIOError):
        read_mesh(step, "p.step")
    assert detect_mesh_format(b"\x00\x01\x02" * 100, "x.bin") == "unknown"
    with pytest.raises(MeshIOError):
        read_mesh(b"", "vacio.stl")
    with pytest.raises(MeshIOError):
        read_mesh(b"v 0 0 0\n", "sincaras.obj")


def test_obj_negative_indices_and_3mf_units():
    data = b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n"
    m = read_mesh(data, "t.obj")
    assert m["num_triangles"] == 1
    # 3MF en metros: 1m^3 -> escala a mm (volumen 1e9 mm^3).
    model = ("""<?xml version="1.0"?>
<model unit="meter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
<resources><object id="1" type="model"><mesh><vertices>
<vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/>
<vertex x="1" y="1" z="0"/><vertex x="0" y="1" z="0"/>
<vertex x="0" y="0" z="1"/><vertex x="1" y="0" z="1"/>
<vertex x="1" y="1" z="1"/><vertex x="0" y="1" z="1"/>
</vertices><triangles>
<triangle v1="0" v2="2" v3="1"/><triangle v1="0" v2="3" v3="2"/>
<triangle v1="4" v2="5" v3="6"/><triangle v1="4" v2="6" v3="7"/>
<triangle v1="0" v2="1" v3="5"/><triangle v1="0" v2="5" v3="4"/>
<triangle v1="2" v2="3" v3="7"/><triangle v1="2" v2="7" v3="6"/>
<triangle v1="0" v2="4" v3="7"/><triangle v1="0" v2="7" v3="3"/>
<triangle v1="1" v2="2" v3="6"/><triangle v1="1" v2="6" v3="5"/>
</triangles></mesh></object></resources>
<build><item objectid="1"/></build></model>""")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("3D/3dmodel.model", model)
    m = read_mesh(buf.getvalue(), "u.3mf")
    assert m["unit_scale_mm"] == 1000.0
    assert abs(mesh_signed_volume(m["vertices"], m["triangles"]) - 1e9) < 1e3


def test_stride_preview_keeps_connectivity():
    rng = np.random.default_rng(7)
    big_v = rng.random((5000, 3))
    big_t = rng.integers(0, 5000, size=(4000, 3))
    pv, pt = coherent_stride_preview(big_v, big_t, 1000)
    assert pt.shape[0] <= 1000
    assert bool((pt >= 0).all()) and bool((pt < pv.shape[0]).all())


def test_service_import_mesh_builds_model():
    from services.cad_service import CADService
    from core.models import SourceType
    svc = CADService()
    model = svc.import_mesh_from_bytes(_stl_binary(), filename="cubo.stl")
    assert model.source.source_type == SourceType.MESH
    assert len(model.solids) == 1 and model.solids[0].id == "solid_0"
    assert abs(model.total_volume - 1.0) < 1e-9
    assert model.tessellation.num_triangles == 12
    full = svc.get_mesh_surface(model.id)
    assert full is not None and full[1].shape == (12, 3)
    assert svc.list_solids(model.id)[0]["solid_id"] == "solid_0"
