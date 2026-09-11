# Sesión: viewport negro al importar + estabilidad + arranque

Fecha: 2026-09-11. Todo reversible donde se indica (marcas en código).

## 1. Negro al importar — causa raíz: TDZ en `App.tsx`

**Síntoma**: al importar un STEP, toda la ventana quedaba en negro (`#10131c`).

**Causa** (`src/App.tsx:242-266`, introducido por el cambio a viewport único):
`viewBodies` se calculaba con `models.flatMap(...)` leyendo `solidsByFile`,
pero ese estado se declaraba **después** (línea 266). Con `models=[]` el
`flatMap` nunca ejecutaba el callback y no se notaba; al importar el primer
modelo → `ReferenceError: Cannot access 'solidsByFile' before initialization`
→ React desmontaba el root → negro total.

**Diagnóstico**: se añadió `ErrorBoundary` (root + viewport) que mostró el
mensaje, y con el stack (`index-*.js:41:16356` + sourcemaps de la build
exacta) se mapeó a `App.tsx:244` (`solidsByFile`).

**Fix**: `solids` / `solidsByFile` / `meshByFile` movidos arriba de
`viewBodies` (marca `TDZ-FIX`). Revisado el resto del render: sin más
usos-antes-de-declarar.

## 2. Blindaje anti-pantalla-negra (sigue en pie)

- `src/components/ErrorBoundary.tsx` (nuevo): boundaries en `main.tsx`
  (toda la app) y `App.tsx` (viewport). Un fallo muestra mensaje + stack
  + botón Reintentar en vez de negro silencioso.
- `CadViewport.tsx`: construcción **atómica** de escena (grupo temporal +
  swap solo si todo sale bien; ante error se conserva la escena anterior),
  validación por cuerpo (coordenadas finitas, índices en rango),
  `fitCamera`/`fitToAll` ignoran valores no finitos, `try/catch` en la
  creación del renderer WebGL con mensaje visible.
- `src/lib/realdata.ts`: `decodeCleanArray` filtra no-finitos,
  `mapMeshPreview` rechaza superficies corruptas, `placeholderSurface()`
  (caja 100×60×40) para subidas sin backend en vez de viewport vacío.
- `backend/api.py` (`_clean`, marca `DECIM-ALIGN`): el diezmado de mallas
  grandes cortaba el array en plano y rompía tripletas xyz/triángulo; ahora
  diezma por filas completas.

## 3. Inestabilidad: zoom que se regresa, caras que parpadean

**Causa**: `viewBodies` era un array nuevo en cada render (hasta por
`mousemove` vía `onUpdateCoords`); el efecto del viewport lo veía como
"todo cambió": reconstruía la escena y hacía `fitToAll()` incondicional.

**Fix**:
- `viewBodies` y `selectedFaces` con `useMemo` en `App.tsx` (marca
  `STABILITY-FIX`): identidad estable.
- `fitToAll()` condicional en `CadViewport.tsx` (marca `FIT-ONCE`, ref
  `fitKeysRef`): solo reencuadra si cambia el conjunto de cuerpos o el
  modelo activo. Material/malla/sección/visibilidad reconstruyen sin mover
  la cámara. Doble-clic y botón FIT intactos.

## 4. Arranque lento

Medido: el `.bat` gastaba ~10 s solo en chequeos (4× `pip show` ≈ 8.3 s +
3× `python -c`). El arranque frío del backend (OCC/VTK) es aparte e
inevitable sin carga diferida (~4.4 s en caliente).

**Fix**:
- `backend/check_env.py` (nuevo, solo stdlib): todos los chequeos en un
  proceso (~0.5 s; pesados por versión vía `importlib.metadata`, sin
  importar DLLs). `INICIAR_APP.bat` pasos 3+4 reducidos a una llamada
  (marca `FAST-CHECK`).
- `index.html`: fuentes Google con `preload` asíncrono + fallback
  `noscript` (marca `STARTUP-FAST`); antes bloqueaban el primer pintado.

## 5. Verificación

- `npx tsc --noEmit`: limpio (se añadió `@types/react@19` + `@types/react-dom@19`
  como devDeps: el paquete `react@19` no trae tipos y ni siquiera compilaba un boundary).
- `npm run build`: OK (`dist/` está gitignorado, se regenera local).
- Tubería real con `backend/uploads/2 cuerpos.step`: `importStepBytes` →
  `getMeshPreview` → `getSolids` OK; `mapMeshPreview` OK (2612 vértices,
  4538 tris, `rangesCover=true`); geometría three.js con 0 normales NaN,
  radio ≈ 40 centrada.
- `backend/api.py`: sintaxis OK; `_clean` probado (filas alineadas tras diezmar).

## Archivos tocados

`src/App.tsx`, `src/components/CadViewport.tsx`, `src/components/ErrorBoundary.tsx`
(nuevo), `src/lib/realdata.ts`, `src/lib/camera3d.ts`, `src/main.tsx`,
`backend/api.py`, `backend/check_env.py` (nuevo), `INICIAR_APP.bat`,
`index.html`, `package.json`/`package-lock.json` (solo devDeps `@types/*`).
