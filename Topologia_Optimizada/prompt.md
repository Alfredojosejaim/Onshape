PROMPT — FINALIZACIÓN DE LA APLICACIÓN STANDALONE

ROL

Actúa como ingeniero de software senior, arquitecto de sistemas y auditor de código, especializado en Python, aplicaciones CAD/CAE, geometría computacional, FEA y optimización topológica.

Trabaja directamente sobre el repositorio:

"Alfredojosejaim/Onshape"

y específicamente:

"Topologia_Optimizada/"

---

1. OBJETIVO FUNDAMENTAL

Debes continuar y finalizar la implementación de la aplicación para convertirla en una:

APLICACIÓN STANDALONE COMPLETAMENTE INDEPENDIENTE

Esta aplicación es el producto principal del proyecto.

Debe poder ejecutarse, utilizarse y desarrollarse sin depender de:

- Onshape.
- SolidWorks.
- Fusion 360.
- FreeCAD.
- AutoCAD.
- ninguna otra aplicación CAD.
- ningún plugin de otra aplicación.
- ninguna extensión de otra aplicación.
- ninguna cuenta de otra plataforma CAD.
- ninguna API externa de CAD.
- ningún documento alojado en otra plataforma.
- ningún Workspace externo.
- ningún sistema OAuth externo de CAD.

PRINCIPIO FUNDAMENTAL

«La aplicación NO es una extensión de un CAD.

La aplicación NO necesita un CAD anfitrión.

La aplicación NO necesita que otro programa CAD esté instalado.

La aplicación NO necesita que el modelo provenga de otro programa CAD en ejecución.

La aplicación debe funcionar por sí misma.»

El modelo CAD será simplemente un archivo de entrada.

Inicialmente el formato principal será:

STEP

Posteriormente podrán incorporarse otros formatos, pero únicamente cuando exista una necesidad real.

---

2. ARQUITECTURA OBJETIVO

La arquitectura inmediata debe ser:

                 APLICACIÓN STANDALONE
                         │
                         ▼
                ┌─────────────────┐
                │   IMPORTACIÓN   │
                │      STEP       │
                └────────┬────────┘
                         ▼
                ┌─────────────────┐
                │   CAD ADAPTER   │
                └────────┬────────┘
                         ▼
                ┌─────────────────┐
                │   CAD MODEL     │
                │  REPRESENTACIÓN │
                │     INTERNA     │
                └────────┬────────┘
                         ▼
                ┌─────────────────┐
                │      CORE       │
                │                 │
                │ Geometría       │
                │ Mallado         │
                │ Materiales      │
                │ Cargas          │
                │ Restricciones   │
                │ FEA             │
                │ TopOpt          │
                └────────┬────────┘
                         ▼
                ┌─────────────────┐
                │    RESULTADO    │
                └────────┬────────┘
                         ▼
                ┌─────────────────┐
                │    EXPORTACIÓN  │
                └─────────────────┘

Este es el único flujo que debe considerarse prioritario actualmente.

---

3. ONSHAPE NO FORMA PARTE DE ESTA ETAPA

Es fundamental entender esto:

NO debes implementar ahora ninguna integración con Onshape.

No debes crear:

connectors/onshape/

No debes crear:

OnshapeAdapter
OnshapeConnector
OnshapeService

No debes implementar:

- OAuth.
- autenticación de Onshape.
- comunicación REST con Onshape.
- App Extension.
- FeatureScript.
- iframe de Onshape.
- selección dentro del viewport de Onshape.
- sincronización con Onshape.
- importación desde una sesión de Onshape.
- exportación hacia Onshape.
- comunicación con ningún CAD externo.

Estas funcionalidades quedan fuera del alcance actual.

---

4. FUTURA INTEGRACIÓN

La integración con Onshape u otros CAD podrá existir en el futuro.

Pero conceptualmente será:

          FUTURO
             │
             ▼
     Plugin / Connector
             │
             ▼
    ┌──────────────────┐
    │ APLICACIÓN       │
    │ STANDALONE       │
    └──────────────────┘

El plugin futuro simplemente podrá facilitar:

- importar modelos;
- exportar resultados;
- transferir información.

Pero la aplicación debe seguir funcionando exactamente igual sin él.

No implementar esta integración ahora.

---

5. DOCUMENTACIÓN OBLIGATORIA

Antes de modificar código debes leer:

1. "README.md"
2. "prompt.md"
3. "metodologia.md"
4. "plan_implementacion_antigravity.md"
5. "RESUMEN_IMPLEMENTACION.md"

Después inspecciona el árbol completo de:

"Topologia_Optimizada/"

No comiences programando inmediatamente.

---

6. AUDITORÍA INICIAL

