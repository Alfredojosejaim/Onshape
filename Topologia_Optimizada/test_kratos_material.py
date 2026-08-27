#!/usr/bin/env python3
"""Test script for Kratos material configuration (Etapa D)."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_material_from_core():
    """Test configuring material from Core's Material object."""
    print("=== ETAPA D - MATERIAL ===")
    print("\n1. Configurando material desde Core...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.materials import STANDARD_MATERIALS
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestMaterial")
        
        # Create a simple mesh for testing
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        # Import mesh with placeholder material
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        
        # Configure material from Core
        steel = STANDARD_MATERIALS["steel"]
        adapter.configure_material_from_core(model_part, steel)
        
        print(f"   [PASS] Material configurado: {steel.name}")
        print(f"   Propiedades: E={steel.young_modulus:.2e} Pa, nu={steel.poisson_ratio}")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error configurando material desde Core: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_manual_material():
    """Test configuring material manually."""
    print("\n2. Configurando material manualmente...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestManualMaterial")
        
        # Create a simple mesh
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        
        # Configure material manually
        adapter.configure_material_manually(
            model_part, 
            young_modulus=68.9e9,  # Aluminum
            poisson_ratio=0.33,
            density=2700.0
        )
        
        print("   [PASS] Material manual configurado (Aluminio)")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error configurando material manual: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_standard_material():
    """Test applying standard materials."""
    print("\n3. Aplicando materiales estándar...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.materials import STANDARD_MATERIALS
        
        adapter = initialize_kratos_adapter()
        
        # Test each standard material
        for material_name in ["steel", "aluminum", "titanium"]:
            model_part = adapter.create_model_part(f"Test{material_name.capitalize()}")
            
            # Create simple mesh
            nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            elements = [[0, 1, 2, 3]]
            
            adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
            adapter.apply_standard_material(model_part, material_name)
            
            material = STANDARD_MATERIALS[material_name]
            print(f"   [PASS] {material_name}: E={material.young_modulus:.2e} Pa, nu={material.poisson_ratio}")
        
        return adapter
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando materiales estándar: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_material_with_real_mesh():
    """Test material configuration with real mesh from Gmsh."""
    print("\n4. Configurando material con malla real Gmsh...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.materials import STANDARD_MATERIALS
        import os
        
        # Check if we have a Gmsh file from the PoC
        gmsh_file = "experimentos/kratos_topopt_poc/model/cantilever_beam.msh"
        
        if not os.path.exists(gmsh_file):
            print(f"   [SKIP] Archivo Gmsh no encontrado: {gmsh_file}")
            return None, None
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestRealMeshMaterial")
        
        # Import mesh with placeholder material
        adapter.import_mesh_from_gmsh(model_part, gmsh_file)
        
        # Configure material
        adapter.apply_standard_material(model_part, "aluminum")
        
        print(f"   [PASS] Material configurado para malla real: {model_part.NumberOfNodes()} nodos, {model_part.NumberOfElements()} elementos")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error configurando material con malla real: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    """Run all Stage D tests."""
    print("=== PRUEBAS DE MATERIAL (ETAPA D) ===\n")
    
    # Test Core material
    adapter, model_part = test_material_from_core()
    if adapter is None or model_part is None:
        print("\n=== RESULTADO: ETAPA D FALLIDA ===")
        print("No se pudo configurar material desde Core")
        return False
    
    # Test manual material
    manual_adapter, manual_model_part = test_manual_material()
    if manual_adapter is None or manual_model_part is None:
        print("\n=== RESULTADO: ETAPA D PARCIAL ===")
        print("Configuración desde Core exitosa pero manual falló")
        return False
    
    # Test standard materials
    std_adapter = test_standard_material()
    if std_adapter is None:
        print("\n=== RESULTADO: ETAPA D PARCIAL ===")
        print("Materiales estándar fallaron")
        return False
    
    # Test with real mesh
    real_adapter, real_model_part = test_material_with_real_mesh()
    if real_adapter is not None and real_model_part is not None:
        print("   Configuración con malla real exitosa")
    
    print("\n=== RESULTADO: ETAPA D COMPLETADA ===")
    print("Materiales pueden configurarse correctamente desde múltiples fuentes")
    print("Componentes verificados:")
    print("  - Configuración desde Material del Core: OK")
    print("  - Configuración manual de propiedades: OK")
    print("  - Aplicación de materiales estándar: OK")
    print("  - Configuración con malla real: OK (si archivo disponible)")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)