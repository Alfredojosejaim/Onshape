"""Quick-win P1: MeshResult.metadata persiste el mapa face_index_to_tag.

Aditivo y sin cambio de comportamiento: solo verifica que el mapa
determinista (cuando existe) quede registrado en metadata para
reproducibilidad, y que el modo order-fallback registre None.
"""

import cadquery as cq
import pytest

gmsh = pytest.importorskip("gmsh")


def _box_shape():
    return cq.Workplane("XY").box(10, 10, 10).val()


def test_metadata_persists_face_index_to_tag():
    from core.meshing import GmshTet4Mesher
    mesher = GmshTet4Mesher(mesh_size_max=5.0)
    shape = _box_shape()
    res = mesher.generate_mesh(shape, target_element_size=5.0)
    assert res.metadata.get("face_correspondence") == "deterministic"
    m = res.metadata.get("face_index_to_tag")
    assert isinstance(m, dict) and len(m) == len(shape.Faces())
    # Claves fi cubren todas las caras, valores tags Gmsh positivos.
    assert sorted(m.keys()) == list(range(len(shape.Faces())))
    assert all(isinstance(t, int) and t > 0 for t in m.values())
    # face_surface_elements usa esas etiquetas (sin mislabeling por orden).
    for fi in range(len(shape.Faces())):
        assert f"face_{fi}" in res.face_surface_elements


def test_metadata_order_fallback_registers_none():
    from core.meshing import GmshTet4Mesher
    import tempfile, os
    shape = _box_shape()
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
        path = tmp.name
    try:
        cq.exporters.export(shape, path, exportType="STEP")
        mesher = GmshTet4Mesher(mesh_size_max=5.0)
        res = mesher.generate_mesh_from_step(path)  # sin cq_shape ni mapa
        assert res.metadata.get("face_correspondence") == "order-fallback"
        assert res.metadata.get("face_index_to_tag") is None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
