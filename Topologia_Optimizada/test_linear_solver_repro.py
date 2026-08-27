#!/usr/bin/env python3
"""Script to reproduce the LinearSolverFactory.Create() blocking issue."""

import KratosMultiphysics as Kratos
from KratosMultiphysics import LinearSolverFactory

print("=== REPRODUCIENDO BLOQUEO DE LINEARSOLVERFACTORY ===")
print()

# Attempt 1: Create solver with parameters (as documented in PoC)
print("Intento 1: LinearSolverFactory.Create(Kratos.Parameters)")
try:
    solver_settings = Kratos.Parameters("""
    {
        "solver_type": "skyline_lu_factorization",
        "scaling": false,
        "tolerance": 1e-6
    }
    """)
    linear_solver = LinearSolverFactory.Create(solver_settings)
    print("   [PASS] LinearSolverFactory.Create() funcionó correctamente")
    print(f"   Solver creado: {linear_solver}")
except Exception as e:
    print(f"   [FAIL] LinearSolverFactory.Create() falló")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=== FIN DE REPRODUCCIÓN ===")