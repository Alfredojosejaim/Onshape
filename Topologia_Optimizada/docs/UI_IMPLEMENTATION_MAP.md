# Mapa de Implementación de la Interfaz (UI → Controller → Core)

> Auditoría de trazabilidad CAD/CAE de la aplicación desktop.
> Regla aplicada: *no se declara una funcionalidad como implementada únicamente
> porque exista una clase, botón o método*; se verifica la conexión real
> Botón → Señal → Método → Controller → Core.

## Convención de niveles

| Nivel | Significado |
|-------|-------------|
| ✅ **Funcional** | Conexión end-to-end real: ejecuta pipeline/controller/core y afecta el estado del modelo o produce un resultado. |
| 🔀 **Redirige / hint** | No ejecuta backend; navega/muestra ayuda apuntando a un panel real (intencional, no es código muerto). |
| 🚫 **Solo visual / NO CONECTADO** | Muestra un mensaje decorativo; no existe implementación reutilizable conectable sin construir UI nueva. |

La UI desktop es `desktop/ui/main_window.py` (coordinador: `__init__` +
`_build_central` + paneles + handlers `_on_*`). La **composición visual** se
delega en `desktop/ui/components/`:
  - widgets: primitivas (`repolish`, `glyph_label`, `mini_label`, `RibbonTool`)
  - menus:    barra de menú (MenuBuilder)
  - workspace: topbar + pestañas + ribbon (WorkspaceBuilder)
  - overlays:  overlays del viewport (OverlayBuilder)
  - main_workspace: composición física del workspace (sidebar + viewport +
    timeline + results) y `ViewportHost` (host del viewport con auto-selección
    de backend VTK/software + posicionado de overlays)

Los builders reciben `owner` (MainWindow) para conectar las mismas señales de
siempre; la ventana conserva las referencias (`rb_*`, `chip_status`, `ctrl_*`,
`_view_combo`, ...) y las rutas de trazabilidad botón→handler→controller→core
se mantienen intactas (verificado por `tests/test_ui_integration_connections.py`).

La composición del workspace principal (sidebar con `DesignTreePanel` +
`PropertiesPanel`, centro con viewport+`TimelinePanel`, derecha con
`ResultsPanel`, márgenes/anchuras/proporciones) la monta
`desktop/ui/components/main_workspace.py` (`MainWorkspaceBuilder`). Antes de esa
extracción vivía en `MainWindow._build_central()`; `ViewportHost` (antes
`_ViewportHost`) es el frame del viewport que auto-selecciona VTK frente al
`SoftwareViewport` según `is_gl_available()` y posiciona los overlays.

ANTES → DESPUÉS → CONEXIÓN PRESERVADA
  MainWindow._build_central (sidebar+centro+derecha)
      → MainWorkspaceBuilder(owner).build()  (solo composición + instancia de paneles)
      → MainWindow conserva la coordinación: set_solid_resolver, signals de
        properties/timeline/design_tree, `_build_viewport_overlays()`.

Los paneles de presentación viven en `desktop/ui/panels/` y el viewport en
`desktop/viewport/` (VTK con fallback `SoftwareViewport` QPainter).
El flujo controlado es `desktop/pipeline/controller.py`, que delega en
`core/` (`document.py`, `features.py`, `commands.py`, `cae_studies.py`,
`optimization_studies.py`, `generative.py`, `conditions.py`).

---

## 1. Carga de modelo

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| Topbar `📁 Importar STEP` / Menú Archivo → Importar STEP / `_on_play_next` (paso 1) | workspace (topbar) / menú Archivo | `clicked` / `triggered` | `_on_import` | `controller.import_model(...)` → `core` (viñeta STEP) | ✅ Funcional |
| `rb_mesh` / PropertiesPanel | workspace ribbon (grupo Modelo) / QSpin `element_size` | `clicked` | `_on_generate_mesh` → `controller.generate_mesh` | `core.meshing` (Gmsh Tet4) | ✅ Funcional |
| `rb_mesh_adaptive` | workspace ribbon (grupo Modelo) | `clicked` | `_on_generate_adaptive_mesh` | `controller.generate_adaptive_mesh` (con fallback explícito a malla uniforme + flag `adaptive_fallback`) | ✅ Funcional |
| `_on_play_next` (guía) | TimelinePanel `playRequested` | `playRequested` | `_on_play_next` | orquesta import→mesh→opt | ✅ Funcional |

