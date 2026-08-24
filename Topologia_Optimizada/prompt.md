ACTÚA COMO PROGRAMADOR SENIOR, ARQUITECTO DE SOFTWARE Y ESPECIALISTA EN INTEGRACIONES CAD, ONSHAPE API, ONSHAPE APP EXTENSIONS, PYTHON, FASTAPI, JAVASCRIPT, THREE.JS, GEOMETRÍA 3D, MALLADO FEM, FEA Y OPTIMIZACIÓN TOPOLÓGICA.

TRABAJA EXCLUSIVAMENTE SOBRE EL REPOSITORIO EXISTENTE.

NO CREES UN PROYECTO NUEVO DESDE CERO.
NO REESCRIBAS COMPONENTES FUNCIONALES SIN JUSTIFICACIÓN.
NO ASUMAS QUE UNA FUNCIÓN ESTÁ IMPLEMENTADA PORQUE EXISTAN SU ARCHIVO, CLASE, ENDPOINT O INTERFAZ.

REPOSITORIO:

https://github.com/Alfredojosejaim/Onshape

PROYECTO PRINCIPAL:

Topologia_Optimizada/

============================================================
OBJETIVO DE ESTA TAREA
============================================================

El proyecto ha avanzado, pero la auditoría anterior detectó una discrepancia importante:

LA DOCUMENTACIÓN DECLARA COMO COMPLETAS FUNCIONES QUE EN REALIDAD TODAVÍA SON CONTRATOS, PLACEHOLDERS O IMPLEMENTACIONES PARCIALES.

Ejemplos detectados:

- MESHER_REQUIRED
- FEA_SOLVER_REQUIRED
- BOUNDARY_MAPPING_REQUIRED
- STEP_RECONSTRUCTOR_REQUIRED
- geometría BoxGeometry de demostración;
- Keep-out ficticio;
- eventos heredados de FeatureScript;
- selección mediante IDs introducidos manualmente;
- TopOpt sin FEA real.

Por lo tanto, la prioridad absoluta de esta tarea es:

CORREGIR → IMPLEMENTAR → PROBAR → VALIDAR.

NO debes intentar completar todo el sistema de una sola vez.

El PRIMER HITO OBLIGATORIO será:

ONS HAPE
→ SELECCIÓN REAL
→ GEOMETRÍA REAL
→ STEP REAL
→ MALLA REAL
→ VISOR 3D REAL

Hasta que este pipeline funcione correctamente NO debes avanzar a FEA ni TopOpt.

============================================================
REGLA FUNDAMENTAL: NO MENTIR SOBRE EL ESTADO
============================================================

Una funcionalidad SOLO puede marcarse como:

COMPLETA

cuando existe código funcional y puede demostrarse mediante una prueba real.

NO considerar completa una funcionalidad porque exista:

- una clase;
- una función;
- un endpoint;
- un modelo Pydantic;
- un botón;
- una interfaz;
- un comentario;
- una documentación;
- un contrato;
- una respuesta JSON;
- un placeholder;
- una variable;
- un TODO.

Si el código devuelve:

MESHER_REQUIRED

entonces:

MALLADO = PENDIENTE.

Si devuelve:

FEA_SOLVER_REQUIRED

entonces:

FEA = PENDIENTE.

Si devuelve:

BOUNDARY_MAPPING_REQUIRED

entonces:

MAPEO DE CONDICIONES DE FRONTERA = PENDIENTE.

Si genera:

THREE.BoxGeometry

entonces:

VISUALIZACIÓN DE GEOMETRÍA REAL = PENDIENTE.

NO maquilles estos estados.

============================================================
FASE 0 — AUDITORÍA OBLIGATORIA
============================================================

ANTES DE MODIFICAR CUALQUIER CÓDIGO:

Lee completamente:

- api_server.py
- onshape_client.py
- geometry_processor.py
- topopt_solver.py
- optimization-app.html
- app-extension.html
- todos los modelos Pydantic;
- módulos OAuth;
- persistencia;
- configuración;
- requirements.txt / pyproject.toml;
- documentación;
- FeatureScript existente;
- tests existentes;
- archivos JavaScript/TypeScript;
- ejemplo.txt si existe.

Después realiza una auditoría real.

Crea una tabla interna:

COMPONENTE
ARCHIVO
ESTADO REAL
EVIDENCIA
PROBLEMA
ACCIÓN

