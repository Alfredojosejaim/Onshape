# AUDITORÍA, CORRECCIÓN Y AUTOCONTENCIÓN DEL ENTORNO LOCAL

## ROL

Actúa como ingeniero de software senior especializado en:

- Python / FastAPI
- Windows
- Uvicorn
- HTTPS local
- mkcert
- OAuth 2.0
- Onshape API
- JavaScript
- testing y validación de integración.

Debes trabajar sobre el repositorio actual respetando estrictamente:

- `prompt.md` → especificación del proyecto.
- `metodologia.md` → reglamento obligatorio.
- `resumen_implementacion.md` → registro real de implementación.

Antes de modificar cualquier cosa, lee los tres archivos y audita el estado actual.

---

# OBJETIVO PRINCIPAL

Corregir la implementación actual de HTTPS/mkcert para que el proyecto pueda ejecutarse en una instalación limpia de Windows sin requerir que el usuario instale mkcert manualmente.

El proyecto debe ser realmente autocontenido respecto de mkcert y su configuración HTTPS local.

El resultado esperado es:

CLONAR REPOSITORIO
↓
EJECUTAR `INICIAR_APLICACION.bat`
↓
detectar dependencias
↓
obtener mkcert si es necesario
↓
verificar integridad
↓
instalar CA local
↓
generar certificados
↓
iniciar FastAPI con HTTPS
↓
https://localhost:8000

---

# FASE 1 — AUDITORÍA OBLIGATORIA

Antes de modificar código:

1. Leer `prompt.md`.
2. Leer `metodologia.md`.
3. Leer `resumen_implementacion.md`.
4. Revisar:
   - `INICIAR_APLICACION.bat`
   - `.gitignore`
   - `.env`
   - `.env.example`
   - `api_server.py`
   - configuración de Uvicorn/FastAPI
   - frontend JavaScript
   - configuración OAuth
   - CORS
   - cookies
   - cualquier URL localhost.
5. Determinar exactamente cómo se genera actualmente el certificado.
6. Determinar si Uvicorn realmente está utilizando el certificado.
7. Determinar si existen referencias HTTP que deban ser HTTPS.
8. Determinar si `.env` contiene secretos reales.

No modifiques código durante esta fase.

---

# FASE 2 — MKCERT AUTOCONTENIDO

Modificar `INICIAR_APLICACION.bat` para que no dependa de una instalación previa de mkcert.

Si `mkcert.exe` no existe dentro del proyecto:

1. detectar arquitectura de Windows;
2. determinar la versión de mkcert que se utilizará;
3. descargar automáticamente el binario oficial correspondiente;
4. utilizar HTTPS para la descarga;
5. verificar SHA-256 contra un hash conocido y documentado;
6. si el hash no coincide, abortar inmediatamente;
7. solo después de verificarlo permitir su ejecución.

No descargar ni ejecutar archivos arbitrarios.

No utilizar fuentes de terceros para obtener el binario si existe una distribución oficial apropiada.

Guardar el binario en una ubicación local del proyecto que ya esté contemplada por `.gitignore`.

El usuario no debe tener que descargar ni copiar manualmente `mkcert.exe`.

---

# FASE 3 — GENERACIÓN DE CERTIFICADOS

El launcher debe:

1. comprobar si existe la CA local de mkcert;
2. ejecutar `mkcert -install` cuando sea necesario;
3. comprobar que la operación fue exitosa;
4. generar certificados para:

   - `localhost`
   - `127.0.0.1`
   - `::1`

5. almacenarlos dentro de:

`certs/`

6. no versionarlos en Git.

Si los certificados ya existen y siguen siendo válidos, no regenerarlos innecesariamente.

Si faltan o son inválidos, regenerarlos.

El launcher debe validar que los archivos esperados existen antes de iniciar FastAPI.

---

# FASE 4 — HTTPS REAL EN FASTAPI

Verificar que `api_server.py` realmente utiliza:

- `SSL_CERTFILE`
- `SSL_KEYFILE`

para configurar Uvicorn.

No basta con definir las variables de entorno.

Debe existir un flujo real equivalente a:

uvicorn
↓
ssl_certfile
↓
ssl_keyfile
↓
HTTPS

El servidor debe arrancar realmente en:

`https://localhost:8000`

Si la configuración actual utiliza otra arquitectura válida, mantenerla siempre que el resultado sea equivalente y verificable.

---

# FASE 5 — CONFIGURACIÓN DE SEGURIDAD

Revisar:

- `COOKIE_SECURE=true`
- CORS
- OAuth redirect URI
- URLs internas
- frontend
- backend
- callbacks OAuth.

Todo el flujo local debe ser coherente con HTTPS.

No permitir que una parte del sistema continúe dependiendo accidentalmente de:

`http://localhost:8000`

cuando deba utilizar HTTPS.

---

# FASE 6 — `.ENV` Y SECRETOS

Auditar `.env`.

Si contiene:

- Client Secret real;
- tokens;
- credenciales;
- claves privadas;
- información sensible;

NO exponerlos en código, frontend ni documentación.

`.env` debe permanecer ignorado por Git.

Si `.env` ya fue versionado anteriormente, comprobar su estado y corregir el repositorio según corresponda.

No publicar ni copiar secretos en archivos de documentación.

Mantener `.env.example` como plantilla sin secretos reales.

---

# FASE 7 — EXPERIENCIA DE ARRANQUE

Mejorar `INICIAR_APLICACION.bat` para que sea robusto y claro.

