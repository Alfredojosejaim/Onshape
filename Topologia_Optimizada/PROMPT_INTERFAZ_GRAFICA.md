Sí. Acá hay que **mantener la interfaz exactamente como está** y agregar el FeatureScript como un componente técnico de comunicación con la app. No hay que convertir la UI en una herramienta compleja todavía.

Además, hay una precisión arquitectónica importante: el FeatureScript debería encargarse de **capturar contexto/selecciones y enviar la definición del estudio**, mientras que la aplicación procesa la geometría y posteriormente devuelve el resultado para que Onshape pueda incorporarlo. La IA debe estudiar tu `ejemplo.txt` antes de escribir el FeatureScript y adaptar el patrón al proyecto.

Te dejo el prompt actualizado:

Trabaja sobre el proyecto existente de Topología Optimizada.

En esta etapa quiero mantener la interfaz gráfica MUY SIMPLE.

La interfaz NO debe convertirse todavía en una interfaz completa de optimización topológica.

Su función principal continúa siendo:

"Mostrar si la aplicación está funcionando y si está conectada correctamente con Onshape."

Además, ahora debemos incorporar un FeatureScript que permita establecer la comunicación entre Onshape y la aplicación.

==================================================

1. INTERFAZ GRÁFICA
   ==================================================

CONSERVAR EL CONCEPTO DE LA INTERFAZ ACTUAL.

No rediseñar la aplicación como un dashboard complejo.

Debe mostrar únicamente:

TOPOLOGÍA OPTIMIZADA

Estado de la aplicación:
● Aplicación iniciada

Estado de Onshape:
● Conectado / ○ No conectado

Usuario:
[usuario autenticado]

[ Conectar con Onshape ]

[ Desconectar ]

La interfaz debe seguir siendo:

* simple;
* limpia;
* profesional;
* compacta;
* responsive.

NO agregar todavía:

* selector de documentos;
* selector de workspace;
* selector de Part Studio;
* parámetros de optimización;
* cargas;
* restricciones;
* materiales;
* solver;
* mallado;
* resultados;
* configurador de estudios.

La interfaz gráfica de esta etapa NO es el lugar donde se configura la optimización.

==================================================
2. OAUTH 2.0
============

Mantener el sistema OAuth 2.0 que ya funciona.

No reemplazar una implementación funcional innecesariamente.

Verificar que continúe funcionando:

GET /login

GET /oauth/callback

El backend debe:

* mantener client_secret exclusivamente en servidor;
* almacenar los tokens de forma segura;
* validar state;
* renovar access_token cuando corresponda;
* validar realmente la conexión con Onshape.

El frontend nunca debe recibir:

* client_secret;
* access_token;
* refresh_token.

==================================================
3. FEATURESCRIPT
================

Ahora debes crear un FeatureScript específico para este proyecto.

ANTES DE ESCRIBIRLO:

En el proyecto se proporcionará un archivo:

`ejemplo.txt`

Este archivo contiene un ejemplo de FeatureScript/comunicación que debes estudiar.

IMPORTANTE:

NO copies el ejemplo literalmente.

Debes:

1. leer completamente `ejemplo.txt`;
2. identificar cómo funciona su comunicación;
3. identificar qué datos envía;
4. identificar cómo recibe resultados;
5. identificar qué mecanismos de Onshape utiliza;
6. determinar qué partes son reutilizables;
7. adaptar el concepto a la arquitectura actual de Topología Optimizada.

Si el ejemplo utiliza una técnica específica de comunicación, determina si es compatible con la arquitectura actual.

No inventes APIs de FeatureScript.

==================================================
4. RESPONSABILIDAD DEL FEATURESCRIPT
====================================

El FeatureScript NO será el lugar donde se ejecuta la optimización.

Su responsabilidad será actuar como puente entre:

ONSHAPE
↕
FEATURESCRIPT
↕
APLICACIÓN
↕
BACKEND / PROCESAMIENTO

El FeatureScript deberá poder:

* identificar el contexto actual;
* obtener las selecciones necesarias;
* recopilar los parámetros que posteriormente utilizará el proceso;
* enviar esos datos a la aplicación;
* recibir el resultado procesado;
* utilizar el mecanismo apropiado de Onshape para aplicar/devolver la geometría resultante.

