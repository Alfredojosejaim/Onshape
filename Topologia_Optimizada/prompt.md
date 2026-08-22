
Trabaja sobre el proyecto existente de Topología Optimizada.

La aplicación actualmente:
- se ejecuta correctamente;
- dispone de backend Python/FastAPI;
- dispone de interfaz web;
- tiene OAuth 2.0 real con Onshape;
- puede conectarse correctamente con Onshape.

NO rehagas ni rompas estas partes. Audita primero el proyecto y modifica solamente lo necesario.

IMPORTANTE: antes de implementar, lee completamente el archivo `ejemplo.txt` disponible en el proyecto y revisa el código existente.

# CAMBIO FUNDAMENTAL DE ARQUITECTURA

El enfoque anterior intentaba establecer:

FeatureScript → Backend Python

Este enfoque debe eliminarse.

FeatureScript es un lenguaje determinista que se ejecuta dentro del sandbox aislado de Onshape. NO tiene acceso a red y no debe utilizarse como cliente HTTP.

Por lo tanto, FeatureScript NO debe intentar:

- realizar HTTP requests;
- abrir sockets;
- comunicarse directamente con FastAPI;
- ejecutar Python;
- ejecutar C++;
- utilizar librerías externas;
- ejecutar directamente el solver TopOpt/FEA;
- conectarse a Internet.

La arquitectura definitiva será:

ONS HAPE
│
├── Part Studio
│   └── FeatureScript
│       └── Lee parámetros/variables y genera/regenera geometría
│
└── App integrada como iFrame
    │
    └── JavaScript/TypeScript
        │
        │ HTTPS REST
        ▼
      FastAPI
        │
        ├── Topología / FEA
        │
        └── Onshape REST API
                  │
                  ▼
           Variables / estado / documento
                  │
                  ▼
             Regeneración
                  │
                  ▼
             FeatureScript
                  │
                  ▼
              Geometría

La comunicación externa debe realizarse mediante el iFrame y el backend, NO mediante FeatureScript.

# OBJETIVO

El usuario debe controlar la herramienta desde dentro de Onshape.

La interfaz web externa debe integrarse como una App/iFrame dentro de Onshape.

El flujo esperado es:

Onshape
↓
App integrada
↓
Usuario configura la operación
↓
iFrame captura eventos y selecciones
↓
Backend recibe parámetros
↓
Backend ejecuta procesamiento pesado
↓
Backend utiliza la API oficial de Onshape para actualizar el documento/estado
↓
FeatureScript se regenera
↓
Onshape muestra la geometría resultante

# 1. AUDITORÍA DEL PROYECTO

Antes de modificar código, audita completamente el repositorio.

Revisa:

- backend;
- frontend;
- OAuth;
- FeatureScript;
- endpoints;
- persistencia;
- configuración;
- dependencias;
- túnel HTTPS;
- configuración de Onshape;
- archivos existentes;
- comunicación actual;
- documentación;
- mocks;
- placeholders;
- datos aleatorios;
- código muerto;
- endpoints que intenten comunicar directamente FeatureScript con Python.

Determina qué partes ya funcionan y NO las rehagas innecesariamente.

Si encuentras código de comunicación directa:

FeatureScript → Backend

elimínalo o sustitúyelo por la nueva arquitectura únicamente cuando sea necesario.

# 2. ARQUITECTURA BIDIRECCIONAL

Implementar:

Usuario
↓
Onshape
↓
iFrame
↓
JavaScript
↓
FastAPI
↓
TopOpt / FEA
↓
Onshape REST API
↓
Variables / estado / documento
↓
Regeneración
↓
FeatureScript
↓
Geometría

La comunicación FeatureScript → Backend queda PROHIBIDA.

# 3. IFRAME

La aplicación debe ejecutarse integrada dentro de Onshape mediante un iFrame.

Evaluar si es más apropiado utilizar:

- Right Panel;
- Document Tab;
- otra modalidad oficialmente soportada.

Elegir la opción adecuada para el proyecto.

La interfaz externa debe seguir funcionando localmente para desarrollo, pero la integración final debe poder ejecutarse dentro de Onshape.

# 4. CLIENTE DEL IFRAME

Crear o modificar:

`app_client.js`

o TypeScript si el proyecto utiliza TypeScript.

El cliente será responsable de:

- comunicarse con Onshape;
- recibir eventos;
- capturar selección;
- obtener contexto;
- enviar datos al backend;
- recibir resultados;
- gestionar estados;
- solicitar actualizaciones;
- mostrar progreso y errores.

Utilizar:

`async/await`

con manejo estricto de:

