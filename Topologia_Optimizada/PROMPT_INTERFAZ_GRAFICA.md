Trabaja sobre el proyecto existente.

En esta etapa NO quiero desarrollar todavía la interfaz de la aplicación de topología optimizada ni el selector de documentos.

El objetivo es crear únicamente una INTERFAZ GRÁFICA INICIAL que permita comprobar visualmente que la aplicación está ejecutándose y que existe una conexión OAuth 2.0 REAL con Onshape.

OBJETIVO

Al ejecutar la aplicación debe abrirse una interfaz web local, por ejemplo:

http://localhost:8000/

La pantalla debe funcionar como un pequeño dashboard de estado.

Debe mostrar:

---

TOPOLOGÍA OPTIMIZADA

Estado de la aplicación:
● Aplicación iniciada

Estado de Onshape:
● Conectado

Usuario:
[usuario autenticado]

[ Desconectar ]

---

Si todavía no existe una sesión:

Estado de la aplicación:
● Aplicación iniciada

Estado de Onshape:
○ No conectado

[ Conectar con Onshape ]

---

OAUTH 2.0

Utilizar el flujo OAuth 2.0 real de Onshape.

El botón "Conectar con Onshape" debe iniciar:

GET /login

El backend debe redirigir al endpoint oficial de autorización de Onshape.

Implementar:

GET /oauth/callback

para recibir el authorization code y realizar el intercambio server-to-server por los tokens correspondientes.

Utilizar "state" para protección contra CSRF.

Las credenciales sensibles deben permanecer exclusivamente en el backend.

El frontend nunca debe recibir:

- client_secret;
- access_token;
- refresh_token.

CONFIRMACIÓN REAL DE CONEXIÓN

NO mostrar "Conectado" simplemente porque existen tokens almacenados.

Después de completar OAuth, el backend debe realizar una petición autenticada real a Onshape para comprobar que:

- el access_token funciona;
- la sesión tiene permisos válidos;
- Onshape responde correctamente.

Solo después de esa comprobación mostrar:

● Conectado a Onshape

Si la petición falla, mostrar:

○ Error de conexión con Onshape

y permitir volver a autenticarse.

ESTADO DE LA APLICACIÓN

La interfaz debe poder determinar que FastAPI/backend está funcionando.

Mostrar:

● Aplicación iniciada

cuando el frontend haya podido comunicarse correctamente con el backend.

Si el backend deja de responder, la interfaz debe poder mostrar:

○ Backend desconectado

INFORMACIÓN DEL USUARIO

Después de validar la conexión, obtener mediante la API real de Onshape la información básica del usuario autenticado y mostrarla en pantalla.

Por ejemplo:

Conectado como:
[Nombre del usuario]

No mostrar información sensible innecesaria.

DESCONEXIÓN

Agregar:

[ Desconectar ]

Debe eliminar/invalidate la sesión local y los tokens almacenados.

Después de desconectarse:

Estado de Onshape:
○ No conectado

[ Conectar con Onshape ]

REFRESH TOKEN

El backend debe mantener la lógica de renovación automática del access_token.

Si Onshape devuelve HTTP 401:

1. intentar renovar mediante refresh_token;
2. repetir la petición cuando corresponda;
3. si falla, invalidar la sesión y mostrar "Sesión expirada".

PERSISTENCIA

Utilizar la persistencia existente del proyecto.

Si todavía no existe, utilizar SQLite.

Guardar únicamente lo necesario para mantener la sesión local.

Los secretos no deben quedar hardcodeados.

Actualizar ".env.example" si es necesario.

DISEÑO

La interfaz debe ser:

- simple;
- limpia;
- profesional;
- responsive;
- fácil de entender.

No crear todavía:

- selector de documentos;
- selector de workspace;
- selector de Part Studio;
- parámetros de optimización;
- solver;
- mallado;
- procesamiento de geometría;
- FeatureScript;
- escritura de resultados.

La única función de esta pantalla es responder visualmente:

"¿La aplicación está funcionando y estoy conectado correctamente a Onshape?"

VALIDACIÓN

Al finalizar debe ser posible comprobar este flujo:

1. Ejecutar la aplicación.
2. Abrir la interfaz local.
3. Ver "Aplicación iniciada".
4. Ver "No conectado a Onshape".
5. Pulsar "Conectar con Onshape".
6. Autorizar la aplicación en Onshape.
7. Volver automáticamente a la interfaz.
8. Validar realmente el access_token contra Onshape.
9. Mostrar "Conectado a Onshape".
10. Mostrar el usuario autenticado.
11. Desconectar.
12. Volver a mostrar "No conectado".

No utilices mocks ni datos ficticios para representar la conexión.

No implementes funcionalidades que no sean necesarias para este objetivo.

Al finalizar, indica:

- archivos creados;
- archivos modificados;
- archivos eliminados;
- dependencias agregadas;
- variables ".env" necesarias;
- configuración requerida en Onshape Developer Portal;
- comando para iniciar la aplicación.