# Auditoría técnica del proyecto

**Fecha:** 2026-09-16
**Alcance:** `HTML_APP/topología-optimizada`
**Estado del árbol al auditar:** limpio antes de la auditoría; no se modificó
la lógica de la aplicación.

## Veredicto

El proyecto tiene una arquitectura funcional y una base de regresión saludable:
la UI React se compila, el núcleo Python ejecuta SIMP/FEA y la suite existente
cubre el flujo estructural, el mapeo degradado de condiciones, el halo de
preservación y la reconstrucción básica. La documentación anterior de este
archivo estaba desactualizada respecto de esos cambios.

El riesgo principal sigue estando en la **reconstrucción CAD**: el suavizado
se calcula, pero el `BRepFitter` prueba primero la malla rellenada sin
suavizar. Por tanto, que exista una etapa `SMOOTHED_MESH` no garantiza que el
STEP final sea el resultado suavizado. El escenario B y el fallback visual
también necesitan una prueba/certificación adicional antes de considerarlos
equivalentes al flujo real.

## Evidencia ejecutada

| Check | Resultado |
|---|---|
| `npm run lint` | OK (`tsc --noEmit`) |
| `npm run build` | OK; Vite produjo `dist/` |
| `python -m pytest backend\tests -q --disable-warnings --maxfail=1` | **75 passed**, 3 warnings |
| Dependencias científicas | Kratos fue detectable durante la suite; el flujo local mantiene fallback explícito |

## Hallazgos

### 1. Alto — el B-Rep puede ignorar el suavizado

**Evidencia:** `backend/core/cad_reconstruction.py:1965-1975`.

`ReconstructionPipeline.run()` ejecuta `fill -> smooth`, pero construye
`candidates` en este orden:

1. `hole_fill_data` (relleno, sin suavizado);
2. `smoothed_data`;
3. malla cruda.

El primer candidato válido que el fitter acepta corta el bucle en
`1989-1997`. Así, el STEP normalmente puede salir de la malla rellenada, pese
a que el comentario afirma “prefer smoothed”. Esto contradice el contrato
documentado del pipeline y explica por qué una superficie final puede seguir
facetada o contener el escalonado previo al suavizado.

**Acción recomendada:** invertir el orden a `smoothed -> filled -> raw` y
añadir una prueba con un fitter espía que verifique que el primer candidato
recibido es `smoothed_data`. Mantener `fill_before_smooth` y el metadata actual.

### 2. Medio — escenario B no tiene cobertura de regresión suficiente

**Evidencia:** `backend/core/generative_engine.py:1137-1152`; las pruebas
generativas existentes (`backend/tests/test_generativa_flujo.py`) cubren
escenario A y fallback legacy, pero no escenario B.

El escenario B reemplaza `engine.mesh_nodes` y `engine.mesh_elements` por la
malla puente. Sin embargo, la instancia conserva referencias creadas para la
malla original (`face_surface_elements` y
`_surface_matches_mesh=True`). La protección existente para no usar índices
de superficie incompatibles solo se activa explícitamente en el camino
`design_space="envelope"` (`347-352`, `1120-1123`), no en el camino B.

Esto deja un riesgo de mapeo de cargas/fijaciones/protecciones a nodos o
triángulos de otra malla. El código puede degradar a una distribución
uniforme/fallback, pero la equivalencia geométrica con las caras seleccionadas
no está demostrada.

**Acción recomendada:** al construir la malla puente, marcar explícitamente
que la triangulación de superficie original no coincide con la malla nueva y
definir un mapeo de targets a nodos puente; después añadir un test B con dos
targets, una carga y una fijación que compruebe `_halo_nodes`,
`_preserved_elements`, densidades finitas y reconstrucción.

### 3. Medio — fallback mock permitido en desarrollo no queda visible como
`MOCK-FALLBACK` en la UI principal

**Evidencia:** `src/lib/bridge.ts:19-20,36-57` marca respuestas mock con
`mock: true`, y `src/lib/jobs.ts:53-58` rechaza el sondeo mock. No obstante,
`src/App.tsx:1079-1118` ejecuta un timer local tras pulsar Iniciar cuando no
hay bridge y genera compliance/volumen sintéticos, incluyendo
`MOCK_BASE_COMPLIANCE = 148.5`.

La regla del proyecto permite este fallback únicamente después de Iniciar,
anclado al estado propio y etiquetado. En el código revisado la etiqueta está
en comentarios, pero no se encontró una marca de interfaz visible
`MOCK-FALLBACK`. Esto puede hacer que un usuario interprete la animación como
un resultado científico real.

**Acción recomendada:** establecer un estado explícito `isMockFallback` al
entrar en ese timer, mostrar una etiqueta persistente junto a los resultados y
limpiar esa marca al recibir un resultado de `mapSimpResult` del backend.

### 4. Bajo — los contratos de resultado dependen de señales opcionales

`mapFeaResult` y `mapSimpResult` (`src/lib/realdata.ts:95-137`) devuelven
`null` cuando faltan métricas mínimas, lo cual es preferible a inventar
cifras. Sin embargo, el contrato no distingue entre “estudio aún no
terminado”, “resultado incompleto” y “error”; esa distinción queda repartida
entre polling, `optNotice` y el estado React.

**Acción recomendada:** tipar un resultado discriminado (`pending`,
`completed`, `invalid`, `error`) en el límite bridge/UI. No es bloqueante para
la ejecución actual, pero reduciría estados ambiguos en WebView2.

## Aspectos confirmados como correctos

- El proyecto separa el host pywebview del proceso científico para evitar
  conflictos con DLL nativas.
- El bridge devuelve error explícito si un método no está expuesto
  (`src/lib/bridge.ts:21-32`) y marca las respuestas mock.