> Nota (limpieza del ribbon): el import vive SOLO en el topbar + menú
> Archivo; no existe `rb_import` en el ribbon (duplicado eliminado).

## 2. FEA y optimización

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| `rb_fea` / PropertiesPanel `runFEA` / menú | main_window:415, properties:594 | `clicked` / `runFEA` | `_on_run_fea` (884) | `controller.run_fea` → `core.fea` / solver | ✅ Funcional |
| `rb_opt` / menú | main_window:445 | `clicked` | `_on_run_optimization_default` (906) → `_on_run_optimization` (916) | `controller.run_optimization` (SIMP) | ✅ Funcional |
| PropertiesPanel `runOptimization` | properties:596 | `runOptimization(dict)` | `_on_run_optimization` (916) | `controller.run_optimization` | ✅ Funcional |

## 3. Operaciones CAD (Boolean / Transform / Mirror / Pattern)

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| `rb_union` / Menú Boolean → Unión | main_window:422, 218 | `clicked` | `_on_boolean_op("union")` (1138) → `BooleanPanel` → `controller.execute_command(cmd)` | `core.commands.BooleanCommand` | ✅ Funcional |
| `rb_difference` / Corte | main_window:424, 221 | `clicked` | `_on_boolean_op("difference")` | idem | ✅ Funcional |
| `rb_intersect` / Intersección | main_window:426, 224 | `clicked` | `_on_boolean_op("intersection")` | idem | ✅ Funcional |
| `rb_transform` / Menú → Transformar | main_window:428, 228 | `clicked` | `_on_transform_op` (1292) → `TransformPanel` → `execute_command` | `core.commands.TransformCommand` | ✅ Funcional |
| `rb_mirror` / Simetría | main_window:430, 231 | `clicked` | `_on_mirror_op` (1319) → `MirrorPanel` | `core.commands.MirrorCommand` | ✅ Funcional |
| `rb_pattern` / Patrón | main_window:432, 234 | `clicked` | `_on_pattern_op` (1339) → `PatternPanel` | `core.commands.PatternCommand` | ✅ Funcional |

Los seis paneles reutilizan el `SelectionManager` del viewport para capturar
sólidos/faces reales; solo sobre **Aceptar** se construye el `Command` y se
ejecuta vía pipeline (`_on_cad_edit_done` re-renderiza y sincroniza el árbol).

## 4. Condiciones

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| Menú Condiciones → Carga / Elasticidad / Obstrucción / Región protegida | menú &Condiciones | `triggered` | `_on_condition_op(kind)` → `ConditionPanel` | `controller.execute_command` → `core.conditions.ConditionManager` (append, nunca overwrite) | ✅ Funcional |
| `rb_conditions` (dropdown: Carga/Elasticidad/Obstrucción/Región protegida) | workspace ribbon (grupo Condiciones) | `triggered` (cada acción) + `clicked`→`showMenu` | `_on_condition_op(kind)` (mismo handler que el menú) | idem | ✅ Funcional |
| PropertiesPanel `forceAdded` | properties:597 | `forceAdded(mag,dx,dy,dz)` | `_on_add_force` (1433) | persiste `controller.forces` (consumido por FEA/SIMP) | ✅ Funcional |
| PropertiesPanel `constraintAdded` | properties:598 | `constraintAdded(type)` | `_on_add_constraint` (1444) | persiste `controller.constraints` | ✅ Funcional |
| Overlay `⚡ Fuerzas` / `🔒 Fijaciones` | main_window:627-630 | `toggled` | `_sync_sidebar_vis` | visibilidad (solo presentación) | ✅ Funcional (display) |

## 5. Estudios (arquitectura)

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| Menú Estudio → Nuevo estudio | main_window:255, StudyPanel | `triggered` | `_on_create_study` (976) → `controller.register_study` | `core.cae_studies` / `optimization_studies` | ✅ Funcional |
| Menú Estudio → Ejecutar estudio | main_window:258 | `triggered` | `_on_run_study` (1003) → `controller.execute_study` | estudio determinista por pieza (prior cycle) | ✅ Funcional |
| Menú Estudio → Nuevo diseño generativo... | menú Estudio, GenerativeStudyPanel | `triggered` | `_on_create_generative_study` → `controller.register_study` | `core.generative.GenerativeDesignStudy` (escenario A/B, condiciones por id) | ✅ Funcional |
| Menú Estudio → Ejecutar diseño generativo | menú Estudio | `triggered` | `_on_run_generative_study` → `controller.execute_study` | `core.generative_engine.run_generative_design` + reconstrucción B-Rep | ✅ Funcional |

