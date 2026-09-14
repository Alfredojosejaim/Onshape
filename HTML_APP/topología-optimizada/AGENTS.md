# AGENTS.md — reglas para sesiones de trabajo (Muse Spark / ECC)

## Regla vendored/simp.py (decisión Fase 4.5b, 14-sep-2026, EXPLÍCITA del usuario)

Opción elegida: **REVERTIR**. `backend/vendored/simp.py` vuelve a estar
**CONGELADO** (regla Fase 4 reinstaurada). `set_symmetry_planes()` +
`_mirror_average`/`_mirror_min` eliminados de vendored; la simetría vive
SOLO en `core/topopt.py`. Pedir `symmetry_planes` por el path vendored
(`api._simp_loop`) falla explícito, nunca silencioso.

## Nota GCMMA (Fase 6, 14-sep-2026)

`optimizer="gcmma"` vive SOLO en `core/topopt.py` (vendored congelado).
El certificador interno rara vez cierra en ≤5 internas en compliance SIMP
(gap ~×0.5/interna desde ~0.13 con tolerancia 1e-9) — el optimizador igual
converge bien (Kuhn: 138.5 vs MMA 124.2) y `gcmma_inner_capped` lo declara.
Cada interna cuesta 1 solve FEA extra: no subir `_GCMMA_MAX_INNER` sin
medir costo/beneficio en benchmark.

## Confirm-gate (Fase 0.5)

Cada opción ofrecida en `/plan` debe citar contra qué fase de `plan.md` se
justifica. Sin fase asociada → marcar "fuera de plan, requiere aprobación
explícita". Esto evita que módulos nuevos (ESO/Level-Set/simetría/térmico/
animación en su día) entren sin decisión registrada.
