Perfecto. **Ahora sí tengo el proyecto real** y pude inspeccionarlo. Esto cambia bastante la calidad del prompt, porque ya no necesitamos pedirle a la otra IA que "revise qué hay": podemos darle una instrucción específica para auditar **este proyecto existente**.

Encontré una arquitectura bastante definida:

* `master_topology_input.fs` → FeatureScript.
* `app-extension.html` → panel de Onshape.
* `api_server.py` → FastAPI + jobs en background.
* `geometry_processor.py` → procesamiento de geometría.
* `topopt_solver.py` → solver SIMP.
* `topologia_optimizada.py` → conexión directa con API de Onshape.
* `manifest.json` → configuración de la extensión.
* `pyproject.toml` → entorno Python/dependencias.
* `test_api.py` → pruebas.

Pero también encontré **varias diferencias importantes entre lo que la documentación dice que hace el sistema y lo que realmente implementa el código**. Por ejemplo, el solver todavía utiliza fuerzas y soportes simulados, el `master_topology_input.fs` no está guardando los anchors dentro del JSON, el timestamp está fijo, la autenticación actual utiliza credenciales directamente y no hay todavía una capa robusta de persistencia, entre otras cosas.

Por eso el prompt **no debe pedir simplemente "completá los requisitos"**. Tiene que obligar a la IA a detectar esas discrepancias.

También hay algo importante: el ZIP contiene un archivo `.env`. **No voy a reproducir su contenido ni sus credenciales.** Si esas credenciales son reales y ese `.env` alguna vez fue subido a GitHub, conviene revocarlas/regenerarlas.

### Prompt maestro

Este sería mi primer prompt como arquitecto:

Actúa como ingeniero senior especializado en Python, FastAPI, Onshape API, FeatureScript y desarrollo de App Extensions para Onshape.

Trabajarás sobre un PROYECTO EXISTENTE. NO debes reconstruir la aplicación desde cero.

Tu objetivo es auditar el proyecto actual contra los requisitos proporcionados al final de este prompt, determinar exactamente qué está implementado, qué está incompleto y qué falta, y luego modificar el código para llevarlo al estado requerido.

ESTADO CONOCIDO:

* El requisito 1 de Plataforma y Credenciales ya está cumplido mediante API Keys.
* Los requisitos 2, 3, 4 y 5 están parcialmente implementados.
* El repositorio ya contiene una arquitectura funcional inicial.
* Debes conservar todo lo que funcione correctamente y evitar reescrituras innecesarias.

REGLAS OBLIGATORIAS:

1. PRIMERO AUDITA, DESPUÉS MODIFICA.
   Antes de cambiar cualquier archivo, inspecciona toda la estructura y el código existente.
   No asumas que una funcionalidad falta solamente porque no está documentada.

2. Para cada requisito determina uno de estos estados:

   * COMPLETO
   * PARCIAL
   * FALTANTE
   * NO APLICA
   * REQUIERE CONFIGURACIÓN EXTERNA

3. Para cada estado PARCIAL o FALTANTE indica:

   * qué existe actualmente;
   * qué exige realmente el requisito;
   * qué diferencia existe;
   * qué archivo(s) deben modificarse;
   * qué cambio concreto debe realizarse.

4. NO elimines ni reemplaces funcionalidades existentes que ya cumplan correctamente un requisito.

5. No agregues dependencias innecesarias. Reutiliza la arquitectura y dependencias actuales siempre que sea posible.

6. Distingue claramente entre:

   * funcionalidades que pueden implementarse modificando el código;
   * configuración que debe realizarse manualmente en Onshape Developer Portal;
   * configuración local necesaria para ejecutar la aplicación.

7. No inventes capacidades de Onshape.
   Si una funcionalidad requiere una API, mecanismo de extensión o capacidad específica de Onshape, verifica primero que la arquitectura propuesta sea compatible con ella.

8. Presta especial atención a las diferencias entre la documentación existente y el comportamiento real del código.

9. La aplicación utiliza API Keys como método de autenticación. Mantén este método salvo que exista una razón técnica clara para cambiarlo.

10. Las credenciales nunca deben quedar hardcodeadas en el código ni exponerse en logs, respuestas HTTP, frontend o documentación.

