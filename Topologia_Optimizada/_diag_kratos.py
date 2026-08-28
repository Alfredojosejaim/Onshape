import os
import sys
import traceback

site = next(p for p in sys.path if 'site-packages' in p)
libs = os.path.join(site, 'KratosMultiphysics', '.libs')
os.add_dll_directory(libs)

try:
    import KratosMultiphysics as Kratos
    print("Kratos import OK, version:", getattr(Kratos, "__version__", "unknown"))
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from KratosMultiphysics import StructuralMechanicsApplication
    print("StructuralMechanicsApplication OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from KratosMultiphysics import OptimizationApplication
    print("OptimizationApplication OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

Kratos.Logger.GetDefaultOutput().SetSeverity(Kratos.Logger.Severity.WARNING)
model = Kratos.Model()
mp = model.CreateModelPart("Diag")
print("ModelPart OK:", mp.Name)