import os
import sys
import traceback
import numpy as np

site = next(p for p in sys.path if 'site-packages' in p)
libs = os.path.join(site, 'KratosMultiphysics', '.libs')
if os.path.isdir(libs):
    os.add_dll_directory(libs)

sys.path.insert(0, os.getcwd())

from adapters.cad.step_adapter import StepAdapter
from core.boundary import BoundaryConditionMapper

STEP = "cono.step"

# --- 1. CADModel + shape ---
adapter = StepAdapter()
cad_model = adapter.load_from_file(STEP, model_name="Cono")
shape = adapter.get_shape(cad_model.id)
print("CADModel faces count:", len(cad_model.faces))
print("bbox:", cad_model.bbox)

# --- 2. gmsh mesh from real STEP ---
import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("cono_mesh")
gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
gmsh.model.occ.importShapes(STEP, format="step")
gmsh.model.occ.synchronize()
vols = gmsh.model.getEntities(dim=3)
print("volumes:", len(vols))
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 4.0)
gmsh.model.mesh.generate(3)
node_tags, coords, _ = gmsh.model.mesh.getNodes()
gmsh.finalize()

nodes = []
for i in range(0, len(coords), 3):
    nodes.append([coords[i], coords[i+1], coords[i+2]])
nodes = np.array(nodes)
print("mesh nodes:", len(nodes))

# --- 3. Face->node mapping for the 3 real faces ---
for face_idx in [0, 1, 2]:
    mapped = BoundaryConditionMapper.map_faces_to_nodes(shape, nodes.tolist(), face_indices=[face_idx], tolerance=0.5)
    m = mapped[0]
    idxs = m.node_indices
    print(f"\nface {face_idx}: area={m.area:.2f} matched nodes={m.matched_nodes_count}")
    if idxs:
        sel = nodes[idxs]
        print("  node z-range: [%.3f, %.3f]" % (sel[:,2].min(), sel[:,2].max()))
        print("  node radius range: [%.3f, %.3f]" % (np.linalg.norm(sel[:,:2], axis=1).min(), np.linalg.norm(sel[:,:2], axis=1).max()))
        print("  sample coords:", sel[:3].tolist())

# --- 4. disjointness between bottom and top ---
b = BoundaryConditionMapper.map_faces_to_nodes(shape, nodes.tolist(), face_indices=[1], tolerance=0.5)[0].node_indices
t = BoundaryConditionMapper.map_faces_to_nodes(shape, nodes.tolist(), face_indices=[2], tolerance=0.5)[0].node_indices
print("\nbottom∩top =", len(set(b) & set(t)))