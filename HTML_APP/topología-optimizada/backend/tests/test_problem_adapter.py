"""FASE-1 (2026-09-23): problem_to_solver_inputs alineado con el solver.

El adaptador rechazaba VolfracMode.TOTAL_VOLUME aunque SIMPSolver lo soporta
(volfrac_mode), y validaba el objetivo MINIMIZE_VOLUME pero lo descartaba de
la salida. Los rechazos genuinos (stress/displacement, BC no-FIXED, filtro
no-density) se conservan y se cubren como decisión explícita.
"""

import numpy as np
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
    problem_to_solver_inputs,
)
from core.topopt import TopOptError

NODES = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                  [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
ELEMENTS = [[0, 1, 2, 3]]
MESH = {"nodes": NODES.tolist(), "elements": ELEMENTS}


def _stub_resolver(sel, mesh):
    assert sel.selection_id == "face_0"
    return {"node_indices": [0, 1, 2], "element_indices": [0]}


def _problem(**kw):
    sel = GeometrySelection(selection_id="face_0", entity_type="face")
    mat = Material(id="m", name="steel", young_modulus=210e9,
                   poisson_ratio=0.3, density=7850.0)
    return TopologyOptimizationProblem(
        id="p",
        material=mat,
        design_regions=[DesignRegion(id="d", target=sel)],
        obstacles=[],
        load_cases=[LoadCase(id="lc", loads=[
            Load(id="l", type=LoadType.POINT_FORCE, target=sel,
                 vector=(0.0, -10.0, 0.0))])],
        boundary_conditions=[BoundaryCondition(id="b", type=BCType.FIXED,
                                               target=sel)],
        volume_constraint=kw.get("volume_constraint",
                                 VolumeConstraint(target_fraction=0.4)),
        filter_settings=FilterSettings(filter_radius=0.6),
        objective=kw.get("objective", Objective()),
    )


def test_total_volume_aceptado_y_propagado():
    out = problem_to_solver_inputs(
        _problem(volume_constraint=VolumeConstraint(
            target_fraction=0.4, mode=VolfracMode.TOTAL_VOLUME)),
        MESH, selection_resolver=_stub_resolver)
    assert out["volfrac_mode"] == "total_volume"
    assert out["volfrac"] == pytest.approx(0.4)


def test_active_domain_sigue_aceptado():
    out = problem_to_solver_inputs(_problem(), MESH,
                                   selection_resolver=_stub_resolver)
    assert out["volfrac_mode"] == "active_domain"


def test_min_volume_propagado_con_limite():
    out = problem_to_solver_inputs(
        _problem(objective=Objective(
            type=ObjectiveType.MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE,
            max_compliance=150.0)),
        MESH, selection_resolver=_stub_resolver)
    assert out["objective"] == "min_volume"
    assert out["compliance_limit"] == pytest.approx(150.0)


def test_min_compliance_sin_limite():
    out = problem_to_solver_inputs(_problem(), MESH,
                                   selection_resolver=_stub_resolver)
    assert out["objective"] == "min_compliance"
    assert out["compliance_limit"] is None


def test_min_volume_sin_limite_falla_explicito():
    with pytest.raises(TopOptError):
        problem_to_solver_inputs(
            _problem(objective=Objective(
                type=ObjectiveType.MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE)),
            MESH, selection_resolver=_stub_resolver)


def test_rechazos_genuinos_se_conservan():
    from core.topo_problem import (DisplacementConstraint,
                                   StressConstraint)
    sel = GeometrySelection(selection_id="face_0", entity_type="face")
    base = _problem()
    # stress constraint
    base.stress_constraints = [StressConstraint(max_von_mises=250.0)]
    with pytest.raises(TopOptError):
        problem_to_solver_inputs(base, MESH, selection_resolver=_stub_resolver)
    # BC no-FIXED
    base.stress_constraints = []
    base.boundary_conditions = [BoundaryCondition(
        id="b", type=BCType.PINNED, target=sel)]
    with pytest.raises(TopOptError):
        problem_to_solver_inputs(base, MESH, selection_resolver=_stub_resolver)
    # filtro no-density
    base.boundary_conditions = [BoundaryCondition(
        id="b", type=BCType.FIXED, target=sel)]
    base.filter_settings = FilterSettings(filter_radius=0.6,
                                          filter_type="sensitivity")
    with pytest.raises(TopOptError):
        problem_to_solver_inputs(base, MESH, selection_resolver=_stub_resolver)
    # displacement constraint
    base.filter_settings = FilterSettings(filter_radius=0.6)
    base.displacement_constraints = [DisplacementConstraint(
        target=sel, max_displacement=0.1)]
    with pytest.raises(TopOptError):
        problem_to_solver_inputs(base, MESH, selection_resolver=_stub_resolver)
    # keep_in infactible vs objetivo sigue rechazado (P3)
    base.displacement_constraints = []
    base.obstacles = [ObstacleRegion(id="k", role=RegionRole.KEEP_IN,
                                     target=sel)]
    with pytest.raises(TopOptError):
        problem_to_solver_inputs(
            base, {"nodes": NODES.tolist(), "elements": ELEMENTS * 4},
            selection_resolver=lambda s, m: {"node_indices": [0],
                                             "element_indices": [0, 1, 2, 3]})
