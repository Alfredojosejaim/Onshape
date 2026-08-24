# Documentación de Integración - Onshape App & Optimización Topológica

**Fecha:** 2026-08-24  
**Versión del Pipeline:** 1.2.0 (Hito 1: Geometría Real, Mallado Real y Visualización 3D Real)  
**Repositorio:** https://github.com/Alfredojosejaim/Onshape  

---

## 1. Arquitectura del Sistema

La arquitectura está desacoplada en tres subsistemas sin dependencias directas de FeatureScript para comunicaciones de red:

```
[ ONSHAPE Part Studio ]
          │
          ▼
[ App Extension (app-extension.html) ] ──(postMessage SDK)──► Captura documentId, workspaceId, elementId, selecciones
          │
          ▼  POST /api/context & POST /api/geometry/selection
[ Backend FastAPI (api_server.py) ]
          │
          ├─► OnshapeClient (OAuth 2.0 / REST API) ──► GET /partstudios/.../export (STEP)
          │
          ├─► GeometryProcessor (OpenCASCADE / CadQuery / OCP)
          │      ├─► B-Rep Tessellation ──► Vértices, Normales, Caras Trianguladas (para Three.js)
          │      ├─► Mesher Volumétrico FEM ──► Nodos y Elementos Tetraédricos
          │      └─► B-Rep Face Mapping ──► Bounding Boxes, Centroides y Normales de caras a Nodos
          │
          ▼
[ App Externa Principal (optimization-app.html) ] ──► Renderizado real en Three.js (BufferGeometry)
```

---

## 2. Flujo de Datos y Pipeline Real (Hito 1)

1. **Autenticación:**
   - Flujo OAuth 2.0 oficial (`https://oauth.onshape.com/oauth/authorize` y `/oauth/token`).
   - Tokens almacenados de forma segura en SQLite (`jobs.sqlite3`), con cookie de sesión `topologia_session` (`HttpOnly`, `SameSite=Lax`).
   - Client Secret y Refresh Token residen exclusivamente en el servidor backend.

2. **Captura de Selección:**
   - La App Extension (`app-extension.html`) lee los parámetros del contexto de Onshape (`documentId`, `workspaceId`, `elementId`).
   - El usuario selecciona la pieza (Design Space) y opcionalmente caras/sólidos de obstáculo (Keep-out).
   - Se despacha la selección a `/api/geometry/selection` y `/api/geometry/download`.

3. **Descarga y Validación de STEP:**
   - `GeometryProcessor.download_part_studio()` invoca el endpoint oficial `/api/partstudios/d/{did}/w/{wid}/e/{eid}/export?formatName=STEP`.
   - Se valida que la respuesta sea binaria no vacía, de tipo STEP válido.

4. **Procesamiento de Geometría y Teselación para el Visor:**
   - `GeometryProcessor.tessellate_step()` utiliza el kernel OpenCASCADE (OCP) para importar el B-Rep exacto.
   - Ejecuta `BRepMesh` con deflexión lineal y angular controlada.
   - Extrae vértices `[x, y, z]`, normales `[nx, ny, nz]` e índices de triángulos `[i0, i1, i2]` y bounding boxes.
   - El endpoint `/api/geometry/tessellate` envía esta geometría estructurada al visor Three.js.

5. **Mallado FEM Real:**
   - `GeometryProcessor.create_mesh()` genera la discretización volumétrica en tetraedros (`tet4` / `tet10`), produciendo coordenadas de nodos `(N, 3)` y matrices de conectividad `(E, 4)`.

6. **Mapeo Geometría $\rightarrow$ Malla:**
   - `GeometryProcessor.identify_boundary_conditions()` asocia las caras seleccionadas de Onshape (con su centroide, normal y bounding box) con los nodos de la superficie de la malla FEM mediante tolerancia espacial.

7. **Renderizado en Visor 3D:**
   - `optimization-app.html` construye un `THREE.BufferGeometry` nativo con los vértices e índices reales de la pieza.
   - Se eliminan todas las geometrías sustitutas o de demostración (`BoxGeometry`).

---

## 3. Estado Real de Componentes

| Módulo | Estado Real | Descripción Técnica |
|---|---|---|
| **OAuth 2.0 & Sesiones** | 🟢 **COMPLETO** | Authorization code, refresh automático con cerrojo de concurrencia, reintentos con backoff y SQLite. |
| **Descarga STEP** | 🟢 **COMPLETO** | Descarga real desde API REST de Onshape con reintentos y control de errores. |
| **Teselación 3D (CAD)** | 🟢 **COMPLETO** | Procesamiento OpenCASCADE / CadQuery BRepMesh para renderizado real en Three.js. |
| **Mallado Volumétrico FEM** | 🟢 **COMPLETO** | Generación de malla tetraédrica real con nodos y conectividades. |
| **Mapeo B-Rep $\rightarrow$ Nodos** | 🟢 **COMPLETO** | Búsqueda por proximidad y proyección espacial de caras a nodos FEM. |
| **Visor 3D Three.js** | 🟢 **COMPLETO** | Visualización de geometría real descargada, flechas de fuerzas 3D e indicadores de fijaciones. |
| **Solver FEA Elasticidad** | 🔴 **PENDIENTE** | Enlace con ensamblaje matricial y solver de rigidez (scikit-fem / FEniCS). |
| **Solver TopOpt (SIMP)** | 🔴 **PENDIENTE** | Loop de optimización basado en densidades (requiere FEA completo previo). |
| **Reconstrucción CAD Final** | 🔴 **PENDIENTE** | Isosuperficie (Marching Cubes / OpenCASCADE) a sólido B-Rep. |
| **Devolución a Onshape** | 🔴 **PENDIENTE** | Importación vía Onshape REST API (Blob element o traducción a Part Studio). |

---

## 4. Limitaciones Actuales y Próximos Pasos

- **Limitaciones de FeatureScript:** FeatureScript no puede ejecutar llamadas HTTP ni comunicarse con FastAPI. Se conserva exclusivamente para referencia de sintaxis CAD nativa.
- **Próximo Hito (Hito 2):** Integración del Solver FEA de elasticidad lineal y ciclo SIMP determinista, alimentados con la malla y mapeo de cargas/fijaciones validados en el Hito 1.
