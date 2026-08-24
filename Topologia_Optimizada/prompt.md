ACTÚA COMO PROGRAMADOR SENIOR, ARQUITECTO DE SOFTWARE Y ESPECIALISTA EN INTEGRACIONES CAD, ONSHAPE API, PYTHON, FASTAPI, JAVASCRIPT, WEBGL/THREE.JS, FEA Y OPTIMIZACIÓN TOPOLÓGICA.

TRABAJA DIRECTAMENTE SOBRE EL REPOSITORIO EXISTENTE.

NO CREES UN PROYECTO NUEVO DESDE CERO.

==================================================
CONTEXTO DEL PROYECTO
==================================================

El proyecto es una aplicación de optimización topológica integrada con Onshape.

Repositorio:

Onshape/
└── Topologia_Optimizada/

El proyecto YA tiene una cantidad importante de infraestructura funcional.

NO debes reconstruirla innecesariamente.

Durante la auditoría inicial identificamos que ya existen, entre otros:

- OAuth 2.0;
- cliente de Onshape;
- FastAPI;
- persistencia SQLite;
- modelos Pydantic;
- manejo de tokens;
- refresh token;
- retry HTTP;
- descarga de STEP;
- base de visor Three.js;
- modelos de fuerzas;
- modelos de restricciones;
- modelos de materiales;
- configuración TopOpt;
- App Extension;
- aplicación externa.

Tu trabajo consiste en:

AUDITAR → CORREGIR → COMPLETAR → INTEGRAR → VALIDAR.

No asumir que una funcionalidad está completa solamente porque exista:

- una interfaz;
- un endpoint;
- un modelo Pydantic;
- una función;
- un comentario;
- un mock;
- una documentación que diga que está implementada.

Una funcionalidad solamente se considera COMPLETA cuando los datos reales atraviesan todo el flujo y producen el resultado esperado.

==================================================
1. PRIMER PASO OBLIGATORIO: AUDITORÍA
==================================================

ANTES DE MODIFICAR CUALQUIER ARCHIVO:

1. Lee TODO el repositorio.
2. Lee `ejemplo.txt`.
3. Lee la documentación existente.
4. Audita `api_server.py`.
5. Audita `onshape_client.py`.
6. Audita `geometry_processor.py`.
7. Audita `topopt_solver.py`.
8. Audita `optimization-app.html`.
9. Audita `app-extension.html`.
10. Audita todos los modelos de datos.
11. Audita dependencias.
12. Audita configuración OAuth.
13. Audita persistencia.
14. Audita el flujo de geometría.
15. Audita fuerzas y restricciones.
16. Audita materiales.
17. Audita el flujo de resultados.
18. Identifica código obsoleto relacionado con FeatureScript.
19. Identifica mocks, placeholders y datos ficticios.

Crear internamente una matriz:

ARCHIVO
FUNCIÓN
ESTADO
PROBLEMA
ACCIÓN

Clasificar cada componente como:

- COMPLETO
- PARCIAL
- PENDIENTE
- OBSOLETO
- LIMITACIÓN EXTERNA

NO modificar código antes de completar esta auditoría.

==================================================
2. ARQUITECTURA DEFINITIVA
==================================================

La arquitectura debe quedar dividida en tres componentes principales:

A. ONSHAPE + APP EXTENSION
B. APP EXTERNA PRINCIPAL
C. BACKEND PYTHON

Flujo:

ONS HAPE
   ↓
APP EXTENSION
   ↓
SELECCIÓN DE GEOMETRÍA
   ↓
BACKEND PYTHON
   ↓
GEOMETRÍA REAL
   ↓
APP EXTERNA
   ↓
CONFIGURACIÓN FÍSICA
   ↓
FEA + TOPOPT
   ↓
PREVIEW
   ↓
RESULTADO FINAL
   ↓
ONSHAPE API
   ↓
PIEZA OPTIMIZADA

La aplicación externa será la interfaz PRINCIPAL y MÁS POTENTE.

La App Extension dentro de Onshape será deliberadamente simple.

==================================================
3. DECISIÓN SOBRE FEATURESCRIPT
==================================================

FeatureScript NO forma parte de la nueva arquitectura de comunicación.

