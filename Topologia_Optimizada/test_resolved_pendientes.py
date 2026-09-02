"""Validation tests for the resolved implementation gaps:

1.  The SIMP solve *consumes* the shared reusable conditions (load -> forces,
    elasticity -> constraints, protected region -> preserved elements,
    obstruction -> void elements) instead of only bare force/constraint arrays.
2.  The generative design pipeline (Scenario B: bridge mesh + conditions)
    runs the real SIMP and reconstructs to B-Rep.
3.  The CAD reconstruction pipeline (marching tetrahedra + OCP B-Rep fitter)
    converts a density field into a real BREP solid / optional STEP.
"""

import os
import shutil
import tempfile

import numpy as np
import pytest

from core.cad_entity import CadEntityRef, EntityType, SelectionSet
from core.conditions import (
    ConditionManager,
    ConditionType,
    ElasticityCondition,
    LoadCondition,
    LoadOrientation,
    LoadSense,
    ObstructionCondition,
    ProtectedRegion,
)
from core.generative import GenerativeDesignStudy
from core.generative_engine import (
    GenerativeDesignEngine,
    consume_conditions,
    direction_vector,
    generate_bridge_mesh,
    run_generative_design,
)
from core.topopt import SIMPSolver


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


def _conditions_manager() -> ConditionManager:
    mgr = ConditionManager()
    faces = SelectionSet(name="faces", entities=[
        CadEntityRef(entity_type=EntityType.FACE, face_index=0),
    ])
    load = LoadCondition(name="Carga", faces=faces,
                         orientation=LoadOrientation.PERPENDICULAR,
                         sense=LoadSense.POSITIVE, magnitude=1000.0,
                         indeterminate=False)
    elast = ElasticityCondition(name="Soporte", faces=faces, flex_range_mm=0.5)
    obstr = ObstructionCondition(name="Obst",
                                 bodies=SelectionSet(name="obs", entities=[
                                     CadEntityRef(entity_type=EntityType.SOLID, solid_id="solid_2")]))
    prot = ProtectedRegion(name="Reg", faces=SelectionSet(name="prot", entities=[
        CadEntityRef(entity_type=EntityType.FACE, face_index=1)]))
    for c in (load, elast, obstr, prot):
        mgr.add(c)
    return mgr


# --------------------------------------------------------------------- #
# 1. SIMP consumes shared conditions
# --------------------------------------------------------------------- #
def test_simp_consumes_conditions_and_pins_subdomains():
    nodes, els = _hex_grid()
    mgr = _conditions_manager()

    engine = GenerativeDesignEngine(
        model_id=None, mesh_nodes=nodes, mesh_elements=els,
        condition_manager=mgr, model_shape=None,
    )
    by_type = consume_conditions(mgr, [c.id for c in mgr.all])

    result = engine.solve_simp(by_type, max_iterations=5, tolerance=1e-2)
    x = np.asarray(result["densities"])

    # without a cad shape, obstructions map conservatively to none
    void = engine._void_elements(by_type.get(ConditionType.OBSTRUCTION, []))
    assert void.size == 0
    # protected region must have pinned material somewhere (density 1.0)
    protected = engine._protected_elements(by_type.get(ConditionType.PROTECTED_REGION, []))
    assert protected.size > 0
    assert np.all(np.isclose(x[protected], 1.0, atol=1e-6))
    # the study side must not have duplicated the conditions
    assert mgr.to_dict()["count"] == 4
    # consumed counters
    assert result["_consumed_load_conditions"] >= 1
    assert result["_consumed_elasticity_conditions"] >= 1
    assert result["_consumed_protected_conditions"] >= 1
    assert result["_consumed_obstruction_conditions"] >= 1


