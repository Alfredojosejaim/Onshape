# Respuesta al prompt nuevo (auditoría de cierre de picking)

## 1. `HighlightRenderer`: quedó la versión VECTORIZADA (loop Python eliminado)

Se confirmó que estaba implementado el loop literal (`for cid in range(n):
SetTuple3(...)`) y se sustituyó por (`desktop/viewport/highlight.py`):

- Colores base precomputados una vez en `base_colors_np` (`(n, 3)` uint8).
- `update()` = `copy()` + asignación indexada numpy (`rgb[idx] = (255,165,0)`,
  `rgb[h] = (120,190,255)`) + un único `numpy_to_vtk(..., deep=True)` →
  `SetScalars` + `Modified()`. O(n) en C por click, sin importar cuántas
  caras haya en el Set.
- Robustez añadida: ids fuera de rango se recortan antes de indexar (un
  `cell_id` rancio no tumba el frame); si el polydata cambia de tamaño se
  reconstruye la base. Se mantiene `self.colors` (ref viva al array en uso)
  y `self.base_colors` (dict) por compatibilidad con el resto del código.
- El slot traduce cara→celdas por rangos (`Scene.selected_cell_ids_for_faces`
  sobre el cache `face→[cell_ids]`, construido una sola vez en
  `set_model_geometry`), sin pasar por `face_index_map` completo en cada click.
- Cubierto por `tests/test_pick_tangent_faces.py::
  test_highlight_vectorized_update_matches_selection` (naranja/azul/base
  verificados leyendo el array `Colors` de vuelta).

## 2. `angularTolerance`: confirmada CONSTANTE por diseño, ahora parametrizada

Estado: sigue en 0.1 rad, pero ya no es un literal enterrado — es
`core.geometry.DEFAULT_ANGULAR_DEFLECTION` con `None` como default en toda
la cadena (`GeometryEngine.tessellate_shape` /
`_tessellate_with_face_mapping` → `StepAdapter.tessellate` →
`adapters/cad/base.py` → `CADService.tessellate_model`), resuelto por
`_resolve_angular()`. Comportamiento idéntico al anterior (0.1), un parámetro
de distancia ahora para estrecharlo.

Razonamiento: la tolerancia angular es un ángulo (radianes), invariante de
escala — no tiene sentido hacerla relativa al tamaño. El que cubre caras
pequeñas/fillets finos es el `linear_deflection` relativo (`diag*0.001`),
porque el criterio de chord height domina cuando la deflection lineal es
pequeña. Si la tangencia en fillets persiste tras el fix de tolerancia del
picker (0.0005), el próximo sospechoso es este: estrechar a 0.05.

## 3. Vértices no compartidos entre caras: confirmado, sin cambio de código

Verificado en la tessellation real (caja 10³ con fillet r=1.5, 524 tris):
las caras planas quedan en 2 triángulos enormes y los fillets finos (64–130
tris), con vértices duplicados por cara (misma coordenada, distinto índice).
Es el diseño correcto para `CellData` por cara sin ambigüedad de picking.
Efecto conocido documentado: posibles líneas de z-fighting/grietas sutiles
en aristas compartidas con AA — cosmético, no bug; no se fusiona malla
deliberadamente.

## 4. Test de regresión con geometría real: añadido

`tests/test_pick_tangent_faces.py` (3 tests, todos en verde):

- `test_pick_disambiguates_tangent_faces`: caja con fillet tangente
  (`edges("|Z").fillet(1.5)`), tessellation con face mapping; detecta la
  arista compartida plano↔fillet por proximidad de vértices, muestrea puntos
  DENTRO del triángulo plano pegados a la tangencia y hace ray-pick por CPU
  (Möller–Trumbore double-sided, equivalente al `vtkCellPicker` con
  `BackfaceCullingOff`). Assert: resuelve la cara plana, nunca el fillet.
  Falla exactamente con los dos bugs históricos (mapa por cara o picker
  tolerante que devuelve la vecina).
- `test_pick_spot_check_all_faces`: rayos sobre todas las caras resuelven su
  propia cara (cobertura global del mapeo).
- `test_highlight_vectorized_update_matches_selection`: ver §1.

Hallazgo al escribirlo: con tessellation por cara, los centroides de los
triángulos planos quedan a >2.3u de la arista (triángulos enormes), así que
muestrear centroides NO ejerce la tangencia — hay que muestrear junto a la
arista compartida. Dicho de otro modo: el caso reportado ("selecciona la
tangente") vive precisamente en esa franja que los centroides no tocan.

## Pendiente sugerido

Rubber-band select (máquina de estados original, punto 4): el release
handler ya distingue click/drag (umbral 4px) y deriva a rubber-band, pero no
hay implementación de selección por rectángulo. Siguiente paso si se pide.
