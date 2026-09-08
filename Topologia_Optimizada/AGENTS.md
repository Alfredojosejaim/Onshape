# AGENTS.md — Índice de contexto del proyecto

> Este archivo es un ÍNDICE, no una explicación. Da la ubicación exacta de
> cada cosa para que no haga falta leer toda la documentación del repo antes
> de trabajar. Si necesitás detalle profundo de un tema, andá al doc/archivo
> referenciado — no dupliques su contenido acá.

## Qué es esto

**Topología Optimizada**: app de escritorio CAD/FEM inspirada en Onshape.
Pipeline completo: geometría B-Rep → malla FEM → optimización topológica
SIMP → reconstrucción de geometría. Standalone (sin servidor ni navegador).
Estado real (implementado/parcial/pendiente, por módulo): `PROJECT_STATUS.md`.

## Stack

| Capa | Biblioteca | Uso |
|---|---|---|
| Geometría B-Rep | CadQuery / OCP (OCCT) | STEP I/O, sólidos, caras |
| Mallado | Gmsh | Malla volumétrica Tet4 |
| FEM / Optimización | Kratos Multiphysics (`StructuralMechanicsApplication`, `OptimizationApplication`, MMA/GCMMA) | FEA + SIMP, backend dual con motor local NumPy/SciPy |
| Reconstrucción B-Rep | Marching Tetrahedra + `OCPBRepFitter` | Campo de densidad → STEP editable |
| Visualización | VTK (`vtkCellPicker`, `QVTKRenderWindowInteractor`, `vtkActor2D`) | Viewport 3D, picking, overlays |
| UI | PySide6 | Layout tipo Onshape (ribbon, feature tree, topbar) |

## Mapa de directorios

main.py → desktop/app.py → desktop/ui/main_window.py (arranque)
core/ Lógica de dominio, SIN dependencias de UI (test: test_core_independence.py)
conditions.py ConditionManager: Load/Elasticity/Obstruction/ProtectedRegion (fuente de verdad, YA implementado — no reinventar esquema)
cad_entity.py CadEntityRef (con solid_id) / SelectionSet
topo_problem.py, topopt.py Definición y motor del problema de optimización
kratos_adapter.py (72K) Puente a Kratos — el archivo más grande, ir con cuidado
meshing.py Gmsh
cad_reconstruction.py Marching Tetrahedra + fitting B-Rep
face_correspondence.py Matching geométrico OCCT↔Gmsh (relacionado a bug P1, ver abajo)
selection.py, navigation.py Picking / physical groups
fea.py, materials.py, boundary.py, generative.py, generative_engine.py

desktop/
ui/main_window.py Coordinador: handlers on* (import, mesh, fea, optimize, export, validate...)
ui/components/workspace.py WorkspaceBuilder: topbar + ribbon + pestañas (RECIÉN LIMPIADO, ver "Estado actual" abajo)
ui/components/menus.py MenuBuilder: barra de menú superior
ui/components/widgets.py Primitivas (RibbonTool, glyph_label, repolish)
ui/panels/design_tree.py Árbol de diseño (Onshape-style), agrupa condiciones por pieza (solid_id)
ui/panels/condition_panel.py Diálogo modal por condición (factory pattern: cada Aceptar = instancia nueva)
ui/panels/timeline.py Timeline tipo Fusion, con modo ramificado por pieza (columnas paralelas que convergen en nodo Optimizar compartido: `set_branch_view`)
ui/theme.json Paleta de colores (dark), fuente de verdad para cualquier mockup/UI nueva
viewport/ Viewport3D → Scene/Renderer/CameraController/SelectionManager
pipeline/controller.py PipelineController (orquesta core desde la UI)

services/ cad_service.py, study_service.py — capa de servicio
adapters/cad/ Adaptadores de import/export CAD
tests/ ~40 archivos, convención test_p0_/test_p1_/test_p3_* = ligados a bugs priorizados


## Qué doc leer para qué (no leer todos de entrada)

| Necesito... | Leer |
|---|---|
| Instalar/correr la app | `README.md` §0 |
| Especificación completa del producto | `README.md` (32K, completo) |
| Qué está implementado vs pendiente, por módulo | `PROJECT_STATUS.md` (fuente de verdad del estado REAL) |
| Auditoría botón→handler→controller→core de la UI (✅/🔀/🚫) | `docs/UI_IMPLEMENTATION_MAP.md` — **actualizado tras la limpieza del ribbon y el endurecimiento (ciclo actual, §12b)** |
| Convención de navegación/selección | `docs/NAVIGATION_CONVENTION.md` |
| Arquitectura del pipeline de selección de nodos | `ARQUITECTURA_SELECCION_NODOS.md` |
| Detalle profundo de implementación (histórico, largo) | `RESUMEN_IMPLEMENTACION.md` (96K — último recurso) |

