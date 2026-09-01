# PROJECT_STATUS.md

Estado **REAL** del proyecto **Topología Optimizada** (aplicación CAD/CAE desktop).
Este archivo refleja exclusivamente el estado actual del código, no intenciones ni
informes antiguos.

Leyenda: **IMPLEMENTADO** · **PARCIAL** · **PENDIENTE**

---

## Desktop

**IMPLEMENTADO**

Aplicación desktop nativa **PySide6 + VTK**, sin navegador ni servidor HTTP local
para funcionalidades que se ejecutan directamente.

- Arranque: `main.py` → `desktop/app.py` → `desktop/ui/main_window.py`.
- Central 3D: `desktop/viewport/viewport_3d.py` (`Viewport3D`).
- Pipeline de control: `desktop/pipeline/controller.py` (`PipelineController`).
- Flujo estándar (5 pasos: importar STEP → condiciones → malla → FEA → optimización).

---

## Viewport

**IMPLEMENTADO**

Composición separada por responsabilidades:

```
Viewport3D -> Scene -> Renderer -> GPU
            -> CameraController
            -> SelectionManager
            -> NavigationManager
```

- `desktop/viewport/renderer.py`: `Renderer` (actores, fondo, ejes, rejilla, reset de cámara).
- `desktop/viewport/scene.py`: `Scene` (geometría / malla / densidad / selección / modos de visualización).
- `desktop/viewport/selection.py`: `SelectionManager` (selección por sólido / cara / actor).
- Modos de visualización: surfaced, wireframe, transparent, surfaced_edges, mapa de densidad.

---

## Camera

**IMPLEMENTADO**

Sistema **independiente** `CameraController` (`desktop/viewport/camera.py`), separado
de `NavigationManager`. NO forma parte del sistema de navegación.

```
NavigationManager  -> qué acción solicita el usuario
CameraController   -> cómo se transforma la cámara en 3D
```

Capacidades (validadas con tests):

- **Órbita libre** (trackball) alrededor del Target/Focal Point, sin bloqueo a ejes
  del mundo; mantiene distancia y ancla en el punto de interés.
- **Pan** en el espacio de la cámara (mueve cámara + target juntos, misma orientación,
  independiente de X/Y/Z globales).
- **Zoom** a lo largo de la dirección de observación (dolly), hacia el punto de interés.
- **Vistas predefinidas**: frontal, posterior, superior, inferior, izquierda, derecha,
  isométrica. No limitan la libertad posterior (se puede volver a orbitar desde ellas).
- **Fit-to-view** a partir del bounding box / modelo, sin forzar orientación restringida
  permanente.

Separación de responsabilidades respetada: eventos → NavigationManager → CameraController → VTK Camera.

---

## Navigation

**IMPLEMENTADO**

`NavigationManager` (`core/navigation.py`) traduce eventos de entrada en acciones
`ViewportAction` (ORBIT, PAN, ZOOM_IN, ZOOM_OUT, SELECT, FIT, ROTATE, CONTEXT_MENU).

**Perfiles integrados (4)**:

- **AutoCAD**: rueda = zoom; medio-botón = pan; Shift+medio = orbit; izquierda = select; clic doble/N = fit.
- **Onshape**: izquierda = select; medio = pan; derecha = orbit; F = fit.
- **Fusion 360**: izquierda = select; medio = pan; Shift+medio = orbit; F = fit.
- **Blender**: medio = orbit; Shift+medio = pan; Ctrl+rueda = zoom; teclado . = fit.

Cambio de perfil **en tiempo de ejecución** sin tocar los observers del viewport
(`Viewport3D.set_navigation_profile`). La preferencia **se guarda localmente**
(`core/user_preferences.py` → `preferences.json`) y **se restaura al iniciar**
(`desktop/ui/main_window.py`). Tests en `test_camera_controller.py`.

---

## Selection

**IMPLEMENTADO**

- `desktop/viewport/selection.py`: picking por puntero (hierarchical: sólido / cara / actor),
  con soporte de Ctrl para añadir.
- `desktop/viewport/scene.py`: mapeo de célula de malla triangular → cara B-Rep
  (`face_index_for_cell`), resaltado de caras (`highlight_faces`) y metadatos de cara.
- Selección de nodos geométrica validada (coordinate-based + física) — ver
  `ARQUITECTURA_SELECCION_NODOS.md`.

---

## CAD

**IMPLEMENTADO**

