# Plan de Integración: `crea3d_mainwindow.ui` → Reemplazo de `main_window.py`

> **ARCHIVO ELIMINADO (2026-09-04):** `desktop/ui/crea3d_mainwindow.ui` fue eliminado
> del repositorio. La UI se implementó directamente en `main_window.py` + componentes
> modulares (`desktop/ui/components/`). Este plan está completamente obsoleto.

## 1. Archivo fuente

`desktop/ui/crea3d_mainwindow.ui` — ~~boceto Qt Designer (843 líneas XML)~~ **eliminado**.

**Nota:** El archivo es un boceto incompleto. Faltan menús con items, señales
no conectadas, y el viewport es un placeholder QLabel. Este plan documenta la
estrategia de integración **cuando el diseño .ui esté terminado**.

---

## 2. Widget tree del .ui (nombre Qt → tipo)

```
MainWindow (QMainWindow)
├── centralwidget (QWidget)
│   └── verticalLayoutCentral (QVBoxLayout, margins=0)
│       ├── horizontalLayoutTabs (QHBoxLayout)           ← workspace tabs
│       │   ├── tabModelo (QToolButton, checkable)
│       │   ├── tabOptimizacion (QToolButton, checkable, checked)
│       │   ├── tabSimulacion (QToolButton, checkable)
│       │   └── horizontalSpacerTabs
│       │
│       └── bodySplitter (QSplitter, horizontal)
│           ├── treePanel (QWidget, minW=200, maxW=320)   ← sidebar izquierdo
│           │   └── verticalLayoutTree
│           │       ├── labelTreeHeader (QLabel "ÁRBOL DEL MODELO")
│           │       ├── treeWidgetModel (QTreeWidget)      ← design tree
│           │       ├── labelPartsHeader (QLabel "PIEZAS")
│           │       └── listWidgetParts (QListWidget)      ← parts list
│           │
│           └── contentArea (QWidget)                      ← área central
│               └── verticalLayoutContent
│                   ├── toolBarHerramientas (QToolBar)     ← toolbar Kratos
│                   │   ├── actionMallaFEM
│                   │   ├── actionAnalisisFEM
│                   │   ├── [separator]
│                   │   ├── actionSensibilidad
│                   │   ├── actionFiltros
│                   │   ├── actionOptimizarMMA
│                   │   ├── [separator]
│                   │   ├── actionSuavizado
│                   │   └── actionExportar
│                   │
│                   └── viewportWidget (QFrame)            ← área 3D
│                       └── verticalLayoutViewport
│                           ├── horizontalLayoutViewportHeader
│                           │   ├── labelViewportTitle (QLabel)
│                           │   ├── labelViewportBadge (QLabel badge)
│                           │   └── horizontalSpacerViewport
│                           ├── verticalSpacerViewportTop
│                           ├── labelPlaceholder (QLabel)  ← placeholder VTK
│                           └── verticalSpacerViewportBottom
│
├── menubar (QMenuBar)
│   ├── menuArchivo
│   ├── menuEditar
│   ├── menuDiseno
│   ├── menuHerramientas
│   └── menuAyuda
│
├── toolBarExtensions (QToolBar, vertical, LeftToolBarArea)
│   ├── actionPartStudio (checkable, checked)
│   ├── actionEnsamblajes (checkable)
│   ├── [separator]
│   ├── actionExtensiones (checkable)
│   ├── actionKratosSolver (checkable)
│   ├── actionDatosReportes (checkable)
│   ├── [separator]
│   └── actionConfiguracion (checkable)
│
└── statusbar (QStatusBar)
    ├── labelVolumen     (QLabel "Volumen: <b>128.4 cm³</b>")
    ├── labelMasa        (QLabel "Masa: <b>346.7 g</b>")
    ├── labelFraccionVolumen (QLabel "Fracción de volumen: <b>35%</b>")
    ├── labelCompliance  (QLabel "Compliance: <b>4.82e-3</b>")
    └── labelConvergencia (QLabel "Convergencia: <b>0.4% Δ</b>")
```

---

## 3. Mapa de migración: .ui widgets → widget actual en `main_window.py`