- La generativa falla explícitamente sin cargas/fijaciones reutilizables ni BC
  legacy (`backend/core/generative_engine.py`, `GEN-NOCOND`).
- Las cargas y fijaciones se convierten en un halo preservado por defecto en
  `solve_simp`; el caso de cobertura total se revierte y se reporta como
  `full_coverage`.
- La reconstrucción aplica `preserved_elements`/`frozen_elements` a densidades
  elementales y nodales antes de extraer la isosuperficie.
- El orden `fill -> smooth` está cubierto por
  `backend/tests/test_reconstruction_fill_order.py`.
- La UI no muestra resultados reales por defecto: los mapeadores exigen
  métricas mínimas y el flujo backend se sondea mediante job.
- `backend/vendored/simp.py` permanece congelado; las opciones avanzadas viven
  en `core/topopt.py`, conforme a `AGENTS.md`.

## Cobertura faltante priorizada

1. Verificar con un fitter espía que el STEP use la malla suavizada.
2. Añadir regresión del escenario B con condiciones sobre los dos sólidos
   objetivo.
3. Ejecutar una prueba de integración WebView2/pywebview que confirme que el
   fallback local muestra `MOCK-FALLBACK` y nunca cifras antes de Iniciar.
4. Probar exportación y reimportación del STEP generado, incluyendo
   `registerReconstruction`, no solo el diccionario de reconstrucción.
5. Medir que el `physical_volume_fraction` reportado sea el que consume la UI
   cuando hay regiones preservadas y obstrucciones.

## Orden de trabajo recomendado

1. Corregir la prioridad de candidatos del fitter y añadir la regresión
   unitaria.
2. Cerrar el contrato de mapeo de la malla puente y cubrir escenario B.
3. Hacer visible el estado `MOCK-FALLBACK`.
4. Repetir lint, build y la suite completa; después validar una corrida real
   con STEP, carga, fijación, exportación y reimportación.

No se implementaron estas correcciones en esta auditoría: este documento
registra el estado observado, la evidencia y el backlog verificable.

## Addendum 2026-09-17 — cierre verificado de H1/H2/H3

Verificación posterior (árbol limpio, sin cambios de lógica):

- **H1 Alto (B-Rep ignoraba suavizado) → CERRADO.** `backend/core/cad_reconstruction.py:2353-2365` construye `candidates = smoothed → filled → raw` con `brep_source` en metadata. El comentario "prefer smoothed" ahora coincide con el código.
- **H2 Medio (escenario B sin regresión) → CERRADO.** `backend/core/generative_engine.py:1540-1596` invalida explícitamente `engine._surface_matches_mesh = False`, ancla `bridge.target_node_sets` por extremos y expone `result["_bridge"] = {surface_matches_mesh: False, target_node_sets}`. `backend/tests/test_generativa_flujo.py:432-471` (`test_scenario_b_bridge_invalidates_surface_and_maps_targets`) cubre dos targets + carga + fijación y assert `_halo_nodes`, `_preserved_elements`, densidades finitas y reconstrucción. `pytest backend/tests/test_generativa_flujo.py`: **11 passed**.
- **H3 Medio (MOCK-FALLBACK invisible) → CERRADO.** `src/App.tsx:478-481,1869-1873` tiene `isMockFallback` + badge persistente "MOCK-FALLBACK — animación local, no resultado científico"; `src/lib/bridge.ts:54` documenta el etiquetado.
- **Queda abierto:** H4 (resultado discriminado `pending/completed/invalid/error`), exportación + reimportación STEP con `registerReconstruction`, y `physical_volume_fraction` vs UI con preservadas/obstrucciones. Suite completa `backend/tests` en curso sin fallos a los 120 s (81+ tests vistos pasar); el run completo excede el timeout del runner y queda como validación manual pendiente.

## Addendum 2026-09-17 (2) — cierre de H4, STEP roundtrip y physical_volume_fraction

Implementación mínima aplicada (Fase D):

- **H4 → CERRADO.** `mapFeaOutcome`/`mapSimpOutcome` ya existían en `src/lib/realdata.ts:95-164`; el poll SIMP ya los usaba (`App.tsx:761`) pero el poll FEA seguía con `mapFeaResult` crudo. Cambio: `src/App.tsx` importa `mapFeaOutcome` y `feaPoll` clasifica `pending/completed/invalid/error` con `optNotice` fail-loud, sin inventar cifras. `npm run lint` (tsc --noEmit): OK.
- **Export + reimport STEP → CERRADO (con prueba).** `backend/tests/test_generative_step_roundtrip.py:26-67`: SIMP A + `registerReconstruction` + `exportStep` + `importStep` del STEP generado, assert `num_solids >= 1` y `brep_source == "smoothed"`. Verificado: **1 passed**.
- **physical_volume_fraction → CERRADO.** `mapSimpResult` (`realdata.ts:181-183`) consume `physical_volume_fraction` cuando existe (rho-ponderado sobre activos) en vez del target; el core lo reporta (`topopt.py:1398`, `vendored/simp.py:596`). El roundtrip assert ambos (`final` y `physical`) en rango. Verificado: `test_mock_fallback_contract + test_heaviside_extrusion + test_reconstruction_fill_order`: **21 passed**; `test_generativa_flujo.py`: **11 passed**.
- Sin regresiones detectadas en los tests corridos. Backlog restante real: ver `inventario.md` (ESO/Level-Set, MMA, tensión, manufacturing constraints, UI Térmico/Modal, remallado/decimación).

## Addendum 2026-09-17 (3) — auditoría completa: TODO BIEN salvo 1 bug real (corregido)

Comando y resultado:

| Check | Resultado |
|---|---|
| `npm run lint` (tsc --noEmit) | OK |
| `npm run build` (Vite) | OK, `dist/` generado |
| `python -m pytest backend/tests` | **94 passed** en 114 s, 3 warnings (ver nota bug) |
| `git status` | Solo `M prompt.md, backend/api.py, src/App.tsx, .gitignore` (trabajo propio) + `?? backend/uploads/tet.stl` (artefacto drag&drop de usuario, ahora ignorado) |

Hallazgo único — **bug real, NO latente: deadlock en `Api._submit`** (`backend/api.py:314-337`):
causa: el `Lock` se tomaba antes de `pool.submit` + `add_done_callback`. Si el job terminaba antes del `add_done_callback` (caso del test `test_polljob_error_string.py`, cuyo `_boom` falla al instante), `concurrent.futures` ejecuta el callback en el mismo hilo y `_done` pedía el `Lock` no reentrante ya tomado → cuelgue infinito. Era invisible en producción porque los jobs reales tardan (el callback corre en el worker), pero cualquier job rápido colgaba la API.
Corrección mínima: registrar el job en el dict, soltar el lock, hacer `submit`, reasociar el `future` y llamar `add_done_callback` fuera del lock (marcado `JOB-DEADLOCK`, reversible). Verificado: el test pasa en 3.08 s y la suite completa llega a 94 passed (antes se colgaba en el test 83).
Regresión que lo cubre: `backend/tests/test_polljob_error_string.py` (existente; ahora ejerce el camino rápido sin colgarse).

Contratos re-verificados (HECHO en código + tests en verde):
bridge mock etiquetado, `jobs.ts` rechaza mock, badge `MOCK-FALLBACK`, outcomes discriminados FEA+SIMP, halo/preservadas, `brep_source=="smoothed"`, roundtrip STEP con `registerReconstruction`, `physical_volume_fraction` en UI.
Sin cambios de arquitectura ni refactors. No se commitea: queda en árbol para tu revisión.

## Addendum 2026-09-17 (4) — "backend no responde (pollJob): WinError 10061"

Diagnóstico (Fase B, evidencia en `backend/server_stdout.log`):
tu corrida 1 (17:21–17:29, envelope 60k tets, threshold 0.3) completó solve + reconstruct + register + export + reimport sin errores. La corrida 2 (17:43–, threshold 0.5) hizo solve OK (17:45:14) y `GEN reconstruct done: BREP_SOLID` (17:47:49); el log se corta ahí, sin traceback y sin "Stored computed shape". `WinError 10061` = connection refused = nada escucha en el puerto = **el proceso `server.py` murió entre el fin de la reconstrucción y el siguiente poll** (muerte nativa/OOM: no deja traceback). El cálculo en sí había terminado; lo que se perdió es el registro/export posterior. Causa nativa exacta indeterminable desde aquí (candidatos: pico de memoria en B-Rep fit/sewing con 60k densidades, u OCC). Nota: el aviso `falling back to UNIFORM per-node force ... across 234 nodes` aparece en ambas corridas (también en la buena), así que no es la causa.
Corrección aplicada (Fase D, `backend/app_desktop.py`, reversible `DEAD-SERVER`): el puente distingue connection-refused (proceso muerto, confirma con `server.poll()`) de timeout (proceso ocupado) y devuelve causa accionable con exit code + puntero a logs, en vez del crudo `URLError 10061`. La UI (`jobs.ts` + `optNotice`) ya propaga ese detalle sin cambios.
Verificación: `py_compile` OK; `_make_bridge` contra puerto muerto devuelve el mensaje con exit code; `test_mock_fallback_contract + test_polljob_error_string`: **8 passed**.
Para tu caso concreto: reabre la app (el `finally` de `main` ya mató el resto) y repite; si vuelve a morir en el mismo punto, prueba malla más gruesa (el envelope genera 60k tets: `resolution`/`padding` en el panel generativo) o threshold 0.3 (el que sí completó).

## Addendum 2026-09-17 (5) — el 10061 también en threshold 0.3: dos causas, tres fixes

Nueva evidencia (`server_stdout.log` 18:25–18:33, threshold 0.3, la config que sí funcionó a las 17:28): solve OK + `reconstruct done BREP_SOLID`, y el log vuelve a cortarse ahí. Además hay dos `ConnectionAbortedError WinError 10053` en `wfile.write`: el cliente abortó mientras el servidor escribía una respuesta. Diagnóstico completo (Fase B):
1. El proceso muere tras `reconstruct done` también con 0.3 → no es el threshold; con 8 GB RAM y un único proceso vivo desde las 17:20 acumulando modelos OCC + picos del ajuste B-spline sobre 60k tets, el candidato es OOM/muerte nativa no determinista (sin traceback).
2. El servidor es MONOHILO con backlog TCP de 5: los handlers bloqueantes (register/export, minutos) + sondeo cada 1s (varios hooks) llenan la cola → polls RECHAZADOS con 10061 aunque el servidor siga vivo. Y la UI (`jobs.ts`) trataba CUALQUIER fallo de transporte como "optimización terminada con error" aunque el cálculo estuviera sano.
Fixes mínimos aplicados (Fase D, todos reversibles y marcados):
- `backend/server.py`: `request_queue_size = 64` (margen sin tocar el modelo monohilo que exige Gmsh) + se silencia `ConnectionAbortedError/BrokenPipe` en `wfile.write` (`WRITE-ABORT`, `BACKLOG`).
- `backend/app_desktop.py`: con refused y proceso vivo → `"backend ocupado (proceso vivo...) — reintentando"`; con proceso muerto → mensaje con exit code (completa el `DEAD-SERVER` del addendum 4).
- `src/lib/jobs.ts` (`POLL-RETRY`): fallos de transporte reintentan en silencio hasta 150 (~2.5 min); solo la muerte confirmada (`el proceso backend terminó`) o estado error/failed detienen el sondeo.
- Nuevo `backend/tests/test_bridge_dead_server.py` (3 tests: muerto/ocupado/sin-sonda).
Verificación (Fase E): `npm run lint` OK, `npm run build` OK (`dist/` regenerado: relanza con `INICIAR_APP.bat` para usarlo), tests puente+contrato+polljob **11 passed**.
Uso: relanza la app (proceso fresco). Si el job muere de verdad verás el exit code y el puntero a logs; si solo es el servidor ocupado, el sondeo seguirá solo sin marcar error. Si se repite la muerte tras `reconstruct done`, baja `resolution`/`padding` del envelope o cierra/reabre entre corridas largas.

