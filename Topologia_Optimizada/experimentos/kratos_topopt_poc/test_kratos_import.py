#!/usr/bin/env python
"""
PRUEBA MÍNIMA OBLIGATORIA DE KRATOS MULTIPHYSICS
Este script realiza únicamente la importación de Kratos y sus aplicaciones principales.
No ejecuta FEA, Gmsh ni TopOpt.
"""

import sys

def test_kratos_import():
    """Prueba mínima de importación de Kratos"""
    
    print("Iniciando prueba de importación de Kratos Multiphysics...")
    print("-" * 60)
    
    # 1. Importar KratosMultiphysics
    print("1. Importando KratosMultiphysics...")
    try:
        import KratosMultiphysics
        print("   [PASS] KratosMultiphysics")
        try:
            version = KratosMultiphysics.__version__
            print(f"   Versión: {version}")
        except AttributeError:
            print("   Versión: No disponible")
    except ImportError as e:
        print(f"   [FAIL] KratosMultiphysics: {e}")
        return False
    
    # 2. Importar StructuralMechanicsApplication
    print("\n2. Importando StructuralMechanicsApplication...")
    try:
        from KratosMultiphysics import StructuralMechanicsApplication
        print("   [PASS] StructuralMechanicsApplication")
    except ImportError as e:
        print(f"   [FAIL] StructuralMechanicsApplication: {e}")
        return False
    
    # 3. Importar OptimizationApplication
    print("\n3. Importando OptimizationApplication...")
    try:
        from KratosMultiphysics import OptimizationApplication
        print("   [PASS] OptimizationApplication")
    except ImportError as e:
        print(f"   [FAIL] OptimizationApplication: {e}")
        return False
    
    print("-" * 60)
    print("RESULTADO: Todas las importaciones fueron exitosas")
    return True

if __name__ == "__main__":
    success = test_kratos_import()
    sys.exit(0 if success else 1)