| Widget .ui (objectName) | Widget actual en `main_window.py` | Estado |
|---|---|---|
| `tabModelo`, `tabOptimizacion`, `tabSimulacion` | `_tabs[0..3]` en `_build_workspace_tabs()` | **Reemplazable** — el .ui solo tiene 3 tabs (falta Fabricación) |
| `treeWidgetModel` | `self.design_tree` (`DesignTreePanel`) | **Reemplazable** — el .ui tiene un QTreeWidget estático; el actual es unQWidget con QTreeWidget interno |
| `listWidgetParts` | No existe (nuevo en .ui) | **Agregar** — lista de piezas debajo del árbol |
| `toolBarHerramientas` | `_build_ribbon()` (ribbon completo con 18+ tools) | **Reemplazable** — el .ui simplifica a 8 acciones Kratos específicas |
| `viewportWidget` / `labelPlaceholder` | `_ViewportHost` + `Viewport3D` (VTK real) | **Reemplazable** — reemplazar QFrame+QLabel por QFrame+Viewport3D |
| `labelViewportTitle` | `self.host._slots["badge"]` (overlay positioning) | **Reemplazable** — el .ui lo pone en layout normal |
| `labelViewportBadge` | `self.host._slots["badge"]` (overlay) | **Reemplazable** — mismo concepto |
| `toolBarExtensions` | Barra vertical izquierda (no existía) | **NUEVO** — barra de extensiones lateral |
| `statusbar` + 5 labels | `self.statusBar().showMessage(...)` (texto libre) | **Reemplazable** — el .ui tiene labels fijos dedicados |
| `menuArchivo/Editar/Diseno/Herramientas/Ayuda` | `_build_menus()` (8 menús con items) | **Parcial** — el .ui define menús vacíos; hay que agregar items |
| `actionMallaFEM` etc. | `_build_ribbon()` + menú Herramientas | **Reemplazable** — acciones del toolbar Kratos |

---

## 4. Imports necesarios por herramienta

Estos son los imports PySide6 que cada herramienta del .ui requiere
para funcionar. Cuando termines de diseñar la interfaz, asegúrate de
que cada widget esté cubierto:

### 4.1 Ventana principal y layout
```python
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFrame, QLabel, QStatusBar, QToolBar,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
```

### 4.2 Tabs de workspace (`tabModelo`, `tabOptimizacion`, `tabSimulacion`)
```python
from PySide6.QtWidgets import QToolButton
# checkable=True, autoRaise=True
# Señal: tab.toggled.connect(handler)
# Señal: tab.clicked.connect(handler)
```

### 4.3 Árbol del modelo (`treeWidgetModel`)
```python
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
# headerHidden=True, indentation=14
# Señal: treeWidgetModel.itemClicked.connect(handler)
# Señal: treeWidgetModel.itemDoubleClicked.connect(handler)
```

### 4.4 Lista de piezas (`listWidgetParts`)
```python
from PySide6.QtWidgets import QListWidget, QListWidgetItem
# frameShape=NoFrame
# Señal: listWidgetParts.itemClicked.connect(handler)
# Señal: listWidgetParts.currentRowChanged.connect(handler)
```

### 4.5 Toolbar de herramientas Kratos (`toolBarHerramientas`)
```python
from PySide6.QtWidgets import QToolBar, QToolButton
# movable=False, floatable=False
# iconSize=18x18
# Acciones via addaction:
#   actionMallaFEM, actionAnalisisFEM, actionSensibilidad,
#   actionFiltros, actionOptimizarMMA, actionSuavizado, actionExportar
# Señal: action.triggered.connect(handler)
# toolTip en cada action
```

### 4.6 Viewport 3D (reemplazar `labelPlaceholder`)
```python
from desktop.viewport.viewport_3d import Viewport3D
# Reemplazar labelPlaceholder por:
#   viewport_3d = Viewport3D()
#   verticalLayoutViewport.addWidget(viewport_3d)
# Señal: viewport_3d.selectionChanged.connect(handler)
```

### 4.7 Badge del viewport (`labelViewportBadge`)
```python
from PySide6.QtWidgets import QLabel
# objectName: labelViewportBadge
# Estilo: color:#bcd8ff; background:rgba(47,123,246,0.16);
#         border:1px solid rgba(74,141,255,0.38); border-radius:10px
# Actualización dinámica: badge.setText("Iteración 62/80")
```

### 4.8 Toolbar lateral de extensiones (`toolBarExtensions`)
```python
from PySide6.QtWidgets import QToolBar
from PySide6.QtGui import QAction
# orientation=Vertical
# toolBarArea=LeftToolBarArea
# movable=False, floatable=False
# Acciones (checkable):
#   actionPartStudio, actionEnsamblajes, actionExtensiones,
#   actionKratosSolver, actionDatosReportes, actionConfiguracion
# Señal: action.triggered.connect(toggle_panel_handler)
```