FeatureScript no puede realizar:

- HTTP;
- sockets;
- acceso a Internet;
- comunicación directa con Python;
- comunicación directa con FastAPI;
- ejecución de librerías externas;
- ejecución del solver externo.

PROHIBIDO utilizar FeatureScript como puente de comunicación.

NO eliminarlo inmediatamente.

Primero audita todos los FeatureScript existentes.

Determina:

1. Para qué sirven.
2. Qué archivos dependen de ellos.
3. Qué funciones proporcionan.
4. Si alguna función sigue siendo necesaria.
5. Si puede reemplazarse mediante App Extension + SDK + API oficial.

Después:

SI NO ES NECESARIO:
→ ELIMINAR FEATURESCRIPT DEL PROYECTO Y DEL FLUJO.

SI EXISTE UNA FUNCIÓN NATIVA DE ONSHAPE QUE SIGA SIENDO NECESARIA:
→ CONSERVARLO únicamente para esa función.

SI DEBE MODIFICARSE:
→ REDISEÑARLO exclusivamente para operaciones nativas de Onshape.

EN NINGÚN CASO:
FeatureScript → Backend.

La opción preferida es eliminarlo si la arquitectura funciona correctamente sin él.

==================================================
4. APP EXTENSION DE ONSHAPE
==================================================

NO crear una nueva App Extension.

EVOLUCIONAR LA EXISTENTE.

La App Extension actual debe convertirse en un:

"SELECTOR DE GEOMETRÍA"

Debe conservar:

- OAuth;
- estado de conexión;
- integración existente;
- componentes funcionales.

Debe eliminar la dependencia de introducción manual de:

- documentId;
- workspaceId;
- elementId;

cuando estos datos puedan obtenerse directamente del contexto de Onshape.

La interfaz debe ser simple.

Debe permitir:

1. Mostrar estado de aplicación.
2. Mostrar conexión real con Onshape.
3. Seleccionar el sólido/pieza a optimizar.
4. Seleccionar uno o varios sólidos Keep-out.
5. Mostrar las selecciones realizadas.
6. Confirmar selección.
7. Enviar contexto al backend.

NO agregar:

- solver;
- fuerzas;
- materiales;
- mallado;
- FEA;
- parámetros avanzados;
- porcentaje de optimización;
- visor 3D principal.

La App Extension solamente captura:

GEOMETRÍA + CONTEXTO.

==================================================
5. SELECCIÓN REAL DE ONSHAPE
==================================================

La selección debe utilizar mecanismos oficiales de Onshape.

NO asumir que los eventos actuales del proyecto son eventos oficiales.

Auditar la implementación actual.

Consultar la documentación oficial actual de Onshape para determinar:

- SDK correcto;
- API correcta;
- mecanismo de selección;
- contexto;
- documentId;
- workspaceId;
- elementId;
- partId;
- faceId.

Si la API actual no permite una determinada operación:

NO inventarla.

Documentar la limitación.

La selección debe entregar IDs reales.

No aceptar IDs ficticios escritos manualmente como flujo principal.

==================================================
6. APP EXTERNA: FUNCIÓN PRINCIPAL
==================================================

La aplicación externa será el entorno principal de trabajo.

Debe evolucionar el archivo existente:

`optimization-app.html`

NO crear una aplicación paralela si la existente puede evolucionarse.

Debe convertirse en una interfaz tipo CAD / diseño generativo.

El visor 3D será el elemento central.

==================================================
7. VISOR 3D
==================================================

Actualmente existe una base Three.js.

CONSERVARLA.

NO empezar nuevamente desde cero.

Eliminar:

- BoxGeometry de demostración;
- geometría ficticia;
- "Geometría de ejemplo";
- geometría optimizada simulada;
- resultados falsos.

El visor debe mostrar geometría REAL obtenida de Onshape.

Debe permitir:

- orbit;
- zoom;
- pan;
- rotación;
- inspección completa;
- reset de cámara;
- fit-to-object;
- ocultar/mostrar geometrías;
- selección cuando corresponda.

La experiencia debe parecerse a un visor CAD.

El usuario debe poder moverse alrededor de la pieza libremente.

==================================================
8. GEOMETRÍA REAL
==================================================

