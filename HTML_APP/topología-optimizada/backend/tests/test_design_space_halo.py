"""Tests design space/envelope + halo consistente + tolerancia adaptativa.

Aprobado explícitamente por el usuario (15-sep-2026):
- Design space envelope: dominio donde el optimizador puede CRECER material.
- Halo robusto: los nodos BC del halo deben ser los MISMOS que aplican la BC
  (con su fallback), no un conjunto vacío cuando la cara no mapea.
- Tolerancia cara->nodo mesh-adaptativa (`face_tolerance`).
"""
import numpy as np
import pytest

from core.conditions import condition_from_dict, ConditionManager, ConditionType
from core.generative import GenerativeDesignStudy
from core.generative_engine import (
    GenerativeDesignEngine,
    generate_design_space_mesh,
    run_generative_design,
)
from core.materials import STANDARD_MATERIALS
from core.optimization_studies import TopOptParameters
from tests.test_gcmma import kuhn_bar


def _mesh(nx=2):
    nodes, els, nid = kuhn_bar(nx)
    return np.asarray(nodes, dtype=float), np.asarray(els, dtype=int), nid


def _load_cond():
    return condition_from_dict({
        "type": "load", "name": "Carga",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "orientation": "perpendicular", "reference_plane_normal": [0, 0, 1],
        "angle_deg": None, "sense": "positive", "magnitude": 1000.0,
        "indeterminate": False, "unit": "N", "metadata": {},
        "direction": [0.0, 0.0, 1.0],
    })


def _faced_elasticity(face_index=3):
    return condition_from_dict({
        "type": "elasticity", "name": "Fijacion",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": face_index}], "mode": "multi"},
        "flex_range_mm": None, "metadata": {},
    })


def _engine(nodes, els, manager, **kw):
    return GenerativeDesignEngine(
        model_id=None, mesh_nodes=nodes, mesh_elements=els,
        material=STANDARD_MATERIALS["steel"], condition_manager=manager, **kw)


def test_design_space_mesh_bounds_cap_and_tet_count():
    nodes, _, _ = _mesh(3)
    env = generate_design_space_mesh(nodes, resolution=0.5, padding=0.25)
    lo = nodes.min(axis=0) - 0.25
    hi = nodes.max(axis=0) + 0.25
    assert np.all(env.nodes.min(axis=0) >= lo - 1e-9)
    assert np.all(env.nodes.max(axis=0) <= hi + 1e-9)
    assert env.elements.shape[0] == 6 * len(env.voxels)
    # El cap de voxels engrosa la resolución si hace falta.
    tiny = generate_design_space_mesh(nodes, resolution=0.01, max_voxels=100)
    assert len(tiny.voxels) <= 100
    assert tiny.target_node_sets["resolution"][0] > 0.01


