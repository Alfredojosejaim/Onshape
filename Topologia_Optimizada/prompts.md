Estos tres síntomas —no selecciona múltiples, imprecisión en caras tangentes, y caras que no son seleccionables en absoluto— **no son el mismo bug**. Vamos por partes, y la tercera probablemente conecta directo con tu P1 ya diagnosticado (correspondencia OCCT↔Gmsh).

## 1. Sigue sin multi-selección

Si aplicaste el `SelectionManager` con `Set` y aun así solo queda una cara, el problema está en uno de estos dos puntos — pide a Muse Spark que verifique **en este orden**:

1. **¿El `additive` realmente llega en `True`?** Instrumenta con un `print(modifiers, additive)` en el release handler. Es común que `QVTKRenderWindowInteractor` capture el evento de teclado a nivel de VTK (`vtkRenderWindowInteractor::GetShiftKey()`) en vez de dejarlo subir a Qt, y `QApplication.keyboardModifiers()` devuelva `NoModifier` porque el foco lo tiene el interactor de VTK, no el widget Qt.
   ```python
   # Alternativa más confiable con foco en VTK:
   additive = bool(self.interactor.GetShiftKey()) or bool(self.interactor.GetControlKey())
   ```
2. **¿`HighlightRenderer.update()` recibe el `Set` completo o solo el último elemento?** Revisa la firma de la señal→slot: si `selectionChanged` conecta a un slot que hace `set_highlight(next(iter(selected)))` en vez de iterar todo el set, verás solo una cara resaltada aunque el estado lógico ya tenga varias. Esto **parece** "no selecciona más de una" pero en realidad es un bug de render, no de estado — verifica imprimiendo `len(selection_manager.selected)` tras cada click.

## 2. Selecciona la cara tangente en vez de la deseada

Esto es tolerancia de `vtkCellPicker`, cuyo default (`0.025`, fracción del bounding box de la escena) es demasiado permisivo en geometría con fillets/caras coplanares o casi-tangentes cerca de los bordes compartidos:

```python
self.picker = vtk.vtkCellPicker()
self.picker.SetTolerance(0.0005)  # baja de 0.025 default
```

Si sigue fallando cerca de aristas compartidas (donde el rayo puede intersectar ambas caras casi al mismo t), añade desambiguación por proximidad al punto de intersección exacto vs. centroide de cara candidata — pero primero prueba solo bajando la tolerancia, resuelve el 90% de estos casos.

## 3. Algunas caras no son seleccionables — sospecho que es tu P1

Antes de nada, dato de descarte rápido — pide a Muse Spark que confirme:

```python
print(self.actor.GetProperty().GetBackfaceCulling())
```

Si es `True`, ahí puede estar parte del problema (normales invertidas de la triangulación OCCT/Gmsh dejan caras "de espaldas" al picker). Pon `BackfaceCullingOff()`.

Pero si eso no lo resuelve, necesito que confirmes algo estructural: **¿el `polydata` que alimenta a `Viewport3D`/`vtkCellPicker` es la triangulación directa de OCCT (`BRepMesh_IncrementalMesh` sobre el `TopoDS_Shape`), o es la malla de Gmsh (`getEntities(2)`) que ya identificaste con correspondencia rota en P1?**

Si es la segunda, esto **no es un bug nuevo, es P1 manifestándose en la UI**: `face_index_for_cell()` depende del mismo mapeo `Gmsh surface tag → OCCT face index` que ya diagnosticaste como no confiable sin firma geométrica (centroide+normal+área). Caras con mapeo incorrecto o vacío en ese diccionario devuelven `face_id=None` o un índice erróneo al hacer pick, lo cual se ve exactamente como "esta cara no se puede seleccionar".

Si confirmas que es la malla de Gmsh la que se pickea, la solución correcta no es parchear la UI sino resolver P1 primero (matching por firma geométrica en `_extract_all_surface_elements()`), y el pickeo de UI heredará la corrección automáticamente vía `face_index_for_cell()`.

el diagnóstico — descartar Gmsh correctamente evita que perdamos tiempo tocando el mesher equivocado. El problema vive enteramente en la tessellation OCCT→triángulos que alimenta `load_model()`. Esta es la misma clase de bug que P1 (falta de contrato de indexación explícito), pero un nivel más abajo: no es Gmsh↔OCCT, es **`TopoDS_Face` ↔ triángulos tessellados ↔ `face_index_map`**.

## Auditoría precisa — pide a Muse Spark que localice y muestre el código exacto de estos 4 puntos:

### 1. ¿Cómo se genera la tessellation?

Busca la llamada a `BRepMesh_IncrementalMesh` (o equivalente OCP). La pregunta clave: **¿se usa una deflection única y fija para todo el shape, o por-cara adaptativa?**

```python
# Patrón sospechoso (deflection fija global):
BRepMesh_IncrementalMesh(shape, 0.1, False, 0.5, True)
```