### 4.9 Status bar con labels fijos
```python
from PySide6.QtWidgets import QStatusBar, QLabel
# Labels embebidos en QStatusBar:
#   labelVolumen, labelMasa, labelFraccionVolumen,
#   labelCompliance, labelConvergencia
# Actualización dinámica:
#   self.labelVolumen.setText(f"Volumen: <b>{vol} cm³</b>")
#   self.labelMasa.setText(f"Masa: <b>{mass} g</b>")
#   self.labelFraccionVolumen.setText(f"Fracción de volumen: <b>{vf}%</b>")
#   self.labelCompliance.setText(f"Compliance: <b>{c:.2e}</b>")
#   self.labelConvergencia.setText(f"Convergencia: <b>{conv:.1f}% Δ</b>")
```

### 4.10 Menús con items (completar el .ui)
```python
from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction, QKeySequence
# Menús necesarios (el .ui los define vacíos):
#
# Archivo:
#   Importar archivo STEP...  (Ctrl+O)
#   Exportar resultado...
#   Exportar STEP...
#   ---
#   Salir (Ctrl+Q)
#
# Editar:
#   Limpiar selección
#   Reiniciar flujo
#
# Diseño:
#   Isométrica / Frontal / Superior / Lateral derecha (radio group)
#   ---
#   Ajustar a pantalla (F)
#   Centrar modelo
#
# Herramientas:
#   Generar malla
#   Análisis FEM
#   Optimizar SIMP
#
# Ayuda:
#   Acerca de
#
# + Menús nuevos del .ui (a decidir):
#   Operaciones → Boolean (Unión/Corte/Intersección)
#   Condiciones → Carga/Elasticidad/Obstrucción/Región protegida
#   Estudio → Nuevo estudio/Ejecutar estudio
```

### 4.11 Splitter
```python
from PySide6.QtWidgets import QSplitter
# bodySplitter: orientation=Horizontal
# handleWidth=1, childrenCollapsible=False
# treePanel: minW=200, maxW=320
# Estilo handle: background:#2a2b2e; width:1px
```

### 4.12 Estilos globales (ya en el .ui)
```python
# El .ui incluye una hoja de estilos completa en la propiedad
# styleSheet de MainWindow. Alternativa: usar desktop/ui/style.py
# (DARK_QSS) que es más extensa. Decidir cuál:
#
# Opción A: Usar el QSS del .ui (más limpio, menos cobertura)
# Opción B: Aplicar DARK_QSS de style.py después de loadUi()
# Opción C: Merge de ambos (recomendado)
```

---

## 5. Estrategia de integración paso a paso

### Fase 1: Carga del .ui (sin romper nada)
```python
# En main_window.py, reemplazar la construcción manual de widgets:
from PySide6.QtUiTools import QUiLoader
# O mejor: usar pyside6-uic para compilar .ui → .py en build time

# Opción recomendada (compilada en build time):
#   pyside6-uic desktop/ui/crea3d_mainwindow.ui -o desktop/ui/crea3d_mainwindow_ui.py
#
# En main_window.py:
#   from desktop.ui.crea3d_mainwindow_ui import Ui_MainWindow
#
#   class MainWindow(QMainWindow, Ui_MainWindow):
#       def __init__(self):
#           super().__init__()
#           self.setupUi(self)  # carga todos los widgets del .ui
```

### Fase 2: Conectar widgets del .ui al backend

| Widget del .ui | Conexión requerida | Handler existente |
|---|---|---|
| `tabModelo/ tabOptimizacion/ tabSimulacion` | `.toggled` → `_activate_tab(i)` | Sí |
| `actionMallaFEM` | `.triggered` → `_on_generate_mesh(...)` | Sí |
| `actionAnalisisFEM` | `.triggered` → `_on_run_fea` | Sí |
| `actionOptimizarMMA` | `.triggered` → `_on_run_optimization_default` | Sí |
| `actionSensibilidad` | `.triggered` → placeholder/status | Sí |
| `actionFiltros` | `.triggered` → `_on_focus_filter` | Sí |
| `actionSuavizado` | `.triggered` → placeholder/status | Nuevo |
| `actionExportar` | `.triggered` → `_on_export` | Sí |
| `actionPartStudio` etc. | `.triggered` → toggle panel visibility | Nuevo |
| `treeWidgetModel` | `.itemClicked` → `_on_selection` | Adaptar |
| `listWidgetParts` | `.itemClicked` → select part in viewport | Nuevo |
| `labelVolumen` etc. | Actualización en `_on_import_done`, `_on_optimization_done` | Nuevo |
| `labelViewportBadge` | Actualización en `_on_run_optimization` loop | Nuevo |

### Fase 3: Reemplazar paneles embebidos

