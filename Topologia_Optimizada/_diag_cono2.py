import os
import sys
import traceback

site = next(p for p in sys.path if 'site-packages' in p)
libs = os.path.join(site, 'KratosMultiphysics', '.libs')
if os.path.isdir(libs):
    os.add_dll_directory(libs)

sys.path.insert(0, os.getcwd())

from adapters.cad.step_adapter import StepAdapter

adapter = StepAdapter()
cad_model = adapter.load_from_file("cono.step", model_name="Cono")
shape = adapter.get_shape(cad_model.id)

cq_faces = shape.Faces()
print("== cq.Shape.Faces() count:", len(cq_faces))

for idx, face in enumerate(cq_faces):
    print(f"\n--- face idx {idx} type {type(face).__name__} ---")
    try:
        c = face.Center()
        print("  Center:", (c.x, c.y, c.z))
    except Exception as e:
        print("  Center FAILED:", repr(e))
    try:
        n = face.normalAt(c)
        print("  normalAt(center):", (n.x, n.y, n.z))
    except Exception as e:
        print("  normalAt FAILED:", repr(e))
    try:
        print("  Area:", face.Area())
    except Exception as e:
        print("  Area FAILED:", repr(e))
    try:
        b = face.BoundingBox()
        print("  bbox:", b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)
    except Exception as e:
        print("  bbox FAILED:", repr(e))

print("\n== GeometryEngine.extract_faces_metadata on same shape ==")
from core.geometry import GeometryEngine
import logging
logging.basicConfig(level=logging.DEBUG)
cad_faces = GeometryEngine.extract_faces_metadata(shape)
for f in cad_faces:
    print(" ", f.id, "idx=", f.face_index, "area=", round(f.area,2), "center=", tuple(round(c,3) for c in f.center))

print("\n== tessellate ==")
try:
    tess = GeometryEngine.tessellate_shape(shape)
    print("  OK vertices=", tess.num_vertices, "triangles=", tess.num_triangles)
except Exception as e:
    print("  tessellate FAILED:", repr(e))
    traceback.print_exc()