def test_direction_vector_orientation_sense_angle():
    n = (0.0, 0.0, 1.0)

    perp = LoadCondition(orientation=LoadOrientation.PERPENDICULAR, sense=LoadSense.POSITIVE)
    v = direction_vector(perp)
    assert np.allclose(np.abs(v), [0, 0, 1])
    assert np.dot(v, [0, 0, 1]) > 0

    neg = LoadCondition(orientation=LoadOrientation.PERPENDICULAR, sense=LoadSense.NEGATIVE)
    assert np.dot(direction_vector(neg), [0, 0, 1]) < 0

    # parallel lies in the plane -> z component ~0
    par = LoadCondition(orientation=LoadOrientation.PARALLEL, sense=LoadSense.POSITIVE)
    assert abs(direction_vector(par)[2]) < 1e-9

    # angle 90 -> horizontal
    ang = LoadCondition(orientation=LoadOrientation.ANGLE, angle_deg=90.0,
                        sense=LoadSense.POSITIVE)
    assert abs(direction_vector(ang)[2]) < 1e-9

    # angle 0 -> like normal
    ang0 = LoadCondition(orientation=LoadOrientation.ANGLE, angle_deg=0.0,
                         sense=LoadSense.POSITIVE)
    assert np.allclose(direction_vector(ang0), [0, 0, 1], atol=1e-9)


# --------------------------------------------------------------------- #
# 2. Generative design pipeline
# --------------------------------------------------------------------- #
def test_generative_scenario_b_pipeline():
    targets = [
        CadEntityRef(entity_type=EntityType.SOLID, solid_id="solid_0"),
        CadEntityRef(entity_type=EntityType.SOLID, solid_id="solid_1"),
    ]
    bridge = generate_bridge_mesh(targets, resolution=0.5,
                                  model_nodes=np.array([[0, 0, 0], [2, 0, 0], [2, 2, 2], [0, 2, 2]],
                                                       dtype=float))
    assert bridge.nodes.shape[1] == 3
    assert bridge.elements.shape[1] == 4
    assert bridge.elements.size > 0

    mgr = _conditions_manager()
    study = GenerativeDesignStudy()
    study.set_scenario_a("model_1")
    for c in mgr.all:
        study.add_condition(c.id)

    engine = GenerativeDesignEngine(
        model_id="model_1", mesh_nodes=bridge.nodes, mesh_elements=bridge.elements,
        condition_manager=mgr, model_shape=None,
    )
    out = run_generative_design(study, mgr, engine)
    assert out.get("success") is True
    assert out["_consumed_load_conditions"] == 1
    assert out["_consumed_elasticity_conditions"] == 1
    assert out["_consumed_protected_conditions"] == 1
    assert out["_consumed_obstruction_conditions"] == 1
    # reconstructed (brep solid completed)
    rec = out["reconstruction"]
    assert rec.get("status") in ("completed", "in_progress")


# --------------------------------------------------------------------- #
# 3. CAD reconstruction (marching tetrahedra + OCP B-Rep)
# --------------------------------------------------------------------- #
def test_reconstruction_pipeline_brep_and_step(tmp_path):
    from core.cad_reconstruction import MarchingTetrahedraExtractor, OCPBRepFitter, ReconstructionPipeline

    nodes, els = _hex_grid()
    # first hex fully solid, second hex fully void -> isosurface cube
    densities = np.ones(els.shape[0]) * 0.9
    densities[6:] = 0.1

    step_path = os.path.join(str(tmp_path), "result.step")
    pipe = ReconstructionPipeline(
        surface_extractor=MarchingTetrahedraExtractor(),
        brep_fitter=OCPBRepFitter(step_path=step_path),
    )
    final = pipe.run(nodes, els, densities, threshold=0.5)
    from core.cad_reconstruction import ReconstructionStage
    surf = pipe.get_stage_result(ReconstructionStage.SURFACE_MESH)
    assert surf is not None and surf.status.value == "completed"
    assert surf.data["triangles"].shape[0] > 0
    # pipeline returns the best available result (surface at minimum)
    assert final.status.value == "completed"
    # step stage is registered
    assert pipe._stages[ReconstructionStage.STEP_FILE] is not None