- Importación STEP vía `services/cad_service.py` (gmsh/OCCT).
- `core/cad_entity.py`: `CadEntityRef`, `SelectionSet`.
- `core/geometry.py`: entidades y operaciones geométricas de B-Rep.
- `core/cad_reconstruction.py`: reconstrucción CAD B-Rep a partir de resultados de malla
  (ver CAD Reconstruction).

---

## Features

**IMPLEMENTADO**

`core/features.py` (203 líneas): sistema de Features de modelado paramétrico
(extrusión, chaflán, etc.). Validado con `test_fase2_features.py`.

---

## Commands

**IMPLEMENTADO**

`core/commands.py` (577 líneas): patrón command y timeline de operaciones,
incluidos los comandos de condiciones CAD/CAE (`ConditionCommandBase` →
`build_condition()`, llamado una sola vez).

---

## Conditions

**IMPLEMENTADO**

`core/conditions.py` (287 líneas): sistema de condiciones CAD/CAE reutilizables
exigido por `prompts.md`:

- Tipos: `LoadCondition`, `ElasticityCondition`, `ObstructionCondition`,
  `ProtectedRegion` (`core/conditions.py`).
- `ConditionManager`: registro, `consume_conditions()` y `resolve()` (deduplica ids).
- Comandos tipo condición → Feature → `FeatureHistory` → timeline → árbol de diseño.
- UI: panel de condiciones, menú superior "Condiciones" y nodo "Condiciones" en el
  design tree (`desktop/ui/panels/design_tree.py`).
- Consumidas **por id** por estudios de optimización y diseño generativo, sin duplicarse.
- Validado con `test_conditions.py` (272 líneas) y `test_pruebas_base.py`.

---

## Boolean

**IMPLEMENTADO**

Operación booleana CAD funcional e integrada (ver `prompts.md`):

- **Menú superior**: `Operaciones → Boolean → {Unión, Corte, Intersección}`.
- **Panel Qt** (`desktop/ui/panels/boolean_panel.py`): tipo de operación,
  cuerpo objetivo, cuerpos herramienta, conservar herramientas, Aceptar/Cancelar.
- **Selección** reutiliza el `SelectionManager` existente (captura de cuerpos
  objetivo/herramienta desde el viewport).
- **Ejecución CAD** por cuerpos (`services/cad_service.py::boolean_bodies`):
  unión / corte / intersección sobre cuerpos de un compuesto, reensamblado del
  modelo y almacenado como nuevo modelo.
- **Keep tools**: ON mantiene las herramientas; OFF las consume (sin ocultarlas
  solo visualmente).
- **Feature + Timeline + Design Tree**: `Boolean <op>` en `FeatureHistory`,
  timeline en modo features y árbol de diseño actualizado.
- **Validación**: cuerpo objetivo obligatorio, ≥1 herramienta, herramienta ≠
  objetivo, operación válida, índices en rango. Los errores CAD conservan el
  modelo anterior sin crear Feature.
- **Cancelación**: no crea Feature ni modifica el modelo.
- Validado con `test_boolean_operation.py` (19 casos).

---

## Mesh

**IMPLEMENTADO**

`core/meshing.py` (478 líneas): mallado desde STEP, mallado adaptativo y mallado básico.
- Fase 2 completada: **physical groups de gmsh** → submodelparts de Kratos
  (`MeshResult.physical_groups`, `_emit_physical_groups`, `_nodes_for_physical_groups`).
- Validado con `test_fase2_physical_groups.py` y `test_gmsh_mesher.py`.

---

## FEA

**IMPLEMENTADO**

- `core/fea.py` (335 líneas): montaje y solución FEA elemental (SIMP local).
- `core/solver_interface.py`: interfaz de solver; `create_kratos_fea_solver` propaga
  physical groups.
- `core/boundary.py`: condiciones de contorno (cargas/restricciones).
- `core/study.py`, `core/cae_studies.py`: estudios CAE y casos de carga.

---

## Kratos

**IMPLEMENTADO**

Kratos Multiphysics autocontenido instalado vía pip en `.venv` (no conda):

- `KratosMultiphysics==10.4.3`, `KratosStructuralMechanicsApplication==10.4.3`,
  `KratosOptimizationApplication==10.4.3`, `kratoslinearsolversapplication==10.4.3`.
- Integración en `core/kratos_adapter.py` (importa formato core → Kratos, submodelparts
  por physical groups).
- Extra `kratos` en `pyproject.toml` con los pins exactos; `addopts = "-m 'not slow'"`.
- Fallback local funcional (`benchmarks/test_kratos_fallback.py` pasa).

