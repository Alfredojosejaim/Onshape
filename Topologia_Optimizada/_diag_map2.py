import os
import sys
import numpy as np

site = next(p for p in sys.path if 'site-packages' in p)
libs = os.path.join(site, 'KratosMultiphysics', '.libs')
if os.path.isdir(libs):
    os.add_dll_directory(libs)

sys.path.insert(0, os.getcwd())

from adapters.cad.step_adapter import StepAdapter
import cadquery as cq

STEP = "cono.step"
adapter = StepAdapter()
cad_model = adapter.load_from_file(STEP, model_name="Cono")
shape = adapter.get_shape(cad_model.id)

import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("cono_mesh")
gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
gmsh.model.occ.importShapes(STEP, format="step")
gmsh.model.occ.synchronize()
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 4.0)
gmsh.model.mesh.generate(3)
node_tags, coords, _ = gmsh.model.mesh.getNodes()
gmsh.finalize()

nodes = []
for i in range(0, len(coords), 3):
    nodes.append([coords[i], coords[i+1], coords[i+2]])
nodes = np.array(nodes)
print("mesh nodes:", len(nodes))

cq_faces = shape.Faces()
print("faces:", len(cq_faces))

def robust_normal(face):
    """Fallback normal from tessellation when normalAt fails."""
    try:
        c = face.Center()
        n = face.normalAt(c)
        return c, n
    except Exception:
        pts, tris = face.tessellate(tolerance=0.1, angularTolerance=0.1)
        for tri in tris:
            p0 = pts[tri[0]]; p1 = pts[tri[1]]; p2 = pts[tri[2]]
            u = p1 - p0; v = p2 - p0
            n = u.cross(v)
            ln = n.Length
            if ln > 1e-12:
                n = n.multiply(1.0 / ln)
                cx = (p0.x + p1.x + p2.x) / 3.0
                cy = (p0.y + p1.y + p2.y) / 3.0
                cz = (p0.z + p1.z + p2.z) / 3.0
                return cq.Vector(cx, cy, cz), n
        return None, None

for idx in [0, 1, 2]:
    face = cq_faces[idx]
    c, n = robust_normal(face)
    print(f"\nface {idx}: center={tuple(round(getattr(c,a),4) for a in 'xyz') if c else None} normal={tuple(round(getattr(n,a),4) for a in 'xyz') if n else None}")
    # distance-based matching
    matches = []
    for ni, node in enumerate(nodes):
        v = cq.Vertex.makeVertex(float(node[0]), float(node[1]), float(node[2]))
        try:
            d = float(face.distance(v))
        except Exception as e:
            print("  distance FAILED:", repr(e))
            break
        if d <= 0.5:
            matches.append(ni)
    print(f"  matched {len(matches)} nodes within tol=0.5")
    if matches:
        sel = nodes[matches]
        print("  z-range: [%.3f, %.3f]  radius-range: [%.3f, %.3f]" % (
            sel[:,2].min(), sel[:,2].max(),
            np.linalg.norm(sel[:,:2], axis=1).min(), np.linalg.norm(sel[:,:2], axis=1).max()))