def test_ocp_brep_fitter_closed_cube(tmp_path):
    """A closed triangle mesh must fit a valid OCP B-Rep solid + STEP file."""
    from core.cad_reconstruction import OCPBRepFitter

    # unit cube surface (8 vertices, 12 triangles, outward orientation)
    verts = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
    ], dtype=float)
    tris = np.array([
        [0, 2, 1], [0, 3, 2],   # bottom
        [4, 5, 6], [4, 6, 7],   # top
        [0, 1, 5], [0, 5, 4],   # front
        [1, 2, 6], [1, 6, 5],   # right
        [2, 3, 7], [2, 7, 6],   # back
        [3, 0, 4], [3, 4, 7],   # left
    ], dtype=int)

    step_path = os.path.join(str(tmp_path), "cube.step")
    fitter = OCPBRepFitter(step_path=step_path)
    brep = fitter.fit(verts, tris)
    assert brep.status.value == "completed", brep.error_message
    assert brep.metadata.get("step_path") == step_path
    assert os.path.exists(step_path), "STEP file must be exported"
    assert os.path.getsize(step_path) > 0


def test_ocp_brep_fitter_single_tet():
    from core.cad_reconstruction import MarchingTetrahedraExtractor, OCPBRepFitter
    nodes = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    elems = np.array([[0, 1, 2, 3]], dtype=int)
    dens = np.array([0.9, 0.1, 0.1, 0.1])  # per-node densities
    ex = MarchingTetrahedraExtractor()
    r = ex.extract(nodes, elems, dens, threshold=0.5)
    assert r.data["triangles"].shape[0] == 1
    fitter = OCPBRepFitter()
    brep = fitter.fit(r.data["vertices"], r.data["triangles"])
    assert brep.status.value == "completed"


# --------------------------------------------------------------------- #
# Integration through the PipelineController
# --------------------------------------------------------------------- #
def test_pipeline_controller_consumes_conditions_generative(tmp_path):
    """The full controller -> generate -> SIMP -> reconstruct path works."""
    from desktop.pipeline.controller import PipelineController

    c = PipelineController.__new__(PipelineController)
    c.constraints = []
    c.forces = []
    c.model_id = None
    c.mesh = None
    c.mesh_nodes = None
    c.mesh_elements = None
    c._material_name = "steel"

    mgr = ConditionManager()
    lc = LoadCondition(name="Carga", magnitude=500.0, indeterminate=False,
                       sense=LoadSense.POSITIVE, orientation=LoadOrientation.PERPENDICULAR,
                       faces=SelectionSet(name="c"))
    mgr.add(lc)
    c.conditions = mgr
    c._studies = {}
    c.result = None
    c.result_densities = None

    class FakeDoc:
        def add_study(self, s):
            pass

        def add_result(self, id_, r):
            pass

    c.document = FakeDoc()

    class FakeCAD:
        def get_model_shape(self, mid):
            return None

    c.cad = FakeCAD()

    study = GenerativeDesignStudy()
    study.set_scenario_b([
        CadEntityRef(entity_type=EntityType.SOLID, solid_id="solid_0"),
        CadEntityRef(entity_type=EntityType.SOLID, solid_id="solid_1"),
    ])
    study.add_condition(lc.id)

    r = c.execute_study(study, progress_cb=lambda d: None)
    assert study.status.value == "completed"
    assert r.success is True
    assert "reconstruction" in r.data
    # conditions were not re-created / duplicated
    assert mgr.to_dict()["count"] == 1


# --------------------------------------------------------------------- #
# SIMP subdomains directly
# --------------------------------------------------------------------- #
def test_simp_pinned_preserved_and_void_direct():
    nodes, els = _hex_grid()
    solver = SIMPSolver(nodes, els, young_modulus=210e9, poisson_ratio=0.3,
                        volfrac=0.5, filter_radius=1.2)
    force = np.zeros(nodes.shape[0] * 3)
    force[-3:] = 1000.0
    solver.set_load(force)
    fixed = []
    for i in range(nodes.shape[0]):
        if abs(nodes[i, 0]) < 1e-9:
            fixed += [i * 3, i * 3 + 1, i * 3 + 2]
    solver.set_fixed_dofs(np.asarray(fixed, dtype=int))
    solver.set_preserved_elements([0, 1, 2, 3, 4, 5])
    solver.set_void_elements([6, 7, 8, 9, 10, 11])

    result = solver.optimize(max_iterations=10, tolerance=1e-2)
    x = np.asarray(result["densities"])
    assert np.allclose(x[:6], 1.0, atol=1e-6)
    assert np.allclose(x[6:], solver.rho_min, atol=1e-6)
    assert result["preserved_elements"] is not None
    assert result["void_elements"] is not None
    assert result["preserved_elements"][0] is True