## 6. Postproceso y exportación

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| `rb_viz` | workspace ribbon (grupo Postproceso) | `clicked` | `_on_visualize_result` | `viewport.show_density` (campo real, colormap elegible) | ✅ Funcional |
| `rb_export` (dropdown: Resultado JSON / Modelo STEP) | workspace ribbon (grupo Postproceso) | `triggered` + `clicked`→`showMenu` | `_on_export` / `_on_export_step` | escribe JSON con `controller.result` real / `controller.cad.export_step` | ✅ Funcional |

> Nota: `rb_export_step` como botón separado fue eliminado; vive como
> acción dentro del dropdown `rb_export`.

## 7. Vista, navegación y guía

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Nivel |
|----------------|----|----------------|------------------|-------|
| Vistas (ISO/FRONT/TOP/RIGHT) | menú Diseño, combo vista (workspace, `owner._view_combo`) | `triggered`/`currentIndexChanged` | `_on_view` → `viewport.set_view` | ✅ Funcional |
| Ajustar a pantalla / Centrar | menú:277, overlay:621 | `clicked` | `viewport.fit_to_view` / `center_model` | ✅ Funcional |
| Wireframe / Ejes / Rejilla | overlay:622-626, ribbon:497 | `toggled` | `viewport.set_display_mode` / `toggle_axes` / `toggle_grid` | ✅ Funcional |
| Limpiar selección | menú Editar:209, DesignTree | `triggered`/`clicked` | `_on_clear_selection` (1506) | ✅ Funcional |
| Reiniciar flujo | menú Editar:212, Timeline `resetRequested` | `triggered`/`resetRequested` | `_on_reset_flow` (1394) | ✅ Funcional |
| `_on_play_next` / Siguiente | TimelinePanel `playRequested`, `_btn_play`,`_btn_next` | `playRequested` | `_on_play_next` (1382) | ✅ Funcional |
| Prev | TimelinePanel `_btn_prev` → `resetRequested` | `resetRequested` | `_on_reset_flow` | ✅ Funcional |

## 8. Herramientas

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| **`rb_validate` (✓ Validar)** | workspace ribbon (grupo Herramientas) | `clicked` | **`_on_validate`** | reporta estado real del `controller` (modelo, sólidos vía `cad.list_solids`, malla, fuerzas/restricciones, condiciones, estudios, resultado) | ✅ Funcional *(corregido en auditoría previa)* |

---

## 9. Botones eliminados en la limpieza del ribbon (histórico)

| Botón | Comportamiento anterior | Decisión |
|-------|------------------------|----------|
| `rb_sens` (Sensibilidad) | `statusBar().showMessage(...)` estático | **Eliminado**: la sensibilidad ya se computa dentro del SIMP; no había backend separado que conectar. |
| `rb_filtros` (⚙ Filtros) | redirigía al panel de propiedades (`_on_focus_filter`) | **Eliminado** junto con su handler. |
| `rb_design_space` (Espacio de Diseño) | `showMessage(...)` estático | **Eliminado**: el dominio se determina por pieza en `execute_study`; no hay panel de dominio. |
| `rb_generative` (Generativo) | `showMessage(...)` estático | **Eliminado de la UI**: el motor `core/generative.py` existe pero no hay flujo de escenarios conectado; conectarlo exige panel nuevo (fuera de alcance). |
| `rb_export_step` (botón suelto) | duplicaba la exportación STEP | **Eliminado como botón**; vive como acción del dropdown `rb_export`. |
| `rb_import` (ribbon) | duplicaba el import del topbar | **Eliminado del ribbon**; import único en topbar + menú Archivo. |

Nota: `rb_mesh_adaptive`, `rb_fea`, `rb_opt`, `rb_viz`, `rb_export`,
`rb_validate` y todos los de Edición/Condiciones se habilitan/deshabilitan
según el estado real del pipeline (`_set_enabled`).

---

## 10. Señales muertas / código detectado

Las señales de `PropertiesPanel` (`runOptimization`, `runFEA`, `generateMesh`,
`forceAdded`, `constraintAdded`) están **todas conectadas** y verificadas por
`tests/test_ui_integration_connections.py`.

`DesignTreePanel.entitiesChanged` (señal muerta histórica) fue **eliminada**
del código — grep confirma 0 referencias. Sin señales muertas conocidas.

