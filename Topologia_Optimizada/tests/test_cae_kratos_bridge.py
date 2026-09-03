"""Tests for the Kratos FEA backend bridge (closing the Kratos/local gap).

Scope: with the local NumPy solver remaining the default, ``run_fea`` gains an
optional ``backend="kratos"`` that consumes the *same* reusable conditions and
the mesh ``physical_groups``.  This module exercises:

1.  The pure translation layer ``core.kratos_bridge`` (LoadCondition ->
    LoadDefinition, ElasticityCondition -> ConstraintDefinition), including the
    exact face region emitted by the local ``FaceRegion.to_dict``.
2.  The controller wiring: ``run_fea(backend="kratos")`` builds the definitions
    from conditions and forwards ``physical_groups`` to
    ``create_kratos_fea_solver`` (verified with a fake solver so the unit test
    does not require a real Kratos installation / solve).

No real Kratos solve is executed here: the integration path is verified
deterministically, and the heavy solve remains an environment-level concern.
"""

import numpy as np
import pytest

from core.cad_entity import CadEntityRef, EntityType, SelectionSet
from core.conditions import (
    ConditionManager,
    ElasticityCondition,
    LoadCondition,
    LoadOrientation,
    LoadSense,
    ObstructionCondition,
)
from core.kratos_bridge import (
    conditions_to_kratos_definitions,
    elasticity_condition_to_definition,
    load_condition_to_definition,
)
from core.study import ConstraintType, LoadType
from desktop.pipeline.controller import PipelineController


# --------------------------------------------------------------------------- #
# Bridge: LoadCondition -> LoadDefinition
# --------------------------------------------------------------------------- #
def _load_condition(faces, sense=LoadSense.POSITIVE, magnitude=1000.0):
    return LoadCondition(
        name="Carga",
        faces=faces,
        orientation=LoadOrientation.PERPENDICULAR,
        sense=sense,
        magnitude=magnitude,
        indeterminate=False,
    )


def _face_selection(*indices):
    sel = SelectionSet(name="cara")
    for i in indices:
        sel.add(CadEntityRef(entity_type=EntityType.FACE, face_index=i))
    return sel


def test_load_condition_to_definition_uses_face_selection():
    faces = _face_selection(2, 0)
    load = _load_condition(faces, magnitude=300.0)

    d = load_condition_to_definition(load)

    assert d.magnitude == 300.0
    assert d.load_type == LoadType.DISTRIBUTED
    # Perfectly down (positive Z normal) -> non-zero direction.
    assert np.linalg.norm(d.direction) == pytest.approx(1.0)
    assert d.application_face_id == "2"  # first selected face
    # The advanced-selection descriptor must be a valid FaceRegion dict; the
    # bridge emits face indices deterministically sorted.
    from core.selection import FaceRegion
    assert d.selection["type"] == "face"
    assert set(d.selection["face_indices"]) == {0, 2}
    assert d.selection["tolerance"] == 0.5
    assert d.selection == FaceRegion(face_indices=[0, 2], tolerance=0.5).to_dict()


def test_load_condition_indeterminate_magnitude_defaults():
    load = _load_condition(_face_selection(1), magnitude=None, sense=LoadSense.NEGATIVE)
    d = load_condition_to_definition(load)
    # Indeterminate magnitude mirrors GenerativeDesignEngine's 1000 N default.
    assert d.magnitude == 1000.0
    assert tuple(np.round(d.direction, 10)) == (0.0, 0.0, -1.0)


def test_load_condition_without_face_has_no_selection():
    empty = SelectionSet(name="vacio")
    d = load_condition_to_definition(_load_condition(empty))
    assert d.selection is None
    assert d.application_face_id is None


# --------------------------------------------------------------------------- #
# Bridge: ElasticityCondition -> ConstraintDefinition
# --------------------------------------------------------------------------- #
def test_elasticity_condition_to_definition_uses_face_selection():
    sel = _face_selection(1)
    e = ElasticityCondition(name="Soporte", faces=sel)

    c = elasticity_condition_to_definition(e)

    assert c.constraint_type == ConstraintType.FIXED
    assert c.location_face_id == "1"
    assert all(c.degrees_of_freedom.values())
    from core.selection import FaceRegion
    assert c.selection == FaceRegion(face_indices=[1], tolerance=0.5).to_dict()


def test_elasticity_condition_without_face_has_no_selection():
    empty = SelectionSet(name="vacio")
    c = elasticity_condition_to_definition(ElasticityCondition(faces=empty))
    assert c.selection is None
    assert c.location_face_id == ""


