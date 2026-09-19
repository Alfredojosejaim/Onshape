# Sesión 2026-09-19  Volfrac sobre volumen total, unidades mm-N y guard de BC

**Proyecto:** `HTML_APP/topología-optimizada`
**Fecha:** 19-sep-2026
**Alcance:** `backend/core/topopt.py`, `backend/core/materials.py`,
`backend/core/generative_engine.py`, `backend/core/cae_studies.py`,
`backend/core/topo_problem.py`, `backend/api.py`,
`backend/desktop/pipeline/controller.py`, `src/types.ts`, `src/App.tsx`,
`src/components/RightPanel.tsx`, `backend/tests/*`.
**Relacionado:** `sesion-2026-09-17-envelope-preserve-keepout-banda-oc.md`
(piso OC absoluto / "bulto cuadrado"),
`sesion-2026-09-17-generativa-threshold-muerte-backend.md`
(compliance ~1e-6 / degradación BC en envelope).

Reportes del usuario que originan la sesión:

1. *"cambien el volfrac a 0.35 y resuelve pero no es lo esperado, infla el
   modelo y no debería pasar, si se supone que tiene que quedar el 35% de
   volumen inicial"*.
2. *"ese problema lo da con 50n"* (compliance ~0, `Complimiento: 0.0 mJ`,
   `Reconstructed solid is not valid`).

---

## 1. VOLFRAC-MODE  el % aplicaba al dominio activo, no al volumen de la pieza

**Síntoma:** con `volfrac = 0.35` el sólido resultante era un bulto con más
material del pedido ("infla todo").

**Causa:** `volfrac` se aplicaba solo al subdominio **activo**
(`V_active = V_total - V_preserved - V_void`, `topopt.py:15-29`, opción A de
traceback.md "PROBLEMA 3"). Con regiones preservadas (Pernos/Bujos), keep-out
(Paso Tornillo) y el halo de carga/apoyo, el volumen físico total es
`V_preserved + volfrac * V_active > volfrac * V_total`. A esto se sumaba que la
proyección Heaviside con `eta` fijo no conserva volumen (`topopt.py:465-476`
documenta el caso medido 0.35 -> 0.419, +20%).

**Fix (reversible):** nuevo modo `volfrac_mode` en `SIMPSolver`:

| modo | objetivo sobre el dominio activo |
|---|---|
| `active_domain` | `volfrac * V_active` (histórico) |
| `total_volume` | `volfrac * V_total - V_preserved - rho_min * V_void` |

- `topopt.py`: `volfrac_mode` en `__init__`; helpers
  `_preserved_volume/_void_volume/_target_active_volume/_volfrac_active`;
  OC, MMA, GCMMA, ESO y level-set usan el objetivo mode-aware; chequeo de
  factibilidad fail-loud (si `volfrac*V_total < V_preserved` o
  `> V_preserved + V_active`); reporta `volfrac_mode` y
  `target_active_volume_fraction`. La densidad inicial del dominio activo se
  precarga al objetivo real en modo total.
- `generative_engine.py` / `api.py`: propagan `volfrac_mode`.
- UI: campo `volfracMode` en `SimpParameters`, selector "Volumen sobre" en el
  panel de Fracción de Volumen. **Default = `total_volume`** (lo que el usuario
  espera: "marco 35% y queda el 35% de la pieza"); `active_domain` sigue
  disponible.
- Solo aplica a **Generativa**; la ruta estructural usa `vendored/simp.py`, que
  no conoce el modo.

**Para volver atrás:** quitar `volfrac_mode` + helpers y restaurar
`self.volfrac * self._vol0_free`; borrar campo/selector/`volfrac_mode` en UI.

**Verificación:** `tests/test_volfrac_mode.py` (4). Demo con 25% preservado y
`volfrac=0.40`: `active_domain` -> físico 0.55; `total_volume` -> físico 0.40.

---

## 2. UNITS-MM  E del material en Pa con malla en mm (1e6 de más)

**Síntoma:** `Complimiento: 0.0 mJ`; compliance/sensibilidades ~1e-6 de lo
real, lo que empujaba el OC a los pisos numéricos (`1e-12`, `1e-18`) y al
colapso del diseño (el "bulto cuadrado" que se parcheó en
`sesion-2026-09-17-envelope-preserve-keepout-banda-oc.md` era el síntoma, no la
causa).

