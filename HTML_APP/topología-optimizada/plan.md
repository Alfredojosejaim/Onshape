# Plan de ejecución — huecos del inventario

Basado en `inventario_motores_herramientas.md`. Orden por dependencia real y relación riesgo/beneficio, no por orden en que aparecen en el inventario. Sigue tu flujo: Claude arma diff/spec → vos aprobás → Muse Spark ejecuta vía ECC (`/plan` → aprobar → TDD → `/code-review` → `/build-fix`).

---

## Fase 0 — Higiene inmediata (antes que nada, riesgo casi cero)

**0.1 Ocultar/deshabilitar ESO y Level-Set en cualquier selector de UI**
Si `OptimizerType.ESO` / `LEVEL_SET` aparecen como opciones elegibles en algún combo, eso viola tu propio principio de "no fallback silencioso": el usuario elegiría un motor que no existe y probablemente caería en SIMP sin avisar, o rompería. Fix: restringir el combo a `SIMP` únicamente, o si ya están ocultos, no hace falta tocar nada — solo confirmar.
- Riesgo: nulo. Candidato ideal para Muse Spark sin supervisión estrecha.
- No depende de nada.

**0.2 Confirmar que `ObjectiveType.MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE` no es seleccionable en UI**
Mismo motivo: el solver la rechaza explícitamente (`topo_problem.py:362-365`), así que si es elegible en algún panel, es una trampa silenciosa disfrazada de opción válida.
- Riesgo: nulo.

---

## Fase 1 — Exponer lo que YA funciona en backend (mayor ROI, menor riesgo)

Estos tres ítems no requieren tocar ningún solver: el motor ya está validado y corre. El trabajo es UI + wiring, no matemática.

**1.1 Panel de estudio Térmico**
- Agregar `ThermalAnalysis` a `study_panel.py` (mismo patrón que `TopologyOptimizationStudy`)
- Exponer `ThermalBoundary` (temperatura / flujo / convección) como condición seleccionable, reusando `NodeSelectionEngine` que ya tenés
- Conectar al `execute_on_mesh()` que ya existe en `cae_studies.py`
- Resultado esperado: temperatura nodal + flujo por elemento visibles en `results.py`

**1.2 Panel de estudio Modal**
- Mismo patrón: agregar `ModalAnalysis` a `study_panel.py`
- UI mínima: cantidad de modos, frecuencia mín/máx (`ModalParameters` ya existe)
- Requiere que el usuario defina al menos una fijación (ya validado en `validate_with_message()` — exige constraints para evitar K singular)
- Resultado esperado: lista de frecuencias + posibilidad futura de animar modo (la animación queda para después, no bloquea esta fase)

**1.3 UI de `load_case_id` en el panel de Carga**
- Agregar campo opcional "caso de carga" (agrupador) + peso relativo a `LoadCondition`
- Sin este campo, todas las cargas caen en el mismo caso (`__single_{n}` en `controller.py`) — comportamiento actual, no rompe nada, es aditivo
- Esto activa multicarga real sin tocar el solver

**Orden interno sugerido dentro de la fase:** 1.3 primero (más chico, un solo campo nuevo), después 1.1 y 1.2 en paralelo si querés repartir entre sesiones — no dependen entre sí.

**Riesgo:** bajo-medio. Es el primer tramo de esta fase donde recomendaría diff revisado por vos antes de aplicar (no delegación ciega a Muse Spark), porque toca paneles con más superficie de UI que los bugs P1-P4.

---

## Fase 2 — Bugs conocidos (ya tenés el orden, lo mantengo sin cambios)

Tu cadena ya establecida: **P1 → P2 → P4 → P3**

- **P1** — Correspondencia de tags OCCT↔Gmsh (`face_correspondence.py` ya tiene el mecanismo de `FaceSignature`; falta conectarlo en `GmshTet4Mesher._extract_all_surface_elements()`)
- **P2** — Propagación de `face_id` a triángulos de frontera (depende de P1 resuelto)
- **P4** — Halo derivado de `filter_radius` en vez de tamaño de elemento real (independiente, buen candidato de bajo riesgo para probar el pipeline ECC)
- **P3** — Semántica de `volfrac_mode` + detección de infeasibility explícita

No repito el detalle porque ya está fijado; solo lo ubico en la secuencia general porque P1/P2 bloquean que la Fase 1.1 (térmico) tenga distribución de flujo confiable si algún día usás caras para condiciones de contorno térmicas por flujo — ahí sí hay dependencia cruzada: si vas a exponer `HEAT_FLUX`/`CONVECTION` en 1.1 con selección por cara, conviene tener P1 resuelto antes, porque ambos dependen del mismo mapeo cara↔malla. Si en 1.1 solo usás `TEMPERATURE` (por nodos) al principio, podés adelantar la Fase 1 sin esperar P1.

