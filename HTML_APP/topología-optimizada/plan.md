# Plan vigente — cierre de brechas del núcleo (EJECUTADO 2026-09-23)

> Supersede al roadmap original por fases (Fase 0–6, vaciado el 2026-09-16,
> commit `0a179e5`; recuperable con `git show 0a179e5^:plan.md`).
> Aquel roadmap está **completado**: LOAD-CASE (Fase 1.3), SafetyCard (3.1),
> CompareTable (3.2), MMA (Fase 4), GCMMA/ESO/Level-Set (Fase 6) existen en
> código y UI. Los comentarios `plan.md Fase X` en el código refieren a ese
> roadmap histórico, no a este archivo.
>
> Fuente de verdad del estado real: `inventario.md` (en reescritura, Fase 5.1),
> `prompt.md` (auditoría + addenda 1–12) y `docs/sesion-*.md`.
> Criterio de orden: `AGENTS.md` §7 (corrección física > arquitectura >
> conservación > robustez > mantenibilidad > rendimiento > complejidad mínima).

## Fase 0 — Línea base (solo lectura/ejecución)

- 0.1 `npm run lint`, `npm run build`, `pytest backend/tests -q` → anotar resultado antes de tocar nada.
- 0.2 Confirmar `V2_ENABLED` (`src/lib/v2flags.ts`) y si `CompareTable` está cableado en el flujo principal.

## Fase 1 — `topo_problem.py` alinear con el solver (prioridad máxima)

`problem_to_solver_inputs` rechaza lo que `core/topopt.py` + UI ya soportan
(`topo_problem.py:358-380` vs `AdvancedOptPanel.tsx`).
- 1.1 Aceptar `VolfracMode.TOTAL_VOLUME` y propagar `volfrac_mode` real (hoy línea 516 fija comentario "siempre active_domain").
- 1.2 Aceptar `MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE` con `max_compliance > 0` y pasar `objective/compliance_limit` al solver.
- 1.3 Decidir `stress/displacement constraints` y `BCType != FIXED`: pass-through honesto o rechazo explícito documentado como decisión (no como "Fase 1 pendiente").
- Tests: extender `test_volfrac_mode.py` vía schema; casos `min_volume` sin/con límite; cada rechazo conservado con su test.

## Fase 2 — Ruta estructural (`vendored/simp.py`, congelado)

- 2.1 Subir piso OC `1e-12 → np.finfo.tiny` (`vendored/simp.py:314`, una línea reversible) **o** documentar divergencia estructural/generativa en `docs/`.
- 2.2 `volfrac_mode` en estructural: propagar modo total o rechazar explícito (nunca silencioso).

## Fase 3 — Unidades mm (densidad/Kratos)

- 3.1 Auditar consumidores de `Material.density` / `young_modulus` (`kratos_adapter.py`, `fea.py`, estudios) y aplicar `density_mm` / `young_modulus_mm` donde falte, sin doble conversión.
- Regresión: extender `test_units_mm.py`.

## Fase 4 — Guard BC carga-en-preservada

- 4.1 Helper simétrico a `_load_on_fixed_fraction` que mida solape carga↔`preserved_elements` (>99.9% error, ≥90% degradada).
- Test nuevo `test_bc_on_preserved.py` espejo de `test_bc_shortcut.py`.

## Fase 5 — Deuda documental (cierre)

- 5.1 Reescribir `inventario.md` §1.2/§3/§4 con el estado real (✅ ESO/Level-Set/MMA/GCMMA/Tet10/remesh/FoS/overhang/multicarga).
- 5.2 ESTE ÍTEM (hecho): `plan.md` = plan vigente; `Auditoria scope creep y plan v2.md` = stub con puntero.
- 5.3 Actualizar `cerebro_agentico/proyectos/topologia-optimizada/estado.md` + línea en `log/` al cerrar.

## Verificación por fase (FASE E)

`tsc --noEmit` + `vite build` + suite backend completa; corrida real corta
(STEP + carga + fijación + export/reimport) al final de Fase 2.
