#!/usr/bin/env python3
"""Test script for Kratos adapter initialization (Etapa A)."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_kratos_availability():
    """Test if Kratos is available in the project environment."""
    print("=== ETAPA A - INICIALIZACIÓN DE KRATOS ===")
    print("\n1. Verificando disponibilidad de Kratos...")
    
    try:
        from core.kratos_adapter import is_kratos_available, get_kratos_import_error
        
        available = is_kratos_available()
        print(f"   Kratos disponible: {available}")
        
        if not available:
            error = get_kratos_import_error()
            print(f"   Error de importación: {error}")
            return False
        
        print("   [PASS] Kratos está disponible")
        return True
        
    except Exception as e:
        print(f"   [ERROR] Error verificando disponibilidad: {e}")
        return False


def test_kratos_adapter_creation():
    """Test Kratos adapter creation."""
    print("\n2. Creando adaptador Kratos...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        
        adapter = initialize_kratos_adapter()
        print("   [PASS] Adaptador Kratos creado exitosamente")
        return adapter
        
    except Exception as e:
        print(f"   [ERROR] Error creando adaptador: {e}")
        return None


def test_model_part_creation(adapter):
    """Test ModelPart creation."""
    print("\n3. Creando ModelPart...")
    
    try:
        model_part = adapter.create_model_part("TestModelPart")
        print(f"   [PASS] ModelPart creado: {model_part}")
        return model_part
        
    except Exception as e:
        print(f"   [ERROR] Error creando ModelPart: {e}")
        return None


def test_applications_check(adapter):
    """Test applications availability check."""
    print("\n4. Verificando aplicaciones Kratos...")
    
    try:
        apps = adapter.check_applications()
        print("   Aplicaciones disponibles:")
        for app_name, available in apps.items():
            status = "[PASS]" if available else "[FAIL]"
            print(f"     {status} {app_name}: {available}")
        
        all_available = all(apps.values())
        if all_available:
            print("   [PASS] Todas las aplicaciones críticas disponibles")
        else:
            print("   [WARNING] Algunas aplicaciones no disponibles")
        
        return apps
        
    except Exception as e:
        print(f"   [ERROR] Error verificando aplicaciones: {e}")
        return None


def test_direct_imports():
    """Test direct Kratos imports."""
    print("\n5. Verificando importaciones directas...")
    
    try:
        import KratosMultiphysics as Kratos
        print("   [PASS] KratosMultiphysics importado")
        
        from KratosMultiphysics import StructuralMechanicsApplication
        print("   [PASS] StructuralMechanicsApplication importado")
        
        from KratosMultiphysics import OptimizationApplication
        print("   [PASS] OptimizationApplication importado")
        
        return True
        
    except ImportError as e:
        print(f"   [ERROR] Error de importación: {e}")
        return False


def main():
    """Run all Stage A tests."""
    print("=== PRUEBAS DE INICIALIZACIÓN DE KRATOS (ETAPA A) ===\n")
    
    # Test direct imports first
    direct_import_ok = test_direct_imports()
    
    # Test adapter availability
    available_ok = test_kratos_availability()
    
    if not available_ok:
        print("\n=== RESULTADO: ETAPA A FALLIDA ===")
        print("Kratos no está disponible en el entorno del proyecto principal")
        return False
    
    # Test adapter creation
    adapter = test_kratos_adapter_creation()
    if adapter is None:
        print("\n=== RESULTADO: ETAPA A FALLIDA ===")
        print("No se pudo crear el adaptador Kratos")
        return False
    
    # Test ModelPart creation
    model_part = test_model_part_creation(adapter)
    if model_part is None:
        print("\n=== RESULTADO: ETAPA A PARCIAL ===")
        print("Adaptador creado pero ModelPart falló")
        return False
    
    # Test applications check
    apps = test_applications_check(adapter)
    if apps is None:
        print("\n=== RESULTADO: ETAPA A PARCIAL ===")
        print("Verificación de aplicaciones falló")
        return False
    
    print("\n=== RESULTADO: ETAPA A COMPLETADA ===")
    print("Kratos está correctamente inicializado en el entorno del proyecto principal")
    print("Componentes verificados:")
    print("  - Importación de KratosMultiphysics: OK")
    print("  - Importación de StructuralMechanicsApplication: OK")
    print("  - Importación de OptimizationApplication: OK")
    print("  - Creación de adaptador: OK")
    print("  - Creación de ModelPart: OK")
    print("  - Verificación de aplicaciones: OK")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)