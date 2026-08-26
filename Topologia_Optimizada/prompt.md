

# PROMPT — LIMPIEZA FINAL DE RESIDUOS DE ONSHAPE

## 1. OBJETIVO

Realizar exclusivamente la limpieza final del repositorio después de la migración a la arquitectura standalone.

La arquitectura objetivo YA ESTÁ DEFINIDA y NO debe modificarse.

El objetivo de esta tarea es eliminar completamente del código ejecutable cualquier dependencia, compatibilidad o residuo funcional de Onshape que ya no sea necesario.

La aplicación debe quedar como:

```text
ARCHIVO CAD LOCAL
       ↓
STEP Adapter
       ↓
CADModel
       ↓
Core
       ↓
Servicios de la aplicación

La aplicación standalone debe continuar funcionando exactamente después de la limpieza.


---

2. REGLA PRINCIPAL

A partir de esta tarea:

> ONshape NO forma parte de la aplicación principal.



No conservar código de Onshape por:

compatibilidad;

versiones anteriores;

posibles usos futuros;

"por si acaso";

facilidad de migración futura.


Las futuras integraciones con Onshape serán desarrolladas posteriormente como módulos independientes.

NO desarrollar ningún plugin, extensión o integración CAD durante esta tarea.


---

3. DOCUMENTACIÓN OBLIGATORIA

Antes de modificar código lee:

1. README.md


2. metodologia.md


3. prompt.md


4. RESUMEN_IMPLEMENTACION.md



No utilices:

plan_implementacion_antigravity.md

Si aparece nuevamente, debe considerarse un archivo obsoleto y eliminarse.

No crees ningún nuevo archivo de planificación.


---

4. AUDITORÍA ANTES DE MODIFICAR

Primero realiza una búsqueda global en TODO el repositorio.

Busca al menos:

onshape
Onshape
ONSHAPE
oauth
OAuth
featurescript
FeatureScript
app-extension
App Extension
iframe
client_id
client_secret
document_id
workspace_id
element_id
did
wid
eid
onshape_session

También busca:

connectors.onshape
onshape_client
oauth2
oauth/callback
oauth/token
cad.onshape.com
oauth.onshape.com

NO elimines todavía.

Clasifica cada coincidencia como:

A — Código funcional obsoleto
B — Compatibilidad obsoleta
C — Test obsoleto
D — Configuración obsoleta
E — Documentación histórica
F — Referencia válida no funcional
G — Falso positivo

Documenta esta clasificación antes de comenzar las eliminaciones.


---

5. ELIMINAR EL CONECTOR ONSHAPE

Audita:

connectors/onshape/

Si este directorio únicamente contiene la antigua integración con Onshape:

> ELIMINARLO COMPLETAMENTE.



Esto incluye:

cliente;

servicio;

helpers;

OAuth;

modelos;

tests específicos;

imports asociados.


No reemplazarlo por otro conector.

No crear un "placeholder".

La ausencia del conector es el comportamiento esperado.


---

6. ELIMINAR onshape_client.py

Audita:

onshape_client.py

Si únicamente funciona como shim o compatibilidad hacia el antiguo conector:

> ELIMINARLO.



Antes de eliminarlo:

1. buscar todos sus imports;


2. determinar qué módulos lo utilizan;


3. eliminar esas dependencias;


4. ejecutar tests.



No modificar la arquitectura standalone para conservar este archivo.


---

7. ELIMINAR ONSHAPE DE geometry_processor.py

Audita cuidadosamente:

geometry_processor.py

Elimina cualquier parámetro heredado como:

onshape_session
did
wid
eid

si ya no forma parte de la arquitectura standalone.

Elimina también métodos cuya única finalidad sea:

listar partes desde Onshape;

descargar modelos desde Onshape;

obtener propiedades desde Onshape;

comunicarse con Onshape.


Por ejemplo, revisa específicamente métodos como:

get_parts_list()
download_part_studio()
get_part_properties()

No reemplaces estos métodos por llamadas falsas.

Si ya no tienen utilidad dentro de la arquitectura actual:

> eliminarlos.



Si alguna parte del GeometryProcessor sigue siendo necesaria para STEP/CADModel:

> conservar únicamente esa funcionalidad.



El resultado debe ser un componente limpio y coherente con la arquitectura standalone.


---

8. ELIMINAR OAUTH

Audita todo el repositorio buscando:

oauth
OAuth
client_id
client_secret
access_token
refresh_token
authorization
oauth/callback
oauth/token

Elimina cualquier código OAuth cuya finalidad sea la integración con Onshape.

Esto incluye:

funciones;

rutas;

servicios;

clientes;

tests;

configuración;

variables de entorno.


NO sustituyas OAuth por otro sistema de autenticación.

La aplicación standalone no necesita autenticación externa para cargar modelos locales.


---

9. CONFIGURACIÓN

Audita:

.env.example
pyproject.toml
requirements.txt
configuración
scripts

No debe existir ninguna configuración obligatoria relacionada con:

ONSHAPE_*
OAUTH_*
ONSHAPE_CLIENT_ID
ONSHAPE_CLIENT_SECRET

Si una variable solamente existía para Onshape:

> eliminarla.



No eliminar variables que tengan una función standalone válida.


---

10. API

Audita api_server.py y todos los routers/servicios.

No deben existir endpoints cuya función sea:

login de Onshape;

OAuth;

callback OAuth;

listar documentos de Onshape;

listar partes de Onshape;

descargar modelos desde Onshape;

consultar propiedades de Onshape.


El API standalone debe conservar únicamente funcionalidad propia de la aplicación.

Debe seguir funcionando el flujo:

STEP local
   ↓
upload
   ↓
StepAdapter
   ↓
CADModel
   ↓
procesamiento

NO reemplazar endpoints eliminados por endpoints simulados.


---

11. FRONTEND

Audita todo el frontend.

Elimina cualquier UI que exista únicamente para:

conectar Onshape;

iniciar sesión;

mostrar estado de conexión Onshape;

OAuth;

seleccionar documentos de Onshape;

seleccionar Workspaces;

seleccionar Elements;

utilizar un iframe de Onshape.


NO implementar una nueva integración.

El frontend debe continuar orientado a:

Importar modelo CAD local
        ↓
Procesar modelo
        ↓
Mostrar información/resultados

No desarrollar nuevas funciones de FEA ni TopOpt.


---

12. TESTS

Audita todos los tests.

Elimina tests cuyo único propósito sea probar:

OAuth;

Onshape;

connectors.onshape;

onshape_client;

App Extension;

API REST de Onshape;

autenticación externa.


No conservar tests obsoletos solamente para mantener el número de tests.

Conserva y fortalece los tests de:

STEP
CADModel
Core
API standalone
independencia


---

13. NO UTILIZAR MOCKS PARA OCULTAR ELIMINACIONES

No hagas esto:

mock_onshape_client

para mantener funcionando código que debería eliminarse.

Tampoco:

mocks de OAuth;

clientes falsos de Onshape;

fallback silencioso;

imports opcionales utilizados para ocultar errores.


Si una funcionalidad ya no pertenece al producto:

> eliminarla.




---

14. DEPENDENCIAS PYTHON

Audita los imports después de eliminar Onshape.

Busca dependencias que hayan quedado sin uso.

No elimines una dependencia únicamente por intuición.

Para cada dependencia candidata:

1. buscar todos sus usos;


2. confirmar que no tiene utilidad;


3. eliminarla si realmente está obsoleta;


4. ejecutar tests.



No agregues dependencias nuevas salvo que sean estrictamente necesarias para reparar la aplicación después de la limpieza.


---

15. DOCUMENTACIÓN

Después de eliminar el código, vuelve a buscar referencias a Onshape.

Las referencias restantes pueden existir únicamente si son:

documentación histórica explícitamente identificada;

explicación de decisiones arquitectónicas anteriores;

referencias futuras claramente marcadas como futuras.


No debe existir documentación que indique que Onshape es una dependencia actual.

Si existe documentación histórica que pueda confundir a una IA:

> eliminarla o marcarla claramente como HISTÓRICA / OBSOLETA.




---

16. NO MODIFICAR LA ARQUITECTURA STANDALONE

No hagas cambios innecesarios en:

core/
adapters/
CADModel
StepAdapter
API standalone

La arquitectura actual ya fue migrada.

Solo modifica esos componentes si una dependencia heredada de Onshape todavía existe realmente.

No reescribas componentes que ya funcionan.


---

17. NO IMPLEMENTAR FEA

ESTA TAREA NO INCLUYE:

Gmsh;

Tet4;

solver FEA;

SciPy FEA;

SfePy;

cálculo de tensiones;

condiciones de frontera;

cargas;

SIMP;

TopOpt.


Si esos componentes ya existen:

> no los desarrolles ni los rediseñes.



Solo asegúrate de que no dependan de Onshape.


---

18. VALIDACIÓN DURANTE LA LIMPIEZA

Después de cada bloque importante:

1. ejecutar tests relevantes;


2. corregir errores;


3. continuar únicamente cuando el sistema vuelva a estar estable.



No acumules cambios sin validar.


---

19. VALIDACIÓN FINAL

Al finalizar ejecuta:

A. Búsqueda global

Buscar nuevamente:

onshape
Onshape
ONSHAPE
oauth
OAuth
featurescript
FeatureScript
app-extension
App Extension
onshape_client
connectors.onshape
onshape_session

B. Clasificación

Cada coincidencia restante debe clasificarse:

DOCUMENTACIÓN HISTÓRICA
REFERENCIA FUTURA
FALSO POSITIVO
ERROR

No debe quedar ninguna coincidencia correspondiente a código funcional de Onshape.


---

20. PRUEBAS FUNCIONALES OBLIGATORIAS

Ejecuta la suite completa.

Además verifica explícitamente:

1. La aplicación inicia sin credenciales externas.
2. La API inicia.
3. El frontend funciona.
4. Se puede cargar un STEP.
5. STEPAdapter procesa el STEP.
6. Se crea CADModel.
7. El Core procesa CADModel.
8. Los tests de independencia pasan.
9. No se necesita Onshape.
10. No se necesita OAuth.
11. No se necesita otro CAD.

No declares éxito si alguna de estas pruebas falla.


---

21. PRUEBA DE AISLAMIENTO

La prueba definitiva debe comprobar que el proyecto funciona sin:

Onshape
OAuth
credenciales externas
sesión CAD
CAD instalado
API CAD externa

El resultado esperado es:

APLICACIÓN
    ↓
ARCHIVO STEP LOCAL
    ↓
STEP ADAPTER
    ↓
CADModel
    ↓
CORE


---

22. ACTUALIZAR RESUMEN_IMPLEMENTACION.md

Al finalizar actualiza:

RESUMEN_IMPLEMENTACION.md

Documenta:

auditoría inicial;

archivos eliminados;

directorios eliminados;

imports eliminados;

OAuth eliminado;

configuración eliminada;

tests eliminados;

tests conservados;

tests ejecutados;

resultado de las pruebas;

referencias Onshape restantes y su clasificación;

problemas encontrados;

problemas resueltos;

pendientes reales.


No declares algo como COMPLETADO sin evidencia.


---

23. CRITERIOS DE ACEPTACIÓN

La tarea solamente puede declararse:

COMPLETADA

si:

[ ] connectors/onshape/ fue eliminado si era exclusivamente legado.

[ ] onshape_client.py fue eliminado si era exclusivamente un shim.

[ ] OAuth fue eliminado del código funcional.

[ ] No existen endpoints funcionales de Onshape.

[ ] No existen credenciales Onshape requeridas.

[ ] No existen tests funcionales de Onshape.

[ ] geometry_processor.py no conserva compatibilidad innecesaria con Onshape.

[ ] Frontend no depende de Onshape.

[ ] Core sigue siendo independiente.

[ ] STEP → CADModel sigue funcionando.

[ ] La API standalone sigue funcionando.

[ ] La suite completa de tests pasa.

[ ] La aplicación puede ejecutarse sin servicios externos.

[ ] La búsqueda final no encuentra código funcional de Onshape.

[ ] RESUMEN_IMPLEMENTACION.md está actualizado.



---

24. CONDICIÓN DE BLOQUEO

Si después de la limpieza existe cualquier código que haga que el funcionamiento normal de la aplicación dependa de:

Onshape
OAuth
otro CAD
API CAD externa

entonces:

STANDALONE = BLOQUEADO

No declares la tarea completada.


---

25. REGLA FINAL

No intentes demostrar que la nueva arquitectura funciona conservando la antigua.

La antigua arquitectura debe desaparecer del producto principal.

El resultado final debe ser:

┌─────────────────────────────┐
│     APLICACIÓN STANDALONE   │
├─────────────────────────────┤
│                             │
│  STEP → Adapter → CADModel  │
│              ↓              │
│             Core            │
│              ↓              │
│       Servicios propios     │
│                             │
└─────────────────────────────┘

        SIN ONSHAPE
        SIN OAUTH
        SIN CAD EXTERNO
        SIN PLUGINS

No avances al desarrollo del Hito 2 durante esta tarea.

Primero deja la arquitectura standalone completamente limpia y verificable.

Cuando finalices, informa exactamente:

1. qué eliminaste;


2. qué conservaste y por qué;


3. qué modificaste;


4. qué tests ejecutaste;


5. resultados;


6. referencias Onshape restantes;


7. estado final de cada criterio;


8. pendientes reales.



No ocultes problemas ni declares éxito anticipadamente.