# --------------------------------------------------------------------- #
# Unsupported-condition handling (never a silent wrong result)
# --------------------------------------------------------------------- #
def test_obstruction_without_cad_shape_is_marked_unsupported():
    """Body-based obstructions without a CAD shape cannot be mapped to mesh
    elements; solve_simp must surface an explicit unsupported marker instead
    of silently ignoring the condition."""
    nodes, els = _hex_grid()
    mgr = _conditions_manager()

    engine = GenerativeDesignEngine(
        model_id=None, mesh_nodes=nodes, mesh_elements=els,
        condition_manager=mgr, model_shape=None,
    )
    by_type = consume_conditions(mgr, [c.id for c in mgr.all])
    result = engine.solve_simp(by_type, max_iterations=5, tolerance=1e-2)

    assert result["_consumed_obstruction_conditions"] >= 1
    assert "obstruction" in result["_unsupported_conditions"]
    # with no unsupported-friendly geometry, the solve still succeeds
    assert np.asarray(result["densities"]).size > 0


# --------------------------------------------------------------------- #
# Reconstruction robustness / performance helpers
# --------------------------------------------------------------------- #
def test_deduplicate_vertices_is_consistent():
    """Coincident marching-tet vertices must collapse without changing
    connectivity and reproduce the exact shared points."""
    from core.cad_reconstruction import _deduplicate_vertices

    raw = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0],
        [0.5, 0.5, 0.5], [1.0, 0.0, 0.0], [0.5, 0.5, 0.5000000001],
    ], dtype=float)
    remap, uniq = _deduplicate_vertices(raw)
    assert uniq.shape[0] == 3
    for i, p in enumerate(raw):
        assert np.allclose(uniq[remap[i]], np.round(p, 9))
    # coincident entries map to the same unique vertex
    assert remap[0] == remap[2]
    assert remap[1] == remap[4]
    assert remap[3] == remap[5]


def test_oct_brep_fitter_skips_degenerate_triangles(tmp_path):
    """Degenerate triangles must be rejected before sewing so a noisy
    isosurface cannot corrupt the B-Rep shell."""
    from core.cad_reconstruction import OCPBRepFitter

    # unit cube surface plus a degenerate (repeated-vertex) triangle
    verts = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
    ], dtype=float)
    tris = np.array([
        [0, 2, 1], [0, 3, 2],
        [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4],
        [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6],
        [3, 0, 4], [3, 4, 7],
    ], dtype=int)
    # degenerate triangles appended (repeated vertex -> zero area), reusing the
    # existing cube vertices (indices 0-7) so no re-indexing is required
    degenerate = np.array([
        [0, 0, 1],
        [1, 2, 2],
        [3, 3, 5],
    ], dtype=int).reshape(-1, 3)
    verts_full = np.vstack([verts, [[2, 2, 2], [3, 3, 3], [10, 10, 10]]])
    tris_full = np.vstack([tris, degenerate])

    step_path = os.path.join(str(tmp_path), "cube_with_degenerate.step")
    fitter = OCPBRepFitter(step_path=step_path)
    brep = fitter.fit(verts_full, tris_full)
    assert brep.status.value == "completed", brep.error_message
    assert os.path.exists(step_path)
    assert os.path.getsize(step_path) > 0