11. Después de realizar los cambios, ejecuta una segunda auditoría completa contra todos los requisitos y corrige cualquier requisito que continúe incompleto y pueda resolverse desde el código.

ÁREAS QUE DEBES AUDITAR CON ESPECIAL ATENCIÓN:

A. AUTENTICACIÓN Y API DE ONSHAPE

* Verifica cómo se autentican actualmente las peticiones.
* Verifica que el mecanismo utilizado sea correcto para API Keys de Onshape.
* Centraliza la autenticación para evitar implementaciones duplicadas.
* Verifica manejo de errores HTTP 401, 403, 404 y 429.
* Implementa reintentos controlados para rate limits.
* No expongas ACCESS_KEY ni SECRET_KEY al frontend.
* Verifica que documentId, workspaceId y elementId sean obtenidos dinámicamente cuando corresponda y no dependan de valores globales del .env para operar sobre el documento activo.

B. BACKEND

* Mantén FastAPI.
* Revisa los endpoints existentes.
* Valida correctamente todos los payloads mediante Pydantic.
* Mejora manejo de errores.
* Mantén el sistema de jobs y polling si es adecuado.
* Evita depender de variables globales para el estado de trabajos si existe una solución local sencilla y compatible con el proyecto.
* Verifica que las tareas de optimización no bloqueen innecesariamente el servidor.
* Añade logging estructurado sin información sensible.

C. FRONTEND / APP EXTENSION

* Verifica que el panel pueda ejecutarse correctamente dentro de Onshape.
* Obtén dinámicamente documentId, workspaceId y elementId desde el contexto disponible.
* No dependas exclusivamente de parámetros manuales de URL si Onshape proporciona un mecanismo de contexto más apropiado.
* Verifica compatibilidad con iframe.
* Revisa CSP, CORS y headers de seguridad.
* El frontend nunca debe contener secretos de API.
* Mantén una interfaz sencilla y funcional.

D. FEATURESCRIPT

* Revisa `master_topology_input.fs`.
* Verifica que las selecciones de geometría y parámetros realmente se almacenen de forma recuperable.
* El JSON debe representar correctamente:

  * anchors;
  * load face;
  * dirección normalizada;
  * magnitud;
  * unidad;
  * parámetros de optimización;
  * versión del esquema;
  * timestamp real.
* No uses timestamps fijos.
* Verifica que el backend pueda recuperar de forma inequívoca la información generada por el FeatureScript.
* No inventes identificadores de entidades si FeatureScript/Onshape no los proporciona directamente de esa manera.

E. PROCESAMIENTO GEOMÉTRICO

* Audita `geometry_processor.py`.
* Determina qué partes realmente descargan geometría desde Onshape.
* Determina qué partes realmente generan mesh.
* Determina qué partes son solamente placeholders/mockups.
* No declares una funcionalidad como implementada si únicamente está simulada.
* Mantén una separación clara entre:

  1. adquisición de geometría;
  2. extracción de condiciones de contorno;
  3. mallado;
  4. optimización;
  5. reconstrucción CAD;
  6. exportación.

F. SOLVER

* Audita `topopt_solver.py`.
* Identifica cualquier utilización de datos simulados, aleatorios o hardcodeados.
* No consideres una optimización real solamente porque el algoritmo tenga una estructura SIMP.
* El solver debe recibir progresivamente los datos reales obtenidos del modelo cuando la arquitectura lo permita.
* Si una parte todavía requiere implementación científica adicional, déjala claramente identificada en lugar de simular resultados y presentarlos como reales.

G. PERSISTENCIA
Implementa una solución local sencilla y apropiada para este proyecto.
Preferentemente SQLite si no existe una razón técnica para utilizar Redis.

Debe permitir almacenar como mínimo:

* jobs;
* estado;
* timestamps;
* configuración utilizada;
* resultados;
* errores;
* metadatos necesarios;
* cache local cuando realmente reduzca llamadas a Onshape.

Los tokens/credenciales sensibles no deben almacenarse innecesariamente.

H. CONFIGURACIÓN

