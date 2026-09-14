# AGENTS.md — reglas para sesiones de trabajo (Muse Spark / ECC)

## Regla vendored/simp.py (decisión Fase 4.5b, 14-sep-2026)

La regla original "keep `backend/vendored/simp.py` untouched" (Fase 4, path
congelado Kratos-in-loop) **ya no aplica**: Fase 6c añadió
`set_symmetry_planes()` + espejo en `vendored/simp.py`, idéntico al núcleo
(`core/topopt.py`), más espejos de optimizer/eso_criterion en cada fase 6x.

Decisión formal (opción 2 de la auditoría scope-creep): **vendored NO está
congelado**. Mantener paridad core↔vendored en cada cambio de solver
(verificado: cantilever core=vendored bit-idéntico en OC/MMA/ESO-stress).

## Confirm-gate (Fase 0.5)

Cada opción ofrecida en `/plan` debe citar contra qué fase de `plan.md` se
justifica. Sin fase asociada → marcar "fuera de plan, requiere aprobación
explícita". Esto evita que módulos nuevos (ESO/Level-Set/simetría/térmico/
animación en su día) entren sin decisión registrada.