Actualmente el backend tiene capacidad de descarga de STEP.

Auditarla y conservarla si funciona.

El flujo debe quedar:

ONSHAPE
↓
GEOMETRÍA REAL
↓
STEP / GLTF / STL / otro formato apropiado
↓
BACKEND
↓
VISOR 3D

Determinar cuál es el formato más adecuado para:

1. visualización;
2. FEA;
3. TopOpt;
4. reconstrucción.

Consultar documentación oficial de Onshape.

No asumir que Parasolid está disponible.

No asumir que un STL sirve para todas las etapas.

Si conviene utilizar diferentes representaciones:

VISUALIZACIÓN:
GLTF/STL/teselación apropiada.

CÁLCULO:
STEP/B-Rep/u otro formato adecuado.

No duplicar innecesariamente los datos.

==================================================
9. LOGIN DESDE LA APP EXTERNA
==================================================

La aplicación externa debe poder iniciar el flujo OAuth.

Cuando el usuario abra la aplicación externa y NO exista una sesión válida:

mostrar:

"Conectá tu cuenta de Onshape para comenzar"

[ INICIAR SESIÓN CON ONSHAPE ]

El botón debe utilizar:

GET /login

y el backend debe realizar el OAuth 2.0 real.

Después de autenticarse:

Onshape
↓
/oauth/callback
↓
authorization code
↓
token exchange
↓
access_token
+
refresh_token
↓
validación real contra Onshape
↓
APP EXTERNA

Mostrar:

"Conectado a Onshape como: [usuario]"

No considerar que está conectado simplemente porque existe un token almacenado.

Validar siempre que el token funciona.

==================================================
10. SESIÓN OAUTH
==================================================

Conservar el OAuth existente si funciona.

Mantener:

- authorization code;
- access token;
- refresh token;
- expiración;
- refresh automático;
- state CSRF;
- almacenamiento seguro.

El frontend nunca debe recibir:

- client_secret;
- refresh_token.

No hardcodear secretos.

==================================================
11. FUTURA INSTALACIÓN AUTOMÁTICA
==================================================

NO implementar todavía la instalación automática de la App Extension.

Sin embargo, diseñar la arquitectura para permitirla posteriormente.

En el futuro queremos poder detectar:

"El usuario está autenticado pero todavía no tiene instalada la App Extension."

Y eventualmente mostrar:

[ AGREGAR APP A ONSHAPE ]

Pero actualmente:

NO IMPLEMENTAR.

Solamente:

- documentar el punto de integración;
- dejar la arquitectura preparada;
- investigar si Onshape ofrece API oficial para esta operación;
- NO inventar mecanismos.

==================================================
12. FLUJO PRINCIPAL
==================================================

El flujo debe ser:

1. Usuario abre la aplicación externa.
2. Backend comprueba sesión.
3. Si no existe:
   mostrar "Iniciar sesión con Onshape".
4. Usuario inicia OAuth.
5. OAuth finaliza.
6. Validar token contra Onshape.
7. Mostrar usuario autenticado.
8. Usuario abre la App Extension dentro de Onshape.
9. Selecciona pieza.
10. Selecciona opcionalmente Keep-out.
11. Confirma.
12. App Extension envía contexto.
13. Backend obtiene geometría real.
14. Aplicación externa recibe geometría.
15. Visor muestra la pieza.
16. Usuario configura condiciones físicas.
17. Backend genera malla.
18. Se prepara FEA.
19. Se ejecuta TopOpt.
20. Se genera preview.
21. Usuario modifica parámetros.
22. Se vuelve a calcular.
23. Usuario acepta el resultado.
24. Backend genera resultado final.
25. Resultado se devuelve a Onshape.

==================================================
13. MODELO DE GEOMETRÍA
==================================================

Representar explícitamente:

DESIGN SPACE
→ pieza que será optimizada.

KEEP-OUT
→ geometría que no puede ser ocupada/removida.

KEEP-IN / REGIONES PROTEGIDAS
→ regiones que deben permanecer.

FIJACIONES
→ zonas estructuralmente restringidas.

CARGAS
→ zonas donde actúan fuerzas.

No mezclar estos conceptos.

==================================================
14. FUERZAS
==================================================

