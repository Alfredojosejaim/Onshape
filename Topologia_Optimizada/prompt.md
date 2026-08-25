PROMPT — FINALIZACIÓN ESTRICTA DE LA MIGRACIÓN CAD-AGNOSTIC

ROL

Actúa como ingeniero de software senior, arquitecto de sistemas y auditor de código, especializado en Python, aplicaciones CAD/CAE y refactorizaciones arquitectónicas.

Estás trabajando directamente sobre este repositorio:

"Alfredojosejaim/Onshape"

y específicamente sobre:

"Topologia_Optimizada/"

---

1. OBJETIVO ÚNICO DE ESTA EJECUCIÓN

Debes FINALIZAR LA MIGRACIÓN ARQUITECTÓNICA CAD-AGNOSTIC que quedó incompleta.

La aplicación debe dejar de estar estructuralmente centrada en Onshape y pasar a ser una aplicación standalone, capaz de funcionar independientemente de Onshape.

OBJETIVO ARQUITECTÓNICO FINAL

                    ┌─────────────────┐
                    │   CAD INPUT     │
                    │ STEP inicialmente│
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  CAD ADAPTER    │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │      CORE       │
                    │                 │
                    │ Geometry        │
                    │ Mesh            │
                    │ Materials       │
                    │ Boundary        │
                    │ Study           │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  APPLICATION    │
                    │    SERVICES     │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │   STANDALONE    │
                    │   APPLICATION   │
                    └─────────────────┘

         FUTURO — NO IMPLEMENTAR AHORA
                             │
                 ┌───────────┴───────────┐
                 ↓                       ↓
             Onshape                  Otros CAD
            Connector                Connectors

---

2. DOCUMENTACIÓN OBLIGATORIA ANTES DE MODIFICAR CÓDIGO

Antes de tocar cualquier archivo debes leer obligatoriamente:

1. "README.md"
2. "prompt.md"
3. "metodologia.md"
4. "plan_implementacion_antigravity.md"
5. "RESUMEN_IMPLEMENTACION.md"

Después debes inspeccionar el árbol completo de:

"Topologia_Optimizada/"

No empieces a programar inmediatamente.

Primero realiza una auditoría del estado actual.

---

3. AUDITORÍA INICIAL OBLIGATORIA

Debes construir internamente una tabla de control con TODOS los puntos del "plan_implementacion_antigravity.md".

Cada punto debe clasificarse exclusivamente como:

- "IMPLEMENTADO"
- "PARCIAL"
- "NO IMPLEMENTADO"
- "NO APLICA"

No asumas que algo está implementado porque exista un archivo.

Debes comprobar el código real.

Regla

«La existencia de un archivo NO demuestra que una funcionalidad esté implementada.»

---

4. REGLA DE ALCANCE

Durante esta ejecución NO debes implementar:

- Gmsh definitivo.
- Solver FEA definitivo.
- SIMP.
- Optimización topológica.
- nuevas funcionalidades matemáticas.
- nuevas integraciones CAD.
- plugin de Onshape.
- extensión de Onshape.
- OAuth nuevo.
- funcionalidades avanzadas de visualización.

El único objetivo es terminar la migración arquitectónica.

Si encuentras código relacionado con estas áreas, no lo elimines si todavía es necesario para preservar el funcionamiento existente. Solo modifica lo estrictamente necesario para completar la arquitectura.

---

5. PASO 1 — ELIMINAR LA DEPENDENCIA ESTRUCTURAL DE ONSHAPE

Debes revisar TODO el repositorio buscando:

- "onshape"
- "Onshape"
- "OAuth"
- "document_id"
- "workspace_id"
- "element_id"
- "OnshapeClient"
- "OAuthTokenStore"
- URLs de API de Onshape
- imports de módulos Onshape
- sesiones OAuth
- endpoints específicos de Onshape
- lógica de autenticación específica de Onshape

IMPORTANTE

NO debes simplemente borrar todos los archivos relacionados con Onshape.

Debes distinguir entre:

Código que pertenece al Core

Debe eliminarse cualquier dependencia de Onshape.

Código que pertenece a una futura integración

Debe aislarse en:

connectors/onshape/

Código obsoleto

Debe eliminarse únicamente si ya no tiene ninguna utilidad.

---

6. PASO 2 — CREAR EL LÍMITE DEL CONNECTOR ONSHAPE

Implementa:

connectors/
└── onshape/
    ├── __init__.py
    ├── client.py
    └── service.py

El connector debe contener exclusivamente lógica específica de Onshape.

Debe incluir, cuando corresponda:

- autenticación;
- OAuth;
- llamadas REST;
- descarga de geometría;
- operaciones específicas de Onshape.

REGLA CRÍTICA

El Core NO puede importar nada desde:

connectors.onshape

La dependencia permitida es únicamente:

Connector → Application/Core

Nunca:

Core → Connector

---

7. PASO 3 — ELIMINAR O AISLAR "onshape_client.py"

Si existe:

onshape_client.py

en la raíz de "Topologia_Optimizada/", debes determinar si contiene lógica exclusiva de Onshape.

Si es así:

1. migrarla al connector;
2. actualizar los imports;
3. ejecutar los tests;
4. eliminar el archivo raíz cuando ya no sea necesario.

No dejes dos implementaciones simultáneas.

Debe existir una única fuente de verdad para la integración Onshape.

---

8. PASO 4 — DESACOPLAR COMPLETAMENTE EL CORE

Revisa TODOS los archivos dentro de:

core/

El Core debe poder importarse y ejecutarse sin:

- Onshape;
- OAuth;
- requests específicos de Onshape;
- IDs de documentos Onshape;
- sesiones;
- endpoints REST de Onshape.

REGLA

No debe existir ningún import directa o indirectamente equivalente a:

from onshape_client import ...
from connectors.onshape import ...

dentro del Core.

---

9. PASO 5 — ELIMINAR DEPENDENCIAS CAD CONCRETAS INNECESARIAS DEL CORE

Inspecciona especialmente:

core/meshing.py
core/geometry.py
core/models.py

El Core debe trabajar con las abstracciones internas del proyecto.

No debe depender innecesariamente de objetos concretos de:

- CadQuery;
- OpenCASCADE;
- Onshape;
- cualquier CAD específico.

Si CadQuery/OpenCASCADE es necesario para el procesamiento del STEP, esa dependencia debe pertenecer al Adapter correspondiente.

La arquitectura correcta debe ser:

STEP
 ↓
StepAdapter
 ↓
CADModel
 ↓
Core

No:

STEP
 ↓
StepAdapter
 ↓
CadQuery Shape
 ↓
Core

---

10. PASO 6 — VERIFICAR "CADModel"

Revisa:

core/models.py

El "CADModel" debe representar una geometría independientemente de su origen.

Debe poder representar modelos provenientes de:

- STEP;
- futuros formatos;
- futuros connectors.

Los identificadores internos no deben depender de Onshape.

Si existe metadata de origen, debe ser opcional.

---

11. PASO 7 — VERIFICAR EL STEP ADAPTER

Revisa:

adapters/cad/step_adapter.py

Debe ser responsable exclusivamente de:

STEP
 ↓
lectura
 ↓
validación
 ↓
conversión
 ↓
CADModel

No debe contener:

- OAuth;
- llamadas a Onshape;
- lógica de UI;
- lógica de FEA;
- lógica de optimización.

Debe permanecer independiente del backend y del frontend.

---

12. PASO 8 — CREAR LA CAPA DE SERVICES

Implementa:

services/
├── __init__.py
├── cad_service.py
└── study_service.py

"cad_service.py"

Debe centralizar operaciones relacionadas con:

- importar CAD;
- validar CAD;
- obtener información del modelo;
- administrar modelos cargados.

"study_service.py"

Debe centralizar operaciones relacionadas con:

- creación de estudios;
- configuración del estudio;
- material;
- cargas;
- restricciones;
- malla;
- resultados.

No debe contener lógica específica de Onshape.

---

13. PASO 9 — REFACTORIZAR "api_server.py"

"api_server.py" no debe seguir siendo el lugar donde se concentra toda la lógica del sistema.

Debe convertirse principalmente en:

HTTP
 ↓
Router / Endpoint
 ↓
Service
 ↓
Core

No debe contener directamente toda la lógica de:

- CAD;
- estudios;
- persistencia;
- OAuth;
- Onshape;
- procesamiento geométrico.

Extrae responsabilidades a las capas correspondientes.

---

14. PASO 10 — DESACOPLAR LA PERSISTENCIA

Revisa la base de datos y los modelos persistentes.

La aplicación debe poder almacenar un estudio sin requerir:

- document_id;
- workspace_id;
- element_id;
- OAuth;
- sesión Onshape.

Un estudio standalone debe poder existir por sí mismo.

Si existen campos Onshape, deben convertirse en metadata opcional de un futuro connector o eliminarse cuando corresponda.

---

15. PASO 11 — CREAR FLUJO STANDALONE

Debe existir un flujo real:

Usuario
 ↓
Selecciona archivo STEP
 ↓
Backend
 ↓
CAD Service
 ↓
STEP Adapter
 ↓
CADModel
 ↓
Respuesta
 ↓
Frontend
 ↓
Visualización

Este flujo NO debe requerir:

- login Onshape;
- OAuth;
- document ID;
- workspace ID;
- element ID.

---

16. PASO 12 — REVISAR EL FRONTEND

Revisa:

optimization-app.html

y todos los archivos frontend relacionados.

El frontend standalone no debe iniciar preguntando:

"Comprobando conexión con Onshape"

ni depender de:

Selector de Geometría de Onshape

La experiencia principal debe ser:

Importar CAD

o equivalente.

La aplicación debe poder iniciar sin conexión externa.

---

17. PASO 13 — MANTENER ONSHAPE COMO FUTURO CONNECTOR

NO elimines toda posibilidad futura de Onshape.

Debe quedar preparado conceptualmente:

connectors/onshape/

pero la aplicación standalone NO debe depender de él.

La aplicación debe funcionar perfectamente si:

connectors/onshape/

no está disponible.

---

18. PASO 14 — TESTS DE LÍMITES ARQUITECTÓNICOS

Implementa tests específicos:

tests/
├── test_core_cad.py
├── test_step_adapter.py
├── test_standalone_api.py
└── test_architecture_boundaries.py

Como mínimo debes comprobar:

Test A

El Core importa correctamente sin Onshape.

Test B

El StepAdapter genera un "CADModel".

Test C

La API puede iniciar sin credenciales OAuth.

Test D

La importación STEP funciona sin conexión a Onshape.

Test E

El Core no importa módulos de:

connectors.onshape

Test F

Un estudio standalone puede existir sin:

document_id
workspace_id
element_id

---

19. PASO 15 — BÚSQUEDA AUTOMÁTICA DE DEPENDENCIAS PROHIBIDAS

Después de la refactorización realiza una búsqueda global.

Debes buscar al menos:

onshape
OAuth
document_id
workspace_id
element_id
OnshapeClient
OAuthTokenStore
/api/v2/
api.onshape.com

Clasifica cada coincidencia.

Ninguna coincidencia dentro de "core/" debe quedar sin justificación.

Ninguna dependencia de Onshape debe ser necesaria para arrancar la aplicación standalone.

---

20. PASO 16 — EJECUTAR TESTS

Ejecuta:

pytest

y todos los tests específicos creados durante esta migración.

No aceptes:

"debería funcionar"

como evidencia.

Debe existir ejecución real.

Si existen fallos:

1. identificar;
2. corregir;
3. volver a ejecutar;
4. documentar.

---

21. PASO 17 — VERIFICACIÓN MANUAL DEL FLUJO STANDALONE

Debes comprobar realmente:

arrancar aplicación
        ↓
sin OAuth
        ↓
sin Onshape
        ↓
abrir aplicación
        ↓
seleccionar STEP
        ↓
importar
        ↓
crear CADModel
        ↓
mostrar modelo

Si no puedes ejecutar una prueba manual completa por limitaciones del entorno, debes declararlo explícitamente.

No lo marques como PASS.

---

22. PASO 18 — NO TOCAR TODAVÍA EL MOTOR FEM

El mallador provisional existente debe permanecer claramente identificado como provisional.

NO reemplazarlo todavía por Gmsh durante esta tarea.

NO implementar todavía:

- Tet4 definitivo;
- ensamblaje K;
- solver FEA;
- SIMP.

Eso será la siguiente etapa.

---

23. PASO 19 — ACTUALIZAR "RESUMEN_IMPLEMENTACION.md"

Documenta la ejecución realizada.

Debes agregar una nueva sección indicando:

Migración CAD-Agnostic

Para cada acción:

Acción
Estado
Archivos modificados
Archivos creados
Archivos eliminados
Tests ejecutados
Resultado

Diferencia obligatoriamente:

- Implementado.
- Parcial.
- Pendiente.
- No verificable.

No declares la migración completa si existe cualquier criterio pendiente.