Debes revisar el estado REAL del repositorio y comparar:

prompt.md
        +
README.md
        +
metodologia.md
        +
plan_implementacion_antigravity.md
        ↓
CÓDIGO REAL

Clasifica cada punto relevante como:

- "IMPLEMENTADO"
- "PARCIAL"
- "NO IMPLEMENTADO"
- "NO APLICA"

No consideres implementada una funcionalidad simplemente porque exista un archivo o una función.

---

7. PRIMERA ACCIÓN — ELIMINAR LA DEPENDENCIA DE OTRAS APLICACIONES CAD

Realiza una búsqueda completa del proyecto.

Busca:

onshape
Onshape
OAuth
document_id
workspace_id
element_id
OnshapeClient
OAuthTokenStore
api.onshape.com
/api/v2/
FeatureScript
App Extension
iframe

También busca referencias a cualquier otro CAD externo.

---

8. ELIMINAR LA DEPENDENCIA FUNCIONAL DE ONSHAPE

Debes modificar la aplicación para que:

ARRANQUE

no dependa de:

- OAuth.
- Onshape.
- credenciales externas.
- documentos remotos.
- APIs externas.

Si existe código específico de Onshape que actualmente sea necesario para iniciar la aplicación, debes eliminar esa dependencia.

Importante

No significa necesariamente borrar todos los archivos históricos relacionados con Onshape sin analizarlos.

Primero determina si:

1. son necesarios para la aplicación standalone;
2. son código histórico;
3. son código obsoleto.

El objetivo es que ninguno sea necesario para ejecutar la aplicación standalone.

---

9. ELIMINAR O AISLAR CUALQUIER FLUJO DE ONSHAPE

El flujo principal NO debe ser:

Onshape
 ↓
API
 ↓
STEP
 ↓
Aplicación

Debe ser:

Archivo STEP
 ↓
Aplicación

El usuario debe poder seleccionar directamente un archivo desde su PC.

---

10. PASO — IMPORTACIÓN STANDALONE

Debe existir un flujo funcional:

Usuario
 ↓
Selecciona STEP
 ↓
Aplicación
 ↓
STEP Adapter
 ↓
CADModel

El archivo debe estar físicamente disponible para la aplicación.

No debe descargarse desde:

- Onshape;
- una API CAD;
- una nube CAD;
- otro programa.

---

11. CADMODEL

Revisa:

core/models.py

El "CADModel" debe representar internamente el modelo importado.

Debe contener únicamente información necesaria para el funcionamiento del Core.

No debe requerir:

document_id
workspace_id
element_id
Onshape ID
OAuth session

Los identificadores internos deben pertenecer a la aplicación.

---

12. STEP ADAPTER

Revisa:

adapters/cad/step_adapter.py

Debe encargarse de:

STEP
 ↓
Lectura
 ↓
Validación
 ↓
Procesamiento
 ↓
CADModel

Debe estar separado del:

- frontend;
- API;
- FEA;
- TopOpt;
- Onshape.

Si utiliza CadQuery/OpenCASCADE para leer STEP, esa dependencia pertenece al Adapter y no debe filtrarse innecesariamente hacia el Core.

---

13. CORE

Revisa completamente:

core/

El Core debe funcionar con el modelo interno.

No debe importar:

Onshape
OAuth
onshape_client
connectors
API específica de CAD externo

El Core tampoco debe requerir que exista un programa CAD instalado.

Regla estricta

El Core debe poder ejecutarse en una máquina donde:

- Onshape no exista;
- ningún CAD esté instalado;
- no exista conexión a Internet.

---

14. NO SOBREDISEÑAR LA ARQUITECTURA

No crees todavía:

ICADAdapter
CADFactory
PluginManager
ConnectorRegistry
OnshapeConnector
FreeCADConnector
SolidWorksConnector

si no son necesarios para que la aplicación standalone funcione.

Queremos una arquitectura limpia, pero no una arquitectura artificialmente compleja.

Actualmente basta con:

STEP Adapter
      ↓
CADModel
      ↓
Core

Cuando se incorpore otro formato, se evaluará entonces la mejor abstracción.

---

15. SERVICES

Completa la separación de responsabilidades mediante:

services/
├── __init__.py
├── cad_service.py
└── study_service.py

"cad_service.py"

Debe gestionar:

- importación;
- validación;
- información del modelo;
- operaciones relacionadas con CAD importado.

"study_service.py"

Debe gestionar:

- creación de estudios;
- configuración;
- materiales;
- cargas;
- restricciones;
- malla;
- resultados.

Los Services tampoco deben depender de Onshape.

---

16. API

Refactoriza "api_server.py".

La arquitectura debe ser:

Frontend
   ↓