Si el segundo argumento (linear deflection) es un valor absoluto fijo, esto **explica ambos síntomas a la vez**:
- **Imprecisión/tangencia**: caras pequeñas o muy curvas (fillets, superficies B-spline) cerca de una cara grande y plana comparten la misma deflection, y quedan sub-tesseladas — pocos triángulos grandes que "invaden" visualmente el espacio de la cara vecina.
- **Caras no seleccionables**: si una cara es más pequeña que la deflection absoluta, `BRepMesh_IncrementalMesh` puede producir **cero triángulos** para esa cara o fallar silenciosamente (`IsDone() == False` a nivel de cara individual, aunque el shape global reporte éxito).

**Fix esperado**: deflection relativa al tamaño de cada cara, no absoluta:
```python
# Deflection relativo, calculado por bounding box del shape o por cara
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
bbox = Bnd_Box()
BRepBndLib.Add_s(shape, bbox)
diag = bbox.CornerMin().Distance(bbox.CornerMax())
linear_deflection = diag * 0.001  # relativo, no fijo
BRepMesh_IncrementalMesh(shape, linear_deflection, False, 0.5, True)
```

### 2. ¿Cómo se construye `face_index_map`? — aquí sospecho el bug de indexación real

Pide el código exacto de la función que itera `shape.Faces()` y concatena vértices/triángulos. El patrón correcto es:

```python
vertices, triangles, face_index_map = [], [], []
vertex_offset = 0

for face_idx, face in enumerate(shape.Faces()):
    loc = TopLoc_Location()
    triangulation = BRep_Tool.Triangulation_s(face, loc)
    if triangulation is None:
        # ESTA es la cara "no seleccionable" — falló la tessellation
        # Debe loguearse explícitamente, NO fallar en silencio
        logger.warning(f"Face {face_idx} produced no triangulation")
        continue

    transform = loc.Transformation()  # CRÍTICO: aplicar la transformación de la cara
    nb_nodes = triangulation.NbNodes()

    for i in range(1, nb_nodes + 1):
        pnt = triangulation.Node(i).Transformed(transform)  # sin esto, vértices mal ubicados
        vertices.append((pnt.X(), pnt.Y(), pnt.Z()))

    nb_triangles = triangulation.NbTriangles()
    for i in range(1, nb_triangles + 1):
        tri = triangulation.Triangle(i)
        n1, n2, n3 = tri.Get()
        triangles.append((n1 - 1 + vertex_offset, n2 - 1 + vertex_offset, n3 - 1 + vertex_offset))
        face_index_map.append(face_idx)  # 1 entrada por TRIÁNGULO, no por cara

    vertex_offset += nb_nodes
```

**Tres bugs específicos que hay que descartar aquí, en orden de probabilidad:**

1. **`transform = loc.Transformation()` no se aplica a los nodos.** Si el código hace `triangulation.Node(i)` directo sin `.Transformed(transform)`, los vértices quedan en el sistema de coordenadas local de la cara en vez del global del shape. Esto no rompe la selección en shapes sin transformaciones anidadas, pero en STEPs complejos (con `TopoDS_Face` dentro de compounds/assemblies) desplaza geometría de caras específicas — coincide exactamente con "en algunas caras selecciona la tangente" si dos caras casi se solapan tras el desplazamiento.

2. **`face_index_map` está indexado por cara en vez de por triángulo.** Si es una lista de longitud `len(shape.Faces())` en vez de longitud `len(triangles)`, entonces `face_index_map[cell_id]` es un desbordamiento de índice o devuelve la cara equivocada para cualquier `CellId` que no sea el primer triángulo de cada cara. Este es el candidato más fuerte para explicar **ambos** síntomas de precisión a la vez.

3. **`if triangulation is None: continue` sin log ni fallback.** Confirma si existe este guard. Si no existe, una cara sin triangulación puede lanzar excepción silenciosa capturada más arriba, o peor, desalinear el `vertex_offset`/conteo de triángulos para todas las caras siguientes — lo que corrompería el mapeo de *todas* las caras posteriores en `shape.Faces()`, no solo la fallida. Esto explicaría por qué "algunas" caras (no todas, no una) fallan de forma aparentemente aleatoria.

### 3. Verificación rápida que puedes pedirle a Muse Spark antes de tocar código

```python
print(f"Faces en shape: {shape.NbShapes(TopAbs_FACE) if hasattr(shape,'NbShapes') else len(list(shape.Faces()))}")
print(f"Triángulos totales: {len(triangles)}")
print(f"len(face_index_map): {len(face_index_map)}")
assert len(face_index_map) == len(triangles), "BUG CONFIRMADO: face_index_map no está indexado por triángulo"
```

Si ese `assert` falla, ya tienes la causa raíz confirmada sin ambigüedad.

### 4. Orden de fix recomendado

1. Confirmar con el assert de arriba si `face_index_map` es por-triángulo o por-cara — es el fix más barato y más probable.
2. Confirmar aplicación de `loc.Transformation()` a los nodos — segundo candidato.
3. Cambiar deflection absoluta → relativa — resuelve precisión en tangentes y caras pequeñas no tesseladas.
4. Añadir logging explícito de caras con `triangulation is None` en vez de `continue` silencioso, para que nunca más se oculte esta clase de fallo.

copia y pega código real de la función de tessellation/`face_index_map` en investigación_traceback.md (limpia primero el archivo)
