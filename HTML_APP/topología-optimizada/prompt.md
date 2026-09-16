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
