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
| `rb_import` / Menú Archivo → Importar STEP / `_on_play_next` (paso 1) | main_window:409 / 196 | `clicked` / `triggered` | `_on_import` (721) | `controller.import_model(...)` → `core` (viñeta STEP) | ✅ Funcional |
| `rb_mesh` / PropertiesPanel | main_window:411 / QSpin `element_size` | `clicked` | `_on_generate_mesh` (819) → `controller.generate_mesh` | `core.meshing` (Gmsh Tet4) | ✅ Funcional |
| `rb_mesh_adaptive` | main_window:413 | `clicked` | `_on_generate_adaptive_mesh` (868) | `controller.generate_adaptive_mesh` | ✅ Funcional |
| `_on_play_next` (guía) | TimelinePanel `playRequested` | `playRequested` | `_on_play_next` (1382) | orquesta import→mesh→opt | ✅ Funcional |

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
| Menú Condiciones → Carga / Elasticidad / Obstrucción / Región protegida | main_window:239-251 | `triggered` | `_on_condition_op(kind)` (1206) → `ConditionPanel` | `controller.execute_command` → `core.conditions.ConditionManager` | ✅ Funcional |
| PropertiesPanel `forceAdded` | properties:597 | `forceAdded(mag,dx,dy,dz)` | `_on_add_force` (1433) | persiste `controller.forces` (consumido por FEA/SIMP) | ✅ Funcional |
| PropertiesPanel `constraintAdded` | properties:598 | `constraintAdded(type)` | `_on_add_constraint` (1444) | persiste `controller.constraints` | ✅ Funcional |
| Overlay `⚡ Fuerzas` / `🔒 Fijaciones` | main_window:627-630 | `toggled` | `_sync_sidebar_vis` | visibilidad (solo presentación) | ✅ Funcional (display) |

## 5. Estudios (arquitectura)

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| Menú Estudio → Nuevo estudio | main_window:255, StudyPanel | `triggered` | `_on_create_study` (976) → `controller.register_study` | `core.cae_studies` / `optimization_studies` | ✅ Funcional |
| Menú Estudio → Ejecutar estudio | main_window:258 | `triggered` | `_on_run_study` (1003) → `controller.execute_study` | estudio determinista por pieza (prior cycle) | ✅ Funcional |

## 6. Postproceso y exportación

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| `rb_viz` | main_window:459 | `clicked` | `_on_visualize_result` (1119) | `viewport.show_density` (campo real) | ✅ Funcional |
| `rb_export` / Menú → Exportar resultado | main_window:461, 197 | `clicked`/`triggered` | `_on_export` (1067) | escribe JSON con `controller.result` real | ✅ Funcional |
| `rb_export_step` / Herramientas | main_window:471 | `clicked` | `_on_export_step` (1095) | `controller.cad.export_step` | ✅ Funcional |

## 7. Vista, navegación y guía

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Nivel |
|----------------|----|----------------|------------------|-------|
| Vistas (ISO/FRONT/TOP/RIGHT) | menú Diseño:264, combo:490 | `triggered`/`currentIndexChanged` | `_on_view` (1530) → `viewport.set_view` | ✅ Funcional |
| Ajustar a pantalla / Centrar | menú:277, overlay:621 | `clicked` | `viewport.fit_to_view` / `center_model` | ✅ Funcional |
| Wireframe / Ejes / Rejilla | overlay:622-626, ribbon:497 | `toggled` | `viewport.set_display_mode` / `toggle_axes` / `toggle_grid` | ✅ Funcional |
| Limpiar selección | menú Editar:209, DesignTree | `triggered`/`clicked` | `_on_clear_selection` (1506) | ✅ Funcional |
| Reiniciar flujo | menú Editar:212, Timeline `resetRequested` | `triggered`/`resetRequested` | `_on_reset_flow` (1394) | ✅ Funcional |
| `_on_play_next` / Siguiente | TimelinePanel `playRequested`, `_btn_play`,`_btn_next` | `playRequested` | `_on_play_next` (1382) | ✅ Funcional |
| Prev | TimelinePanel `_btn_prev` → `resetRequested` | `resetRequested` | `_on_reset_flow` | ✅ Funcional |

## 8. Herramientas

| Botón / Acción | UI | Señal / Acción | Método ejecutado | Backend real | Nivel |
|----------------|----|----------------|------------------|--------------|-------|
| **`rb_validate` (✓ Validar)** | main_window:468 | `clicked` | **`_on_validate` (1456)** | reporta estado real del `controller` (modelo, sólidos vía `cad.list_solids`, malla, fuerzas/restricciones, condiciones, estudios, resultado) | ✅ Funcional *(corregido en este ciclo)* |
| `rb_filtros` (⚙ Filtros) | main_window:443 | `clicked` | `_on_focus_filter` (1135) | redirige al panel de propiedades | 🔀 Redirige |

---

## 9. Solo visuales / NO CONECTADOS (con motivo)

| Botón | UI | Comportamiento actual | Motivo / decisión |
|-------|----|----------------------|-------------------|
| `rb_sens` (📈 Sensibilidad) | main_window:440 | `statusBar().showMessage(...)` estático | La sensibilidad adjunta ya se computa internamente por el motor SIMP en `controller.run_optimization`; no hay backend separado reutilizable que conectar. |
| `rb_design_space` (◆ Espacio de Diseño) | main_window:447 | `showMessage(...)` estático | Definir espacio de diseño requiere captura de dominio nueva; el dominio se determina por pieza dentro de `execute_study` (ciclo previo) y no hay panel de dominio conectado. No se construye UI nueva (prompt: no inventar funcionalidad). |
| `rb_generative` (✧ Generativo) | main_window:450 | `showMessage(...)` estático | Existe `core/generative.py` (motor + validación) pero no hay flujo de escenarios configurado en la UI. Conectarlo exigiría un panel de escenarios nuevo. Documentado como **NO CONECTADO**, no implementado. |

Nota: `rb_mesh_adaptive`, `rb_fea`, `rb_opt`, `rb_viz`, `rb_export`,
`rb_export_step` y todos los de Edición/Condiciones se habilitan/deshabilitan
según el estado real del pipeline (`_set_enabled`), de modo que los botones
solo-visuales anteriores son los únicos que muestran mensaje fijo.

---

## 10. Señales muertas / código detectado

| Ubicación | Señal | Estado |
|-----------|-------|--------|
| `desktop/ui/panels/design_tree.py` | `entitiesChanged` | **Declarada pero NUNCA emitida** (código muerto). Ningún slot conectado en `main_window`. No afecta funcionalidad; preservada por si el árbol notifica cambios. |

Las señales de `PropertiesPanel` (`runOptimization`, `runFEA`, `generateMesh`,
`forceAdded`, `constraintAdded`) están **todas conectadas** y verificadas por
`tests/test_ui_integration_connections.py`.

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

## 13. Verificación

- Arranque de `MainWindow` confirmado en entorno headless (`QT_QPA_PLATFORM=offscreen`
  con `SoftwareViewport`; el viewport VTK real requiere GPU y degrada
  automáticamente a `SoftwareViewport` vía `is_gl_available()`).
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
