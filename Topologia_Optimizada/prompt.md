ACTÚA COMO PROGRAMADOR SENIOR Y ARQUITECTO DE SOFTWARE ESPECIALIZADO EN PYTHON, FASTAPI, JAVASCRIPT/WEBGL, APIs CAD Y ONSHAPE.

Trabaja DIRECTAMENTE sobre el proyecto existente de Topología Optimizada.

NO desarrolles un proyecto desde cero.

Tu objetivo es AUDITAR, CORREGIR, REESTRUCTURAR Y MEJORAR el proyecto existente para convertirlo en una aplicación funcional de optimización topológica integrada con Onshape.

IMPORTANTE:
Antes de modificar cualquier archivo:

1. Lee y analiza TODO el repositorio.
2. Lee completamente `ejemplo.txt`.
3. Revisa la implementación actual de OAuth.
4. Revisa el backend FastAPI.
5. Revisa el frontend.
6. Revisa cualquier FeatureScript existente.
7. Revisa cómo se obtiene actualmente la geometría.
8. Revisa el solver TopOpt existente.
9. Revisa la generación de malla.
10. Revisa cómo se pretende devolver actualmente la geometría a Onshape.
11. Identifica mocks, datos aleatorios, placeholders, funciones incompletas y código que simule funcionalidades reales.
12. Verifica las APIs de Onshape utilizadas contra la documentación oficial actual antes de implementar cambios.

NO asumas que una API, endpoint, evento o función existe. Si no existe, busca la alternativa oficial correcta.

==================================================
1. NUEVA ARQUITECTURA DEFINITIVA
==================================================

CAMBIA EL ENFOQUE DEL PROYECTO.

La aplicación NO debe intentar realizar la optimización directamente dentro de Onshape.

Onshape será principalmente el entorno CAD de origen y destino.

La aplicación externa será el entorno principal de trabajo y tendrá la interfaz más completa.

La arquitectura será:

ONS HAPE
    │
    │
    ▼
APP INTEGRADA EN ONSHAPE
"SELECTOR DE GEOMETRÍA"
    │
    │ IDs + contexto
    ▼
BACKEND PYTHON / FASTAPI
    │
    ├── Obtención de geometría
    ├── Preparación geométrica
    ├── Mallado
    ├── FEA
    └── TopOpt
    │
    ▼
APP EXTERNA PRINCIPAL
"ENTORNO DE DISEÑO"
    │
    ├── Visor 3D CAD
    ├── Configuración de fuerzas
    ├── Fijaciones
    ├── Restricciones
    ├── Material
    ├── Optimización
    └── Previsualización
    │
    ▼
BACKEND
    │
    ▼
RESULTADO FINAL
    │
    ▼
ONSHAPE REST API
    │
    ▼
PIEZA OPTIMIZADA EN ONSHAPE

==================================================
2. PRINCIPIO FUNDAMENTAL
==================================================

La aplicación integrada dentro de Onshape NO será el configurador de TopOpt.

Su función será únicamente seleccionar geometría y enviar el contexto a la aplicación principal.

La aplicación integrada debe permitir seleccionar como mínimo:

- pieza/sólido a optimizar;
- piezas que actúan como obstáculos / Keep-out.

Debe poder obtener:

- documentId;
- workspaceId;
- elementId;
- identificadores de las piezas seleccionadas;
- identificadores de caras o entidades cuando sean necesarios.

NO colocar en esta interfaz:

- solver;
- parámetros de fuerzas;
- materiales;
- porcentaje de optimización;
- configuración avanzada;
- mallado;
- parámetros FEA;
- visor 3D avanzado.

La interfaz integrada debe ser simple.

==================================================
3. FEATURESCIPT
==================================================

NO considerar FeatureScript como canal de comunicación con el backend.

FeatureScript es un lenguaje determinista que se ejecuta en un sandbox aislado de Onshape.

NO tiene acceso a:

- HTTP;
- sockets;
- Internet;
- Python;
- C++;
- librerías externas;
- TopOpt externo.

Por lo tanto:

PROHIBIDO:

FeatureScript → HTTP → FastAPI

PROHIBIDO:

FeatureScript → Python

PROHIBIDO:

FeatureScript → Socket

Si existe actualmente código que intente realizar esto, eliminarlo o desactivarlo correctamente.

Si FeatureScript deja de ser necesario debido a la nueva arquitectura, NO lo mantengas artificialmente.

Antes de eliminarlo, determina si alguna parte del proyecto realmente depende de él.

==================================================
4. APP INTEGRADA EN ONSHAPE
==================================================

La App integrada debe funcionar como un "Selector de Geometría".

El flujo será:

Usuario abre App
↓
Selecciona pieza a optimizar
↓
Selecciona opcionalmente piezas Keep-out
↓
Confirma selección
↓
La aplicación obtiene los IDs reales
↓
Envía el contexto al backend
↓
Backend obtiene la geometría
↓
Se abre/continúa el entorno principal de optimización

La selección debe utilizar los mecanismos oficiales disponibles para Apps/Extensions de Onshape.

NO inventar eventos.

Investigar el SDK/API oficial actual de Onshape para determinar cómo capturar correctamente las selecciones.

==================================================
5. APLICACIÓN EXTERNA PRINCIPAL
==================================================

Esta aplicación será el componente principal del proyecto.

Debe tener una interfaz gráfica profesional orientada a CAD / diseño generativo.

NO debe parecer simplemente un formulario web.

La pieza debe visualizarse en un visor 3D interactivo.

El usuario debe poder:

- orbitar alrededor de la pieza;
- rotar;
- hacer zoom;
- hacer pan;
- cambiar el ángulo de cámara;
- inspeccionar todos los lados;
- ocultar/mostrar geometrías;
- visualizar obstáculos;
- visualizar fijaciones;
- visualizar fuerzas;
- visualizar el resultado optimizado;
- comparar geometría original y optimizada.

El visor debe ser realmente interactivo.

NO utilizar una imagen estática.

Utilizar una tecnología apropiada como:

- Three.js;
- Babylon.js;
- WebGL/WebGPU;
- u otra tecnología adecuada.

Primero audita el proyecto y reutiliza la tecnología existente si es razonable.

==================================================
6. VISUALIZACIÓN TIPO CAD
==================================================

La experiencia debe acercarse a un visor CAD.

El usuario debe poder inspeccionar la pieza libremente.

La geometría original debe poder distinguirse de:

- obstáculos;
- zonas de fijación;
- zonas protegidas;
- resultado optimizado.

Las cargas deben visualizarse gráficamente.

Por ejemplo:

Fuerza ↓
    ↓
    ↓
┌───────────┐
│   PIEZA   │
└───────────┘
████████████
 FIJACIÓN

No utilizar únicamente números en formularios.

Las condiciones físicas deben poder verse sobre el modelo 3D.

==================================================
7. GEOMETRÍA REAL
==================================================

Eliminar cualquier implementación que utilice:

- geometría aleatoria;
- geometría ficticia;
- STEP ficticio;
- malla aleatoria;
- resultados aleatorios;
- fuerzas simuladas;
- soportes simulados.

La geometría debe provenir del documento real de Onshape.

Audita la API oficial actual para determinar el mecanismo correcto para obtener:

- geometría;
- topología;
- teselación;
- STEP;
- STL;
- Parasolid u otro formato disponible.

No asumir que Parasolid está disponible si la API actual no lo permite.

Elegir el formato que sea realmente viable para el solver.

Documentar la decisión.

==================================================
8. BACKEND PYTHON
==================================================

Mantener FastAPI si ya existe.

No crear múltiples backends innecesarios.

El backend será responsable de:

- autenticación;
- contexto;
- descarga de geometría;
- preparación geométrica;
- mallado;
- análisis FEA;
- ejecución TopOpt;
- generación del resultado;
- comunicación con Onshape.

La aplicación frontend nunca debe ejecutar el solver pesado directamente.

==================================================
9. AUDITORÍA DEL SOLVER TOPOPT
==================================================

ESTO ES OBLIGATORIO.

Antes de diseñar definitivamente la interfaz de fuerzas y restricciones, analiza exactamente qué librería/solver TopOpt utiliza actualmente el proyecto.

