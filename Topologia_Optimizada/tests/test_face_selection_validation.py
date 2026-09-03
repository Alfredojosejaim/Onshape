"""Validación de mapeo geométrico de cargas/restricciones con geometría STEP real.

Cubre los criterios del prompt.md (CORRECCIÓN FOCALIZADA — MAPEO GEOMÉTRICO):

 1. Una cara/región CAD seleccionada identifica únicamente los nodos correspondientes.
 2. Una restricción se aplica exclusivamente a esos nodos.
 3. Una carga se aplica exclusivamente a esos nodos.
 4. No se modifican nodos pertenecientes a otras regiones.
 5. El flujo funciona con geometría STEP real (cono.step).
 6. El resultado llega correctamente a Kratos.

No se utiliza geometría artificial como única evidencia.
"""

import logging
import os
import sys

import numpy as np
import pytest

# Allow direct execution and pytest-safe imports from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

REAL_STEP_FILE = "cono.step"
FACE_TOLERANCE = 0.5
FIXED_FACE_INDEX = 1          # Face inferior (disco, z≈0)
LOAD_FACE_INDEX = 2           # Face superior (disco, z≈zmax)
LATERAL_FACE_INDEX = 0        # Superficie cónica lateral (curva)

pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_real_cone_model():
    """Import the real STEP into CADModel and return (cad_model, shape)."""
    from adapters.cad.step_adapter import StepAdapter

    assert os.path.exists(REAL_STEP_FILE), f"STEP real no encontrado: {REAL_STEP_FILE}"
    adapter = StepAdapter()
    cad_model = adapter.load_from_file(REAL_STEP_FILE, model_name="Cono")
    shape = adapter.get_shape(cad_model.id)
    return cad_model, shape


def mesh_real_cone(shape, element_size: float = 5.0):
    """Generate a Tet4 FEM mesh of the real STEP with Gmsh.

    Returns (nodes: list[list[float]], elements: list[list[int]]) with 0-based
    element connectivity, as consumed by the Core/Kratos integration.
    """
    import gmsh

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("cono_validation_mesh")
    gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
    gmsh.model.occ.importShapes(REAL_STEP_FILE, format="step")
    gmsh.model.occ.synchronize()
    assert len(gmsh.model.getEntities(dim=3)) > 0, "El STEP real no contiene sólidos 3D"

    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", element_size)
    gmsh.model.mesh.generate(3)

    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    nodes = [[coords[3 * i], coords[3 * i + 1], coords[3 * i + 2]] for i in range(len(node_tags))]

    element_types = gmsh.model.mesh.getElementTypes()
    _, _, element_connectivity = gmsh.model.mesh.getElements()
    tet_connectivity = None
    for i, et in enumerate(element_types):
        if et == 4:  # Tet4
            tet_connectivity = element_connectivity[i]
            break
    gmsh.finalize()

    assert tet_connectivity is not None, "La malla del STEP real no contiene elementos Tet4"
    elements = np.array(tet_connectivity).reshape(-1, 4) - 1  # 1-based → 0-based
    return nodes, elements.tolist()


def build_kratos_study(nodes, elements, material):
    """Mirror the setup steps of create_kratos_fea_solver and return the
    (adapter, model_part) pair so that tests can introspect node-level state."""
    from core.kratos_adapter import KratosAdapter

    adapter = KratosAdapter()
    model_part = adapter.create_model_part("FaceMappingValidation")
    adapter.add_nodal_variables(model_part)
    adapter.import_mesh_from_core_format(model_part, nodes, elements, element_type="tet4")
    adapter.configure_material_from_core(model_part, material)
    adapter.add_displacement_dofs(model_part)
    return adapter, model_part


def map_face_nodes(shape, nodes, face_index, tolerance=FACE_TOLERANCE):
    """Map a real CAD face index to mesh node indices (0-based)."""
    from core.boundary import BoundaryConditionMapper

    mapped = BoundaryConditionMapper.map_faces_to_nodes(
        shape, nodes, face_indices=[face_index], tolerance=tolerance
    )
    assert mapped, f"No se pudo mapear la cara {face_index}"
    return set(mapped[0].node_indices)
