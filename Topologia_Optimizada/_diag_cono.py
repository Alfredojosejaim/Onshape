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

print("== CADModel ==")
print("units:", cad_model.units)
print("bbox:", cad_model.bbox)
print("total_volume:", cad_model.total_volume)
print("total_area:", cad_model.total_area)
print("faces:", len(cad_model.faces))
print("solids:", len(cad_model.solids))

print("\n== CADModel.faces ==")
for f in cad_model.faces:
    print(f"  {f.id}: idx={f.face_index} area={f.area:.4f} center={tuple(round(c,4) for c in f.center)} normal={tuple(round(n,4) for n in f.normal)} type={f.surface_type}")

print("\n== cq.Shape.Faces() ==")
cq_faces = shape.Faces()
print("  count:", len(cq_faces))
for idx, face in enumerate(cq_faces):
    c = face.Center()
    n = face.normalAt(c)
    b = face.BoundingBox()
    print(f"  {idx}: area={face.Area():.4f} center=({c.x:.4f},{c.y:.4f},{c.z:.4f}) normal=({n.x:.4f},{n.y:.4f},{n.z:.4f}) bbox=[{b.xmin:.4f},{b.xmax:.4f}]x[{b.ymin:.4f},{b.ymax:.4f}]x[{b.zmin:.4f},{b.zmax:.4f}] type={type(face).__name__}")

print("\n== Tessellation ==")
tess = cad_model.tessellation
if tess:
    print("vertices:", tess.num_vertices, "triangles:", tess.num_triangles)