Determina:

- qué tipo de problema resuelve;
- qué entradas necesita;
- qué tipo de cargas acepta;
- qué condiciones de frontera acepta;
- qué materiales acepta;
- qué algoritmo utiliza;
- qué parámetros necesita;
- qué devuelve;
- qué limitaciones tiene.

NO agregues controles en la interfaz que luego no puedan utilizarse realmente.

Si el solver actual NO soporta directamente una funcionalidad:

NO simularla.

Indicar:

"NO SOPORTADO ACTUALMENTE POR EL SOLVER"

y diseñar la arquitectura para permitir agregarla posteriormente.

==================================================
10. FUERZAS Y CARGAS
==================================================

Las fuerzas son una funcionalidad FUNDAMENTAL de la aplicación.

La aplicación debe permitir definir condiciones de carga reales compatibles con el solver.

Como mínimo evaluar soporte para:

- magnitud;
- dirección;
- sentido;
- punto o cara de aplicación;
- múltiples fuerzas;
- fijaciones;
- restricciones de movimiento.

Evaluar también si el solver puede soportar:

- momentos;
- torques;
- cargas distribuidas;
- presión;
- gravedad.

NO implementar estos tipos automáticamente.

Primero verifica si el solver actual los soporta.

Cuando una fuerza sea definida, debe representarse visualmente en el visor 3D.

Por ejemplo mediante vectores/flechas.

El usuario debe poder comprender visualmente:

- dónde actúa;
- hacia dónde apunta;
- qué magnitud tiene.

==================================================
11. CONDICIONES DE FRONTERA
==================================================

Separar claramente:

CARGAS

de

RESTRICCIONES / FIJACIONES.

Una fijación no es una fuerza.

El usuario debe poder seleccionar las zonas donde el modelo queda restringido.

Ejemplo:

- cara fija;
- desplazamiento bloqueado;
- soporte;
- etc.

Utilizar solamente condiciones realmente soportadas por el solver.

==================================================
12. OPTIMIZACIÓN
==================================================

La interfaz debe permitir configurar el objetivo de optimización.

Como mínimo evaluar:

- porcentaje de reducción de volumen;
- volumen objetivo;
- número de iteraciones;
- tolerancia;
- parámetros específicos del algoritmo TopOpt.

No agregar parámetros que el solver no utilice.

El porcentaje debe tener efecto real sobre el cálculo.

Por ejemplo:

0 % → conservar geometría original

50 % → objetivo de aproximadamente 50 % de reducción de volumen

80 % → objetivo de aproximadamente 80 %

Si el solver interpreta este parámetro de otra forma, utilizar la interpretación correcta y explicarla en la interfaz.

==================================================
13. PREVISUALIZACIÓN EN TIEMPO REAL
==================================================

La aplicación externa debe permitir modificar parámetros y observar el resultado.

Flujo:

Modificar fuerza
↓
Backend
↓
TopOpt / FEA
↓
Preview
↓
Visor 3D

Modificar porcentaje
↓
Backend
↓
Preview actualizado

Modificar restricción
↓
Backend
↓
Preview actualizado

NO es necesario recalcular exactamente con cada pulsación de teclado.

Implementar:

- debounce;
- cancelación;
- requestId;
- control de respuestas antiguas.

Una respuesta antigua nunca puede sobrescribir una respuesta nueva.

==================================================
14. PREVIEW VS RESULTADO FINAL
==================================================

Separar:

PREVIEW

Debe priorizar velocidad.

Puede utilizar:

- menor resolución;
- menos iteraciones;
- malla simplificada;
- aproximaciones controladas.

RESULTADO FINAL

Debe priorizar precisión.

Debe ejecutar el cálculo completo.

La interfaz debe distinguir ambos estados.

==================================================
15. MATERIAL
==================================================

La biblioteca de materiales NO es obligatoria para el MVP inicial.

Sin embargo, la arquitectura DEBE quedar preparada para incorporarla posteriormente.

No crear una implementación innecesariamente compleja si el solver actual no la necesita todavía.

Diseñar el modelo de datos para permitir:

Material
├── nombre
├── módulo de Young
├── coeficiente de Poisson
├── densidad
├── límite elástico
├── resistencia
└── propiedades adicionales

Preparar la posibilidad de:

1. Biblioteca integrada de materiales.
2. Materiales personalizados creados por el usuario.
3. Edición de materiales.
4. Guardado local.
5. Selección de material para el solver.

Ejemplo futuro:

Material:
[ Acero ]

Módulo de Young:
[...]

Poisson:
[...]

Densidad:
[...]

[ Crear material personalizado ]

NO implementar propiedades que el solver no utilice.

La biblioteca debe ser extensible.

==================================================
16. MODELO DE DATOS
==================================================

Diseñar una estructura capaz de representar:

GEOMETRÍA

- pieza;
- obstáculos;
- caras;
- regiones.

CONDICIONES FÍSICAS

- fuerzas;
- fijaciones;
- restricciones.

OPTIMIZACIÓN

- volumen objetivo;
- porcentaje;
- iteraciones;
- parámetros TopOpt.

MATERIAL

- material seleccionado;
- propiedades.

CONTEXTO

- documentId;
- workspaceId;
- elementId;
- partId.

==================================================
17. PAYLOAD
==================================================

Utilizar una estructura equivalente a:

{
  "contexto": {
    "documentId": "...",
    "workspaceId": "...",
    "elementId": "..."
  },
  "geometria": {
    "designSpace": [],
    "keepOut": []
  },
  "cargas": [],
  "restricciones": [],
  "optimizacion": {
    "porcentaje": 50
  },
  "material": null
}

Los campos pueden evolucionar según el proyecto.

Validar estrictamente el payload.

No aceptar datos arbitrarios.

==================================================
18. VISOR 3D
==================================================

El visor debe ser un componente central de la aplicación.

Debe permitir:

- orbit;
- zoom;
- pan;
- selección;
- ocultar/mostrar;
- reset de cámara;
- ajuste automático a la pieza.

Debe permitir representar diferentes estados:

PIEZA ORIGINAL

KEEP-OUT

KEEP-IN

FIJACIONES

FUERZAS

RESULTADO OPTIMIZADO

Idealmente utilizar diferentes representaciones visuales para distinguirlos.

No hardcodear colores sin necesidad; utilizar una arquitectura de estilos configurable.

==================================================
19. INTERFAZ DE USUARIO
==================================================

La aplicación externa debe tener una interfaz profesional.

No convertirla en una lista interminable de campos.

Organizar la configuración por categorías:

GEOMETRÍA

CARGAS

RESTRICCIONES

MATERIAL

OPTIMIZACIÓN

RESULTADO

El visor debe ocupar la mayor parte de la pantalla.

Los paneles de configuración deben acompañarlo.

La aplicación debe ser usable con piezas complejas.

==================================================
20. ESTADOS DE LA APLICACIÓN
==================================================

Implementar estados claros:

READY

GEOMETRY_LOADING

GEOMETRY_READY

MESHING

READY_FOR_ANALYSIS

PREVIEW_PROCESSING

PREVIEW_READY

FINAL_PROCESSING

FINAL_READY

ERROR

Mostrar estados comprensibles al usuario.

Ejemplos:

"Preparando geometría..."

"Generando malla..."

"Preparado para calcular"

"Generando previsualización..."

"Previsualización actualizada"

"Calculando resultado final..."

"Resultado listo"

"Error de cálculo"

==================================================
21. ONSHAPE → APP
==================================================

La aplicación integrada envía:

- contexto;
- pieza;
- obstáculos;
- referencias necesarias.

El backend obtiene la geometría real.

No transferir geometría mediante métodos inseguros o improvisados.

==================================================
22. APP → ONSHAPE
==================================================

El botón:

[ ACEPTAR ]

debe representar una operación explícita.

Al pulsarlo:

1. validar que existe un resultado final;
2. validar que el cálculo terminó correctamente;
3. enviar el resultado al backend;
4. utilizar la API oficial de Onshape;
5. crear/importar/actualizar el resultado dentro del documento;
6. informar al usuario del resultado.