## Principios de diseño no negociables

- **No fallback silencioso**: cualquier inconsistencia se reporta explícitamente, nunca se resuelve con un default oculto.
- **Physical groups → submodelparts** es el único mecanismo de propagación de identidad geometría→solver. No duplicar lógica de selección en otro lado (por eso `TopologyOptimizationProblem` referencia `selection_id`, no repite geometría).
- La reconstrucción B-Rep y la validación de BCs ya están a nivel comercial — **no regresar**, solo extender.
- Condiciones (`Load`/`Elasticity`/`Obstruction`/`ProtectedRegion`) son **instancias reutilizables**, nunca se sobrescriben: cada acción de la UI hace `append`, nunca overwrite.

## Bugs conocidos (prioridad y ubicación)

| ID | Bug | Ubicación | Bloquea |
|---|---|---|---|
| P1 | Correspondencia OCCT `shape.Faces()` ↔ Gmsh `getEntities(2)` por firma geométrica (sin IDs persistentes); fallbacks por orden eliminados del modo determinista (`face_unmapped_<tag>` + warning, `core/meshing.py`) | `core/face_correspondence.py` | P2 |
| P2 | Mesher provisorio clasifica frontera por cara CAD (`classify_triangles_to_faces`); resto no asignable → bucket `"boundary"` explícito (aprox. a ~h/2, solo Gmsh vale para cargas validadas) | `core/meshing.py` (`ProvisionalTet4Mesher`), `core/kratos_adapter.py` | Validación de cargas reales |
| P3 | Ambigüedad `volfrac` (dominio activo vs volumen total) — RESUELTO: `ACTIVE_DOMAIN` (decisión Option A, `core/topopt.py`); `VolfracMode` lo modela en `core/topo_problem.py` | `core/topo_problem.py` (`VolfracMode`) | — (cerrado) |
| P4 | Halo radius mal derivado de `filter_radius` — RESUELTO: deriva de tamaño de elemento de malla en `protect_elements_near_nodes()`; `halo_radius_source` lo modela | `protect_elements_near_nodes()` en meshing/topo | — (cerrado) |

Orden de resolución: P1 → P2 (P2 depende de P1). P3 y P4 ya cerrados (ver arriba).

## Estado actual de trabajo en curso (sesión activa)

Se auditó y limpió `desktop/ui/components/workspace.py` (ribbon):
- Dropdown "Condiciones" agregado (Carga/Elasticidad/Obstrucción/Región protegida) → llama `owner._on_condition_op(kind)` (ya existente, sin cambios).
- `design_tree.py`: `set_conditions()` reescrito para agrupar por pieza (`solid_id`) con badge de valor por instancia.
- Import consolidado a un solo botón (topbar `📁 Importar STEP`); se eliminó el duplicado del ribbon.
- Eliminados 4 botones sin función real (solo mostraban mensaje en status bar): `rb_sens`, `rb_filtros`, `rb_design_space`, `rb_generative`.
- Export consolidado en dropdown único (`rb_export`: Resultado JSON / Modelo STEP), eliminado `rb_export_step` duplicado.
- **Hecho**: `docs/UI_IMPLEMENTATION_MAP.md` sincronizado (§§1,4,6–9, §12b); ruta legacy del controller con fallbacks explícitos; timeline rama clicable con umbral ≥1.
- **Hecho**: timeline ramificada por pieza en `timeline.py` (columnas paralelas por pieza que convergen en `Optimizar()` vía `set_branch_view`; pipeline/feature salen del modo automáticamente).

## Convención de flujo de trabajo

- Claude diagnostica sobre el código real (no asunciones) y entrega diffs exactos o archivos completos.
- Muse Spark 1.3 aplica los cambios al repo real.
- Todo diff se valida con `python3 -m ast` antes de entregarse; correr la app y los tests queda del lado de Muse Spark/Alfredo, ya que el entorno de Claude no tiene PySide6/Qt/Kratos instalados.
- Prioridad explícita P0/P1/P2/P3/P4 en cualquier lista de bugs — no reordenar sin discutirlo.