Las fuerzas son parte fundamental del proyecto.

El usuario debe poder configurar:

- magnitud;
- unidad;
- dirección;
- sentido;
- cara/punto de aplicación;
- múltiples cargas.

La interfaz debe mostrar las fuerzas sobre el modelo 3D.

Utilizar vectores/flechas.

Por ejemplo:

       ↓ 1000 N
       ↓
 ┌────────────┐
 │    PIEZA   │
 └────────────┘
 █████████████
    FIJACIÓN

Auditar exactamente qué tipos de carga admite el solver actual.

Evaluar:

- fuerza puntual;
- fuerza distribuida;
- presión;
- gravedad;
- momento;
- torque.

NO implementar automáticamente lo que el solver no soporte.

==================================================
15. RESTRICCIONES / FIJACIONES
==================================================

Separar:

FUERZAS

de

RESTRICCIONES.

Una restricción no es una fuerza.

Permitir configurar restricciones compatibles con el solver.

La aplicación debe poder asociar una restricción a una región de la geometría.

==================================================
16. MAPEO GEOMETRÍA → MALLA
==================================================

ESTE ES UNO DE LOS PUNTOS CRÍTICOS.

Debe existir un flujo real:

Onshape Face
↓
Geometría
↓
Malla
↓
Nodos / elementos correspondientes
↓
Condición FEA

No basta con almacenar un `faceId`.

El backend debe determinar qué nodos/elementos de la malla pertenecen a la región seleccionada.

Implementar esta etapa correctamente.

Si la tecnología de mallado seleccionada no permite realizarlo directamente:

buscar una estrategia viable.

No simularlo.

==================================================
17. MALLADO
==================================================

Actualmente el proyecto no tiene un mallador funcional integrado.

Implementar un pipeline real.

Evaluar herramientas como:

- Gmsh;
- Netgen;
- TetGen;
- otra alternativa apropiada.

Elegir en función de:

- compatibilidad;
- calidad;
- Python;
- geometría STEP;
- capacidad FEA;
- facilidad de instalación local.

No incorporar una dependencia sin justificarla.

La malla debe ser real.

No utilizar mallas aleatorias.

==================================================
18. FEA
==================================================

Actualmente `topopt_solver.py` espera un FEA solver real.

Implementar la integración real.

Auditar primero las opciones disponibles.

Evaluar librerías apropiadas para:

- elasticidad lineal;
- condiciones de frontera;
- cargas;
- cálculo de desplazamientos;
- tensiones;
- compliance.

No crear un solver ficticio.

No devolver resultados aleatorios.

Si la librería TopOpt actual requiere un FEA externo:

integrarlo correctamente.

==================================================
19. TOPOPT
==================================================

Auditar `topopt_solver.py`.

Determinar exactamente:

- algoritmo;
- entradas;
- salidas;
- parámetros;
- dependencia real;
- limitaciones.

Actualmente el solver requiere un FEA real.

No eliminar esa validación.

Completarla.

El resultado debe depender realmente de:

- geometría;
- malla;
- cargas;
- restricciones;
- material;
- objetivo.

==================================================
20. OPTIMIZACIÓN
==================================================

La aplicación debe permitir configurar:

- porcentaje de optimización / reducción de volumen;
- iteraciones;
- tolerancia;
- parámetros específicos del solver.

El porcentaje debe afectar realmente al cálculo.

No crear un control visual que no modifique el solver.

==================================================
21. PREVIEW
==================================================

Implementar previsualización real.

El usuario debe poder modificar:

- fuerzas;
- restricciones;
- optimización;
- otros parámetros compatibles.

y obtener un nuevo resultado.

Utilizar:

- debounce;
- requestId;
- cancelación de jobs;
- control de concurrencia.

Una respuesta antigua NO puede sobrescribir un resultado más reciente.

Separar:

PREVIEW

de

RESULTADO FINAL.

Preview:
prioridad = velocidad.

Resultado final:
prioridad = precisión.

==================================================
22. VISUALIZACIÓN DE RESULTADOS
==================================================

El visor debe poder alternar:

- original;
- resultado optimizado;
- comparación.

Debe mostrar:

- fuerzas;
- fijaciones;
- Keep-out;
- Keep-in;
- resultado.