Los únicos estados permitidos son:

🟢 COMPLETO
🟡 PARCIAL
🔴 PENDIENTE
⚫ OBSOLETO
⚠️ LIMITACIÓN EXTERNA

NO uses "COMPLETO" si no existe una implementación verificable.

============================================================
FASE 1 — ARQUITECTURA DEFINITIVA
============================================================

La arquitectura definitiva será:

                    ONSHAPE
                       │
                       ▼
              APP EXTENSION
             SELECTOR CAD
                       │
                       ▼
                 BACKEND
                  PYTHON
                       │
                       ▼
             GEOMETRÍA REAL
                       │
                       ▼
                  MALLADOR
                       │
                       ▼
                 VISOR 3D
                       │
                       ▼
            FEA + TOPOPT
                       │
                       ▼
               RESULTADO
                       │
                       ▼
                ONSHAPE API

La aplicación externa será la interfaz principal.

La App Extension dentro de Onshape será deliberadamente simple.

============================================================
FASE 2 — FEATURESCRIPT
============================================================

NO utilizar FeatureScript como mecanismo de comunicación.

FeatureScript NO puede comunicarse directamente con:

- Python;
- FastAPI;
- HTTP;
- sockets;
- servicios externos;
- librerías Python;
- solver TopOpt.

Por lo tanto:

NO IMPLEMENTAR:

FeatureScript → Backend

NO IMPLEMENTAR:

Backend → FeatureScript

Audita los FeatureScript existentes.

Si son innecesarios para la nueva arquitectura:

ELIMÍNALOS.

Si algún FeatureScript proporciona una función nativa que sigue siendo imprescindible:

CONSERVARLO SOLO PARA ESA FUNCIÓN.

En ningún caso utilizarlo como puente.

Eliminar también del backend cualquier semántica que suponga:

"FeatureScript event received"

si ya no corresponde a la arquitectura actual.

============================================================
FASE 3 — APP EXTENSION
============================================================

La App Extension existente NO debe convertirse en una aplicación TopOpt.

Debe ser un:

SELECTOR DE GEOMETRÍA.

Su función será exclusivamente:

1. Detectar el contexto actual de Onshape.
2. Permitir seleccionar la pieza principal.
3. Permitir seleccionar uno o varios sólidos Keep-out.
4. Mostrar las selecciones.
5. Confirmar.
6. Enviar los identificadores reales al backend.

NO debe contener:

- solver;
- FEA;
- TopOpt;
- parámetros de optimización;
- biblioteca de materiales;
- configuración avanzada de fuerzas;
- visor 3D principal.

La aplicación externa se encargará de todo eso.

============================================================
SELECCIÓN REAL — PROHIBIDO USAR IDs MANUALES COMO FLUJO PRINCIPAL
============================================================

La App Extension actual contiene campos como:

Document ID
Workspace ID
Element ID

y mecanismos de selección manual.

Eso debe considerarse:

PARCIAL.

Investiga la API/SDK oficial actual de Onshape.

Debes determinar el mecanismo correcto para obtener:

- documentId;
- workspaceId;
- elementId;
- partId;
- faceId cuando corresponda.

NO inventes eventos.

NO inventes métodos del SDK.

NO supongas que:

applicationInit
requestSelection
onSelectionChanged

son válidos simplemente porque existan en el código.

Verifica su compatibilidad con la API actual de Onshape.

Si el mecanismo actual no es válido:

REEMPLÁZALO POR EL MECANISMO OFICIAL.

Si una capacidad no existe:

DOCUMENTA LA LIMITACIÓN.

============================================================
FASE 4 — GEOMETRÍA REAL
============================================================

El backend ya posee lógica para descargar STEP.

AUDITA:

geometry_processor.py

Conserva lo que realmente funcione.

El objetivo de esta fase es conseguir:

SELECCIÓN REAL
↓
IDs REALES
↓
API ONSHAPE
↓
STEP REAL
↓
ARCHIVO REAL

NO generar:

- STEP ficticio;
- geometría aleatoria;
- geometría de prueba en producción.

El STEP debe provenir realmente de Onshape.

Validar:

- HTTP status;
- contenido;
- tamaño;
- formato;
- archivo válido.

Si la exportación falla:

devolver error real.

NO devolver una geometría de reemplazo.

============================================================
FASE 5 — VISOR 3D
============================================================