Debe informar:

- qué dependencia está comprobando;
- si mkcert ya existe;
- si se está descargando;
- si se está verificando;
- si se está instalando la CA;
- si se están generando certificados;
- si FastAPI arrancó correctamente;
- cuál es la URL final.

Si ocurre un error, debe:

1. explicar el problema;
2. indicar la causa probable;
3. detenerse;
4. devolver un código de error apropiado.

No ocultar errores mediante `|| exit /b 0`.

---

# FASE 8 — PREPARACIÓN PARA HITO 2

Después de completar correctamente el objetivo HTTPS/autocontenido, puedes realizar mejoras adicionales SOLO si cumplen estas condiciones:

- bajo riesgo;
- no alteran la arquitectura establecida;
- mejoran mantenibilidad;
- mejoran validación;
- mejoran trazabilidad;
- preparan la futura etapa de FEA/mallado;
- no implementan todavía FEA ni TopOpt.

Prioridad de mejoras permitidas:

### 1. Validación de contratos

Revisar que los endpoints actuales:

- validen correctamente entradas;
- devuelvan errores coherentes;
- no acepten datos incompletos silenciosamente.

### 2. Persistencia

Revisar que los datos de:

- selección;
- geometría;
- malla;
- fuerzas;
- restricciones;

mantengan una estructura consistente.

### 3. Identificación geométrica

Preparar interfaces claras para:

Onshape Entity
↓
CAD/B-Rep Entity
↓
Mesh Entity

No implementar todavía el solver.

### 4. Testing

Agregar tests que detecten regresiones en:

- OAuth;
- HTTPS;
- descarga STEP;
- selección de Parts;
- tessellación;
- endpoints existentes.

No presentar mocks como pruebas E2E.

### 5. Limpieza técnica

Eliminar código muerto, duplicado o contradictorio siempre que pueda hacerse sin modificar el comportamiento esperado.

---

# RESTRICCIÓN CRÍTICA

NO implementar:

- FEA;
- solver FEM;
- TopOpt;
- SIMP;
- reconstrucción B-Rep;
- exportación de geometría optimizada;
- nuevas funcionalidades de Hito 2 que todavía no estén definidas.

Si detectas algo que debería hacerse para Hito 2, documentarlo como propuesta y NO implementarlo.

---

# REGLA DE NO REGRESIÓN

Las funcionalidades actualmente verificadas no deben romperse.

Después de las modificaciones:

1. ejecutar todos los tests existentes relevantes;
2. agregar tests cuando sea necesario;
3. verificar el arranque HTTPS;
4. verificar OAuth;
5. verificar endpoints principales.

Si algo falla, corregirlo antes de declarar la iteración terminada.

---

# VALIDACIÓN REAL OBLIGATORIA

No marques HTTPS como COMPLETADO simplemente porque:

- existe `mkcert.exe`;
- existen variables SSL;
- existen certificados;
- existe código de configuración.

Debes verificar el flujo real:

launcher
↓
mkcert
↓
certificado
↓
FastAPI/Uvicorn
↓
HTTPS
↓
localhost:8000

Si no puedes ejecutar alguna parte por limitaciones del entorno, declararla como PENDIENTE/BLOQUEADA y explicar exactamente qué no pudo verificarse.

No inventar resultados.

---

# DOCUMENTACIÓN OBLIGATORIA

Actualizar `resumen_implementacion.md`.

Registrar:

## Auditoría inicial

Qué estaba funcionando y qué estaba mal.

## Cambios realizados

Archivos modificados y motivo.

## MKCERT

Indicar:

- método de obtención;
- versión utilizada;
- verificación de integridad;
- ubicación;
- comportamiento cuando no existe.

## HTTPS

Indicar:

- certificado;
- clave;
- configuración Uvicorn;
- URL final;
- validación realizada.

## Seguridad

Registrar:

- tratamiento de `.env`;
- secretos;
- CORS;
- cookies;
- OAuth.

## Tests

Registrar cada prueba realizada y resultado.

## Mejoras adicionales

Si implementaste mejoras preparatorias para Hito 2, documentarlas por separado.

## Estado final

Clasificar cada requisito:

- COMPLETADO
- PARCIAL
- PENDIENTE
- BLOQUEADO

---

# REGLA DE HONESTIDAD

Nunca declarar una funcionalidad como COMPLETADA solo porque el código parece correcto.

Debe existir evidencia.

Si existe cualquier duda:

PARCIAL / PENDIENTE / BLOQUEADO.

---

# AUDITORÍA FINAL

Antes de terminar:

1. volver a leer `prompt.md`;
2. comprobar `metodologia.md`;
3. revisar `resumen_implementacion.md`;
4. revisar todos los archivos modificados;
5. comprobar que no se introdujeron secretos;
6. comprobar que no se introdujeron certificados al repositorio;
7. comprobar HTTPS real;
8. ejecutar tests;
9. comprobar que no se rompió funcionalidad anterior.

---

# RESPUESTA FINAL

Devuelve únicamente:

## Implementado
- ...

## Verificado
- ...

## Parcial
- ...

## Pendiente
- ...

## Bloqueado
- ...

## Archivos modificados
- ...

## Mejoras adicionales realizadas
- ...

## Recomendaciones para Hito 2
- ...

No declares el Hito 2 como iniciado.

El objetivo de esta iteración es dejar el proyecto autocontenido, seguro, reproducible y técnicamente preparado para que posteriormente podamos definir y ejecutar el Hito 2.