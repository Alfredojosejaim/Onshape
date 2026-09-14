# Cierre de fases 4b–6f — motores, malla y acoplamientos (13-sep-2026)

De Fase 4 parcial (MMA solo accesible por API Python) a **Fases 0–6 cerradas**.
Stack: solo `numpy`/`scipy` (sin dependencias nuevas). Principio transversal:
rechazo explícito antes que fallback silencioso.

## 1. Fase 4b/4c — MMA completo

- Espejo MMA en `backend/vendored/simp.py` (`_mma_reset_state`, `_mma_update`,
  `optimize(optimizer=...)`).
- `api.runOptimization` / `runSimpLoop` aceptan `optimizer` (`oc|mma`, rechazo
  explícito); `_simp_loop` lo propaga. `run_generative_design` propaga el
  optimizer del estudio.
- UI desktop: combo OC/MMA en `properties.py` → `main_window.py` → controller.

## 2. Fase 5a/5b — herramientas de malla (`core/cad_reconstruction.py`)

- 5a: `mesh_quality_report`, `repair_mesh` (suelda + degenerados + huérfanos),
  `decimate_mesh` (clustering por área), `MeshRepair`/`MeshDecimator`, wiring
  opt-in en `ReconstructionPipeline`. Non-manifold se **reporta**, no se arregla.
- 5b: `uniform_remesh` (split >4/3·L, collapse <4/5·L, flip por valencia,
  laplaciano con borde fijo), `split_non_manifold` (duplicación explícita,
  residual 0), `count_self_intersections` (grilla + SAT completo, **solo
  reporta**), `MeshRemesher`.

## 3. Fase 6a/6b — ESO + tensión (`core/topopt.py`, espejo en `vendored/simp.py`)

- ESO hard-kill (`optimizer="eso"`, ER=0.02): ranking por energía de deformación
  filtrada + promedio histórico; preservados nunca removidos; convergencia
  clásica + óptimo discreto. Finalizador extraído a `_finalize_result`
  (OC/MMA bit-idénticos).
- 6b: `eso_criterion="compliance"|"stress"` (von Mises por elemento, Xie &
  Steven original) + `max_von_mises` / `p_norm_von_mises` (p=8) en todo resultado.

## 4. Fase 6c — manufactura

- `set_symmetry_planes([(eje, valor)])`: OC/MMA promedian pares, ESO promedia
  sensibilidades y propaga remociones al espejo (preservados re-pineados).
  Plomeado por controller/engine/API (`symmetry_planes`).
- `overhang_report` por **facetas** (normal exterior vs. vertical, placa excluida)
  + `api.getOverhangReport`. Overhang *activo* fuera de alcance (documentado).

## 5. Fase 6d — acoplamiento térmico-estructural one-way

- `core/thermal.py::thermal_load_vector`: `f_e = V_e·B_eᵀ·D·ε_th,e`,
  `ε_th = α·(T̄_e−T_ref)·[1,1,1,0,0,0]`. Se suma a cada caso mecánico
  (controller/engine/`_simp_loop`). α de `thermal_alpha` o
  `material.thermal_expansion`; sin α → error explícito.

## 6. Fase 6e — animación de modos

- `cae_studies.animate_mode_shape` (fotogramas `amp·sin(2πf/n)·phi`,
  `auto` = 5% de la diagonal del bbox) + `api.getModeAnimation`
  (job modal + malla activa, límite N·n_frames ≤ 2M).

## 7. Fase 6f — Level-Set real (`optimizer="level_set"`)

- Frontera implícita φ=0, HJ explícito con V=λ−se y λ con ganancia,
  Heaviside 0.5h, redistancing de Sussman, nucleación topológica por
  espaciado nodal. Vendored **delega** al núcleo (sin legado que espejar,
  etiqueta engine y error propios).

## 8. API nueva / parámetros nuevos

- Endpoints: `getOverhangReport`, `getModeAnimation`.
- Params (`runOptimization`, `runSimpLoop`): `optimizer` (oc|mma|eso|level_set),
  `eso_criterion`, `symmetry_planes`, `thermal_temperatures`,
  `thermal_alpha`, `thermal_reference_temperature`.
- UI desktop: combo algoritmo (4) + criterio ESO. UI React sin cambios.

## 9. Verificación (mallas sintéticas Kuhn, cantilever)

