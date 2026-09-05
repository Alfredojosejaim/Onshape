# Rubber-band select estilo Onshape — implementado (Ctrl = sustractivo)

Decisión de producto confirmada: **Onshape completo** — drag simple reemplaza,
Shift+drag añade, Ctrl+drag resta.

## Menores del cierre (no bloqueantes)

- **Z-fighting (§3)**: no se toca ahora. Anotado el fix futuro sin fusionar
  malla: `vtkPolyDataMapper.SetResolveCoincidentTopologyToPolygonOffset()`
  (solo z-buffer, no afecta picking ni `face_index_map`).
- **`angularTolerance` (§2)**: de acuerdo — constante por invariante de escala,
  consistente con P4 (halo vs. filter_radius). Si 0.05 no basta en fillets
  residuales, tessellation adaptativa por curvatura real (over-engineering
  hasta tener evidencia).

## Implementación

**`SelectionManager.handle_rubber_band(face_indices, additive, subtractive)`**
(`desktop/viewport/selection.py`): sustractivo resta, aditivo une, simple
reemplaza (incluso con set vacío: soltar sobre vacío limpia). Construye los
`CadEntityRef` desde los índices, reutiliza `_sync_legacy_after_set_change()`
y emite `selectionChanged` + callback legacy. **Solo emite si el set cambió**:
un drag sin efecto es no-op total (sin reflow ni re-render).

**Contención total, no bbox** (`faces_fully_in_rect` a nivel de módulo en
`desktop/viewport/viewport_3d.py`, testeable sin GL): la cara entra solo si
TODOS sus vértices proyectados caen en el `QRect` — nunca intersección de
bounding box (evita geometría de fondo parcialmente visible). `project_fn`
inyectable para tests; por defecto `vtkCoordinate` en modo world con
conversión `sy_qt = height - sy_vtk` (Y invertido VTK vs Qt).

**Cableado Qt/VTK** (`Viewport3D`):
- `_on_left_press` arma `_left_held`; `_on_move` en modo idle con click
  pendiente y botón abajo activa la banda al superar 4px (mismo umbral
  click/drag existente) y actualiza `QRubberBand` (hijo del interactor).
- `_on_left_release` con banda activa → `_finish_rubber_band()`: oculta,
  rect normalizado, modificadores OR Qt+VTK por separado
  (`_drag_modifiers()` → Shift=aditivo, Ctrl=sustractivo), caras contenidas,
  `handle_rubber_band`. El pick puntual queda intacto cuando no hubo drag.
- La proyección se calcula **una sola vez al soltar**, no durante el arrastre
  (el move solo mueve el rectángulo): no hace falta `vtkHardwareSelector`
  salvo lag medible en STEPs enormes.
- No hizo falta tocar `core/navigation`: el perfil AutoCAD resuelve LEFT
  siempre a SELECT (con o sin modificadores), así que Shift/Ctrl+drag entran
  en modo select sin cambios.
- `Scene` cachea `face→[vertex_ids]` una sola vez en `set_model_geometry()`
  (`face_vertex_cache`, con rebuild lazy + `model_vertices`).
- `SoftwareViewport` queda fuera de alcance (sus handlers Qt son propios);
  mantiene click-select; anotado como trabajo futuro si se quiere paridad.

## Tests

`tests/test_rubber_band_select.py` (10 tests, en verde): reemplaza / vacía /
aditivo / sustractivo / no-op sin emisión / callback legacy con set completo /
fully-contained vs. solape parcial (2 de 3 vértices dentro NO entra) / cache
de vértices en `Scene` / contrato de API sin GL.

---

# Verificación "¿qué viewport corre en realidad?" — hipótesis del fallback DESCARTADA aquí

Pregunta del prompt: `is_gl_available()` imprime **`True`** en esta máquina
(medido con `.venv\Scripts\python.exe -c`, 2026-09-05). La ruta VTK
(`Viewport3D` + todo lo auditado: tolerancia 0.0005, `Set`, rubber-band,
highlight vectorizado) **sí se ejecuta**; la hipótesis de estar corriendo el
fallback queda descartada para este entorno.

Puntos confirmados del diagnóstico (correctos, pero no aplicables aquí):
- `main_workspace.py:57-65` elige `Viewport3D` vs `SoftwareViewport` según
  `is_gl_available()`, con `try/except` que cae a software si VTK falla.
- `_SoftwareSelectionManager.pick()` (`software_viewport.py:115-135`):
  toggle acumulativo siempre, sin reemplazo en click simple, sin distinción
  Shift/Ctrl, sin `handle_pick`/`handle_rubber_band`, sin highlight
  vectorizado. Sus síntomas ("no multi-selección" / "desmarcar marca otra")
  coinciden con ese toggle — pero aquí GL es `True`, así que de persistir
  síntomas vendrían de la ruta VTK, no del fallback.

Medición auxiliar: la primera llamada al probe tardó >60s (subprocess que
importa VTK desde cero); el resultado queda cacheado (`_GL_AVAILABLE`).

Acciones propuestas (pendientes de decisión, no implementadas):
1. Badge/log al arranque con el backend activo (`_use_vtk` hoy no se usa
   fuera del host): evita esta confusión en máquinas remotas/VM sin GPU.
2. Si el probe diera `False` en la máquina de uso diario: camino 2 del
   prompt — portar la máquina de estados (`Set`, reemplazo/toggle/rubber)
   al fallback o unificar ambos viewports sobre el mismo `SelectionManager`
   de estado puro, difiriendo solo en picking/render.

---

# Actor-pick: causa raíz del "desmarca una pero marca otra" (ambas capas aplicadas)

Diagnóstico confirmado: `_do_pick_release()` no validaba el actor — el
`vtkCellPicker` golpea TODOS los actores (grid, ejes, overlays) y
`face_index_for_cell()` indexaba ese `cell_id` ciegamente como triángulo del
modelo → cara arbitraria + `handle_pick()` reemplazando (correcto según su
lógica, con una cara falsa). El `pick()` legacy sí validaba; se perdió en el
refactor.

**Fix 1 — validación de actor** (`desktop/viewport/viewport_3d.py`):
`resolve_pick_entity(picked_actor, cell_id, scene)` → `None` (vacío) si
actor None / cell −1 / actor no-modelo; `CadEntityRef` si modelo + cara;
`KEEP_SELECTION` (conservar) si modelo + hueco sin cara. `_do_pick_release()`
lo consume. Apoyo: `Scene.actor_key_for()` nuevo. Nota: más estricto que el
legacy (clicks en actor-malla/densidad ahora son vacío, no selección de
actor).

**Fix 2 — defensa en profundidad** (`SetPickable(False)`): grid
(`Renderer.create_grid`), ejes (`create_axes`), outline de identificación
(`_build_identification`) y **overlay de highlight** (`Scene.highlight_faces`,
no listado en el prompt pero crítico: va +eps hacia la cámara, ganaría el
picker y rompería el toggle-off en caras resaltadas).

**Multi-selección**: a nivel lógica, cerrada por la misma causa (Shift+clicks
rozando grid/ejes se corrompían igual; P0 verdes). Segundo factor pendiente
de runtime: tolerancia 0.0005 quizá demasiado ajustada en bordes reales —
sin cobertura de test, solo verificable con la app.

**Tests**: `tests/test_pick_actor_validation.py` (8 en verde) + suite de
selección 42 passed.