- errores HTTP;
- JSON inválido;
- timeouts;
- respuestas inesperadas;
- pérdida de conexión.

# 5. POSTMESSAGE

Implementar comunicación mediante:

`window.postMessage`

cuando corresponda al mecanismo real de integración de Onshape.

Investigar primero la documentación y el mecanismo real de eventos de Onshape.

NO asumir que los eventos:

- `onSelectionChanged`
- `onModelUpdated`

existen exactamente con esos nombres o tienen exactamente ese formato.

Si existen, utilizarlos correctamente.

Si no existen, utilizar el mecanismo oficial equivalente.

NO inventar APIs ni eventos.

Todo mensaje recibido debe validar:

- `event.origin`;
- estructura del mensaje;
- tipo;
- campos;
- tipos de datos.

Nunca aceptar cualquier origen mediante `*`.

# 6. COMUNICACIÓN IFRAME → BACKEND

El iFrame debe comunicarse con FastAPI mediante HTTPS REST.

Ejemplo conceptual:

iFrame
↓
POST /api/preview
↓
FastAPI
↓
Procesamiento
↓
Respuesta
↓
iFrame

Utilizar endpoints reales del proyecto.

No crear endpoints ficticios.

# 7. FEATURESCRIPT

Crear o modificar:

`script.fs`

El FeatureScript debe ser 100 % válido para Onshape.

Debe utilizar únicamente:

- FeatureScript;
- Standard Library;
- funciones realmente disponibles en Onshape.

NO debe utilizar:

- HTTP;
- sockets;
- Python;
- C++;
- librerías externas;
- acceso a Internet.

Su responsabilidad será exclusivamente:

1. leer parámetros;
2. leer variables/estado disponibles en el Part Studio;
3. validar la geometría;
4. generar/regenerar la geometría;
5. producir métricas o resultados mediante mecanismos compatibles con Onshape.

El cálculo pesado pertenece al backend.

# 8. VARIABLES Y ESTADO DE ONSHAPE

El backend/iFrame debe utilizar los mecanismos oficiales de Onshape para modificar el estado del documento.

NO asumir que existe una función externa como:

`setVariable(context, "nombre_variable", valor)`

que permita a Python modificar directamente una variable de Onshape.

Investigar la API oficial actual de Onshape para determinar cómo:

- crear variables;
- modificar variables;
- leer variables;
- actualizar elementos;
- provocar regeneración;
- comunicar resultados al FeatureScript.

Las variables forman parte del modelo de Onshape y FeatureScript debe consumirlas durante la regeneración.

NO inventar endpoints.

Si una estrategia no existe realmente en la API, reemplazarla por una alternativa oficial viable.

# 9. CUSTOM FEATURE

Crear/modificar el Custom Feature:

`Topología Optimizada`

Todos los textos visibles deben estar en español.

Debe permitir:

Pieza a modificar

[ Seleccionar sólido ]

Restricciones opcionales:

☐ Piezas que obstruyen

[ Seleccionar geometría ]

☐ Lugares de anclaje

[ Seleccionar caras ]

☐ Caras sin modificar

[ Seleccionar caras ]

Optimización:

Porcentaje de optimización

[ 50 ] %

# 10. PIEZA A MODIFICAR

La pieza a modificar es obligatoria.

Debe ser un sólido.

No aceptar:

- superficies;
- geometría abierta;
- entidades incompatibles.

Si no es un sólido mostrar:

"La pieza seleccionada debe ser un sólido."

# 11. PIEZAS QUE OBSTRUYEN

La opción es completamente opcional.

Si está desactivada:

- no solicitar selección;
- no enviar datos;
- no aplicar esta restricción.

Si está activada:

- permitir seleccionar las piezas/geometrías que representan obstáculos.

Estas geometrías representan regiones que el resultado no debe ocupar.

# 12. LUGARES DE ANCLAJE

La opción es completamente opcional.

Si está desactivada:

- no solicitar selección;
- no enviar datos;
- no aplicar esta restricción.

Si está activada:

- permitir seleccionar las caras de anclaje.

No inventar fuerzas.

Un anclaje representa una condición de soporte.

Si el solver necesita cargas/fuerzas para un cálculo físico válido, documentar qué información adicional es necesaria y no inventar valores.

# 13. CARAS SIN MODIFICAR

La opción es completamente opcional.

Si está desactivada:

- no solicitar selección;
- no enviar datos;
- no aplicar esta restricción.

Si está activada:

- permitir seleccionar las caras que deben permanecer protegidas.

# 14. PORCENTAJE DE OPTIMIZACIÓN

Agregar:

"Porcentaje de optimización"

Ejemplo:

50 %

