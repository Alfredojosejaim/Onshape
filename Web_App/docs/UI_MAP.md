# UI_MAP — Mapa interactivo completo de la interfaz (`html/src`)

> Generado 2026-09-09 por lectura directa del código. Solo se leyó `html/src`; no se modificó nada fuera de `docs/UI_MAP.md`.
> Convención: cada ítem cita `archivo:línea`. Rutas relativas a `Web_App/html/src/`.
> Leyenda backend: **CABLEADO** = llama a `backend.*` con pywebview real · **MOCK** = `bridge.ts` devuelve mock sin pywebview · **DEMO** = simula en frontend sin backend · **SIN-CABLEAR** = no llama a ningún backend.

---

## 1. ÁRBOL DE COMPONENTES + FLUJO DE ESTADO GLOBAL

```
App (App.tsx:40)
├── Header (App.tsx:158, Header.tsx:28) ............ barra superior fija + tabs 1-5
├── backendError banner (App.tsx:167)
├── Sidebar (App.tsx:179, Sidebar.tsx:10) .......... árbol operaciones + snapshot.model_name
├── Viewport dinámico (App.tsx:182)
│   ├── Screen1CadPreProcess (App.tsx:184) ......... CAD + material + viewer real
│   ├── Screen2MeshingConditions (App.tsx:194) ..... Gmsh + BCs + SVG estático
│   ├── Screen3FeaSolver (App.tsx:201) ............. FEA + colormap + jobs
│   ├── Screen4TopologyOptimization (App.tsx:210) .. SIMP + densidades + jobs
│   └── Screen5GenerativeBRepExport (App.tsx:218) .. B-Rep SVG + export
├── Footer (App.tsx:228, Footer.tsx:9) ............. telemetría fija
├── ImportStepModal (App.tsx:231) ──► onModelSelected → App.handleModelSelected
├── HelpModal (App.tsx:237)
└── CreateStudyModal (App.tsx:239) ──► onCreateStudy → App.handleCreateStudy
MeshViewer (MeshViewer.tsx:79, forwardRef) usado en Screen1/3/4
ViewCube (ViewCube.tsx:8) usado en Screen1/2/3/4/5
```

### 1.1 Estado que vive en `App` (global)

| Estado | Archivo:línea | Tipo | Quién lo escribe | A quién baja por props |
|---|---|---|---|---|
| `currentScreen` | `App.tsx:41` | `ScreenId` (`types.ts:1`) | `setCurrentScreen`: shortcuts teclado `App.tsx:107-116`, Header tabs/toolbar, Sidebar, `handleModelSelected` `App.tsx:139`, `handleCreateStudy` `App.tsx:145`, botones avance de cada Screen | `Header.currentScreen` `App.tsx:159`, `Sidebar.currentScreen` `App.tsx:179`, render condicional Screens `App.tsx:183-223` |
| `materials` | `App.tsx:42` | `MaterialProperty[]` (`types.ts:10`, datos `data/materials.ts:3`) | init `MATERIALS`, refresh `backend.getMaterials()` `App.tsx:80-90` | `Screen1.materials` `App.tsx:189`, usado en `handleCreateStudy` `App.tsx:147` |
| `selectedMaterial` | `App.tsx:43` | `MaterialProperty` | init `MATERIALS[0]`, `handleSelectMaterial` `App.tsx:130` (hace `backend.setMaterial`), `handleCreateStudy` `App.tsx:146-149` | `Screen1.selectedMaterial` `App.tsx:186`, `Screen3.material` `App.tsx:205`, `Screen5.material` `App.tsx:219` |
| `activeBackend` | `App.tsx:44` | `FeaBackend` (`types.ts:8`: `'numpy'\|'kratos'`) | `setActiveBackend` directo (Screen3) `App.tsx:204`; Header querría `onToggleBackend` (ver §7 bug) | `Screen3.backend` `App.tsx:203`; intentado `Header.activeBackend` `App.tsx:161` |
| `activeFilename` | `App.tsx:45` | `string` | init `'cono_soporte_aero.step'`; `refreshSnapshot` lo pisa con `snapshot.model_name` `App.tsx:67`; `handleModelSelected` `App.tsx:139` | `Screen1.activeFilename` `App.tsx:188`, `Screen2.activeFilename` `App.tsx:196`, `Screen5.activeFilename` `App.tsx:221`; intentado `Header.activeFilename` |
| `snapshot` | `App.tsx:46` | `BackendSnapshot` (`App.tsx:17`) | `refreshSnapshot()` → `backend.getSnapshot()` `App.tsx:62-74`; al montar `App.tsx:95` | `Sidebar.snapshot` `App.tsx:179` (solo muestra `model_name` `Sidebar.tsx:93`); `counts` → `Footer` `App.tsx:228` |
| `backendError` | `App.tsx:47` | `string\|null` | cualquier `catch` (`App.tsx:72,92,135`) | banner con botón `ocultar` `App.tsx:167-174` |
| `simpConfig` | `App.tsx:49-56` | `SimpConfig` (`types.ts:57`) | `handleUpdateSimpConfig` merge parcial `App.tsx:126-128` | `Screen4.simpConfig/onUpdateSimpConfig` `App.tsx:212-213` |
| `isImportModalOpen/isHelpModalOpen/isCreateStudyModalOpen` | `App.tsx:58-60` | `boolean` | setters locales; shortcut `?`/`h` abre ayuda `App.tsx:117` | `isOpen/onClose` de cada modal `App.tsx:231-243` |

### 1.2 Estado local (`useState`) por componente — no sube a App

| Componente | Estado local | Archivo:línea | Notas de cableado |
|---|---|---|---|
| `Header` | ninguno (props + const `screens` lista) | `Header.tsx:38-44` | Todos los botones emiten callbacks; el toggle motor llama `onToggleBackend` (prop que App **no** pasa → bug §7) |
| `Sidebar` | ninguno (const `navItems`) | `Sidebar.tsx:11-47` | Solo `onSelectScreen`; badges hardcodeados (`Sólido`, `p=3.0`…) |
| `Footer` | ninguno (defaults por props) | `Footer.tsx:9-13` | `elementsCount=184920`, `nodesCount=38412`, `cursorCoordinates` estático; sin setters |
| `ViewCube` | `activeFace` (`'ISO'` init) | `ViewCube.tsx:9-16` | `handleFaceClick` → `setActiveFace` + `onViewChange(face)` al padre |
| `MeshViewer` | refs escena/cámara/controles/malla/marcador/clip/profile (`useRef`), `selInfo` (`useState`) | `MeshViewer.tsx:96-108` | Reconstruye geometría en `useEffect [mesh, values, colorMin, colorMax]` `MeshViewer.tsx:388`; expone `setView/reset` por ref `MeshViewer.tsx:162` |
| `Screen1` | `hMin/hMax` (1.5/6.0), `selectionMode`, `wireframeActive`, `clipActive`, `isRemeshing/remeshStatus/remeshError`, `globalCoordsExpanded`, `previewMesh/meshError/meshLoading`, `navProfile`, `selPoint` | `Screen1CadPreProcess.tsx:43-57` | `handleRemesh` → `generateMesh` + `loadMeshPreview`; `handleNavProfile` → `setNavProfile` + backend |
| `Screen2` | `elementShrink`, `showNodeCloud`, `meshAlgorithm`, `isMeshing`, `activeTab` (**muerto**: `void` `Screen2:35-36`**), `loadMagnitude`, `meshStatus/meshError` | `Screen2MeshingConditions.tsx:27-36` | `handleGenerateMesh` → `generateMesh` + `setBoundaries` |
| `Screen3` | `scaleFactor/isAnimating/animPhase`, `activeFieldMode`, `wireframeVisible`, `probeSelected`, `jobId/feaBusy/feaError/feaResult`, `previewMesh/meshError/meshLoading`, `fieldValues/fieldMin/fieldMax/fieldError/fieldLoading`, `navProfile` (solo lectura, sin setter), `poll=useJobPoll(jobId)` | `Screen3FeaSolver.tsx:40-62` | `handleSolve` → `runFea`; `loadSurfaceField` → `window.pywebview.api.getSurfaceMesh` directo |
| `Screen4` | `currentIter` (init **42**), `isPlaying`, `isoThreshold`, `viewMode`, `jobId/optBusy/optError/optResult`, `previewMesh/meshError/meshLoading`, `densityValues/densityMin/densityMax/densityError/densityLoading`, `navProfile` (solo lectura), `poll=useJobPoll(jobId)` | `Screen4TopologyOptimization.tsx:36-56` | `handleRunOptimization` → `runOptimization`; `loadDensityField` → `getSurfaceMesh` directo |
| `Screen5` | `zebraView/curvatureView/wireframeOn`, `isExporting/downloadSuccess`, `exportPath`, `exportStatus/exportError` | `Screen5GenerativeBRepExport.tsx:30-37` | `handleBackendExport` → `exportStep`; `handleDownload` → descarga sintética |
| `ImportStepModal` | `selectedPreset`, `dragActive`, `importedCustomName`, `stepPath`, `isImporting`, `status/statusError` | `ImportStepModal.tsx:16-22` | `handleConfirm` → `importStep` + `onModelSelected(base)` + `onClose` |
| `CreateStudyModal` | `studyName`, `analysisType`, `selectedMaterialId`, `loadMagnitudeN` | `CreateStudyModal.tsx:16-19` | `handleSubmit` → `onCreateStudy({...})` + `onClose`; **sin** llamada backend |
| `HelpModal` | ninguno | `HelpModal.tsx:9` | Solo `onClose` |

