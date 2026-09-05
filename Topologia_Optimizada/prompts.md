Con ese pipeline, el patrón correcto en VTK es: **`vtkCellPicker` te da `CellId` global de un `vtkPolyData` combinado (probablemente `vtkAppendPolyData` de todas las caras), y el highlight no puede vivir en la property del actor** (eso es lo que te limita a una sola cara resaltada). Necesitas colorear celdas individuales vía `vtkUnsignedCharArray` como `CellData` scalars, y separar completamente el **estado de selección** (lógico) del **picking** (evento) y del **render** (highlight).

Aquí las instrucciones precisas para Muse Spark:

## 1. `SelectionManager` — estado puro, sin lógica de Qt ni VTK

```python
# selection_manager.py
from PySide6.QtCore import QObject, Signal
from typing import Set

class SelectionManager(QObject):
    selectionChanged = Signal(set)  # emite el nuevo Set[CadEntityRef]

    def __init__(self):
        super().__init__()
        self._selected: Set[CadEntityRef] = set()

    @property
    def selected(self) -> Set[CadEntityRef]:
        return frozenset(self._selected)

    def handle_pick(self, entity: CadEntityRef | None, additive: bool):
        if entity is None:
            if not additive:
                self._selected.clear()
                self.selectionChanged.emit(self._selected)
            return  # click vacío con Shift no hace nada (Onshape)

        if additive:
            if entity in self._selected:
                self._selected.remove(entity)      # toggle OFF
            else:
                self._selected.add(entity)          # toggle ON
        else:
            if self._selected == {entity}:
                return  # no-op, evita reflow innecesario
            self._selected = {entity}               # reemplaza

        self.selectionChanged.emit(self._selected)

    def clear(self):
        if self._selected:
            self._selected.clear()
            self.selectionChanged.emit(self._selected)
```

**Punto crítico**: si tu `SelectionManager` actual guarda `_selected` como variable singular (`self._selected_face`) en vez de `Set`, ahí está el bug raíz de "solo selecciona una cara". Pide a Muse Spark que audite esto primero antes de tocar nada más.

## 2. `Viewport3D` — captura de modificadores y distinción click/drag

```python
# viewport3d.py, dentro del handler de mouse release (NO en press)
def _on_left_button_release(self, obj, event):
    if self._is_drag(self._press_pos, self._current_pos, threshold_px=4):
        return  # dejar que la lógica de rubber-band lo maneje aparte

    click_pos = self.interactor.GetEventPosition()
    self.picker.Pick(click_pos[0], click_pos[1], 0, self.renderer)
    cell_id = self.picker.GetCellId()

    modifiers = QApplication.keyboardModifiers()
    additive = bool(modifiers & (Qt.ShiftModifier | Qt.ControlModifier))

    if cell_id == -1:
        entity = None
    else:
        face_id = self.scene.face_index_for_cell(cell_id)
        entity = CadEntityRef.from_face(face_id)

    self.selection_manager.handle_pick(entity, additive=additive)
```

Si actualmente estás decidiendo modificadores dentro del `vtkInteractorStyle` en vez de en `Viewport3D`/Qt, dile a Muse Spark que mueva esa lectura a nivel Qt (`QApplication.keyboardModifiers()`), porque VTK y Qt a veces desincronizan el estado de teclado cuando el foco cambia entre widgets.

## 3. Highlight multi-cara — el fix que realmente te falta

Esto es lo que probablemente rompe el "no permite desmarcar": si el highlight se aplica con `actor.GetProperty().SetColor(...)` sobre un actor completo, solo puedes resaltar una entidad a la vez porque es una property global del actor, no por celda.

```python
# highlight_renderer.py
import vtk

class HighlightRenderer:
    def __init__(self, polydata: vtk.vtkPolyData, n_cells: int):
        self.polydata = polydata
        self.base_colors = self._init_base_colors(n_cells)
        self.colors = vtk.vtkUnsignedCharArray()
        self.colors.SetNumberOfComponents(3)
        self.colors.SetName("Colors")
        self.polydata.GetCellData().SetScalars(self.colors)

    def update(self, selected_cell_ids: set[int], hovered_cell_id: int | None):
        self.colors.SetNumberOfTuples(self.polydata.GetNumberOfCells())
        for cid in range(self.polydata.GetNumberOfCells()):
            if cid in selected_cell_ids:
                rgb = (255, 165, 0)      # naranja Onshape-like
            elif cid == hovered_cell_id:
                rgb = (120, 190, 255)    # azul claro prehover
            else:
                rgb = self.base_colors[cid]
            self.colors.SetTuple3(cid, *rgb)
        self.polydata.Modified()
```

Y conectar `SelectionManager.selectionChanged` a un slot que traduzca `Set[CadEntityRef]` → `Set[cell_id]` (mapeo inverso de `face_index_for_cell`, necesitas cachear ese mapeo cara→lista de cell_ids una vez al cargar la malla) y llame a `HighlightRenderer.update()`.

## 4. Checklist de auditoría para Muse Spark, en orden

1. Confirmar que `SelectionManager` usa `Set`, no variable singular.
2. Confirmar que el highlight usa `CellData` por-celda, no `actor.GetProperty()`.
3. Mover lectura de modificadores Shift/Ctrl a nivel Qt en el release handler.
4. Verificar que `cell_id == -1` (click vacío) limpia selección solo si no hay modificador.
5. Cachear `face_id → List[cell_id]` una sola vez (no recalcular en cada pick).
6. Conectar `ConditionPanel` a `selectionChanged` en vez de a un callback directo del picker (para que quede desacoplado y sirva para BCs, loads, etc. igual que planeas para P2).

Si me pasas el código real de `SelectionManager` y del handler de mouse en `Viewport3D`, te devuelvo el diff exacto en vez de este esqueleto genérico.