---

## 11. Trazabilidad panel → controller → core (resumen verificado)

- `properties.generateMesh/runFEA/runOptimization` → `_on_generate_mesh` /
  `_on_run_fea` / `_on_run_optimization` → `controller` → `core.meshing`/`fea`.
- `properties.forceAdded/constraintAdded` → `_on_add_force/_on_add_constraint`
  → persisten `controller.forces`/`controller.constraints` (consumidos por FEA/SIMP).
- `study_panel` → `controller.register_study` → `controller.studies`/`document`.
- `_on_run_study` → `controller.execute_study` → resultado store (`results`).
- Paneles Boolean/Transform/Mirror/Pattern/Condition → `controller.execute_command`
  → `core.commands.*` → `document.add_feature` + `conditions`.

Fuentes de verdad auditadas (verificación visual de conexión real en el código):
`desktop/ui/main_window.py` (handlers `_on_*` + `_build_central`),
`desktop/ui/components/` (menus, workspace, overlays, main_workspace), paneles en
`desktop/ui/panels/*.py`, `desktop/pipeline/controller.py`,
`core/document.py`, `core/cae_studies.py`, `core/optimization_studies.py`,
`core/generative.py`, `core/conditions.py`, `core/commands.py`.

---

## 12. Correcciones aplicadas en esta auditoría

1. **`rb_validate` (Validar)**: conectado a `_on_validate` (real). Antes era un
   lambda `showMessage` estático. Ahora refleja el estado real del `controller`
   (modelo, sólidos, malla, fuerzas/restricciones, condiciones, estudios,
   resultado). Cobertura: `tests/test_ui_validate_connection.py` (3 tests).
2. **Documento de trazabilidad** creado (este archivo).

**No** se construyeron UIs nuevas (sensibilidad/espacio/generativo se documentan
como NO CONECTADO, conforme a la regla de no inventar funcionalidad futura).

## 12b. Sincronización post-limpieza del ribbon + endurecimiento (este ciclo)

1. **Mapa actualizado tras la limpieza**: §§1, 4, 6–9 reescritos (import solo
   topbar, dropdown `rb_conditions`, dropdown `rb_export`, combo de vista en
   workspace, §9 convertido en histórico de eliminados).
2. **P1 (fallbacks por orden)**: `_emit_physical_groups` advierte explícito sin
   correspondencia; `_extract_all_surface_elements` en modo determinista ya no
   etiqueta por posición — superficies sin match → `face_unmapped_<tag>` +
   warning (nunca confundible con `face_<fi>`).
3. **Ruta legacy explícita** (`controller.py`): `set_material` rechaza nombre
   inválido; `generate_adaptive_mesh` marca `adaptive_fallback`; `_apply_*`,
   `build_problem`/`run_optimization` y `run_in_background` con warnings
   explícitos; `_apply_*` documentados LEGACY (preferir `ConditionManager`).
4. **`_study_solid_index`/`_active_study_id`** inicializados en `__init__`;
   timeline rama: nodo converge emite `playRequested` + tooltip de vista,
   umbral unificado a ≥1 grupo (igual que el árbol); `design_tree` con helper
   `_labeled_item` e imports top-level; dropdowns ribbon con `showMenu`.

## 12c. Plan aprobado D1–D6 + Fases 0/1/3 (este ciclo)

Decisiones del usuario: UI generativa primero (D1), PRESSURE con área real
(D2), Thermal/Modal quedan scaffold (D3), solver iterativo sí (D4), orden
1→3→2 (D6). Fase 2 (IDs persistentes P1/P2) diferida.

1. **Fase 0**: baseline `439 passed, 6 deselected` (sin benchmarks).
2. **Fase 1**: `entitiesChanged` ya eliminada (confirmado 0 refs); Validar
   muestra `face_unmapped_<tag>`; CI sigue en `runtime/python` (§13b).
3. **Fase 3a (UI generativa)**: `GenerativeStudyPanel` (escenarios A/B,
   `study_panel.py`), menú Estudio → Nuevo/Ejecutar diseño generativo
   (`_on_create_generative_study` / `_on_run_generative_study`,
   post-proceso compartido `_finish_study_execution`).
4. **Fase 3b (PRESSURE)**: `core/boundary.py` (`is_pressure_unit`,
   `surface_area_mm2`, `pressure_to_total_force_N`: F[N]=p[Pa]×A[m²], malla
   en mm); motor local y Kratos integran área; sin área → error explícito;
   `kratos_bridge` propaga `LoadType.PRESSURE`; panel de carga con selector
   N/Pa/kPa/MPa.