## Addendum 2026-09-17 (6) — "backend no responde tras ~2.5 min": GIL retenido por OCP, no proceso caído

Síntoma reportado: `La optimización terminó con error: backend no responde tras ~2.5 min de reintentos (¿proceso caído? revisa backend/server_stdout.log)` — con `server_stdout.log` (18:40–18:48) mostrando la corrida COMPLETA y sana: `GEN solve start` 18:42:01 → `GEN solve done` 18:44:08 → `GEN reconstruct done: BREP_SOLID` **18:48:07**, sin traceback, sin `server_error.log`. El job nunca falló: la UI lo declaró muerto mientras seguía calculando.

Causa raíz (medida, no inferida). El job corre en un hilo del MISMO proceso (`api.py:155,335` con `_pool`) y el servidor HTTP es monohilo (`server.py:110`), así que el sondeo depende del GIL del proceso que ejecuta OCP (`OCP` = pybind11 sin `gil_scoped_release`):

| Sonda (temporal, ya eliminada) | Resultado |
|---|---|
| `BRepBuilderAPI_Sewing.Perform()` 4000 caras, en hilo trabajador | el hilo principal queda **1.12 s** sin GIL dentro de 1.87 s |
| `SIMPSolver.optimize()` 8412 dofs / 6 iter, en hilo trabajador | pausa máxima **0.04 s** → el solve (numpy/scipy) NO bloquea |
| `ReconstructionPipeline.run()` real (10 368 tets, bspline) | 64.2 s en los que el hilo principal recibe **87 ticks en vez de ~6423**; pausa máxima **10.4 s**, p95 4.3 s, 16 pausas > 0.5 s |

Es decir: durante la reconstrucción B-Rep el proceso queda congelado para HTTP en tramos de 10 s (con 60 030 tets y 239 s de reconstrucción, tramos proporcionalmente mayores). Con el sondeo cada 1 s y el timeout de 120 s del puente, esos tramos generan fallos de transporte por ráfaga y el contador de 150 fallos "de 2.5 min" se agota aunque el proceso esté vivo y el job avance.

Bug de la UI que convierte el bloqueo en falso error (`src/lib/jobs.ts`, HECHO):
- `transportFails` **nunca se reiniciaba** tras un poll correcto: los hipos se acumulaban durante toda la corrida;
- los ticks se **solapaban** (`setInterval` + `tick` async sin guarda): un tramo bloqueado contaba cientos de fallos por segundo y llenaba la cola TCP del servidor monohilo (origen de los `10061` del addendum 5);
- el presupuesto era un **número de fallos** rotulado como "~2.5 min", que no corresponde a tiempo real.

Fix mínimo aplicado (Fase D, reversible, marcado `POLL-STALL` / `POLL-STALL-UI`):
- `src/lib/jobs.ts`: ticks serializados (1 petición en vuelo como máximo), contador reiniciado en cada respuesta correcta, presupuesto por **tiempo sin respuesta** (`STALL_WARN_MS` 45 s → aviso no terminal; `STALL_FAIL_MS` 60 min → error terminal), y nuevo campo `stalled` en `JobPollData`. La muerte confirmada del proceso (`el proceso backend terminó`) y los estados `error/failed` siguen siendo terminales.
- `src/App.tsx`: aviso honesto mientras `stalled` ("el backend está ocupado… el cálculo continúa. Esperá sin relanzar la optimización"), sin tocar el flujo de resultados.
- Verificación (Fase E): `npm run lint` (tsc) OK; `npm run build` OK (`dist/` regenerado); `test_bridge_dead_server + test_polljob_error_string + test_mock_fallback_contract`: **11 passed**.

Pendiente real (no implementado, decisión de arquitectura): el único arreglo de fondo es sacar el cómputo científico del proceso que atiende HTTP (subproceso propio + IPC), porque ninguna solución in-process sobrevive a una llamada nativa que retiene el GIL — ni `ThreadingHTTPServer`, ni `setswitchinterval`, ni timeouts. Mientras eso no se haga, el coste de reconstrucción (10.4 s de bloqueo por 10 k tets) marca el presupuesto de paciencia de la UI.

## Addendum 2026-09-17 (7) — JOB-STATUS: el sondeo ya no depende del GIL (HECHO)

Cierra el pendiente del addendum 6. En lugar de mover el pipeline numérico a otro proceso (inviable sin un protocolo worker completo: el `GenerativeDesignEngine`/`Api` sostienen formas OCC `TopoDS_Shape` NO serializables), se separa lo único que la UI necesita durante la corrida: **la señal de avance**.