---

## Fase 3 — Postproceso nuevo (autocontenido, sin dependencias del solver)

**3.1 Factor de seguridad**
- Función derivada: `FoS = yield_strength / von_mises` por elemento
- Input: resultado de `StructuralAnalysis` (ya tenés von Mises) + `Material.yield_strength` (ya existe)
- Visualización: mapa de zonas bajo el mínimo, reusando el mismo pipeline de color que ya usás para tensión
- No toca ningún solver, es post-cálculo puro

**3.2 Comparación de resultados (original vs. optimizado)**
- Estructura de datos nueva: snapshot de {masa, volumen, compliance, desplazamiento máx, FoS mín} por estudio
- UI: tabla comparativa simple primero (A vs B), sin animaciones ni gráficos todavía
- Extensible después a A vs B vs C

**Riesgo:** bajo. Buenos candidatos para Muse Spark con TDD, ninguno toca código de solver existente.

---

## Fase 4 — MMA/GCMMA (mayor esfuerzo, ya está en tu roadmap)

- Conectar `KratosOptimizationApplication` (MMA/GCMMA) al núcleo SIMP, replicando el patrón dual-backend que ya usás en FEA (`fea_solver` inyectable en `VendoredSIMP`, visto en `api.py: _simp_loop`)
- Esto es lo único de esta lista que yo trataría con diff-first estricto y revisión tuya en cada paso, no delegación amplia a Muse Spark — toca el núcleo del optimizador
- Depende de: nada técnicamente bloqueante de fases anteriores, pero tiene sentido hacerlo después de estabilizar Fase 1-3 para no mezclar cambios de UI con cambios de solver en la misma ventana de trabajo

---

## Fase 5 — Herramientas de malla nuevas (remesh, decimación, reparación avanzada)

- Remallado, decimación y reparación no-manifold/self-intersections no existen aún
- Recomendación: no arrancar esta fase hasta que P1/P2 estén cerrados — cualquier herramienta nueva de malla que dependa de correspondencia cara↔malla hereda el mismo riesgo que ya tenés diagnosticado
- Prioridad relativa baja: no bloquea ningún flujo actual, es calidad de geometría de salida

---

## Fase 6 — Largo plazo (cerrada 6a–6f, 13-sep-2026)

- Restricción de tensión máxima ✅ (6b): ESO con `eso_criterion="stress"` (von Mises por elemento, Xie & Steven original) + `max_von_mises` y `p_norm_von_mises` en todo resultado.
- Manufacturing constraints ✅ parcial (6c): simetría por planos (`symmetry_planes`, espejo-exacto en OC/ESO) + `overhang_report` diagnóstico por facetas + `getOverhangReport`. Overhang *activo* (sensibilidades de soporte) y resto (espesor mínimo = `filter_radius` ya existente) documentados como fuera de alcance.
- Acoplamiento térmico-estructural ✅ (6d): `thermal_load_vector` one-way (f_e = V·Bᵀ·D·ε_th) + wiring controller/engine/api (`thermal_temperatures`/`thermal_alpha`/`thermal_reference_temperature`).
- ESO ✅ motor real (Fase 6a) / Level-Set ✅ motor real (Fase 6f, HJ explícito + redistancing + nucleación topológica).
- Animación de modos ✅ (6e): `animate_mode_shape` + `getModeAnimation` (job modal + malla activa).

---

## Resumen de secuencia recomendada

```
Fase 0 (higiene)
   ↓
Fase 1.3 (UI load_case_id) ──┐
Fase 1.1 (panel térmico)      ├─ pueden repartirse, no dependen entre sí
Fase 1.2 (panel modal)       ─┘
   ↓
Fase 2 (P1 → P2 → P4 → P3)   — ya en curso según tu cadena existente
   ↓
Fase 3 (FoS + comparación)   — puede adelantarse en paralelo a Fase 2, es independiente
   ↓
Fase 4 (MMA/GCMMA)
   ↓
Fase 5 (malla nueva)
   ↓
Fase 6 (futuro sin código)
```

Nota: Fase 3 es realmente paralela a Fase 2 — no hay dependencia técnica entre postproceso nuevo y los bugs de mallado. Si en algún momento querés repartir carga entre dos sesiones de trabajo, esa es la pareja natural para hacerlo en simultáneo.

---

## Bitácora de avance (12-sep-2026)

