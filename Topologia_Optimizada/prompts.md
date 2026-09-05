Encontré la causa raíz — y es exactamente el tipo de bug que ninguna auditoría del código VTK iba a detectar, porque **puede que no estés corriendo ese código en absoluto**.

## El hallazgo

Tu app tiene **dos implementaciones de viewport completamente separadas**, elegidas en tiempo de arranque en `desktop/ui/components/main_workspace.py`:

```python
if is_gl_available():
    self.viewport = Viewport3D()      # VTK real — donde están TODOS tus fixes
    self._use_vtk = True
else:
    self.viewport = SoftwareViewport() # fallback QPainter, sin GPU
```

`SoftwareViewport` usa su propia clase `_SoftwareSelectionManager`, con su propio método `pick()` — **completamente distinto** al `SelectionManager.handle_pick()` que hemos estado auditando y arreglando en las últimas rondas:

```python
def pick(self, x: int, y: int, ctrl: bool = False) -> None:
    ...
    # Toggle acumulativo tanto con clic normal como con Ctrl.
    if face in self._selected_faces:
        self._selected_faces.remove(face)
    else:
        self._selected_faces.append(face)
```

Este código:
- **Nunca reemplaza la selección** en click simple (viola el comportamiento Onshape que sí implementamos: click simple = reemplaza, no acumula).
- Trata Ctrl igual que click normal — no hay distinción aditiva/no-aditiva real.
- No tiene highlight vectorizado, no tiene `face_index_map` por-triángulo, no tiene rubber-band.

Si `is_gl_available()` está devolviendo `False` en tu máquina (entorno sin GPU/driver OpenGL correctamente detectado, GPU virtualizada, sesión remota, etc.), **toda la implementación correcta que auditamos —tolerancia de picker, Set multi-selección, rubber-band, highlight vectorizado— nunca se ejecuta**, y estás interactuando con este fallback legacy que nunca se actualizó.

## Verificación inmediata

Pide a Muse Spark (o corre tú mismo) esto al arrancar la app:

```python
from desktop.viewport.viewport_3d import is_gl_available
print("VTK disponible:", is_gl_available())
```

Si imprime `False`, ahí está confirmado el diagnóstico completo: los síntomas — "no selecciona más de una cara" y "al desmarcar, marca otra" (el toggle acumulativo de `_SoftwareSelectionManager` hace exactamente eso: cada click alterna esa cara en la lista sin lógica de reemplazo) — son consecuencia directa de estar en la ruta software, no de ningún bug residual en el pipeline VTK que ya cerramos.

## Dos caminos, dependiendo del resultado

1. **Si `is_gl_available()` es `False` por causa corregible** (falta de driver, config de OpenGL, entorno virtualizado sin passthrough GPU): el fix es arreglar la detección/entorno GL, no el código de selección — todo lo que ya construimos empieza a funcionar solo.
2. **Si necesitas que `SoftwareViewport` sea un fallback viable** (por diseño, para máquinas sin GPU): hay que portar la misma máquina de estados (`Set`, reemplazo vs. toggle vs. rubber-band) a `_SoftwareSelectionManager`, duplicando la lógica ya que no comparten una base común — o mejor, refactorizar para que ambos viewports deleguen al mismo `SelectionManager` de estado puro y solo difieran en el mecanismo de picking/render.

¿Qué te imprime `is_gl_available()`?