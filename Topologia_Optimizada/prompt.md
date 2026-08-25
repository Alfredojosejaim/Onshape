# MIGRACIÓN ARQUITECTÓNICA — CORE CAD/CAE INDEPENDIENTE

Lee y cumple OBLIGATORIAMENTE `metodologia.md` antes de realizar cualquier acción.

También debes leer y utilizar como contexto:
- `README.md`
- `prompt.md`
- `RESUMEN_IMPLEMENTACION.md`
- `investigación_onshape.md`
- documentación existente relacionada con arquitectura e integración Onshape.

## OBJETIVO

Migrar la arquitectura actual de `Topologia_Optimizada` desde un enfoque centrado en Onshape hacia una arquitectura:

CAD-AGNOSTIC CORE + CAD CONNECTORS.

La aplicación debe poder funcionar de manera independiente de Onshape, utilizando inicialmente archivos STEP como entrada CAD.

Onshape NO se elimina. Debe convertirse progresivamente en un conector/plugin independiente del núcleo.

La nueva arquitectura debe permitir en el futuro incorporar otros CAD sin modificar el núcleo FEM/TopOpt.

## REGLA PRINCIPAL

El CORE nunca debe depender directamente de Onshape.

Ningún módulo perteneciente al núcleo de:

- geometría;
- mallado;
- FEM;
- condiciones de frontera;
- cargas;
- materiales;
- optimización topológica;

puede importar, llamar o depender directamente de:

- OnshapeClient;
- OAuth de Onshape;
- Document ID;
- Workspace ID;
- Element ID;
- API REST de Onshape;
- App Extension de Onshape.

Toda comunicación con Onshape debe quedar encapsulada dentro de su connector.

## OBJETIVO DE ESTA ITERACIÓN

NO implementar todavía:

- solver FEA real;
- SIMP;
- optimización topológica real;
- Gmsh definitivo;
- nuevo sistema avanzado de selección;
- integración completa de otros CAD.

Esta iteración es EXCLUSIVAMENTE de migración arquitectónica.

Debe dejar preparado el proyecto para implementar posteriormente:

STEP → CAD interno → Gmsh → Tet4 → FEA → SIMP.

---

# FASE 1 — AUDITORÍA ANTES DE MODIFICAR

Primero inspecciona TODO el repositorio.

Identifica:

1. dependencias directas de Onshape;
2. dependencias indirectas de Onshape;
3. código reutilizable;
4. código que debe convertirse en adapter/connector;
5. código provisional que posteriormente deberá reemplazarse;
6. tests afectados;
7. documentación que contradice la nueva arquitectura.

NO modifiques código durante esta fase.

Primero genera internamente un mapa de dependencias y úsalo para planificar la migración.

No inventes archivos ni arquitectura que no hayas comprobado.

---

# FASE 2 — NUEVA ARQUITECTURA

Establece una separación clara entre:

## CORE

Responsable exclusivamente de:

- modelo CAD interno;
- geometría;
- malla;
- materiales;
- cargas;
- restricciones;
- estudios;
- resultados;
- interfaces FEM;
- interfaces de optimización.

## CAD ADAPTERS

Responsables de transformar distintos formatos CAD hacia el modelo CAD interno.

Inicialmente:

- STEP.

Posteriormente podrán existir:

- IGES;
- otros formatos.

## CONNECTORS

Responsables de integraciones externas.

Inicialmente:

- Onshape.

El connector de Onshape debe encapsular:

- OAuth;
- REST API;
- descarga de STEP;
- contexto de documento;
- workspace;
- element;
- App Extension.

## APPLICATION

Responsable de:

- API;
- servicios;
- jobs;
- persistencia;
- coordinación entre Core y adapters/connectors.

## FRONTEND

Debe poder existir independientemente de Onshape.

Debe existir un flujo standalone para trabajar con un archivo STEP.

---

# FASE 3 — MODELO CAD INTERNO

Implementa una representación interna mínima y agnóstica del origen CAD.

Debe permitir representar como mínimo:

- modelo;
- sólidos;
- caras;
- aristas;
- vértices;
- unidades;
- identificadores internos;
- referencia al origen;
- metadata.

IMPORTANTE:

No utilices IDs de Onshape como identificadores internos del Core.

El Core debe poder trabajar con un CAD importado desde STEP sin conocer que alguna vez existió Onshape.

Diseña interfaces claras para que:

STEP → CADModel

y posteriormente:

Onshape → CADModel.

Ambos deben producir la misma representación interna.

---

# FASE 4 — STEP COMO PRIMER INPUT STANDALONE

