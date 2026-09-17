# Sesión 2026-09-17 — Generativa: threshold muerto, poll opaco y muerte del backend

**Proyecto:** `HTML_APP/topología-optimizada`
**Fecha:** 17-sep-2026
**Alcance:** `backend/api.py`, `backend/app_desktop.py`,
`backend/core/generative_engine.py`, `src/App.tsx`,
`src/components/RightPanel.tsx`, `src/lib/jobs.ts`, `src/types.ts`.
**Relacionado:** `sesion-2026-09-16-generativa-envelope-bspline-error.md`
(la hipótesis de volfrac infactible de su §4 quedó **refutada**: el guard de
`vendored/simp.py` solo dispara con `volfrac < rho_min ≈ 0.001`).

Contexto previo (commit `579cb5a`, ya integrado): `max_hole_edges` ("auto" =
mediana de loops × 4.0, mín 12) cableado `api → engine → ReconstructionPipeline`
+ fix del filler inyectado; skin del envelope excluye elementos con nodos de
carga/soporte (`void_skin_bc_excluded`); `_solve_linear` captura excepciones de
scipy y falla ruidoso ante NaN/Inf (`_check_finite_solution`).

---

## 1. "Sin geometría registrable: Reconstructed solid is not valid" — CAUSA + PALANCAS

Con defaults (volfrac 0.3, 50 iter, p=3, sin Heaviside, envelope) el umbral de
isosuperficie estaba **hardcodeado en 0.5** (`_reconstruct`), sin vía desde UI.
SIMP estándar deja mucha densidad en intermedios ≤ 0.5 → la isosuperficie 0.5
encierra mucho menos del 30% → fragmentos abiertos → el cosido falla. En
envelope se agrava (el 30% se diluye en caja + padding 10% y el skin vacía el
borde). Segunda brecha: el aviso decía "(mira compliance/volumen)" pero el
fallo no adjuntaba **ningún** número.

**Fix (defaults intactos):**
- `threshold` parametrizado `api → run_generative_design → _reconstruct →
  pipe.run` (default 0.5 histórico, validado en (0,1)); el umbral usado queda
  en metadata (`reconstruction_threshold`).
- Ante fallo BREP, `brep_error` trae números: % elementos sobre el umbral,
  dens min/media/max, volfrac objetivo, compliance final, más claves
  `brep_fail_*` en metadata (solo diagnóstico).
- UI: `SimpParameters` suma `reconThreshold` (0.5) y `holeCap: 'all'|'auto'`
  (`'all'` = histórico); `runGenerativeDesign` los envía; panel "Geometría
  limpia" con controles Umbral sólido ρ (0.05–0.95) y Agujeros grandes.
  Sin esto, el backend de los turnos previos era inalcanzable (mismo patrón
  de cableado muerto del bug #1).

## 2. "pollJob falló en el backend" sin detalle — CORREGIDO (dos capas)

- `src/lib/jobs.ts` **descartaba** `r.error` cuando `ok:false` y mostraba solo
  el genérico. Ahora propaga el detalle
  (`pollJob falló en el backend: <detalle>`). El backend solo devuelve
  `ok:false` en `job desconocido` o excepción del puente.
- Aclarado: el job generativo se sondea por el mismo `simpPoll`
  (`setSimpJobId`, `App.tsx`), así que ese aviso sí aplica a generativa.

## 3. Muerte del backend (WinError 10061, connection refused) — DIAGNOSTICADA

Arquitectura (HECHO): `app_desktop.py` lanza `server.py` en subprocess
(HTTP 127.0.0.1, puerto aleatorio) porque las DLL nativas corrompen el heap
con WebView2. Refused = proceso muerto, no lento. Evidencia en
`backend/server_stdout.log` (sesión 08:11–08:13, modelo `1pieza`, malla Gmsh
3639 nodos / 20165 elementos):
- `WARNING — Load Carga en caras: no surface triangulation → fallback
  UNIFORM en 234 nodos`: 1 cara de 35 **no se mapeó** (en envelope es por
  diseño: `_surface_matches_mesh=False`); física degradada, pero no mortal.
- **Silencio total después, sin traceback ni `server_error.log`** → muerte
  **nativa** (segfault/heap/OOM en OCC/Kratos/SuperLU) durante el solve.
  Un error Python habría dado `state=error` con mensaje.
- Agravante de observabilidad: stdout/stderr del server iban a `DEVNULL`.

**Fix (solo observabilidad, sin efecto numérico):**
- Server vuelca a `backend/server_stdout.log` (truncado por arranque,
  `*.log` en `.gitignore`) + arranque con `python -u` (sin buffer: una
  muerte nativa perdía las últimas líneas en el buffer de 4-8KB).
- Hitos `GEN solve start/done` (design_space, volfrac, iters, nº elementos,
  threshold) y `GEN reconstruct start/done` en `generative_engine.py`.
  La última línea del log ubica la fase: sin `done` tras `solve start` =
  muere en SIMP/scipy; sin `done` tras `reconstruct start` = muere en OCC.

## 4. Verificación

- `py_compile` backend OK; `tsc --noEmit` limpio; `npm run build` OK (3.2s).
- Tests backend: `generativa_flujo` + `design_space_halo` + `generative_organic`
  + `fill_order` = 22 passed (incl. colapso BREP). El live-run de
  `test_polljob_error_string.py` quedó bloqueado por lentitud del entorno
  (init Kratos de minutos); el mecanismo se verificó por código + el test
  existe y no fue tocado (este turno solo cambió frontend).

## 5. Pendientes reales

1. Reintentar generativa + envelope con **Umbral ρ 0.3** (≈ volfrac). Si
   registra geometría, causa §1 confirmada.
2. Si el backend vuelve a morir, leer el final de `server_stdout.log`
   (hitos §3) y atacar la fase exacta (SuperLU/OOM vs OCC).
3. Backfill test de `max_hole_edges="auto"` con bore de anclaje real
   (factor 4.0 / mín 12 sin medir contra pieza real; no exponer `auto`
   por defecto hasta entonces).
4. Fitting NURBS multi-región: cambio de diseño (curvas de borde compartidas
   exactas), con confirm-gate de Fase 4.5 — **no tocado**.
5. Degradación BC en envelope (fallback uniforme, §3): física incorrecta
   aunque no mortal; pendiente de diseño de mapeo en caja.
