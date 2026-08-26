#!/usr/bin/env python
"""
Script de verificación mínima para Kratos Multiphysics y aplicaciones necesarias.
Verifica: versión de Python, versión de Kratos, y las importaciones críticas.
"""

import sys

print("=" * 60)
print("VERIFICACIÓN DE IMPORTACIÓN KRATOS")
print("=" * 60)
print()

# Verificar versión de Python
print(f"Versión de Python: {sys.version}")
print()

# Verificar KratosMultiphysics
try:
    import KratosMultiphysics
    print("[PASS] KratosMultiphysics")
    try:
        print(f"       Versión: {KratosMultiphysics.__version__}")
    except:
        print("       Versión: No disponible")
except Exception as e:
    print(f"[FAIL] KratosMultiphysics")
    print(f"       Error: {e}")
    sys.exit(1)

# Verificar StructuralMechanicsApplication
try:
    from KratosMultiphysics import StructuralMechanicsApplication
    print("[PASS] StructuralMechanicsApplication")
except Exception as e:
    print(f"[FAIL] StructuralMechanicsApplication")
    print(f"       Error: {e}")
    sys.exit(1)

# Verificar OptimizationApplication
try:
    from KratosMultiphysics import OptimizationApplication
    print("[PASS] OptimizationApplication")
except Exception as e:
    print(f"[FAIL] OptimizationApplication")
    print(f"       Error: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("TODAS LAS IMPORTACIONES EXITOSAS")
print("=" * 60)