Permitir ocultar/mostrar cada categoría.

==================================================
23. MATERIALES
==================================================

La biblioteca de materiales NO es obligatoria para la primera versión funcional.

Pero la arquitectura debe permitir incorporarla.

Conservar el modelo existente si es válido.

Preparar:

Material
├── nombre
├── módulo de Young
├── Poisson
├── densidad
├── límite elástico
└── propiedades adicionales

Debe ser posible posteriormente:

- utilizar materiales predeterminados;
- crear materiales personalizados;
- guardar materiales;
- editar materiales;
- seleccionarlos para el solver.

No implementar propiedades que el solver no utilice.

==================================================
24. PERSISTENCIA
==================================================

Conservar SQLite.

Utilizarla para:

- OAuth;
- sesiones;
- contexto;
- jobs;
- configuraciones;
- materiales futuros;
- resultados/metadatos.

No almacenar secretos innecesarios.

==================================================
25. BACKEND
==================================================

Conservar FastAPI.

No crear otro backend.

Auditar y mejorar:

- endpoints;
- modelos;
- validaciones;
- errores;
- jobs;
- estados;
- concurrencia.

Los cálculos pesados no deben bloquear el servidor.

Evaluar:

- BackgroundTasks;
- worker;
- cola;
- WebSocket;
- SSE;
- polling.

Elegir la solución adecuada.

==================================================
26. RESULTADO FINAL → ONSHAPE
==================================================

El botón:

[ ACEPTAR ]

debe ser el único paso que consolide el resultado.

Antes de aceptar:

NO modificar permanentemente el modelo CAD.

Al aceptar:

1. Validar resultado.
2. Validar que el cálculo final terminó.
3. Generar geometría final.
4. Determinar si es:
   - malla;
   - superficie;
   - sólido CAD.
5. Si es necesario, realizar reconstrucción.
6. Utilizar API oficial de Onshape.
7. Crear/importar el resultado.
8. Confirmar operación.
9. Informar al usuario.

NO afirmar que STL/mesh = sólido CAD automáticamente.

==================================================
27. RECONSTRUCCIÓN CAD
==================================================

Determinar qué produce realmente el solver.

Separar:

RESULTADO TOPOPT

de

GEOMETRÍA CAD FINAL.

Si el solver produce una densidad/malla:

implementar la etapa necesaria para obtener una representación apropiada.

Investigar las posibilidades reales de Onshape para importar el resultado.

No inventar APIs.

==================================================
28. MOCKS Y DATOS FICTICIOS
==================================================

Eliminar del flujo real:

- BoxGeometry;
- geometría ficticia;
- STEP ficticio;
- malla ficticia;
- fuerzas ficticias;
- restricciones ficticias;
- TopOpt simulado;
- resultado optimizado simulado.

Los mocks pueden existir ÚNICAMENTE para tests y deben estar claramente separados.

==================================================
29. DOCUMENTACIÓN DE ONSHAPE
==================================================

Consultar documentación oficial actual de Onshape.

Verificar:

- OAuth;
- Apps;
- App Extensions;
- JavaScript SDK;
- selección;
- contexto;
- exportación;
- GLTF;
- STL;
- STEP;
- Blob Elements;
- importación;
- Part Studio;
- creación de elementos;
- mecanismos para devolver geometría.

NO inventar endpoints.

Si existe una limitación:

DOCUMENTARLA.

==================================================
30. SEGURIDAD
==================================================

Implementar:

- OAuth real;
- state CSRF;
- secretos en `.env`;
- CORS restringido;
- validación de origen;
- validación Pydantic;
- validación de mensajes;
- HTTPS cuando corresponda.

El archivo `.env` debe ser LOCAL.

NO incluir secretos reales en el repositorio.

Conservar `.env.example`.

Si se detecta que alguna credencial real fue expuesta históricamente:

indicar que debe ser rotada.

==================================================
31. LIMPIEZA DEL REPOSITORIO
==================================================

Eliminar archivos obsoletos.

No conservar:

- código muerto;
- endpoints de FeatureScript innecesarios;
- mocks utilizados en producción;
- duplicaciones;
- dependencias no utilizadas.

NO borrar archivos funcionales sin comprobar dependencias.