# --------------------------------------------------------------------------- #
# Bridge: conditions_to_kratos_definitions
# --------------------------------------------------------------------------- #
def test_conditions_to_kratos_definitions_skips_non_fea_kinds():
    faces = _face_selection(1)
    loads = [_load_condition(faces, magnitude=200.0)]
    supports = [ElasticityCondition(faces=faces)]
    obstruction = ObstructionCondition(bodies=SelectionSet(name="body"))

    ld, cd, skipped = conditions_to_kratos_definitions(loads + supports + [obstruction])

    assert len(ld) == len(loads)
    assert len(cd) == len(supports)
    assert skipped == [obstruction.id]


def test_conditions_to_kratos_definitions_rejects_unknown_object():
    with pytest.raises(ValueError):
        conditions_to_kratos_definitions([object()])


# --------------------------------------------------------------------------- #
# Controller wiring: run_fea(backend="kratos")
# --------------------------------------------------------------------------- #
def _controller_with_mesh():
    c = PipelineController()
    nodes, els = _hex_grid()
    c.mesh_nodes = nodes
    c.mesh_elements = els
    c.mesh = {"nodes": nodes.shape[0], "elements": els.shape[0],
              "physical_groups": {"base": [0, 1, 2, 3]}}
    faces = _face_selection(1)
    load = _load_condition(faces, magnitude=500.0)
    support = ElasticityCondition(faces=faces)
    c.conditions.add(load)
    c.conditions.add(support)
    return c, list(c.conditions.all)


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


def test_run_fea_default_backend_is_local():
    """The local NumPy solver remains the default (backend="local")."""
    c, conditions = _controller_with_mesh()
    # face-less conditions -> the local FEA uses the legitimate coordinate default
    c.conditions = ConditionManager()
    load = _load_condition(SelectionSet(name="vacio"), magnitude=1000.0)
    support = ElasticityCondition(faces=SelectionSet(name="sop"))
    c.conditions.add(load)
    c.conditions.add(support)
    result = c.run_fea(conditions=list(c.conditions.all))
    assert result["success"] is True
    assert result["engine"] == "self-contained-numpy-tet4"


def test_run_fea_kratos_backend_builds_definitions_and_forwards_groups(monkeypatch):
    """run_fea(backend="kratos") translates reusable conditions into Kratos
    load/constraint definitions and forwards ``physical_groups`` to
    ``create_kratos_fea_solver``.  The callable is faked so the unit test does
    not depend on a live Kratos solve."""
    captured = {}

    def fake_create_kratos_fea_solver(nodes, elements, material, constraints,
                                      loads, cad_shape, physical_groups,
                                      **kwargs):
        captured["nodes"] = np.asarray(nodes)
        captured["elements"] = np.asarray(elements)
        captured["material"] = material
        captured["constraints"] = constraints
        captured["loads"] = loads
        captured["cad_shape"] = cad_shape
        captured["physical_groups"] = physical_groups

        def solve(densities, *args, **kwargs):
            return {
                "success": True,
                "status": "completed",
                "displacements": np.zeros(int(densities.sum())),
                "compliance": 1.0,
                "element_energies": np.zeros(len(captured["elements"])),
                "num_nodes": len(captured["nodes"]),
                "num_elements": len(captured["elements"]),
            }

        return solve

    monkeypatch.setattr(
        "core.solver_interface.create_kratos_fea_solver", fake_create_kratos_fea_solver
    )

    c, conditions = _controller_with_mesh()
    result = c.run_fea(conditions=conditions, backend="kratos")

    # Physical groups (mesh boundary) forwarded verbatim.
    assert captured["physical_groups"] == {"base": [0, 1, 2, 3]}
    # The translated conditions arrive as LoadDefinition / ConstraintDefinition.
    assert len(captured["loads"]) == 1
    assert len(captured["constraints"]) == 1
    from core.study import ConstraintDefinition, LoadDefinition
    assert isinstance(captured["loads"][0], LoadDefinition)
    assert isinstance(captured["constraints"][0], ConstraintDefinition)
    # The result is stored back on the controller.
    assert c.result is result
    assert result["success"] is True


def test_run_fea_kratos_requires_mesh(monkeypatch):
    monkeypatch.setattr(
        "core.solver_interface.create_kratos_fea_solver",
        lambda **kw: (lambda **kw2: {"success": True}),
    )
    c = PipelineController()
    c.mesh = None
    with pytest.raises(Exception):
        c.run_fea(conditions=[], backend="kratos")


def test_run_fea_kratos_surfaces_solve_failure(monkeypatch):
    """A non-successful Kratos solve becomes a PipelineError."""

    def fake_create_kratos_fea_solver(**kwargs):
        return lambda **kw: {"success": False, "error": "boom"}

    monkeypatch.setattr(
        "core.solver_interface.create_kratos_fea_solver", fake_create_kratos_fea_solver
    )
    c, conditions = _controller_with_mesh()
    with pytest.raises(Exception, match="boom"):
        c.run_fea(conditions=conditions, backend="kratos")