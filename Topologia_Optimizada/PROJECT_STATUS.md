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

> **Convención de navegación (corregida, 2026):** órbita, pan y zoom siguen la
> convención CAD "el modelo sigue al cursor" (arriba → la pieza sube; derecha →
> la pieza gira a la derecha; rueda arriba → acercar). Detalle de signos y
> causa raíz (el `QVTKRenderWindowInteractor` invierte la Y de Qt) en
> [`docs/NAVIGATION_CONVENTION.md`](docs/NAVIGATION_CONVENTION.md).

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

`core/commands.py` (≈1060 líneas): patrón command y timeline de operaciones,
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

## Transform

**IMPLEMENTADO**

Transformación CAD (trasladar / rotar / escalar) integrada de extremo a extremo:

- **Comando**: `TransformCommand` (`core/commands.py`) — tipo de transformación,
  traslación, eje/ángulo de rotación, factor de escala y cuerpo objetivo.
- **Menú superior**: `Operaciones → Transformar...` y botón de cinta **Transformar**
  (`desktop/ui/main_window.py`).
- **Panel Qt** (`desktop/ui/panels/transform_panel.py`): tipo de transformación,
  cuerpo capturado desde el viewport (reutiliza `SelectionManager` vía
  `get_solid_selections`) y parámetros según tipo, Aceptar/Cancelar.
- **Ejecución CAD** (`PipelineController::_execute_transform` →
  `CADService::transform_bodies`): la geometría real se modifica y se almacena como
  **nuevo modelo activo** (`model_id` actualizado).
- **Invalidación**: al cambiar la geometría se limpian la malla FEM, resultados y
  tessellation anteriores y se re-tessela el nuevo modelo para el viewport.
- **Feature + Timeline + Design Tree**: `Transform <tipo>` en `FeatureHistory` /
  `Document`, timeline y árbol de diseño actualizados.
- **Validación**: cuerpo obligatorio, tipo válido, factor de escala > 0.
- Validado con `test_edit_operations.py`.

---

## Mirror

**IMPLEMENTADO**

Simetría (espejo) de un sólido respecto a un plano, integrada de extremo a extremo:

- **Comando**: `MirrorCommand` (`core/commands.py`) — punto del plano, normal,
  `keep_original` y cuerpo objetivo.
- **Menú superior**: `Operaciones → Simetría...` y botón de cinta **Simetría**.
- **Panel Qt** (`desktop/ui/panels/mirror_panel.py`): cuerpo capturado desde el
  viewport, punto y normal del plano, conservar original, Aceptar/Cancelar.
- **Ejecución CAD** (`PipelineController::_execute_mirror` →
  `CADService::mirror_bodies`): se refleja el cuerpo y se almacena como nuevo
  modelo activo.
- **Corrección**: el plano ahora se define por su **normal** y un **punto** sobre el
  plano (antes el código pasaba el punto como dirección, produciendo un error de
  normal cero).
- **Invalidación** y **Feature/Timeline/DesignTree** igual que Transform.
- **Validación**: cuerpo obligatorio, normal no nula.
- Validado con `test_edit_operations.py`.

---

## Pattern

**IMPLEMENTADO**

Patrón lineal / rectangular / circular de un sólido, integrado de extremo a extremo:

- **Comando**: `PatternCommand` (`core/commands.py`) — tipo, direcciones, cantidades,
  separación, eje, centro y ángulo.
- **Menú superior**: `Operaciones → Patrón...` y botón de cinta **Patrón**.
- **Panel Qt** (`desktop/ui/panels/pattern_panel.py`): tipo de patrón, cuerpo
  capturado desde el viewport y parámetros según tipo, Aceptar/Cancelar.
- **Ejecución CAD** (`PipelineController::_execute_pattern` →
  `CADService::pattern_bodies`): se generan los ejemplares y se almacena como nuevo
  modelo activo.
- **Centro del patrón circular corregido**: antes la geometría rotaba siempre
  alrededor del origen `(0,0,0)`; ahora usa el parámetro **`center`** definido por el
  usuario/comando (rotación alrededor del eje que pasa por ese punto).
- **Invalidación** y **Feature/Timeline/DesignTree** igual que Transform.
- **Validación**: cuerpo obligatorio, cantidad ≥ 2, segundo-direction ≥ 1.
- Validado con `test_edit_operations.py` (incluye centro circular ≠ origen).

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

## Motor Dual FEA (local ↔ Kratos)

**IMPLEMENTADO Y VERIFICADO**

Ruta verificable cerrada (prompt "Cierre del motor dual FEA"): mismo problema → dos motores →
resultados físicos → comparación automatizada.

- **Motor local** (`core/fea.py`): Tet4 lineal estático NumPy/SciPy, `success` con convergencia
  real (no artificial), default del desktop. Sin cambios.
- **Motor Kratos** (`core/kratos_adapter.py` + `core/solver_interface.py`): consume las mismas
  condiciones vía `core/kratos_bridge.py` y resuelve el mismo problema físico.
- **Carga real ensamblada (fix del RHS en cero):** `KratosAdapter.apply_loads_to_model_part()`
  crea `PointLoadCondition3D1N` reales por nodo de carga con `POINT_LOAD`. El
  `ResidualBasedBlockBuilderAndSolver` ensambla la carga en el RHS (`K·u=f`), eliminando el
  warning `setting the RHS to zero` y el `u=0` anterior.
