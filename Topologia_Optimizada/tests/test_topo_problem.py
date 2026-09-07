"""Fase 1: esquema TopologyOptimizationProblem + adaptador al SIMPSolver."""

import pytest

from core.topo_problem import (
    BCType,
    BoundaryCondition,
    DesignRegion,
    FilterSettings,
    GeometrySelection,
    Load,
    LoadCase,
    LoadType,
    Material,
    Objective,
    ObjectiveType,
    ObstacleRegion,
    RegionRole,
    TopologyOptimizationProblem,
    VolfracMode,
    VolumeConstraint,
    StressConstraint,
    default_face_resolver,
    problem_to_solver_inputs,
)
from core.topopt import TopOptError


def _mat():
    return Material(id="m1", name="steel", young_modulus=210e9,
                    poisson_ratio=0.3, density=7850.0)


def _mesh():
    # Dos tets disjuntos: cara_0 -> nodos {0,1,2} (elemento 0),
    # cara_1 -> nodos {5,6,7} (elemento 1). Sin nodos compartidos
    # para que KEEP_IN/KEEP_OUT no solapen en el camino feliz.
    return {
        "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
                  [2, 2, 2], [3, 2, 2], [2, 3, 2], [2, 2, 3]],
        "elements": [[0, 1, 2, 3], [4, 5, 6, 7]],
        "physical_groups": {"face_0": [0, 1, 2], "face_1": [5, 6, 7]},
        "face_surface_elements": {"face_0": [[0, 1, 2]], "face_1": [[5, 6, 7]]},
    }


def _problem(**kw):
    base = dict(
        id="p1",
        material=_mat(),
        design_regions=[DesignRegion(
            id="d1", target=GeometrySelection("solid_0", "solid"))],
        load_cases=[LoadCase(id="lc1", loads=[Load(
            id="l1", type=LoadType.SURFACE_FORCE,
            target=GeometrySelection("face_1", "face"),
            vector=(0.0, 0.0, -100.0))])],
        boundary_conditions=[BoundaryCondition(
            id="b1", type=BCType.FIXED,
            target=GeometrySelection("face_0", "face"))],
        volume_constraint=VolumeConstraint(target_fraction=0.3),
    )
    base.update(kw)
    return TopologyOptimizationProblem(**base)


def test_validate_clean_problem():
    assert _problem().validate() == []


def test_validate_reports_missing_blocks():
    p = TopologyOptimizationProblem(id="x", material=_mat())
    errs = p.validate()
    assert any("design_regions" in e for e in errs)
    assert any("cargas" in e for e in errs)
    assert any("boundary_conditions" in e for e in errs)
    assert any("volume_constraint" in e for e in errs)


def test_halo_auto_from_mesh_is_valid():
    p = _problem(obstacles=[ObstacleRegion(
        id="o1", role=RegionRole.KEEP_OUT,
        target=GeometrySelection("face_1", "face"),
        halo_radius=None, halo_radius_source="mesh_element_size")])
    assert p.validate() == []


def test_halo_manual_without_value_is_error():
    p = _problem(obstacles=[ObstacleRegion(
        id="o1", role=RegionRole.KEEP_OUT,
        target=GeometrySelection("face_1", "face"),
        halo_radius=None, halo_radius_source="manual")])
    assert any("halo manual" in e for e in p.validate())


def test_halo_unknown_source_is_error():
    p = _problem(obstacles=[ObstacleRegion(
        id="o1", role=RegionRole.KEEP_IN,
        target=GeometrySelection("face_1", "face"),
        halo_radius_source="filter_radius")])
    assert any("desconocido" in e for e in p.validate())


def test_keep_in_with_tiny_volfrac_is_error():
    p = _problem(
        volume_constraint=VolumeConstraint(target_fraction=0.01),
        obstacles=[ObstacleRegion(
            id="k1", role=RegionRole.KEEP_IN,
            target=GeometrySelection("face_1", "face"))],
    )
    assert any("infactibilidad" in e for e in p.validate())


def test_adapter_happy_path_maps_regions():
    p = _problem(obstacles=[
        ObstacleRegion(id="k1", role=RegionRole.KEEP_IN,
                       target=GeometrySelection("face_1", "face")),
        ObstacleRegion(id="k2", role=RegionRole.KEEP_OUT,
                       target=GeometrySelection("face_0", "face")),
    ])
    out = problem_to_solver_inputs(p, _mesh())
    assert out["material"]["young_modulus"] == 210e9
    assert out["material"]["penalization"] == 3.0
    assert out["volfrac"] == 0.3 and out["volfrac_mode"] == "active_domain"
    assert out["filter_radius"] == 1.5
    # face_1 toca nodos {2,3,4} -> elemento 1; face_0 toca {0,1,2} -> elemento 0
    assert out["preserved_elements"] == [1]
    assert out["void_elements"] == [0]
    assert len(out["loads"]) == 1 and out["loads"][0]["vector"] == (0.0, 0.0, -100.0)
    assert out["boundary_conditions"][0]["node_indices"] == [0, 1, 2]
    assert out["halos"][0]["radius"] is None  # auto P4


