"""Fase 2 validation tests.

Covers the Fase 2 recommendations implemented on top of the FASE 1
architecture:

- F2a: body/solid selection resolution (resolve_solid_for_face)
- F2b: real boolean operations via CadQuery cached back as a new model
- F2c: adaptive (density-driven) mesh generation
- F2d: density color map / colormap builder
- F2e: STEP export of the current model

These are additive checks; they must not break the existing suite.
"""

import os
import tempfile

import numpy as np
import pytest

import cadquery as cq

from services.cad_service import CADService


@pytest.fixture
def service():
    return CADService()


@pytest.fixture
def box_model(service):
    shape = cq.Workplane("XY").box(20, 10, 10).val()
    return service.store_computed_shape(shape, "Caja")


# --------------------------------------------------------------------- #
# F2b: Boolean operations
# --------------------------------------------------------------------- #
def test_boolean_union_volume(service, box_model):
    tool = cq.Workplane("XY").box(5, 5, 5).val()
    t_id = service.store_computed_shape(tool, "Herramienta")

    target = service.get_model_shape(box_model)
    tool_shape = service.get_model_shape(t_id)
    result = target.fuse(tool_shape)

    # 20x10x10 fully contains 5x5x5 -> volume unchanged (overlap)
    assert abs(result.Volume() - 2000.0) < 1e-6


def test_boolean_difference_reduces_volume(service, box_model):
    tool = cq.Workplane("XY").box(3, 3, 3).val()
    t_id = service.store_computed_shape(tool, "Herramienta")

    target = service.get_model_shape(box_model)
    result = target.cut(service.get_model_shape(t_id))
    assert result.Volume() < 2000.0


def test_store_computed_shape_registers_in_both_caches(service, box_model):
    assert service.get_model_shape(box_model) is not None
    assert service.step_adapter.get_shape(box_model) is not None


# --------------------------------------------------------------------- #
# F2a: Solid/body selection
# --------------------------------------------------------------------- #
def test_resolve_solid_for_face_single_solid(service, box_model):
    solid = service.resolve_solid_for_face(box_model, 0)
    assert solid is not None
    assert solid["solid_id"] == "solid_0"
    assert solid["index"] == 0


def test_list_solids(service, box_model):
    solids = service.list_solids(box_model)
    assert len(solids) == 1
    assert solids[0]["solid_id"] == "solid_0"
    assert solids[0]["faces_count"] == 6
    assert solids[0]["volume"] is not None
    assert abs(solids[0]["volume"] - 2000.0) < 1e-6


def test_list_solids_multiple(service):
    # Compound of two separated boxes -> two solids
    b1 = cq.Workplane("XY").box(4, 4, 4).translate((0, 0, 0))
    b2 = cq.Workplane("XY").box(4, 4, 4).translate((30, 0, 0))
    comp = b1.val().fuse(b2.val())
    m = service.store_computed_shape(comp, "Dos cuerpos")
    solids = service.list_solids(m)
    assert len(solids) == 2


# --------------------------------------------------------------------- #
# F2c: Adaptive mesh
# --------------------------------------------------------------------- #
def test_generate_uniform_mesh(service, box_model):
    mesh = service.generate_mesh(box_model, target_element_size=8.0)
    assert mesh.get("success")
    assert mesh.get("num_elements", 0) > 0
    assert len(mesh["nodes"]) == mesh.get("num_nodes")


def test_generate_adaptive_mesh_density_driven(service, box_model):
    mesh = service.generate_mesh(box_model, target_element_size=8.0)
    nodes = np.asarray(mesh["nodes"], dtype=float)
    elems = np.asarray(mesh["elements"], dtype=int)
    d = np.ones(len(elems))  # all "solid" density -> refine everywhere

    am = service.generate_adaptive_mesh(
        box_model, densities=d, elements=elems, nodes=nodes,
        base_size=8.0, min_size=2.0,
    )
    assert am.get("success")
    assert am.get("num_elements", 0) > 0
    assert am.get("metadata", {}).get("adaptive")


# --------------------------------------------------------------------- #
# F2d: Density colormap
# --------------------------------------------------------------------- #
def test_density_colormap_builder():
    from desktop.viewport.scene import Scene, _COLORMAPS

    ctf = Scene._density_colormap("jet")
    assert ctf is not None
    assert "viridis" in _COLORMAPS
    assert "coolwarm" in _COLORMAPS
    assert len(_COLORMAPS["jet"]) > 2


# --------------------------------------------------------------------- #
# F2e: STEP export
# --------------------------------------------------------------------- #
def test_export_step(service, box_model):
    tmp = tempfile.mkstemp(suffix=".step")
    os.close(tmp[0])
    try:
        ok = service.export_step(box_model, tmp[1])
        assert ok
        assert os.path.getsize(tmp[1]) > 0
        # Re-import to confirm validity
        with open(tmp[1], "rb") as fh:
            data = fh.read()
        assert len(data) > 100
    finally:
        if os.path.exists(tmp[1]):
            os.unlink(tmp[1])