### 1.3 Flujos de datos clave

- **Materiales**: `App useEffect` `App.tsx:78-97` → `getMaterials()` → `setMaterials/setSelectedMaterial`; `Screen1` select `Screen1:615-628` → `onSelectMaterial` → `App.handleSelectMaterial` `App.tsx:130` → `setMaterial(m.name)`. Error → `backendError` banner.
- **Snapshot**: `refreshSnapshot` `App.tsx:62` → `getSnapshot()` → `snapshot` → `Sidebar` (`model_name` `Sidebar.tsx:93`) y `Footer` (conteos con fallback `App.tsx:153,228`; normalización alias `App.tsx:30-38`).
- **Jobs FEA/SIMP**: `runFea/runOptimization` devuelven `jobId` → `useJobPoll(jobId)` (`lib/jobs.ts:13`) sondea `pollJob` cada 2 s (`jobs.ts:58`) → `onDone` fija `feaResult/optResult` → dispara `loadSurfaceField/loadDensityField`.
- **Navegación**: `Screen1` carga `getNavProfiles().current` y persiste `localStorage 'topoopt.nav'` (`Screen1:91-115`, `lib/navigation.ts:75,82`); Screen3/4 solo leen `readStoredNavProfile()` sin setter.

---

## 2. TABLA MAESTRA DE CONTROLES INTERACTIVOS

### 2.0 Globales (App + Header + Sidebar + Footer + teclado)

| # | Ubicación | Control | Archivo:línea | Handler | Estado que muta | Llamada backend | Resultado / error dónde se ve |
|---|---|---|---|---|---|---|---|
| G1 | App | Shortcuts `1-5` cambian pantalla | `App.tsx:107-116` | `handleKeyDown` + `setCurrentScreen` | `currentScreen` | — (SIN-CABLEAR) | viewport cambia; ignorado si foco en `INPUT/SELECT/TEXTAREA` `App.tsx:103` |
| G2 | App | Shortcuts `?` / `h` abren ayuda | `App.tsx:117` | `setIsHelpModalOpen(true)` | `isHelpModalOpen` | — | `HelpModal` |
| G3 | App | Banner error `ocultar` | `App.tsx:170` | `setBackendError(null)` | `backendError` | — | banner desaparece |
| G4 | Header toolbar | `Importar STEP` | `Header.tsx:79-87` | `onOpenImportModal` → `setIsImportModalOpen(true)` | modal open | — | abre `ImportStepModal` |
| G5 | Header toolbar | `Crear Estudio` | `Header.tsx:89-97` | `onOpenCreateStudyModal` | modal open | — | abre `CreateStudyModal` |
| G6 | Header toolbar | `Malla Gmsh` | `Header.tsx:99-110` | `onSelectScreen('mallado-y-condiciones')` | `currentScreen` | — | Screen2; resaltado si activa `Header.tsx:102` |
| G7 | Header toolbar | `Resolver FEA (K·u=F)` | `Header.tsx:112-123` | `onSelectScreen('solver-fea-y-tensiones')` | `currentScreen` | — | Screen3 |
| G8 | Header toolbar | `Optimización SIMP` | `Header.tsx:125-136` | `onSelectScreen('optimizacion-topologica-simp')` | `currentScreen` | — | Screen4 |
| G9 | Header toolbar | `Reconstrucción B-Rep` | `Header.tsx:138-149` | `onSelectScreen('generativo-y-b-rep-export')` | `currentScreen` | — | Screen5 |
| G10 | Header toolbar | `Exportar STEP` | `Header.tsx:151-158` | `onSelectScreen('generativo-y-b-rep-export')` (¡mismo destino que G9!) | `currentScreen` | — (SIN-CABLEAR: no exporta, solo navega) | Screen5; para exportar real usar `Exportar vía backend` en Screen5 |
| G11 | Header chip motor | toggle `RefreshCw` numpy↔kratos | `Header.tsx:170-177` | `onToggleBackend` | `activeBackend` (esperado) | — (previsto) | chip `Header.tsx:167-169`; ⚠️ **App no pasa `onToggleBackend`/`backend`/`activeFilename` → botón roto** (ver §7) |
| G12 | Header | `?` ayuda (icono) | `Header.tsx:185-192` | `onOpenHelpModal` | `isHelpModalOpen` | — | `HelpModal` |
| G13 | Header tabs | 5 tabs `screens[]` | `Header.tsx:205-221` | `onSelectScreen(screen.id)` | `currentScreen` | — | tab activa `Header.tsx:212` |
| G14 | Sidebar | 5 items árbol operaciones | `Sidebar.tsx:62-81` | `onSelectScreen(item.path)` | `currentScreen` | — | resaltado `Sidebar.tsx:68`; badges estáticos |
| F1-F3 | Footer | XYZ / Elementos / Nodos (solo lectura) | `Footer.tsx:19-34` | — (ninguno) | props con defaults | — (DEMO: `184920/38412` si no hay snapshot `App.tsx:228`) | propio footer; unidades y `60 FPS` hardcodeados `Footer.tsx:25,40` |

### 2.1 Screen1 — CAD & Pre-proceso (`Screen1CadPreProcess.tsx`)

