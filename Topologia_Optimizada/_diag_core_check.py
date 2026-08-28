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
from core.geometry import GeometryEngine
from core.boundary import BoundaryConditionMapper, resolve_face_index

# 1) CADModel must now preserve ALL real B-Rep faces of the cone (curved lateral included)
adapter = StepAdapter()
cad_model = adapter.load_from_file("cono.step", model_name="Cono")
shape = adapter.get_shape(cad_model.id)
n_shape_faces = len(shape.Faces())
print("shape.Faces() count:", n_shape_faces)
print("CADModel.faces count:", len(cad_model.faces))
for f in cad_model.faces:
    print(f"  {f.id}: idx={f.face_index} area={f.area:.2f} center={tuple(round(c,3) for c in f.center)} normal={tuple(round(n,3) for n in f.normal)}")
assert len(cad_model.faces) == n_shape_faces, "CADModel must not drop curved faces"

# 2) resolve_face_index parser
assert resolve_face_index("face_0") == 0
assert resolve_face_index("face 2") == 2
assert resolve_face_index("3") == 3
assert resolve_face_index("base") is None
assert resolve_face_index(None) is None
print("resolve_face_index OK")

# 3) BoundaryConditionMapper must map all 3 faces (including curved) without crashing
import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("cono")
gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
gmsh.model.occ.importShapes("cono.step", format="step")
gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 5.0)
gmsh.model.mesh.generate(3)
node_tags, coords, _ = gmsh.model.mesh.getNodes()
gmsh.finalize()
nodes = np.array([[coords[3*i], coords[3*i+1], coords[3*i+2]] for i in range(len(node_tags))])
print("mesh nodes:", len(nodes))

for idx in [0, 1, 2]:
    mapped = BoundaryConditionMapper.map_faces_to_nodes(shape, nodes.tolist(), face_indices=[idx], tolerance=0.5)
    m = mapped[0]
    sel = nodes[m.node_indices] if m.node_indices else np.empty((0, 3))
    print(f"face {idx}: nodes={m.matched_nodes_count} z=[{sel[:,2].min() if len(sel) else 0:.3f},{sel[:,2].max() if len(sel) else 0:.3f}]")
    assert m.matched_nodes_count > 0

print("\nALL CORE CHECKS PASSED")