NO modificar Onshape mientras el usuario solamente está probando previews, salvo que la API y la arquitectura hagan necesario algún mecanismo temporal.

El objetivo es que el resultado definitivo vuelva a Onshape solamente cuando el usuario pulse:

[ ACEPTAR ]

==================================================
23. API DE ONSHAPE
==================================================

AUDITAR LA DOCUMENTACIÓN OFICIAL ACTUAL DE ONSHAPE.

Verificar específicamente:

- OAuth;
- Apps;
- iframe;
- JavaScript SDK;
- selección;
- contexto;
- exportación de geometría;
- importación;
- Blob Elements;
- Part Studio;
- actualización de documentos;
- creación de elementos;
- ejecución de Features;
- cualquier mecanismo necesario para devolver el resultado.

NO inventar endpoints.

NO asumir que una API de escritura puede modificar arbitrariamente una geometría existente.

Si Onshape no permite una operación concreta:

marcarla como:

LIMITACIÓN DE ONSHAPE

y proponer la alternativa oficial más cercana.

==================================================
24. OAUTH
==================================================

Conservar el OAuth 2.0 actual si funciona.

No romperlo.

Mantener:

- Client ID;
- Client Secret solamente en backend;
- access token;
- refresh token;
- renovación;
- persistencia;
- scopes.

Auditar los scopes necesarios.

==================================================
25. SEGURIDAD
==================================================

Implementar:

- validación estricta de mensajes;
- validación de origen;
- CORS limitado;
- HTTPS;
- validación de payload;
- OAuth;
- secretos en .env;
- ningún secreto hardcodeado.

==================================================
26. PERSISTENCIA
==================================================

Conservar la persistencia existente si es adecuada.

Si falta:

usar SQLite inicialmente.

Preparar estructuras para:

- sesión;
- contexto;
- configuraciones;
- jobs;
- resultados;
- materiales personalizados futuros.

==================================================
27. ELIMINAR CÓDIGO FICTICIO
==================================================

Eliminar o sustituir:

- datos aleatorios;
- geometría aleatoria;
- solver simulado;
- fuerzas ficticias;
- soportes ficticios;
- STEP falso;
- resultados falsos;
- mocks utilizados como si fueran funcionalidades reales.

Los mocks solamente pueden mantenerse para pruebas claramente identificadas.

==================================================
28. EJECUCIÓN DE CÁLCULOS
==================================================

No bloquear innecesariamente el servidor.

Evaluar:

- BackgroundTasks;
- workers;
- cola de trabajos;
- WebSocket;
- Server-Sent Events;
- polling.

Elegir la solución apropiada para el proyecto.

La interfaz debe poder conocer:

- progreso;
- estado;
- errores;
- resultado.

==================================================
29. ARQUITECTURA DEL RESULTADO
==================================================

El resultado de TopOpt puede ser:

- malla;
- superficie;
- sólido reconstruido.

Determinar qué genera actualmente el solver.

Si el solver produce una malla pero Onshape necesita una geometría CAD adecuada:

documentar la etapa necesaria de reconstrucción.

NO afirmar que una malla es automáticamente un sólido CAD.

Separar:

RESULTADO DEL SOLVER

de

GEOMETRÍA CAD FINAL.

==================================================
30. AUDITORÍA DEL REPOSITORIO
==================================================

Antes de modificar:

crear mentalmente una matriz:

ARCHIVO
FUNCIÓN ACTUAL
ESTADO
PROBLEMA
ACCIÓN

Clasificar:

COMPLETO

PARCIAL

PENDIENTE

OBSOLETO

LIMITACIÓN EXTERNA

No reescribir archivos que ya funcionen correctamente.

==================================================
31. ORDEN DE IMPLEMENTACIÓN
==================================================

Implementar en este orden:

ETAPA 1
Auditoría completa.

ETAPA 2
Arquitectura Onshape Selector.

ETAPA 3
Captura real de selección.

ETAPA 4
Obtención real de geometría.

ETAPA 5
Visor 3D.

ETAPA 6
Preparación de malla.

ETAPA 7
Auditoría/integración real del solver TopOpt.

ETAPA 8
Restricciones y fijacio