Mecanismo (nuevo `backend/job_status.py`, stdlib puro):
1. El proceso pesado publica el estado MÍNIMO de cada job (`state`, `progress`, `error`) en `job_status_<puerto>.json`, de forma atómica (`tmp` + `os.replace`). Se publica al crear el job, en cada callback de progreso (solve estructural y generativo) y en el estado terminal (`done`/`error`). **El `result` NO viaja ahí** (puede pesar MB).
2. El host de la UI (`app_desktop.py`, OTRO proceso que nunca importa VTK/OCC/Kratos) responde `pollJob`:
   - `running` → contesta con el snapshot **sin tocar la red** (inmune al GIL retenido);
   - terminal (`error/failed`) → también local (el detalle del fallo vive en el snapshot);
   - `done` → **reenvía** al proceso pesado, que en ese momento ya está libre, para traer el `result` completo;
   - sin snapshot (arranque, tests, sesión vieja) → camino normal (`_call`).
3. Señal honesta `stale`/`stale_sec`: si el backend lleva >45 s sin publicar avance (llamada nativa larga), el sondeo sigue siendo `ok` pero marcado como `stale`; `jobs.ts` lo muestra como aviso ("el backend está ocupado… el cálculo continúa") y solo tras 60 min de silencio declara error terminal. Proceso muerto (`is_alive`) → mensaje con exit code, como antes (`DEAD-SERVER`).

Archivos: `backend/job_status.py` (nuevo), `backend/api.py` (`status_port` + `_publish_jobs` en `_submit`/`_done`/`_prog`/`_prog_g`), `backend/server.py` (asigna el puerto, limpia snapshot propio + litter de sesiones muertas), `backend/app_desktop.py` (`Bridge.pollJob` con vía rápida; `pollJob` sale del wrapper genérico), `src/lib/jobs.ts` (consume `stale`/`stale_sec`), `src/App.tsx` (aviso), `.gitignore`.

Verificación (Fase E):
| Prueba | Resultado |
|---|---|
| `npm run lint` (tsc) | OK |
| `npm run build` | OK (`dist/` regenerado) |
| `tests/test_job_status_bridge.py` (nuevo, 10) | **passed** |
| `tests/test_job_status_live_job.py` (nuevo: job generativo REAL sondeado con el `Bridge` contra un puerto muerto) | **passed** |
| Suite backend completa | **108 passed** en 94 s (el intérprete cierra con un crash nativo `0xC0000005` al descargar DLLs: preexistente, también ocurre con `test_undo_api.py` aislado) |
| E2E con `server.py` REAL (envelope 63 750 tets, threshold 0.3, bspline) | **299 sondeos locales, 0 errores de sondeo**, latencia máxima **13.3 ms** mientras el backend acumuló **34.5 s sin publicar avance** (la ventana de reconstrucción que antes tumbaba el HTTP); 212 sondeos marcados `stale`; el terminal se reenvió con el resultado completo (`final_volume_fraction=0.35`) |

Segundo bug real encontrado al verificar (y corregido): la lectura del snapshot no era robusta en Windows. Mientras un hilo publica, `open` puede fallar transitoriamente con `PermissionError` (violación de compartición durante `os.replace`; **medido: 381 fallos en 3 s con 3 publicadores y 3 lectores**), y el lector lo interpretaba como "no hay snapshot" → caía al camino HTTP → con el backend ocupado reaparecía el falso "backend no responde" (así falló la suite: `105 passed, 1 failed`, y después `106 passed, 2 failed`, hasta cerrarlo). Arreglos: temporal **único por escritura** (dos publicadores simultáneos son normales: hilo del solver por progreso + hilo HTTP al crear otro job), **reintentos** de lectura y **cache del último snapshot válido** en el puente (la edad se calcula de la marca `written` del propio snapshot, así que la señal `stale` no se falsea). Regresión: `test_read_snapshot_survives_concurrent_publishers` y `test_transient_read_failure_uses_last_valid_snapshot`.

Nota de alcance: el proceso pesado sigue sin poder atender *otros* endpoints síncronos mientras una llamada nativa retiene el GIL (`registerReconstruction`, `exportStep`, `getSurfaceMesh`). Eso no es una regresión (ya era así) y ocurre después del job, cuando la UI no sondea; si alguna vez molesta, el siguiente paso es el worker con IPC real.

## Addendum 2026-09-18 (8) — "el modelo no es generativo, infla todo": marching-tets roto y presupuesto de material

Síntoma: el sólido generativo sale como un bloque inflado (sin miembros ni canales), no como estructura orgánica.

**Causa raíz medida (HECHO) — el extractor de isosuperficie estaba roto.** Dos defectos independientes en `core/cad_reconstruction.py`:

1. **Orientación mezclada.** `_voxel_tet_mesh` (dominio de diseño del generativo) emite **5 de cada 6 tets con volumen negativo** (medido: `53125/63750` en un envelope de 63 750 tets), y `_tet_iso_triangles` heredaba ese volteo: el caso 1-abajo salía invertido y el segundo triángulo del caso 2-2 también. Medición sobre una esfera sintética (material dentro de la caja, malla `_voxel_tet_mesh`): **4082 normales hacia afuera vs 4094 hacia adentro**, integral de volumen **−1392 mm³ en vez de +167 260** (cancelación ~100%). Es decir: normales visuales invertidas en la mitad de la superficie, volumen sin sentido y cosido/`ShapeFix` de OCC trabajando sobre una cáscara incoherente.
2. **Vértices no soldados.** Cada tetraedro calculaba el corte de una arista compartida en su propio **orden local**, así que los dos floats diferían en los últimos bits y el soldado a 1e-9 no los fusionaba: la isosuperficie quedaba **abierta** (medido: 100 aristas abiertas en la esfera sintética, 400 en el envelope real). Ordenar por índice local no alcanza: la misma arista global aparece con índices locales distintos en cada tet.