Actualmente existe Three.js.

CONSERVARLO.

NO crear otro visor.

Eliminar del flujo productivo:

THREE.BoxGeometry

y cualquier otra geometría artificial utilizada como sustituto de la pieza real.

NO utilizar:

- cubos;
- esferas;
- geometría dummy;
- modelos hardcodeados.

El visor debe mostrar la geometría REAL descargada.

El usuario debe poder:

- orbitar;
- rotar;
- hacer zoom;
- hacer pan;
- ajustar cámara al objeto;
- inspeccionar la pieza;
- ocultar/mostrar geometrías.

La experiencia debe parecer un visor CAD.

============================================================
IMPORTANTE: VISUALIZACIÓN ≠ MALLADO
============================================================

No confundas:

GEOMETRÍA CAD

con:

MALLA FEM.

El visor puede utilizar una representación optimizada para visualización.

El solver puede utilizar otra representación.

No fuerces un único formato para todo el pipeline.

Investiga la mejor estrategia.

============================================================
FASE 6 — MALLADO REAL
============================================================

SOLO después de conseguir:

Onshape → STEP → visor

implementar el mallado.

Actualmente existen contratos como:

MESHER_REQUIRED.

Eso significa:

MALLADO NO IMPLEMENTADO.

Debes integrar un mallador REAL.

Evaluar:

- Gmsh;
- Netgen;
- TetGen;
- otra solución apropiada.

Elegir una sola solución inicialmente.

Justificar la elección.

Debe poder:

1. recibir geometría real;
2. generar una malla real;
3. controlar tamaño de elemento;
4. producir nodos;
5. producir elementos;
6. identificar regiones;
7. devolver datos utilizables por FEA.

NO utilizar mallas aleatorias.

NO utilizar nodos generados artificialmente.

============================================================
FASE 7 — MAPEO GEOMETRÍA → MALLA
============================================================

ESTE PUNTO ES OBLIGATORIO.

Una selección realizada en Onshape debe poder terminar asociada a entidades de la malla.

Ejemplo:

ONSHAPE FACE
↓
IDENTIFICACIÓN GEOMÉTRICA
↓
ELEMENTOS/NODOS DE MALLA
↓
CONDICIÓN FEA

Debe resolverse:

- Design Space;
- Keep-out;
- Keep-in;
- caras de fijación;
- caras de carga.

NO basta con guardar:

faceId = "xxx"

Eso solamente representa una referencia.

Debe existir un mecanismo real para determinar qué entidades de la malla corresponden a esa región.

Si es necesario utilizar:

- tolerancias geométricas;
- proximidad;
- normales;
- bounding boxes;
- intersección geométrica;
- información B-Rep;

implementarlo correctamente.

============================================================
FASE 8 — VALIDACIÓN DEL PRIMER HITO
============================================================

ANTES DE CONTINUAR CON FEA:

Debe poder ejecutarse:

1. Abrir aplicación.
2. Iniciar sesión con Onshape.
3. Abrir App Extension.
4. Seleccionar una pieza real.
5. Seleccionar opcionalmente un Keep-out real.
6. Confirmar.
7. Backend recibe IDs reales.
8. Backend descarga STEP real.
9. STEP es válido.
10. Backend genera malla real.
11. Malla contiene nodos y elementos reales.
12. Visor muestra geometría real.
13. El usuario puede rotarla/inspeccionarla.

Solo cuando TODO esto funcione:

continuar.

============================================================
FASE 9 — NO IMPLEMENTAR FEA TODAVÍA SI EL HITO ANTERIOR FALLA
============================================================

No quiero una arquitectura enorme que termine teniendo:

- FEA ficticio;
- TopOpt ficticio;
- fuerzas simuladas;
- resultados falsos.

Primero:

GEOMETRÍA + MALLA + VISOR.

Después:

FEA.

Después:

TopOpt.

============================================================
FASE 10 — FEA
============================================================

Una vez validado el hito anterior:

auditar topopt_solver.py.

Actualmente existe:

FEA_SOLVER_REQUIRED.

Eso significa:

FEA = PENDIENTE.

No cambiar el mensaje simplemente para que parezca completado.

Integrar un solver FEA real compatible con:

- elasticidad lineal;
- módulo de Young;
- Poisson;
- desplazamientos;
- cargas;
- restricciones;
- compliance;
- tensiones cuando corresponda.

