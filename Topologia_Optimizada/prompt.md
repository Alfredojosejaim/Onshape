# IMPLEMENTACIÓN Y AUDITORÍA — HITO 1: SELECCIÓN REAL DE GEOMETRÍA EN ONSHAPE

## ROL

Actúa como ingeniero de software senior especializado en:

- Python
- FastAPI
- JavaScript
- Onshape API
- Onshape App Extensions
- CAD/B-Rep
- procesamiento STEP
- integración CAD ↔ backend
- testing y validación E2E.

Debes trabajar sobre el repositorio actual y respetar estrictamente:

- `prompt.md` → especificación técnica del proyecto.
- `metodologia.md` → reglamento obligatorio de trabajo.
- `resumen_implementacion.md` → registro oficial del estado real de implementación.

`metodologia.md` es de cumplimiento obligatorio. No puedes ignorar, reinterpretar ni flexibilizar sus reglas.

---

# OBJETIVO DE ESTA ITERACIÓN

Completar de forma REAL y verificable el bloque actualmente pendiente del Hito 1:

ONSHAPE → APP EXTENSION → SELECCIÓN REAL → BACKEND → STEP → VISUALIZACIÓN

El objetivo principal es eliminar la dependencia de IDs introducidos manualmente y conseguir una selección real de entidades desde Onshape.

NO avances hacia FEA, TopOpt ni reconstrucción de STEP mientras este bloque no esté correctamente resuelto.

---

# FASE 0 — AUDITORÍA OBLIGATORIA

Antes de modificar cualquier archivo:

1. Lee completamente `prompt.md`.
2. Lee completamente `metodologia.md`.
3. Lee `resumen_implementacion.md`.
4. Audita el código actual relacionado con:
   - App Extension.
   - comunicación Onshape ↔ iframe.
   - autenticación OAuth.
   - API backend.
   - descarga STEP.
   - procesamiento geométrico.
   - tessellación.
   - visor Three.js.
   - tests.
5. Determina qué requisitos están:
   - COMPLETADOS.
   - PARCIALES.
   - PENDIENTES.
   - BLOQUEADOS.
6. No asumas que una funcionalidad está implementada porque exista una función, endpoint, botón, clase o test.
7. Identifica cualquier implementación artificial, mock, fallback o aproximación que pueda estar siendo presentada como funcionalidad real.

Antes de programar, debes tener claro exactamente qué falta.

---

# FASE 1 — VERIFICAR EL MECANISMO REAL DE ONSHAPE

Investiga primero la documentación oficial y actual de Onshape relacionada con:

- App Extensions.
- Element Tabs / iframe.
- comunicación entre Onshape y la aplicación.
- selección de entidades.
- contexto del documento.
- acceso a entidades seleccionadas.
- APIs o mecanismos oficialmente soportados para obtener selección CAD.

NO asumas que mecanismos existentes en el código son válidos.

En particular, verifica antes de utilizarlos conceptos como:

- `postMessage`
- `applicationInit`
- `requestSelection`
- `SELECTION`
- `onSelectionChanged`

Si alguno de ellos no corresponde al mecanismo oficial aplicable, reemplázalo por la solución correcta.

No inventes APIs ni protocolos.

---

# FASE 2 — IMPLEMENTAR SELECCIÓN REAL

Implementa el mecanismo necesario para permitir que el usuario seleccione desde Onshape la geometría requerida.

Como mínimo debe ser posible obtener de forma real y verificable:

- contexto del documento;
- workspace/version correspondiente;
- element/Part Studio correspondiente;
- entidad geométrica seleccionada;
- identificación necesaria para procesarla posteriormente.

La selección debe producir datos reales provenientes de Onshape.

## PROHIBIDO

El flujo principal NO puede depender de:

- introducir manualmente Document ID;
- introducir manualmente Workspace ID;
- introducir manualmente Element ID;
- introducir manualmente Body ID;
- introducir manualmente Face ID.

Los campos manuales existentes deben eliminarse, reemplazarse o quedar fuera del flujo normal de uso.

No implementes un sistema que simplemente simule una selección.

---

# FASE 3 — INTEGRAR SELECCIÓN CON BACKEND

Conecta la selección real con el backend.

El flujo esperado debe ser conceptualmente:

ONSHAPE
↓
APP EXTENSION
↓
SELECCIÓN REAL
↓
DATOS DE CONTEXTO + ENTIDADES
↓
BACKEND FASTAPI
↓
PROCESAMIENTO

La comunicación debe:

- validar los datos recibidos;
- validar contexto;
- rechazar datos incompletos;
- manejar errores;
- evitar confiar ciegamente en valores enviados por el frontend.

No almacenar ni exponer secretos OAuth en frontend.

---

# FASE 4 — CONECTAR CON EL PIPELINE STEP EXISTENTE

Una vez obtenida una selección real:

1. utilizar los datos reales de Onshape;
2. obtener la geometría mediante la API correspondiente;
3. generar/descargar STEP;
4. validar que el STEP sea válido;
5. procesarlo mediante CadQuery/OCP;
6. generar la tessellación;
7. entregar los datos necesarios al visor.

No reemplaces este flujo por una geometría generada artificialmente.

---

# FASE 5 — VISUALIZACIÓN

Verifica que la geometría obtenida realmente corresponda a la entidad seleccionada.

El visor debe utilizar la geometría obtenida del pipeline real.

No utilizar:

