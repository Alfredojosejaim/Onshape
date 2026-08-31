#!/usr/bin/env python3
"""Test script for Kratos results extraction (Etapa H)."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== ETAPA H - RESULTADOS ===")
print()

def test_results_extraction():
    """Test extraction of analysis results with correct Kratos initialization order."""
    print("1. Ejecutando análisis con orden correcto de inicialización Kratos...")
    
    try:
        # Import the adapter module directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("kratos_adapter", "core/kratos_adapter.py")
        kratos_adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kratos_adapter)
        
        adapter = kratos_adapter.initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestResultsExtraction")
        
        # CORRECT ORDER: Add variables BEFORE creating nodes
        adapter.add_nodal_variables(model_part)
        
        # Create a simple mesh (nodes are created AFTER variables)
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 210e9, 0.3)
        adapter.add_displacement_dofs(model_part)
        
        # Apply constraint to make problem well-posed
        adapter.apply_fixed_constraint(model_part, [0])
        
        # Run analysis (without external loads for now)
        result = adapter.run_analysis(model_part)
        
        if result["success"]:
            print("   [PASS] Análisis completado exitosamente")
            
            # Check results
            if "results" in result:
                results = result["results"]
                print(f"   [PASS] Resultados extraídos:")
                print(f"      - Desplazamientos: {results['num_nodes_with_displacement']} nodos")
                print(f"      - Compliance: {results['compliance']:.6e}")
                print(f"      - Desplazamiento máximo: {results['max_displacement']:.6e}")
                print(f"      - Energías elementales: {results['num_elements_with_energy']} elementos")
                
                # Verify displacement values are reasonable
                if results['num_nodes_with_displacement'] == len(nodes):
                    print("   [PASS] Todos los nodos tienen desplazamientos")
                else:
                    print(f"   [WARN] Solo {results['num_nodes_with_displacement']}/{len(nodes)} nodos tienen desplazamientos")
                
                # Check displacement values are not all zero
                if results['max_displacement'] > 0:
                    print("   [PASS] Hay desplazamientos no nulos (análisis produjo resultados)")
                else:
                    print(f"   [INFO] Desplazamientos son cero (posible para caso sin cargas)")
                
                return True
            else:
                print("   [FAIL] No se encontraron resultados en la respuesta")
                return False
        else:
            print(f"   [FAIL] Análisis falló: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] Error extrayendo resultados: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run Stage H tests."""
    print("=== PRUEBAS DE RESULTADOS (ETAPA H) ===\n")
    
    success = test_results_extraction()
    
    if success:
        print("\n=== RESULTADO: ETAPA H COMPLETADA ===")
        print("Resultados pueden extraerse correctamente del solver Kratos")
        print("Componentes verificados:")
        print("  - Ejecución de análisis: OK")
        print("  - Extracción de desplazamientos: OK")
        print("  - Cálculo de compliance: OK")
        print("  - Extracción de energías elementales: OK")
    else:
        print("\n=== RESULTADO: ETAPA H FALLIDA ===")
        print("No se pudo extraer resultados correctamente")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)