Fix (Fase D, mínimo y reversible, marcado `ORIENT-FIX` / `EDGE-CANON`):
- `_tet_iso_triangles(..., gcon)`: los triángulos se orientan con la **dirección material del propio tet** (`dot(normal, centro_alto − centro_bajo)`), criterio geométrico que hace irrelevante el signo del tet — en lugar de análisis de casos.
- `_lerp_edge(..., gcon)`: el par de nodos se ordena por **índice GLOBAL** antes de interpolar, así los dos tets que comparten arista producen bit a bit el mismo punto y el soldado los fusiona.
- `MarchingTetrahedraExtractor.extract` pasa la conectividad global.

Verificación (Fase E):
| Prueba | Antes | Después |
|---|---|---|
| Normales hacia afuera (esfera sintética, t=0.3) | 4082/8176 | **8320/8320** |
| Volumen por divergencia (analítico 167 260 mm³) | −1392 | **169 239 (+1.18 %)** |
| Aristas abiertas (esfera que sobresale de la caja: corte real del dominio) | 100 | 100 (legítimas) |
| `pytest backend/tests` | 108 passed | **110 passed** (2 nuevos) |

Regresión nueva: `backend/tests/test_isosurface_orientation.py` (normales 100 % hacia afuera, malla cerrada cuando el material no toca la frontera, volumen positivo del orden correcto, y puntos de arista compartida idénticos entre tets con conectividad permutada).

**Diagnóstico del "inflado" que NO era del extractor (medido, pendiente de decisión).** Reproducción con el pipeline real (cono + envelope 63 750 tets, volfrac 0.35, 50 iters, threshold 0.3), cadena de volúmenes:

| Etapa | Volumen (% de la caja de diseño) |
|---|---|
| Pedido por el usuario (volfrac) | 35.0 % |
| Campo físico del solver (`physical_volume_fraction`) | **41.9 %** |
| Material del campo por umbral (`rho>0.5`) | 43.9 % |
| Isosuperficie cruda + `fill_holes` | 27.7 % |
| Tras Taubin | 24.7 % |
| Tras decimar (≤6000 tris) | 22.5 % |

1. **P1 — sobrellenado (+20 %):** la proyección Heaviside (`beta` 8, `eta` 0.5 **fijo**) no conserva volumen, así que el campo físico queda 20 % por encima del `volfrac` pedido. Arreglo estándar: actualizar `eta` por bisección cada iteración (volume-preserving projection) para que `Σ x̄·V` = objetivo. No implementado (toca el lazo del optimizador y las regresiones numéricas).
2. **P2 — la extracción pierde ~40 % del material:** 43.9 % del campo → 27.7 % de malla. `_element_densities_to_nodes` promedia **sin pesos** y el resultado se corta por umbral, así que los miembros delgados se diluyen. Arreglo: umbral elegido por conservación de volumen (bisección sobre el volumen encerrado) o promedio ponderado por volumen de tet, y reportar `solid/field` en metadata.
3. **P3 — el material se pega a la caja de diseño:** el guard `ENV-SKIN-BC-GUARD` quita del void-skin todo elemento que toque un nodo de BC; cuando la carga/fijación cae al **fallback** (toda una cara extrema o base-Z), cancela **7500 de 8640** elementos de skin. Medido: la capa de pared queda con **46.7 % de material** (debería ser ~0) y **27.5 % del dominio queda en 13 bolsas de vacío encerrado** (el "blob" no tiene canales abiertos). Con las caras bien mapeadas el efecto se acota, pero el fallback lo dispara. Arreglo propuesto: proyectar la cara CAD a los nodos del envelope (vecinos por KD-tree de los nodos de la cara en la malla del modelo) en vez de "todos los nodos del plano extremo", y/o que el material preservado gane al void del skin.
4. **P4 — la cadena B-Rep histórica (`unify` → `ShapeCustom_BSplineRestriction` → `continuity`) no tiene guarda de volumen:** el `VOL-GUARD` (75 %–133 %) solo existe en el camino de parches B-spline. Si `BSplineRestriction` infla el sólido, nada lo detecta ni lo reporta.

Nota: en el diseño `part` (malla del modelo) el pipeline sigue eligiendo `brep_source="smoothed"` (los tests de roundtrip STEP siguen pasando); en el envelope de la reproducción el fitter terminó aceptando la candidata `raw` (`brep_source="raw"`, `bspline_fit=fallback_mixed`) — comportamiento reportado en metadata, no silencioso.

## Addendum 2026-09-18 (9) — "sigue inflando: tiene que quitar material": proyección conservativa

Continuación del addendum 8, con la instrucción explícita del usuario: la optimización generativa debe **sacar** material, no rellenarlo. Se atacaron las dos causas medidas ahí (`P1` y `P3`).

**P1 — el campo físico ya pesa lo pedido (`VOL-PRESERVE`).** Con `eta` fijo en 0.5 la proyección Heaviside no conserva volumen y el desvío va en **ambos** sentidos según el campo: en el envelope real el usuario pedía 0.35 y obtenía **0.419** (+20%, rellenaba); en una viga pequeña con `beta=8` la misma configuración daba **0.2517** con objetivo 0.40 (−37%, vaciaba de más). Control negativo medido (viga Kuhn 4x1x1, 12 iteraciones, `volfrac=0.4`):

| | `final_volume_fraction` (diseño) | `physical_volume_fraction` | `eta` |
|---|---|---|---|
| Sin el fix (control) | 0.4000 | **0.2517** | 0.5000 (fijo) |
| Con el fix | 0.4000 | **0.4000** | 0.4389 |

