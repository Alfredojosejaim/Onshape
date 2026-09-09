# Experimento HTML standalone (pywebview + core vendorizado)

Sin branch, sin tocar `Topologia_Optimizada/`. El experimento es una app
independiente en `Web_App/` que **copia** el core necesario y lo sirve con
interfaz HTML nativa.

## Arquitectura

```
Web_App/
  html/                  # UI Vite+React (mock -> cableando a bridge.ts)
  html/src/lib/bridge.ts # window.pywebview.api con fallback mock en dev
  app_desktop.py         # host pywebview (WebView2 nativo, offline)
  api.py                 # JS API: materiales, STEP, malla, FEA/SIMP (jobs), snapshot
  core_vendor/           # COPIA de core/, services/, adapters/, desktop/pipeline/
  requirements-experiment.txt  # solo pywebview (el resto ya esta en el .venv)
  INICIAR_APP_HTML.bat   # iniciador (1-python, 2-deps, 3-dist/dev, lanza)
  app_hybrid.py / bridge_core.py  # fase 2 (QWebEngine+VTK nativo), referencia
```

Decisión de framework (3 agentes): **pywebview** — Python en proceso,
sin sidecar, sin HTTP, sin reescribir solvers. Tauri/Electron exigirían
congelar Kratos/VTK/gmsh en un sidecar (2-4 semanas de riesgo) para el
mismo resultado.

## Origen de core_vendor/ (trazabilidad)

Copia robocopy desde `../Topologia_Optimizada` (40 archivos):
`core/*` (topo_problem, topopt, fea, meshing, materials, study, document,
features, conditions, commands, generative*, cae/optimization_studies,
cad_*, boundary, selection, thermal, kratos_*), `services/cad_service.py`
(+study_service inofensivo), `adapters/cad/*`,
`desktop/__init__.py` + `desktop/pipeline/controller.py`.
Excluidos: `desktop/ui/*`, `desktop/viewport/*`, `desktop/app.py`,
tests, docs, ECC. Verificado: `PipelineController()` instancia sin
QApplication y `material_names()` responde.

Si el core evoluciona, re-copiar con el mismo robocopy (ver historial del
chat) o migrar a `pip install -e` / submódulo.

## Contrato UI<->Python (pywebview, todo JSON)

`getSnapshot, getMaterials, setMaterial, validateProblem, importStep,
generateMesh, setBoundaries, runFea/runOptimization -> {jobId},
pollJob, getMeshPreview (teselado diezmado p/ three.js), exportStep`.
Progreso: jobs en ThreadPoolExecutor + `pollJob`. 3D fase 1: three.js con
malla serializada; VTK nativo queda para fase 2 (ver app_hybrid.py).

## Cómo corre

```powershell
cd Web_App
..\Topologia_Optimizada\.venv\Scripts\python.exe -m pip install -r requirements-experiment.txt
..\Topologia_Optimizada\.venv\Scripts\python.exe -m pytest tests/ -v   # 6 passed
INICIAR_APP_HTML.bat            # dist (hace npm run build si falta)
INICIAR_APP_HTML.bat --dev      # vite :3000 (corre `npm run dev` en html/)
```

Verificado: pasos 1-3 OK, ventana WebView2 abre, bridge `pywebview` inyectado,
`Api().getMaterials()` -> steel/aluminum/titanium contra core vendorizado.

## Migración del ecosistema (origen: solo copias, original intacto)

| Copiado a Web_App/ | Desde Topologia_Optimizada/ | Nota |
|---|---|---|
| `core_vendor/` (40 .py) | `core/`, `services/`, `adapters/`, `desktop/pipeline/` | diff 1:1, sin `ui`/`viewport`/`app.py` |
| `fixtures/cono.step`, `prueba.step` | raíz | `cono.step` es el fixture canónico de sus tests |
| `conftest.py` | raíz | registro DLL Kratos en Windows |
| `requirements-experiment.txt` pines | `requirements.txt` | + pywebview + pytest |
| `pyproject.toml` (pytest) | adaptado de su `pyproject.toml` | `testpaths=tests`, marker `slow` |
| `tests/test_api.py` (6 tests) | propios | import+malla+BC+preview+materiales+snapshot |

Hallazgo real de migración: `prueba.step` con `target_element_size=5.0`
dispara el guard `FaceCorrespondenceError` del core (área CAD vs Gmsh
difiere 26% > 15%) — comportamiento propio del core, no bug migrado;
con `cono.step` todo pasa. `test_run_fea_job` marcado `slow` (minutos).

## Visor 3D (three.js, sin navegador)

`MeshViewer.tsx` + `api.getSurfaceMesh({field})` (superficie desde
`face_surface_elements`, indices = nodos FEA): colormap von Mises /
desplazamiento / densidad SIMP con leyenda, clip plane X, ViewCube
sincronizado (ref `setView/reset`). Suite 7 passed + Kratos/SIMP/FEA
verificados E2E. Smoke en ventana nativa: 13 funciones expuestas.