Los 4 paneles actuales (`DesignTreePanel`, `PropertiesPanel`,
`ResultsPanel`, `TimelinePanel`) NO están en el .ui. El .ui solo
tiene `treeWidgetModel` y `listWidgetParts`.

**Decisión arquitectónica necesaria:**

| Opción | Descripción | Esfuerzo |
|--------|-------------|----------|
| **A: Mantener paneles Python** | El .ui define el shell; los paneles Python se embeben via `layout.addWidget()` | Bajo |
| **B: Migrar paneles al .ui** | Cada panel se rediseña en Qt Designer como .ui separado | Alto |
| **C: Híbrido** | .ui solo para la ventana principal; paneles se mantienen en Python | Recomendado |

**Recomendación: Opción C (híbrido).**
El .ui define la estructura global (menús, splitter, toolbar, status bar,
viewport). Los 4 paneles se mantienen como clases Python que se insertan
en los layouts del .ui:

```python
# Después de setupUi():
self.design_tree = DesignTreePanel()
self.verticalLayoutTree.addWidget(self.design_tree)  # reemplaza treeWidgetModel

self.properties = PropertiesPanel()
self.verticalLayoutTree.addWidget(self.properties)  # debajo del árbol

self.results = ResultsPanel()
# En un layout nuevo a la derecha del splitter (el .ui no tiene right sidebar)
# → agregar programmáticamente o extender el .ui

self.timeline = TimelinePanel()
self.verticalLayoutContent.addWidget(self.timeline)  # debajo del viewport
```

### Fase 4: Reemplazar el viewport placeholder

```python
# En setupUi() o después:
from desktop.viewport.viewport_3d import Viewport3D

# Eliminar labelPlaceholder del layout
self.labelPlaceholder.hide()
# self.verticalLayoutViewport.removeWidget(self.labelPlaceholder)

# Insertar Viewport3D
self.viewport = Viewport3D()
self.verticalLayoutViewport.addWidget(self.viewport)

# Reconectar señales
self.viewport.selectionChanged.connect(self._on_selection)
```

### Fase 5: Completar menús vacíos del .ui

Los menús del .ui están vacíos. Agregar items en Python:

```python
def _populate_menus(self):
    # Archivo (completar)
    act_open = QAction("Importar archivo STEP...", self)
    act_open.setShortcut(QKeySequence("Ctrl+O"))
    act_open.triggered.connect(self._on_import)
    self.menuArchivo.addAction(act_open)
    # ... resto de items

    # Diseño (completar con vistas)
    # Herramientas (completar)
    # Ayuda (completar)
```

### Fase 6: Conectar status bar labels

```python
def _update_status_bar(self, **kwargs):
    if "volume" in kwargs:
        self.labelVolumen.setText(f"Volumen: <b>{kwargs['volume']} cm³</b>")
    if "mass" in kwargs:
        self.labelMasa.setText(f"Masa: <b>{kwargs['mass']} g</b>")
    if "vol_frac" in kwargs:
        self.labelFraccionVolumen.setText(f"Fracción de volumen: <b>{kwargs['vol_frac']}%</b>")
    if "compliance" in kwargs:
        self.labelCompliance.setText(f"Compliance: <b>{kwargs['compliance']:.2e}</b>")
    if "convergence" in kwargs:
        self.labelConvergencia.setText(f"Convergencia: <b>{kwargs['convergence']:.1f}% Δ</b>")
```

---

## 6. Archivos que cambian

| Archivo | Cambio | Prioridad |
|---------|--------|-----------|
| `desktop/ui/crea3d_mainwindow.ui` | **Completar** (faltan menús items, señales,右sidebar, Fabricación tab) | Alta |
| `desktop/ui/crea3d_mainwindow_ui.py` | **Generar** con `pyside6-uic` (no commit, se genera en build) | Alta |
| `desktop/ui/main_window.py` | Refactor: heredar de `Ui_MainWindow`, eliminar construcción manual de widgets migrados al .ui | Alta |
| `desktop/ui/style.py` | Evaluar merge del QSS del .ui con `DARK_QSS` existente | Media |
| `desktop/ui/panels/properties.py` | Sin cambios (se mantiene como widget Python embebido) | - |
| `desktop/ui/panels/results.py` | Sin cambios (se mantiene; agregar al .ui o embeber) | - |
| `desktop/ui/panels/timeline.py` | Sin cambios (se mantiene como widget Python embebido) | - |
| `desktop/ui/panels/design_tree.py` | Sin cambios (se mantiene; reemplaza `treeWidgetModel` del .ui) | - |
| `desktop/ui/panels/study_panel.py` | Sin cambios (dialog modal, lazy import) | - |
| `desktop/ui/panels/boolean_panel.py` | Sin cambios (dialog modal, lazy import) | - |
| `desktop/ui/panels/condition_panel.py` | Sin cambios (dialog modal, lazy import) | - |