| # | Control | Archivo:línea | Handler | Estado | Backend | Resultado/error |
|---|---|---|---|---|---|---|
| S1-1 | Árbol: `Sist. Coordenado Global` colapsable | `:168-180` | `setGlobalCoordsExpanded(!…)` | `globalCoordsExpanded` | — | muestra/oculta Planos XY/XZ/YZ |
| S1-2 | Filas Planos XY/XZ/YZ | `:184-202` | ninguno (divs con hover) | — | SIN-CABLEAR | sin efecto |
| S1-3 | Nodo sólido `{activeFilename}` + ojo | `:206-217` | ninguno | prop `activeFilename` | — | informativo; `12 Caras…` hardcodeado `:213` |
| S1-4 | Nodos Encastre / Tracción / Región SAFE / Obstáculo VOID | `:220-277` | ninguno (hover) | — | SIN-CABLEAR | informativos; vectores `[0,-4500,1200] N` hardcodeados `:241` |
| S1-5 | Input `h_min` | `:304-312` | `setHMin(parseFloat…\|\|1.5)` | `hMin` | — (el valor **no** se envía: `handleRemesh` solo manda `hMax` `:122`) | — |
| S1-6 | Input `h_max` | `:320-328` | `setHMax(…\|\|6.0)` | `hMax` | **CABLEADO** vía S1-7 | — |
| S1-7 | Botón `Remallar Geometría Gmsh` | `:350-358` | `handleRemesh` `:117-137` | `isRemeshing/remeshStatus/remeshError` | **CABLEADO** `backend.generateMesh({target_element_size: hMax})` `:122` | OK → `remeshStatus` `:360` + `loadMeshPreview()`; error → `remeshError` `:363` |
| S1-8 | Toggle selección `Caras/Aristas/Vértices/Volúmenes` | `:383-438` | `setSelectionMode(…)` | `selectionMode` | SIN-CABLEAR (visual; el pick real del viewer no filtra por modo) | resaltado botón |
| S1-9 | Toggle `Plano de Corte (Clip)` tijeras | `:443-452` | `setClipActive(!…)` | `clipActive` → prop `clip` de `MeshViewer` `:545` | — (corte GPU local, plano X en `MeshViewer.tsx:486-506`) | viewport recorta |
| S1-10 | Botón `Medición` regla | `:454-460` | ninguno | — | SIN-CABLEAR | sin efecto |
| S1-11 | Toggle `Wireframe` rejilla | `:462-471` | `setWireframeActive(!…)` | `wireframeActive` → `MeshViewer` `:545` | — | malla alambre/sólido (`MeshViewer.tsx:478-480`) |
| S1-12 | Botón `Aislar Selección` filtro | `:473-479` | ninguno | — | SIN-CABLEAR | sin efecto |
| S1-13 | Select perfil navegación | `:483-492` | `handleNavProfile` `:111-115` | `navProfile` + `localStorage` | **CABLEADO** `backend.setNavProfile(p)` (fire-and-forget, `.catch(()=>undefined)`) | tooltip muestra mapeo `:487`; error silenciado |
| S1-14 | `ViewCube` + stack cámara (fit/rotar/pan) | `:498-523` | `handleViewChange` `:143` → `mapCubeFace` → `viewerRef.setView/reset`; `resetCamera` `:139` | `activeFace` (ViewCube) | — | cámara three.js (`MeshViewer.tsx:118-150`) |
| S1-15 | Botones cámara `3d_rotation` / `pan_tool` | `:508-521` | ninguno | — | SIN-CABLEAR | sin efecto (rotar/pan reales son con ratón según perfil) |
| S1-16 | Botón `Cargar malla` + `Reintentar` | `:537-539,548-555` | `loadMeshPreview` `:60-84` | `previewMesh/meshLoading/meshError` | **CABLEADO** `backend.getMeshPreview()` (MOCK sin pywebview → mesh `null`, vacío elegante `:72`) | banner carga/error `:527-543`; `MeshViewer mesh=` `:545` |
| S1-17 | Click picking sobre malla | vía `MeshViewer onSelect` `:545` | `setSelPoint(…)` | `selPoint` | — | chip `sel […]` `:590-592` + marcador esfera (`MeshViewer.tsx:254-268`) |
| S1-18 | Select `Aleación/Polímero` | `:615-628` | `onSelectMaterial(mat)` → `App.handleSelectMaterial` | `selectedMaterial` (App) | **CABLEADO** `backend.setMaterial(m.name)` `App.tsx:133` | tabla E/ν/σy/ρ/tracción `:637-656`; error → banner App |
| S1-19 | CTA `Validar Condiciones & Generar Malla` | `:724-731` | `onAdvanceToMesh` → `setCurrentScreen('mallado…')` | `currentScreen` | — (solo navega; no valida ni malla) | Screen2 |

### 2.2 Screen2 — Mallado & Condiciones (`Screen2MeshingConditions.tsx`)

Viewport central es **SVG estático** (`:234-329`), no `MeshViewer`. `elementShrink` y `meshAlgorithm` no afectan al dibujo.

| # | Control | Archivo:línea | Handler | Estado | Backend | Resultado/error |
|---|---|---|---|---|---|---|
| S2-1 | Botón `Remallar` (strip superior) | `:96-102` | `handleGenerateMesh` `:38-66` | `isMeshing/meshStatus/meshError` | **CABLEADO** `generateMesh({target_element_size: 6.0})` + `setBoundaries({bottom_axis:2, load_dir:[0,0,1], magnitude: loadMagnitude})` | `meshStatus/meshError` abajo `:426-434`; spinner `:100` |
| S2-2 | Select `Algoritmo Volumétrico 3D` | `:125-133` | `setMeshAlgorithm` | `meshAlgorithm` | SIN-CABLEAR (**no** se envía: `handleGenerateMesh` usa tamaño fijo 6.0) | solo cambia el select |
| S2-3 | Slider `Shrink 0-0.5` | `:181-189` | `setElementShrink` | `elementShrink`, label `%` `:179` | SIN-CABLEAR/DEMO (no toca SVG ni malla) | solo número |
| S2-4 | Toggle `Nube de Nodos Visible/Oculto` | `:197-204` | `setShowNodeCloud(!…)` | `showNodeCloud` | — (local) | muestra/oculta `<g>` nodos SVG `:278-298` |
| S2-5 | `ViewCube` (sin `onViewChange`) | `:218-220` | `handleFaceClick` interno cambia `activeFace` pero **nadie lo escucha** | `activeFace` local | SIN-CABLEAR | ningún movimiento (pasar `onViewChange` + ref como en Screen1/3/4 para cablearlo) |
| S2-6 | Input `Magnitud (N)` BCs | `:376-382` | `setLoadMagnitude` | `loadMagnitude` (init 4500) | **CABLEADO** vía S2-1 (`magnitude`) | — |
| S2-7 | Botón `Resolver FEA (K·u=F)` | `:435-442` | `onAdvanceToFea` | `currentScreen` | — (navega) | Screen3 |
| — | Tabs `mesh/bcs` | `:31,35-36` | ninguno (`void activeTab`) | muerto | — | código muerto: quitar o cablear |

### 2.3 Screen3 — Solver FEA (`Screen3FeaSolver.tsx`)

