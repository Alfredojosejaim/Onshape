Buena auditoría, y los tres descartes están bien fundamentados (offset por-triángulo, transform interno de `face.tessellate()`, logging explícito). Quedan 4 puntos que verificaría antes de dar esto por cerrado — dos son riesgos reales, dos son preguntas de confirmación:

## 1. Riesgo real: `HighlightRenderer.update()` con loop Python por celda

Si aplicaste el patrón que te di literal (`for cid in range(n_cells): SetTuple3(...)`), en un STEP complejo con decenas de miles de triángulos esto se vuelve perceptible por click — cada selección recalcula el array completo en Python puro. Con `face_triangles` ya teniendo rangos `start`/`count` por cara, puedes vectorizar:

```python
import numpy as np
from vtk.util.numpy_support import numpy_to_vtk

def update(self, selected_cell_ids: set[int], hovered_cell_id: int | None):
    n = self.polydata.GetNumberOfCells()
    rgb = self.base_colors_np.copy()          # (n, 3) uint8, precomputado una vez
    if selected_cell_ids:
        idx = np.fromiter(selected_cell_ids, dtype=np.int64)
        rgb[idx] = (255, 165, 0)
    if hovered_cell_id is not None:
        rgb[hovered_cell_id] = (120, 190, 255)
    vtk_arr = numpy_to_vtk(rgb, deep=True)
    vtk_arr.SetName("Colors")
    self.polydata.GetCellData().SetScalars(vtk_arr)
    self.polydata.Modified()
```

Con `face_triangles[i]["start"]:start+count` puedes ir directo de "cara seleccionada" a slice de índices sin pasar por `face_index_map` completo. Confirma con Muse Spark cuál de las dos versiones quedó implementada — si es el loop Python, vale la pena el cambio ahora que tienes multi-selección funcionando (el loop escala mal precisamente cuando seleccionas varias caras a la vez).

## 2. Pregunta: `angularTolerance` — ¿sigue en valor fijo?

Bajaste `linear_deflection` a relativo, pero el fix del prompt no menciona si `angular_deflection` (parámetro `angularTolerance` de `face.tessellate()`) también es fijo. Si quedó en el default de CadQuery (típicamente ~0.1–0.5 rad), caras muy curvas con bbox pequeño (fillets finos, por ejemplo) pueden seguir generando pocos triángulos incluso con deflection lineal correcta, porque el criterio angular domina en superficies de alta curvatura y bajo tamaño. Vale la pena confirmar si esto sigue como constante o si también quedó parametrizado — si el problema de tangencia en fillets persiste tras el fix de tolerancia de picker, este es el próximo sospechoso.

## 3. Riesgo real no cubierto: vértices no compartidos entre caras adyacentes

Como cada cara se tessela independientemente (`face.tessellate()` por cara, sin fusión de malla), los vértices en aristas compartidas **no son el mismo punto de memoria** aunque coincidan en coordenadas — esto es correcto y esperado para que `CellData` por-cara funcione sin ambigüedad de picking, pero puede producir *z-fighting* o "grietas" visuales sutiles en el render cuando dos caras casi-tangentes comparten arista, especialmente con anti-aliasing. No afecta al picking (que ya mejoraste con tolerancia 0.0005), pero si notas líneas parpadeantes en bordes compartidos tras este fix, es este efecto — no un bug nuevo, es consecuencia del diseño correcto.

## 4. Test que falta para cerrar el caso completo

`test_tessellation_face_mapping_ranges_cover_all_triangles` valida el contrato de índices, pero no valida el caso que originó todo esto: **picking correcto sobre un STEP con caras tangentes/fillets reales**. Sugiero:

```python
def test_pick_disambiguates_tangent_faces(complex_step_shape):
    """Regression test para el caso reportado: cara tangente seleccionada
    en vez de la cara objetivo cerca de un fillet."""
    vertices, triangles, face_triangles = tessellate_with_face_mapping(complex_step_shape)
    # Punto conocido cerca de arista compartida entre cara plana y fillet
    picked_face = pick_at_point(vertices, triangles, face_triangles, known_point)
    assert picked_face == expected_face_index
```

Sin este test con geometría real (no sintética), el `assert` de cobertura de rangos te protege de regresiones de indexación pero no de regresiones de precisión geométrica — que es el síntoma original que reportaste.

¿Confirmas el estado de `angularTolerance` y cuál versión de `HighlightRenderer` quedó? Con eso cierro la auditoría de picking y pasamos a rubber-band select (mencionado en la máquina de estados original, punto 4) si sigue pendiente.

la respuesta a este prompt déjala en investigación_traceback.md (limpialo previamente)