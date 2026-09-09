"""Pass-through FROZEN_FACE en reconstrucción.

FROZEN_FACE se comporta como KEEP_IN documentado (elementos fijos a 1.0,
rol propagado en halos/metadata) y ya no levanta TopOptError.
"""

import numpy as np
import pytest


def _mesh_two_tets():
    nodes = np.array([
        [0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 0., 1.],
        [1., 1., 1.],
    ])
    elements = [[0, 1, 2, 3], [1, 2, 3, 4]]
    return nodes, elements


def _problem_with_roles(frozen=True, keep_in=True, keep_out=True):
    from core.topo_problem import (
        TopologyOptimizationProblem, Material, DesignRegion, ObstacleRegion,
        GeometrySelection, RegionRole, VolumeConstraint, LoadCase, Load,
        LoadType, BoundaryCondition, BCType,
    )
    mat = Material(id="m", name="steel", young_modulus=210e9,
                   poisson_ratio=0.3, density=7850.0)
    obstacles = []
    if keep_in:
        obstacles.append(ObstacleRegion(id="ki", role=RegionRole.KEEP_IN,
                                        target=GeometrySelection(
                                            selection_id="face_0",
                                            entity_type="face")))
    if keep_out:
        obstacles.append(ObstacleRegion(id="ko", role=RegionRole.KEEP_OUT,
                                        target=GeometrySelection(
                                            selection_id="face_1",
                                            entity_type="face")))
    if frozen:
        obstacles.append(ObstacleRegion(id="fz", role=RegionRole.FROZEN_FACE,
                                        target=GeometrySelection(
                                            selection_id="face_0",
                                            entity_type="face")))
    return TopologyOptimizationProblem(
        id="p", material=mat,
        design_regions=[DesignRegion(id="d", target=GeometrySelection(
            selection_id="face_0", entity_type="face"))],
        obstacles=obstacles,
        load_cases=[LoadCase(id="lc", loads=[Load(
            id="l", type=LoadType.POINT_FORCE,
            target=GeometrySelection(selection_id="face_0",
                                     entity_type="face"),
            vector=(0.0, 0.0, -1.0))])],
        boundary_conditions=[BoundaryCondition(
            id="bc", type=BCType.FIXED,
            target=GeometrySelection(selection_id="face_1",
                                     entity_type="face"))],
        volume_constraint=VolumeConstraint(target_fraction=0.5),
    )


def _fake_mesh():
    return {
        "nodes": [[0., 0., 0.], [1., 0., 0.]],
        "elements": [[0, 1, 0, 1]],
        "physical_groups": {},
        "face_surface_elements": {"face_0": [[0, 1, 0]],
                                  "face_1": [[1, 0, 1]]},
        "metadata": {"face_correspondence": "deterministic"},
    }


def test_frozen_no_raise_and_preserved():
    from core.topo_problem import problem_to_solver_inputs
    problem = _problem_with_roles()
    out = problem_to_solver_inputs(
        problem, _fake_mesh(),
        selection_resolver=lambda sel, mesh: (
            {"node_indices": [0], "element_indices": [0]}
            if sel.selection_id == "face_0"
            else {"node_indices": [1], "element_indices": []}),
    )
    assert out["frozen_elements"] == [0]
    assert 0 in out["preserved_elements"]
    assert out["frozen_faces"] == ["face_0"]
    assert out["frozen_passthrough"] == "frozen_face_as_keep_in@1.0"
    roles = {h["id"]: h["role"] for h in out["halos"]}
    assert roles["fz"] == "frozen_face"


def test_no_rompe_keep_in_keep_out():
    from core.topo_problem import problem_to_solver_inputs
    problem = _problem_with_roles(frozen=False)
    out = problem_to_solver_inputs(
        problem, _fake_mesh(),
        selection_resolver=lambda sel, mesh: (
            {"node_indices": [0], "element_indices": [0]}
            if sel.selection_id == "face_0"
            else {"node_indices": [1], "element_indices": [1]}),
    )
    assert out["preserved_elements"] == [0]
    assert out["void_elements"] == [1]
    assert out["frozen_elements"] == []
    assert out["frozen_passthrough"] is None


def test_metadata_refleja_frozen_en_reconstruccion():
    from core.cad_reconstruction import ReconstructionPipeline
    nodes, elements = _mesh_two_tets()
    densities = np.array([0.0, 0.0])  # todo vacío sin frozen
    pipe = ReconstructionPipeline()
    final = pipe.run(np.asarray(nodes), np.asarray(elements), densities,
                     threshold=0.5, frozen_elements=[1])
    dens_stage = pipe.get_stage_result(
        __import__("core.cad_reconstruction", fromlist=["ReconstructionStage"])
        .ReconstructionStage.DENSITY_FIELD)
    assert dens_stage.metadata["frozen_elements"] == [1]
    assert (dens_stage.metadata["frozen_passthrough"]
            == "frozen_face_as_keep_in@1.0")
    assert float(dens_stage.data["densities"][1]) == 1.0
    assert float(dens_stage.data["densities"][0]) == 0.0
    # El elemento frozen genera isosuperficie aunque el resto esté vacío.
    assert final.metadata.get("frozen_passthrough") == "frozen_face_as_keep_in@1.0"


def test_frozen_indices_invalidos_error_explicito():
    from core.cad_reconstruction import apply_frozen_passthrough
    with pytest.raises(ValueError, match="fuera de rango"):
        apply_frozen_passthrough(np.array([0.5, 0.5]), 2, [7])