| # | Control | Archivo:línea | Handler | Estado | Backend | Resultado/error |
|---|---|---|---|---|---|---|
| S3-1 | Botón `Re-computar/Resolver FEA` | `:273-280` | `handleSolve` `:167-193` | `feaBusy/jobId/feaError/feaResult` | **CABLEADO** `runFea({backend: feaBackend})` → `jobId`; **DEMO** sin bridge: resetea escala y sale `:169-174` | estado `feaStatusText` `:195-203` → banner `:419-423`; JSON real `:424-428`; sondeo `useJobPoll` |
| S3-2 | Selector motor `NumPy/SciPy` | `:301-317` | `onSetBackend('numpy')` | `activeBackend` (App) | — (solo cambia flag que se envía en el próximo `runFea`) | resaltado + telemetría `NumPy Core vs AMGCL` `:342` |
| S3-3 | Selector motor `Kratos` | `:319-335` | `onSetBackend('kratos')` | idem | — | idem |
| S3-4 | Tabs campo `Von Mises / Disp / σ₁ / SED` | `:483-523` | `setActiveFieldMode` | `activeFieldMode` | **CABLEADO parcial**: `vonmises/disp` → `getSurfaceMesh({field})` directo a `window.pywebview.api` `:105-150` (fuera de `bridge.ts`); `sigma1/sed` → `setFieldValues(null)` `:157` (SIN-CABLEAR, limpiamapa) | `MeshViewer values=` `:568`; leyenda `colorbarLabel` `:570`; texto estado `:574`; error `fieldError` |
| S3-5 | Toggle `Wireframe` | `:527-535` | `setWireframeVisible(!…)` | `wireframeVisible` → `MeshViewer` `:567` | — | alambre |
| S3-6 | Botones vectores / isosuperficie / captura | `:536-554` | ninguno | — | SIN-CABLEAR | sin efecto |
| S3-7 | Slider + presets `1x/5x/20x` deformación | `:646-680` | `handlePresetScale` (para animación; anim loop escribe `osc` cada 45 ms `:206-221`) | `scaleFactor` (+`animPhase`) | DEMO (deformación visual; el `skewDeg/deformY` `:238-239` están calculados pero **no aplicados** a ningún SVG) | label `S3:640-642`; en `MeshViewer` no deforma geometría |
| S3-8 | Play/Pause ciclo armónico | `:686-694` | `handlePlayPause` `:223-230` | `isAnimating` (+reset 5.0 al pausar) | DEMO (`setInterval` 45 ms) | icono Play/Pause |
| S3-9 | `Reset Cámara` + `Cargar malla` | `:697-703,576-579` | `viewerRef.reset()` / `loadMeshPreview` (`getMeshPreview` `:65-86`) | — / `previewMesh/meshError` | — / **CABLEADO** | — / banner `:561-565` |
| S3-10 | Hotspots (3 tarjetas, 2 clicables) | `:756-810` | `setProbeSelected('14092'/'08941')` (3ª sin handler) | `probeSelected` → sonda `:625` | SIN-CABLEAR (valores 342.6/284.1/14.2 MPa hardcodeados) | tooltip sonda `:623-630`; colorbar estática `:603-620` |
| S3-11 | Botón `X/Y/Z` bajo ViewCube | `:588-591` | ninguno | — | SIN-CABLEAR | sin efecto |
| S3-12 | CTA `Configurar Optimización Topológica` | `:874-881` | `onAdvanceToSimp` | `currentScreen` | — | Screen4 |
| — | Telemetría `4.82s/1.15s/2.94s/0.73s`, residuos, `FS=1.47`, `cond(K)`, `ΣF` | `:338-353,367-407,431-472,710-738,823-846` | ninguno | — | DEMO (hardcodeado) | informativo |

### 2.4 Screen4 — Optimización SIMP (`Screen4TopologyOptimization.tsx`)

| # | Control | Archivo:línea | Handler | Estado | Backend | Resultado/error |
|---|---|---|---|---|---|---|
| S4-1 | Botón `Lanzar optimización (backend)` | `:236-242` | `handleRunOptimization` `:156-176` | `optBusy/jobId/optError/optResult` | **CABLEADO** `runOptimization({volume_fraction: targetVolumeFraction, max_iterations: maxIterations})`; sin bridge: `return` silencioso `:158` (conserva demo) | banner `:531-535` (`Optimizando… estado/progreso` vía `poll`); JSON real; `realCompliance/realMass` `:178-180` |
| S4-2 | Botón `Reiniciar SIMP` | `:243-252` | `setCurrentIter(1); setIsPlaying(true)` | `currentIter/isPlaying` | DEMO (no toca backend) | reanima demo |
| S4-3 | Slider `penalización p 1-5` | `:278-286` | `onUpdateSimpConfig({penaltyExponent})` | `simpConfig.penaltyExponent` (App) | — (se envía solo `volume_fraction/max_iterations` en S4-1; `p` **no** se envía) | label `:276`; cabecera `:222` |
| S4-4 | Slider `Vf 15-70%` | `:300-308` | `onUpdateSimpConfig({targetVolumeFraction})` | `targetVolumeFraction` | **CABLEADO** vía S4-1 | label `:296`; volumen demo `:523-526` |
| S4-5 | Slider `r_min 2-12 mm` | `:320-328` | `onUpdateSimpConfig({filterRadiusMm})` | `filterRadiusMm` | SIN-CABLEAR (no se envía) | label `:318`; cabecera `:227` |
| S4-6 | Select algoritmo `OC/MMA` | `:337-344` | `onUpdateSimpConfig({algorithm})` | `simpConfig.algorithm` | SIN-CABLEAR (no se envía) | — |
| S4-7 | Play/Pause + `±1 iter` + scrubber `1..maxIter` | `:386-427` | `setIsPlaying`, `setCurrentIter(±1 / parseInt)` (pausa al arrastrar `:422`) | `currentIter/isPlaying` | DEMO (`setInterval` 120 ms `:183-199`, tope `maxIterations`) | `Iter: x/y` `:412`; curvas/volumen/compliance derivadas por fórmula `:202-206` |
| S4-8 | Tabs vista `Densidad / Isosuperficie` | `:431-447` | `setViewMode` | `viewMode` → `wireframe={viewMode==='iso'}` `:460` | — (local; `iso` no filtra por `isoThreshold`, solo alambre) | resaltado |
| S4-9 | Slider `Corte isosuperficie 0.1-0.9` | `:508-516` | `setIsoThreshold` | `isoThreshold` → marca colorbar `:491-494` + label tab `:445` | DEMO (no filtra geometría) | — |
| S4-10 | `Cargar malla` | `:469-471` | `loadMeshPreview` (`getMeshPreview` `:58-79`) | `previewMesh/meshError` | **CABLEADO** | texto estado densidad `:466-468` |
| S4-11 | CTA `Reconstruir B-Rep NURBS & Exportar` | `:628-636` | `onAdvanceToBRep` | `currentScreen` | — | Screen5 |
| — | Curva convergencia SVG, `Ahorro -x%`, `+152%`, `ΔC 0.0004`, regiones frozen, overhang 45° | `:233-234,558-616,370-376,349-367` | ninguno | derivado de `currentIter` por fórmula (no del backend salvo `realCompliance/realMass`) | DEMO | — |

### 2.5 Screen5 — B-Rep & Export (`Screen5GenerativeBRepExport.tsx`)

Viewport es **SVG estático** (sólido titanio `:264-368`), no `MeshViewer`.

| # | Control | Archivo:línea | Handler | Estado | Backend | Resultado/error |
|---|---|---|---|---|---|---|
| S5-1 | Input `Ruta de exportación` | `:425-430` | `setExportPath` | `exportPath` (init `C:\Modelos\optimized.step`) | — (se usa en S5-2) | — |
| S5-2 | Botón `Exportar vía backend (exportStep)` | `:437-444` | `handleBackendExport` `:39-55` | `isExporting/exportStatus/exportError` | **CABLEADO** `backend.exportStep(exportPath)` | OK → `exportStatus` `:432`; error → `exportError` `:435` |
| S5-3 | Botón `Descargar STEP AP242` | `:445-452` | `handleDownload('STEP')` `:57-95` | `isExporting/downloadSuccess` | **DEMO/SINTÉTICO**: `Blob` con STEP falso (`dummyContent` `:66-81`) + `<a download>` `:83-91`; `setTimeout` 600 ms `:59` | banner éxito `:402-407`, auto-limpia 4 s `:93` |
| S5-4 | Botones `IGES/STL/glTF Exportar` | `:461-494` | `handleDownload('IGS'/'STL'/'GLB')` | idem | **DEMO**: mismo STEP sintético renombrado (ni siquiera formato IGS/STL/GLB real) | idem |
| S5-5 | Botón `Guardar Paquete (.zip)` | `:517-523` | `handleDownload('STEP')` (¡reutilizado!) | idem | **DEMO**: descarga un `.step`, no un `.zip` | idem |
| S5-6 | Toggles `Cebra / Curvatura / Isoparámetros UV` | `:229-255` | `setZebraView/CurvatureView/WireframeOn` | los tres `boolean` | — (local SVG) | overlays `:319-340`; `title` explica G1/G2 `:233` |
| S5-7 | `ViewCube` (sin `onViewChange`) | `:372-374` | solo `activeFace` interno | — | SIN-CABLEAR | no mueve nada (SVG estático) |
| S5-8 | Botón `Nuevo Ciclo de Diseño` | `:125-131` | `onRestartStudy` → `setCurrentScreen('modelo…')` | `currentScreen` | — | Screen1 |
| — | Pipeline 5 pasos, telemetría `0.038mm/1e-5/G1`, `FS=1.62`, `-64.9%` | `:148-212,500-515,377-389` | ninguno | — | DEMO (hardcodeado) | informativo |

