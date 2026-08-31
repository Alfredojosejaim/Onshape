#!/usr/bin/env python3
"""Script to test the corrected LinearSolver setup using python_linear_solver_factory."""

import KratosMultiphysics as Kratos
import KratosMultiphysics.python_linear_solver_factory as python_linear_solver_factory

print("=== PRUEBA DE SOLUCIÓN CORREGIDA ===")
print()

# Test the corrected solution using python_linear_solver_factory
print("Intento corregido: python_linear_solver_factory.ConstructSolver(Kratos.Parameters)")
try:
    solver_settings = Kratos.Parameters("""
    {
        "solver_type": "skyline_lu_factorization",
        "scaling": false,
        "tolerance": 1e-6
    }
    """)
    linear_solver = python_linear_solver_factory.ConstructSolver(solver_settings)
    print("   [PASS] python_linear_solver_factory.ConstructSolver() funcionó correctamente")
    print(f"   Solver creado: {linear_solver}")
    print(f"   Tipo de solver: {type(linear_solver)}")
except Exception as e:
    print(f"   [FAIL] python_linear_solver_factory.ConstructSolver() falló")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=== FIN DE PRUEBA ===")