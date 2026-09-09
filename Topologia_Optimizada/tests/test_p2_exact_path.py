"""P2 exact path promoted to productive: faced conditions travel on exact
per-condition submodelparts in run_fea(backend="kratos").

Covers:
1. Faced load uses the exact named submodelpart (Strategy 1), even with no
   CAD shape available (no silent geometric substitution).
2. No silent mislabeling: missing/empty submodelpart + unmappable face ->
   UNRESOLVED (never a coordinate fallback region).
3. Local<->Kratos parity preserved: bridge emits submodelpart_name only for
   faced conditions; faceless conditions keep the explicit parity defaults.
4. The undifferentiated "boundary" bucket is strictly a last resort: explicit
   warning + matched_specific=False, and opt-out via allow_boundary_fallback.
"""

import logging

import numpy as np

from core.boundary import face_triangles_for_indices
from core.cad_entity import CadEntityRef, EntityType, SelectionSet
from core.conditions import (
    ElasticityCondition,
    LoadCondition,
    LoadOrientation,
    LoadSense,
)
from core.kratos_bridge import (
    condition_face_groups,
    condition_group_name,
    conditions_to_kratos_definitions,
    load_condition_to_definition,
)


def _face_selection(*indices):
    sel = SelectionSet(name="cara")
    for i in indices:
        sel.add(CadEntityRef(entity_type=EntityType.FACE, face_index=i))
    return sel


def _load(faces, magnitude=1000.0):
    return LoadCondition(
        name="Carga",
        faces=faces,
        orientation=LoadOrientation.PERPENDICULAR,
        sense=LoadSense.POSITIVE,
        magnitude=magnitude,
        indeterminate=False,
    )


class _FakeAdapter:
    """Minimal adapter surface used by solver_interface strategies."""

    def __init__(self, submodelparts):
        # {name: [0-based node indices]}
        self._parts = dict(submodelparts)
        self.applied = []

    def get_nodes_from_submodelpart(self, model_part, name):
        return list(self._parts.get(name, []))

    def apply_load_from_core(self, model_part, load, node_indices, **kwargs):
        self.applied.append((load.id, list(node_indices)))
        return None

    def apply_constraint_from_core(self, model_part, constraint, node_indices):
        self.applied.append((constraint.id, list(node_indices)))
        return None


# --------------------------------------------------------------------------- #
# 1. Faced load uses the exact submodelpart (Strategy 1)
# --------------------------------------------------------------------------- #
def test_faced_load_uses_exact_submodelpart():
    from core.solver_interface import _apply_load_geometrically
    from core.study import LoadDefinition

    load = _load(_face_selection(2), magnitude=500.0)
    d = load_condition_to_definition(load)
    assert d.submodelpart_name == condition_group_name(load.id)

    expected_nodes = [3, 7, 9]
    adapter = _FakeAdapter({d.submodelpart_name: expected_nodes})
    nodes = [[float(i), 0.0, 0.0] for i in range(12)]
    ld = LoadDefinition(
        id="L1", magnitude=500.0, direction=(0.0, 0.0, 1.0),
        application_face_id=None,  # no face id at all: exact path must still win
        submodelpart_name=d.submodelpart_name,
    )
    status = _apply_load_geometrically(adapter, object(), ld, nodes, None)
    assert status == "APPLIED"
    assert adapter.applied == [("L1", expected_nodes)]


def test_faced_constraint_uses_exact_submodelpart():
    from core.solver_interface import _apply_constraint_geometrically
    from core.study import ConstraintDefinition, ConstraintType

    support = ElasticityCondition(name="Soporte", faces=_face_selection(1))
    groups = condition_face_groups([support])
    assert groups == {condition_group_name(support.id): [1]}

    expected_nodes = [0, 1, 2]
    adapter = _FakeAdapter({condition_group_name(support.id): expected_nodes})
    nodes = [[float(i), 0.0, 0.0] for i in range(6)]
    cd = ConstraintDefinition(
        id="C1", constraint_type=ConstraintType.FIXED, location_face_id=None,
        submodelpart_name=condition_group_name(support.id),
    )
    status = _apply_constraint_geometrically(adapter, object(), cd, nodes, None)
    assert status == "APPLIED"
    assert adapter.applied == [("C1", expected_nodes)]


# --------------------------------------------------------------------------- #
# 2. No silent mislabeling: unmappable faced load -> UNRESOLVED
# --------------------------------------------------------------------------- #
def test_missing_submodelpart_with_bad_face_is_unresolved_not_relocated():
    from core.solver_interface import _apply_load_geometrically
    from core.study import LoadDefinition

    adapter = _FakeAdapter({})  # named submodelpart absent/empty
    nodes = [[float(i), 0.0, 0.0] for i in range(8)]
    ld = LoadDefinition(
        id="Lbad", magnitude=100.0, direction=(0.0, 0.0, 1.0),
        application_face_id="not-a-face",
        submodelpart_name="cond_missing",
    )
    status = _apply_load_geometrically(adapter, object(), ld, nodes, None)
    assert isinstance(status, str) and status.startswith("UNRESOLVED")
    assert adapter.applied == []  # nothing applied anywhere else


# --------------------------------------------------------------------------- #
# 3. Parity local<->Kratos preserved (faceless untouched, faced exact)
# --------------------------------------------------------------------------- #
def test_bridge_parity_faced_exact_faceless_none():
    empty = SelectionSet(name="vacio")
    faced = _load(_face_selection(0))
    loads, constraints, _ = conditions_to_kratos_definitions(
        [faced, _load(empty), ElasticityCondition(faces=empty)]
    )
    assert loads[0].submodelpart_name == condition_group_name(faced.id)
    assert loads[0].selection is not None
    # Faceless: no submodelpart, no selection -> explicit parity defaults stay.
    assert loads[1].submodelpart_name is None
    assert loads[1].selection is None
    assert constraints[0].submodelpart_name is None
    assert constraints[0].selection is None


# --------------------------------------------------------------------------- #
# 4. "boundary" bucket: last resort with explicit warning + opt-out
# --------------------------------------------------------------------------- #
def test_boundary_bucket_is_last_resort_with_warning(caplog):
    fse = {"boundary": [[0, 1, 2]]}
    with caplog.at_level(logging.WARNING, logger="core.boundary"):
        tris, matched = face_triangles_for_indices(
            [5], fse, group_index={}, node_indices=[0, 1, 2])
    assert tris == [[0, 1, 2]]
    assert matched is False  # never reported as exact
    assert any("LAST-RESORT" in r.message for r in caplog.records)

    tris_off, matched_off = face_triangles_for_indices(
        [5], fse, group_index={}, node_indices=[0, 1, 2],
        allow_boundary_fallback=False)
    assert tris_off == [] and matched_off is False


def test_exact_group_wins_over_boundary_bucket(caplog):
    fse = {"cond_x": [[0, 1, 2]], "boundary": [[0, 1, 2], [3, 4, 5]]}
    with caplog.at_level(logging.WARNING, logger="core.boundary"):
        tris, matched = face_triangles_for_indices(
            [5], fse, group_index={5: ["cond_x"]}, node_indices=[0, 1, 2])
    assert tris == [[0, 1, 2]]
    assert matched is True
    assert not any("LAST-RESORT" in r.message for r in caplog.records)
