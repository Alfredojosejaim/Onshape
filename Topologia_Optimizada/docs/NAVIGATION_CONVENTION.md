# Convención de Navegación de Cámara (Órbita / Pan / Zoom)

> Documento de referencia de la convención CAD/Onshape/Fusion esperada para los
> controles de cámara del viewport. Incluye el diagnóstico del bug de inversión
> reportado, cómo está cableada cada capa (NavigationManager → viewport →
> cámara), los signos de cada implementación y el plan de corrección.
>
> Objetivo: servir de puntal para futuras implementaciones de **configuraciones
> personalizadas** de navegación y para evitar regresiones de signo.

---

## 1. Convención objetivo (modo CAD, "el modelo sigue al cursor")

El usuario espera la convención de las herramientas CAD/Onshape/Fusion:

| Gesto | Convención esperada |
|-------|---------------------|
| Arrastrar a la **derecha** | La pieza **gira a la derecha** (rota en el sentido del arrastre). |
| Arrastrar a la **izquierda** | La pieza **gira a la izquierda**. |
| Arrastrar **hacia arriba** | La pieza **va hacia arriba** (se ve más su cara superior). |
| Arrastrar **hacia abajo** | La pieza **va hacia abajo**. |
| **Pan** (arrastrar con botón de pan) | El modelo **sigue al cursor** (derecha→derecha, abajo→abajo). |
| **Rueda hacia arriba** (`wheel_delta > 0`) | **Zoom in** (acercar). |
| **Rueda hacia abajo** (`wheel_delta < 0`) | **Zoom out** (alejar). |

En una frase: *arrastras el objeto y lo "agarras"*; el objeto rota/desplaza con
el cursor, y la rueda arriba acerca.

---

## 2. Capas y flujo

```
Input (ratón / rueda / teclado)
   │
   ▼
viewport (desktop/viewport/)
   ├── Viewport3D (GPU/VTK)      ──►  CameraController.orbit/pan/dolly
   └── SoftwareViewport (QPainter) ─►  _rot_x / _rot_z / _cam_x / _cam_y / _zoom
   │
   ▼
NavigationManager (core/navigation.py)  → decide QUÉ acción (ORBIT/PAN/ZOOM_IN/...)
```

Regla de arquitectura (documentada en `camera.py`):

- `NavigationManager` decide **QUÉ** acción pide el usuario.
- La **cámara** decide **CÓMO** se transforma la vista.

### Selección del viewport (`desktop/viewport/viewport_3d.py`)

`_ViewportHost` (en `desktop/ui/main_window.py`) elige automáticamente:

- `Viewport3D` (VTK/OpenGL) si `is_gl_available()` devuelve `True`.
- `SoftwareViewport` (QPainter) si no hay OpenGL.

`is_gl_available()` hace un *probe* real con `vtkOpenGLRenderWindow` en un
subproceso (evita que un crash de VTK tumbé el proceso principal) y cachea el
resultado.

> ⚠️ Importante: en sistemas con GPU se usa `Viewport3D`; sin GPU,
> `SoftwareViewport`. En los tests siempre se valida `CameraController` (que es
> agnóstico de GUI). **El `SoftwareViewport` NO está cubierto por tests de
> convención**, lo que permite que sus signos divergan del `CameraController`.

---

## 3. Estado actual de cada implementación (diagnóstico)

### 3.1 CameraController (VTK) — `desktop/viewport/camera.py`

- `orbit(dx, dy)` (línea 114): trackball libre "follow-the-pointer".
  `drag = right*(-dx) + up*dy`, `axis = cross(drag, forward)`. El `-dx`
  hace que la pieza siga al cursor horizontalmente (arrastrar derecha →
  la cámara orbita a la derecha alrededor de la pieza); el `+dy` hace lo
  mismo verticalmente (arrastrar arriba → la cámara se eleva).
  **Importante**: VTK (`QVTKRenderWindowInteractor`) invierte la Y de Qt
  (`y_vtk = height - y_qt - 1`), por lo que en VTK `dy > 0` es arrastrar
  **arriba**; esto fue el origen del bug de inversión (se creía que era la
  horizontal la invertida, pero era la vertical la que necesitaba el
  ajuste de Y).