Evaluar herramientas disponibles.

NO inventar un solver.

============================================================
FASE 11 — FUERZAS
============================================================

Las fuerzas se configuran EN LA APP EXTERNA.

No en la App Extension.

La aplicación debe permitir posteriormente:

- magnitud;
- unidad;
- dirección;
- sentido;
- región/cara de aplicación;
- múltiples cargas.

Visualizarlas sobre el modelo con flechas.

Ejemplo:

             ↓ 1000 N
             ↓
       ┌────────────┐
       │    PIEZA   │
       │            │
       └────────────┘
       █████████████
          FIJACIÓN

La fuerza debe terminar realmente en:

Face/Region
↓
Mesh
↓
Nodes
↓
FEA.

============================================================
FASE 12 — RESTRICCIONES
============================================================

Separar claramente:

FUERZA

de:

RESTRICCIÓN.

Las restricciones pueden ser:

- empotramiento;
- desplazamiento restringido;
- otros tipos soportados por el solver.

No implementar tipos que el solver no soporte.

============================================================
FASE 13 — TOPOPT
============================================================

Auditar completamente:

topopt_solver.py

Determinar:

- algoritmo actual;
- librería;
- entradas;
- salidas;
- dependencias.

El resultado debe depender realmente de:

- geometría;
- malla;
- material;
- fuerzas;
- restricciones;
- volumen objetivo;
- parámetros del algoritmo.

NO utilizar:

- random;
- números generados;
- desplazamientos ficticios;
- densidades ficticias.

============================================================
FASE 14 — PORCENTAJE DE OPTIMIZACIÓN
============================================================

El usuario podrá introducir un porcentaje de optimización.

Por ejemplo:

30 %

significa que el solver debe utilizar el valor correspondiente según la definición real de la librería.

NO crear simplemente un campo visual.

Debe estar conectado al solver.

Documentar exactamente qué significa:

- volumen objetivo;
- reducción de masa;
- densidad objetivo;

según corresponda.

============================================================
FASE 15 — PREVIEW
============================================================

Después de tener:

malla + FEA + TopOpt

implementar Preview.

El usuario podrá cambiar:

- fuerza;
- restricción;
- porcentaje;
- parámetros compatibles.

El sistema debe recalcular.

Utilizar:

- jobs;
- request IDs;
- cancelación;
- debounce;
- control de concurrencia.

Una respuesta vieja NO puede reemplazar una nueva.

Separar:

PREVIEW

de:

RESULTADO FINAL.

============================================================
FASE 16 — MATERIALES
============================================================

NO es obligatorio implementar todavía una biblioteca completa de materiales.

Pero NO destruir los modelos existentes.

La arquitectura debe permitir:

Material
- nombre
- módulo de Young
- Poisson
- densidad
- límite elástico
- propiedades adicionales

En el futuro:

- materiales incluidos;
- materiales personalizados;
- guardar;
- editar;
- seleccionar.

Implementar únicamente las propiedades realmente utilizadas por el solver actual.

============================================================
FASE 17 — RESULTADO FINAL
============================================================

El resultado TopOpt NO debe considerarse automáticamente un sólido CAD.

Separar:

TOPOPT RESULTADO

de:

CAD RESULTADO.

Determinar qué produce realmente el solver:

- densidades;
- voxel;
- malla;
- superficie;
- sólido.

Después determinar la estrategia adecuada para obtener una representación utilizable en Onshape.

============================================================
FASE 18 — DEVOLUCIÓN A ONSHAPE
============================================================

El botón:

[ ACEPTAR ]

debe consolidar el resultado.

Antes de aceptar:

NO modificar permanentemente el modelo original.

Al aceptar:

1. validar resultado;
2. generar representación final;
3. utilizar API oficial de Onshape;
4. importar/crear el resultado mediante un mecanismo realmente soportado;
5. verificar respuesta;
6. mostrar confirmación.

NO inventar endpoints.

NO afirmar que una malla es un sólido CAD.

Si Onshape no permite realizar una determinada operación:

documentar la limitación.

============================================================
FASE 19 — LOGIN DE LA APP EXTERNA
============================================================

La aplicación externa debe controlar el estado de autenticación.

Al iniciar:

"Comprobando conexión con Onshape..."

Si no existe sesión:

"○ No conectado"

[ INICIAR SESIÓN CON ONSHAPE ]

Debe ejecutar:

GET /login

Después del OAuth:

validar realmente el access token.

Mostrar:

"● Conectado a Onshape"

"Conectado como: [usuario]"

NO mostrar "Conectado" únicamente porque existe un token guardado.

============================================================
FASE 20 — APP EXTENSION INSTALADA
============================================================

NO implementar todavía instalación automática.

Solo preparar arquitectura futura.

Más adelante queremos:

¿App Extension instalada?

NO
↓
[ AGREGAR A ONSHAPE ]

Pero NO desarrollar esta función ahora.

No inventar API para instalar aplicaciones.

============================================================
FASE 21 — LIMPIEZA
============================================================

Eliminar código obsoleto únicamente después de comprobar dependencias.

Eliminar del flujo productivo:

- FeatureScript bridge;
- endpoints de eventos FeatureScript;
- geometría dummy;
- resultados dummy;
- mallas aleatorias;
- mocks productivos.

Los mocks solo pueden permanecer en:

tests/

y deben estar claramente identificados.

No borrar pruebas válidas.

============================================================
FASE 22 — DOCUMENTACIÓN
============================================================

Actualizar toda documentación que actualmente diga:

COMPLETO

cuando en realidad sea:

PARCIAL

o:

PENDIENTE.

La documentación debe reflejar el estado REAL.

Crear/actualizar:

integracion_onshape_app.md

Debe incluir:

- arquitectura;
- flujo de datos;
- autenticación;
- selección;
- geometría;
- STEP;
- mallado;
- mapeo;
- FEA;
- TopOpt;
- preview;
- materiales;
- resultado;
- retorno a Onshape;
- limitaciones.

============================================================
FASE 23 — PRUEBAS
============================================================

Crear pruebas reales para cada etapa.

Como mínimo:

TEST 1
OAuth válido.

TEST 2
OAuth inválido.

TEST 3
Refresh token.

TEST 4
Selección real.

TEST 5
Descarga STEP.

TEST 6
STEP inválido.

TEST 7
Mallado.

TEST 8
Malla contiene nodos.

TEST 9
Malla contiene elementos.

TEST 10
Visualización de geometría real.

NO considerar un test válido si solamente comprueba:

HTTP 200.

Debe comprobar comportamiento real.

============================================================
FASE 24 — DEPENDENCIAS
============================================================

Antes de instalar cualquier librería:

explicar:

- por qué;
- qué problema resuelve;
- compatibilidad;
- impacto.

No agregar dependencias innecesarias.

Si se necesita Gmsh, FEA u otra herramienta externa:

documentar instalación.

============================================================
FASE 25 — REGLAS ABSOLUTAS
============================================================

REGLA 1:

NO INVENTES APIs DE ONSHAPE.

REGLA 2:

NO INVENTES EVENTOS DE ONSHAPE.

REGLA 3:

NO INVENTES FUNCIONALIDADES DEL SOLVER.

REGLA 4:

NO UTILICES DATOS ALEATORIOS PARA SIMULAR RESULTADOS.

REGLA 5:

NO UTILICES BoxGeometry COMO SUSTITUTO DE LA PIEZA REAL.

REGLA 6:

NO MARQUES COMO COMPLETO ALGO QUE NO PUEDAS EJECUTAR.

REGLA 7:

NO CREES UN SEGUNDO BACKEND.

REGLA 8:

NO CREES UNA SEGUNDA APP EXTERNA.

REGLA 9:

NO CONVIERTAS LA APP EXTENSION EN LA INTERFAZ PRINCIPAL.

REGLA 10:

NO UTILICES FEATURESCRIPT COMO PUENTE.

REGLA 11:

NO BORRES COMPONENTES FUNCIONALES SIN AUDITARLOS.

REGLA 12:

NO IMPLEMENTES FEA ANTES DE TENER MALLA REAL.

REGLA 13:

NO IMPLEMENTES TOPOPT ANTES DE TENER FEA REAL.

REGLA 14:

NO IMPLEMENTES DEVOLUCIÓN CAD ANTES DE TENER UN RESULTADO REAL.

REGLA 15:

NO CAMBIES EL OBJETIVO DEL PROYECTO.

============================================================
FASE 26 — ORDEN ESTRICTO DE EJECUCIÓN
============================================================

Debes trabajar exactamente en este orden:

PASO 1
Auditoría.

PASO 2
Corrección de documentación.