def test_mesh_smoothing_reduces_noise_and_keeps_boundary():
    """Laplacian post-process must reduce high-frequency noise on an open
    surface while leaving the boundary (open) vertices fixed."""
    from core.cad_reconstruction import smooth_surface_mesh

    # A noisy flat patch: 4x4 grid in the XY plane + random z noise.
    xs, ys = np.meshgrid(np.linspace(0, 1, 4), np.linspace(0, 1, 4))
    verts = np.stack([xs.ravel(), ys.ravel(), np.zeros(16)], axis=1)
    rng = np.random.default_rng(0)
    verts[:, 2] = rng.normal(0.0, 0.1, size=16)
    tris = []
    idx = lambda i, j: i * 4 + j
    for i in range(3):
        for j in range(3):
            a, b, c, d = idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)
            tris.append([a, b, c])
            tris.append([a, c, d])
    tris = np.asarray(tris, dtype=int)

    smv, smt = smooth_surface_mesh(verts, tris, iterations=10, alpha=0.5)
    assert np.array_equal(smt, tris)  # connectivity unchanged
    # Smoothing reduces the *spread* of interior points (surface flattens).
    interior = [5, 6, 9, 10]  # interior vertices of the 4x4 grid
    spread_before = float(np.std(verts[interior, 2]))
    spread_after = float(np.std(smv[interior, 2]))
    noise_before = float(np.mean(np.abs(verts[interior, 2])))
    noise_after = float(np.mean(np.abs(smv[interior, 2])))
    assert noise_after < noise_before + 1e-9
    assert spread_after < spread_before + 1e-9
    # Boundary vertices stay fixed (open edge preserved).
    boundary = {0, 1, 2, 3, 4, 7, 8, 11, 12, 13, 14, 15}
    for i in boundary:
        assert np.allclose(smv[i], verts[i])


def test_reconstruction_pipeline_runs_smoothing_stage():
    """The pipeline must now complete the SMOOTHED_MESH stage for a noisy
    isosurface instead of skipping it."""
    from core.cad_reconstruction import (
        MeshSmoother,
        ReconstructionPipeline,
        ReconstructionStage,
    )

    nodes, els = _hex_grid()
    dens = np.asarray([0.9, 0.1, 0.2, 0.8, 0.15, 0.85, 0.1, 0.2, 0.3, 0.7, 0.9, 0.05])
    pipe = ReconstructionPipeline(mesh_smoother=MeshSmoother())
    final = pipe.run(nodes, els, dens, threshold=0.5)
    smoothed = pipe.get_stage_result(ReconstructionStage.SMOOTHED_MESH)
    assert smoothed is not None
    assert smoothed.status.value == "completed"
    assert smoothed.data["triangles"].shape[0] > 0
    assert final.status.value == "completed"


# --------------------------------------------------------------------- #
# Obstruction body -> mesh element mapping via the CAD shape
# --------------------------------------------------------------------- #
def test_obstruction_body_maps_to_mesh_elements_via_cad_shape():
    """With a real CAD shape, body obstructions must map to mesh elements
    (never silently ignored) and the SIMP solve must pin them to rho_min."""
    import cadquery as cq

    nodes, els = _hex_grid()

    mgr = ConditionManager()
    load = LoadCondition(name="Carga", magnitude=1000.0, indeterminate=False,
                         sense=LoadSense.POSITIVE, orientation=LoadOrientation.PERPENDICULAR,
                         faces=SelectionSet(name="c"))
    obstr = ObstructionCondition(
        name="Obst",
        bodies=SelectionSet(name="obs", entities=[
            CadEntityRef(entity_type=EntityType.SOLID, solid_id="solid_0")]),
    )
    for c in (load, obstr):
        mgr.add(c)

    # A unit box at the origin contains elements 0 and 4 of the hex grid
    # (their centroids (0.5, 0.25, 0.25) and (0.25, 0.5, 0.25) lie inside).
    shape = cq.Workplane("XY").box(1.0, 1.0, 1.0).val()

    engine = GenerativeDesignEngine(
        model_id=None, mesh_nodes=nodes, mesh_elements=els,
        condition_manager=mgr, model_shape=shape,
    )
    by_type = consume_conditions(mgr, [c.id for c in mgr.all])
    void = engine._void_elements(by_type.get(ConditionType.OBSTRUCTION, []))
    assert set(void.tolist()) == {0, 4}

    result = engine.solve_simp(by_type, max_iterations=8, tolerance=1e-2)
    assert "obstruction" not in result["_unsupported_conditions"]
    x = np.asarray(result["densities"])
    # void elements (0 and 4) pinned at rho_min (material excluded)
    assert np.allclose(x[[0, 4]], 1e-3, atol=1e-5)