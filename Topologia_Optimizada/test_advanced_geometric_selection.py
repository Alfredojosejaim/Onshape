"""Validación del motor de selección geométrica avanzada (Fase 3).

Cubre:

  1. Regiones puntuales: plano arbitrario, caja AABB, esfera, cilindro.
  2. Composición booleana: unión / intersección / exclusión.
  3. Parser de descriptores JSON (contract GeometryReference.geometry).
  4. Inyección de tolerancia por defecto solo en regiones puntuales.
  5. Selección por cara CAD exacta y selección automática por normal sobre STEP real
     (cono.step) — sin gmsh, solo mapeo geométrico.
  6. Integración Estrategia 0 en core/solver_interface (consumida antes que
     submodelpart / face mapping / fallback de coordenadas), con adapter stub.
  7. Extensión de ConstraintDefinition / LoadDefinition con el campo ``selection``.
  8. Flujo PipelineController: import real + selección avanzada por región.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REAL_STEP_FILE = "cono.step"
FACE_TOLERANCE = 0.5
FIXED_FACE_INDEX = 1          # Face inferior (disco, z≈0)
LOAD_FACE_INDEX = 2           # Face superior (disco, z≈zmax)
LATERAL_FACE_INDEX = 0        # Superficie cónica lateral (curva)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def load_real_cone_shape():
    """Importa el STEP real y devuelve (cad_model, shape, adapter)."""
    from adapters.cad.step_adapter import StepAdapter

    assert os.path.exists(REAL_STEP_FILE), f"STEP real no encontrado: {REAL_STEP_FILE}"
    adapter = StepAdapter()
    cad_model = adapter.load_from_file(REAL_STEP_FILE, model_name="Cono")
    return cad_model, adapter.get_shape(cad_model.id), adapter


@pytest.fixture(scope="module")
def real_cone_shape():
    return load_real_cone_shape()


class _RecordingAdapter:
    """Stub that records which node indices received constraints / loads."""

    def __init__(self):
        self.constraints: dict = {}
        self.loads: dict = {}
        self.submodelpart_calls = 0
        self.coordinate_filter_calls = 0

    def apply_constraint_from_core(self, model_part, constraint, node_indices):
        self.constraints[constraint.id] = list(node_indices)

    def apply_load_from_core(self, model_part, load, node_indices):
        self.loads[load.id] = list(node_indices)

    def get_nodes_from_submodelpart(self, model_part, name):
        self.submodelpart_calls += 1
        return []

    def get_nodes_by_coordinate_filter(self, model_part, coordinate, value, tolerance):
        self.coordinate_filter_calls += 1
        return []


# ---------------------------------------------------------------------------
# 1) Regiones puntuales
# ---------------------------------------------------------------------------

def test_plane_region_selection():
    from core.selection import NodeSelectionEngine

    nodes = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [5, 5, 5.01]], dtype=float
    )
    # Plano z=0 (normal +Z): pertenecen solo los nodos en z≈0
    sel = {"type": "plane", "point": [0, 0, 0], "normal": [0, 0, 1], "tolerance": 0.01}
    idx = NodeSelectionEngine.select_nodes(nodes, sel)
    assert idx == [0, 1, 2], f"Se esperaban [0,1,2], got {idx}"

    # Plano arbitrario: normal [1,1,0], pasa por el punto (0,0,0) → nodos con x==y
    sel = {"type": "plane", "point": [0, 0, 0], "normal": [1, 1, 0], "tolerance": 1e-6}
    idx = NodeSelectionEngine.select_nodes(nodes, sel)
    assert idx == [0, 3], f"Se esperaban [0, 3] (x==y), got {idx}"


def test_box_region_selection():
    from core.selection import NodeSelectionEngine

    nodes = np.array([[0, 0, 0], [1, 1, 1], [2, 2, 2], [-1, 1, 0]], dtype=float)
    sel = {"type": "box", "bbox": {"xmin": -1, "xmax": 1, "ymin": -1, "ymax": 1,
                                   "zmin": -1, "zmax": 1}, "tolerance": 0.0}
    assert NodeSelectionEngine.select_nodes(nodes, sel) == [0, 1, 3]

    # Conveniencia de plano ortogonal a un eje (acceso por índice)
    plane = NodeSelectionEngine.plane(2, 0.0)  # plano Z=0
    assert plane.contains(nodes[0]) and not plane.contains(nodes[1])


def test_sphere_region_selection():
    from core.selection import NodeSelectionEngine

    nodes = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [2, 2, 2]], dtype=float)
    sel = {"type": "sphere", "center": [0, 0, 0], "radius": 1.0, "tolerance": 1e-6}
    assert NodeSelectionEngine.select_nodes(nodes, sel) == [0, 1, 2]


def test_cylinder_region_selection():
    from core.selection import NodeSelectionEngine

    nodes = np.array(
        [[0, 0, 0], [0, 0, 5], [0.5, 0, 1], [1.0, 0, 0], [0, 0, 6], [5, 5, 0]], dtype=float
    )
    sel = {"type": "cylinder", "point": [0, 0, 0], "axis": [0, 0, 1],
           "radius": 0.6, "height": 5.0, "tolerance": 1e-6}
    # Dentro del radio y con t_axial ∈ [0, 5]
    idx = NodeSelectionEngine.select_nodes(nodes, sel)
    assert idx == [0, 1, 2], f"Se esperaban nodos axiales, got {idx}"

    # Cilindro sin límite axial: todo lo radialmente cercano al eje
    sel_ub = {"type": "cylinder", "point": [0, 0, 0], "axis": [0, 0, 1], "radius": 0.6}
    idx_ub = NodeSelectionEngine.select_nodes(nodes, sel_ub)
    assert 5 not in idx_ub and 1 in idx_ub and 0 in idx_ub


# ---------------------------------------------------------------------------
# 2) Composición booleana
# ---------------------------------------------------------------------------

def test_composition_union_intersection_exclusion():
    from core.selection import NodeSelectionEngine

    nodes = np.array(
        [[0, 0, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1], [5, 5, 5]], dtype=float
    )
    plane_z0 = {"type": "plane", "point": [0, 0, 0], "normal": [0, 0, 1], "tolerance": 1e-6}
    sphere = {"type": "sphere", "center": [0, 0, 0], "radius": 2.0}

    union = NodeSelectionEngine.select_nodes(nodes, {"operator": "union", "regions": [plane_z0, sphere]})
    assert union == [0, 1, 2, 3]

    inter = NodeSelectionEngine.select_nodes(nodes, {"operator": "intersection", "regions": [plane_z0, sphere]})
    assert inter == [0, 1, 2]

    excl = NodeSelectionEngine.select_nodes(nodes, {"operator": "exclusion", "regions": [{"type": "all"}, plane_z0]})
    assert excl == [3, 4]


# ---------------------------------------------------------------------------
# 3) Parser + tolerancia por defecto
# ---------------------------------------------------------------------------

def test_parse_region_errors_and_roundtrip():
    from core.selection import parse_region, RegionType, AllRegion

    assert isinstance(parse_region({"type": "all"}), AllRegion)
    assert parse_region({"type": "sphere", "center": [0, 0, 0], "radius": 1}).to_dict()["type"] ==\
        RegionType.SPHERE

    with pytest.raises(ValueError):
        parse_region({"type": "torus"})
    with pytest.raises(ValueError):
        parse_region({"operator": "difference", "regions": []})
    with pytest.raises(ValueError):
        parse_region("not-a-region")


def test_default_tolerance_injection_only_point_based():
    from core.selection import NodeSelectionEngine

    # Caja con techo en z=0: sin tolerancia el nodo z=0.02 queda fuera.
    nodes = np.array([[0, 0, 0], [1, 0, 0], [0, 0, 0.02]], dtype=float)
    sel = {"type": "box", "bbox": {"xmin": -1, "xmax": 1, "ymin": -1, "ymax": 1,
                                   "zmin": -1, "zmax": 0}}
    # Sin tolerancia: solo los nodos del suelo
    assert NodeSelectionEngine.select_nodes(nodes, sel, default_tolerance=None) == [0, 1]
    # Con tolerancia inyectada (0.05): la caja se infla y el nodo z=0.02 entra
    assert NodeSelectionEngine.select_nodes(nodes, sel, default_tolerance=0.05) == [0, 1, 2]

    # En composiciones, la inyección llega a los hijos puntuales
    comp = {"operator": "union", "regions": [sel, {"type": "all"}]}
    assert len(NodeSelectionEngine.select_nodes(nodes, comp, default_tolerance=0.05)) == 3


# ---------------------------------------------------------------------------
# 4) Selección por cara y por normal con STEP real (sin gmsh)
# ---------------------------------------------------------------------------

def test_normal_region_matches_real_step_faces(real_cone_shape):
    from core.selection import NodeSelectionEngine, NormalRegion

    _, shape, _ = real_cone_shape
    nodes = np.array([[0, 0, 0.0], [0, 0, shape.BoundingBox().zmax]], dtype=float)

    # Los discos plano del cono apuntan +Z (superior) / −Z (inferior)
    top = NodeSelectionEngine.select_nodes(nodes, NormalRegion((0, 0, 1), angle_tolerance_deg=5),
                                           cad_shape=shape)
    bottom = NodeSelectionEngine.select_nodes(nodes, NormalRegion((0, 0, -1), angle_tolerance_deg=5),
                                              cad_shape=shape)
    assert len(top) >= 1, "La cara superior debe seleccionarse con normal +Z"
    assert len(bottom) >= 1, "La cara inferior debe seleccionarse con normal −Z"

    # La cara lateral cónica no es normal a Z (radio) → no debe coincidir
    lateral = NodeSelectionEngine.select_nodes(nodes, NormalRegion((1, 0, 0), angle_tolerance_deg=5),
                                               cad_shape=shape)
    assert set(lateral) < set(top) | set(bottom), "La normal X no debe emparejar masas Z"

    # Descriptor: accessor directo por índice de cara
    face_sel = {"type": "face", "face_indices": [FIXED_FACE_INDEX], "tolerance": FACE_TOLERANCE}
    mapped = NodeSelectionEngine.select_nodes(nodes, face_sel, cad_shape=shape)
    assert len(mapped) >= 1
    assert all(abs(nodes[i, 2]) <= FACE_TOLERANCE for i in mapped)


def test_face_region_selects_correct_side_on_real_step(real_cone_shape):
    from core.selection import NodeSelectionEngine

    cad_model, shape, _ = real_cone_shape
    zmax = cad_model.bbox.zmax

    # Nodos sintéticos: puntos sobre el disco inferior, el disco superior y lejos.
    nodes = np.array(
        [[0, 0, 0.0], [10, 0, 0.0], [0, 0, zmax], [10, 0, zmax], [100, 100, 100]],
        dtype=float,
    )
    top_sel = {"type": "face", "face_indices": [LOAD_FACE_INDEX], "tolerance": 10.0}
    idx_top = NodeSelectionEngine.select_nodes(nodes, top_sel, cad_shape=shape)
    assert set(idx_top) == {2, 3}, f"La cara superior debe seleccionar (2,3), got {idx_top}"

    bottom_sel = {"type": "face", "face_indices": [FIXED_FACE_INDEX], "tolerance": 10.0}
    idx_bot = NodeSelectionEngine.select_nodes(nodes, bottom_sel, cad_shape=shape)
    assert set(idx_bot) == {0, 1}, f"La cara inferior debe seleccionar (0,1), got {idx_bot}"


# ---------------------------------------------------------------------------
# 5) Integración Estrategia 0 en solver_interface (adapter stub)
# ---------------------------------------------------------------------------

def test_advanced_selection_strategy0_consumed_first():
    from core.selection import AllRegion
    from core.solver_interface import _apply_constraint_geometrically, _apply_load_geometrically
    from core.study import ConstraintDefinition, ConstraintType, LoadDefinition, LoadType

    nodes = [[0, 0, 0], [1, 0, 0], [5, 5, 5]]
    adapter = _RecordingAdapter()

    c = ConstraintDefinition(id="c1", constraint_type=ConstraintType.FIXED,
                             location_face_id="face_0",
                             selection={"type": "all"})
    _apply_constraint_geometrically(adapter, None, c, nodes, cad_shape=None)
    assert adapter.constraints["c1"] == [0, 1, 2], "La selección avanzada (all) se aplica primero"
    assert adapter.submodelpart_calls == 0, "No debe intentarse submodelpart antes"
    assert adapter.coordinate_filter_calls == 0, "No debe usarse el fallback de coordenadas"

    l = LoadDefinition(id="l1", magnitude=100.0, direction=(0, 0, -1),
                       load_type=LoadType.DISTRIBUTED,
                       application_face_id="face_1",
                       selection={"type": "all"})
    _apply_load_geometrically(adapter, None, l, nodes, cad_shape=None)
    assert adapter.loads["l1"] == [0, 1, 2]


def test_advanced_selection_fail_is_loud_no_fallback():
    from core.solver_interface import _apply_constraint_geometrically
    from core.study import ConstraintDefinition, ConstraintType

    nodes = [[0, 0, 0], [1, 0, 0], [5, 5, 5]]
    adapter = _RecordingAdapter()

    # Selección explícita que no coincide con ningún nodo → se reporta y NO se
    # cae al fallback de coordenadas (REGLA FINAL).
    c = ConstraintDefinition(
        id="c_far", constraint_type=ConstraintType.FIXED,
        location_face_id="", fixed_axis=2, fixed_coordinate=0.0,
        tolerance=0.01,
        selection={"type": "plane", "point": [100, 100, 100],
                   "normal": [0, 0, 1], "tolerance": 0.001},
    )
    c.tolerance = 0.001
    _apply_constraint_geometrically(adapter, None, c, nodes, cad_shape=None)
    assert "c_far" not in adapter.constraints, "Selección vacía no aplica restricción"
    assert adapter.coordinate_filter_calls == 0, "No debe silenciarse el fallo con fallback"


def test_advanced_selection_no_fallback_when_selection_none():
    """Sin selección avanzada, las estrategias previas siguen vigentes (Caso A)."""
    from core.solver_interface import _apply_constraint_geometrically
    from core.study import ConstraintDefinition, ConstraintType

    nodes = [[0, 0, 0], [1, 0, 0], [5, 5, 5]]
    adapter = _RecordingAdapter()

    c = ConstraintDefinition(id="c_base", constraint_type=ConstraintType.FIXED,
                             location_face_id="", fixed_axis=2, fixed_coordinate=0.0,
                             tolerance=0.01)
    _apply_constraint_geometrically(adapter, None, c, nodes, cad_shape=None)
    # Sin cara y sin selección avanzada → se usa el fallback de coordenadas.
    assert adapter.coordinate_filter_calls == 1, "El fallback por coordenadas sigue activo"
    assert "c_base" not in adapter.constraints


def test_definition_selection_field_roundtrip():
    from core.study import ConstraintDefinition, ConstraintType, LoadDefinition, LoadType

    sel = {"operator": "intersection",
           "regions": [{"type": "box", "bbox": {"xmin": 0, "xmax": 1, "ymin": 0,
                                                "ymax": 1, "zmin": 0, "zmax": 1}}]}
    c = ConstraintDefinition(id="c", constraint_type=ConstraintType.FIXED,
                             location_face_id="face_0", selection=sel)
    assert c.to_dict()["selection"] == sel

    l = LoadDefinition(id="l", magnitude=1.0, direction=(0, 0, -1),
                       load_type=LoadType.POINT, selection=sel)
    assert l.to_dict()["selection"] == sel


# ---------------------------------------------------------------------------
# 6) Tessellation con mapeo de caras (viewport)
# ---------------------------------------------------------------------------

def test_tessellation_face_mapping_ranges_cover_all_triangles(real_cone_shape):
    cad_model, _shape, adapter = real_cone_shape
    tess = adapter.tessellate(cad_model, face_mapping=True).to_dict()

    counts = [int(r["count"]) for r in tess["face_triangles"]]
    assert sum(counts) == tess["num_triangles"], "Los rangos deben cubrir todos los triángulos"
    starts = [int(r["start"]) for r in tess["face_triangles"]]
    assert starts[0] == 0
    assert [int(r["face_index"]) for r in tess["face_triangles"]] == [0, 1, 2]

    # Sin face_mapping el comportamiento previo se mantiene (regresión)
    legacy = adapter.tessellate(cad_model, face_mapping=False).to_dict()
    assert legacy.get("face_triangles", []) == []


# ---------------------------------------------------------------------------
# 7) PipelineController: selección avanzada end-to-end
# ---------------------------------------------------------------------------

def test_controller_applies_advanced_selection_region():
    from desktop.pipeline.controller import PipelineController

    controller = PipelineController()
    out = controller.import_model(REAL_STEP_FILE)
    mesh = controller.generate_mesh()

    nodes = controller.mesh_nodes
    bbox = out["model"].bbox

    # Restricción: región cilíndrica en el interior de la base (z<tope inferior)
    z_lo = bbox.zmin
    z_hi = bbox.zmin + 0.15 * (bbox.zmax - bbox.zmin)
    csel = {"type": "box",
            "bbox": {"xmin": bbox.xmin, "xmax": bbox.xmax,
                     "ymin": bbox.ymin, "ymax": bbox.ymax,
                     "zmin": z_lo, "zmax": z_hi}}
    controller.constraints = [{"constraint_type": "fixed", "location": "",
                               "selection": csel}]
    controller.forces = [{"magnitude": 500.0, "direction_x": 0.0,
                          "direction_y": 0.0, "direction_z": -1.0}]

    fixed = controller._apply_constraints(nodes)
    assert fixed.size > 0, "Debe fijarse al menos un DOF en la región seleccionada"
    dofs = set(fixed)
    constrained_nodes = {d // 3 for d in dofs}
    for ni in constrained_nodes:
        x, y, z = nodes[ni]
        assert z_lo - 1e-6 <= z <= z_hi + 1e-6, "Nodo fijado fuera de la región avanzada"

    # Ningún nodo fuera de la caja quedó restringido
    assert all(z_lo - 1e-6 <= nodes[ni, 2] <= z_hi + 1e-6 for ni in constrained_nodes)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))