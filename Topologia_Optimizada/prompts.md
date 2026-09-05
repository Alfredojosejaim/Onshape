Encontrado, con evidencia de código, no hipótesis. Y es un bug distinto y mucho más simple que todo lo que llevamos auditado hasta ahora.

## La causa raíz

`_do_pick_release()` en `viewport_3d.py` (el pipeline nuevo, prompts.md §2) **nunca valida qué actor golpeó el picker** antes de traducir el `cell_id` a una cara:

```python
self.selection._picker.Pick(click_pos[0], click_pos[1], 0, self.renderer.vtk_renderer)
cell_id = int(self.selection._picker.GetCellId())
...
face_id = self.scene.face_index_for_cell(cell_id)   # <-- sin verificar el actor
```

`vtkCellPicker.Pick(x, y, z, renderer)` pickea contra **todos los actores del renderer**, no solo el modelo. Y en `renderer.py`, tanto el grid del suelo como el triedro de ejes se crean y añaden sin `SetPickable(False)`:

```python
def create_grid(...): ...
self.add_actor(self._grid_actor)   # sin SetPickable(False)

def create_axes(...): ...
self.add_actor(self._axes_actor)   # sin SetPickable(False)
```

Y aquí está el golpe de gracia — `Scene.face_index_for_cell()` no sabe de qué actor viene el `cell_id`, solo comprueba que esté en rango:

```python
def face_index_for_cell(self, cell_id: int) -> Optional[int]:
    if self._tri_face_index is None or cell_id < 0:
        return None
    if cell_id >= self._tri_face_index.shape[0]:
        return None
    fi = int(self._tri_face_index[cell_id])   # <-- indexa ciegamente
    return fi if fi >= 0 else None
```

**Consecuencia exacta de tus dos síntomas**: cuando clicas lo que parece "vacío" (el suelo del grid, o cerca del triedro de ejes) para deseleccionar, el picker sí golpea algo — el grid o los ejes, que son geometría real pickeable — y devuelve un `cell_id` válido perteneciente a **esa** malla, no a la del modelo. `face_index_for_cell()` lo interpreta igualmente como si fuera un triángulo del modelo, siempre que el número esté dentro del rango de triángulos totales del modelo, y te devuelve una cara **arbitraria y sin relación con lo que clicaste**. Como no es un click aditivo, `handle_pick()` hace lo correcto según su propia lógica: reemplaza la selección — pero con esa cara falsa. De ahí "se desmarca la anterior pero se marca otra".

Esto también es candidato fuerte para el problema de multi-selección: si al intentar Shift+click sobre una segunda cara el rayo roza el grid o los ejes cerca del borde del modelo, el mismo bug corrompe ese click también.

Nota interesante: el método legado `pick()` (el que quedó como fallback en el `except`) **sí hace esta validación correctamente**:
```python
actor = self._picker.GetActor()
key = self._actor_to_key(actor)
if key is not None and getattr(self._scene, "_model_actor_key", None) == key:
    ...  # solo entonces mapea cell_id -> face
```
Se perdió al escribir el pipeline nuevo — típico bug de refactor donde una validación existente no se porta.

## Fix — dos capas, ambas necesarias

**1. Validar el actor en `_do_pick_release()`** (fix principal):
```python
def _do_pick_release(self) -> None:
    click_pos = self._interactor.GetEventPosition()
    self.selection._picker.Pick(
        click_pos[0], click_pos[1], 0, self.renderer.vtk_renderer)
    picked_actor = self.selection._picker.GetActor()
    model_key = getattr(self.scene, "_model_actor_key", None)
    hit_actor_key = self.scene.actor_key_for(picked_actor) if picked_actor is not None else None

    cell_id = int(self.selection._picker.GetCellId())
    additive = self._qt_additive()

    if cell_id == -1 or picked_actor is None or hit_actor_key != model_key:
        entity = None   # golpeó grid/ejes/otro actor no-modelo, o nada: tratar como vacio
    else:
        face_id = self.scene.face_index_for_cell(cell_id)
        ...
    self.selection.handle_pick(entity, additive=additive)
```
(Necesitas exponer o reutilizar `_actor_to_key`, que ya existe en `SelectionManager`, para mapear `picked_actor` a su key.)

**2. Defensa en profundidad — marcar grid, ejes y el outline de identificación como no-pickeables**, para que este bug no pueda repetirse aunque otro camino de picking se olvide de validar el actor:
```python
# renderer.py
self._grid_actor.SetPickable(False)   # en create_grid, tras crear el actor
self._axes_actor.SetPickable(False)   # en create_axes

# selection.py, _build_identification()
outline.SetPickable(False)            # el cubo wireframe de identificación tampoco debe ser pickeable
```

## Test de regresión sugerido

```python
def test_click_on_grid_does_not_select_random_face(scene_with_model_and_grid):
    """Clic sobre el grid (que parece 'vacio') debe limpiar seleccion,
    no seleccionar una cara arbitraria del modelo."""
    select_face(viewport, face_index=3)
    assert selection.selected == {face(3)}
    click_at(viewport, grid_point_far_from_model)
    assert selection.selected == set()   # no una cara aleatoria
```

Con el fix 1 solo (validación de actor), el bug queda resuelto de raíz sin tocar tolerancia de picker ni nada del pipeline ya auditado. El fix 2 es barato y evita que reaparezca. Pide a Muse Spark que aplique ambos y confirme si esto también resuelve la dificultad de multi-selección — sospecho que sí, pero vale la pena verificarlo por separado ya que puede haber un segundo factor (p. ej. tolerancia 0.0005 ahora demasiado ajustada cerca de bordes reales del modelo).