def test_halo_nodes_match_applied_bc_fallback():
    """Sin CAD shape, las caras no mapean: el halo debe usar el MISMO fallback
    que la BC aplicada (antes quedaba vacío -> zona BC sin proteger)."""
    nodes, els, _ = _mesh(4)
    mgr = ConditionManager()
    supp = _faced_elasticity()
    mgr.add(supp)
    eng = _engine(nodes, els, mgr)  # model_shape=None
    conds = {ConditionType.ELASTICITY: [supp], ConditionType.LOAD: [],
             ConditionType.PROTECTED_REGION: [], ConditionType.OBSTRUCTION: []}
    _, fixed, _, _, unsupported = eng._map_conditions_to_problem(
        conds, raise_on_unmapped_face=False)
    assert "elasticity(fallback_base_Z)" in unsupported
    fixed_nodes = sorted({int(d) // 3 for d in fixed})
    halo_nodes = eng._support_node_indices(conds)
    assert fixed_nodes and fixed_nodes == halo_nodes


def test_face_mapping_adaptive_tolerance_retry():
    """Malla NO conforme (voxel/provisional): los nodos no están sobre la cara,
    así que 0.5mm no mapea; el reintento con 2·h sí. Regresión de la fijación
    "degradada" que dejaba la isosuperficie abierta y la reconstrucción inválida.
    """
    import cadquery as cq
    from core.boundary import BoundaryConditionMapper

    shape = cq.Solid.makeBox(10.0, 10.0, 10.0)
    faces = shape.Faces()
    centers = [float(f.Center().z) for f in faces]
    zmin = min(centers)
    bottom = centers.index(zmin)
    cx = float(faces[bottom].Center().x)
    cy = float(faces[bottom].Center().y)

    xs = [cx - 5.0, cx - 2.5, cx, cx + 2.5, cx + 5.0]
    ys = [cy - 5.0, cy - 2.5, cy, cy + 2.5, cy + 5.0]
    nodes = [[x, y, zmin - 3.0] for x in xs for y in ys]  # 3mm bajo la cara
    nodes.append([cx, cy, zmin])                           # nodo sobre la cara
    top = len(nodes) - 1

    def nid(i, j):
        return i * len(xs) + j

    els = []
    for i in range(len(xs) - 1):
        for j in range(len(xs) - 1):
            els.append([nid(i, j), nid(i + 1, j), nid(i, j + 1), top])
    nodes_arr = np.asarray(nodes, dtype=float)
    els_arr = np.asarray(els, dtype=int)

    # A 0.5mm solo el nodo sobre la cara mapea (casi ninguno).
    strict = BoundaryConditionMapper.map_faces_to_nodes(
        shape, nodes_arr.tolist(), [bottom], tolerance=0.5)
    assert len(strict[0].node_indices) <= 1

    eng = GenerativeDesignEngine(
        model_id=None, mesh_nodes=nodes_arr, mesh_elements=els_arr,
        material=STANDARD_MATERIALS["steel"], condition_manager=None,
        model_shape=shape)
    mapped = eng._select_nodes_for_faces([bottom])
    assert len(mapped) > 1  # el reintento 2·h mapea los nodos a 3mm


def test_envelope_runs_and_reports_design_space():
    nodes, els, _ = _mesh(3)
    mgr = ConditionManager()
    load = _load_cond()
    supp = _faced_elasticity()
    mgr.add(load)
    mgr.add(supp)
    study = GenerativeDesignStudy(name="g")
    study.scenario = "A"
    study.conditions = [load.id, supp.id]
    op = TopOptParameters()
    op.volume_fraction = 0.4
    op.max_iterations = 2
    op.filter_radius = 0.6
    study.optimization_params = op
    eng = _engine(nodes, els, mgr)
    result = run_generative_design(study, mgr, eng, design_space="box",
                                   design_space_resolution=0.6)
    meta = result.get("_design_space")
    assert meta and meta["design_space"] == "envelope"
    assert meta["num_elements"] == 6 * meta["voxels"]
    assert np.all(np.isfinite(np.asarray(result["densities"], dtype=float)))
    # El envelope desactiva los triángulos de superficie del modelo.
    assert eng._surface_matches_mesh is False
    assert eng._face_tolerance == pytest.approx(1.5 * meta["resolution"])


def test_keepout_face_voids_full_hole_passage_in_envelope():
    """KEEPOUT-PASSAGE: en envelope, el keep-out por cara de un agujero debe
    vaciar el pasaje COMPLETO, no solo el forro (~0.75 voxel). Regresión del
    reporte: los agujeros de tornillo/buje quedaban rellenos en generativa."""
    import cadquery as cq
    box = cq.Solid.makeBox(20.0, 20.0, 10.0)
    cutter = cq.Solid.makeCylinder(
        2.5, 14.0, cq.Vector(10.0, 10.0, -2.0), cq.Vector(0, 0, 1))
    shape = box.cut(cutter)
    wall = next(i for i, f in enumerate(shape.Faces())
                if f.geomType() == "CYLINDER")
    xs = np.linspace(0, 20, 6)
    ys = np.linspace(0, 20, 6)
    zs = np.linspace(0, 10, 4)
    grid = np.array([[x, y, z] for x in xs for y in ys for z in zs])
    env = generate_design_space_mesh(grid, resolution=2.0, padding=1.0)
    mgr = ConditionManager()
    eng = _engine(np.asarray(env.nodes), np.asarray(env.elements), mgr,
                  model_shape=shape, surface_matches_mesh=False)
    eng._env_resolution = float(env.target_node_sets["resolution"][0])
    keep = condition_from_dict({
        "type": "obstruction", "name": "K",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": wall}], "mode": "multi"},
        "offset_mm": None, "metadata": {},
    })
    void = eng._void_elements([keep])
    void_set = set(int(i) for i in np.asarray(void).tolist())
    bb = shape.Faces()[wall].BoundingBox()
    centroids = eng._element_centroids()
    passage = [i for i in range(centroids.shape[0])
               if (bb.xmin <= centroids[i][0] <= bb.xmax
                   and bb.ymin <= centroids[i][1] <= bb.ymax
                   and bb.zmin <= centroids[i][2] <= bb.zmax)
               and not eng._point_inside_shape(centroids[i])]
    assert passage, "el agujero no contiene centroides del envelope"
    assert set(passage) <= void_set


def test_envelope_rejects_unknown_design_space():
    nodes, els, _ = _mesh(2)
    mgr = ConditionManager()
    load = _load_cond()
    mgr.add(load)
    study = GenerativeDesignStudy(name="g")
    study.scenario = "A"
    study.conditions = [load.id]
    study.optimization_params = TopOptParameters()
    with pytest.raises(ValueError, match="design_space"):
        run_generative_design(study, mgr, _engine(nodes, els, mgr),
                              design_space="bogus")