No implementar todavía toda la interfaz de configuración del estudio si no es necesaria para esta etapa.

==================================================
5. COMUNICACIÓN FEATURESCRIPT → APLICACIÓN
==========================================

Diseñar una comunicación clara entre FeatureScript y el backend/aplicación.

El mensaje debe contener un esquema de datos estructurado.

Como mínimo debe existir un contexto:

{
documentId,
workspaceId,
elementId
}

Y una estructura preparada para:

{
selections,
parameters,
geometry,
operation
}

No es necesario implementar todavía todos los parámetros de optimización.

Pero la estructura debe ser extensible.

IMPORTANTE:

No utilizar datos hardcodeados.

No utilizar IDs ficticios.

No depender de que el usuario copie manualmente IDs.

==================================================
6. IDENTIFICACIÓN DE SELECCIONES
================================

El FeatureScript debe estar preparado para trabajar con las entidades seleccionadas dentro de Onshape.

Dependiendo del ejemplo proporcionado y de las capacidades reales de FeatureScript, estudiar cómo representar:

* cuerpos;
* caras;
* aristas;
* vértices.

La referencia debe mantenerse de forma que posteriormente el backend pueda identificar correctamente la geometría correspondiente.

No inventar identificadores de geometría.

==================================================
7. COMUNICACIÓN APLICACIÓN → FEATURESCRIPT
==========================================

La arquitectura debe permitir que, después del procesamiento, la aplicación pueda devolver información al entorno de Onshape.

El objetivo final será:

Onshape
↓
selección/configuración
↓
FeatureScript
↓
aplicación
↓
procesamiento
↓
pieza modificada
↓
Onshape

El resultado NO debe ser simplemente un archivo mostrado en la web.

Debe existir una estrategia real para devolver/incorporar la geometría modificada dentro del flujo de Onshape.

IMPORTANTE:

Investiga en la documentación/API real de Onshape cuál es el mecanismo correcto para conseguirlo.

NO inventes endpoints.

Si la incorporación directa de la geometría todavía requiere una etapa posterior, implementa primero la arquitectura de comunicación y documenta exactamente qué parte queda pendiente.

==================================================
8. FEATURESCRIPT COMO CUSTOM FEATURE
====================================

Siempre que sea compatible con el proyecto y con el ejemplo proporcionado, crear el FeatureScript como Custom Feature de Onshape.

Debe poder ser agregado al Feature List del Part Studio.

La experiencia buscada es que el usuario pueda permanecer dentro de Onshape.

No queremos que el usuario tenga que abrir manualmente la aplicación externa para operar el FeatureScript.

==================================================
9. BACKEND
==========

Crear/modificar los endpoints necesarios para recibir la comunicación del FeatureScript.

El backend debe:

* validar el request;
* validar el contexto;
* validar los datos recibidos;
* identificar la sesión;
* procesar la solicitud;
* devolver una respuesta estructurada.

No permitir que el FeatureScript controle directamente credenciales OAuth.

La autenticación con Onshape permanece en el backend.

==================================================
10. ESTADOS DE COMUNICACIÓN
===========================

La aplicación debe poder determinar si existe comunicación válida.

Estados posibles:

● Aplicación iniciada
● Onshape conectado
● FeatureScript conectado
● Solicitud recibida
● Procesando
● Resultado disponible
● Error

No es necesario mostrar todos estos estados permanentemente en la interfaz.

La interfaz principal debe seguir siendo simple.

Estos estados pueden existir internamente para debugging/logging.

==================================================
11. GEOMETRÍA
=============

NO simular geometría.

NO utilizar piezas aleatorias.

NO generar resultados ficticios.

Cuando el FeatureScript envíe información sobre la pieza:

* identificar qué datos reales recibe la aplicación;
* determinar cómo obtener la geometría real mediante Onshape API;
* utilizar esos datos para el procesamiento.

Si la extracción completa de geometría todavía no está implementada, no inventar el resultado.

Dejar claramente identificada esa etapa como pendiente.