- **Restricciones con error claro:** una condición explícita (cara/selection) que no se puede
  mapear a nodos produce un error (`create_kratos_fea_solver` lanza), NO una región alternativa
  silenciosa ni una restricción en todos los nodos.
- **Convergencia real:** la verificación/re-resolución de `run_analysis` (amgcl iterativo →
  verificación de estabilidad → fallback skyline_lu) se conserva; con RHS no vacío, `success`
  ya representa convergencia física.
- **Cross-engine automatizado** (`test_cae_cross_engine.py`): mismo caso en ambos motores,
  `‖u_l − u_k‖/‖u_l‖ ≤ 1e-8`, compliance relativo ≤ 1e-6. Detecta regresiones del bridge/cargas/
  restricciones/ensamblado.
- **Cargas superficiales/distribuidas (`LoadType.DISTRIBUTED`):** el cross-engine cubre
  explícitamente el caso de carga superficial: la magnitud TOTAL se reparte por nodo
  (`mag / len(nodos)`) — la misma semántica del motor local — y cada nodo se materializa como
  una `PointLoadCondition3D1N` real (`test_cross_engine_distributed_surface_load_agrees`).
  `apply_loads_to_model_part` es idempotente (no duplica condiciones si se reinvoca).
- **`LoadType.PRESSURE` sin modelo de área → error claro:** el sistema no integra área de
  superficie, por lo que Pa→N (Pa × área) no se puede resolver; en vez de tratar Pa como N
  (error físico silencioso) se lanza `ValueError` (`test_pressure_load_without_area_fails_clearly`).
- **Verificación:** suite completa **320 passed, 6 deselected, 1 warning** (`.venv` y
  `runtime/python`). Tras la reorganización de tests en `tests/` (y retiro de 2 de diagnóstico a
  `tests_obsoletos/`): **321 passed, 6 deselected**.

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
  - `TopologyOptimizationStudy.validate()` requiere **al menos un sólido** en `parts`,
    todos de tipo SOLID, del mismo `model_id`. Acepta condiciones reutilizables por id
    **o** la config heredada `loads`/`constraints`.

---

## Studios end-to-end (CAD/CAE)

**IMPLEMENTADO**

Flujo integrado y verificable (STEP → selección real → estudio → malla → SIMP
→ resultado → UI), sin rediseñar la UI existente:

- **Selección real de pieza**: el usuario selecciona sólido(s) desde el viewport
  (`_current_solid_selections()` en `main_window.py` → `SelectionManager` → `CadEntityRef`).
  Las selecciones se pasan a `StudyPanel` como `parts` y se almacenan en
  `TopologyOptimizationStudy.parts`.
- **Crear estudio**: `desktop/ui/panels/study_panel.py` (`StudyPanel`) — muestra las
  piezas seleccionadas, nombre, tipo (Topology Optimization/SIMP), parámetros de
  optimización, botón **"Capturar desde selección"** (recaptura los sólidos del
  viewport reutilizando el `SelectionManager` vía `get_solid_selections`, sin crear
  una interfaz paralela), y selección de condiciones reutilizables. Rechaza
  explícitamente cero piezas, entidades no-SOLID, y model_id incompatible.
- **Menú superior "Estudio"**: `Nuevo estudio de optimización...` y
  `Ejecutar estudio (topología)` (`desktop/ui/main_window.py`).
- **Registro y ejecución**: `PipelineController.register_study()` →
  `execute_study()` (valida, DRAFT→RUNNING→COMPLETED/FAILED) en **background**
  (`run_in_background`), reutilizando Properties / Results / DesignTree / Timeline /
  Viewport.
  - `execute_study()` usa `study.parts` para **resolver el sólido seleccionado como
    dominio determinista** (`_resolve_study_solid_index` → `generate_mesh_for_solid`),
    nunca el primer sólido implícito ni el compuesto completo. Valida que el sólido
    seleccionado sea resolvable en el modelo (índice en rango) y rechaza con error
    claro (`invalid_part` / `unresolvable_part` / `no_solids`) un sólido imposible de
    resolver.
  - Malla automática: si no existe malla (o cambia el sólido seleccionado) se genera
    la malla del sólido específico (`CADService.generate_mesh_for_solid` vía
    `generate_mesh_for_shape`, reutilizando los meshers gmsh/provisional existentes —
    sin nuevo sistema de mallado).
  - Las condiciones se consumen por id vía `study.consume_conditions(manager)` →
    se pasan al solver SIMP via `run_optimization(conditions=...)`.
- **Resultado/estado**: `StudyResult` → `document.add_result()`, panel de resultados y
  visualización de densidad en el viewport; errores explícitos cuando el estudio no
  está configurado o la condición no está soportada.
- **Tests**: `test_study_pipeline.py` (53 tests) cubre selección → CadEntityRef →
  study.parts → validación → dominio determinista (sólido seleccionado ≠ primer
  sólido, recaptura de selección en el panel) → condiciones → solver → resultado → UI.
- Verificación: suite completa **321 passed, 6 deselected** (estado actual tras la
  reorganización de tests en `tests/`).