---

## Structural Optimization

**IMPLEMENTADO**

- `core/topopt.py` (373 líneas): motor SIMP de optimización topológica.
  - Subdominios: `set_preserved_elements()` / `set_void_elements()`; actualización OC y
    `volfrac` restringidos al **dominio activo** `~(preservado | vacío)`.
  - Preservados fijos a `1.0`, vacíos fijos a `rho_min`; resultado con máscaras
    `preserved_elements` / `void_elements`.
  - Consume las condiciones compartidas (ver Conditions).
- `core/optimization_studies.py`: parámetros de optimización (`TopOptParameters`).

---

## Generative Design

**IMPLEMENTADO**

- `core/generative.py` (170 líneas): backbone del estudio (`GenerativeDesignStudy`,
  escenarios A y B, `DesignSpace`, configs). `validate()` acepta **o** `loads` **o**
  `conditions` **o** `constraints`.
- `core/generative_engine.py` (368 líneas, nuevo): motor real puro Python —
  `generate_bridge_mesh` (hex → 6 tets), `consume_conditions`, `direction_vector`
  (perpendicular / paralela / ángulo + sentido), `GenerativeDesignEngine.solve_simp`
  (traduce condiciones → fuerzas/fijaciones/preservados/vacíos) y
  `run_generative_design` (escenarios A y B + reconstrucción). Sin skimage/OCSMeshing.
- Los métodos de generación `VOXEL_FILL` / `LEVEL_SET` / `GROWTH` / `AI_GUIDED` quedan
  como configuración (`GenerationMethod`); el algoritmo real implementado es SIMP sobre
  malla puente (escenario B) y sobre la geometría existente (escenario A).
- Validado con `test_resolved_pendientes.py` (8 tests).

---

## CAD Reconstruction

**IMPLEMENTADO**

`core/cad_reconstruction.py` (435 líneas): conversión resultado volumétrico/malla → B-Rep.

- `MarchingTetrahedraExtractor`: isosuperficie real (densidades por elemento → nodos,
  dedup de vértices por posición).
- `OCPBRepFitter`: sewing → wiring → solid → exportación **STEP** (vía OCP).
- `ReconstructionPipeline` con componentes reales por defecto; política "best effort":
  devuelve el mejor resultado disponible (SURFACE_MESH completed como mínimo).
- Pendiente: robustez B-Rep sobre isosuperficies ruidosas (post-proceso de malla).

---

## UI

**IMPLEMENTADO**

`desktop/ui/main_window.py` (1149 líneas): menús (Archivo, Editar, Diseño, Herramientas,
Ayuda), selección de perfil de navegación, estados de licencia, pipeline de 5 pasos,
barra de estado.

---

## License

**IMPLEMENTADO (abstracción)**

`core/license.py`: `LicenseManager` (estados LICENSED/TRIAL/EXPIRED/INVALID/
OFFLINE_GRACE_PERIOD), protocolo `LicenseServerProtocol`, `NoOpLicenseServer`.

- CAD/malla/FEA/optimización/visualización funcionan 100 % localmente.
- Internet se usa únicamente para la futura validación de licencia/suscripción.
- **No** hay backend comercial implementado (solo la abstracción).
- Validado con `test_license_manager.py`.

---

## Notas de estado actual (this cycle)

- `Camera` renombrada a `CameraController` (sistema independiente de la navegación).
- Corregido un bug de deriva de la caché de distancia en el zoom (dolly): ahora opera
  sobre el estado real de la cámara VTK.
- Tests nuevos de cámara/navegación en `test_camera_controller.py` (16 casos).
- `prompt.md` → `prompts.md` (solo el prompt vigente); `prompt_investigacion.md` eliminado
  (prompt anterior).
- **Condiciones CAD/CAE reutilizables** implementadas y consumidas por id (ver Conditions).
- **Pendientes resueltos**: SIMP consumidor (subdominios preservado/vacío), motor de
  diseño generativo real, reconstrucción B-Rep real (STEP). Ver `RESUMEN_IMPLEMENTACION.md`
  (sección "INTERVENCIÓN - SISTEMA DE CONDICIONES REUTILIZABLES + PENDIENTES RESUELTOS...").
- Verificación: suite completa **176 passed, 6 deselected, 1 warning**.
- Pendientes reales: mapeo obstrucciones→elementos sin `model_shape`; rendimiento del
  marching tetrahedra; robustez del B-Rep sobre isosuperficies ruidosas.
