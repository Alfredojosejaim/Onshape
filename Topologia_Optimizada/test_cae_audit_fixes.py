"""Tests for the audit fixes in ``prompts.md``.

Covers the CRITICAL / HIGH findings resolved within the existing architecture:

1.  FEA consumes the reusable conditions (ConditionManager) instead of only the
    bare ``self.forces`` / ``self.constraints`` arrays (``run_fea``).
2.  A load/support selected on a real CAD face is never silently relocated to
    arbitrary coordinate nodes; an unmappable face raises a clear error.
3.  The reconstructed B-Rep of the generative-design flow is registered back as
    a real ``CADModel`` flowing into the Document / feature history / Design Tree.
"""

import numpy as np
import pytest

from core.cad_entity import CadEntityRef, EntityType, SelectionSet
from core.conditions import (
    ElasticityCondition,
    LoadCondition,
    LoadOrientation,
    LoadSense,
)
from desktop.pipeline.controller import PipelineController


# --------------------------------------------------------------------- #
# Shared synthetic hex grid (2x1x1 cubes -> 12 tets)
# --------------------------------------------------------------------- #
def _hex_grid(nx=2, ny=1, nz=1):
    nodes = []
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                nodes.append([float(i), float(j), float(k)])
    nodes = np.asarray(nodes, dtype=float)

    def ni(i, j, k):
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    els = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                a = ni(i, j, k); b = ni(i + 1, j, k)
                c = ni(i + 1, j + 1, k); d = ni(i, j + 1, k)
                e = ni(i, j, k + 1); f = ni(i + 1, j, k + 1)
                g = ni(i + 1, j + 1, k + 1); h = ni(i, j + 1, k + 1)
                els.append([a, b, e, c]); els.append([b, f, e, c])
                els.append([e, f, g, c]); els.append([e, g, h, c])
                els.append([a, e, d, c]); els.append([h, e, d, c])
    return nodes, np.asarray(els, dtype=int)


def _reusable_conditions(select_face=True):
    """Add load + support conditions to the *controller's* shared store.

    Returns the list of Condition objects (as used by ``run_fea``).
    """
    if select_face:
        faces = SelectionSet(name="face", entities=[
            CadEntityRef(entity_type=EntityType.FACE, face_index=0)])
    else:
        faces = SelectionSet(name="face")
    load = LoadCondition(
        name="Carga", faces=faces, orientation=LoadOrientation.PERPENDICULAR,
        sense=LoadSense.POSITIVE, magnitude=1000.0, indeterminate=False,
    )
    support = ElasticityCondition(name="Soporte", faces=SelectionSet(name="sop"))
    return load, support


def _controller_with_mesh(select_face=False):
    """A real PipelineController wired with a synthetic tet mesh + conditions."""
    c = PipelineController()
    nodes, els = _hex_grid()
    c.mesh_nodes = nodes
    c.mesh_elements = els
    c.mesh = {"nodes": nodes.shape[0], "elements": els.shape[0]}
    load, support = _reusable_conditions(select_face=select_face)
    c.conditions.add(load)
    c.conditions.add(support)
    return c, list(c.conditions.all)


# --------------------------------------------------------------------- #
# 1. FEA consumes reusable conditions
# --------------------------------------------------------------------- #
def test_run_fea_consumes_reusable_conditions():
    """run_fea with reusable (face-less) conditions produces a real solve."""
    c, conditions = _controller_with_mesh(select_face=False)

    result = c.run_fea(conditions=conditions)

    assert result["success"] is True
    assert result["status"] == "completed"
    assert result["num_elements"] == c.mesh_elements.shape[0]
    assert result["max_displacement"] >= 0.0
    assert len(result["fixed_dofs"]) > 0
    assert result["engine"] == "self-contained-numpy-tet4"


def test_run_fea_without_conditions_keeps_legacy_path():
    """run_fea with no reusable conditions still works via bare arrays."""
    c, _ = _controller_with_mesh(select_face=False)
    c.set_simple_boundaries()
    result = c.run_fea()
    assert result["success"] is True
    assert result["num_elements"] == c.mesh_elements.shape[0]


# --------------------------------------------------------------------- #
# 2. Coherent BC handling: never relocate a selected face silently
# --------------------------------------------------------------------- #
def test_build_fea_problem_rejects_unmapped_selected_face():
    """A load with a selected face that cannot map to nodes raises (no silent
    relocation to arbitrary coordinate nodes), matching the Kratos path."""
    c, conditions = _controller_with_mesh(select_face=True)

    with pytest.raises(ValueError, match="load"):
        c.run_fea(conditions=conditions)


def test_build_fea_problem_allows_no_face_coordinate_default():
    """A load without any selected face legitimately defaults to coordinate
    nodes (this is a default, not a silent relocation of a real selection)."""
    c, conditions = _controller_with_mesh(select_face=False)

    result = c.run_fea(conditions=conditions)
    assert result["success"] is True


# --------------------------------------------------------------------- #
# 3. Reconstruction B-Rep is registered back as a CADModel
# --------------------------------------------------------------------- #
def test_register_reconstruction_model_registers_model_e2e():
    """A completed reconstruction solid becomes an active CADModel recorded in
    the Document / feature history, and the raw solid is consumed."""
    import cadquery as cq
    from core.features import FeatureType

    c = PipelineController()
    box = cq.Workplane("XY").box(5, 5, 5).val()  # cq.Shape (wraps a TopoDS)

    rec = {"stage": "brep_solid", "status": "completed",
           "metadata": {}, "data": box}
    info = c._register_reconstruction_model(rec)

    assert info.get("model_id")
    assert c.model_id == info["model_id"]
    assert c.model_name == "Reconstrucción Topológica"
    # registered in the CAD service cache + active in the Document
    assert c.cad.get_model(c.model_id) is not None
    assert c.document.active_model_id == c.model_id
    # recorded in the feature history
    assert c.feature_history.executed_features
    feat = c.feature_history.executed_features[-1]
    assert feat.feature_type == FeatureType.CUSTOM
    assert feat.result_model_id == c.model_id
    # raw solid consumed from the dict (not passed on to consumers)
    assert "data" not in rec
    assert rec["model_id"] == c.model_id


def test_register_reconstruction_model_no_solid_is_noop():
    """Without a reconstructed solid the helper is a harmless no-op."""
    c = PipelineController()
    rec = {"stage": "brep_solid", "status": "not_started", "metadata": {}}
    assert c._register_reconstruction_model(rec) == {}
    assert c.model_id is None


def test_register_reconstruction_model_honours_the_layer_capability():
    """Even when the CAD layer cannot store a shape the study is not failed."""

    class NoStoreCAD:
        def get_model(self, mid):
            return None

    class FakeDoc:
        def set_model(self, m):
            raise AssertionError("should not be called")

    c = PipelineController.__new__(PipelineController)
    c.model_id = None
    c.model_name = None
    c.result_densities = None
    c.current_tessellation = None
    c.cad = NoStoreCAD()
    c.document = FakeDoc()
    c.feature_history = None

    rec = {"stage": "brep_solid", "status": "completed", "metadata": {},
           "data": object()}
    # No store_computed_shape -> returns {} without raising.
    assert c._register_reconstruction_model(rec) == {}