Implementación (`core/topopt.py`, marcada `VOL-PRESERVE`, reversible): `_update_heaviside_eta(x, beta)` resuelve `eta` por bisección (50 pasos sobre `(1e-6, 1-1e-6)`, 60 evaluaciones vectorizadas) para que `Σ x̄·V` sobre el subdominio activo iguale el volumen del campo de diseño; se llama al inicio de cada iteración del lazo OC/MMA/GCMMA y otra vez en `_finalize_result` (el `eta` de la última iteración corresponde al `x` anterior). El filtro ya es conservativo, así que diseño → filtrado → proyectado mantienen el mismo volumen. `d(eta)/dx` se desprecia (aproximación estándar). Sin Heaviside es no-op bit a bit (lo cubre `test_heaviside_regression_no_projection`). Se reporta `volume_preserving_projection: true` y el `heaviside_eta` final en el resultado.

Efecto medido en el envelope real (cono, 63 750 tets, `volfrac=0.35`, 50 iters): `physical_volume_fraction` **0.4193 → 0.3748**; volumen de tets con `rho>0.5` **43.9% → 39.3%**; `final_volume_fraction` 0.3500 (el pedido). Regresión nueva: `test_heaviside_projection_conserva_el_volumen_pedido`.

**P3 — fallback de BC acotado (`FALLBACK-BOUND`).** Al medir el mapeo con **caras válidas** se aclaró el alcance real: el cono tiene **3 caras** (0,1,2), así que las sondas previas (con `face_index` 3 y 5, copiado de tests sintéticos) no mapeaban nunca y caían al fallback plano. Con caras reales el mapeo **sí funciona**: carga → 492 nodos (cara 2), fijación → 2444 nodos (cara 0), y el guard de BC sólo cancela **2 293 de 16 140** elementos de skin (14 %), no 7 500 de 8 640 (87 %). Aun así, cuando la cara pedida no existe o no mapea, el fallback histórico aplicaba la condición a **todos los nodos del plano extremo** del dominio; ahora se acota al bbox de las caras pedidas más 2·h de margen (`_fallback_face_mask`, aplicado en los tres fallbacks: `_resolved_load_nodes`, `_resolved_support_nodes`, `_force_vector_for_load`). Detalle de implementación: `model_shape` es una shape de **CadQuery** (no un `TopoDS` crudo) y OCP no expone `Face.Bnd()`; el bbox se saca con `BoundingBox()` y, si llegara una cara OCC cruda, con `BRepBndLib.Add_s(face.wrapped, box)`. Sin caras o sin shape CAD se mantiene el comportamiento histórico (None), así que no hay regresión. Limitación honesta: para caras cuyo bbox abarca toda la pieza (p. ej. la cara lateral de un cono) el acotado no restringe nada — el arreglo de fondo es proyectar la cara a los nodos del envelope por distancia, no por bbox.

**Verificación (Fase E):** `pytest backend/tests` → **111 passed** (nuevas: `test_isosurface_orientation.py` ×2, `test_heaviside_projection_conserva_el_volumen_pedido`); el intérprete sigue cerrando con el crash nativo `0xC0000005` preexistente. Sigue pendiente `P2` (la extracción pierde ~30-40% del material del campo: 39.3% → ~27% de malla) y `P4` (la cadena B-Rep histórica no tiene guarda de volumen).

## Addendum 2026-09-18 (10) — el "sólido" registrado era una CÁSCARA (`num_solids = 0`)

Con la captura de la UI del usuario se reencuadró el problema: **el optimizador sí vacía** (la UI muestra `Masa 0.13 kg (-81%)`; en la reproducción, `volfrac=0.2` → `final_volume_fraction=0.2000`, material rho-ponderado 26.2% de la caja). Lo que falla es la **reconstrucción**, y de dos formas distintas:

1. **El pipeline entrega una superficie etiquetada como sólido (HECHO, grave).** Medición directa con el pipeline real (cono + envelope 63 750 tets, `volfrac=0.2`, umbral 0.3, B-spline, `max_hole_edges='auto'`): `reconstruction.stage = brep_solid / completed`, pero al registrar y reimportar, el **snapshot de la app reporta `num_solids = 0`** con 5 619 caras y 5 624 triángulos (STEP de 15 MB). Causa: `BRepCheck_Analyzer` considera **válida** una cáscara (`TopAbs_SHELL`), y los pasos de la cadena B-Rep (`ShapeUpgrade_UnifySameDomain`, `ShapeCustom_BSplineRestriction`, `ShapeUpgrade_ShapeDivideContinuity` — este último devuelve un COMPOUND por diseño) podían degradar el sólido a cáscara sin que nadie lo verificara: `unify_same_domain = applied` y el resultado guardado ya no era un sólido. La app registraba y mostraba una **superficie**, no un sólido CAD.
   **Fix (`SOLID-GUARD`, reversible):** `_shape_has_solid(shape)` exige `TopAbs_SOLID` (o un COMPOUND con al menos un sólido); los tres pasos de la cadena sólo se aceptan si la forma sigue siendo sólida (`skipped_not_solid` en metadata) y `OCPBSplineFitter.fit` devuelve el sólido facetado original si la cadena lo degradó (`brep_chain_downgraded = kept_faceted_solid`). Regresión: `backend/tests/test_brep_solid_guard.py` (sólido / cáscara suelta / compuesto con sólido / compuesto sólo con cáscaras).
2. **La reconstrucción conserva sólo el 31% del material del campo.** `snapshot.volume_cm3 = 51.9` frente a `165.9 cm³` de material en el campo (rho-ponderado). Es `P2` del addendum 8, ahora cuantificado a nivel app: el sólido registrado no representa lo optimizado (y sobre eso actúa el suavizado B-spline, que redondea lo poco que queda). Pendiente.

Números de la corrida (para trazabilidad): `final=0.2000`, `physical=0.2620` (el campo físico sigue arriba del objetivo cuando se mide sobre la caja completa: el objetivo del `VOL-PRESERVE` es el volumen del campo de diseño sobre el subdominio activo), `eta=0.5506`, `brep_source=raw`, `bspline_fit=fallback_mixed`, `brep_decimated_from=18516 → 5980`, `unify_same_domain=applied`.

