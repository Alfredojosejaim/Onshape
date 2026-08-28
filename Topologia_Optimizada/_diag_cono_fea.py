import os
import sys
import traceback
import numpy as np

site = next(p for p in sys.path if 'site-packages' in p)
libs = os.path.join(site, 'KratosMultiphysics', '.libs')
if os.path.isdir(libs):
    os.add_dll_directory(libs)

sys.path.insert(0, os.getcwd())

STEP = "cono.step"

import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("cono_mesh")
gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
gmsh.model.occ.importShapes(STEP, format="step")
gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 6.0)
gmsh.model.mesh.generate(3)
node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
element_types = gmsh.model.mesh.getElementTypes()
element_tags, element_node_tags, element_connectivity = gmsh.model.mesh.getElements()
nodes = np.array([[node_coords[3*i], node_coords[3*i+1], node_coords[3*i+2]] for i in range(len(node_tags))])
tet = None
for i, et in enumerate(element_types):
    if et == 4:
        tet = element_connectivity[i]
        break
elements = np.array(tet).reshape(-1, 4) - 1
gmsh.finalize()
print("mesh nodes:", nodes.shape[0], "elements:", elements.shape[0])

from core.solver_interface import create_kratos_fea_solver
from core.materials import STANDARD_MATERIALS
from core.study import ConstraintDefinition, ConstraintType, LoadDefinition, LoadType

material = STANDARD_MATERIALS["steel"]
constraints = [ConstraintDefinition(id="base", constraint_type=ConstraintType.FIXED, location_face_id="base",
                                    fixed_axis=2, fixed_coordinate=0.0, tolerance=0.5)]
loads = [LoadDefinition(id="top", magnitude=1000.0, direction=(0, 0, -1), load_type=LoadType.DISTRIBUTED,
                        load_axis=2, load_coordinate=50.2724536763264, tolerance=0.5)]

try:
    fea_solver = create_kratos_fea_solver(nodes=nodes, elements=elements, material=material,
                                          constraints=constraints, loads=loads)
    result = fea_solver(densities=np.ones(elements.shape[0]), forces=None, supports=None, max_iterations=1)
    print("success:", result.get("success"))
    print("status:", result.get("status"))
    print("error:", str(result.get("error"))[:500] if result.get("error") else None)
    print("max_displacement:", result.get("max_displacement"))
    print("compliance:", result.get("compliance"))
    print("displacements:", len(result.get("displacements", [])))
except Exception:
    traceback.print_exc()
    sys.exit(1)