---

## 7. Inventario completo: qué tiene `.py` que NO tiene el `.ui`

Esta sección es la referencia para que decidas qué agregar al diseño en
Qt Designer. Cada item indica si es **crítico** (sin esto la app no
funciona), **deseable** (mejora la experiencia), o **nuevo** (funcionalidad
que el .ui propone y el .py no tiene).

---

### 7.1 Menús con items

El .ui define 5 menús **vacíos**. El .py tiene 8 menús con ~25 actions.

| Menú | Action | Atajo | Handler en .py | ¿Agregar al .ui? |
|------|--------|-------|----------------|-------------------|
| **Archivo** | Importar archivo STEP... | `Ctrl+O` | `_on_import` | Crítico |
| Archivo | Exportar resultado... | — | `_on_export` | Crítico |
| Archivo | Exportar STEP... | — | `_on_export_step` | Deseable |
| Archivo | Salir | `Ctrl+Q` | `self.close` | Crítico |
| **Editar** | Limpiar selección | — | `_on_clear_selection` | Deseable |
| Editar | Reiniciar flujo | — | `_on_reset_flow` | Deseable |
| **Operaciones** | Boolean → Unión | — | `_on_boolean_op("union")` | Deseable |
| Operaciones | Boolean → Corte | — | `_on_boolean_op("difference")` | Deseable |
| Operaciones | Boolean → Intersección | — | `_on_boolean_op("intersection")` | Deseable |
| **Condiciones** | Carga | — | `_on_condition_op("load")` | Deseable |
| Condiciones | Elasticidad | — | `_on_condition_op("elasticity")` | Deseable |
| Condiciones | Obstrucción | — | `_on_condition_op("obstruction")` | Deseable |
| Condiciones | Región protegida | — | `_on_condition_op("protected")` | Deseable |
| **Estudio** | Nuevo estudio de optimización... | — | `_on_create_study` | Deseable |
| Estudio | Ejecutar estudio (topología) | — | `_on_run_study` | Deseable |
| **Diseño** | Isométrica | — | `_on_view(ISO)` | Deseable |
| Diseño | Frontal | — | `_on_view(FRONT)` | Deseable |
| Diseño | Superior | — | `_on_view(TOP)` | Deseable |
| Diseño | Lateral derecha | — | `_on_view(RIGHT)` | Deseable |
| Diseño | Ajustar a pantalla | `F` | `viewport.fit_to_view()` | Deseable |
| Diseño | Centrar modelo | — | `viewport.center_model()` | Deseable |
| **Herramientas** | Generar malla | — | `_on_generate_mesh(...)` | Crítico |
| Herramientas | Análisis FEM | — | `_on_run_fea` | Crítico |
| Herramientas | Optimizar SIMP | — | `_on_run_optimization_default` | Crítico |
| **Ayuda** | Acerca de | — | `_on_about` | Nuevo |

> El .ui no tiene menús **Operaciones**, **Condiciones** ni **Estudio**.
> El .py los tiene como menús independientes. Decide si los agregas al .ui
> o si los cubres con el `toolBarExtensions` (el .ui ya tiene
> `actionKratosSolver`).

---

### 7.2 Top bar (barra superior)

El .ui **no tiene** top bar. El .py construye una barra de 52px de alto
con estos widgets:

| Widget | Función | ¿Agregar al .ui? |
|--------|---------|-------------------|
| Glyph label "◱" | Icono decorativo del app | Nuevo (diseño) |
| Title QLabel "OPTIMIZACIÓN TOPOLÓGICA" | Título centrado | Nuevo (diseño) |
| `chip_status` QLabel "☁ Standalone" | Estado de licencia (cambia dinámicamente) | Deseable |
| `_btn_import_top` QPushButton | Botón de importar arriba | Crítico (atajo visual) |
| Avatar QLabel "JD" | Avatar de usuario | Nuevo (diseño) |

> **Recomendación:** Agregar al .ui como un QWidget horizontal en la parte
> superior del `verticalLayoutCentral`, antes de los tabs.

---

### 7.3 Ribbon toolbar completo vs toolbar Kratos del .ui

El .ui tiene `toolBarHerramientas` con **8 acciones** (solo workflow Kratos).
El .py tiene un ribbon con **18+ tools** agrupados en 5 secciones:

| Sección | Tool | Glyph | Handler | ¿Agregar al .ui? |
|---------|------|-------|---------|-------------------|
| **Modelo** | Importar | 📂 | `_on_import` | Crítico |
| Modelo | Malla FEM | 🔲 | `_on_generate_mesh` | Crítico |
| Modelo | Malla adaptativa | 🔲⚡ | `_on_generate_adaptive_mesh` | Deseable |
| Modelo | Análisis FEM | ⚡ | `_on_run_fea` | Crítico |
| **Edición** | Unión | ⊕ | `_on_boolean_op("union")` | Deseable |
| Edición | Corte | ⊖ | `_on_boolean_op("difference")` | Deseable |
| Edición | Intersección | ⊗ | `_on_boolean_op("intersection")` | Deseable |
| Edición | Transformar | 🔄 | `_on_transform_op` | Nuevo |
| Edición | Espejo | ⇔ | `_on_mirror_op` | Nuevo |
| **Optimización** | Sensibilidad | 📊 | placeholder | Deseable |
| Optimización | Filtros | 🔍 | `_on_focus_filter` | Deseable |
| Optimización | Optimizar SIMP | ▶ | `_on_run_optimization_default` | Crítico |
| Optimización | Design Space | 📐 | placeholder | Nuevo |
| Optimización | Generativo | 🧬 | placeholder | Nuevo |
| **Postproceso** | Visualizar | 👁 | `_on_visualize_result` | Deseable |
| Postproceso | Exportar | 💾 | `_on_export` | Crítico |
| **Herramientas** | Validar | ✓ | placeholder | Nuevo |
| Herramientas | Exportar STEP | 📄 | `_on_export_step` | Deseable |

> **El .ui ya cubre:** Malla FEM, Análisis FEM, Sensibilidad, Filtros,
> Optimizar MMA, Suavizado, Exportar (7 de 8 acciones del toolbar Kratos).
>
> **Falta en el .ui:** Importar, Malla adaptativa, Boolean (3), Design Space,
> Generativo, Visualizar, Validar, Exportar STEP.
> (Transformar/Espejo/Patrón ya están cableados en la cinta + menú "Operaciones".)

---

### 7.4 Sidebar derecho (Results + Properties)

El .ui **no tiene** sidebar derecho. El .py tiene un layout de 3 columnas:

```
┌──────────────┬──────────────────────┬──────────────┐
│ LEFT (265px) │ CENTER (stretch=1)   │ RIGHT (250px)│
│              │                      │              │
│ DesignTree   │ Viewport3D           │ ResultsPanel │
│ Properties   │ TimelinePanel        │              │
│              │                      │              │
└──────────────┴──────────────────────┴──────────────┘
```

| Panel | Ubicación en .py | Widgets internos | ¿Agregar al .ui? |
|-------|-------------------|------------------|-------------------|
| `DesignTreePanel` | Left sidebar, arriba | QTreeWidget + botón Limpiar | El .ui ya tiene `treeWidgetModel` |
| `PropertiesPanel` | Left sidebar, abajo | Material, Fuerzas, Restricciones, Parámetros SIMP, botones | **Crítico** — es donde se configura todo |
| `ResultsPanel` | Right sidebar | Nodos, Elementos, Compliance, Convergencia, Log | **Crítico** — sin esto no se ven resultados |
| `TimelinePanel` | Debajo del viewport | 5 pasos del pipeline, playback controls | **Crítico** — guía el flujo de trabajo |

> **Recomendación para el .ui:** Agregar un `rightPanel` (QWidget) al
> `bodySplitter` después de `contentArea`, con un QScrollArea que contenga
> los labels de resultados. Los paneles Python (`PropertiesPanel`,
> `ResultsPanel`) se embeben via `layout.addWidget()` después de `setupUi()`.

---

### 7.5 Viewport overlays (elementos superpuestos al Viewport 3D)

El .ui tiene `labelViewportBadge` y `labelViewportTitle` en layout normal.
El .py tiene un sistema de overlays posicionados absolutamente sobre el VTK:

| Overlay | Posición | Widget | Función | ¿Agregar al .ui? |
|---------|----------|--------|---------|-------------------|
| `badge` | Arriba-izquierda | QWidget con QLabel + chip | Muestra "Optimización" + "SIMP" | Deseable |
| `controls` | Arriba-derecha | 5 QPushButton toggle | Ajustar/Wireframe/Ejes/Fuerzas/Restricciones | Deseable |
| `status` | Abajo | QWidget con dots + info | Leyenda de colores (sólido/carga/restricción) | Nuevo |
| `placeholder` | Centro | QLabel | "Importe un STEP" (se oculta al cargar) | El .ui ya lo tiene |

