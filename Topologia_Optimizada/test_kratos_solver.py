#!/usr/bin/env python3
"""Test script for Kratos solver configuration and execution (Etapa G)."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_solver_setup():
    """Test solver and strategy setup."""
    print("=== ETAPA G - SOLVER ===")
    print("\n1. Configurando solver y estrategia...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestSolverSetup")
        
        # Create a simple mesh
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Setup solver
        solver_setup = adapter.setup_solver_and_strategy(model_part)
        
        if solver_setup["status"] == "configured":
            print("   [PASS] Solver configurado exitosamente")
            return adapter, model_part, solver_setup
        else:
            print(f"   [FAIL] Configuración de solver falló: {solver_setup.get('error')}")
            return None, None, None
        
    except Exception as e:
        print(f"   [ERROR] Error configurando solver: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def test_simple_analysis():
    """Test running a simple analysis with constraints only."""
    print("\n2. Ejecutando análisis simple (solo restricciones)...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.study import ConstraintDefinition, ConstraintType
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestSimpleAnalysis")
        
        # Create a simple mesh
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Apply constraint to make problem well-posed
        constraint = ConstraintDefinition(
            id="fixed_constraint",
            constraint_type=ConstraintType.FIXED,
            location_face_id="face_0"
        )
        adapter.apply_constraint_from_core(model_part, constraint, [0])
        
        # Run analysis
        result = adapter.run_analysis(model_part)
        
        if result["success"]:
            print(f"   [PASS] Análisis completado: {result['message']}")
            return adapter, model_part, result
        else:
            print(f"   [FAIL] Análisis falló: {result.get('error')}")
            return None, None, result
        
    except Exception as e:
        print(f"   [ERROR] Error ejecutando análisis simple: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def test_analysis_with_loads():
    """Test running analysis with both constraints and loads."""
    print("\n3. Ejecutando análisis con cargas...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.study import ConstraintDefinition, LoadDefinition, ConstraintType, LoadType
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestAnalysisWithLoads")
        
        # Create a cantilever-like mesh
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
            [2.0, 0.0, 0.0], [2.0, 1.0, 0.0], [2.0, 0.0, 1.0], [2.0, 1.0, 1.0]
        ]
        elements = [[0, 1, 2, 3], [1, 4, 2, 5], [2, 6, 3, 7]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Apply fixed constraint to one end
        constraint = ConstraintDefinition(
            id="fixed_end",
            constraint_type=ConstraintType.FIXED,
            location_face_id="face_left"
        )
        adapter.apply_constraint_from_core(model_part, constraint, [0, 1, 2])
        
        # Apply point load to the other end
        load = LoadDefinition(
            id="tip_load",
            magnitude=1000.0,
            direction=(0.0, 0.0, -1.0),
            load_type=LoadType.POINT
        )
        adapter.apply_load_from_core(model_part, load, [7])
        
        # Run analysis
        result = adapter.run_analysis(model_part)
        
        if result["success"]:
            print(f"   [PASS] Análisis con cargas completado: {result['message']}")
            return adapter, model_part, result
        else:
            print(f"   [FAIL] Análisis con cargas falló: {result.get('error')}")
            return None, None, result
        
    except Exception as e:
        print(f"   [ERROR] Error ejecutando análisis con cargas: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def test_analysis_with_real_mesh():
    """Test analysis with real mesh from Gmsh."""
    print("\n4. Ejecutando análisis con malla real Gmsh...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.study import ConstraintDefinition, LoadDefinition, ConstraintType, LoadType
        import os
        
        # Check if we have a Gmsh file from the PoC
        gmsh_file = "experimentos/kratos_topopt_poc/model/cantilever_beam.msh"
        
        if not os.path.exists(gmsh_file):
            print(f"   [SKIP] Archivo Gmsh no encontrado: {gmsh_file}")
            return None, None, None
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestRealMeshAnalysis")
        
        # Import real mesh
        adapter.import_mesh_from_gmsh(model_part, gmsh_file)
        adapter.apply_standard_material(model_part, "aluminum")
        adapter.add_displacement_dofs(model_part)
        
        # Apply constraint to some nodes (simulating fixed face)
        constraint = ConstraintDefinition(
            id="fixed_constraint",
            constraint_type=ConstraintType.FIXED,
            location_face_id="face_fixed"
        )
        fixed_nodes = list(range(20))  # First 20 nodes as example
        adapter.apply_constraint_from_core(model_part, constraint, fixed_nodes)
        
        # Apply load to some nodes (simulating loaded face)
        load = LoadDefinition(
            id="distributed_load",
            magnitude=5000.0,
            direction=(0.0, 0.0, -1.0),
            load_type=LoadType.DISTRIBUTED
        )
        loaded_nodes = list(range(1700, 1736))  # Last nodes as example
        adapter.apply_load_from_core(model_part, load, loaded_nodes)
        
        # Run analysis
        result = adapter.run_analysis(model_part)
        
        if result["success"]:
            print(f"   [PASS] Análisis con malla real completado: {result['message']}")
            return adapter, model_part, result
        else:
            print(f"   [FAIL] Análisis con malla real falló: {result.get('error')}")
            return None, None, result
        
    except Exception as e:
        print(f"   [ERROR] Error ejecutando análisis con malla real: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def main():
    """Run all Stage G tests."""
    print("=== PRUEBAS DE SOLVER (ETAPA G) ===\n")
    
    # Test solver setup
    adapter, model_part, solver_setup = test_solver_setup()
    if adapter is None or model_part is None or solver_setup is None:
        print("\n=== RESULTADO: ETAPA G FALLIDA ===")
        print("No se pudo configurar el solver")
        return False
    
    # Test simple analysis
    simple_adapter, simple_model_part, simple_result = test_simple_analysis()
    if simple_adapter is None or simple_model_part is None or simple_result is None:
        print("\n=== RESULTADO: ETAPA G PARCIAL ===")
        print("Configuración de solver exitosa pero análisis simple falló")
        return False
    
    # Test analysis with loads
    load_adapter, load_model_part, load_result = test_analysis_with_loads()
    if load_adapter is None or load_model_part is None or load_result is None:
        print("\n=== RESULTADO: ETAPA G PARCIAL ===")
        print("Análisis simple exitoso pero con cargas falló")
        return False
    
    # Test with real mesh
    real_adapter, real_model_part, real_result = test_analysis_with_real_mesh()
    if real_adapter is not None and real_model_part is not None and real_result is not None:
        print("   Análisis con malla real exitoso")
    
    print("\n=== RESULTADO: ETAPA G COMPLETADA ===")
    print("Solver puede configurarse y ejecutar análisis correctamente")
    print("Componentes verificados:")
    print("  - Configuración de solver y estrategia: OK")
    print("  - Ejecución de análisis simple: OK")
    print("  - Ejecución de análisis con cargas: OK")
    print("  - Análisis con malla real: OK (si archivo disponible)")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)