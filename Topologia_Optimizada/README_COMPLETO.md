Actúa como ingeniero senior especializado en Python, FastAPI, OAuth 2.0 y Onshape REST API.

Trabajarás sobre el proyecto EXISTENTE de Topología Optimizada.

El objetivo ha cambiado: debemos MIGRAR LA ARQUITECTURA ACTUAL para eliminar completamente la dependencia de FeatureScript y permitir que la aplicación local se conecte directamente con la cuenta de Onshape del usuario mediante OAuth 2.0.

NO reconstruyas la aplicación desde cero.

Primero inspecciona todo el proyecto existente, identifica qué componentes siguen dependiendo de FeatureScript/API Keys y determina qué debe conservarse, modificarse, eliminarse o reemplazarse.

IMPORTANTE:

- No asumas que los endpoints de Onshape indicados en este documento existen exactamente con esa forma.
- Verifica la API real de Onshape antes de implementar cada operación.
- Si una operación no puede realizarse mediante REST de la forma planteada, identifica el mecanismo correcto de Onshape y adapta la arquitectura.
- No inventes endpoints ni capacidades.
- No mantengas código legacy solamente por conservarlo si ya no tiene utilidad.
- Evita dependencias innecesarias.
- Mantén el proyecto ejecutable después de cada grupo importante de cambios.

OBJETIVO DE LA NUEVA ARQUITECTURA

La aplicación debe funcionar aproximadamente así:

USUARIO
↓
INTERFAZ LOCAL
↓
OAuth 2.0
↓
Onshape
↓
Backend Python/FastAPI
↓
REST API de Onshape
↓
Lectura de contexto/geometría
↓
Procesamiento Topología Optimizada
↓
Resultado
↓
Onshape mediante la API/mecanismo compatible

FeatureScript y App Extension dejan de ser componentes necesarios del flujo.

==================================================
FASE 1 — AUDITORÍA DEL PROYECTO

Antes de modificar archivos:

1. Inspecciona toda la estructura del proyecto.
2. Identifica:
   - archivos FeatureScript;
   - endpoints relacionados con FeatureScript;
   - llamadas httpPost;
   - autenticación mediante API Keys/HMAC;
   - frontend actual;
   - backend;
   - procesamiento geométrico;
   - solver;
   - persistencia;
   - tests;
   - configuración.
3. Determina las dependencias entre componentes.

Genera una matriz:

Componente| Estado| Dependencia FeatureScript| Acción
Backend| ...| ...| CONSERVAR/MODIFICAR/ELIMINAR
Frontend| ...| ...| ...
FeatureScript| ...| ...| ...
Auth| ...| ...| ...
Geometría| ...| ...| ...
Solver| ...| ...| ...
Persistencia| ...| ...| ...

No implementes cambios hasta terminar esta auditoría.

==================================================
FASE 2 — MIGRACIÓN DE AUTENTICACIÓN

Eliminar del flujo de usuario las API Keys, HMAC y cualquier dependencia de credenciales estáticas.

Implementar OAuth 2.0 real.

Debe existir:

GET /login

Este endpoint debe construir la URL oficial de autorización de Onshape utilizando:

https://oauth.onshape.com/oauth/authorize

con:

- client_id;
- redirect_uri;
- response_type=code;
- scopes necesarios;
- state seguro contra CSRF.

Implementar:

GET /oauth/callback

Debe:

- validar state;
- recibir authorization code;
- intercambiarlo server-to-server;
- utilizar:

https://oauth.onshape.com/oauth/token

- obtener access_token;
- obtener refresh_token si Onshape lo proporciona;
- guardar expiración;
- almacenar la sesión de forma segura.

Implementar una capa centralizada OAuth/OnshapeClient.

NINGÚN código del frontend debe conocer:

- client_secret;
- access_token;
- refresh_token.

==================================================
FASE 3 — REFRESH AUTOMÁTICO

Implementar una rutina centralizada para renovar tokens.

Debe:

- detectar expiración;
- detectar HTTP 401;
- utilizar refresh_token;
- actualizar access_token;
- actualizar expiración;
- repetir la petición original cuando sea seguro hacerlo.