Debe utilizarse realmente en el cálculo.

Validar el rango permitido.

Conceptualmente:

0 % = sin reducción

50 % = objetivo de reducción del 50 %

80 % = objetivo de reducción del 80 %

Si el algoritmo utiliza otra interpretación, documentarla claramente.

NO crear un parámetro que luego sea ignorado.

# 15. PAYLOAD

Utilizar una estructura equivalente a:

{
    "contexto": {
        "documentId": "...",
        "workspaceId": "...",
        "elementId": "..."
    },
    "pieza": {
        "referencia": "..."
    },
    "restricciones": {
        "obstrucciones": [],
        "anclajes": [],
        "carasSinModificar": []
    },
    "optimizacion": {
        "porcentaje": 50
    }
}

Los campos opcionales pueden ser arrays vacíos.

No enviar datos ficticios.

# 16. CONTEXTO DE ONSHAPE

Obtener dinámicamente:

- documentId;
- workspaceId;
- elementId.

No utilizar IDs hardcodeados.

No pedir al usuario que copie IDs manualmente.

# 17. GEOMETRÍA REAL

Eliminar cualquier:

- geometría aleatoria;
- sólido ficticio;
- STEP ficticio;
- resultado simulado.

La geometría debe proceder del documento real de Onshape.

Investigar la API adecuada para obtener:

- geometría;
- topología;
- teselación;
- STEP;
- STL;
- u otro formato apropiado.

Elegir el formato adecuado para el procesamiento actual.

# 18. BACKEND Y SOLVER

El backend puede utilizar herramientas apropiadas para el procesamiento pesado, por ejemplo:

- Python;
- NumPy;
- SciPy;
- Gmsh;
- Netgen;
- solver FEA;
- algoritmos TopOpt.

Estas herramientas NO deben ejecutarse dentro de FeatureScript.

Arquitectura:

FeatureScript
↓
iFrame
↓
FastAPI
↓
TopOpt / FEA
↓
Resultado
↓
Onshape REST API
↓
Regeneración
↓
FeatureScript

# 19. PREVISUALIZACIÓN DINÁMICA

Mantener el requisito fundamental de previsualización del diseño.

El usuario debe poder configurar la operación y observar cómo podría evolucionar la pieza antes de aceptar.

El flujo debe ser:

Seleccionar pieza
↓
Preview
↓
Agregar restricción
↓
Preview actualizado
↓
Cambiar porcentaje
↓
Preview actualizado
↓
Agregar otra restricción
↓
Preview actualizado
↓
Aceptar
↓
Cálculo final

NO esperar al botón Aceptar para ejecutar por primera vez la previsualización.

# 20. PREVIEW Y RESULTADO FINAL

Separar claramente:

PREVIEW:

Prioridad:
velocidad.

Puede utilizar:

- menor resolución;
- menos iteraciones;
- simplificaciones;
- aproximaciones controladas.

RESULTADO FINAL:

Prioridad:
precisión.

Debe ejecutar el procesamiento completo.

El preview no debe confundirse con el resultado final.

# 21. ACTUALIZACIÓN DEL PREVIEW

Cuando cambie:

- pieza;
- obstáculos;
- anclajes;
- caras protegidas;
- porcentaje;

el iFrame debe detectar el cambio y solicitar un nuevo preview.

Implementar:

- debounce;
- cancelación;
- request ID;
- control de respuestas obsoletas.

Ejemplo:

Preview 001
Preview 002
Preview 003

Si llega la respuesta de Preview 001 después de haber solicitado Preview 003, debe descartarse.

Una respuesta antigua nunca debe sobrescribir un resultado más reciente.

# 22. PREVIEW DENTRO DE ONSHAPE

Investigar cómo Onshape representa nativamente la previsualización de Custom Features y operaciones.

Si existe un mecanismo oficial de preview/regeneración que pueda utilizarse, aprovecharlo.

No crear artificialmente un sistema de transparencia si Onshape ya proporciona un mecanismo adecuado.

El objetivo visual es que el usuario pueda ver el posible resultado mientras edita la operación, de manera similar a una operación nativa de Onshape.

# 23. NO BLOQUEAR ONSHAPE

Analizar las limitaciones de regeneración de FeatureScript.

No ejecutar cálculos pesados dentro de FeatureScript.

No mantener procesos externos dentro de la regeneración.

El preview debe realizarse mediante:

iFrame → Backend → resultado → Onshape → regeneración.

Si existen limitaciones de tiempo o frecuencia de regeneración, documentarlas y diseñar una estrategia compatible.

# 24. RESULTADO FINAL

El objetivo final es que el resultado de la optimización pueda incorporarse al flujo de modelado de Onshape.