Implementa un adapter de STEP.

El objetivo de esta iteración es poder realizar:

Archivo STEP
↓
STEP Adapter
↓
CADModel interno
↓
servicios de aplicación
↓
frontend/viewport.

NO implementes todavía el mallado FEM definitivo.

Puedes reutilizar la lógica existente de procesamiento STEP cuando sea técnicamente conveniente, pero debes desacoplarla de Onshape.

No dupliques lógica existente innecesariamente.

---

# FASE 5 — FRONTEND STANDALONE

Modifica la aplicación para que pueda iniciar y funcionar sin autenticarse en Onshape.

Debe existir como mínimo el flujo:

INICIAR APLICACIÓN
↓
IMPORTAR ARCHIVO STEP
↓
PROCESAR CAD
↓
MOSTRAR MODELO EN EL VIEWPORT.

El usuario NO debe necesitar:

- OAuth;
- Onshape;
- Document ID;
- Workspace ID;
- Element ID;

para utilizar este flujo.

Reutiliza el viewport Three.js existente cuando sea posible.

No desarrolles todavía el sistema completo de condiciones de frontera.

---

# FASE 6 — ONESHAPE COMO CONNECTOR

No elimines la integración actual.

Refactorízala para que quede encapsulada como connector.

El flujo debe terminar siendo conceptualmente:

Onshape
↓
Onshape Connector
↓
STEP / CADModel
↓
CORE
↓
mismo pipeline standalone.

El Core no debe saber si la geometría llegó desde:

- STEP local;
- Onshape;
- otro CAD futuro.

Conserva OAuth y la App Extension si actualmente funcionan.

No reescribas innecesariamente código funcional.

---

# FASE 7 — SERVICIOS Y API

Refactoriza progresivamente `api_server.py` si es necesario.

Evita mantener toda la lógica en un único archivo.

Separa responsabilidades de:

- API;
- autenticación;
- conectores;
- importación CAD;
- estudios;
- jobs;
- procesamiento geométrico.

NO hagas una reescritura masiva si no es necesaria.

La migración debe ser incremental y verificable.

---

# FASE 8 — PERSISTENCIA

Revisa la persistencia actual.

Separa conceptualmente:

AUTENTICACIÓN / SESIONES DE CONECTORES

de:

ESTUDIOS DE ANÁLISIS.

Un estudio debe poder existir sin OAuth.

Conceptualmente debe poder representar:

Study
├── CADModel
├── Material
├── Loads
├── Constraints
├── Mesh
├── FEA configuration
└── Optimization configuration.

No implementes todavía toda esta estructura si no es necesaria para esta migración.

Deja las interfaces preparadas y evita romper la persistencia existente.

---

# FASE 9 — MALLADOR ACTUAL

Identifica y documenta claramente cualquier pseudo-mallador o malla provisional existente.

NO presentes una malla de prueba como malla FEM definitiva.

NO implementes todavía Gmsh como parte de esta migración salvo que sea estrictamente necesario para desacoplar una dependencia.

La implementación definitiva de:

CAD → Gmsh → Tet4

será una etapa posterior.

---

# FASE 10 — TESTS

Los tests deben demostrar que el Core puede funcionar sin Onshape.

Como mínimo:

1. importar STEP sin OAuth;
2. crear CADModel;
3. procesar geometría;
4. ejecutar el flujo standalone básico;
5. comprobar que el Core no importa módulos de Onshape;
6. comprobar que el connector Onshape sigue siendo accesible;
7. ejecutar los tests existentes y detectar regresiones.

Si algún test existente depende directamente de Onshape, clasifícalo correctamente como test del connector y no como test del Core.

NO elimines tests solamente para conseguir que pasen.

---

# FASE 11 — REGLA DE NO REGRESIÓN

Antes de finalizar:

- ejecuta todos los tests disponibles;
- comprueba imports;
- comprueba arranque del backend;
- comprueba el flujo standalone;
- comprueba que la integración Onshape existente no se rompe injustificadamente.

Si algo deja de funcionar:

1. identifica la causa;
2. corrígela;
3. vuelve a ejecutar los tests.

No ocultes errores.

No desactives tests.

No reduzcas criterios de validación.

---

# FASE 12 — DOCUMENTACIÓN OBLIGATORIA

Actualiza:

## README.md

Debe reflejar la nueva visión:

Aplicación CAD/CAE independiente con arquitectura:

CORE
+
CAD ADAPTERS
+
CAD CONNECTORS.

Onshape debe aparecer como primer connector, no como dependencia del núcleo.

