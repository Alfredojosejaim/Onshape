# Reporte — "error al optimizar con generativa, envelope, b-spline"

**Proyecto:** `HTML_APP/topología-optimizada`
**Fecha:** 16-sep-2026
**Alcance:** `backend/api.py`, `backend/core/cad_reconstruction.py`.
**Relacionado:** `sesion-2026-09-16-bspline-real-envelope-skin.md`.

El usuario reportó el aviso **`La optimización terminó con error`** (no
`TimeoutError`) al ejecutar generativa + envelope + b-spline.

---

## 1. El detalle del error se perdía en la UI — CORREGIDO

`Api.pollJob` guardaba/devuelta `error` como **dict** (`_err()` →
`{ok, error, trace}`), pero `src/lib/jobs.ts` solo muestra el detalle si es
`string`; con un dict caía al genérico `"El job terminó con error"`,
ocultando la causa real.

**Fix (`JOB-ERR-STR`, `backend/api.py`):** `pollJob` desenvuelve el dict y
devuelve `error` como string (`"<Tipo>: <mensaje>"`). Así la UI muestra el
motivo concreto.

## 2. El ajuste B-spline podía tumbar el job — BLINDADO

`OCPBSplineFitter.fit` invocaba `_fit_patches_solid` **sin** `try/except`; una
excepción inesperada de OCP abortaba toda la reconstrucción y el job
terminaba en error genérico.

**Fix (`FAIL-SAFE`, `backend/core/cad_reconstruction.py`):** la llamada al
ajuste por parches queda envuelta; ante cualquier excepción se cae a la
cadena facetada (unify→restriction→continuidad) y se registra
`bspline_fit="error"` + `bspline_fit_error=<Tipo: mensaje>` en metadata
(nunca silencio, nunca geometría inválida).

## 3. Reproducción (headless) — sin error en el backend

Con `cono.step`, generativa + envelope + b-spline:

- Sin condiciones de cara y **con** condiciones por cara (carga, fijación,
  preservada, keep-out): `state=done`, `stage=brep_solid`, STEP registrado
  (`register` ≈ 37 s, `reason=None`).
- 50 iteraciones: solve ≈ 8,5 min; `bspline_fit=fallback_mixed`
  (isosuperficie TO ruidoso), **sin excepción**.
- `unsupported_conditions` vacío.

Conclusión: el backend no falla en los caminos reproducidos; la causa del
error del usuario requiere el mensaje real (ahora visible con el fix 1).

## 4. Hipótesis pendiente de confirmar

Con la skin de vacío del envelope (~26% del dominio) un `volume_fraction`
alto (la UI permite hasta 0.80) podría volver el problema **infactible**
(material activo < objetivo) y lanzar excepción en el solver. La prueba por
`volfrac` (0.35 / 0.6 / 0.8) quedó **interrumpida**; sin confirmar.

## 5. Acción siguiente

1. Repetir el error con la UI actualizada (ya muestra el mensaje real) y
   capturar el texto `"<Tipo>: <mensaje>"`.
2. Según el caso, decidir:
   - (a) acotar `volume_fraction` al material activo del envelope con skin, o
   - (b) reducir la skin (capa más fina o mayor padding) para bajar el tiempo
     y evitar infactibilidad.

## 6. Riesgo de rendimiento

El envelope con skin elevó el tiempo de corrida (≈250–300 s en 30 iters;
≈8,5 min en 50). Es la contrapartida de garantizar superficie cerrada.