# ---------------------------------------------------------------------------
# Pruebas
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_cone():
    """Importa el STEP real, genera la malla y devuelve todo el contexto."""
    cad_model, shape = load_real_cone_model()
    nodes, elements = mesh_real_cone(shape)
    return {
        "cad_model": cad_model,
        "shape": shape,
        "nodes": nodes,
        "elements": elements,
    }


def test_cadmodel_preserves_all_real_step_faces(real_cone):
    """El CADModel debe conservar TODAS las caras reales del STEP (incl. la cónica curva)."""
    cad_model, _ = load_real_cone_model()
    shape = real_cone["shape"]

    n_shape_faces = len(shape.Faces())
    assert n_shape_faces == 3, (
        f"Se esperaban 3 caras B-Rep en el cono real, hay {n_shape_faces}"
    )
    assert len(cad_model.faces) == n_shape_faces, (
        "CADModel pierde caras: la cara lateral cónica (face_0) no debe descartarse"
    )

    ids = {f.id for f in cad_model.faces}
    assert {f"face_{i}" for i in range(n_shape_faces)} <= ids


def test_face_mapping_selects_only_corresponding_nodes_on_real_step(real_cone):
    """Una cara real identifica únicamente los nodos que le pertenecen."""
    shape, nodes = real_cone["shape"], real_cone["nodes"]
    nodes_arr = np.asarray(nodes, dtype=float)

    bottom = map_face_nodes(shape, nodes, FIXED_FACE_INDEX)
    top = map_face_nodes(shape, nodes, LOAD_FACE_INDEX)
    lateral = map_face_nodes(shape, nodes, LATERAL_FACE_INDEX)

    assert bottom and top and lateral, "Las tres caras reales deben mapear nodos"

    bottom_nodes = nodes_arr[list(bottom)]
    top_nodes = nodes_arr[list(top)]

    # La cara inferior está en el plano z≈0: todos sus nodos mapeados están ahí
    assert np.allclose(bottom_nodes[:, 2], 0.0, atol=FACE_TOLERANCE), \
        "Nodos de la cara inferior fuera del plano z=0"
    # ... y dentro del radio de la base (39.55 mm)
    base_radius = np.linalg.norm(bottom_nodes[:, :2], axis=1)
    assert base_radius.max() <= 39.55 + FACE_TOLERANCE

    # La cara superior está en el plano z≈zmax: todos sus nodos mapeados están ahí
    zmax = real_cone["cad_model"].bbox.zmax
    assert np.allclose(top_nodes[:, 2], zmax, atol=FACE_TOLERANCE), \
        "Nodos de la cara superior fuera del plano z=zmax"
    top_radius = np.linalg.norm(top_nodes[:, :2], axis=1)
    assert top_radius.max() <= 23.33 + FACE_TOLERANCE, \
        "Nodos de la cara superior fuera del radio del disco superior"

    # La cara lateral curva cubre toda la altura (evidencia de cara no plana real)
    lateral_nodes = nodes_arr[list(lateral)]
    assert lateral_nodes[:, 2].min() <= FACE_TOLERANCE + 1e-6
    assert lateral_nodes[:, 2].max() >= zmax - FACE_TOLERANCE

    # Las regiones de los discos (inferior/superior) son disjuntas entre sí
    assert bottom.isdisjoint(top), "Las caras inferior y superior no comparten nodos"

    # Los únicos nodos compartidos con la cara lateral son exactamente los del
    # anillo frontera (arista inferior/superior del cono): nodos que pertenecen a
    # la arista de la cara vecina, no al interior de ninguna región.
    base_r = 39.55
    top_r = 23.33
    shared_bottom_lateral = bottom & lateral
    shared_top_lateral = top & lateral
    if shared_bottom_lateral:
        radii = np.linalg.norm(nodes_arr[list(shared_bottom_lateral)][:, :2], axis=1)
        assert radii.min() >= base_r - 2 * FACE_TOLERANCE, \
            "Nodos interiores de la cara inferior compartidos con la lateral"
    if shared_top_lateral:
        radii = np.linalg.norm(nodes_arr[list(shared_top_lateral)][:, :2], axis=1)
        assert radii.min() >= top_r - 2 * FACE_TOLERANCE, \
            "Nodos interiores de la cara superior compartidos con la lateral"

    # No todos los nodos de la malla pertenecen a la cara inferior (solo su región)
    assert len(bottom) < len(nodes), "El mapeo no debe seleccionar toda la malla"