## RESUMEN_IMPLEMENTACION.md

Documenta:

- arquitectura anterior;
- arquitectura nueva;
- archivos modificados;
- archivos creados;
- responsabilidades;
- decisiones tomadas;
- problemas encontrados;
- tests ejecutados;
- resultados;
- funcionalidades pendientes.

## metodologia.md

NO elimines reglas existentes.

Agrega las reglas necesarias para garantizar:

- independencia del Core respecto del CAD;
- separación entre adapters y connectors;
- posibilidad de probar el Core sin Onshape;
- prohibición de introducir dependencias de Onshape en el Core.

## prompt.md

Reemplaza el prompt anterior por este nuevo enfoque arquitectónico.

Recuerda que `prompt.md` es el archivo destinado exclusivamente a almacenar el prompt vigente del proyecto.

No conserves prompts antiguos dentro de ese archivo.

---

# FASE 13 — CRITERIOS DE ACEPTACIÓN

La migración SOLO se considera completada si se cumplen TODOS estos puntos:

[ ] El proyecto puede iniciarse sin Onshape.

[ ] Se puede importar un archivo STEP sin OAuth.

[ ] El STEP puede convertirse al modelo CAD interno.

[ ] El viewport puede mostrar el modelo importado.

[ ] El Core no depende directamente de Onshape.

[ ] Onshape queda encapsulado como connector.

[ ] OAuth queda dentro del connector correspondiente.

[ ] La App Extension queda dentro del connector de Onshape.

[ ] La aplicación standalone no requiere Document ID, Workspace ID ni Element ID.

[ ] Los tests del Core pueden ejecutarse sin conexión a Onshape.

[ ] Los tests existentes de Onshape siguen funcionando o están correctamente clasificados.

[ ] No se presenta ninguna malla provisional como FEA definitivo.

[ ] No se implementa SIMP todavía.

[ ] No se implementa todavía el solver FEA definitivo.

[ ] No se introduce código especulativo para funcionalidades futuras.

[ ] README.md está actualizado.

[ ] metodologia.md está actualizado.

[ ] prompt.md contiene solamente el prompt vigente.

[ ] RESUMEN_IMPLEMENTACION.md documenta todo lo realizado.

---

# REGLAS ESTRICTAS DE EJECUCIÓN

1. No empieces a programar antes de auditar el repositorio.

2. No borres código funcional sin justificarlo.

3. No dupliques funcionalidades existentes.

4. No implementes funcionalidades del Hito 2 que no correspondan a esta migración.

5. No inventes APIs.

6. No conviertas hipótesis de `investigación_onshape.md` en hechos.

7. Si una decisión arquitectónica requiere información que no está demostrada, documenta la incertidumbre.

8. No agregues dependencias innecesarias.

9. No introduzcas dependencias de Onshape dentro del Core.

10. Toda modificación debe poder justificarse técnicamente.

11. Respeta estrictamente `metodologia.md`.

12. Después de modificar cada área importante, ejecuta las pruebas correspondientes.

13. No declares una funcionalidad como completada únicamente porque existe código.

14. Una funcionalidad se considera completada únicamente si está implementada, integrada, probada y documentada.

15. Mantén el proyecto ejecutable durante toda la migración.

---

# INFORME FINAL OBLIGATORIO

Al finalizar debes proporcionar:

## 1. Estado de la migración

- completado;
- parcialmente completado;
- pendiente.

## 2. Arquitectura final

Explica brevemente cómo quedaron:

- Core;
- CAD adapters;
- connectors;
- application;
- frontend.

## 3. Archivos creados

Lista exacta.

## 4. Archivos modificados

Lista exacta.

## 5. Archivos eliminados

Lista exacta y motivo.

## 6. Funcionalidades reutilizadas

Indica qué código existente fue aprovechado.

## 7. Tests ejecutados

Indica:

- comando;
- cantidad;
- aprobados;
- fallidos;
- motivo de cada fallo.

## 8. Problemas encontrados

No ocultes ninguno.

## 9. Trabajo pendiente

Especialmente:

- Gmsh;
- Tet4;
- CAD → FEM mapping;
- FEA;
- validación FEM;
- SIMP;
- connector Onshape avanzado.

## 10. Recomendación para el siguiente paso

NO implementes automáticamente el siguiente paso.

Solamente indica cuál debería ser la siguiente etapa técnica después de esta migración.

IMPORTANTE:

Antes de terminar verifica nuevamente `metodologia.md` y comprueba uno por uno los criterios de aceptación.

No declares la migración completada si algún criterio obligatorio no se cumple.