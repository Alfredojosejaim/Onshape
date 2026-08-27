#!/usr/bin/env python3
"""Test script for Kratos ModelPart creation and configuration (Etapa B)."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_model_part_creation():
    """Test basic ModelPart creation."""
    print("=== ETAPA B - MODELO/MODELPART ===")
    print("\n1. Creando ModelPart básico...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestModelPart")
        
        print(f"   [PASS] ModelPart creado: {model_part}")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error creando ModelPart: {e}")
        return None, None


def test_structural_analysis_setup(adapter, model_part):
    """Test ModelPart configuration for structural analysis."""
    print("\n2. Configurando ModelPart para análisis estructural...")
    
    try:
        adapter.setup_model_part_for_structural_analysis(model_part)
        print("   [PASS] ModelPart configurado para análisis estructural")
        return True
        
    except Exception as e:
        print(f"   [ERROR] Error configurando ModelPart: {e}")
        return False


def test_displacement_dofs_empty_model(adapter, model_part):
    """Test adding DOFs to empty ModelPart (should handle gracefully)."""
    print("\n3. Verificando DOFs en ModelPart vacío...")
    
    try:
        # This should work even with no nodes
        adapter.add_displacement_dofs(model_part)
        print("   [PASS] DOFs configurados (sin nodos)")
        return True
        
    except Exception as e:
        print(f"   [ERROR] Error configurando DOFs: {e}")
        return False


def test_model_part_from_cad_model(adapter):
    """Test creating ModelPart associated with CAD model ID."""
    print("\n4. Creando ModelPart desde CAD model...")
    
    try:
        cad_model_id = "test_cad_123"
        model_part = adapter.create_model_part_from_cad_model(cad_model_id)
        
        print(f"   [PASS] ModelPart creado desde CAD model {cad_model_id}")
        return model_part
        
    except Exception as e:
        print(f"   [ERROR] Error creando ModelPart desde CAD model: {e}")
        return None


def test_model_part_info(adapter, model_part):
    """Test getting ModelPart information."""
    print("\n5. Obteniendo información del ModelPart...")
    
    try:
        info = adapter.get_model_part_info(model_part)
        
        print("   Información del ModelPart:")
        for key, value in info.items():
            print(f"     {key}: {value}")
        
        print("   [PASS] Información del ModelPart obtenida")
        return info
        
    except Exception as e:
        print(f"   [ERROR] Error obteniendo información: {e}")
        return None


def test_model_part_with_nodes(adapter):
    """Test ModelPart with some sample nodes."""
    print("\n6. Creando ModelPart con nodos de prueba...")
    
    try:
        import KratosMultiphysics as Kratos
        
        model_part = adapter.create_model_part("ModelPartWithNodes")
        
        # Add some test nodes
        for i in range(5):
            model_part.CreateNewNode(i+1, float(i), float(i), float(i))
        
        print(f"   Nodos creados: {model_part.NumberOfNodes()}")
        
        # Add DOFs
        adapter.add_displacement_dofs(model_part)
        
        # Get info
        info = adapter.get_model_part_info(model_part)
        print(f"   Información: {info}")
        
        print("   [PASS] ModelPart con nodos y DOFs creado")
        return model_part
        
    except Exception as e:
        print(f"   [ERROR] Error creando ModelPart con nodos: {e}")
        return None


def main():
    """Run all Stage B tests."""
    print("=== PRUEBAS DE MODELO/MODELPART (ETAPA B) ===\n")
    
    # Test basic creation
    adapter, model_part = test_model_part_creation()
    if adapter is None or model_part is None:
        print("\n=== RESULTADO: ETAPA B FALLIDA ===")
        print("No se pudo crear ModelPart básico")
        return False
    
    # Test structural analysis setup
    if not test_structural_analysis_setup(adapter, model_part):
        print("\n=== RESULTADO: ETAPA B PARCIAL ===")
        print("Configuración estructural falló")
        return False
    
    # Test DOFs on empty model
    if not test_displacement_dofs_empty_model(adapter, model_part):
        print("\n=== RESULTADO: ETAPA B PARCIAL ===")
        print("Configuración de DOFs falló")
        return False
    
    # Test ModelPart info
    info = test_model_part_info(adapter, model_part)
    if info is None:
        print("\n=== RESULTADO: ETAPA B PARCIAL ===")
        print("Obtención de información falló")
        return False
    
    # Test CAD model integration
    cad_model_part = test_model_part_from_cad_model(adapter)
    if cad_model_part is None:
        print("\n=== RESULTADO: ETAPA B PARCIAL ===")
        print("Integración con CAD model falló")
        return False
    
    # Test with nodes
    nodes_model_part = test_model_part_with_nodes(adapter)
    if nodes_model_part is None:
        print("\n=== RESULTADO: ETAPA B PARCIAL ===")
        print("ModelPart con nodos falló")
        return False
    
    print("\n=== RESULTADO: ETAPA B COMPLETADA ===")
    print("ModelPart puede crearse y configurarse correctamente")
    print("Componentes verificados:")
    print("  - Creación de ModelPart básico: OK")
    print("  - Configuración para análisis estructural: OK")
    print("  - Configuración de DOFs: OK")
    print("  - Integración con CAD model del Core: OK")
    print("  - Obtención de información de ModelPart: OK")
    print("  - ModelPart con nodos y DOFs: OK")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)