# Estado — topologia-optimizada

**Objetivo:** App desktop de optimización topológica y diseño generativo (motor Python + GUI HTML/JS/CSS, backend FEM/CAE propio).

**Última actualización:** 2026-09-24

## Qué se hizo (2026-09-24, auditoría thermo-nuclear dual + P0/P1)

## Qué se hizo
- Estructura del cerebro agéntico instalada en `cerebro_agentico/` (copia byte-idéntica del origen en `Downloads/cerebro_agentico`), verificada por hash SHA256.
- Repo local verificado al día con `origin/master` en commit `875d200`.
- Cerebro verificado funcionalmente (6/6 capas, roundtrip inbox OK, `verdad/` intacta) — 2026-09-23.
- Obsidian 1.13.7 instalado y `cerebro_agentico/` abierto como vault (UI por usuario ignorada en `.gitignore`).
- Vault portable GitHub: plugins verificados + `templates.json` + guía `wiki/obsidian-en-cualquier-pc.md`.

## Qué se hizo (2026-09-24, auditoría thermo-nuclear dual + P0/P1)
- Doble auditoría (quality + review, solo lectura) ejecutada y sintetizada: 9 archivos >1k, fork vendored, fallback silencioso, P1 parcial, halo/volfrac ya cerrados.
- P0 docs: `inventario.md` actualizado (halo ✅, volfrac ✅, FoS ✅ postproceso, CompareTable ✅, correspondencia parcial, vendored acepta oc/mma/eso/level_set solo rechaza gcmma); `cae_studies.py` Thermal/Modal docstrings corregidos (solver real vía execute_on_mesh).
- P1: `problem_to_solver_inputs` devuelve `warnings[]` con `order_based_face_labels` (AGENTS §4); `configure_material_manually` rechaza SI sin convertir (guardia x1e6); GCMMA y degradadas verificados ya cubiertos (rechazo temprano en `api.runSimpLoop`, render en `App.tsx`/`main_window.py`).
- Verificación: `tsc --noEmit` OK, `pytest backend/tests` **141 passed** sin regresiones.

## Qué se hizo (2026-09-23, plan cierre-brechas-núcleo)
- `plan.md` = plan vigente (supersede roadmap Fase 0–6 completado); `Auditoria scope creep y plan v2.md` = stub con puntero.
- `topo_problem.py` acepta `TOTAL_VOLUME` + propaga `objective/compliance_limit` (`test_problem_adapter.py`, 6 tests).
- `vendored/simp.py` espeja piso OC relativo a máquina; `api._simp_loop` rechaza `volfrac_mode≠active` explícito.
- `kratos_adapter.configure_material_from_core` convierte SI→mm (E, densidad, yield); test en `test_units_mm.py`.
- Guard carga-en-preservada: solo degradada `load_on_preserved_region`, sin error duro (`test_bc_on_preserved.py`, 3 tests).
- `inventario.md` actualizado al estado real del código; `tsconfig.json` excluye `tools/` del lint.
- Verificación final: lint OK, build OK, suite backend **141 passed** (131 base + 10 nuevos), sin regresiones.

## Qué falta
- Registrar en `verdad/` solo lo que el usuario confirme explícitamente (nada aún).
- Sintetizar conocimiento reutilizable en `wiki/` a medida que surja necesidad real.
- Decidir si Térmico/Modal salen del panel V2 oculto al flujo principal.

## Decisiones abiertas
- Ninguna registrada.

## Decisiones ya tomadas (y por qué)
- Ubicación: `cerebro_agentico/` dentro de `HTML_APP/topología-optimizada` (el proyecto activo), no en la raíz del repo, para que el cerebro acompañe al producto.
- No se versionan artefactos de ejecución (`backend/uploads/`, `backend/job_status_*.json`) según `.gitignore` existente.

## Referencias
- `../AGENTS.md` (manual del cerebro)
- `../../AGENTS.md` (rol CAD/CAE del repo)
- `../../docs/` (sesiones y auditorías del proyecto)