### 2.6 Modales (resumen; detalle en §3)

| # | Control | Archivo:línea | Handler → backend | Resultado |
|---|---|---|---|---|
| M1-1 | Drop zone + `Explorar Archivo` (`<input type=file accept=.step,.stp>`) | `ImportStepModal.tsx:122-151` | `handleFileDrop` `:57` / `handleFileInput` `:67` → `setImportedCustomName/setSelectedPreset` (solo nombre, **no** sube bytes) | chip verde `:153-160` |
| M1-2 | Input `Ruta local STEP` | `:167-172` | `setStepPath` (init `fixtures\cono.step`) | se usa en `handleConfirm` |
| M1-3 | Lista 4 presets | `:192-225` | `setSelectedPreset` + limpia custom `:197-200` | resaltado |
| M1-4 | `Cargar Modelo STEP` / `Cancelar` / `X` | `:231-244,111-116` | `handleConfirm` `:75-98` → **`backend.importStep(effectivePath)`** (`custom ?? stepPath ?? preset` `:82`) | OK → `status` `:176` + `onModelSelected(base)` + `onClose`; error → `statusError` `:181`; spinner `Importando…` |
| M2-1..4 | Inputs `studyName/analysisType/material/loadMagnitudeN` + `Inicializar/Cancelar/X` | `CreateStudyModal.tsx:57-133` | `handleSubmit` `:23-32` → `onCreateStudy({...})` → App aplica material y navega; **sin** backend | cierra modal |
| M3-1 | `Entendido` / `X` | `HelpModal.tsx:109-115,21-26` | `onClose` | cierra; contenido estático (atajos §2.0 G1-G2, fórmulas SIMP, motores) |

---

## 3. MODALES

### 3.1 `ImportStepModal` (`Modals/ImportStepModal.tsx:5-15`)

- **Qué lo abre**: `Header → Importar STEP` (`Header.tsx:79`, `App.tsx:162`). Estado `isImportModalOpen` (`App.tsx:58,231`).
- **Props in**: `isOpen: boolean`, `onClose: () => void`, `onModelSelected: (filename, details?) => void` (`:5-9`). Si `!isOpen` retorna `null` (`:24`).
- **Props out / retorno**: `onModelSelected(base)` con solo el basename (`:89-91`) → `App.handleModelSelected` (`App.tsx:139-143`): `setActiveFilename` + `setCurrentScreen('modelo…')` + `refreshSnapshot()`. Luego `onClose()` (`:92`).
- **Backend que toca**: **`backend.importStep(effectivePath)`** (`:84`). Lógica de ruta (`:80-82`): `importedCustomName ?? (stepPath.trim() || selectedPreset)` — ojo: la línea 80 calcula `path` con precedencia de `??` confusa y `void path` (`:83`); la efectiva es la línea 82. Un drop/input solo aporta el **nombre**, no una ruta real ni bytes → cablear subida real aquí si se necesita.
- **Estados/errores**: `isImporting` (deshabilita botón, `Importando…` `:243`), `status` verde (`:175`), `statusError` rojo (`:180`).
- **Para editar**: presets (`:26-55`, con `size/elements` hardcodeados), `stepPath` inicial (`:19`), `accept=".step,.stp"` (`:146`).

### 3.2 `CreateStudyModal` (`Modals/CreateStudyModal.tsx:5-15`)

- **Qué lo abre**: `Header → Crear Estudio` (`Header.tsx:89`, `App.tsx:164`). Estado `isCreateStudyModalOpen` (`App.tsx:60,239`).
- **Props in**: `isOpen`, `onClose`, `onCreateStudy: (config: any) => void`. `if (!isOpen) return null` (`:21`).
- **Props out**: `onCreateStudy({studyName, analysisType, selectedMaterialId, loadMagnitudeN})` (`:25-30`) → `App.handleCreateStudy` (`App.tsx:145-151`): si hay `selectedMaterialId` busca en `materials` y llama `handleSelectMaterial` (= `setMaterial` backend), luego va a Screen1. `studyName/analysisType/loadMagnitudeN` **se ignoran** (SIN-CABLEAR).
- **Backend que toca**: ninguno directo; indirecto `setMaterial` vía App. Opciones material desde `MATERIALS` (no de `App.materials`) (`:90`).
- **Para editar**: defaults `studyName='ESTRUCTURAL_AERO_V2_STATIC'` (`:16`), `analysisType='linear_static'` (`:17`), opciones análisis (`:75-77`), `step=100` carga (`:106`).

### 3.3 `HelpModal` (`Modals/HelpModal.tsx:3-11`)

- **Qué lo abre**: icono `?` (`Header.tsx:185`, `App.tsx:163`) o teclas `?`/`h` (`App.tsx:117`). Estado `isHelpModalOpen` (`App.tsx:59,237`).
- **Props**: `isOpen/onClose`; sin backend. Secciones: atajos viewport (`:32-63` — ⚠️ desactualizados: dicen `Shift+Clic` orbitar y `R` fit, pero los perfiles reales están en `lib/navigation.ts`), fórmulas SIMP (`:66-83`), motores (`:86-105`).

---

## 4. VIEWER 3D

### 4.1 `MeshViewer` — props (`MeshViewer.tsx:28-41`, uso `Screen1:545`, `Screen3:567`, `Screen5:—no lo usa—`, `Screen4:460`)

| Prop | Tipo / default | Efecto y dónde cablearlo |
|---|---|---|
| `mesh` | `PreviewMesh\|null` (`:6-13`: `vertices[]`, `indices[]`, `normals?`, `bbox?`, `num_vertices?`, `num_triangles?`) | Reconstruye `BufferGeometry` + `computeVertexNormals` si faltan (`:409-418`); auto-fit (`:464-473`). `null` → placeholder `emptyMessage` (`:517-523`) |
| `wireframe` | `boolean=false` | `material.wireframe` en caliente (`:478-480`) |
| `color` | `string='#7bd0ff'` | `material.color` si no hay `values` (`:481-483`); Screen1 usa `#8fa3b8`, Screen3 `#38bdf8`, Screen4 `#3b82f6` |
| `height` | `number=460` | alto contenedor + `renderer.setSize` (`:188,342`); Screen3/4 usan 320 dentro de viewport 620 |
| `emptyMessage` | `string` | texto placeholder + hint `getMeshPreview() sin mesh` (`:521`) |
| `values` | `number[]\|null` | colormap por vértice si `length === vertCount` (`:420`); si no coincide se ignora silenciosamente |
| `colorMin/colorMax` | `number\|undefined` | rango fijo; si faltan se auto-calcula min/max (`:421-432`); leyenda usa `slice(0,200000)` (`:511-512`) |
| `colorbarLabel` | `string\|undefined` | etiqueta leyenda (`:531`); Screen3: `Von Mises (MPa)` / `Desplazamiento \|u\| (mm)`, Screen4: `Densidad SIMP ρ…` |
| `clip` | `boolean=false` | plano X en centro bbox (`:486-506`, normal `(-1,0,0)`); `localClippingEnabled=true` (`:189`) |
| `profile` | `NavProfileName\|string='autocad'` | `applyProfileButtons` (`:165-179`); desconocido → autocad (`:113-116`) |
| `onSelect` | `(sel: MeshSelection\|null) => void` (`:22-26`: `point`, `faceIndex`, `triangle`) | raycast en clic-izq sin drag `<5px` (`:285-293,239-269`); esfera amarilla + `selInfo` (`:267`); Screen1 lo muestra (`Screen1:545`) |

