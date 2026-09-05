Buena elección — es barato de implementar y evita repetir la confusión de la sesión anterior en cualquier máquina remota/VM. Dos partes: log al arranque (para diagnóstico) y badge visible en el viewport (para que no dependa de mirar logs).

## 1. Log al arranque

En `desktop/ui/main_window.py`, justo después de construir el workspace (línea 94, donde ya tienes `self.host`):

```python
central = MainWorkspaceBuilder(self).build()
...
import logging
logging.getLogger(__name__).info(
    "Viewport backend: %s", "VTK (GPU)" if self.host._use_vtk else "Software (sin GPU)")
```

Ya usas `import logging as _logging` más abajo en el archivo (línea 218) — puedes mover el `import logging` arriba con el resto de imports en vez de inline, es más limpio.

## 2. Badge visible — extiende el badge existente, no crees uno nuevo

Ya tienes exactamente el mecanismo que necesitas: `OverlayBuilder.build()` en `overlays.py` ya coloca un badge "Optimización · SIMP · Standalone" en la esquina superior izquierda del viewport vía `host.place("badge", badge)`. Añádele un tercer pill con el backend:

```python
# overlays.py, dentro de OverlayBuilder.build(), junto a t1/t2
t3 = QLabel("GPU · VTK" if host._use_vtk else "Software · sin GPU")
t3.setProperty("badge", True)
if not host._use_vtk:
    t3.setStyleSheet("color: #e0a030;")  # aviso visual sutil si es el fallback
bl.addWidget(t3)
```

Esto es exactamente el tipo de indicador que te habría ahorrado la ronda entera de "¿es el fallback o no?" de la sesión pasada — visible sin abrir consola, en cualquier máquina.

## 3. Opcional: mensaje en la status bar si cae al fallback

Ya que `statusBar().showMessage(...)` está establecido como patrón en toda la app, si `_use_vtk` es `False` vale la pena un aviso más explícito al arrancar (no solo el badge pasivo), porque el fallback implica funcionalidad reducida (sin rubber-band, sin toggle correcto, per lo anotado la sesión pasada como "trabajo futuro si se quiere paridad"):

```python
if not self.host._use_vtk:
    self.statusBar().showMessage(
        "Aceleración GPU no disponible: usando renderer por software (funcionalidad de selección reducida).", 8000)
```

Con los tres puntos cubiertos, cualquier sesión futura empieza sabiendo qué backend corre sin tener que investigarlo desde cero.