- `BoxGeometry`;
- cubos ficticios;
- modelos hardcodeados;
- geometría de prueba como sustituto del modelo real.

Las geometrías sintéticas pueden utilizarse exclusivamente en tests unitarios cuando sea necesario.

---

# FASE 6 — REVISAR EL MALLADO EXISTENTE

Audita la implementación actual de generación de malla.

Determina claramente si cumple o no con los requisitos establecidos en `prompt.md`.

Si el mallado actual utiliza aproximaciones como:

- bounding boxes;
- grids artificiales;
- tetraedros generados manualmente;
- fallback de geometría;
- mallas ficticias;

NO lo declares como mallado FEM CAD completo.

Si es necesario modificarlo para cumplir correctamente el Hito 1, hazlo.

Si requiere una dependencia especializada, evalúa técnicamente la opción adecuada antes de incorporarla.

No agregues dependencias innecesarias.

---

# FASE 7 — MAPEO CAD → FEM

Audita y, si corresponde dentro de esta iteración, mejora el vínculo:

Onshape entity
↓
B-Rep / STEP face
↓
Mesh surface
↓
Mesh nodes/elements

El sistema debe evitar depender únicamente de índices arbitrarios que puedan cambiar.

El mapeo debe ser reproducible y validable.

---

# FASE 8 — TESTING

Implementa o actualiza tests apropiados.

Diferencia claramente:

### Test unitario
Prueba una función aislada.

### Test de integración
Prueba varios componentes conectados.

### Test E2E
Prueba el flujo real completo.

No presentes un test unitario como prueba E2E.

Los tests con geometría creada artificialmente son válidos para probar componentes geométricos, pero NO demuestran que:

Onshape → selección → STEP → visor

funcione.

Si una prueba real requiere interacción con Onshape y no puede ejecutarse automáticamente, documenta esa limitación y realiza la mayor validación posible sin inventar resultados.

---

# REGLA CRÍTICA DE CUMPLIMIENTO

La existencia de código NO significa que un requisito esté cumplido.

Tampoco constituye cumplimiento:

- una función que nunca se ejecuta;
- un endpoint sin integración real;
- un botón sin funcionalidad real;
- un mock;
- un fallback artificial;
- una prueba que solo verifica el mock;
- una implementación teórica;
- documentación que afirma que algo funciona.

Un requisito solo puede marcarse como COMPLETADO cuando exista evidencia suficiente de que funciona.

---

# PROHIBICIÓN DE FALSOS POSITIVOS

Nunca:

- inventes resultados;
- simules respuestas de Onshape;
- generes geometría artificial para aparentar éxito;
- marques como completado algo que no pudiste verificar;
- ocultes errores;
- conviertas un estado pendiente en exitoso mediante fallback;
- cambies los requisitos para que la implementación parezca cumplirlos.

Si algo no puede comprobarse, debe quedar como:

PENDIENTE o BLOQUEADO.

---

# FASE 9 — DOCUMENTACIÓN OBLIGATORIA

Al finalizar la intervención actualiza:

`resumen_implementacion.md`

Debe registrar como mínimo:

## Fecha / Iteración

Indicar qué iteración se realizó.

## Objetivo

Qué requisito se intentó completar.

## Auditoría inicial

Qué estaba:

- completado;
- parcial;
- pendiente;
- bloqueado.

## Cambios realizados

Enumerar archivos modificados y explicar brevemente cada cambio.

## Pruebas realizadas

Indicar:

- tests unitarios;
- tests de integración;
- pruebas E2E;
- pruebas manuales;
- resultados obtenidos.

## Evidencia

Indicar exactamente qué demuestra que una funcionalidad funciona.

## Problemas encontrados

Registrar errores, limitaciones o incompatibilidades.

## Estado final

Para cada requisito:

- COMPLETADO
- PARCIAL
- PENDIENTE
- BLOQUEADO

## Próximo paso

Indicar cuál es la siguiente acción técnica necesaria.

---

# REGLA SOBRE RESUMEN_IMPLEMENTACION.MD

No escribas en `resumen_implementacion.md` lo que debería funcionar.

Escribe únicamente lo que realmente:

- implementaste;
- ejecutaste;
- verificaste;
- observaste.

Si no pudiste probar algo, dilo explícitamente.

---

# RESTRICCIÓN DE ALCANCE

NO implementar todavía:

- FEA real;
- solver estructural;
- Topología optimizada;
- SIMP completo;
- reconstrucción STEP;
- exportación final de geometría optimizada;
- funcionalidades avanzadas que no sean necesarias para cerrar el Hito 1.

No expandas el alcance innecesariamente.

---

# FASE 10 — AUDITORÍA FINAL

Antes de finalizar:

1. vuelve a leer `prompt.md`;
2. vuelve a revisar `metodologia.md`;
3. compara cada requisito afectado contra el código;
4. verifica los tests;
5. revisa `resumen_implementacion.md`;
6. determina honestamente el estado final.

No declares Hito 1 completo si todavía existe un requisito obligatorio sin verificar.

---

# FORMATO DE RESPUESTA FINAL

Al finalizar, responde únicamente con un resumen estructurado:

## Implementado
- ...

## Verificado
- ...

## Parcial
- ...

## Pendiente
- ...

## Bloqueado
- ...

## Archivos modificados
- ...

## Próximo paso recomendado
- ...

No incluyas explicaciones innecesarias ni afirmaciones que no estén respaldadas por pruebas.