---

24. PASO 20 — ACTUALIZAR "plan_implementacion_antigravity.md"

No borres el historial anterior.

Actualiza el plan indicando qué puntos fueron:

[COMPLETADO]
[PARCIAL]
[PENDIENTE]

y deja claramente identificado el siguiente trabajo.

---

25. PASO 21 — AUDITORÍA FINAL

Antes de finalizar debes comprobar:

Arquitectura

Core
 ├── independiente de Onshape
 ├── independiente de OAuth
 └── independiente de conectores

Standalone

STEP
 ↓
Adapter
 ↓
CADModel
 ↓
Service
 ↓
API
 ↓
Frontend

Onshape

Onshape
 ↓
Connector
 ↓
Application/Core

Nunca:

Core
 ↓
Onshape

---

26. CRITERIO DE FINALIZACIÓN

NO puedes declarar la tarea completada hasta que TODOS estos puntos sean verdaderos:

- [ ] Core independiente de Onshape.
- [ ] Core independiente de OAuth.
- [ ] StepAdapter operativo.
- [ ] CADModel independiente del origen.
- [ ] Onshape aislado como connector.
- [ ] "services/" implementado.
- [ ] "api_server.py" desacoplado.
- [ ] Persistencia standalone.
- [ ] Frontend standalone.
- [ ] Aplicación arranca sin Onshape.
- [ ] Importación STEP no requiere Onshape.
- [ ] Tests arquitectónicos implementados.
- [ ] Tests ejecutados.
- [ ] Búsqueda global de dependencias realizada.
- [ ] Documentación actualizada.
- [ ] Auditoría final realizada.

Si alguno está incompleto:

«NO declares la migración terminada.»

---

27. REGLA CONTRA EL USO DE PLACEHOLDERS

No puedes utilizar:

- mocks;
- datos ficticios;
- resultados simulados;
- funciones vacías;
- "pass";
- respuestas hardcodeadas;

para aparentar que una etapa arquitectónica está implementada.

Los mocks solamente son aceptables dentro de tests cuando estén claramente identificados como mocks.

---

28. REGLA CONTRA LA EXPANSIÓN DEL ALCANCE

Si durante la ejecución descubres problemas relacionados con FEA, SIMP, Gmsh u optimización:

1. documenta el problema;
2. no lo resuelvas ahora;
3. continúa con la migración arquitectónica.

La prioridad actual es:

«Arquitectura standalone estable.»

---

29. REGLA DE TRAZABILIDAD

Cada modificación debe poder relacionarse con un objetivo concreto del presente prompt.

No realices refactorizaciones "por si acaso".

Antes de modificar un archivo pregúntate:

«¿Esta modificación es necesaria para completar la migración CAD-Agnostic?»

Si la respuesta es no:

«NO modificar.»

---

30. INFORME FINAL OBLIGATORIO

Al terminar debes responder con:

A. Resumen ejecutivo

Qué se consiguió.

B. Cambios realizados

Lista exacta de modificaciones.

C. Archivos creados

Lista.

D. Archivos modificados

Lista.

E. Archivos eliminados

Lista y motivo.

F. Tests

Comando ejecutado + resultado real.

G. Dependencias Onshape restantes

Lista exacta.

Si no quedan dentro del Core:

NINGUNA

H. Estado de la migración

Uno de:

COMPLETA
PARCIAL
BLOQUEADA

I. Pendientes

Lista exacta.

J. Siguiente etapa

Indicar exclusivamente qué debe hacerse después de esta migración.

---

REGLA FINAL Y MÁS IMPORTANTE

No quiero una explicación teórica de cómo debería quedar la arquitectura.

Quiero que modifiques el repositorio real.

Debes trabajar de forma secuencial, verificando cada etapa antes de pasar a la siguiente.

No marques una tarea como completada porque hayas escrito el código.

Una tarea solo está completada cuando:

IMPLEMENTACIÓN
+
INTEGRACIÓN
+
TEST
+
VERIFICACIÓN
+
DOCUMENTACIÓN

están presentes.

Si los tokens o el tiempo se agotan antes de terminar:

1. detente;
2. documenta exactamente hasta dónde llegaste;
3. marca los puntos restantes como "PENDIENTE";
4. NO declares la migración completada.

No continúes con Gmsh, FEA ni SIMP.

Primero termina y verifica completamente esta migración arquitectónica.