| Check | Resultado |
|---|---|
| ESO compliance/stress, core=vendored | binario 0/1, 7 iters, conv |
| OC/MMA regresión post-refactor | C=1030 / 715.2, vol exacto |
| Simetría y=1.0 (OC y ESO) | espejo-exacto (diff 0.0) |
| Overhang columna / T | 0.0 / 0.242 |
| Térmico: ΣF≈1e-13, dT=0→cero, acoplado C 2.05e9→9.2e9 | OK |
| Animación (eigenvector `solve_modal`) | sinusoidal exacto, auto=5% bbox |
| Level-Set 12×2×2 | vol 0.47, C 8.7e4 (rango OC), conectado |
| Rechazos (`bogus`, ER=0, fracción 2.0, build_direction nulo…) | todos explícitos |

## 10. Observaciones y límites honestos

1. **Level-Set, transitorio inicial**: la nucleación puede desconectar el diseño
   en las primeras iteraciones (C alto) y el HJ lo reconecta solo. En mallas
   gruesas (<100 tets) cualquier método 0/1 (ESO incluido) degrada: usar OC.
2. **Correcciones hechas en el camino**: signo de velocidad HJ, radio de
   nucleación bajo espaciado nodal, ejes SAT para coplanares, celda broadphase
   por área (mallas planas), soporte circular en overhang (→ formulación por
   facetas), `build_direction` dict → ValueError, celda de decimación por área.
3. **Fuera de alcance (explícito)**: overhang activo, GCMMA / MMA-vía-Kratos
   (Kratos 10.4 no expone MMA standalone), Level-Set con redistancing exacto,
   espesores mínimos más allá de `filter_radius`, UI React para los motores
   nuevos (solo desktop).
4. **Coerción silenciosa eliminada**: `generative_engine` mapeaba todo lo no-MMA
   a OC; ahora `level_set` sin motor falla explícito.
5. `src/App.tsx`: el duplicado `handleSelectTool` que rompía `npm run build`
    se eliminó; el archivo quedó idéntico a HEAD (venía de un cambio sin
    commitear de otra sesión).

## 11. Fase 4.5 — auditoría scope-creep (14-sep-2026)

- **4.5a**: `load_case_id`/`load_weight` ya en UI React (`faces.ts`,
  `ToolParamsPanel`, `App`); desktop sin campo (gap registrado).
- **4.5b (decisión EXPLÍCITA, revertir)**: `vendored/simp.py` vuelve a
  CONGELADO — `set_symmetry_planes()` + espejo eliminados; simetría solo en
  `core/topopt.py`; `api._simp_loop` falla explícito — ver `AGENTS.md`.
  (2da ronda 14-sep: 4.5a también cerrado en desktop — campo ID + peso en
  Cargas → `controller.forces`.)
- **4.5c**: `backend/tests/test_fase45_regresion.py`, 9/9 (simetría+rechazo vendored,
  térmico, ESO compliance/stress, level-set, animación).
- **4.5d**: `evolutionary_rate`/`ls_cfl`/`ls_hole_period` + plano de simetría
  en desktop → controller → engine/API (fail-loud por capa). Diferidos:
  toggle térmico (requiere estudio térmico resuelto) y botón animar-modo
  (requiere plumbing modal→panel).
- **0.5**: confirm-gate anclado a fases de `plan.md` (ver `AGENTS.md`).

## 12. Fase 4.5d.4–5 — toggle térmico + animar-modo en UI desktop (14-sep-2026)

- **4.5d.4**: sección "Acoplamiento térmico" en `properties.py` (checkbox +
  combo de Thermal COMPLETED + α manual/0=auto) y en `StudyPanel` (topology);
  `controller.resolve_thermal_kwargs()` fail-loud (tipo/estado/campo/malla/α);
  `TopologyOptimizationStudy.thermal_study_id/alpha/Tref` → `execute_study`;
  quick-run valida en hilo UI antes del worker. Sin backend nuevo: el core y
  `_simp_loop` ya procesaban `thermal_*` (vale para ambos motores).
- **4.5d.5**: sección "Animación modal" en `results.py` (combo de modos +
  ▶/⏸ + velocidad 0.5/1/2×), visible solo con Modal corrido; `MainWindow`
  con QTimer (~120ms/velocidad), frames de `core.animate_mode_shape`
  (base + desplazamiento, desktop directo — misma función que `api`).
  Restricciones: (1) solo actor "mesh" (`begin` falla explícito sin malla;
  densidad oculta durante, B-Rep nunca tocado; software viewport dice que
  requiere GPU); (2) base guardada en `set_mesh`, `end` restaura exacto;
  (3) picking suspendido + cursor ⊘ + mensajes; (4) QTimer, sin loops;
  (5) parada en pausa/nuevo run/malla/import/cierre/reset (`_stop_animation_and_modal`;
  caché modal validado por stamp de malla).