- `pan(dx, dy)` (línea 181): `delta = right*(-dx*scale) + up*(-dy*scale)`.
  Horizontal con signo `-dx` (arrastrar derecha mueve el modelo a la
  derecha), vertical `-dy` (compensa el flip de Y de VTK: arrastrar abajo
  mueve el modelo abajo).
- `dolly(steps, ...)`: `factor = exp(-steps*sensitivity)`;
  `steps > 0` acerca (distancia disminuye), `steps < 0` aleja.

**Validación existente** (`tests/test_camera_controller.py`):
- `test_orbit_vertical_sense_follows_pointer` (línea 106): fija que
  arrastrar arriba (dy<0 en VTK) baja la cámara (el modelo sube).
- `test_orbit_horizontal_sense_unaffected` (línea 121): fija que arrastrar
  a la derecha (dx>0) mueve la cámara a `+X` en vista FRONT (órbita
  derecha = pieza gira a la derecha).
- `test_pan_follows_pointer_horizontal` / `_vertical`: fijan que el pan
  sigue al cursor en ambos ejes.
- `test_zoom_wiring_zoomin_brings_closer`: fija el cableado
  `ZOOM_IN → dolly(+)` (acercar).
- `test_zoom_inclined_camera` (línea 181): `dolly(+)` acerca.

### 3.2 SoftwareViewport (QPainter) — `desktop/viewport/software_viewport.py`

Estado inicial: `_rot_x=30`, `_rot_z=-45`, `_zoom=100`, `_cam_x=_cam_y=0`.

Input (líneas 457-489):
- `mouseMoveEvent`: `dx,dy` = desplazamiento Qt (**dy>0 = arrastrar abajo**).
- Modo `orbit`: `_rot_z += dx*0.5` y `_rot_x += dy*0.5` (líneas 468-469).
- Modo `pan`: `_cam_x += dx*zoom*0.002`, `_cam_y += dy*zoom*0.002` (471-472).
- `wheelEvent` (484-488): `delta=angleDelta().y()/120`, `factor=1-delta*0.15`.

Proyección en pantalla (líneas 596-599, 637-638):
- `X = cx + (rx + cam_x)/zoom`
- `Y = cy - (ry + cam_y)/zoom` (la componente Y está **invertida** en pantalla)

Rotación (líneas 37-54): `rot = Rz(rot_z) @ Rx(rot_x)`, Y global arriba.

**Hallazgos del análisis:**

| Operación | Código actual | Resultado observado | ¿Correcto CAD? |
|-----------|---------------|---------------------|----------------|
| Órbita horizontal | `_rot_z += dx` | Al arrastrar derecha el borde derecho **baja** (rotación horaria en pantalla) | PENDIENTE de confirmar |
| Órbita vertical | `_rot_x += dy` | Al arrastrar arriba (dy<0) reduce `rot_x` | PENDIENTE |
| Pan horizontal | `_cam_x += dx` | El modelo sigue al cursor (derecha→derecha) | ✅ |
| Pan vertical | `_cam_y += dy` | Al arrastrar abajo el modelo **sube** (invertido) | ❌ |
| Zoom | `factor=1-delta*0.15` | Rueda arriba (delta>0) reduce zoom → acerca | ✅ |

**Conclusión del diagnóstico:** el `SoftwareViewport` tiene al menos el **pan
vertical invertido** y requiere alinear su órbita y signos con el
`CameraController` (la referencia validada). El `CameraController` ya fue
corregido en su vertical en un ciclo previo.

---

## 4. Datos empíricos (proyección del SoftwareViewport, vista "front")

Lecturas de referencia con `rot = Rz(rot_z)@Rx(rot_x)`, `zoom=100`, `cx=cy=200`,
puntos del modelo en `(1,0,0)` (borde derecho), `(0,1,0)` (borde superior),
`(0,0,1)` (frente). Movimiento en pantalla `(ΔX, ΔY)`:

```
base (rot_x=0,rot_z=0):      right(+0.0100,+0.0000)  top(+0.0000,-0.0100)
Órbita horizontal:
  rot_z += 30:  right(+0.0087,-0.0050)  top(-0.0050,-0.0087)   ← borde derecho BAJA (horario)
  rot_z -= 30:  right(+0.0087,+0.0050)  top(+0.0050,-0.0087)   ← borde derecho SUBE (antihorario)
Órbita vertical:
  rot_x = -30:  top(+0.0000,-0.0087)  front(+0.0000,-0.0050)
  rot_x = +30:  top(+0.0000,-0.0087)  front(+0.0000,+0.0050)
```

> Nota: la magnitud de los desplazamientos es pequeña porque `zoom=100` y los
> puntos de referencia están a una unidad; la *dirección* es lo que importa.

---

## 5. Plan de corrección (por confirmar)

1. **Confirmar el viewport real en uso** (GPU → `Viewport3D`/`CameraController`;
   sin GPU → `SoftwareViewport`). En este sistema la sonda da `GL_AVAILABLE=True`.
2. **Alinear `SoftwareViewport` a la convención del `CameraController`**:
   - Órbita horizontal: ajustar signo de `rot_z` para "girar a la derecha".
   - Órbita vertical: ajustar signo de `rot_x` para "arrastrar arriba → sube".
   - Pan vertical: negar `_cam_y` (arrastrar abajo → modelo abajo). ✅ *(hecho)*
   - Zoom: mantener "rueda arriba → acercar" (ya coincide). ✅ *(verificado)*
3. **Añadir tests de convención** para `SoftwareViewport` en modo `offscreen`
   (análogos a `test_camera_controller.py`) para fijar los signos y evitar
   regresiones en configuraciones personalizadas.
4. **Validar** con `python -m py_compile` y la suite (`pytest`).
5. Actualizar `PROJECT_STATUS.md` y, si el usuario lo pide, realizar commit.

## 6. Estado de la corrección aplicada

> Última actualización: ciclo de inversión de cámara (zoom + órbita + pan).

### Aplicado (Viewport3D / CameraController — el que usa GPU)
- **Zoom**: `Viewport3D._resolve_and_execute` ahora cablea
  `ZOOM_IN → dolly(+0.8)` (acercar) y `ZOOM_OUT → dolly(-0.8)` (alejar).
  Antes estaba al revés (`dolly(+)` acerca, así que "zoom in" alejaba).
- **Órbita** (`CameraController.orbit`): se negó `dx`
  (`drag = right*(-dx) + up*dy`) para que la pieza siga al cursor
  horizontalmente.
- **Pan** (`CameraController.pan`): se negó `dy`
  (`delta = right*(-dx) + up*(-dy)`) para compensar el flip de Y de VTK y
  que el pan siga al cursor verticalmente.
- Causa raíz de las inversiones "solo órbita" / "solo pan": el
  `QVTKRenderWindowInteractor` invierte la coordenada Y de Qt
  (`y_vtk = height - y_qt - 1`), por lo que la semántica de `dy` es opuesta
  a la de pantalla. El pan horizontal ya era correcto; el vertical necesitaba
  el `-dy`.

### Pendiente (SoftwareViewport — fallback sin GPU)
- La órbita del `SoftwareViewport` (Euler `_rot_x`/`_rot_z`) no se ha
  modificado: requiere validación comparativa dedicada contra el
  `CameraController` para fijar sus signos sin riesgo. El pan vertical ya se
  corrigió en el código.

## 7. Reglas de oro para futuras configuraciones

- **Una única fuente de verdad**: el `CameraController` (la referencia
  validada). Cualquier viewport nuevo debe reproducir su convención.
- **Los tests de convención son obligatorios** para cada viewport nuevo
  (especialmente el fallback por software, que es el que tiende a quedar
  desalineado).
- Recuerda que en Qt/eventos `y` crece hacia **abajo** (arrastrar arriba ⇒
  `dy<0`); en proyección por software la componente `Y` se invierte al dibujar.
- Si una configuración personalizada cambia un signo, debe hacerlo en **ambos**
  viewports a la vez, o el comportamiento divergirá según haya GPU o no.
