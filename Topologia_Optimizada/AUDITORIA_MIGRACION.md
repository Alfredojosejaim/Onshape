# Auditoría de migración a OAuth 2.0

Fecha: 2026-08-21

## Matriz de componentes

| Componente | Estado actual | Dependencia FeatureScript | Acción |
| --- | --- | --- | --- |
| Backend (`api_server.py`) | FastAPI, jobs SQLite y proxy parcial con API Keys | Indirecta: recibe `topologyConfig` producido por el panel | Modificar: OAuth, sesiones, cliente centralizado y contexto CAD |
| Frontend (`app-extension.html`) | Panel dentro de App Extension; lee un adaptador SDK y envía configuración | Directa | Reemplazar por interfaz local autenticada y selector DID/WID/EID |
| FeatureScript (`master_topology_input.fs`) | Selecciona caras y parámetros, guarda atributos | Directa | Conservar temporalmente para referencia; retirar del flujo funcional |
| App Extension (`manifest.json`) | Declara panel y capacidades `feature_script`/`partstudio` | Directa | Modificar o retirar cuando la UI local sea el flujo principal |
| Autenticación (`api_server.py`, `topologia_optimizada.py`) | Basic Auth con `ONSHAPE_ACCESS_KEY`/`ONSHAPE_SECRET_KEY` | No | Reemplazar por OAuth 2.0 server-side |
| Cliente Onshape | Sesiones `requests` duplicadas y endpoints sin capa común | No | Crear cliente centralizado con refresh, errores, timeout y rate limiting |
| Geometría (`geometry_processor.py`) | Descarga STEP/properties; no genera mesh sin adaptador | No | Conservar adquisición real; documentar y mantener pendientes explícitos |
| Solver (`topopt_solver.py`) | Rechaza ejecución sin FEA real; no genera resultados ficticios | No | Conservar y conectar progresivamente a datos reales |
| Persistencia (`api_server.py`) | Tabla SQLite únicamente para jobs | No | Ampliar a OAuth, usuario, contexto, configuración y resultados |
| Licenciamiento | No existe capa independiente | No | Crear interfaz `validate_user_access()` |
| Tests (`test_api.py`) | Script manual contra servidor; no cubre OAuth | Indirecta | Reemplazar/ampliar con tests aislados y mocks de transporte |
| Configuración (`.env.example`, documentación) | Variables de API Keys e IDs hardcodeables | Indirecta | Migrar a variables OAuth y actualizar documentación |

## Hallazgos técnicos

- `api_server.py` y `topologia_optimizada.py` usan credenciales estáticas; el segundo además termina el proceso si faltan IDs.
- `app-extension.html` depende de `getContext()`/`getFeatureData()` no documentados en el archivo y de datos del FeatureScript.
- `geometry_processor.py` descarga STEP y propiedades mediante rutas que deben validarse contra la API real; el mallado, el mapeo de caras y la reconstrucción no están implementados.
- `topopt_solver.py` evita correctamente datos aleatorios, pero no dispone de un adaptador FEA real.
- Los jobs sí persisten en SQLite, pero las sesiones OAuth, el usuario, el último contexto, configuración y resultados no están modelados.
- `manifest.json` mantiene permisos y capacidades de App Extension que dejarán de ser necesarios para el flujo local.
- No se encontraron llamadas `httpPost` en el código Python/HTML; el FeatureScript solo persiste atributos.

## Verificación de API externa

La documentación oficial de Onshape confirma:

- autorización en `https://oauth.onshape.com/oauth/authorize`;
- intercambio y refresh en `https://oauth.onshape.com/oauth/token`;
- perfil de sesión en `https://cad.onshape.com/api/users/sessioninfo`;
- token OAuth enviado en el header `Authorization` para endpoints bajo `/api`;
- refresh token rotativo: deben persistirse access y refresh token actualizados.

La API de geometría y escritura de resultados no se da por implementada hasta validar cada endpoint concreto con la documentación de Onshape y una cuenta configurada.

## Limpieza realizada

Eliminados por ser legacy y no tener referencias de ejecución:

- `master_topology_input.fs`
- `manifest.json`
- `INTEGRACION_APP_EXTENSION.md`
- `documentacion_tecnica.md`
- `INICIO_RAPIDO.py`
- `test_api.py`
- `topologia_optimizada.py`

Se conserva `app-extension.html` porque ahora es la interfaz local servida por
`GET /`. Se conserva `jobs.sqlite3` porque contiene el historial persistente de
jobs y sesiones locales.

## Orden de migración

1. OAuth 2.0, sesiones SQLite y cliente Onshape centralizado.
2. Contexto CAD y consulta de documentos/elementos.
3. UI local y eliminación del flujo FeatureScript.
4. Geometría real, solver y escritura de resultados.
5. Licenciamiento, tests y auditoría final.

## Auditoría de implementación — 2026-08-21

### Funcional

- El panel principal está organizado como estudio de optimización y no solicita IDs
  CAD manuales.
- El payload separa `context`, `designSpace`, `loadCases`, `material`,
  `objectives` y `solverSettings`.
- Las selecciones se mantienen separadas para conservar, obstáculo, forma inicial,
  restricciones y cargas.
- El backend valida tipos, referencias, contexto, material, volumen, iteraciones
  y tolerancia antes de aceptar un trabajo.
- La sesión OAuth y la descarga de geometría real STEP/properties se conservan.

### Parcial

- La UI usa un puente `postMessage` para solicitar selecciones y recibir
  referencias del host Onshape; falta registrar y conectar el App Extension real
  en una cuenta de Onshape.
- El contexto se acepta desde el host o parámetros de integración, pero todavía
  requiere validar el contrato concreto del contenedor Onshape.
- Los jobs muestran progreso por etapas, aunque siguen ejecutándose con
  `BackgroundTasks`.

### Pendiente

- FeatureScript/App Extension nativo para producir selecciones reales sin un
  adaptador host configurado.
- Validación en vivo de que cada referencia resuelve a una entidad del modelo.
- Mallado, mapeo de referencias a nodos/elementos, adaptador FEA y reconstrucción
  CAD. El sistema continúa bloqueando estas etapas y no genera resultados falsos.
- Escritura de la geometría optimizada y métricas estructurales reales.

## Análisis de `ejemplo.txt` y puente actual

El ejemplo usa un Custom Feature FeatureScript 3044 con campos `Query` para
seleccionar caras y valores numéricos para la carga/optimización. Su
comunicación consiste en persistir un mapa mediante `setAttribute`; no realiza
peticiones HTTP ni recibe respuestas de una aplicación externa.

`topology_bridge.fs` reutiliza conceptualmente el Custom Feature, las
selecciones nativas y los atributos por entidad, pero separa los roles
`preserve`, `obstacle`, `initialShape`, `constraint` y `load`. No copia el
solver ni datos con timestamps ficticios. FeatureScript no serializa por sí
solo `documentId`, `workspaceId` o `elementId`; esos datos deben aportarlos el
App Extension/host que conoce el contexto.

Se añadió `POST /api/integration/events` para que el componente que sí puede
hacer HTTP (App Extension o adaptador host) envíe un sobre con `context`,
`selections`, `parameters`, `geometry` y `operation`. El backend autentica,
valida y persiste el evento sin exponer tokens.

### Auditoría de esta etapa

- **Creados:** `topology_bridge.fs`.
- **Modificados:** `app-extension.html`, `api_server.py`,
  `AUDITORIA_MIGRACION.md`.
- **Eliminados:** ninguno.
- **Dependencias:** ninguna.
- **Variables `.env`:** ninguna nueva.
- **Configuración Onshape:** crear/importar `topology_bridge.fs` como Custom
  Feature en el Feature List y usarlo en un Part Studio.
- **Prueba mínima:** autenticarse en el panel, ejecutar el Custom Feature,
  seleccionar entidades y verificar el atributo `topologyBridgeSelection`;
  después un App Extension/adaptador debe enviar el evento validado al nuevo
  endpoint.
- **Pendiente:** conexión oficial del host/App Extension con el atributo,
  resolución de referencias a geometría mediante API real, devolución de
  geometría modificada y optimización FEA real.