NO utilizar como solución definitiva:

Descargar STEP
↓
Importar manualmente.

Investigar las APIs oficiales disponibles para:

- importar geometría;
- actualizar elementos;
- modificar el documento;
- crear resultados;
- regenerar;
- utilizar FeatureScript.

Si una operación no es posible directamente mediante las APIs disponibles, documentar la limitación y proponer la alternativa real más cercana.

NO fingir que una capacidad existe.

# 25. ESTADOS

Implementar estados internos equivalentes a:

READY

PREVIEW_REQUESTED

PREVIEW_PROCESSING

PREVIEW_READY

FINAL_REQUESTED

FINAL_PROCESSING

FINAL_READY

ERROR

La interfaz puede mostrar:

"Preparado"

"Generando previsualización..."

"Previsualización actualizada"

"Calculando resultado final..."

"Resultado listo"

"Error"

# 26. OAUTH

Conservar el OAuth 2.0 existente.

No romper la autenticación actual.

Los secretos deben permanecer en backend.

Nunca enviar al frontend:

- client_secret;
- refresh_token;
- secretos privados.

Auditar los scopes y conservar únicamente los necesarios.

# 27. SEGURIDAD

Implementar:

- validación estricta de postMessage;
- validación de origen;
- CORS limitado;
- HTTPS;
- validación de payloads;
- autenticación del backend;
- protección CSRF cuando corresponda;
- secretos mediante .env;
- ningún secreto hardcodeado.

Actualizar `.env.example` si es necesario.

# 28. ARCHIVO ejemplo.txt

Leer completamente:

`ejemplo.txt`

antes de implementar el FeatureScript.

Utilizarlo como referencia para comprender patrones de FeatureScript.

NO copiar mecanismos de comunicación externa si contradicen la arquitectura actual.

El nuevo sistema NO debe realizar comunicación de red desde FeatureScript.

# 29. ENTREGABLE PRINCIPAL

Debes generar un único archivo Markdown:

`integracion_onshape_app.md`

Este archivo debe contener la documentación completa y el código necesario para la integración.

Debe incluir exactamente estas secciones:

## 1. ARQUITECTURA DEL FLUJO BIDIRECCIONAL

Explicar:

Onshape UI
↓
iFrame
↓
JavaScript
↓
Backend
↓
Onshape REST API
↓
Variables/estado/documento
↓
Regeneración
↓
FeatureScript
↓
Geometría

Explicar claramente la responsabilidad de cada componente.

## 2. SCRIPT EN FEATURESCRIPT

Archivo:

`script.fs`

Incluir código FeatureScript válido.

Debe:

- leer parámetros;
- leer variables/estado;
- validar sólidos;
- generar/regenerar geometría;
- producir métricas compatibles;
- no utilizar red.

## 3. CLIENTE DEL IFRAME

Archivo:

`app_client.js`

o:

`app_client.ts`

Debe incluir:

- async/await;
- postMessage;
- validación de origen;
- validación de mensajes;
- comunicación con backend;
- manejo de errores;
- timeout;
- procesamiento de respuestas.

## 4. BACKEND

Documentar endpoints reales.

Por ejemplo, solamente si existen:

POST /api/preview

POST /api/final

GET /api/status

Documentar:

- payload;
- respuesta;
- validaciones;
- errores;
- procesamiento.

## 5. INTEGRACIÓN CON ONSHAPE REST API

Documentar:

- endpoint real;
- método HTTP;
- autenticación;
- scopes;
- payload;
- respuesta;
- mecanismo utilizado para actualizar el documento;
- mecanismo de regeneración.

No inventar endpoints.

## 6. MATRIZ DE CONFIGURACIÓN Y PERMISOS

Incluir:

- OAuth Client ID;
- Redirect URI;
- Scopes;
- URL del iFrame;
- URL del backend;
- puerto;
- túnel;
- configuración de extensión;
- variables;
- permisos.

## 7. FLUJO DE PREVIEW

Documentar:

Cambio del usuario
↓
Evento
↓
iFrame
↓
Backend
↓
Preview
↓
Onshape
↓
Regeneración
↓
Resultado

## 8. FLUJO FINAL

Documentar:

Aceptar
↓
Solicitud final
↓
Solver completo
↓
Resultado
↓
Onshape
↓
Regeneración

## 9. LIMITACIONES TÉCNICAS

Documentar claramente:

- limitaciones de FeatureScript;
- limitaciones del iFrame;
- limitaciones de REST API;
- limitaciones de regeneración;
- limitaciones de tiempo;
- limitaciones del preview;
- limitaciones de actualización de geometría.

