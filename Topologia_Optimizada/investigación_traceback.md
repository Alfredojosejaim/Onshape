# Auditoría prompts.md (nuevo): pickeo UI vive en tessellation OCCT, no en Gmsh

Conclusión estructural: el `polydata` que alimenta a `Viewport3D`/`vtkCellPicker`
es la triangulación directa de OCCT vía `face.tessellate()` de CadQuery
(`core/geometry.py::GeometryEngine`), NO la malla de Gmsh. Gmsh solo genera la
malla volumétrica FEM. Por tanto P1 (Gmsh↔OCCT) no contamina el pickeo; el
contrato que importa es `TopoDS_Face ↔ triángulos ↔ face_index_map`.

## 1. Cómo se genera la tessellation (código real)

`core/geometry.py::GeometryEngine.tessellate_shape` (deflection ahora relativa):

```python
linear_deflection = GeometryEngine._relative_deflection(shape, linear_deflection)
# _relative_deflection: None (default) => diag_bbox * 0.001 (mínimo 1e-4);
# valor explícito se respeta tal cual.
```

Antes: `linear_deflection=0.1` fijo global (patrón sospechoso del prompt §4.1:
misma deflection para fillets/B-splines que para caras grandes planas →
sub-tesselado + posibles caras con cero triángulos). Ahora: relativo al bbox.

`face.tessellate()` de CadQuery devuelve vértices en coordenadas globales
(aplica `loc.Transformation()` internamente), así que el bug §4.2.1
(transform no aplicado) queda descartado por construcción.

## 2. Cómo se construye `face_index_map` (código real)

`core/geometry.py::GeometryEngine._tessellate_with_face_mapping`:

```python
for idx, face in enumerate(faces):
    try:
        pts, tris = face.tessellate(tolerance=linear_deflection,
                                    angularTolerance=angular_deflection)
    except Exception as ex:
        logger.warning("Face %d produced no triangulation (exception: %s)", idx, ex)
        continue
    if not pts or not tris:
        logger.warning("Face %d produced no triangulation (%s pts, %s tris) ...", ...)
        continue
    base = vertex_offset
    for p in pts:
        vertices.extend([float(p.x), float(p.y), float(p.z)])
    for tri in tris:
        indices.extend([int(tri[0]) + base, int(tri[1]) + base, int(tri[2]) + base])
    face_triangles.append({"face_index": idx, "start": triangle_offset,
                           "count": len(tris)})
    vertex_offset += len(pts)
    triangle_offset += len(tris)
```

- Una entrada por TRIÁNGULO vía rangos `start/count` (no por cara) → el bug
  §4.2.2 (indexado por cara) queda descartado: `face_index_map[cell_id]` es
  correcto para todo `CellId`.
- El `continue` con `WARNING` explícito (antes `debug` silencioso) + offsets
  solo avanzados tras éxito → el bug §4.2.3 (desalineo de caras posteriores)
  queda descartado/documentado.
- `desktop/ui/main_window.py::_show_tessellation` reconstruye el mapa
  per-triángulo desde los rangos, recorta rangos fuera de límite con warning,
  y verifica `assert len(face_index_map) == n_tri`.

Verificación rápida (§4.3): `face_triangles` cubre todos los triángulos
(`tests/test_advanced_geometric_selection.py::test_tessellation_face_mapping_ranges_cover_all_triangles`).

## 3. Fixes aplicados del prompt nuevo

1. **Multi-selección (§1.1)**: `_qt_additive()` = OR de Qt
   (`QApplication.keyboardModifiers()`) y VTK (`interactor.GetShiftKey()` /
   `GetControlKey()`); el foco cautivo del QVTK interactor ya no puede forzar
   `additive=False`. Highlight recibe el Set completo
   (`selected_cell_ids_for_faces` sobre todas las caras, no solo la última).
2. **Tangentes (§2)**: `PICK_TOLERANCE` 0.025 → 0.0005.
3. **Caras no seleccionables (§3)**: `BackfaceCullingOff()` +
   `FrontfaceCullingOff()` en `Renderer.make_triangle_actor`; resto atribuido
   a tessellation (ver §1/§2 arriba), no a Gmsh.
4. **Deflection relativa (§4.1)**: default `None` → `diag*0.001` en
   `GeometryEngine` y `StepAdapter.tessellate`.