- **Fase 0 ✅** (`ab95be6`): saneados combos de `properties.py` (solo Compliance mínima + SIMP/OC). ESO/Level-Set/MMA/GCMMA/Steepest sin motor no son elegibles.
- **Fase 1 ✅** (`ab95be6`): Thermal/Modal en `StudyPanel` desktop (el controller ya los ejecutaba; React ya los tenía vía V2Panel) + `load_case_id`/`load_weight` en UI React de Carga (backend ya agrupaba por metadata).
- **Fase 2 ✅** (`8499e02`): P1/P2/P4 verificados ya resueltos con malla real (`cono.step`: correspondence deterministic, sin unmapped; halo desde malla). P3 implementado: `problem_to_solver_inputs` rechaza infactibilidad por volumen (KEEP_IN/FROZEN_FACE > volfrac).
- **Fase 3 ✅** (`e3d431a`): FoS por elemento (`factor_of_safety`, `safety_summary`, campo `safety` en `getSurfaceMesh`, `getSafetySummary`) + `compareStudies`/`study_snapshot`; UI `SafetyCard` + `CompareTable` (reversibles).
- **Fase 4 ✅ (cerrada 13-sep-2026)**: Kratos 10.4 no expone MMA standalone → MMA propio numpy en `core/topopt.py` (`optimizer="mma"`, OC default intacto, 30 iters cantilever: MMA 0.7506 vs OC 0.7856, vol exacto). Cableado completo: (a) `controller.run_optimization(optimizer=...)` en ambas ramas + `OptimizerType.MMA`; (b) `api.runOptimization`/`runSimpLoop` aceptan `optimizer` (rechazo explícito, sin fallback) + espejo MMA en `vendored/simp.py` + `generative_engine.run_generative_design` propaga optimizer del estudio; (c) selector MMA en UI desktop (`properties.py` combo OC/MMA → `main_window.py` → controller). Verificado: `py_compile` OK + `vendored` rechaza `optimizer='bogus'` con `TopOptError` + firmas API contienen `optimizer`.
- **Fase 5 ✅ (cerrada 5a+5b, 13-sep-2026)**: herramientas de malla numpy-only en `core/cad_reconstruction.py`, sin dependencias nuevas. 5a: `mesh_quality_report`, `repair_mesh`, `decimate_mesh`, `MeshRepair`/`MeshDecimator`, wiring opt-in en `ReconstructionPipeline`. 5b: `uniform_remesh` (split >4/3·L / collapse <4/5·L / flip por valencia + laplaciano con borde fijo + `repair_mesh` final, clase `MeshRemesher`), `split_non_manifold` (duplicación explícita por hoja/componente, residual 0, sin eliminar geometría), `count_self_intersections` (broadphase por grilla + SAT completo, solo REPORTA — la reparación es ambigua por definición). Verificado sintético: remesh 200→29 tris hacia L=0.2 sin degenerados; split deja residual 0; SAT detecta 1 cruce real y 0 falsos en plano (tras corregir ejes coplanares + celda por área). Siguiente: Fase 6 (largo plazo, sin código todavía).
- **Fase 6a ✅ (13-sep-2026)**: ESO hard-kill real en `core/topopt.py` (`optimizer="eso"`, `_eso_optimize`: ranking por energía de deformación filtrada + promedio histórico, tasa evolutiva ER=0.02, preservados nunca removidos, convergencia clásica por estabilidad del compliance + óptimo discreto). Refactor seguro: análisis final extraído a `_finalize_result` compartido (OC/MMA bit-idénticos: regresión cantilever 10 iters OC C=1030 / MMA C=715.2, vol exacto). Espejo en `vendored/simp.py` + wiring (`controller`, `api.runOptimization`/`runSimpLoop`, `generative_engine` con mapeo honesto sin coerción silenciosa, UI desktop OC/MMA/ESO). Verificado cantilever 36 tets: ESO 7 iters, diseño binario 0/1, vol 0.5005 (tolerancia de un elemento discreto), core y vendored idénticos. Resta Fase 6: tensión máxima, manufacturing, acoplamiento térmico-estructural, Level-Set, animación de modos.
- **Fase 6 ✅ (cerrada 6b–6f, 13-sep-2026)**: (6b) ESO `eso_criterion="stress"` + `max/p_norm_von_mises` en todo resultado (cantilever: stress-ESO binario 7 iters, core=vendored); (6c) `set_symmetry_planes` (espejo-exacto OC/ESO verificado) + `overhang_report` por facetas (`T: 0.242` vs `columna: 0.0`) + `api.getOverhangReport`; (6d) `thermal_load_vector` one-way auto-equilibrado (ΣF≈1e-13, dT=0→cero exacto) + wiring controller/engine/api, verificado acoplado (C 2.05e9→9.2e9 con gradiente); (6e) `animate_mode_shape` (auto=5% bbox, sinusoidal exacto, eigenvector real `solve_modal`) + `api.getModeAnimation`; (6f) Level-Set HJ (`optimizer="level_set"`, Heaviside 0.5h, λ con ganancia, nucleación por espaciado nodal, Sussman): cantilever 12×2×2 → vol 0.47, C 8.7e4 (rango OC), conectado; delegación vendored→núcleo con etiqueta engine y error propio. Bugs encontrados y corregidos: signo de velocidad HJ, radio de nucleación bajo espaciado nodal, SAT coplanar, grilla plana, soporte circular en overhang. Plan completo: Fases 0–6 cerradas.
- **Fase 4.5 ✅ (auditoría scope-creep, 14-sep-2026)**: 4.5a verificado — `load_case_id`/`load_weight` ya en UI React (`faces.ts` + `ToolParamsPanel` + `App`); desktop cerrado en 2da ronda (campo ID + peso en Cargas). 4.5b decisión EXPLÍCITA (revertir): `vendored/simp.py` vuelve a CONGELADO, simetría solo en núcleo (ver `AGENTS.md`). 4.5c `backend/tests/test_fase45_regresion.py` 9/9 (simetría+rechazo vendored, térmico auto-equilibrado/cero-exacto, ESO binario compliance+stress, level-set estable, animación forma/salida). 4.5d `evolutionary_rate`/`ls_cfl`/`ls_hole_period` y plano de simetría expuestos en desktop (`properties.py` → `main_window.py` → `controller` → `generative_engine`/`api.runOptimization`/`runSimpLoop`/`_simp_loop`, con validación fail-loud en cada capa). Diferido con motivo: toggle térmico (requiere estudio térmico previo resuelto como fuente de T) y botón animar-modo (requiere plumbing de resultados modales al panel) — ambos necesitan flujo de datos, no solo un campo. 0.5 confirm-gate documentado en `AGENTS.md`.
- **Fase 4.5d.4 ✅ + 4.5d.5 ✅ (14-sep-2026)**: toggle térmico (properties + StudyPanel → `resolve_thermal_kwargs` → ambos paths, vale core+vendored) y animar-modo (results + QTimer + 5 restricciones VTK). Tests 16/16. Detalle en `docs/cierre-fases-4b-6f.md` §12.
- **Fase 6 GCMMA ✅ (14-sep-2026, solo núcleo, vendored intacto)**: `optimizer="gcmma"` en core + controller/api/engine/UI; benchmark Kuhn OC=202.6 MMA=124.2 GCMMA=138.5. Tests 20/20. Detalle en `docs/cierre-fases-4b-6f.md` §13.
- **Cierre prompt.md (14-sep-2026, auditoría + validación pre-export)**: verificado que GCMMA/ESO/Level-Set/simetría/multicarga/térmico/modal/generativo A+B ya están operativos UI+backend (tests 13/13: `test_gcmma` + `test_fase45_regresion`). Añadido `api.validateExportGeometry` (Fase 5+6c, solo diagnóstico: `mesh_quality_report` + `count_self_intersections` + `overhang_report` volumétrico si hay densidades; sin malla o con degenerados falla explícito). Fuera de plan y SIN implementar sin aprobación explícita (confirm-gate): espesor mínimo independiente, overhang activo, reparación auto de self-intersections, minimizar-volumen-sujeto-a-compliance, Tet10/Hex8, soportes automáticos.
- **Implementación alcance prompt.md ✅ (14-sep-2026, con aprobación explícita del usuario)**: (a) espesor mínimo `min_thickness` en `core/topopt.py` (piso de filtro + apertura morfológica por iteración, fail-loud si ≤0); (b) overhang activo `overhang_constraint` (filtro por capas según `build_direction`/ángulo, penalización configurable); (c) `repair_self_intersections` (weld + laplaciano local iterado, reporta residual) + `api.repairSelfIntersections`; (d) soportes `generate_supports` (pilares a la base desde `unsupported_ids`) + `api.generateSupports`; (e) objetivo `min_volume` por bisección externa sobre volfrac (requiere `compliance_limit`, fail-loud si infactible; `topo_problem` acepta `MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE` con `max_compliance`); (f) Tet10 (`tet4_to_tet10` + `solve_fea_tet10` por subdivisión en 8 Tet4) y Hex8 (`hex8_stiffness` Gauss 2x2x2 + `solve_fea_hex8`); wiring `controller`/`generative_engine`/`api.runOptimization`/UI desktop (espesor, overhang, objetivo+limite). Tests: `test_fabricacion_objetivo.py` 5/5, suite total 41/41. Vendored intacto (sin gcmma/simetría/nuevos objetivos por path vendored).
