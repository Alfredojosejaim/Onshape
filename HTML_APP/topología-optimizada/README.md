# Topología Optimizada

Aplicación de escritorio para optimización topológica estructural (SIMP) y
análisis por elementos finitos, con viewport 3D interactivo.

Pipeline: importación B-Rep (STEP/OCCT) → mallado volumétrico Tet4 (Gmsh) →
FEA → SIMP → reconstrucción B-Rep → exportación STEP.

Shell nativo: **pywebview (WebView2)**, sin navegador externo. El núcleo
científico corre en un proceso aparte (`backend/server.py`) porque las DLL
nativas (VTK/Qt/OCC) corrompen el heap si comparten proceso con WebView2.

## Arranque (Windows)

```
INICIAR_APP.bat
```

Comprueba dependencias (`backend/check_env.py`), verifica `dist/index.html` y
abre la ventana nativa. Para desarrollo con recarga en caliente:

```
npm run dev              # terminal 1 — vite en :3000
INICIAR_APP.bat --dev    # terminal 2 — ventana nativa apuntando a :3000
```

## Requisitos

**Python 3.10+** con `backend/requirements.txt`:

```
python -m pip install -r backend\requirements.txt
```

Obligatorios: `numpy`, `scipy`, `pywebview`, `vtk`.
Para importar STEP y mallar: `cadquery`, `gmsh`.
`PySide6` es opcional: solo la UI Qt legacy (`desktop/app.py`,
`desktop/ui_legacy`) y sus tests lo usan; la ventana pywebview no.
Kratos (`KratosMultiphysics` + `StructuralMechanics` + `Optimization`) es
opcional: sin él, el flujo local funciona y el verificado-Kratos reporta
`kratos_no_disponible`.

**Node.js LTS 20+** para construir la UI:

```
npm install
npm run build        # genera dist/, que consume app_desktop.py
```

## Scripts

| Comando | Qué hace |
|---|---|
| `npm run dev` | Vite en `http://localhost:3000` |
| `npm run build` | Construye `dist/` |
| `npm run lint` | `tsc --noEmit` |
| `npm run clean` | Borra `dist/` |
| `pytest backend/tests` | Suite del backend |

## Estructura

```
src/                 UI React + Tailwind; viewport three.js (CadViewport.tsx)
  lib/bridge.ts      puente a window.pywebview.api.*
backend/
  app_desktop.py     host pywebview + whitelist de métodos
  server.py          proceso del núcleo (HTTP local, puerto aleatorio)
  api.py             fachada de la aplicación
  core/              solver, mallado, condiciones, reconstrucción
  vendored/simp.py   CONGELADO — ver AGENTS.md
```

## Reglas de trabajo

Ver `AGENTS.md` (vendored congelado, confirm-gate, regla de resultados UI:
sin estudio real → estado vacío, nunca cifras por defecto) y `plan.md`.
