

# PROMPT — SANEAMIENTO Y CONSOLIDACIÓN DE LA ARQUITECTURA STANDALONE

## 1. OBJETIVO

Realizar una migración y saneamiento técnico definitivo del proyecto `Topologia_Optimizada` para convertirlo en una aplicación **100 % standalone**, completamente independiente de cualquier aplicación, plataforma, servicio o API CAD externa.

La prioridad absoluta de esta intervención es conseguir que la aplicación pueda funcionar con un archivo CAD local, inicialmente STEP, sin necesitar:

- Onshape;
- SolidWorks;
- Fusion 360;
- FreeCAD;
- AutoCAD;
- ninguna otra aplicación CAD;
- cuentas externas;
- OAuth;
- APIs CAD externas;
- plugins;
- extensiones;
- iframes de plataformas CAD;
- conexión a servidores CAD externos.

## 2. REGLA ARQUITECTÓNICA SUPREMA

La aplicación standalone es el producto principal.

El flujo objetivo de esta etapa es:

```text
ARCHIVO STEP LOCAL
        ↓
STEP ADAPTER
        ↓
CADModel
        ↓
CORE DE LA APLICACIÓN
        ↓
RESULTADO / PREPARACIÓN PARA ETAPAS POSTERIORES

No debe existir ninguna dependencia de Onshape ni de otro CAD para ejecutar este flujo.

Las futuras integraciones con CAD serán módulos opcionales y externos al Core.

NO desarrollar dichos módulos durante esta intervención.


---

3. DOCUMENTACIÓN QUE DEBES LEER

Antes de modificar código debes leer obligatoriamente:

1. README.md


2. metodologia.md


3. prompt.md


4. RESUMEN_IMPLEMENTACION.md



IMPORTANTE:

plan_implementacion_antigravity.md pertenece a una arquitectura anterior y NO debe utilizarse como fuente de requisitos, planificación ni arquitectura.

Si existe, debe ser eliminado durante esta intervención.

No crees ningún nuevo archivo de planificación equivalente.


---

4. AUDITORÍA INICIAL OBLIGATORIA

Antes de modificar archivos realiza una auditoría completa del repositorio.

Debes identificar explícitamente:

estructura actual;

módulos;

dependencias;

imports;

endpoints;

frontend;

tests;

scripts;

configuraciones;

variables de entorno;

documentación;

archivos heredados;

referencias a Onshape;

referencias a OAuth;

referencias a FeatureScript;

referencias a App Extension;

referencias a iframe de Onshape;

referencias a APIs CAD externas;

código muerto;

mocks;

fallbacks;

componentes duplicados.


Busca referencias tanto por nombre de archivo como por contenido.

No asumas que un archivo es innecesario únicamente por su nombre.

Antes de eliminar código debes determinar qué dependencias tiene.


---

5. ELIMINACIÓN DE LA ARQUITECTURA ONshape

La arquitectura actual del producto NO debe conservar funcionalidad Onshape.

Debes identificar y eliminar o aislar completamente del flujo standalone cualquier componente relacionado con:

onshape_client.py;

OAuth;

/login;

/oauth/callback;

tokens;

Client ID;

Client Secret;

Document ID;

Workspace ID;

Element ID;

API REST de Onshape;

FeatureScript;

App Extension;

iframe específico de Onshape;

selección de geometría desde Onshape;

descarga de modelos desde Onshape;

endpoints específicos de Onshape;

tests específicos de Onshape;

frontend específico de Onshape.


La decisión sobre cada archivo debe basarse en su uso real.

Si un archivo es exclusivamente de la arquitectura Onshape anterior y ya no tiene utilidad:

> ELIMINARLO.



No mantenerlo solamente para "compatibilidad hacia atrás".

La compatibilidad con la arquitectura anterior NO es un requisito.


---

6. ARCHIVOS HEREDADOS

Presta especial atención a archivos como:

onshape_client.py

test_oauth.py

app-extension.html

integracion_onshape_app.md

plan_implementacion_antigravity.md


Determina individualmente si:

1. debe eliminarse;


2. debe reemplazarse;


3. debe conservarse por una razón técnica real.



No conserves código exclusivamente porque existía antes.

No elimines archivos sin analizar sus dependencias.

Toda decisión debe documentarse en RESUMEN_IMPLEMENTACION.md.


---

7. OAUTH

La aplicación standalone NO utiliza OAuth.

Debes eliminar del producto:

flujo de login OAuth;

callback OAuth;

intercambio de tokens;

refresh tokens;

credenciales OAuth;

configuración específica de Onshape;

variables de entorno relacionadas con Onshape.


No reemplaces OAuth por otro sistema de autenticación.

La aplicación standalone no necesita autenticación externa para cargar y procesar archivos locales.


---

8. API

Audita api_server.py y todos los servicios relacionados.

El servidor debe quedar orientado exclusivamente a las necesidades de la aplicación standalone.

Elimina endpoints cuya única función sea:

autenticarse contra Onshape;

obtener datos de Onshape;

descargar modelos desde Onshape;

consultar documentos externos;

ejecutar operaciones específicas de Onshape.


No crees endpoints equivalentes innecesarios.

La API debe evolucionar alrededor del flujo:

ARCHIVO LOCAL
      ↓
IMPORTACIÓN
      ↓
CADModel
      ↓
PROCESAMIENTO


---

9. FRONTEND

Audita todo el frontend.

El frontend actual NO debe presentar:

conexión con Onshape;

estado de conexión Onshape;

login;

OAuth;

Document ID;

Workspace ID;

Element ID;

selector de plataforma CAD.


La interfaz debe orientarse al uso standalone.

El flujo mínimo esperado es:

IMPORTAR ARCHIVO STEP
        ↓
VALIDAR ARCHIVO
        ↓
CARGAR MODELO
        ↓
MOSTRAR ESTADO DEL MODELO

No desarrolles todavía:

configuración avanzada de FEA;

optimización topológica;

selección avanzada de restricciones;

plugins CAD;

integración con Onshape.


Esas funcionalidades pertenecen a etapas posteriores.


---

10. CADModel

Verifica que CADModel sea realmente independiente del formato y de cualquier plataforma CAD externa.

El Core no debe recibir objetos específicos de Onshape.

El flujo correcto es:

STEP
 ↓
STEP Adapter
 ↓
CADModel
 ↓
Core

El Core no debe importar directamente:

onshape_client;

módulos OAuth;

APIs externas;

código específico del formato STEP.


El adaptador debe ser responsable de convertir la información externa al modelo interno.


---

11. STEP ADAPTER

Audita el adaptador STEP existente.

Debe permitir:

1. recibir una ruta local;


2. validar que el archivo existe;


3. validar extensión/formato;


4. abrir el STEP;


5. detectar errores de lectura;


6. extraer la geometría necesaria;


7. construir un CADModel;


8. devolver errores claros cuando corresponda.



No utilizar datos ficticios para afirmar que el adaptador funciona.


---

12. PRUEBA REAL DE IMPORTACIÓN

Debes realizar una prueba utilizando un archivo STEP real.

La prueba debe demostrar:

STEP REAL
   ↓
STEP ADAPTER
   ↓
CADModel REAL

Debe comprobarse como mínimo:

archivo válido;

archivo inexistente;

archivo inválido/corrupto;

extracción de geometría;

creación del modelo interno;

manejo correcto de errores.


Si no existe un STEP real apropiado en el repositorio, crea una prueba reproducible que indique claramente qué archivo externo local debe utilizarse.

No inventes resultados.


---

13. CORE

Audita todos los módulos dentro de core/.

El Core debe ser independiente de:

Onshape;

OAuth;

HTTP externo;

APIs CAD;

frontend;

detalles de presentación;

credenciales.


Debe poder recibir información del modelo interno y trabajar sobre ella.

Si encuentras imports o dependencias prohibidas dentro del Core:

> corrígelos.




---

14. DEPENDENCIAS

Audita:

requirements.txt;

pyproject.toml;

archivos de configuración;

scripts de instalación;

variables de entorno.


Elimina dependencias que sean utilizadas exclusivamente por Onshape/OAuth si ya no tienen otra función válida.

No elimines una librería solamente porque parezca innecesaria.

Comprueba primero sus usos.

No agregues dependencias nuevas salvo que sean necesarias para cumplir el objetivo de esta intervención.


---

15. VARIABLES DE ENTORNO

Audita .env.example y cualquier configuración relacionada.

No deben existir variables obligatorias relacionadas con:

ONSHAPE_*
OAUTH_*
CLIENT_ID
CLIENT_SECRET

si su único propósito era la integración anterior.

La aplicación standalone debe poder iniciarse sin credenciales externas.


---

16. TESTS

Audita todos los tests existentes.

Clasifícalos:

VÁLIDOS

Tests que comprueban funcionalidades pertenecientes a la nueva arquitectura standalone.

OBSOLETOS

Tests cuyo único objetivo era comprobar:

OAuth;

Onshape;

App Extension;

APIs Onshape;

integración CAD externa.


Los tests obsoletos deben eliminarse junto con la funcionalidad obsoleta.

No mantengas tests de arquitectura descartada solamente para conservar un número elevado de tests.

NUEVOS

Cuando sea necesario, crea tests que demuestren:

STEP → Adapter → CADModel

y la independencia del Core.


---

17. TEST DE INDEPENDENCIA

Debes crear o adaptar una prueba que demuestre que el Core puede utilizarse sin:

onshape_client;

OAuth;

credenciales externas;

red;

aplicaciones CAD externas.


La prueba debe fallar si el Core vuelve a depender de componentes de Onshape.


---

18. NO UTILIZAR MOCKS COMO EVIDENCIA

No utilices mocks para afirmar que:

STEP funciona;

CADModel funciona con geometría real;

la aplicación standalone procesa modelos reales.


Los mocks pueden utilizarse únicamente para tests unitarios aislados.

Toda afirmación sobre funcionamiento real debe tener evidencia real.


---

19. NO AVANZAR A FEA NI TOPOPT

Esta intervención NO tiene como objetivo implementar:

Gmsh;

FEA;

solver Tet4;

SIMP;

optimización topológica;

sensibilidades;

compliance;

condiciones de frontera avanzadas.


Si ya existen componentes relacionados, únicamente audítalos y asegúrate de que no introduzcan dependencias prohibidas.

No conviertas esta intervención en una implementación de Hito FEA.


---

20. ELIMINAR DOCUMENTACIÓN OBSOLETA

Elimina o actualiza documentación que presente Onshape como dependencia actual.

Debe eliminarse especialmente:

plan_implementacion_antigravity.md

No debe existir otro documento que contradiga:

> STANDALONE FIRST.



La documentación histórica puede conservarse únicamente si está claramente marcada como histórica y no forma parte de las instrucciones activas del proyecto.


---

21. README Y METODOLOGÍA

No cambies arbitrariamente README.md ni metodologia.md.

Si durante la implementación detectas una contradicción real:

1. documenta la contradicción;


2. determina cuál es la interpretación correcta según la arquitectura actual;


3. corrige únicamente lo necesario;


4. registra el cambio.



No reescribas estos documentos innecesariamente.


---

22. RESUMEN_IMPLEMENTACION.md

Al finalizar debes actualizar RESUMEN_IMPLEMENTACION.md.

La documentación debe registrar:

auditoría inicial;

archivos eliminados;

archivos modificados;

dependencias eliminadas;

código Onshape eliminado;

OAuth eliminado;

tests eliminados;

tests nuevos;

pruebas ejecutadas;

resultado de cada prueba;

problemas encontrados;

decisiones tomadas;

estado de cada requisito;

pendientes;

bloqueadores;

siguiente etapa recomendada.


No declares COMPLETADO algo que no pueda demostrarse.


---

23. CRITERIOS DE ACEPTACIÓN

La intervención solo puede declararse COMPLETADA si se cumplen TODOS estos puntos:

Arquitectura

[ ] La aplicación principal es standalone.

[ ] No necesita ningún CAD externo.

[ ] No necesita Onshape.

[ ] No necesita OAuth.

[ ] No necesita credenciales externas.


Código

[ ] No existe dependencia funcional del código Onshape.

[ ] El Core es CAD-agnostic.

[ ] STEP entra mediante un Adapter.

[ ] CADModel funciona como representación interna.

[ ] No existen endpoints obligatorios de Onshape.


Configuración

[ ] No existen credenciales Onshape obligatorias.

[ ] No existen variables OAuth obligatorias.

[ ] El proyecto puede iniciarse sin cuentas externas.


Tests

[ ] Tests obsoletos de Onshape/OAuth eliminados.

[ ] Tests standalone ejecutados.

[ ] Importación STEP real verificada.

[ ] STEP → Adapter → CADModel verificado.

[ ] Independencia del Core verificada.


Documentación

[ ] README.md sigue alineado.

[ ] metodologia.md sigue alineado.

[ ] prompt.md refleja la tarea actual.

[ ] RESUMEN_IMPLEMENTACION.md actualizado.

[ ] plan_implementacion_antigravity.md eliminado.

[ ] No existen documentos activos que presenten Onshape como dependencia.



---

24. AUDITORÍA FINAL OBLIGATORIA

Antes de declarar la tarea terminada realiza una segunda auditoría completa.

Debes buscar nuevamente en todo el repositorio:

onshape
oauth
featurescript
app extension
iframe
client_id
client_secret
document id
workspace id
element id

Cada coincidencia debe ser clasificada como:

NECESARIA
HISTÓRICA
DOCUMENTACIÓN
CÓDIGO OBSOLETO
ERROR

No debe quedar ninguna dependencia funcional de Onshape.


---

25. PRUEBA FINAL DE AISLAMIENTO

La prueba final debe demostrar que la aplicación puede ejecutarse en un entorno donde:

no exista Onshape;

no existan credenciales Onshape;

no exista OAuth;

no exista una sesión CAD;

no exista conexión con un CAD externo.


Debe poder realizar:

INICIAR APLICACIÓN
      ↓
CARGAR STEP LOCAL
      ↓
CREAR CADModel
      ↓
PROCESAR MODELO

Si alguna parte del flujo requiere Onshape u otro CAD:

> la migración NO está completada.




---

26. ESTADOS FINALES

Al terminar clasifica explícitamente cada requisito:

COMPLETADO
PARCIAL
PENDIENTE
BLOQUEADO

No utilices otros estados.

Si existe cualquier dependencia funcional de Onshape:

> STANDALONE = BLOQUEADO



Si la importación STEP no funciona realmente:

> IMPORTACIÓN STEP = PARCIAL o BLOQUEADO



Si no existen pruebas suficientes:

> VALIDACIÓN = PARCIAL




---

27. REGLA FINAL

NO avances a FEA, SIMP o TopOpt como siguiente implementación dentro de esta misma tarea.

Primero debe existir una base standalone limpia, verificable y reproducible.

El resultado esperado de esta intervención es:

ARQUITECTURA ANTIGUA
Onshape + OAuth + CAD externo
          ↓
       ELIMINADA
          ↓
ARQUITECTURA STANDALONE
          ↓
STEP LOCAL
          ↓
STEP ADAPTER
          ↓
CADModel
          ↓
CORE

Solo cuando esta arquitectura esté demostrada mediante código y pruebas podrá comenzar la siguiente etapa de desarrollo.

28. PRINCIPIO SUPREMO

> NO CONFUNDIR CÓDIGO EXISTENTE CON FUNCIONALIDAD VÁLIDA.



El objetivo no es conservar todo lo que ya existe.

El objetivo es dejar una base técnica limpia, independiente, verificable y preparada para continuar el desarrollo.

La aplicación standalone es el producto.

Las integraciones CAD externas son futuras extensiones opcionales.

No invertir estas prioridades.

