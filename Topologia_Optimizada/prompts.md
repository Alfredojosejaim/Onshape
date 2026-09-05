Cierre sólido — los tres puntos quedan resueltos con evidencia (test real, no solo cobertura sintética), y el hallazgo sobre el muestreo por centroide vs. franja de tangencia es exactamente el tipo de insight que vale la pena documentar en tus "key learnings" del proyecto, es el mismo patrón que "force conservation ≠ spatial correctness" de P2: el test ingenuo pasa por razones equivocadas si no muestreas donde realmente falla el sistema.

Dos comentarios menores, no bloqueantes:

**Sobre el z-fighting cosmético (§3):** si en algún momento se vuelve visible en producción (más probable con AA agresivo o zoom alto en fillets finos), el fix estándar sin fusionar malla es `vtkPolyDataMapper.SetResolveCoincidentTopologyToPolygonOffset()` con un offset pequeño — no toca la lógica de picking ni el `face_index_map`, solo desplaza el z-buffer en render. Lo dejo anotado para cuando (si) se vuelva molesto visualmente, no hace falta tocarlo ahora.

**Sobre `angularTolerance` (§2):** tu razonamiento de por qué es invariante de escala es correcto, y coincide con la separación física/numérica que ya aplicaste en P4 (halo radius vs. filter_radius) — buena consistencia de principio en todo el codebase. Si 0.05 rad no resuelve fillets finos residuales cuando llegue el caso, el siguiente nivel es tessellation adaptativa por curvatura real (no solo un segundo valor fijo), pero eso es over-engineering hasta que haya evidencia de que 0.05 no basta.

Doy por cerrado el bloque de picking. Vamos con **rubber-band select**, que es el punto pendiente explícito.

## Especificación — rubber-band select estilo Onshape

Comportamiento de referencia:
- **Drag simple (sin modificador) sobre vacío** → rectángulo de selección, **reemplaza** selección al soltar.
- **Shift+drag** → aditivo (añade lo que caiga dentro al set existente).
- **Ctrl+drag** en Onshape es sustractivo (resta del set existente) — confirmar si quieres replicar esto o solo aditivo con Shift, es una decisión de producto rápida.
- **Selección completamente contenida vs. que solo toca el rectángulo**: Onshape usa *fully-contained* para caras en 3D (evita seleccionar geometría de fondo parcialmente visible), esto es importante — no uses intersección de bounding box, usa proyección de todos los vértices de la cara al plano de pantalla y verifica que **todos** caigan dentro del rectángulo.

```python
# viewport3d.py — ya tienes distinción click/drag por umbral de 4px

def _on_drag_move(self, current_pos):
    self.rubber_band_rect.setGeometry(
        QRect(self._press_pos, current_pos).normalized()
    )
    self.rubber_band_rect.show()

def _on_drag_end(self, end_pos, modifiers):
    self.rubber_band_rect.hide()
    rect = QRect(self._press_pos, end_pos).normalized()
    additive = bool(modifiers & Qt.ShiftModifier) or self.interactor.GetShiftKey()
    subtractive = bool(modifiers & Qt.ControlModifier) or self.interactor.GetControlKey()

    contained_faces = self._faces_fully_in_rect(rect)
    self.selection_manager.handle_rubber_band(contained_faces, additive, subtractive)
```

```python
def _faces_fully_in_rect(self, rect: QRect) -> set[int]:
    """Proyecta vértices de cada cara a screen-space; cara entra
    solo si TODOS sus vértices caen dentro del rect."""
    coord = vtk.vtkCoordinate()
    coord.SetCoordinateSystemToWorld()
    result = set()
    for face_idx, vertex_ids in self.face_vertex_cache.items():  # cachear al cargar modelo
        all_inside = True
        for vid in vertex_ids:
            coord.SetValue(*self.vertices[vid])
            sx, sy = coord.GetComputedDisplayValue(self.renderer)
            if not rect.contains(sx, self.viewport_height - sy):  # VTK Y invertido vs Qt
                all_inside = False
                break
        if all_inside:
            result.add(face_idx)
    return result
```

```python
# selection_manager.py — nuevo método
def handle_rubber_band(self, entities: set, additive: bool, subtractive: bool):
    if subtractive:
        self._selected -= entities
    elif additive:
        self._selected |= entities
    else:
        self._selected = set(entities)
    self.selectionChanged.emit(self._selected)
```

**Punto de rendimiento a vigilar**: proyectar cada vértice individualmente con `vtkCoordinate.GetComputedDisplayValue()` en un loop Python es lento en STEPs grandes (miles de vértices). Si notas lag al arrastrar el rectángulo, la alternativa es usar `vtkHardwareSelector` (selección por color-picking en buffer offscreen), que es lo que VTK recomienda para selección de área — pero es más código y más complejo de integrar con tu highlight actual. Empezaría con la versión simple de arriba y solo migraría si hay lag medible.

¿Confirmas si quieres Ctrl como sustractivo (Onshape real) o prefieres solo Shift-aditivo para simplificar el primer pase? 

responde en investigación_traceback.md (limpia primero el archivo)