Evitar múltiples refresh simultáneos para la misma sesión.

No duplicar esta lógica en cada endpoint.

==================================================
FASE 4 — ELIMINACIÓN DE FEATURESCRIPT

Eliminar del flujo funcional:

- master_topology_input.fs;
- httpPost provenientes de FeatureScript;
- endpoints creados exclusivamente para recibir datos desde FeatureScript;
- lógica de serialización cuyo único propósito sea comunicarse con FeatureScript;
- dependencia del contexto entregado por una App Extension.

IMPORTANTE:

No borres archivos inmediatamente si contienen lógica reutilizable.

Primero identifica qué funcionalidad puede reutilizarse y migra esa lógica al nuevo flujo.

Una vez que la nueva arquitectura funcione, elimina código legacy que ya no tenga utilidad.

==================================================
FASE 5 — CAPA DIRECTA DE ONSHAPE

Crear o reorganizar un cliente centralizado para Onshape.

Todas las peticiones REST autenticadas deben pasar por esta capa.

Utilizar:

Authorization: Bearer <access_token>

No permitir llamadas directas desde el frontend a la API de Onshape.

La capa debe centralizar:

- autenticación;
- refresh;
- headers;
- timeout;
- errores;
- rate limiting;
- logging;
- serialización.

Implementar manejo apropiado de:

- 400;
- 401;
- 403;
- 404;
- 409;
- 429;
- 5xx.

==================================================
FASE 6 — CONTEXTO CAD

La aplicación ya no recibe contexto automáticamente desde FeatureScript.

Implementar en la interfaz local un selector para:

- Documento (did);
- Workspace (wid);
- Elemento / Part Studio (eid).

El usuario debe poder consultar sus documentos disponibles mediante la API de Onshape y seleccionar el contexto de trabajo.

Guardar el último contexto seleccionado.

La aplicación debe mostrar claramente:

Conectado a Onshape como: [usuario]

y:

Documento: [...]
Workspace: [...]
Elemento: [...]

No utilizar IDs hardcodeados.

==================================================
FASE 7 — GEOMETRÍA

Auditar completamente "geometry_processor.py" y cualquier código relacionado.

Determinar exactamente qué geometría obtiene actualmente y qué partes son simuladas.

Implementar la adquisición directa de geometría mediante los mecanismos REALES disponibles en Onshape.

Evaluar las alternativas disponibles para:

- teselado;
- STL;
- STEP;
- exportación;
- información de Part Studio;
- cuerpos/parts.

Elegir el formato más apropiado para el pipeline existente.

NO utilizar geometría aleatoria como sustituto silencioso de geometría real.

Si alguna etapa todavía no puede procesarse realmente:

- dejarla explícitamente identificada;
- devolver un estado correcto;
- no presentar datos ficticios como resultados reales.

==================================================
FASE 8 — ESCRITURA DE RESULTADOS

Auditar cómo devuelve actualmente resultados el sistema.

Eliminar cualquier dependencia de:

Resultado → FeatureScript → Onshape

Investigar el mecanismo REAL de Onshape que permita escribir/importar/actualizar el resultado.

Puede ser mediante:

- importación de geometría;
- creación de elementos;
- Feature API;
- Feature Studios;
- u otro mecanismo soportado.

NO inventar endpoints.

Si la escritura directa del resultado topológico todavía no puede implementarse correctamente:

- no generar archivos falsos;
- mantener los resultados calculados;
- crear una interfaz limpia para la futura escritura;
- documentar exactamente qué API/mecanismo falta.

==================================================
FASE 9 — INTERFAZ LOCAL

Mover toda la configuración funcional a la interfaz local.

Debe permitir configurar como mínimo los parámetros que actualmente correspondan al proceso:

- material;
- tolerancias;
- ángulo de voladizo;
- parámetros de optimización;
- condiciones necesarias para el cálculo.

Eliminar la dependencia del panel FeatureScript.

La UI debe mostrar estados claros:

- Desconectado;
- Conectando;
- Conectado;
- Token renovado;
- Error de autenticación;
- Documento seleccionado;
- Procesando;
- Resultado disponible;
- Error.

==================================================
FASE 10 — PERSISTENCIA

Utilizar SQLite como almacenamiento local salvo que el proyecto ya tenga una alternativa claramente superior.

Persistir:

- sesión OAuth;
- access_token;
- refresh_token;
- expiración;
- usuario;
- último documento;
- último workspace;
- último elemento;
- configuración;
- jobs;
- resultados;
- errores.

Aplicar protección razonable a los secretos almacenados.

No almacenar credenciales en código fuente.

Crear ".env.example" sin secretos reales.

==================================================
FASE 11 — LICENCIAMIENTO

Crear una capa independiente para validar acceso:

validate_user_access()

o equivalente.

El cálculo principal NO debe conocer directamente cómo se valida el usuario.

Inicialmente puede utilizar una implementación local/simple.

La arquitectura debe permitir posteriormente reemplazarla por:

usuario → backend → base de datos → estado de licencia

sin modificar el núcleo del cálculo.

==================================================
FASE 12 — DEPENDENCIAS LEGACY

Después de implementar la nueva arquitectura, identificar:

- FeatureScript innecesario;
- App Extension innecesaria;
- API Keys;
- HMAC;
- endpoints legacy;
- payloads antiguos;
- variables de entorno obsoletas;
- dependencias Python obsoletas;
- código muerto.

Eliminar solamente aquello que realmente ya no sea utilizado.

Actualizar:

- pyproject.toml;
- documentación;
- tests;
- ".env.example".

==================================================
FASE 13 — TESTS

Actualizar y ampliar los tests.

Como mínimo verificar:

- /login;
- OAuth callback;
- state/CSRF;
- token exchange;
- refresh;
- HTTP 401;
- selección de contexto;
- consulta de documentos;
- consulta de elementos;
- adquisición de geometría;
- persistencia SQLite;
- jobs;
- validación de licencia;
- errores de API;
- rate limiting.

Los tests no deben depender de credenciales reales.

Usar mocks únicamente para pruebas automatizadas, nunca como sustituto silencioso de funcionalidad en producción.

==================================================
FASE 14 — AUDITORÍA FINAL

Al terminar, volver a auditar TODOS los requisitos de esta especificación.

Entregar:

Requisito| Estado final| Evidencia| Archivo(s)

Estados permitidos:

COMPLETO
PARCIAL
FALTANTE
NO APLICA
CONFIGURACIÓN EXTERNA

Para cualquier requisito PARCIAL o FALTANTE explicar exactamente por qué.

Además entregar:

1. Archivos eliminados.
2. Archivos creados.
3. Archivos modificados.
4. Dependencias agregadas/eliminadas.
5. Variables ".env" nuevas.
6. Configuración necesaria en Onshape Developer Portal.
7. Pasos para ejecutar localmente.
8. Limitaciones conocidas.
9. Funcionalidades que continúan siendo simuladas o pendientes.

REGLA FUNDAMENTAL:

No optimices para "marcar todos los checks".

Optimiza para que la aplicación tenga una arquitectura REAL, coherente y mantenible.

Nunca reemplaces una funcionalidad faltante con:

- datos aleatorios;
- mocks;
- placeholders;
- respuestas falsas;
- archivos ficticios.

Si algo no puede implementarse todavía mediante la API real de Onshape, dilo explícitamente y deja la arquitectura preparada para incorporarlo posteriormente.

PRIORIDAD:

1. OAuth 2.0 real.
2. Seguridad de credenciales.
3. Conexión real con Onshape.
4. Contexto CAD real.
5. Geometría real.
6. Persistencia.
7. UI funcional.
8. Procesamiento.
9. Escritura de resultados.
10. Licenciamiento preparado para nube.

No vuelvas a solicitar decisiones sobre aspectos ya definidos en este prompt. Si surge una decisión técnica nueva, elige la alternativa más simple y compatible con la API real de Onshape y documenta la decisión.