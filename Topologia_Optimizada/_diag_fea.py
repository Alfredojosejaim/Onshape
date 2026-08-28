import os
import sys
import traceback
import numpy as np

site = next(p for p in sys.path if 'site-packages' in p)
libs = os.path.join(site, 'KratosMultiphysics', '.libs')
if os.path.isdir(libs):
    os.add_dll_directory(libs)

sys.path.insert(0, os.getcwd())

from core.solver_interface import create_kratos_fea_solver
from core.materials import Material
from core.study import ConstraintDefinition, ConstraintType, LoadDefinition, LoadType

material = Material(name="Steel", density=7850.0, young_modulus=210e9, poisson_ratio=0.3, yield_strength=250e6)

# Simple 1x1x1 cube: 6 tets (from test file)
nodes = np.array([
    [0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
    [1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1],
], dtype=float)
elements = np.array([
    [0, 1, 2, 3], [1, 4, 2, 5], [2, 4, 6, 7],
    [0, 2, 3, 6], [1, 5, 3, 7], [2, 3, 6, 7],
], dtype=int)

# Fix nodes at X=0 plane, load at X=1
constraints = [ConstraintDefinition(id="fixed", constraint_type=ConstraintType.FIXED, location_face_id="face_0",
                                    fixed_axis=0, fixed_coordinate=0.0, tolerance=0.1)]
loads = [LoadDefinition(id="load", magnitude=100.0, direction=(1, 0, 0), load_type=LoadType.POINT,
                        load_axis=0, load_coordinate=1.0, tolerance=0.1)]

try:
    fea_solver = create_kratos_fea_solver(nodes=nodes, elements=elements, material=material,
                                          constraints=constraints, loads=loads)
    print("solver created")
    result = fea_solver(densities=np.ones(elements.shape[0]), forces=None, supports=None, max_iterations=1)
    print("success:", result.get("success"))
    print("status:", result.get("status"))
    print("error:", result.get("error"))
    print("max_displacement:", result.get("max_displacement"))
    print("compliance:", result.get("compliance"))
    print("num_nodes:", result.get("num_nodes"))
except Exception:
    traceback.print_exc()
    sys.exit(1)