## Addendum 2026-09-18 (11) — por qué la app registraba una cáscara: el tapado invertía los parches

Cerrando el addendum 10. Se implementó la extracción que conserva el material (`VOL-MATCH`) y, al verificarla contra los tests de generativa, quedó al descubierto la causa real del `num_solids = 0`:

**`fill_holes` construía el abanico con el bobinado al revés.** Los parches de tapado quedaban con la normal opuesta a la superficie, así que la cáscara cerrada tenía caras invertidas y `BRepGProp.VolumeProperties` daba un volumen ~0 (**medido: 5.52 mm³ frente a 1.57e+05 mm³ de malla**). Consecuencias encadenadas: el guardia de volumen de `_register_reconstruction_model` **rechazaba** el sólido ("volumen del sólido reconstruido degenerado"), el registro caía a una cáscara y el STEP salía sin sólidos. Fix de una línea marcado `CAP-ORIENT` (`[new_idx, v1, v0]`), con el motivo escrito en el código.

**VOL-MATCH (nuevo, activo por defecto).** `resolve_volume_threshold` busca por bisección el umbral de isosuperficie que hace que el volumen encerrado iguale el material que el umbral del usuario define en el campo de elementos, y lo reporta (`marching_threshold_requested/used`, `material_volume_target_mm3`, `material_volume_extracted_mm3`, `material_volume_ratio`, `volume_matching_error`) — en la etapa terminal también, para que la UI pueda decirlo. La medición durante la búsqueda se hace sobre la malla con los **cortes de dominio** tapados (`max_hole_edges=0` + `domain_lo/hi/tol`), porque una malla abierta no tiene volumen encerrado medible (sin esto la bisección divergía: `ratio 0.38`, `error 0.62`). Caso de placa delgada de 1 voxel: sin VOL-MATCH al umbral 0.5 se extraía **26.3%** del material del campo; con VOL-MATCH (**t\*=0.067**) se extrae **97.8%**.

**DOMAIN-CUT.** Un loop abierto cuyos vértices caen todos sobre la frontera del dominio no es un agujero de diseño: es el corte de la isosuperficie contra la caja de diseño. Esos loops se tapan **siempre**, aunque superen `max_hole_edges` (si no, la cáscara queda abierta y no hay sólido); los agujeros interiores siguen sujetos al tope del usuario. Guardia añadido: con un dominio degenerado (nodos de prueba en cero) la regla NO aplica (antes marcaba cualquier agujero como corte).

**SOLID-GUARD** queda como **detección reportada** (`unify_same_domain_not_solid`, `bspline_restriction_not_solid`, `continuity_upgrade_not_solid`, `brep_chain_not_solid`), no como sustitución: sustituir por el sólido facetado crudo resultó peor (ese shape tiene volumen degenerado para OCC y el registro lo rechaza).

**Verificación (Fase E):** `pytest backend/tests` → **119 passed** (nuevas: `test_volume_matching.py` ×3, `test_brep_solid_guard.py` ×4, `test_isosurface_orientation.py` ×2, `test_heaviside_projection_conserva_el_volumen_pedido`, `test_loop_sobre_la_frontera_del_dominio_se_tapa_siempre`). Los tests de app (`test_generativa_flujo::test_registration_exposes_reconstructed_tessellation` y `test_generative_step_roundtrip`) —que registran el sólido, exportan el STEP y lo reimportan con `num_solids >= 1`— pasan de fallar por "volumen degenerado" a pasar con el fix de orientación de abanicos. Queda pendiente de re-medición E2E el caso envelope completo (la corrida de verificación se lanzó antes del `CAP-ORIENT`).

## Addendum 2026-09-18 (12) — "sin geometría registrable": la cáscara quedaba abierta

Captura del usuario tras el addendum 11: la forma ya es una **estructura de miembros finos** (lo que se buscaba) y el campo está en presupuesto (`sobre-umbral 20.6%` con `volfrac 0.25`), pero el registro falla con *"Reconstructed solid is not valid (isosuperficie abierta/degenerada…)"* → no se registra NADA.

Causa: con "Agujeros grandes: Conservar (auto)" los loops que superan el tope se dejan abiertos y, si el material toca el borde del dominio, también quedan cortes; una cáscara abierta no puede convertirse en sólido y el fitter base devuelve FAILED (su guardia de validez es correcta).

Fix (`CIERRE-FORZADO`, reversible): antes del ajuste B-Rep, si el candidato tiene loops abiertos se cierra **una copia** (`fill_holes(..., max_hole_edges=None)`) y se reporta `brep_forced_close_loops`. Justificación física, no conveniencia: un loop abierto **nunca** es un agujero de diseño — los agujeros reales (pernos, keep-out) son **túneles**, o sea superficies cerradas; un loop abierto es un corte contra el dominio o un artefacto del marching-tets. La metadata de la etapa de tapado sigue diciendo fielmente cuántos loops dejó el tope del usuario (no se falsea su ajuste). Regresión: `test_forced_close_when_user_cap_leaves_the_shell_open` (con un fitter que rechaza mallas abiertas, como OCC).

**Verificación:** `pytest backend/tests` → **120 passed**.

**A revisar del lado del usuario (no es reconstrucción):** su corrida reporta `compliance final = 3.03e-10`, es decir el trabajo de deformación es prácticamente nulo: la carga no está generando desplazamiento apreciable (estructura rígida u over-constrained). Con compliance ≈ 0 el optimizador no tiene sensibilidad útil, así que conviene revisar magnitud/dirección de la carga y qué caras quedaron fijas (si la fijación cubre casi toda la pieza, el problema es trivialmente rígido y el resultado deja de ser significativo).
