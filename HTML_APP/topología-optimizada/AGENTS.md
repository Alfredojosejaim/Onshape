# AGENTS.md — reglas para sesiones de trabajo (Muse Spark / ECC)

## Regla vendored/simp.py (decisión Fase 4.5b, 14-sep-2026, EXPLÍCITA del usuario)

Opción elegida: **REVERTIR**. `backend/vendored/simp.py` vuelve a estar
**CONGELADO** (regla Fase 4 reinstaurada). `set_symmetry_planes()` +
`_mirror_average`/`_mirror_min` eliminados de vendored; la simetría vive
SOLO en `core/topopt.py`. Pedir `symmetry_planes` por el path vendored
(`api._simp_loop`) falla explícito, nunca silencioso.

## Confirm-gate (Fase 0.5)

Cada opción ofrecida en `/plan` debe citar contra qué fase de `plan.md` se
justifica. Sin fase asociada → marcar "fuera de plan, requiere aprobación
explícita". Esto evita que módulos nuevos (ESO/Level-Set/simetría/térmico/
animación en su día) entren sin decisión registrada.