def test_adapter_rejects_total_volume():
    p = _problem(volume_constraint=VolumeConstraint(
        target_fraction=0.3, mode=VolfracMode.TOTAL_VOLUME))
    with pytest.raises(TopOptError, match="TOTAL_VOLUME"):
        problem_to_solver_inputs(p, _mesh())


def test_adapter_rejects_multi_load():
    p = _problem(load_cases=[
        LoadCase(id="a", loads=[Load(id="l1", type=LoadType.SURFACE_FORCE,
                                     target=GeometrySelection("face_1", "face"))]),
        LoadCase(id="b", loads=[Load(id="l2", type=LoadType.SURFACE_FORCE,
                                     target=GeometrySelection("face_0", "face"))]),
    ])
    with pytest.raises(TopOptError, match="Multi-load"):
        problem_to_solver_inputs(p, _mesh())


def test_adapter_rejects_stress_and_frozen_and_pinned_and_heaviside():
    p = _problem(stress_constraints=[StressConstraint(max_von_mises=1e6)])
    with pytest.raises(TopOptError, match="stress"):
        problem_to_solver_inputs(p, _mesh())

    p = _problem(obstacles=[ObstacleRegion(
        id="f1", role=RegionRole.FROZEN_FACE,
        target=GeometrySelection("face_0", "face"))])
    with pytest.raises(TopOptError, match="FROZEN_FACE"):
        problem_to_solver_inputs(p, _mesh())

    p = _problem(boundary_conditions=[BoundaryCondition(
        id="b1", type=BCType.PINNED,
        target=GeometrySelection("face_0", "face"))])
    with pytest.raises(TopOptError, match="PINNED"):
        problem_to_solver_inputs(p, _mesh())

    p = _problem(filter_settings=FilterSettings(
        filter_radius=1.5, use_heaviside_projection=True))
    with pytest.raises(TopOptError, match="Heaviside"):
        problem_to_solver_inputs(p, _mesh())

    p = _problem(objective=Objective(
        type=ObjectiveType.MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE))
    with pytest.raises(TopOptError, match="MINIMIZE_VOLUME"):
        problem_to_solver_inputs(p, _mesh())


def test_adapter_rejects_unknown_selection_and_overlap():
    p = _problem(obstacles=[ObstacleRegion(
        id="k1", role=RegionRole.KEEP_OUT,
        target=GeometrySelection("face_99", "face"))])
    with pytest.raises(TopOptError, match="sin nodos"):
        problem_to_solver_inputs(p, _mesh())

    # La misma cara en KEEP_IN y KEEP_OUT -> elementos en ambos sets.
    p = _problem(obstacles=[
        ObstacleRegion(id="k1", role=RegionRole.KEEP_IN,
                       target=GeometrySelection("face_0", "face")),
        ObstacleRegion(id="k2", role=RegionRole.KEEP_OUT,
                       target=GeometrySelection("face_0", "face")),
    ])
    with pytest.raises(TopOptError, match="a la vez"):
        problem_to_solver_inputs(p, _mesh())


def test_solid_entity_needs_custom_resolver():
    p = _problem(obstacles=[ObstacleRegion(
        id="k1", role=RegionRole.KEEP_OUT,
        target=GeometrySelection("solid_0", "solid"))])
    with pytest.raises(TopOptError, match="resolvedor propio"):
        problem_to_solver_inputs(p, _mesh())

    def solid_resolver(sel, mesh):
        if sel.entity_type == "solid":
            assert sel.selection_id == "solid_0"
            return {"node_indices": [0, 1, 2, 3, 4, 5, 6, 7],
                    "element_indices": [0, 1]}
        return default_face_resolver(sel, mesh)  # cargas/BCs en caras

    out = problem_to_solver_inputs(p, _mesh(), selection_resolver=solid_resolver)
    assert out["void_elements"] == [0, 1]


def test_default_face_resolver_accepts_id_forms():
    m = _mesh()
    for sid in ("face_0", "face:0", "0"):
        res = default_face_resolver(GeometrySelection(sid, "face"), m)
        assert res["node_indices"] == [0, 1, 2]
