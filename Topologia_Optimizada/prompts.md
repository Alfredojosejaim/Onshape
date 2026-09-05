Encontré el error, y es mío desde el turno 1: **especifiqué mal el modelo de selección de Onshape**. No hace falta seguir cazando bugs en el pipeline VTK — el pipeline ya funciona bien, el problema es que le pedí a Muse Spark que implementara una semántica equivocada.

## La corrección, con fuente oficial

Verifiqué contra la documentación oficial de Onshape ("Selection"): la selección en Onshape funciona como **toggle puro, sin necesidad de modificador**. Onshape confirma que su selección funciona como un interruptor: clic para seleccionar, clic de nuevo para deseleccionar, y que el clic plano ya se comporta de forma aditiva —lo que en otras apps esperarías de Ctrl+click— sin necesidad de mantener presionada ninguna tecla.

Es decir, mi especificación original ("click plano reemplaza, Shift+click hace toggle") estaba invertida respecto al Onshape real. Lo correcto es:

```
on_click(entity):
    if entity is None:
        selected.clear()                    # clic en vacío: limpia todo
    elif entity in selected:
        selected.remove(entity)              # YA estaba: toggle OFF
    else:
        selected.add(entity)                 # no estaba: toggle ON (añade, no reemplaza)
```

Sin ramas de `additive`/modificador para el click puntual. Esto explica **ambos** síntomas a la vez con un solo cambio: no podías multi-seleccionar porque cada click reemplazaba en vez de añadir, y perdiste el deselect-por-click porque yo mismo introduje ese "no-op" pensando que era el comportamiento correcto de Onshape.

## Fix preciso para Muse Spark

**1. `SelectionManager.handle_pick()`** — quitar la lógica condicional de `additive`, siempre toggle:

```python
def handle_pick(self, entity: Optional[CadEntityRef], additive: bool = True) -> None:
    """Onshape real (docs oficiales): click SIEMPRE hace toggle, sin
    necesitar Shift/Ctrl. 'Click to select, click again to deselect...
    additively select and deselect (the same behavior you would expect
    from Ctrl+click)' -- el click plano YA es aditivo.
    """
    if entity is None:
        if self._selected:
            self._selected.clear()
            self._sync_legacy_after_set_change()
            self.selectionChanged.emit(self.selected)
            self._emit_legacy()
        return

    if entity in self._selected:
        self._selected.remove(entity)
    else:
        self._selected.add(entity)

    self._sync_legacy_after_set_change(entity)
    self.selectionChanged.emit(self.selected)
    self._emit_legacy()
```

**2. `handle_rubber_band()`** — por simetría/consistencia, el drag simple también debería ser aditivo (unión), no reemplazo; solo Ctrl+drag resta (esto ya está bien y confirmado: la documentación indica explícitamente Ctrl+arrastre para deseleccionar):

```python
def handle_rubber_band(self, face_indices, subtractive: bool = False) -> None:
    faces = {int(f) for f in (face_indices or set())}
    ...
    before = set(self._selected)
    if subtractive:
        self._selected -= entities
    else:
        self._selected |= entities   # simple = aditivo, igual que el click
    if self._selected == before:
        return
    ...
```

(Quita el parámetro `additive` distinto de `subtractive` en la firma y en `_finish_rubber_band()` — ya no hay dos modos, solo "unión" o "resta".)

**3. Tests a actualizar** — `tests/test_rubber_band_select.py` tiene casos que verifican explícitamente "drag simple reemplaza" y "click simple reemplaza" en `test_pick_*`; hay que reescribirlos para afirmar unión/toggle en vez de reemplazo, no son regresiones a preservar, son tests de la especificación incorrecta anterior.

Con esto, click simple sobre varias caras acumula sin tocar Shift (resuelve #1), y click sobre una cara ya seleccionada la quita (resuelve #2) — exactamente el comportamiento que recordabas y que yo había alterado por mi error de especificación inicial.