def test_constraint_applies_only_to_face_nodes_in_kratos(real_cone):
    """Una restricción por cara CAD se aplica EXCLUSIVAMENTE a esos nodos en Kratos."""
    from core.kratos_adapter import KRATOS_AVAILABLE
    from core.solver_interface import _apply_constraint_geometrically
    from core.study import ConstraintDefinition, ConstraintType

    if not KRATOS_AVAILABLE:
        pytest.skip("Kratos no está disponible")

    import KratosMultiphysics as Kratos

    shape, nodes = real_cone["shape"], real_cone["nodes"]
    from core.materials import STANDARD_MATERIALS

    adapter, model_part = build_kratos_study(nodes, real_cone["elements"], STANDARD_MATERIALS["steel"])

    expected_bottom = map_face_nodes(shape, nodes, FIXED_FACE_INDEX)
    expected_top = map_face_nodes(shape, nodes, LOAD_FACE_INDEX)

    constraint = ConstraintDefinition(
        id="fixed_base",
        constraint_type=ConstraintType.FIXED,
        location_face_id=f"face_{FIXED_FACE_INDEX}",
        tolerance=FACE_TOLERANCE,
    )
    _apply_constraint_geometrically(adapter, model_part, constraint, nodes, cad_shape=shape)

    fixed = {
        node.Id - 1 for node in model_part.Nodes
        if node.IsFixed(Kratos.DISPLACEMENT_X)
           and node.IsFixed(Kratos.DISPLACEMENT_Y)
           and node.IsFixed(Kratos.DISPLACEMENT_Z)
    }

    # 1) Solo los nodos de la cara inferior quedaron restringidos
    assert fixed == expected_bottom, (
        f"La restricción afectó {len(fixed)} nodos; se esperaban exactamente "
        f"los {len(expected_bottom)} nodos de la cara {FIXED_FACE_INDEX}"
    )

    # 2) Ningún nodo de otra región quedó modificado
    assert fixed.isdisjoint(expected_top), "Nodos de la cara superior no deben restringirse"
    assert len(fixed) >= 1
def test_load_applies_only_to_face_nodes_in_kratos(real_cone):
    """Una carga por cara CAD se aplica EXCLUSIVAMENTE a esos nodos en Kratos."""
    from core.kratos_adapter import KRATOS_AVAILABLE
    from core.solver_interface import _apply_load_geometrically
    from core.study import LoadDefinition, LoadType

    if not KRATOS_AVAILABLE:
        pytest.skip("Kratos no está disponible")

    shape, nodes = real_cone["shape"], real_cone["nodes"]
    from core.materials import STANDARD_MATERIALS

    adapter, model_part = build_kratos_study(nodes, real_cone["elements"], STANDARD_MATERIALS["steel"])

    expected_top = map_face_nodes(shape, nodes, LOAD_FACE_INDEX)
    expected_bottom = map_face_nodes(shape, nodes, FIXED_FACE_INDEX)

    magnitude = 1000.0
    load = LoadDefinition(
        id="top_load",
        magnitude=magnitude,
        direction=(0.0, 0.0, -1.0),
        load_type=LoadType.DISTRIBUTED,
        application_face_id=f"face_{LOAD_FACE_INDEX}",
        tolerance=FACE_TOLERANCE,
    )
    _apply_load_geometrically(adapter, model_part, load, nodes, cad_shape=shape)

    # La carga queda registrada en el adapter bajo los ids Kratos (1-based)
    model_part_name = str(model_part.Name)
    registered = adapter.external_loads.get(model_part_name, {})
    assert registered, "La carga no quedó registrada en el adapter"

    registered_node_ids = set(registered.keys())
    expected_kratos_ids = {node_id + 1 for node_id in expected_top}
    assert registered_node_ids == expected_kratos_ids, (
        f"Carga registrada en nodos equivocados: se esperaban los "
        f"{len(expected_top)} nodos de la cara {LOAD_FACE_INDEX}"
    )

    # Todos los valores apuntan a la dirección pedida y quedan repartidos uniformemente
    expected_per_node = magnitude / len(expected_top)
    for _, fv in registered.items():
        assert abs(fv[0]) < 1e-9 and abs(fv[1]) < 1e-9
        assert fv[2] == pytest.approx(-expected_per_node, abs=1e-9)

    # 2) Ningún nodo de otra región quedó modificado (cara inferior sin carga)
    bottom_kratos_ids = {node_id + 1 for node_id in expected_bottom}
    assert registered_node_ids.isdisjoint(bottom_kratos_ids)