PASO 3
Eliminar dependencia conceptual de FeatureScript.

PASO 4
App Extension como selector real.

PASO 5
Selección real.

PASO 6
Obtención de STEP real.

PASO 7
Mallado real.

PASO 8
Mapeo geometría → malla.

PASO 9
Integración del visor con geometría real.

PASO 10
VALIDAR HITO 1.

NO avanzar si el HITO 1 falla.

HITO 1:

Onshape
↓
selección real
↓
backend
↓
STEP real
↓
malla real
↓
visor real

Solo después:

PASO 11
FEA.

PASO 12
Fuerzas.

PASO 13
Restricciones.

PASO 14
TopOpt.

PASO 15
Preview.

PASO 16
Materiales.

PASO 17
Resultado final.

PASO 18
Retorno a Onshape.

============================================================
FASE 27 — INFORME FINAL OBLIGATORIO
============================================================

Al finalizar debes entregar:

1. RESUMEN DE LA AUDITORÍA.

2. FUNCIONALIDADES QUE YA ESTABAN REALMENTE COMPLETAS.

3. FUNCIONALIDADES QUE ESTABAN PARCIALES.

4. FUNCIONALIDADES QUE ESTABAN FALSAMENTE MARCADAS COMO COMPLETAS.

5. ARCHIVOS MODIFICADOS.

6. ARCHIVOS CREADOS.

7. ARCHIVOS ELIMINADOS.

8. DEPENDENCIAS AGREGADAS.

9. DEPENDENCIAS ELIMINADAS.

10. VARIABLES `.env`.

11. CONFIGURACIÓN DE ONSHAPE.

12. SCOPES OAUTH.

13. FEATURESCRIPT:
    - eliminado;
    - conservado;
    - rediseñado;
    y justificación.

14. APP EXTENSION:
    - qué hace ahora;
    - cómo obtiene la selección.

15. GEOMETRÍA:
    - formato utilizado;
    - origen;
    - validación.

16. MALLADOR:
    - herramienta;
    - configuración;
    - resultado.

17. VISOR:
    - formato visual;
    - cómo recibe la geometría.

18. FEA:
    - estado.

19. TOPOPT:
    - estado.

20. RETORNO A ONSHAPE:
    - estado.

21. PRUEBAS EJECUTADAS.

22. RESULTADOS DE CADA PRUEBA.

23. LIMITACIONES ACTUALES.

24. PRÓXIMO HITO.

============================================================
REGLA FINAL Y MÁS IMPORTANTE
============================================================

NO QUIERO UNA IMPLEMENTACIÓN "DEMO".

QUIERO UNA IMPLEMENTACIÓN REAL Y VERIFICABLE.

Si una parte no puede implementarse todavía:

NO LA SIMULES.

Déjala explícitamente como:

PENDIENTE

y explica exactamente qué dependencia falta.

Si descubres una limitación de Onshape:

NO INVENTES UNA SOLUCIÓN.

Documenta:

- qué intentaste;
- qué API consultaste;
- qué permite;
- qué no permite;
- alternativa técnicamente viable.

Si encuentras código existente que funciona:

REUTILÍZALO.

Si encuentras código que solamente aparenta funcionar:

CORRÍGELO.

Si la documentación contradice al código:

EL CÓDIGO REAL TIENE PRIORIDAD PARA DETERMINAR EL ESTADO.

============================================================
COMIENZA AHORA
============================================================

PRIMERO:

AUDITA TODO EL REPOSITORIO.

NO MODIFIQUES NADA TODAVÍA.

Después de la auditoría, presenta:

A. Estado real actual.
B. Problemas encontrados.
C. Archivos afectados.
D. Plan exacto de implementación.
E. Dependencias necesarias.
F. Riesgos o limitaciones.

SOLO DESPUÉS DE PRESENTAR ESA AUDITORÍA COMIENZA A MODIFICAR EL CÓDIGO.

Y RECUERDA:

EL PRIMER OBJETIVO NO ES TOPOPT.

EL PRIMER OBJETIVO ES CONSEGUIR DE FORMA REAL Y DEMOSTRABLE:

ONSHAPE
→ SELECCIÓN REAL
→ STEP REAL
→ MALLA REAL
→ VISOR 3D REAL.

NO AVANCES AL SIGUIENTE NIVEL HASTA QUE ESE FLUJO FUNCIONE.