* Verifica Python >= 3.10.
* Mantén el entorno virtual aislado.
* Revisa `pyproject.toml`.
* El `.env` debe ser solamente local y nunca debe formar parte del repositorio.
* Genera/actualiza `.env.example` sin secretos reales.
* Documenta las variables requeridas.

I. TÚNEL HTTPS
Determina qué necesita realmente la aplicación para:

* App Extension;
* iframe;
* comunicación frontend → backend;
* OAuth si posteriormente se incorpora.

Si el túnel es obligatorio para el funcionamiento real de la integración, documenta claramente cómo configurarlo.
No confundas `localhost` con una URL accesible por Onshape.

J. WEBHOOKS
Son opcionales.
No implementarlos simplemente para marcar una casilla.
Solo incorporarlos si aportan valor a la arquitectura actual.

REQUISITOS DE REFERENCIA:

1. PLATAFORMA Y CREDENCIALES

* Cuenta Developer activa.
* API Keys configuradas.
* URLs y OAuth solamente si corresponden.
* Scopes/permisos apropiados.

ESTADO: COMPLETO. NO REHACER.

2. INFRAESTRUCTURA LOCAL Y RED

* Python 3.10+ en entorno aislado.
* FastAPI + Uvicorn.
* Tunnel HTTPS cuando sea necesario.
* Variables de entorno.
* Configuración reproducible.

3. BACKEND Y REST API

* Autenticación correcta con Onshape.
* Server-side proxy.
* Manejo 401/403/404/429.
* Reintentos ante rate limits.
* Validación defensiva.
* Webhooks opcionales.

4. PERSISTENCIA

* SQLite, Redis o almacenamiento local apropiado.
* Estados de jobs.
* Configuración.
* Cache.
* Resultados.
* Persistencia necesaria para que reiniciar el servidor no destruya todo el estado.

5. FRONTEND E INTEGRACIÓN

* UI web.
* Compatibilidad iframe/App Extension.
* Contexto CAD dinámico:
  documentId
  workspaceId
  elementId
* Comunicación segura frontend → backend.
* Sin exposición de credenciales.

FORMATO DE TRABAJO:

FASE 1 — AUDITORÍA
Primero presenta una tabla:

| Requisito | Estado actual | Evidencia | Acción |
| --------- | ------------- | --------- | ------ |

No modifiques todavía el proyecto.

FASE 2 — PLAN
Después presenta únicamente las modificaciones necesarias, ordenadas por prioridad:

1. Críticas
2. Necesarias
3. Mejoras

FASE 3 — IMPLEMENTACIÓN
Realiza los cambios directamente sobre el proyecto existente.

Para cada archivo modificado explica brevemente:

* por qué se modificó;
* qué problema resuelve;
* qué compatibilidad mantiene.

No reescribas archivos completos si solo es necesario modificar una parte.

FASE 4 — VALIDACIÓN
Ejecuta las pruebas disponibles y agrega pruebas para las funcionalidades nuevas o corregidas.

Comprueba como mínimo:

* startup del backend;
* validación de configuración;
* endpoints;
* autenticación;
* manejo de errores;
* contexto CAD;
* payload FeatureScript → frontend → backend;
* creación y consulta de jobs;
* persistencia;
* flujo de optimización.

FASE 5 — AUDITORÍA FINAL
Vuelve a recorrer TODOS los requisitos.

Entrega:

| Requisito | Estado final | Evidencia |
| --------- | ------------ | --------- |

Ningún requisito implementable desde código debe quedar como PARCIAL sin una explicación técnica concreta.

Si un requisito depende de una acción manual en Onshape Developer Portal, túnel o credenciales, márcalo como `REQUIERE CONFIGURACIÓN EXTERNA` y proporciona exactamente qué debe configurar el usuario.

REGLA FINAL:

No declares que el sistema está "completo", "funcional" o "listo para producción" si alguna parte crítica continúa siendo simulada, hardcodeada o incompleta.

Diferencia siempre entre:

* implementación real;
* mock;
* placeholder;
* configuración externa;
* funcionalidad futura.

El objetivo no es producir más código, sino conseguir que el proyecto existente cumpla realmente los requisitos con la menor cantidad de cambios necesarios.
estructura inicial de la documentación y preséntame las primeras preguntas de aclaración que necesites para asegurar el éxito de la arquitectura.