def test_coordinate_fallback_still_works_when_no_cad_shape(real_cone):
    """Sin CAD shape, el fallback por coordenadas sigue operativo (sin regresión)."""
    from core.kratos_adapter import KRATOS_AVAILABLE
    from core.solver_interface import _apply_constraint_geometrically
    from core.study import ConstraintDefinition, ConstraintType

    if not KRATOS_AVAILABLE:
        pytest.skip("Kratos no está disponible")

    import KratosMultiphysics as Kratos

    nodes = real_cone["nodes"]
    from core.materials import STANDARD_MATERIALS

    adapter, model_part = build_kratos_study(nodes, real_cone["elements"], STANDARD_MATERIALS["steel"])

    constraint = ConstraintDefinition(
        id="fixed_base",
        constraint_type=ConstraintType.FIXED,
        location_face_id="base",
        fixed_axis=2,
        fixed_coordinate=0.0,
        tolerance=FACE_TOLERANCE,
    )
    # cad_shape=None → strategy 2 no aplica, se usa el fallback de coordenadas
    _apply_constraint_geometrically(adapter, model_part, constraint, nodes, cad_shape=None)

    fixed = {
        node.Id - 1 for node in model_part.Nodes
        if node.IsFixed(Kratos.DISPLACEMENT_X) and node.IsFixed(Kratos.DISPLACEMENT_Z)
    }
    assert fixed, "El fallback por coordenadas debe seguir funcionando"
    for node_id in fixed:
        assert abs(nodes[node_id][2]) <= FACE_TOLERANCE, "Nodo fijado fuera de la región z≈0"


def test_face_mapping_end_to_end_with_real_step_and_kratos(real_cone):
    """Flujo completo: STEP real → CADModel → cara → malla → nodos → carga/restricción → Kratos → FEA."""
    from core.kratos_adapter import KRATOS_AVAILABLE
    from core.materials import STANDARD_MATERIALS
    from core.solver_interface import create_kratos_fea_solver
    from core.study import ConstraintDefinition, ConstraintType, LoadDefinition, LoadType

    if not KRATOS_AVAILABLE:
        pytest.skip("Kratos no está disponible")

    shape, nodes = real_cone["shape"], real_cone["nodes"]

    constraints = [
        ConstraintDefinition(
            id="fixed_base",
            constraint_type=ConstraintType.FIXED,
            location_face_id=f"face_{FIXED_FACE_INDEX}",
            tolerance=FACE_TOLERANCE,
        )
    ]
    loads = [
        LoadDefinition(
            id="top_load",
            magnitude=1000.0,
            direction=(0.0, 0.0, -1.0),
            load_type=LoadType.DISTRIBUTED,
            application_face_id=f"face_{LOAD_FACE_INDEX}",
            tolerance=FACE_TOLERANCE,
        )
    ]

    fea_solver = create_kratos_fea_solver(
        nodes=nodes,
        elements=real_cone["elements"],
        material=STANDARD_MATERIALS["steel"],
        constraints=constraints,
        loads=loads,
        cad_shape=shape,
    )

    result = fea_solver(
        densities=np.ones(len(real_cone["elements"]), dtype=float),
        forces=None,
        supports=None,
        max_iterations=1,
    )

    assert result["success"], f"FEA falló: {result.get('error')}"
    assert result["status"] == "completed"
    assert result["num_nodes"] == len(nodes), "Todos los nodos deben resolverse"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))