> **El .ui ya tiene** `labelPlaceholder`. **Faltan:** badge, controls, status.
> Estos se pueden agregar como widgets flotantes en el .ui o mantenerse
> como overlays programáticos (como el .py actual).

---

### 7.6 Workspace tabs

| Tab | En .ui | En .py | ¿Agregar al .ui? |
|-----|--------|--------|-------------------|
| Modelo | `tabModelo` | `_tabs[0]` | Ya está |
| Optimización | `tabOptimizacion` | `_tabs[1]` | Ya está |
| Simulación | `tabSimulacion` | `_tabs[2]` | Ya está |
| **Fabricación** | **NO** | `_tabs[3]` | **Falta** — agregar `tabFabricacion` |

> El .py tiene 4 tabs. El .ui solo 3. Falta **Fabricación**.

---

### 7.7 Acciones nuevas del .ui que el .py NO tiene

El .ui propone acciones que el .py actual no implementa:

| Acción .ui | Función propuesta | ¿Mantener en el .ui? |
|------------|-------------------|-----------------------|
| `actionPartStudio` | Cambiar a vista Part Studio | Sí (nuevo flujo) |
| `actionEnsamblajes` | Vista de ensamblajes | Sí (nuevo flujo) |
| `actionExtensiones` | Panel de extensiones/plugins | Sí (nuevo flujo) |
| `actionKratosSolver` | Panel del solver Kratos | Sí (ya existe en .py como menú) |
| `actionDatosReportes` | Datos y reportes | Sí (nuevo flujo) |
| `actionConfiguracion` | Configuración de la app | Sí (nuevo flujo) |
| `listWidgetParts` | Lista de piezas (original + optimizada) | Sí (nuevo, no existe en .py) |

---

### 7.8 Status bar

| Elemento | En .ui | En .py | ¿Agregar al .ui? |
|----------|--------|--------|-------------------|
| `labelVolumen` | "Volumen: **128.4 cm³**" | `statusBar().showMessage("Listo...")` (texto libre) | Sí — label fijo dinámico |
| `labelMasa` | "Masa: **346.7 g**" | No existe | Sí — nuevo |
| `labelFraccionVolumen` | "Fracción de volumen: **35%**" | No existe | Sí — nuevo |
| `labelCompliance` | "Compliance: **4.82e-3**" | No existe (se muestra en ResultsPanel) | Sí — nuevo |
| `labelConvergencia` | "Convergencia: **0.4% Δ**" | No existe | Sí — nuevo |

> El .ui es **mejor** que el .py aquí: tiene labels dedicados en vez de
> un solo `showMessage()`. Esto permite actualización por separado de cada
> métrica sin reescribir todo el texto.

---

### 7.9 Señales y conexiones

El .ui **no tiene** `<connections>`. El .py tiene ~40 conexiones de señales.

| Señal | Widget origen | Target en .py | ¿Conectar en .ui? |
|-------|---------------|---------------|---------------------|
| `triggered` | Cada QAction | Handler correspondiente | Crítico |
| `toggled` | Tabs | `_activate_tab(i)` | Crítico |
| `itemClicked` | `treeWidgetModel` | `_on_selection` | Deseable |
| `itemClicked` | `listWidgetParts` | Selección de pieza | Nuevo |
| `clicked` | Botones toolbar | Handlers de cada tool | Crítico |
| `selectionChanged` | Viewport3D | `_on_selection` | Crítico |
| `playRequested` | TimelinePanel | `_on_play_next` | Crítico |
| `resetRequested` | TimelinePanel | `_on_reset_flow` | Crítico |
| `generateMesh` | PropertiesPanel | `_on_generate_mesh` | Crítico |
| `runFEA` | PropertiesPanel | `_on_run_fea` | Crítico |
| `runOptimization` | PropertiesPanel | `_on_run_optimization` | Crítico |

> Las señales se conectan en Python después de `setupUi()`, no en el .ui.
> Pero el .ui debe tener las **actions** definidas para que `self.actionMallaFEM`
> exista al hacer `setupUi()`.

---

### 7.10 Resumen: quéSÍ tiene el .ui y quéFALTA