---

## Generative Design

**IMPLEMENTADO**

- `core/generative.py` (170 líneas): backbone del estudio (`GenerativeDesignStudy`,
  escenarios A y B, `DesignSpace`, configs). `validate()` acepta **o** `loads` **o**
  `conditions` **o** `constraints`.
- `core/generative_engine.py` (nuevo): motor real puro Python —
  `generate_bridge_mesh` (hex → 6 tets), `consume_conditions`, `direction_vector`
  (perpendicular / paralela / ángulo + sentido), `GenerativeDesignEngine.solve_simp`
  (traduce condiciones → fuerzas/fijaciones/preservados/vacíos) y
  `run_generative_design` (escenarios A y B + reconstrucción). Sin skimage/OCSMeshing.
  - **Obstrucciones por cuerpo → elementos**: con `model_shape`, `_void_elements` mapea
    los sólidos obstructivos a elementos de malla por centroide (con `offset_mm`); solo
    cuando **no** hay forma CAD se devuelve el marcador
    `result["_unsupported_conditions"]` (sección 6 — nunca un resultado silenciosamente
    incorrecto).
- Los métodos de generación `VOXEL_FILL` / `LEVEL_SET` / `GROWTH` / `AI_GUIDED` quedan
  como configuración (`GenerationMethod`); el algoritmo real implementado es SIMP sobre
  malla puente (escenario B) y sobre la geometría existente (escenario A).
- Validado con `test_resolved_pendientes.py` (9+ tests).

---

## CAD Reconstruction

**IMPLEMENTADO**

`core/cad_reconstruction.py` (≈750 líneas): conversión resultado volumétrico/malla → B-Rep.

- `MarchingTetrahedraExtractor`: isosuperficie real (densidades por elemento → nodos,
  dedup de vértices vectorizado con structured-array `np.unique` — mejora de rendimiento).
- `OCPBRepFitter`: sewing → wiring → solid → exportación **STEP** (vía OCP). Rechaza
  explícitamente triángulos degenerados (área cero) antes del sewing para que una
  isosuperficie ruidosa no corrompa el B-Rep (robustez).
- `ReconstructionPipeline` con componentes reales por defecto; etapa `SMOOTHED_MESH`
  (pulido Laplaciano con bordes fijos) aplicada antes del fitting, preferida sobre la
  malla cruda; **hole-filling** (`fill_holes` / `MeshHoleFiller`) cierra automáticamente
  huecos en shells abiertos no-manifold antes del fitting B-Rep (fan triangulation por
  boundary loop); política "best effort": devuelve el mejor resultado disponible (B-Rep o
  malla de superficie suavizada).
- Validado con `test_resolved_pendientes.py` (tests de dedupe, pulido, robustez B-Rep y
  hole-filling).

---

## UI

**IMPLEMENTADO**