### 4.2 Ref imperativo (`MeshViewer.tsx:17-20,162`)

```tsx
const viewerRef = useRef<MeshViewerHandle>(null);           // Screen1:55, Screen3:58, Screen4:52
<MeshViewer ref={viewerRef} … />
viewerRef.current?.setView('front'|'back'|'left'|'right'|'top'|'bottom'|'iso'); // applyView :118-135 (Z-up como camera.py)
viewerRef.current?.reset();                                  // frameByBbox :137-150
```

`mapCubeFace(face)` (`:61-72`): `FRONT/BACK/LEFT/RIGHT/TOP/BOTTOM/ISO` → dirección; `FIT/PERSP/RESET` → `'reset'`; resto → `'iso'`. Usado en `Screen1:143`, `Screen3:161`, `Screen4:150`.

### 4.3 Perfiles de navegación (`lib/navigation.ts`, espejo de `core/navigation.py`)

| Perfil (`NAV_PROFILES` `:25-71`) | medio | shift+medio | derecho | tecla fit | Uso |
|---|---|---|---|---|---|
| `autocad` (default `DEFAULT_NAV_PROFILE` `:76`) | pan | orbit (temporal `:272-283`) | menu | `n` + `r`=rotate 30° Z (`rotateStep` `:152`, `MeshViewer.tsx:308-310`) | `Screen1` select `:483`; `MeshViewer profile=` |
| `onshape` | pan | pan | orbit | `f` (`:311`); `shift+←` rotate | idem |
| `fusion360` | pan | orbit | menu | `f` | idem |
| `blender` | orbit | pan | menu | `.` (`:314`) | idem |

Reglas globales: izq siempre `select` (`left:'select'`); doble-clic = fit (`:295`); menú contextual suprimido salvo `right==='menu'` (`:296-300`); teclas fit ignoradas en inputs y sin hover/foco (`:302-305`, `tabIndex=0` `:190`). Persistencia `localStorage 'topoopt.nav'` (`NAV_STORAGE_KEY` `:75`, `readStoredNavProfile` `:82`). Backend espejo: `getNavProfiles/setNavProfile` (mocks en `bridge.ts:34-43`).

### 4.4 Cómo agregar un modo de vista o campo nuevo

**Nuevo modo de vista** (p. ej. `BOTTOM` ya existe en tipos pero ViewCube no lo ofrece):
1. `ViewCube.tsx:34-91` — añade `<polygon onClick={() => handleFaceClick('BOTTOM')}>` (copia un polígono existente).
2. `MeshViewer.tsx:61-72` — `mapCubeFace` ya mapea `'BOTTOM'`; si fuera una etiqueta nueva, añade su `if`.
3. Pantalla — el `handleViewChange` existente (`Screen1:143`…) funciona sin cambios; opcional añade botón que llame `viewerRef.current?.setView('bottom')`.

**Nuevo campo escalar** (p. ej. temperatura):
1. Backend `api.py:getSurfaceMesh` debe aceptar `field='temperature'` (hoy Screen3 pide `vonmises/displacement` `Screen3:153-159`, Screen4 `density` `Screen4:146`).
2. En la pantalla, añade al tipo (`Screen3:43`: `'vonmises'|'disp'|'sigma1'|'sed'`), botón tab (copia `Screen3:503-512`), y rama en el `useEffect` (`Screen3:153-159`) que llame `loadSurfaceField('temperature')`.
3. Pasa `values={fieldValues} colorMin={fieldMin} colorMax={fieldMax} colorbarLabel="Temperatura (°C)"` al `MeshViewer` (patrón `Screen3:567-570`). El colormap azul→rojo (`MeshViewer.tsx:44-58`) y la leyenda (`:529-541`) son automáticos.

---

## 5. BACKEND DISPONIBLE — las 16 funciones de `lib/bridge.ts` (`bridge.ts:48-71`)

Patrón común (`bridge.ts:15-26`): si no hay `window.pywebview.api`, responde **mock** (`mock()` `:28-46`) con `{ok:true,…}`; si hay bridge, reenvía y ante excepción devuelve `{ok:false, error}`. Firmas literales (no inventadas):

| # | Función (`bridge.ts:línea`) | Firma TS | Qué hace / ejemplo |
|---|---|---|---|
| 1 | `hasBridge` `:49` | `() => boolean` | `if (!backend.hasBridge()) return; // modo demo` (usado `Screen3:169`, `Screen4:158`) |
| 2 | `getSnapshot` `:50` | `() => Promise<{ok} & {snapshot: unknown}>` | `const r = await backend.getSnapshot(); if (r.ok && r.snapshot) setSnapshot(r.snapshot)` (`App.tsx:64`). Mock: `{model_name:'demo.step', has_mesh:false, has_result:false}` (`:31`) |
| 3 | `getMaterials` `:51` | `() => Promise<{materials: unknown[]; names: string[]}>` | `const r = await backend.getMaterials(); if (r.ok && r.materials?.length) …` (`App.tsx:80-88`). Mock: `{materials:[], names:['steel','aluminum','titanium']}` (`:32`) |
| 4 | `setMaterial` `:52` | `(name: string) => Promise<…>` | `await backend.setMaterial(m.name)` (`App.tsx:133`) — ojo: envía `m.name` largo (`Aluminio 7075…`), no el `id` |
| 5 | `validateProblem` `:53` | `(problemJson: string) => Promise<…>` | ⚠️ **Sin llamadas en la UI** — para cablear: `await backend.validateProblem(JSON.stringify({…}))` |
| 6 | `importStep` `:54` | `(path: string) => Promise<…>` | `await backend.importStep(effectivePath)` (`ImportStepModal.tsx:84`) |
| 7 | `generateMesh` `:55-56` | `(params = {}) => Promise<…>` — envía `JSON.stringify(params)` | `await backend.generateMesh({target_element_size: hMax})` (`Screen1:122`); `({target_element_size: 6.0})` (`Screen2:43`) |
| 8 | `setBoundaries` `:57-58` | `(params: object) => Promise<…>` — envía `JSON.stringify(params)` | `await backend.setBoundaries({bottom_axis:2, load_dir:[0,0,1], magnitude: loadMagnitude})` (`Screen2:51-55`) |
| 9 | `runFea` `:59` | `(params = {}) => Promise<{jobId: string}>` — envía `JSON.stringify(params)` | `const r = await backend.runFea({backend: feaBackend}); setJobId(r.jobId)` (`Screen3:177-187`) |
| 10 | `runOptimization` `:60-61` | `(params = {}) => Promise<{jobId: string}>` — envía `JSON.stringify(params)` | `await backend.runOptimization({volume_fraction, max_iterations})` (`Screen4:161-164`) |
| 11 | `pollJob` `:62` | `(jobId: string) => Promise<…>` | Vía `useJobPoll(jobId)` (`jobs.ts:26`): `{state, progress, result, error}` cada 2 s (`jobs.ts:58`); mock `{state:'done', progress:1}` (`:33`) |
| 12 | `getMeshPreview` `:63` | `() => Promise<{mesh: unknown}>` | `const r = await backend.getMeshPreview(); setPreviewMesh(r.mesh ?? null)` (patrón `Screen1:60-84`, `Screen3:65`, `Screen4:58`) |
| 13 | `exportStep` `:64` | `(path: string) => Promise<…>` | `await backend.exportStep(exportPath)` (`Screen5:44`) |
| 14 | `getNavProfiles` `:65-69` | `() => Promise<{profiles: {name, display_name}[]; current: string}>` | `const r = await backend.getNavProfiles(); setNavProfile(r.current)` (`Screen1:94`); mock 4 perfiles + `current:'autocad'` (`:34-42`) |
| 15 | `setNavProfile` `:70` | `(name: string) => Promise<…>` | `void backend.setNavProfile(p).catch(()=>undefined)` (`Screen1:114`); mock `{ok:true}` (`:43`) |