NO ocultar limitaciones.

# 30. REQUISITOS DEL CÓDIGO

FeatureScript:

- 100 % sintácticamente válido;
- compatible con Onshape;
- sin pseudocódigo presentado como código funcional;
- sin funciones inventadas;
- sin acceso a red.

JavaScript/TypeScript:

- async/await;
- validación estricta;
- manejo de errores HTTP;
- validación JSON;
- validación de mensajes;
- validación de origen.

Python:

- mantener FastAPI existente;
- no crear una segunda aplicación innecesaria;
- reutilizar componentes funcionales.

# 31. NO HACER

NO:

- rehacer el proyecto desde cero;
- romper OAuth;
- modificar innecesariamente la UI externa;
- hacer HTTP desde FeatureScript;
- hacer sockets desde FeatureScript;
- ejecutar Python desde FeatureScript;
- ejecutar C++ desde FeatureScript;
- utilizar mocks;
- utilizar geometría aleatoria;
- utilizar STEP ficticios;
- inventar APIs;
- inventar eventos;
- hardcodear IDs;
- hardcodear credenciales;
- asumir restricciones opcionales;
- crear una falsa previsualización;
- afirmar que algo funciona si no fue validado.

# 32. IMPLEMENTACIÓN POR ETAPAS

Implementar y validar en este orden:

ETAPA A
Auditar arquitectura actual.

ETAPA B
Eliminar comunicación directa FeatureScript → Backend.

ETAPA C
Confirmar iFrame dentro de Onshape.

ETAPA D
Confirmar:

Onshape → iFrame → Backend

ETAPA E
Confirmar:

Backend → Onshape

mediante mecanismos oficiales.

ETAPA F
Confirmar:

Variable/estado
↓
FeatureScript
↓
Geometría

ETAPA G
Implementar selección.

ETAPA H
Implementar restricciones.

ETAPA I
Implementar porcentaje.

ETAPA J
Implementar Preview.

ETAPA K
Implementar cálculo final.

ETAPA L
Integrar geometría final.

No avanzar silenciosamente si una etapa anterior falla.

# 33. AUDITORÍA FINAL

Comprobar:

APLICACIÓN

[ ] FastAPI funciona.
[ ] OAuth funciona.
[ ] UI externa funciona.
[ ] iFrame funciona dentro de Onshape.

COMUNICACIÓN

[ ] iFrame → Backend funciona.
[ ] Backend → Onshape funciona.
[ ] No existe comunicación directa FeatureScript → Backend.
[ ] postMessage validado.
[ ] Payload validado.

FEATURESCRIPT

[ ] Sintaxis válida.
[ ] No utiliza red.
[ ] Lee parámetros.
[ ] Lee variables/estado.
[ ] Genera geometría.

SELECCIÓN

[ ] Pieza sólida.
[ ] Obstáculos opcionales.
[ ] Anclajes opcionales.
[ ] Caras protegidas opcionales.
[ ] Porcentaje configurable.

PREVIEW

[ ] Preview inicial.
[ ] Preview dinámico.
[ ] Debounce.
[ ] Cancelación.
[ ] Requests identificados.
[ ] Respuestas antiguas descartadas.

GEOMETRÍA

[ ] Geometría real.
[ ] Sin mocks.
[ ] Sin datos aleatorios.
[ ] Sin STEP ficticio.

RESULTADO

[ ] Preview real.
[ ] Cálculo final real.
[ ] Resultado incorporable a Onshape.

# 34. CLASIFICACIÓN FINAL

Cada requisito debe clasificarse como:

COMPLETO

PARCIAL

PENDIENTE

LIMITACIÓN DE ONSHAPE

Para cada requisito no completado indicar:

1. Qué falta.
2. Por qué falta.
3. Qué dependencia existe.
4. Cuál es el siguiente paso.

# 35. INFORME FINAL

Al finalizar indicar:

- archivos creados;
- archivos modificados;
- archivos eliminados;
- dependencias agregadas;
- variables .env necesarias;
- scopes OAuth;
- configuración necesaria en Onshape Developer Portal;
- configuración del iFrame;
- URL del backend;
- configuración del túnel;
- comandos para ejecutar;
- pruebas realizadas;
- problemas encontrados;
- limitaciones de Onshape;
- funcionalidades que quedaron pendientes.

IMPORTANTE:

No quiero una explicación genérica.

Quiero que trabajes directamente sobre el proyecto existente, audites el código actual, realices las modificaciones necesarias y dejes implementada la arquitectura.

Si una parte no puede implementarse debido a una limitación real de Onshape, NO inventes una solución. Déjala claramente identificada co