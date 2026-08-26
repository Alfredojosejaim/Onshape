#!/usr/bin/env python
"""
Script mínimo de reproducibilidad para Kratos Multiphysics
Ejecuta únicamente las importaciones críticas sin dependencias adicionales.
"""

import sys

print("Iniciando prueba de reproducibilidad desde terminal nueva...")
print("-" * 60)

# 1. Importar KratosMultiphysics
print("1. import KratosMultiphysics")
try:
    import KratosMultiphysics
    print("[PASS] KratosMultiphysics")
    try:
        version = KratosMultiphysics.KratosVersion()
        print(f"Versión: {version}")
    except:
        print("Versión: No disponible")
except ImportError as e:
    print(f"[FAIL] KratosMultiphysics: {e}")
    sys.exit(1)

# 2. Importar StructuralMechanicsApplication
print("\n2. from KratosMultiphysics import StructuralMechanicsApplication")
try:
    from KratosMultiphysics import StructuralMechanicsApplication
    print("[PASS] StructuralMechanicsApplication")
except ImportError as e:
    print(f"[FAIL] StructuralMechanicsApplication: {e}")
    sys.exit(1)

# 3. Importar OptimizationApplication
print("\n3. from KratosMultiphysics import OptimizationApplication")
try:
    from KratosMultiphysics import OptimizationApplication
    print("[PASS] OptimizationApplication")
except ImportError as e:
    print(f"[FAIL] OptimizationApplication: {e}")
    sys.exit(1)

print("-" * 60)
print("RESULTADO: Todas las importaciones exitosas desde terminal nueva")