> **Nota histórica (ya resuelto 2026-09-09)**: `getSurfaceMesh` YA está en `bridge.ts`; antes Screen3 (`:108-110`) y Screen4 (`:100-102`) la llaman vía `window.pywebview?.api.getSurfaceMesh(JSON.stringify({field}))` con `unwrap()` de `{positions, indices, values, min, max}` (`Screen3:94-103`). Si la añades a `bridge.ts`, sigue el patrón `call('getSurfaceMesh', JSON.stringify(params))`.

---

## 6. GUÍA DE EDICIÓN

### 6.1 Convenciones

- **Tailwind inline**: fondo `#0f1117`, paneles `#181b24`/`#1f2430`, bordes `#2e3646`, acento `#0ea5e9`/`#7bd0ff`, éxito `#10b981`, aviso `#ffb95f`/`#f59e0b`, error `#ef4444`/`#fca5a5`. Botón primario: `bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751]`; secundario: `bg-[#1f2430] hover:bg-[#272a33] border-[#2e3646]`; CTA grande con `Play`: patrón `Screen1:724-731`.
- **Iconos**: `lucide-react` (`Header.tsx:3-15`, cada Screen) + `material-symbols-outlined` (requiere fuente global). Números monoespaciados: `font-mono` / `font-label-sm`.
- **Formatos**: `ScreenId` kebab (`types.ts:1`); `FeaBackend` `'numpy'|'kratos'` (`types.ts:8`); unidades mm/kg/N/GPa; `toFixed(1-2)`, `toLocaleString()` en Footer; errores como `{ok, error}` y texto `… devolvió ok=false`; estado triplete `data/loading/error` (patrón `previewMesh/meshLoading/meshError`).
- **Teclado**: todo atajo global debe ignorar `INPUT/SELECT/TEXTAREA` (`App.tsx:103`, `MeshViewer.tsx:303`); los del viewer además exigen hover/foco (`MeshViewer.tsx:305`, `tabIndex=0` `:190`).

### 6.2 Cómo agregar un control nuevo cableado (pasos 1-2-3 con ejemplo)

Ejemplo: input `Tolerancia CG (1e-6…1e-12)` en Screen3 que llegue a `runFea`.

1. **Estado + control** (copia `Screen2:376-382`):
```tsx
const [cgTol, setCgTol] = useState<number>(1e-8);   // junto a Screen3:40-56
<label>Magnitud… <input type="number" value={cgTol}
  onChange={(e) => setCgTol(parseFloat(e.target.value) || 1e-8)}
  className="w-24 bg-[#0b0e17] border border-[#2e3646] rounded px-1.5 py-0.5 text-[#f1f5f9] text-[10px]" /></label>
```
2. **Enviarlo** en el handler existente (`Screen3:167-193`):
```tsx
const r = await backend.runFea({ backend: feaBackend, cg_tolerance: cgTol });
```
3. **Mostrar resultado/error** en el banner ya existente (`Screen3:419-423`, texto `Screen3:195-203`): sin cambios — `poll.error/feaError` aparecen solos. Si el backend no lo soporta aún, añade el parámetro en `api.py:runFea` y reexpón como en §6.3.

### 6.3 Cómo agregar una llamada backend nueva (`api.py` ya expone más métodos)
api.py expone metodos ya envueltos en bridge.ts (ej. getSurfaceMesh, 2026-09-09). Patron para agregar otro:
1. En `lib/bridge.ts` añade (misma forma que `getSurfaceMesh`):
```ts
getSurfaceMesh: (params = {}) =>
  call('getSurfaceMesh', JSON.stringify(params) as never),
```
2. En la pantalla sustituye el acceso directo (`Screen3:108-110`, `Screen4:100-102`):
```ts
const r = await backend.getSurfaceMesh({ field: 'vonmises' });
```
3. Reutiliza `unwrap()` (`Screen3:94-103`) y el triplete `fieldValues/fieldLoading/fieldError` (`Screen3:53-57`). Para un método `api.py` totalmente nuevo, añade `def nuevo(...)` en `api.py` + una línea `call('nuevo', …)` en `bridge.ts` + `mock` en `base` (`bridge.ts:30-44`) para no romper `vite dev`.

### 6.4 Errores comunes

| Error | Dónde | Cómo evitarlo |
|---|---|---|
| Inputs que roban teclas (atajos `1-5/?/h`, fit `n/f/./r`) | `App.tsx:102-105`, `MeshViewer.tsx:302-305` | Todo `onKeyDown` global debe empezar con el guarda `['INPUT','SELECT','TEXTAREA'].includes(tag)`; viewer además pide hover/foco |
| Mocks sin pywebview enmascaran fallos (`{ok:true}` con `mesh undefined`, `poll done`) | `bridge.ts:28-46`, `Screen1:71-74`, `Screen3:169`, `Screen4:158` | Usa `backend.hasBridge()` para etiquetar `Demo (sin pywebview)` (`Screen3:415`) y no confundir demo con real |
| Props que App no pasa a Header (`activeFilename/backend/onToggleBackend`) | `App.tsx:158-165` vs `Header.tsx:17-26` | Pasar `activeFilename={activeFilename} backend={activeBackend} onToggleBackend={() => setActiveBackend(b => b==='numpy'?'kratos':'numpy')}` o quitar el toggle |
| `ViewCube` sin `onViewChange` no mueve nada | `Screen2:219`, `Screen5:373` | Pasar `onViewChange={handleViewChange}` + `viewerRef` como en `Screen1:498,143` (en Screen2/5 además el viewport es SVG: o monta `MeshViewer` o documenta que es ilustrativo) |
| `values.length !== vertCount` silencia el colormap | `MeshViewer.tsx:420`, `Screen3:568` | Tras `setPreviewMesh` con `getSurfaceMesh`, verifica `values.length === pos.length/3`; hoy `sigma1/sed` ponen `null` a propósito (`Screen3:157`) |
| Enviar `m.name` largo a `setMaterial` en vez de `id` | `App.tsx:133`, `data/materials.ts:6` | Confirmar qué acepta `api.py:setMaterial`; si espera `steel/aluminum…` (mock `bridge.ts:32`), mapear `id→nombre backend` |
| Sliders que no llegan al backend (`p`, `r_min`, `algorithm`, `meshAlgorithm`, `h_min`, `shrink`) | `Screen4:278-344`, `Screen2:125-189`, `Screen1:304` | O inclúyelos en el `params` del `run*/generateMesh` o marca el slider `visual/demo` en la etiqueta |
| `void` + `catch(()=>undefined)` tragan errores | `Screen1:114`, `App.tsx:143,148` | Al menos `console.warn` o banner; hoy el fallo de `setNavProfile` es invisible |
| `details?` de `onModelSelected` nunca se pasa | `ImportStepModal.tsx:8,91` | Si el backend devuelve metadatos, pásalos y úsalos en Screen1 en vez de `12 Caras…` hardcodeado (`Screen1:213`) |