`desktop/ui/main_window.py` (≈1495 líneas): menús (Archivo, Editar, Diseño, Herramientas,
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
- **Flujo CAD/CAE end-to-end cerrado**: creación/ejecución de estudios de optimización
  (menú "Estudio", `StudyPanel`), validación que acepta condiciones **o** la config
  heredada `loads`/`constraints`, y marcador explícito de condiciones no soportadas
  (`_unsupported_conditions`) — nunca un resultado silenciosamente incorrecto.
- **Pendientes resueltos**: SIMP consumidor (subdominios preservado/vacío), motor de
  diseño generativo real, reconstrucción B-Rep real (STEP), hole-filling en shells abiertos
  no-manifold, **selección real de sólido → estudio** (StudyPanel recibe partes del
  viewport, validación SOLID, model_id automático, malla automática en execute_study).
  Ver `RESUMEN_IMPLEMENTACION.md` (sección "INTERVENCIÓN - SISTEMA DE
  CONDICIONES REUTILIZABLES + PENDIENTES RESUELTOS...").
- Verificación: suite completa **270 passed, 6 deselected, 1 warning**.
- **Post-proceso de malla implementado**: `MeshSmoother` / `smooth_surface_mesh`
  (Laplaciano con bordes fijos) como etapa `SMOOTHED_MESH` del pipeline, aplicado antes
  del fitting B-Rep y usado de forma preferente (fallback a la malla cruda). Reduce el
  ruido de isosuperficies; la conectividad no cambia.
- **Pendientes funcionales cerrados** (this cycle):
  - **STEP export real del pipeline de reconstrucción**: `ReconstructionPipeline` ahora
    acepta `step_path` y registra el `STEP_FILE` como `COMPLETED` cuando el `OCPBRepFitter`
    exporta el sólido; `run_generative_design(..., step_path=...)` lo propaga
    (`core/cad_reconstruction.py`, `core/generative_engine.py`).
  - **Parámetros de optimización del estudio en el generativo**: `run_generative_design`
    pasa ahora `volume_fraction`, `max_iterations`, `penalization`, `filter_radius` y
    `convergence_tolerance` de `GenerativeDesignStudy.optimization_params` a `solve_simp`
    (antes usaba defaults fijos).
  - **Aviso visible de condiciones no soportadas**: `_on_run_study` abre un
    `QMessageBox.warning` además del mensaje de la barra de estado cuando hay condiciones
    que no pudieron mapearse (`desktop/ui/main_window.py`).
  - **Selector de colormap en la UI**: el botón "Visualizar" permite elegir entre
    `jet`, `viridis`, `coolwarm`, `inferno`; `Viewport3D.show_density(colormap=...)`
    lo propaga a la escena.
- Pendientes reales restantes (documentados):
  - **`ThermalAnalysis`** / **`ModalAnalysis`**: *scaffolded* pero sin solver numérico
    integrado todavía (`core/cae_studies.py`). La integración futura es ahora un cambio
    localizado (ver abajo). No devuelven `not_implemented` ciego; reportan
    `not_implemented` claro vía `StudyNotImplementedError` o `validation_failed` con
    mensaje específico.
- **Scaffolding de Thermal/Modal para futura integración (this cycle)**:
  - **Materiales**: `core/materials.py` añade propiedades térmicas opcionales y
    retrocompatibles (`thermal_conductivity`, `specific_heat`, `thermal_expansion`,
    `has_thermal_properties`, `with_thermal_properties()`); los presets estándar no
    cambian.
  - **Modelo de datos térmico** (`core/cae_studies.py`): `ThermalBoundary`/
    `ThermalBoundaryType` (TEMPERATURE / HEAT_FLUX / CONVECTION), `Study.thermal_boundaries`
    y `add_thermal_boundary()`; validación con mensaje específico (modelo, conductividad
    térmica, ≥1 condición).
  - **Modelo de datos modal**: `ModalParameters` (`mode_count`, `frequency_min/max`),
    `Study.modal`; validación (modelo, ≥1 constraint para quitar modos de cuerpo rígido,
    parámetros válidos).
  - **Contrato de integración documentado** en cada clase: qué ensamblar (K/M), qué
    resolver (ecuación de calor estacionaria / eigen-problema generalizado) y qué
    devolver (`temperatures`, `frequencies`, `mode_shapes`).
  - **Pipeline** (`controller.execute_study`): dispatch explícito para `thermal`/`modal`;
    estudio inválido -> `validation_failed` con mensaje específico; válido pero sin solver
    -> `not_implemented` claro (sin romper el flujo). La validación genérica ahora respeta
    `validate_with_message()` si el estudio la define.
  - Validado con `test_cae_studies_scaffold.py` (20 casos).
  - Verificación: suite completa **290 passed, 6 deselected, 1 warning**.
- **Default del solver iterativo alineado con Kratos oficial**:
  - El default `AMGCL` del adaptador (`core/kratos_adapter.py::_DEFAULT_AMGCL_SETTINGS`)
    se ajustó a la referencia oficial de `AMGCLSolver::GetDefaultParameters`
    (`krylov_type: gmres`, `coarsening_type: aggregation`, `smoother_type: ilu0`,
    `max_iteration: 100`), dejando atrás `cg`+`smoothed_aggregation`.
  - Verificado empíricamente en este build: `gmres`+`aggregation` construyen y
    **convergen** (compliance idéntica a `skyline_lu`) sobre la malla de referencia;
    `ruge_stuben` sigue sin soporte. Sin regresión: suite completa 270 passed.
  - Mismos ajustes en `benchmarks/benchmark_fase0.py` (preset `amgcl`) y
    `benchmarks/test_kratos_fallback.py` (`AMG_OK`). El fallback a `skyline_lu`
    por no convergencia se mantiene operativo.
- **Operaciones CAD de edición cerradas (this cycle, ver prompts.md)**:
  - **Transform / Mirror / Pattern** ahora se ejecutan **realmente** a través del
    pipeline (`PipelineController::_execute_transform/_execute_mirror/_execute_pattern`
    → `CADService::transform_bodies/mirror_bodies/pattern_bodies`), en lugar de solo
    registrarse como Feature.
  - Miradas: flujo completo `Selección → UI → Command → Validación → Pipeline →
    CADService → Geometría real → Modelo activo → Viewport → FeatureHistory/Document →
    DesignTree → Tests`, con invalidación de malla/resultados al cambiar la geometría.
  - **Centro del patrón circular corregido**: la rotación usa el `center` del comando
    en lugar del origen.
  - **Mirror corregido**: el plano se define por normal + punto (antes el punto se
    trataba como dirección, dando normal cero).
  - Nuevas UI: `desktop/ui/panels/{transform,mirror,pattern}_panel.py` + menú
    "Operaciones" y cinta.
  - Validado con `test_edit_operations.py` (27 casos).
- Verificación: suite completa **320 passed, 6 deselected, 1 warning**.
- **Sincronización de estado CAD + resolución determinista de sólidos (this cycle)**:
  - **`_finalize_cad_result`** ahora sincroniza también **`Document`** (registra el nuevo
    modelo vía `document.set_model(cad_model)` → `active_model_id`) y **`model_name`**
    (toma el nombre del nuevo modelo, e.g. "Transform translate"). Antes `model_id` cambiaba
    pero Document/`model_name` quedaban en el modelo STEP anterior.
  - **Boolean consolidado**: `_execute_boolean` ahora usa el mismo `_finalize_cad_result`
    (antes duplicaba la invalidación y no sincronizaba Document/`model_name`).
  - **`resolve_solid_for_face`**: eliminado el fallback peligroso que asignaba `solid_0`
    arbitrariamente cuando no se podía determinar el sólido; ahora devuelve `None`
    (fallo controlado) en casos ambiguos de modelos multi-cuerpo.
  - Validado con `test_edit_operations.py` (nuevos tests de sincronización Document/
    `model_name` y de resolución determinista).
  - Verificación: suite completa **292 passed, 6 deselected, 1 warning**.

---

## Auditoría flujo CAE completo (this cycle)

Auditoría end-to-end revisada según `prompts.md` (CAD → Condiciones → Mallado → FEA →
Topología → Reconstrucción CAD → Resultado). No se rehízo arquitectura ni se reemplazaron
sistemas funcionales; solo se conectaron las desconexiones CRITICAS/ALTAS dentro de la
arquitectura existente.

### Qué estaba REALMENTE implementado (verificado)
- **CAD import/tessellation**: `CADService` + `StepAdapter` (STEP → `cq.Shape` → malla).
- **Condiciones reutilizables**: `core/conditions.py` (`ConditionManager`, `resolve()`,
  `consume_conditions()`) que el estudio y el generativo consumen **por id**.
- **Mallado**: `core/meshing.py` + gmsh (provisional) con `physical_groups`.
- **FEA local**: `core/fea.py` (`FEASolver` + `solve_fea`, Tet4 NumPy/SciPy) — resultados
  **reales**, no simulados.
- **Topología**: `core/topopt.py` (SIMP real) consumiendo condiciones vía
  `GenerativeDesignEngine.solve_simp`.
- **Reconstrucción CAD**: `core/cad_reconstruction.py` (`MarchingTetrahedraExtractor`,
  `OCPBRepFitter`, hole-filling, STEP export).

### Qué estaba desconectado o incompleto
- **CRITICO — Reconstrucción al CAD**: el sólido B-Rep reconstruido (`TopoDS_Solid`) se
  descartaba: `ReconstructionResult.to_dict()` soltaba `data` y ninguna ruta lo registraba
  como `CADModel` activo ni lo devolvía a Document/historial/DesignTree.
- **CRITICO — Condiciones → FEA**: la ruta "Análisis FEM" (`run_fea`/`build_problem`)
  usaba SOLO los arrays planos `self.forces`/`self.constraints`; las condiciones reutilizables
  del `ConditionManager` nunca llegaban al solver FEA local (el generativo/optimización sí).
- **ALTO — BC incoherente**: cuando una **cara real seleccionada** no podía mapearse a nodos,
  la ruta local caía silenciosamente a nodos por coordenada min/max, mientras la ruta Kratos
  prohíbe ese fallback (comportamiento contradictorio).
- Dato de arquitectura (no defecto): co-existen dos stacks **reales** — el local
  (NumPy/SciPy Tet4 + SIMP + generative engine) es el que usa el desktop; el adaptador Kratos
  (`core/kratos_adapter.py`, `create_kratos_fea_solver`) queda desconectado del flujo del
  controlador (solo se instancia en tests/benchmarks). No se eliminó: es un sistema funcional.

### Qué se corrigió (sin reemplazar sistemas)
- **Reconstrucción → CADModel** (`desktop/pipeline/controller.py` +
  `core/generative_engine.py`):
  - `_reconstruct` expone ahora el sólido B-Rep en `reconstruction["data"]` cuando la etapa
    `BREP_SOLID` completa.
  - Nuevo `_register_reconstruction_model()`: envuelve el sólido como `cq.Shape`, lo registra
    vía `store_computed_shape`, lo activa (controller + `Document.set_model`), lo re-tessela
    para viewport/exportación, y registra un Feature de reconstrucción en `FeatureHistory`/
    `Document` (DesignTree). Es **best-effort**: si no hay sólido o el layer CAD no puede
    almacenarlo, nunca falla el estudio. El sólido crudo se consume del dict (no llega a UI).
  - La rama `generative_design` de `execute_study` ahora además expone `self.result` /
    `self.result_densities` para que el resultado SIMP quede visualizable.
- **Condiciones → FEA** (`core/generative_engine.py` + `desktop/pipeline/controller.py`):
  - Eliminada la duplicación de mapeo: extraído `_map_conditions_to_problem()`
    (cargas/elasticidad → fuerzas/fijaciones + preservados/vacíos) y
    `build_fea_problem()` (público, para FEA), reutilizado por `solve_simp`.
  - `run_fea(conditions=...)` consume ahora las condiciones reutilizables del
    `ConditionManager` y las traduce al solver local, igual que `run_optimization`.
- **BC coherente**: en la ruta con condiciones, una carga/soporte con **cara seleccionada**
  que no se puede mapear **falla con error claro** (`ValueError` listando el tipo), nunca
  se reubica silenciosamente; el default por coordenadas solo aplica cuando **no** hay cara
  seleccionada (legítimo). `solve_simp` conserva su comportamiento permisivo previo.

### Puente Kratos/local cerrado en `run_fea` (this cycle)
- **Nuevo `core/kratos_bridge.py`**: traduce las mismas condiciones reutilizables a
  definiciones FEA de Kratos: `LoadCondition → LoadDefinition` (magnitud, dirección vía el
  `direction_vector` compartido, `application_face_id`, `selection` = `FaceRegion`),
  `ElasticityCondition → ConstraintDefinition` (FIXED, `location_face_id`, `selection`
  `FaceRegion`). Las condiciones de obstrucción/región protegida (no-FEA) se saltan. La
  dirección y la selección por cara son **idénticas** a las de `GenerativeDesignEngine`, de
  modo que el solve local y el de Kratos seleccionan los mismos nodos.
- **`run_fea(backend="local"|"kratos")`** (`desktop/pipeline/controller.py`): el **local sigue
  siendo el default** (nada regresiona). Con `backend="kratos"` se construye el solver vía
  `create_kratos_fea_solver`, propagando `self.mesh["physical_groups"]` → submodelparts Kratos
  (con exactitud de nodos por cara de CAD) y las definiciones traducidas. Conserva el mismo
  contrato estricto que la ruta FEA local: una cara seleccionada que no se puede mapear se
  reporta, nunca se reubica. Si Kratos no está disponible o `physical_groups` faltan, se
  degrada/reporta sin romper el flujo local.
- La optimización **SIMP sigue siendo local** (sin reemplazar ni refactorizar su núcleo): el
  gap se cerró en la etapa de análisis FEM, que es donde `create_kratos_fea_solver` está
  diseñado para enchufarse.

### Archivos modificados
- `core/generative_engine.py` (refactor de mapeo + `build_fea_problem` + `_reconstruct` expone el sólido).
- `desktop/pipeline/controller.py` (`_register_reconstruction_model`, `run_fea(conditions=...)`,
  `backend="kratos"` + `_run_fea_kratos`, rama `generative_design` de `execute_study`).
- `core/kratos_bridge.py` (nuevo: puente condiciones → definiciones FEA de Kratos).
- `test_cae_audit_fixes.py` (existente) y `test_cae_kratos_bridge.py` (nuevo, 11 tests del puente
  + cableado real de `run_fea(backend="kratos")`).

### Tests ejecutados y resultado
- `test_cae_audit_fixes.py`: **7 passed**.
- `test_cae_kratos_bridge.py`: **11 passed**.
- `benchmarks/test_run_fea_kratos_e2e.py` (ahora `tests/benchmarks/test_run_fea_kratos_e2e.py`):
  **3 passed** (solve nativo real de Kratos).
- Suite completa: **313 passed, 6 deselected, 1 warning** baseline FEA (→ +2 de diagnóstico RHS
  en este ciclo = **315 passed** en total, sin regresiones).

### Verificación end-to-end real completada (this cycle)
- **`benchmarks/test_run_fea_kratos_e2e.py`** ejecuta un **solve nativo real de Kratos**
  vía `run_fea(conditions=..., backend="kratos")` sobre la malla de referencia
  `small_500` (206 nodos / 643 tets) y confirma:
  1. La malla se importa de verdad (mismos nodos/elementos que el mesh).
  2. El pipeline completo corre: material, DOFs, BCs geométricos, solve y extracción.
  3. El bridge traduce las condiciones reutilizables a definiciones FEA.
  4. El solve **local** (NumPy) con las MISMAS condiciones produce compliance > 0 y
     sigue siendo el default.
- **Cross-engine verificado** (`test_cae_cross_engine.py`): mismo caso físico resuelto en
  ambos motores con `‖u_l − u_k‖/‖u_l‖ ≤ 1e-8` y compliance relativo ≤ 1e-6.
- La ruta **RHS-force está corregida**: se crean `PointLoadCondition3D1N` reales que el
  `BuilderAndSolver` ensambla, eliminando el warning `setting the RHS to zero`.

### Qué queda (estado real)
- El **default del desktop es el stack local** (NumPy/SciPy/SIMP); `backend="kratos"` es una
  vía opcional real en `run_fea`, verificada end-to-end con solve nativo.
- La **optimización SIMP usa el solver local** por diseño (no se refactorizó su núcleo); Kratos se
  integra en el FEA. Thermal/Modal siguen **scaffolded** sin solver numérico (intencional,
  arquitectura correcta).

**Decisión sobre `run_optimization` con Kratos**
- **No exponer Kratos en SIMP por ahora.** El motor SIMP (`core/topopt.SIMPSolver`) está
  acoplado a su `FEASolver` interno (``assemble_global_stiffness`` / ``apply_bc_and_solve`` /
  ``element_stiffness``) y el callable de Kratos devuelve un dict, no esa interfaz; alinear
  ambos requeriría refactorizar el núcleo que toda la optimización usa, contraviniendo
  "no reemplaces sistemas funcionales". La etapa de análisis FEM (donde Kratos sí encaja y
  ahora funciona con carga real) ya es opcional vía `backend="kratos"`.

### Decisión de arquitectura: dos motores FEA vs Kratos completo (this cycle)
**Pregunta resuelta:** ¿vale la pena mantener los dos motores y, sobre todo,
implementar Kratos **completo** como motor principal del desktop?

**Ventaja de mantener los dos motores (local como default + Kratos opcional):**
- **Verificación cruzada (oráculo mutuo):** dos implementaciones independientes de la misma
  física lineal permiten comparar compliance/desplazamientos. Si coinciden, la confianza es
  mayor que con un solo motor. Es el uso real de `benchmarks/test_run_fea_kratos_e2e.py`.
- **Determinismo y velocidad al iterar:** el motor local (NumPy/SciPy) arranca en segundos y
  no carga el binario nativo de Kratos (~1-2 min al importar), ideal para desarrollo de UI,
  reconstrucción y SIMP.
- **Independencia del runtime de Kratos:** Kratos es una dependencia nativa grande y
  **opcional**. El motor local funciona siempre y no hereda bloqueos del binario.
- **Red de seguridad:** si mañana Kratos falla o no está desplegado, el desktop sigue
  operando. No hay punto único de fallo.
- **Camino de migración sin riesgo:** el local actúa como baseline de referencia para validar
  cualquier mejora del lado Kratos.

**Ventajas de Kratos COMPLETO como motor principal (las reales, para decidir a futuro):**
- **Escalado a mallas grandes / problemas de producción:** Kratos es C++ paralelo (OpenMP) con
  solvers robustos (skyline_lu / sparse_lu / amgcl + fallback de convergencia); el local es más
  lento y con mayor huella de RAM por encima de decenas de miles de tets.
- **Solvers lineales variados y robustos** frente a `scipy.sparse.linalg.spsolve`.
- **Física avanzada futura** (contactos, no-linealidad, térmico/modal reales — hoy scaffolding),
  que el motor self-contained no cubre.
- **Estrategia comercial / IP (README §26):** donde importa know-how propietario y rendimiento,
  Kratos/`C++` protege y escala.

**Conclusión (decisión tomada):** se mantienen **los dos motores** con el **local como default**,
que es la configuración correcta para el pipeline actual (análisis FEM lineal + SIMP sobre pieza
importada). **No** se adoptará Kratos como motor exclusivo/principal *ahora* porque:
1. Para el caso de uso actual, migrar no mejora el resultado (misma física lineal), solo el
   rendimiento en mallas grandes.
2. Se perdería la verificación cruzada y la red de seguridad del motor propio.
La migración a Kratos principal queda **condicionada a** (a) exigencia de rendimiento en mallas
grandes atribuible a *guias/pesos*, (b) necesidades de física avanzada, o (c) decisión de
estrategia comercial/IP.

**Aportaciones de una revisión externa (a incorporar):** el razonamiento dual-motor es sólido,
pero refuerza y matiza cuatro puntos:

- **El oráculo mutuo HOY es real (cerrado en este ciclo).** Con la carga materializada como
  `PointLoadCondition3D1N`, Kratos ya no da `u=0` para la carga por fuerza que usa el desktop;
  el cross-engine es una **suite de regresión automatizada** (`test_cae_cross_engine.py`) que
  corre ambos motores y compara compliance/desplazamientos con tolerancia explícita en cada
  cambio de malla/BC/ensamblado, detectando roturas silenciosas del bridge en CI.
- **Costo de portabilidad/distribución (no estaba documentado).** Para una app de escritorio, el
  motor NumPy/SciPy es trivialmente empaquetable (pip, sin binarios nativos pesados,
  multiplataforma sin compilar). Kratos como dependencia dura complica instaladores (tamaño,
  compatibilidad de wheels por plataforma, tiempos de arranque ya mencionados). Refuerza mantener
  **local como default**, no solo por iteración sino por fricción de distribución al usuario final.
- **Escalón intermedio antes de saltar a Kratos.** Antes de "migrar por rendimiento en mallas
  grandes", hay un paso más barato dentro del stack local: reemplazar `spsolve` (LU directo, con
  fill-in que escala mal en 3D) por **solvers iterativos de SciPy** (`cg`/`minres` +
  precondicionador) o **AMG** (pyamg). Esto retrasa el punto en que Kratos se vuelve necesario.
- **Umbral de decisión concreto (falta definir).** En lugar de "mallas grandes/rendimiento
  exigente" (subjetivo), definir explícitamente un umbral numérico — p. ej. *"por encima de N
  elementos o M segundos de `spsolve`, evaluar Kratos (y antes, PML/pyamg)"* — para que la
  migración no sea una decisión subjetiva más adelante.

### Siguiente paso técnico más lógico (post-fix)
1. ~~Exponer `imposed_disp`~~ → ya resuelto con `PointLoadCondition3D1N` real (carga por fuerza
   ensambla el RHS).
2. Evaluar el **escalón iterativo/AMG** local antes de comprometer a Kratos por rendimiento.
3. ~~Extender el cross-engine a cargas superficiales (`SurfaceLoadCondition3D3N` / pressure)~~ →
   **RESUELTO** (this cycle): la carga superficial/distribuida (`LoadType.DISTRIBUTED`) queda
   cubierta por el cross-engine con semántica `mag / len(nodos)` idéntica al motor local, y
   `LoadType.PRESSURE` (que requiere área de superficie) falla con `ValueError` claro en vez de
   producir una fuerza incorrecta (el sistema no modela área; documentado como limitación honesta).

#### RHS-force en Kratos: CORREGIDO (this cycle)
La causa raíz (ensamblado del RHS antes del solve) se confirmó y **fue corregida**.

**Causa raíz:** los loads se aplicaban ALMACENANDO variables solution-step `FORCE_*` en el nodo
(`apply_point_load` → `external_loads`, aplicadas por `apply_external_loads_to_model_part`). Pero
`ResidualBasedLinearStrategy` + `ResidualBasedBlockBuilderAndSolver` ensamblan el RHS **únicamente
desde los contenedores `Elements` y `Conditions`**. Como no se creaba ningún `Condition` para la
carga, el RHS quedaba vacío → warning `RHS to zero` → `u=0` con `success=True` (trivial).

**Corrección:** `KratosAdapter.apply_loads_to_model_part()` crea **condiciones Kratos reales**
(`PointLoadCondition3D1N`, disponible y verificado en Kratos 10.4.3) sobre cada nodo de carga,
con `POINT_LOAD` por nodo (magnitud ya distribuida por `apply_point_load`/`apply_distributed_load`).
El `ResidualBasedBlockBuilderAndSolver` ahora ensambla la carga como parte del sistema físico
(`K·u = f`) y el RHS deja de ser cero.

**Verificación del fix:**
- Cross-engine (`test_cae_cross_engine.py`): mismo caso físico resuelto en local y Kratos con
  `‖u_l − u_k‖/‖u_l‖ ≤ 1e-8` y compliance relativo ≤ 1e-6.
- `PointLoadCondition3D1N` con `POINT_LOAD` (VectorVariable) → contribute al RHS via el builder.
- El fix es mínimo: se conservan `apply_external_loads_to_model_part` (compatibilidad legacy) y
  `self.external_loads` para compliance; la carga real pasa por `apply_loads_to_model_part`.
- **Suite completa: 320 passed, 6 deselected, 1 warning** (sin regresiones). Tras la
  reorganización de tests en `tests/` (y retiro a `tests_obsoletos/` de 2 tests de diagnóstico):
  **321 passed, 6 deselected**.

**Estado del motor dual (this cycle): sin pendientes funcionales.** Fix del RHS, cargas
superficiales/distribuidas (`DISTRIBUTED`) y error explícito para `PRESSURE` quedan resueltos y
cubiertos por cross-engine. Los tres items de la sección "Siguiente paso" (escalón AMG local,
umbral de migración, peso de profundidad) son **mejoras/decisiones futuras de rendimiento**, no
pendientes funcionales del motor dual.

---

## Auditoría y trazabilidad de la interfaz CAD/CAE (this cycle)

Auditoría de trazabilidad **UI → Controller → Core** según `prompts.md`. Regla aplicada: *no se
declara una funcionalidad como implementada solo porque exista una clase, botón o método*; se
verificó la conexión real Botón → Señal → Método → Backend. Resultado consolidado en
**`docs/UI_IMPLEMENTATION_MAP.md`** (documento nuevo con el mapa por acción).

### Clasificación resultante

- **✅ Funcional (end-to-end real)**: Importar STEP, Malla, Malla Adaptativa, FEA, Optimizar SIMP,
  Boolean (Unión/Corte/Intersección), Transformar, Simetría, Patrón, Condiciones
  (Carga/Elasticidad/Obstrucción/Región protegida), Estudios (Nuevo/Ejecutar), Visualizar,
  Exportar resultado, Exportar STEP, Vistas/Fit/Centrar/Wireframe/Ejes, Limpiar selección,
  Reiniciar flujo, guía play/next, y **Validar (ver corrección abajo)**.
- **🔀 Redirige / hint (intencional)**: `rb_filtros` (⚙ Filtros) redirige al panel de propiedades.
- **🚫 Solo visual / NO CONECTADO (documentado, no implementado)**: `rb_sens` (Sensibilidad),
  `rb_design_space` (Espacio de Diseño), `rb_generative` (Generativo) — muestran mensaje fijo.
  No se construyó UI nueva (regla de no inventar funcionalidad futura). El motor generativo de
  `core/generative.py` existe pero no tiene flujo de escenarios conectado en la UI.
- **Código muerto detectado**: `DesignTreePanel.entitiesChanged` está declarada pero **nunca se
  emite** (ningún slot la usa). No afecta funcionalidad.

### Corrección aplicada

- **`rb_validate` (✓ Validar)**: conectado a un handler real `_on_validate` en vez de un lambda
  `showMessage` estático. Ahora refleja el estado real del `controller` (modelo, sólidos vía
  `cad.list_solids`, malla, fuerzas/restricciones, condiciones, estudios, resultado) y abre un
  diálogo de validación. Cobertura nueva: `tests/test_ui_validate_connection.py` (3 tests).

### Archivos tocados
- `desktop/ui/main_window.py` (nuevo `_on_validate` + conexión del ribbon).
- `docs/UI_IMPLEMENTATION_MAP.md` (nuevo, mapa de trazabilidad).
- `tests/test_ui_validate_connection.py` (nuevo).

### Verificación
- Arranque de `MainWindow` confirmado en entorno headless (`QT_QPA_PLATFORM=offscreen` con
  `SoftwareViewport`; el viewport VTK real requiere GPU y degrada automáticamente vía
  `is_gl_available()`).
- Suite completa: **324 passed, 6 deselected** (243+ tests previos + nuevos de validación y de
  ciclos intermedios; sin fallos ni regresiones).