5. **Fase 3c (iterativo)**: `FEASolver(linear_solver="cg")` (default
   `direct` intacto, fallback explícito); `solve_fea` reporta
   `linear_solver/cg_iterations/solver_fallback/solve_seconds/kratos_suggestion`;
   umbral numérico 50k elementos / 30s; aviso en log + status bar de FEA.

## 12d. Riesgos E1–E4 resueltos (este ciclo, sin cambios de UI)

Sin botones nuevos; impacto observable en Validar/FEA:

1. **E2**: `generate_mesh_for_shape` rechaza `physical_groups` fuera de rango
   (`INVALID_FACE_INDEX`); índices locales al dominio (ver error en status bar
   / log si se dispara desde la UI).
2. **E3**: `_run_fea_kratos` fabrica grupos por condición
   (`condition_face_groups` + `submodelpart_name`) y re-malla si la malla no
   trae ninguno — la FEA Kratos ahora usa la vía exacta (Strategy 1) en el
   flujo por defecto en vez de aproximación geométrica.
3. **E4**: condiciones sin cara aplican defaults con paridad local↔Kratos
   (cargas a extremo según dirección, soportes a base min-eje); el e2e
   verifica acuerdo en vez de `compliance == 0`.
4. **E1**: `build_face_correspondence` con invariante de área total + techo
   absoluto (errores explícitos ante split/merge o contraparte implausible).

## 13. Verificación

- Arranque de `MainWindow` confirmado en entorno headless (`QT_QPA_PLATFORM=offscreen`
  con `SoftwareViewport`; el viewport VTK real requiere GPU y degrada
  automáticamente a `SoftwareViewport` vía `is_gl_available()`).
  **Nota headless/CI**: en `offscreen` la sonda `is_gl_available()` (subprocess) puede
  devolver True sin GPU real, y la construcción de `Viewport3D` (VTK) entonces
  aborta por pixel format inválido. Por eso tests y smoke headless fuerzan
  `SoftwareViewport` parcheando el símbolo `Viewport3D` (patrón de
  `test_ui_validate_connection.py`), no la detección automática.
- Modularización de la composición visual: `menu`/`topbar`/`tabs`/`ribbon`/
  `overlays` extraídos a `desktop/ui/components/`; `MainWindow` conserva handlers
  y coordinación. Conexiones verificadas por
  `tests/test_ui_integration_connections.py` (6) + `test_ui_validate_connection.py` (3).
- El workspace principal (sidebar + centro + results) se extrajo a
  `desktop/ui/components/main_workspace.py` (`MainWorkspaceBuilder`), incluyendo
  `ViewportHost`. Nota: el test `test_ui_validate_connection.py` parchea el
  símbolo `Viewport3D` en `desktop.ui.components.main_workspace` (nueva ruta de
  construcción), no ya en `main_window`.
- Suite: `python -m pytest -q -p no:cacheprovider` → **246 passed** al finalizar
  (243 previos + 3 nuevos de `test_ui_validate_connection.py`).

## 13b. Pendiente resuelto: crash de proceso al salir (CI `.venv`)

Durante esta auditoría se detectó y **descifró** un crash de proceso al salir
(`EXIT=-1073741819` access violation / `-1073740940` heap corruption) cuando la
suite se ejecuta con el intérprete de `.venv`. Causa raíz:

- Es un **bug de cierre del propio intérprete** (CPython **3.12.14** de `.venv`,
  MSC v.1944) en Windows al finalizar (`Current thread <no Python frame>`),
  disparado por la teardown GC de los módulos del paquete `core/` (los que tiran
  de extensiones nativas como Gmsh/Kratos). No es un defecto de la aplicación.
- Se descartó la interferencia de la UI (no precisa Qt), del módulo aislado
  (`core/models.py` copiado en standalone sale **limpio**), y de `gc.collect()`.
- El intérprete **self-contained `runtime/python` (CPython 3.12.10, MSC v.1943)**,
  el que realmente se distribuye, **no lo reproduce**: suite UI + CAD/CAE completa
  → **176 passed con EXIT=0**.

Resolución recomendada para CI/tests: usar el intérprete de `runtime/python`.
Confirmado que el crash **precede** a esta refactorización (reproducido el mismo
comportamiento en `master` anterior vía stash): no fue introducido por la
modularización del workspace.