==================================================
12. RESULTADO DE LA OPTIMIZACIÓN
================================

La arquitectura debe quedar preparada para:

FEATURESCRIPT
↓
DATOS DE PIEZA
↓
APLICACIÓN
↓
TOPOLOGÍA OPTIMIZADA
↓
PIEZA MODIFICADA
↓
FEATURESCRIPT / ONSHAPE

El objetivo final es que la pieza modificada pueda regresar a Onshape.

No crear un flujo donde el usuario tenga que descargar manualmente un archivo como solución definitiva.

==================================================
13. ARCHIVO ejemplo.txt
=======================

El archivo `ejemplo.txt` es una referencia técnica.

Debes leerlo antes de implementar el FeatureScript.

Después de analizarlo, documentar brevemente:

* mecanismo de comunicación utilizado;
* datos enviados;
* datos recibidos;
* qué partes se reutilizaron conceptualmente;
* qué partes no son compatibles con este proyecto;
* qué cambios fueron necesarios.

No copies código innecesariamente.

==================================================
14. PRUEBA MÍNIMA DE INTEGRACIÓN
================================

Antes de intentar ejecutar la optimización completa, conseguir primero esta prueba:

1. Abrir Onshape.
2. Abrir el Part Studio.
3. Ejecutar/agregar el Custom Feature.
4. Realizar una selección simple.
5. Ejecutar el FeatureScript.
6. El FeatureScript envía los datos a la aplicación.
7. El backend recibe la solicitud.
8. El backend registra correctamente:

   * documentId;
   * workspaceId;
   * elementId;
   * selección;
   * datos enviados.
9. La aplicación responde correctamente.
10. El FeatureScript recibe la respuesta.
11. Confirmar que la comunicación funciona.

SOLO después de conseguir esta prueba debe avanzarse hacia el procesamiento real de geometría.

==================================================
15. NO MODIFICAR INNECESARIAMENTE LA UI
=======================================

Este punto es MUY IMPORTANTE.

No agregues a la interfaz externa:

* paneles de selección;
* configuradores;
* formularios;
* árboles de documentos;
* parámetros de cargas;
* materiales;
* restricciones.

La interfaz externa solamente confirma:

"la aplicación está iniciada"

y

"está conectada con Onshape".

La interacción con el modelo debe ocurrir desde Onshape.

==================================================
16. AUDITORÍA FINAL
===================

Al terminar, verificar:

### Aplicación

[ ] Backend ejecuta correctamente
[ ] UI local funciona
[ ] OAuth funciona
[ ] Usuario autenticado
[ ] Desconexión funciona

### FeatureScript

[ ] Custom Feature creado
[ ] FeatureScript puede ejecutarse en Onshape
[ ] Puede capturar selección
[ ] Puede identificar contexto
[ ] Puede comunicarse con la aplicación
[ ] Puede recibir respuesta

### Comunicación

[ ] Onshape → FeatureScript
[ ] FeatureScript → Backend
[ ] Backend → FeatureScript
[ ] Manejo de errores

### Geometría

[ ] Se identifica correctamente la pieza
[ ] Se determina mecanismo real para obtener geometría
[ ] No existen mocks de geometría

### Resultado

[ ] Arquitectura preparada para devolver pieza modificada
[ ] No existen archivos ficticios
[ ] Las partes no implementadas están documentadas

Al finalizar indicar:

1. archivos creados;
2. archivos modificados;
3. archivos eliminados;
4. dependencias agregadas;
5. endpoints nuevos;
6. variables `.env`;
7. configuración necesaria en Onshape;
8. cómo instalar el FeatureScript;
9. cómo realizar la prueba mínima;
10. qué queda pendiente para implementar la optimización topológica real.

REGLA FUNDAMENTAL:

La UI externa debe permanecer SIMPLE.

La interacción con el CAD debe ocurrir DENTRO DE ONSHAPE.

FeatureScript funciona como puente de integración con el modelo, NO como motor de cálculo.

Python/FastAPI es responsable de la lógica pesada y procesamiento.

No inventes capacidades de Onshape: si una operación no es posible exactamente como se solicita, investiga la alternativa oficial y documenta la solución.
