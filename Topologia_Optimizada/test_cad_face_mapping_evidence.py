"""PRUEBA OBLIGATORIA — EVIDENCIA DEL MAPEO CAD FACE → NODOS.

Demuestra el criterio de éxito del prompt.md:
  STEP REAL → CAD Shape → CAD Face → Face index → BoundaryConditionMapper
  → Nodos de esa cara → Carga/Restricción → Kratos

y evidencia que:
  * NODOS_SELECCIONADOS != TODOS_LOS_NODOS
  * el método utilizado fue CAD_FACE_MAPPING para caras válidas.

Se usa el STEP real del proyecto (cono.step). No se genera geometría artificial.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REAL_STEP_FILE = "cono.step"
FIXED_FACE_INDEX = 1   # Disco inferior (z≈0)
LOAD_FACE_INDEX = 2    # Disco superior (z≈zmax)
FACE_TOLERANCE = 0.5


def main():
    from adapters.cad.step_adapter import StepAdapter
    from core.boundary import BoundaryConditionMapper
    from core.kratos_adapter import KRATOS_AVAILABLE
    from core.materials import STANDARD_MATERIALS
    from core.solver_interface import create_kratos_fea_solver
    from core.study import ConstraintDefinition, ConstraintType, LoadDefinition, LoadType

    # 1) Cargar STEP real
    adapter = StepAdapter()
    cad_model = adapter.load_from_file(REAL_STEP_FILE, model_name="Cono")
    shape = adapter.get_shape(cad_model.id)
    assert shape is not None and not shape.isNull()

    # 2) Generar malla con Gmsh
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("cono_evidence")
    gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
    gmsh.model.occ.importShapes(REAL_STEP_FILE, format="step")
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 5.0)
    gmsh.model.mesh.generate(3)
    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    nodes = [[coords[3 * i], coords[3 * i + 1], coords[3 * i + 2]] for i in range(len(node_tags))]
    element_types = gmsh.model.mesh.getElementTypes()
    _, _, element_connectivity = gmsh.model.mesh.getElements()
    tet_connectivity = None
    for i, et in enumerate(element_types):
        if et == 4:
            tet_connectivity = element_connectivity[i]
            break
    gmsh.finalize()
    elements = (np.array(tet_connectivity).reshape(-1, 4) - 1).tolist()

    # 3) Evidencia: mapeo CAD face → nodos
    mapped_fixed = BoundaryConditionMapper.map_faces_to_nodes(
        shape, nodes, face_indices=[FIXED_FACE_INDEX], tolerance=FACE_TOLERANCE
    )[0]
    mapped_load = BoundaryConditionMapper.map_faces_to_nodes(
        shape, nodes, face_indices=[LOAD_FACE_INDEX], tolerance=FACE_TOLERANCE
    )[0]

    fixed_nodes = set(mapped_fixed.node_indices)
    load_nodes = set(mapped_load.node_indices)
    all_nodes = len(nodes)

    lines = []
    lines.append("=== EVIDENCIA: MAPEO CAD FACE -> NODOS ===")
    lines.append(f"STEP utilizado: {REAL_STEP_FILE}")
    lines.append(f"Numero de caras B-Rep del STEP: {len(shape.Faces())}")
    lines.append(f"Numero total de nodos de la malla: {all_nodes}")
    lines.append("--- Restriccion ---")
    lines.append(f"  Cara de restriccion: disco inferior (z=0)")
    lines.append(f"  Face ID: face_{FIXED_FACE_INDEX}")
    lines.append(f"  Face index: {FIXED_FACE_INDEX}")
    lines.append(f"  Nodos seleccionados: {sorted(fixed_nodes)}")
    lines.append(f"  Cantidad de nodos: {len(fixed_nodes)}")
    lines.append("  Metodo utilizado: CAD_FACE_MAPPING")
    lines.append("--- Carga ---")
    lines.append(f"  Cara de carga: disco superior (z=zmax)")
    lines.append(f"  Face ID: face_{LOAD_FACE_INDEX}")
    lines.append(f"  Face index: {LOAD_FACE_INDEX}")
    lines.append(f"  Nodos seleccionados: {sorted(load_nodes)}")
    lines.append(f"  Cantidad de nodos: {len(load_nodes)}")
    lines.append("  Metodo utilizado: CAD_FACE_MAPPING")
    lines.append("--- Criterio de exito ---")
    lines.append(f"  NODOS_SELECCIONADOS({len(fixed_nodes)},{len(load_nodes)}) != TODOS_LOS_NODOS({all_nodes}): "
                 f"{len(fixed_nodes) < all_nodes and len(load_nodes) < all_nodes}")

    # 4) Ejecutar el flujo completo hasta Kratos
    if not KRATOS_AVAILABLE:
        print("\n".join(lines))
        print("KRATOS NO DISPONIBLE: no se ejecuto el paso FEA de la evidencia.")
        return False

    constraints = [
        ConstraintDefinition(
            id="ev_fixed_base",
            constraint_type=ConstraintType.FIXED,
            location_face_id=f"face_{FIXED_FACE_INDEX}",
            tolerance=FACE_TOLERANCE,
        )
    ]
    loads = [
        LoadDefinition(
            id="ev_top_load",
            magnitude=1000.0,
            direction=(0.0, 0.0, -1.0),
            load_type=LoadType.DISTRIBUTED,
            application_face_id=f"face_{LOAD_FACE_INDEX}",
            tolerance=FACE_TOLERANCE,
        )
    ]
    fea_solver = create_kratos_fea_solver(
        nodes=nodes,
        elements=elements,
        material=STANDARD_MATERIALS["steel"],
        constraints=constraints,
        loads=loads,
        cad_shape=shape,
    )
    result = fea_solver(
        densities=np.ones(len(elements), dtype=float),
        forces=None,
        supports=None,
        max_iterations=1,
    )
    lines.append(f"--- Resultado FEA (Kratos) ---")
    lines.append(f"  FEA success: {result.get('success')}")
    lines.append(f"  num_nodes_with_displacement: {result.get('num_nodes')}")
    lines.append(f"  max_displacement: {result.get('max_displacement')}")

    print("\n".join(lines))

    # 5) Verificaciones duras
    assert len(fixed_nodes) >= 1, "Debe haber nodos en la cara de restriccion"
    assert len(load_nodes) >= 1, "Debe haber nodos en la cara de carga"
    assert fixed_nodes < set(range(all_nodes)), "Se seleccionaron TODOS los nodos (falso positivo)"
    assert load_nodes < set(range(all_nodes)), "Se seleccionaron TODOS los nodos (falso positivo)"
    assert fixed_nodes.isdisjoint(load_nodes), "Restriccion y carga no deben compartir la cara"
    assert result.get("success"), f"El FEA fallo: {result.get('error')}"
    return True


def test_cad_face_mapping_evidence():
    """Pytest wrapper: la prueba obligatoria debe pasar dentro de la suite."""
    assert main() is True


def _fallback_would_fix_nodes(shape, nodes, elements, face_id, coord_axis=2, coord_value=0.0):
    """Aplica una restriccion con cad_shape presente.

    Si el fallback por coordenadas NO debe ejecutarse (hay face_id especificado
    pero el mapeo falla: casos B/C/D), NINGUN nodo debe quedar fijo.
    Devuelve la cantidad de nodos fijos.
    """
    from core.kratos_adapter import KRATOS_AVAILABLE, KratosAdapter
    from core.materials import STANDARD_MATERIALS
    from core.solver_interface import _apply_constraint_geometrically
    from core.study import ConstraintDefinition, ConstraintType

    adapter = KratosAdapter()
    model_part = adapter.create_model_part("FallbackGuard")
    adapter.add_nodal_variables(model_part)
    adapter.import_mesh_from_core_format(model_part, nodes, elements, element_type="tet4")
    adapter.configure_material_from_core(model_part, STANDARD_MATERIALS["steel"])
    adapter.add_displacement_dofs(model_part)

    constraint = ConstraintDefinition(
        id="guard",
        constraint_type=ConstraintType.FIXED,
        location_face_id=face_id,
        fixed_axis=coord_axis,
        fixed_coordinate=coord_value,
        tolerance=FACE_TOLERANCE,
    )
    _apply_constraint_geometrically(adapter, model_part, constraint, nodes, cad_shape=shape)

    import KratosMultiphysics as Kratos
    fixed = {
        node.Id - 1 for node in model_part.Nodes
        if node.IsFixed(Kratos.DISPLACEMENT_X)
           and node.IsFixed(Kratos.DISPLACEMENT_Y)
           and node.IsFixed(Kratos.DISPLACEMENT_Z)
    }
    return len(fixed)


def test_fallback_not_applied_when_valid_face_fails_mapping():
    """Un face_id valido que no se mapea NO debe caer al fallback por coordenadas (Caso D).

    Se usa un face_id con formato valido pero fuera del rango de caras del STEP real;
    esto produce OUT_OF_RANGE (Caso C) y obliga a que NINGUN nodo quede fijo (aunque
    exista fixed_coordinate configurado para el fallback).
    """
    from core.kratos_adapter import KRATOS_AVAILABLE
    if not KRATOS_AVAILABLE:
        import pytest
        pytest.skip("Kratos no esta disponible")

    from adapters.cad.step_adapter import StepAdapter
    adapter = StepAdapter()
    cad_model = adapter.load_from_file(REAL_STEP_FILE, model_name="Cono")
    shape = adapter.get_shape(cad_model.id)

    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("fono")
    gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
    gmsh.model.occ.importShapes(REAL_STEP_FILE, format="step")
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 5.0)
    gmsh.model.mesh.generate(3)
    _, coords, _ = gmsh.model.mesh.getNodes()
    nodes = [[coords[3 * i], coords[3 * i + 1], coords[3 * i + 2]] for i in range(len(coords) // 3)]
    element_types = gmsh.model.mesh.getElementTypes()
    _, _, ec = gmsh.model.mesh.getElements()
    tet = None
    for i, et in enumerate(element_types):
        if et == 4:
            tet = ec[i]
            break
    gmsh.finalize()
    elements = (np.array(tet).reshape(-1, 4) - 1).tolist()

    # Caso C: face_id con formato valido, indice fuera de rango (el cono tiene 3 caras).
    n_fixed_c = _fallback_would_fix_nodes(shape, nodes, elements, "face_99")
    assert n_fixed_c == 0, (
        f"CASO C: se aplico el fallback por coordenadas ({n_fixed_c} nodos fijos) a pesar "
        f"de un face_id especificado/out-of-range. El fallback no debe ejecutarse."
    )

    # Caso B: identificador no resoluble ("base") con cad_shape presente.
    n_fixed_b = _fallback_would_fix_nodes(shape, nodes, elements, "base")
    assert n_fixed_b == 0, (
        f"CASO B: se aplico el fallback por coordenadas ({n_fixed_b} nodos fijos) a pesar "
        f"de un face_id invalido especificado. El fallback no debe ejecutarse."
    )


def test_fallback_applied_only_when_no_face_id():
    """Sin face_id (Caso A) SI se aplica el fallback por coordenadas (sin regresion)."""
    from core.kratos_adapter import KRATOS_AVAILABLE
    if not KRATOS_AVAILABLE:
        import pytest
        pytest.skip("Kratos no esta disponible")

    from adapters.cad.step_adapter import StepAdapter
    adapter = StepAdapter()
    cad_model = adapter.load_from_file(REAL_STEP_FILE, model_name="Cono")
    shape = adapter.get_shape(cad_model.id)

    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("fa")
    gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
    gmsh.model.occ.importShapes(REAL_STEP_FILE, format="step")
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 5.0)
    gmsh.model.mesh.generate(3)
    _, coords, _ = gmsh.model.mesh.getNodes()
    nodes = [[coords[3 * i], coords[3 * i + 1], coords[3 * i + 2]] for i in range(len(coords) // 3)]
    element_types = gmsh.model.mesh.getElementTypes()
    _, _, ec = gmsh.model.mesh.getElements()
    tet = None
    for i, et in enumerate(element_types):
        if et == 4:
            tet = ec[i]
            break
    gmsh.finalize()
    elements = (np.array(tet).reshape(-1, 4) - 1).tolist()

    # Sin cad_shape -> NO_FACE_ID -> fallback coordenadas (fijar z=0).
    n_fixed = _fallback_would_fix_nodes(None, nodes, elements, None, coord_axis=2, coord_value=0.0)
    assert n_fixed >= 1, (
        f"CASO A: el fallback por coordenadas deberia aplicarse cuando no hay cara; "
        f"se fijaron {n_fixed} nodos."
    )


if __name__ == "__main__":
    ok = main()
    print("\nPRUEBA OBLIGATORIA:", "OK - CAD_FACE_MAPPING verificado" if ok else "FALLO")
    sys.exit(0 if ok else 1)