---

## 7. BACKLOG — MOCK / DEMO / SIN-CABLEAR detectado

| ID | Qué | Archivo:línea | Tipo | Para cablearlo |
|---|---|---|---|---|
| B1 (RESUELTO 2026-09-09) | Header esperaba props que App no pasaba → chip motor y nombre de archivo rotos | `Header.tsx:17-26` vs `App.tsx:158-165` | SIN-CABLEAR (bug) | Pasar las 3 props desde App (ver §6.4) |
| B2 | Botón Header `Exportar STEP` solo navega a Screen5 | `Header.tsx:151-158` | SIN-CABLEAR | Llamar `backend.exportStep` o eliminar duplicado con G9 |
| B3 | Footer `XYZ 124.5/45.2/0.0`, `184920/38412`, `60 FPS`, unidades | `Footer.tsx:11-13,20-40` | DEMO | Cursor desde `MeshViewer onSelect`; conteos ya llegan por `snapshot` (`App.tsx:228`) |
| B4 | Sidebar badges (`Sólido`, `3 Cargas`, `p=3.0`…) y `Float64/CG`, `1e-6` | `Sidebar.tsx:17-47,86-91` | DEMO | Derivar de `snapshot/simpConfig` reales |
| B5 | Screen1 árbol (planos, sólido, encastre, tracción, SAFE, VOID) sin handlers | `Screen1:184-277` | SIN-CABLEAR | Conectar a `setBoundaries`/visibilidad o marcar `próximamente` |
| B6 | Screen1 `h_min` no se envía; `h_max` sí | `Screen1:122,304-312` | SIN-CABLEAR (parcial) | `generateMesh({h_min, h_max})` + backend |
| B7 | Screen1 botones Medición / Aislar / `3d_rotation` / `pan_tool` | `Screen1:454-479,508-521` | SIN-CABLEAR | Implementar o quitar (dejar solo clip/wireframe que sí funcionan) |
| B8 | Screen2 viewport = SVG estático; `elementShrink` no deforma; `meshAlgorithm` no se envía; tab `mesh/bcs` muerto | `Screen2:234-329,181-189,125-133,31-36` | DEMO + código muerto | Montar `MeshViewer` + pasar algoritmo a `generateMesh`; quitar `activeTab` |
| B9 | Screen2 `ViewCube` sin `onViewChange` | `Screen2:218-220` | SIN-CABLEAR | Patrón §6.4 |
| B10 | Screen3 telemetría `4.82/1.15/2.94/0.73 s`, residuos SVG, `342.6 MPa/FS 1.47/0.412/14.82 J`, colorbar `350/284/210…`, hotspots, `cond(K)`, `ΣF`, `LC1` | `Screen3:338-353,367-407,431-472,594-630,756-846,710-738` | DEMO | Sustituir por `feaResult` (`:424-428`) cuando el backend lo devuelva |
| B11 | Screen3 tabs `σ₁` y `SED` limpian el campo (`setFieldValues(null)`) | `Screen3:157,503-522` | SIN-CABLEAR | Backend `getSurfaceMesh({field:'sigma1'/'sed'})` + rama como `vonmises` |
| B12 | Screen3 botones vectores/iso/captura, `X/Y/Z`, escala `skewDeg/deformY` calculada sin aplicar | `Screen3:536-554,588-591,238-239` | SIN-CABLEAR | Aplicar deformación o eliminar variables |
| B13 | Screen3 `handleSolve` sin bridge resetea escala en silencio | `Screen3:169-174` | DEMO silenciosa | Avisar `Demo (sin pywebview)` en `feaStatusText` |
| B14 | Screen4 física derivada por fórmula (`Vf`, compliance `48.2-32.6√`, masa `3.42·Vf`, `-x%`, `+152%`, curvas SVG, `ΔC 0.0004`) con `currentIter` init **42** | `Screen4:36,202-206,523-615,233-234,558-597` | DEMO | Gobernar por `poll.progress/optResult` (`realCompliance/realMass` `:178-180` ya leídos pero poco visibles) |
| B15 | Screen4 `p/r_min/algorithm` no se envían a `runOptimization` (solo `volume_fraction/max_iterations`); `Reiniciar SIMP` y playback son demo; `isoThreshold` no filtra; sin bridge `return` silencioso | `Screen4:156-176,278-344,243-252,183-199,508-516` | SIN-CABLEAR + DEMO | Ampliar params + cablear `Reiniciar` a backend/cancelar job |
| B16 | Screen5 viewports y pipeline硬: SVG titanio, 5 pasos, `0.038mm/1e-5/G1`, `FS=1.62`, `-64.9%`, `ViewCube` sin handler | `Screen5:264-374,148-212,500-515,377-389` | DEMO | `getSurfaceMesh`/preview real del sólido reconstruido; `onViewChange` |
| B17 | Screen5 descargas `IGS/STL/GLB/ZIP` = STEP sintético (`dummyContent` + `setTimeout` 600 ms); `.zip` descarga `.step` | `Screen5:57-95,461-523` | DEMO/SINTÉTICO | `exportStep` por formato en backend o marcar `solo STEP demo` |
| B18 | `CreateStudyModal` ignora `studyName/analysisType/loadMagnitudeN`; `validateProblem` sin llamadas | `CreateStudyModal.tsx:25-30`, `App.tsx:145-151`, `bridge.ts:53` | SIN-CABLEAR | `validateProblem(JSON.stringify(...))` + `setBoundaries({magnitude: loadMagnitudeN})` |
| B19 | `ImportStepModal` drop solo guarda el nombre (sin bytes/ruta real); `path` línea 80 con precedencia confusa + `void path` | `ImportStepModal.tsx:57-73,80-83` | SIN-CABLEAR (parcial) | Diálogo nativo pywebview o subida real; limpiar líneas 80-83 |
| B20 | `getSurfaceMesh` existe en `api.py:249` pero no en `bridge.ts`; pantallas la llaman directo a `window.pywebview.api` | `Screen3:108-110`, `Screen4:100-102`, `bridge.ts:48-71` | SIN-CABLEAR (en bridge) | Envolverla en `bridge.ts` (§6.3) |
| B21 | `densityMin/Max` con `slice(0,200000)` y `fieldMin/Max` pueden truncar leyenda en mallas grandes | `MeshViewer.tsx:511-512` | DEMO (aprox) | Usar `min/max` del backend (`r.min/r.max`) |
| B22 | `HelpModal` atajos desactualizados (`Shift+Clic`, `R`) vs perfiles reales (`n/f/./dblclick`) | `HelpModal.tsx:37-63` vs `lib/navigation.ts:25-71` | DEMO (docs) | Regenerar desde `NAV_PROFILES` + `fitKeyFor` |
| B23 | `SimpConfig` App init sin `currentIteration/convergencePercent/isRunning/activeCells/…` que `types.ts:57-72` declara | `App.tsx:49-56` vs `types.ts:57-72` | SIN-CABLEAR (tipos) | Inicializar completo o marcar opcionales en `types.ts` |
| B24 | `snapshotCounts` inventa `38412/184920` si falta un conteo | `App.tsx:30-38` | DEMO | Propagar `null` y mostrar `—` en Footer |

---

*Fin de UI_MAP.md — 7 secciones. Para terminar cada control: busca su ID (G#/S#/M#/B#), abre el `archivo:línea`, aplica el patrón de §6.2/§6.3 y mueve el ítem de §7 a CABLEADO.*