- Tests `backend/tests/test_fase45d_ui.py` 7/7 (16/16 total con regresión).

## 13. Fase 6 — GCMMA Svanberg 2002 (14-sep-2026, solo núcleo)

- `core/topopt.py::_gcmma_update`: aproximaciones convexas separables
  conservadoras por función (p/q con ρ + r que iguala en xa), dual por
  bisección (mismo que MMA), iteración interna con update ρ (3.9) y chequeo
  en objetivo + restricción (volumen exacto, compliance con 1 solve extra;
  gradientes no se recalculan). Cap 5 internas con bandera explícita
  (`gcmma_inner_capped`, `gcmma_inner_iters` en resultado e historial).
- `vendored/simp.py` NO tocado (congelado Fase 4.5b): `optimizer="gcmma"`
  ahí y en `api.runSimpLoop` falla explícito. Wiring: controller,
  `api.runOptimization`, `generative_engine` (`OptimizerType.GCMMA`),
  combo desktop.
- Benchmark barra Kuhn 24 tets, 10 iters: OC=202.6, MMA=124.2, GCMMA=138.5
  (vol exacto, mejora vs iter 1). OC/MMA bit-idénticos pre/post cambio.
- Nota honesta: el certificador interno rara vez cierra en ≤5 internas en
  compliance SIMP (gap ~×0.5/interna); el optimizador igual converge bien y
  la bandera lo declara. Costo: ~1 solve extra por interna.

## 14. Alcance prompt.md — fabricación activa, min-volumen, Tet10/Hex8 (14-sep-2026, con aprobación explícita)

- `min_thickness` (`core/topopt.py::_apply_min_thickness`): piso de filtro +
  apertura morfológica por iteración; fail-loud si ≤ 0. Wiring controller /
  engine / `api.runOptimization` / desktop.
- Overhang activo (`_apply_overhang_filter`): filtro por capas según
  `build_direction` + ángulo + `overhang_penalty`; `generate_supports` (pilares
  a la base desde `unsupported_ids`) + `api.generateSupports`.
- `repair_self_intersections` (weld + laplaciano local, reporta residual) +
  `api.repairSelfIntersections`; `api.validateExportGeometry` previo.
- Objetivo `min_volume` por bisección externa (`compliance_limit` requerido,
  fail-loud si infactible); `topo_problem` acepta
  `MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE` con `max_compliance`.
- Tet10 (`tet4_to_tet10` + `solve_fea_tet10` por subdivisión en 8 Tet4) y Hex8
  (`hex8_stiffness` Gauss 2×2×2 + `solve_fea_hex8`). Tests
  `test_fabricacion_objetivo.py` 5/5; suite total 41/41. Vendored intacto.

## 15. NOTA DE OBSERVACIÓN — limitaciones honestas a revisar después (14-sep-2026)

1. **Overhang activo es heurístico por capas, no adjoint.** Atenúa densos sin
   soporte en vez de añadir sensibilidades de soporte al gradiente (Langelaar
   completo). Revisar después: comparar contra sensibilidades adjoint y medir
   si el filtro por capas sub-penaliza voladizos en mallas finas.
2. **Tet10 por subdivisión, no cuadrático real.** Cada Tet10 se resuelve como
   8 Tet4 con el solver existente; el campo se interpola, no hay integración
   con funciones de forma cuadráticas ni error estimado vs Tet10 analítico.
   Revisar después: benchmark Tet10-subdividido vs Tet4 fino en compliance y
   convergencia, y decidir si vale la pena el elemento cuadrático real.
3. **Efecto neutro en mallas gruesas.** En Kuhn 4×1×1 (24 tets, cantilever)
   `min_thickness=0.5` y overhang activo dan compliance idéntica a la base
   (178.669): la malla no resuelve rasgos del orden del filtro. Revisar
   después: repetir en malla fina (p. ej. puente 3D o viga en voladizo densa)
   y comprobar que el espesor mínimo engrosa miembros y el overhang reduce
   `unsupported_fraction` del `overhang_report`.
4. **`min_volume` cuesta ~outer_iters solves completos** (bisección, default
   6 niveles). Revisar después: calentar cada nivel desde el anterior (hoy
   reinicia en uniforme) y exponer `outer_iters` en UI si el costo molesta.
