# Estado — topologia-optimizada

**Objetivo:** App desktop de optimización topológica y diseño generativo (motor Python + GUI HTML/JS/CSS, backend FEM/CAE propio).

**Última actualización:** 2026-09-23

## Qué se hizo
- Estructura del cerebro agéntico instalada en `cerebro_agentico/` (copia byte-idéntica del origen en `Downloads/cerebro_agentico`), verificada por hash SHA256.
- Repo local verificado al día con `origin/master` en commit `875d200`.
- Cerebro verificado funcionalmente (6/6 capas, roundtrip inbox OK, `verdad/` intacta) — 2026-09-23.
- Obsidian 1.13.7 instalado y `cerebro_agentico/` abierto como vault (UI por usuario ignorada en `.gitignore`).
- Vault portable GitHub: plugins verificados + `templates.json` + guía `wiki/obsidian-en-cualquier-pc.md`.

## Qué falta
- Registrar en `verdad/` solo lo que el usuario confirme explícitamente (nada aún).
- Sintetizar conocimiento reutilizable en `wiki/` a medida que surja necesidad real.

## Decisiones abiertas
- Ninguna registrada.

## Decisiones ya tomadas (y por qué)
- Ubicación: `cerebro_agentico/` dentro de `HTML_APP/topología-optimizada` (el proyecto activo), no en la raíz del repo, para que el cerebro acompañe al producto.
- No se versionan artefactos de ejecución (`backend/uploads/`, `backend/job_status_*.json`) según `.gitignore` existente.

## Referencias
- `../AGENTS.md` (manual del cerebro)
- `../../AGENTS.md` (rol CAD/CAE del repo)
- `../../docs/` (sesiones y auditorías del proyecto)