**Causa:** `materials.py` declara E en **SI** (`steel = 210e9 Pa`), pero
`core.fea` / `core.topopt` / `vendored.simp` trabajan con coordenadas en **mm**
y esperan **N/mm**. Los tests ya usaban `E = 210e3` (N/mm), por eso el
solver "funcionaba" en tests y no en la app.

**Fix (reversible):** helpers en `materials.py`:

```
PA_PER_N_PER_MM2   = 1.0e6      # 1 N/mm = 1e6 Pa
KG_M3_TO_TONNE_MM3 = 1.0e-12    # 1 kg/m = 1e-12 tonne/mm

young_modulus_mm(E_pa)        # Pa     -> N/mm
density_mm(density_kg_m3)     # kg/m  -> tonne/mm
```

Aplicados en cada frontera material -> solver de malla:

| Archivo | Puntos |
|---|---|
| `core/generative_engine.py` | SIMPSolver + `thermal_load_vector` |
| `api.py` | `solve_fea`, `KratosSimpFEA`, `VendoredSIMP`, térmico |
| `core/cae_studies.py` | `solve_modal` (E **y** densidad) |
| `desktop/pipeline/controller.py` | térmico, `solve_fea`, `SIMPSolver` |
| `core/topo_problem.py` | dict de entrada al solver |

El `Material` sigue en SI (Pa): Kratos y los reportes no cambian.

**Verificación:** `tests/test_units_mm.py` (3): factores; ratio de compliance
Pa-crudo vs convertido = 1e6 exacto; el motor generativo entrega N/mm.
Medido en barra con 50 N: `1.67e-04` (bug) -> `1.67e+02` mJ (correcto).

---

## 3. BC-SHORTCUT  carga sobre nodos fijos (colapso silencioso)

**Síntoma/causa ya documentada** en `tests/test_generativa_flujo.py:367-370`:
si la carga cae sobre los mismos nodos que el apoyo, `u ~ 0`, la compliance es
~0 a cualquier magnitud, el optimizador solo minimiza volumen y colapsa a
vacío (isosuperficie degenerada). No había ningún chequeo: el usuario veía el
fallo de B-Rep sin saber por qué.

**Fix (reversible):** en `generative_engine.py`:

- `_load_on_fixed_fraction(force, fixed_dofs)`: fracción del módulo de fuerza
  que cae sobre DOFs fijos.
- `_check_load_on_fixed(...)`:
  - **> 99.9%** -> `ValueError` explícito ("La carga está aplicada sobre nodos
    fijos...").
  - **>= 90%** -> marca `load_on_fixed_dofs` en `_unsupported_conditions`
    (la UI lo muestra como "Condiciones degradadas").
  - solape **parcial** (p. ej. una cara que roza el apoyo) -> sin efecto.

Se invoca en `_map_conditions_to_problem` (condiciones reales) y en
`solve_simp` tras el merge `legacy_force` (BC clásicas).

**Verificación:** `tests/test_bc_shortcut.py` (3): -Z sobre base fija lanza;
solape 50% (-Y) no bloquea; fracción 1.0/0.0 en casos límite.

**Para volver atrás:** quitar los dos helpers y sus dos llamadas.

---

## 4. Verificación global

- `py_compile` backend OK; `tsc --noEmit` limpio; `vite build` OK
  (`dist/` regenerado; está en `.gitignore`, hay que reconstruir en cada PC).
- **Suite backend: 130 passed** (124 previos + tests nuevos). Sin regresiones.
- Tests nuevos: `test_volfrac_mode.py` (4), `test_units_mm.py` (3),
  `test_bc_shortcut.py` (3).

## 5. Pendientes reales

1. **`vendored/simp.py`** (ruta estructural, `api.py:1546`): no conoce
   `volfrac_mode` y conserva el piso absoluto `1e-12` en `_oc_update`
   (`vendored/simp.py:314`) que `core/topopt.py` ya subió a `np.finfo.tiny`.
   Alinear si se quiere el mismo comportamiento en estructural.
2. **Densidad/modal**: solo se convirtió `cae_studies.solve_modal`; revisar
   Kratos y cualquier otro consumidor de `Material.density` con geometría mm.
3. `topo_problem.py` sigue rechazando `VolfracMode.TOTAL_VOLUME` en
   `problem_to_solver_inputs` aunque `core.topopt` ya lo soporte; alinear
   cuando exista consumidor real de ese schema.
4. El guard BC cubre carga  fijación; no cubre "carga dentro de región
   preservada" (caso distinto, hoy no reproducido).