API
   ↓
Services
   ↓
Core

No:

Frontend
   ↓
API monolítica
   ├── Onshape
   ├── OAuth
   ├── CAD
   ├── FEA
   ├── persistencia
   └── todo lo demás

"api_server.py" debe encargarse principalmente de:

- endpoints;
- validación HTTP;
- llamadas a services;
- respuestas.

---

17. FRONTEND STANDALONE

Revisa:

optimization-app.html

y cualquier archivo frontend asociado.

El frontend debe dejar de pensar en Onshape.

Eliminar del flujo principal conceptos como:

Conectar con Onshape
Comprobando conexión con Onshape
Selector de geometría de Onshape
Document ID
Workspace ID
Element ID

La interfaz inicial debe orientarse a:

IMPORTAR MODELO

y posteriormente:

CREAR ESTUDIO
CONFIGURAR
ANALIZAR
OPTIMIZAR
VISUALIZAR
EXPORTAR

---

18. PERSISTENCIA

La aplicación debe poder guardar un estudio standalone.

Un estudio NO debe depender de:

OAuth
Onshape
Document ID
Workspace ID
Element ID

Debe poder existir como una entidad propia de la aplicación.

---

19. MALLADO

Mantén el mallador provisional claramente identificado como provisional.

NO reemplaces todavía el mallador por Gmsh definitivo en esta tarea.

No desarrolles todavía el solver FEA.

No desarrolles todavía SIMP.

El objetivo actual es dejar preparada y funcional la arquitectura standalone para posteriormente implementar:

CAD
 ↓
Gmsh
 ↓
Tet4
 ↓
FEA
 ↓
SIMP

---

20. TESTS

Debes crear o adaptar pruebas que demuestren que la aplicación realmente es independiente.

Como mínimo:

Test 1 — Core independiente

El Core debe importarse sin Onshape.

Test 2 — STEP independiente

Un STEP local puede convertirse en "CADModel".

Test 3 — API standalone

La API puede arrancar sin OAuth.

Test 4 — Sin conexión externa

La importación de un STEP local no debe requerir Internet.

Test 5 — Sin CAD instalado

El flujo debe funcionar sin ejecutar ningún programa CAD externo.

Test 6 — Persistencia

Un estudio puede crearse sin ningún identificador de Onshape.

Test 7 — Límites arquitectónicos

El Core no debe importar módulos de Onshape.

---

21. PRUEBA CRÍTICA DE INDEPENDENCIA

Debes verificar conceptualmente y, cuando sea posible, ejecutar el proyecto en un entorno donde:

NO ONSHAPE
NO AUTENTICACIÓN ONSHAPE
NO CREDENCIALES CAD
NO PROGRAMA CAD EXTERNO
NO API CAD EXTERNA

y comprobar:

Aplicación
 ↓
Importar STEP
 ↓
CADModel
 ↓
Visualización

Si esta prueba no puede ejecutarse realmente, debes marcarla:

"NO VERIFICADA"

No marcarla como PASS.

---

22. BÚSQUEDA FINAL DE DEPENDENCIAS

Después de realizar los cambios vuelve a buscar:

onshape
Onshape
OAuth
document_id
workspace_id
element_id
OnshapeClient
OAuthTokenStore
api.onshape.com
FeatureScript
App Extension

Cada coincidencia debe ser analizada.

Una referencia puede permanecer únicamente si:

- pertenece a documentación histórica;
- pertenece a documentación de futuras integraciones;
- está dentro de tests explícitamente destinados a verificar que esa dependencia NO se utiliza;
- o tiene una justificación técnica documentada.

No debe existir ninguna dependencia funcional de Onshape en el flujo standalone.

---

23. TESTS COMPLETOS

Ejecuta todos los tests existentes.

Después ejecuta los nuevos tests de independencia.

No aceptes afirmaciones como:

«"Los tests deberían pasar."»

Necesitas resultados reales.

Si hay errores:

1. identificar;
2. corregir;
3. ejecutar nuevamente;
4. documentar.

---

24. DOCUMENTACIÓN

Actualiza:

RESUMEN_IMPLEMENTACION.md

Documentando esta etapa.

Para cada acción:

Acción
Estado
Archivos modificados
Archivos creados
Archivos eliminados
Tests
Resultado

También actualiza:

plan_implementacion_antigravity.md

marcando claramente:

COMPLETADO
PARCIAL
PENDIENTE

No falsifiques el estado.

---

25. CRITERIO DE FINALIZACIÓN

Esta etapa únicamente se considera completada cuando:

- [ ] La aplicación puede arrancar sin Onshape.
- [ ] La aplicación puede funcionar sin ningún CAD externo.
- [ ] La aplicación puede importar un STEP local.
- [ ] STEP → CADModel funciona.
- [ ] El Core no depende de Onshape.
- [ ] El Core no depende de OAuth.
- [ ] El Core no requiere ningún programa CAD instalado.
- [ ] El frontend funciona como aplicación standalone.
- [ ] La API funciona sin autenticación CAD.
- [ ] Un estudio puede existir independientemente de Onshape.
- [ ] Las pruebas de independencia existen.
- [ ] Las pruebas se ejecutaron realmente.
- [ ] La documentación fue actualizada.
- [ ] No existen dependencias funcionales de Onshape en el flujo principal.

---

26. DEFINICIÓN EXACTA DE "INDEPENDIENTE"

Para evitar cualquier interpretación incorrecta:

Cuando decimos que la aplicación es completamente independiente, significa:

«Una persona debe poder instalar y ejecutar la aplicación en una computadora que no tenga instalado Onshape, SolidWorks, Fusion 360, FreeCAD ni ningún otro programa CAD, sin iniciar sesión en ninguna plataforma CAD, sin disponer de credenciales CAD y sin mantener una conexión con ningún servicio CAD externo, y aun así poder importar un archivo STEP local y utilizar la aplicación.»

Ese es el criterio real de independencia.

---

27. NO IMPLEMENTAR TODAVÍA INTEGRACIONES

No debes implementar ahora:

Onshape plugin
Onshape connector
FreeCAD plugin
SolidWorks plugin
Fusion plugin
CAD synchronization
CAD cloud API

La aplicación debe demostrar primero que puede vivir por sí misma.

---

28. NO AVANZAR A HITO 2 DURANTE ESTA TAREA

No comiences todavía con:

- Gmsh definitivo;
- Tet4;
- ensamblaje de K;
- solver FEA;
- cálculo de tensiones;
- SIMP;
- sensibilidades;
- optimización.

Primero debe existir una base standalone sólida.

---

29. REGLA CONTRA PLACEHOLDERS

No declares implementada una funcionalidad mediante:

- valores hardcodeados;
- datos ficticios;
- mocks fuera de tests;
- simulaciones;
- funciones vacías;
- resultados inventados.

Un mock únicamente es válido dentro de una prueba y debe estar claramente identificado.

---

30. REGLA DE TRAZABILIDAD

Cada cambio realizado debe responder a una necesidad concreta de esta migración.

No realices refactorizaciones innecesarias.

No agregues dependencias innecesarias.

No implementes funcionalidades futuras.

---

31. SI ENCUENTRAS PROBLEMAS

Si durante la migración encuentras problemas relacionados con:

- Gmsh;
- FEA;
- SIMP;
- optimización;
- calidad de malla;

documenta el problema y déjalo pendiente.

NO desvíes el alcance de esta tarea.

---

32. INFORME FINAL OBLIGATORIO

Al terminar debes informar:

A. Estado general

Uno de:

COMPLETA
PARCIAL
BLOQUEADA

B. Cambios realizados

Lista exacta.

C. Archivos creados

Lista.

D. Archivos modificados

Lista.

E. Archivos eliminados

Lista y motivo.

F. Tests ejecutados

Indicar:

comando
resultado
cantidad
fallos

G. Prueba de independencia

Indicar claramente si se verificó:

Sin Onshape: PASS/FAIL/NO VERIFICADO
Sin CAD externo: PASS/FAIL/NO VERIFICADO
Sin OAuth: PASS/FAIL/NO VERIFICADO
STEP local: PASS/FAIL/NO VERIFICADO

H. Dependencias externas de CAD

Lista exacta.

El objetivo es:

NINGUNA dependencia funcional

I. Pendientes

Lista exacta.

J. Siguiente etapa

Indicar qué debe hacerse después.

---

REGLA FINAL

No quiero que diseñes una arquitectura futura de plugins.

No quiero que implementes integración con Onshape.

No quiero que desarrolles todavía FEA ni SIMP.

Quiero que conviertas lo que ya existe en una aplicación standalone real, limpia y verificable.

La prioridad absoluta es:

APLICACIÓN INDEPENDIENTE
        ↓
IMPORTAR STEP
        ↓
CADModel
        ↓
CORE
        ↓
ESTUDIO

La aplicación debe poder existir completamente por sí misma.

Onshape y cualquier otro CAD son externos al producto y no son necesarios para que el producto funcione.

Si la ejecución se interrumpe por límite de tokens, tiempo o cualquier otra causa:

1. detente;
2. documenta exactamente lo realizado;
3. marca lo restante como "PENDIENTE";
4. no declares la etapa completa.

Nunca declares una tarea terminada sin evidencia real de implementación, integración, pruebas y verificación.