```
TIENE EL .UI ✓                              FALTA EN EL .UI ✗
─────────────────────────────               ─────────────────────────────
✅ Workspace tabs (3/4)                     ✗ Tab Fabricación
✅ treeWidgetModel (QTreeWidget)            ✗ PropertiesPanel layout
✅ listWidgetParts (QListWidget)            ✗ ResultsPanel layout
✅ toolBarHerramientas (8 actions Kratos)   ✗ Importar, Boolean, Transformar...
✅ toolBarExtensions (7 actions laterales)  ✗ (son nuevos, OK)
✅ viewportWidget + placeholder             ✗ Viewport3D real
✅ labelViewportBadge + labelViewportTitle  ✗ Overlays (controls, status legend)
✅ statusbar con 5 labels                   ✗ (completo, solo datos hardcodeados)
✅ 5 menús (vacíos)                         ✗ Items en todos los menús
✅ Top bar NO tiene                          ✗ Top bar completa
✅ QSS dark theme inline                    ✗ (evaluar merge con DARK_QSS)
✅ 13 actions definidas                     ✗ ~12 actions faltantes
✅ Signals: Ninguna                          ✗ ~40 conexiones
✅ Sidebar derecho NO tiene                  ✗ ResultsPanel + PropertiesPanel
✅ TimelinePanel NO tiene                    ✗ TimelinePanel layout
```

---

## 8. Patrón de herencia recomendado

```python
# desktop/ui/main_window.py

from desktop.ui.crea3d_mainwindow_ui import Ui_MainWindow  # generado por pyside6-uic

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # carga todo el .ui

        # Paneles Python que se embeben en layouts del .ui
        self._embed_panels()
        self._connect_signals()
        self._populate_menus()

    def _embed_panels(self):
        """Inserta widgets Python en los layouts definidos por el .ui."""
        # Reemplazar treeWidgetModel estático por DesignTreePanel
        self.verticalLayoutTree.removeWidget(self.treeWidgetModel)
        self.treeWidgetModel.hide()
        self.design_tree = DesignTreePanel()
        self.verticalLayoutTree.insertWidget(1, self.design_tree)

        # Properties debajo del árbol
        self.properties = PropertiesPanel()
        self.verticalLayoutTree.addWidget(self.properties)

        # Viewport real reemplaza placeholder
        self.labelPlaceholder.hide()
        self.viewport = Viewport3D()
        self.verticalLayoutViewport.insertWidget(1, self.viewport)

        # Timeline debajo del viewport
        self.timeline = TimelinePanel()
        self.verticalLayoutContent.addWidget(self.timeline)

        # Results (agregar sidebar derecho al splitter)
        self.results = ResultsPanel()
        right_sidebar = QWidget()
        right_layout = QVBoxLayout(right_sidebar)
        right_layout.addWidget(self.results)
        self.bodySplitter.addWidget(right_sidebar)
```

---

## 9. Generación automática del .ui

Para no depender de `PySide6.QtUiTools` en runtime:

```bash
# Compilar .ui → .py (hacer después de cada cambio en Qt Designer)
pyside6-uic desktop/ui/crea3d_mainwindow.ui \
    -o desktop/ui/crea3d_mainwindow_ui.py
```

Agregar a `pyproject.toml` o `Makefile`:
```makefile
ui: desktop/ui/crea3d_mainwindow_ui.py

desktop/ui/crea3d_mainwindow_ui.py: desktop/ui/crea3d_mainwindow.ui
	pyside6-uic $< -o $@
```

---

## 10. Checklist de integración

- [ ] Completar el .ui en Qt Designer (menús, señales,右sidebar, tab Fabricación)
- [ ] Compilar .ui → .py con `pyside6-uic`
- [ ] Refactor `MainWindow` para heredar de `Ui_MainWindow`
- [ ] Eliminar `_build_central()` manual (reemplazado por `setupUi`)
- [ ] Eliminar `_build_workspace_tabs()` (reemplazado por tabModelo/...)
- [ ] Eliminar `_build_ribbon()` (reemplazado por toolBarHerramientas)
- [ ] Eliminar `_build_topbar()` (no está en el .ui; evaluar si agregarlo)
- [ ] Mantener `_build_menus()` y agregar items a los menús del .ui
- [ ] Embeber `DesignTreePanel`, `PropertiesPanel`, `ResultsPanel`, `TimelinePanel` en layouts del .ui
- [ ] Reemplazar `labelPlaceholder` por `Viewport3D`
- [ ] Conectar señales de todas las actions del .ui a handlers existentes
- [ ] Conectar `treeWidgetModel` a `_on_selection`
- [ ] Conectar `listWidgetParts` a selección de pieza
- [ ] Actualizar status bar labels dinámicamente
- [ ] Merge de QSS del .ui con `DARK_QSS` de `style.py`
- [ ] Ejecutar suite de tests completa
- [ ] Verificar que la app arranca y el viewport VTK funciona
