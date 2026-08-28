import os
import sys
import traceback

site = next(p for p in sys.path if 'site-packages' in p)
libs = os.path.join(site, 'KratosMultiphysics', '.libs')
if os.path.isdir(libs):
    os.add_dll_directory(libs)

sys.path.insert(0, os.getcwd())

try:
    import core
    print("core import OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    import core.kratos_adapter as k
    print("kratos_adapter import OK, KRATOS_AVAILABLE=", k.KRATOS_AVAILABLE)
    print("import error:", k.KRATOS_IMPORT_ERROR)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from core.solver_interface import create_kratos_fea_solver, KRATOS_AVAILABLE
    print("solver_interface OK, KRATOS_AVAILABLE=", KRATOS_AVAILABLE)
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from adapters.cad.step_adapter import StepAdapter
    print("StepAdapter OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)