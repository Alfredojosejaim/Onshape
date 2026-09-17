# Sesión 2026-09-17 — Envelope: preserve/keep-out no conservaban y el resultado era un "bulto cuadrado"

**Proyecto:** `HTML_APP/topología-optimizada`
**Fecha:** 17-sep-2026
**Alcance:** `backend/core/generative_engine.py`, `backend/core/topopt.py`.
**Relacionado:** `sesion-2026-09-17-generativa-threshold-muerte-backend.md`
(§5.5 "Degradación BC en envelope... pendiente de diseño de mapeo en caja",
ahora resuelto), `sesion-2026-09-16-bspline-real-envelope-skin.md`.

Reporte del usuario: en `design_space = envelope` las herramientas **Preservada**
y **Keep-out** "no hacían nada" y el sólido resultante parecía **una caja /
bulto cuadrado** alrededor de las zonas marcadas, en vez de una estructura
orgánica que conservara las caras seleccionadas.

---

## 1. Diagnóstico (FASE A/B)

Reproducción headless con `cono.step` (voxel envelope ≈ 4.11 mm, 56304 tets) y
cargas/fijación/preservada/keep-out por cara. Dos defectos **encadenados**:

### 1a. Mapeo por tolerancia -> losa axis-aligned gruesa (ENV-BAND)

Con envelope la malla no es la del modelo (`_surface_matches_mesh=False`), así
que las caras se mapeaban por distancia con tolerancia `1.5·voxel`
(`generative_engine.py`) y luego se marcaba **todo elemento que toca cualquier
nodo** dentro de esa tolerancia (`_protected_elements` / `_void_elements`).
Medido antes del fix (cano, una cara por herramienta):

| cara | elementos marcados |
|---|---|
| lateral (área 10434) | 19270 (**34.2%** del dominio) |
| base | 9709 (17.2%) |
| tapa | 4103 (7.3%) |

Cada cara se convertía en una **losa de ~2-3 voxels**. Al marcar lateral +
base + tapa, ~44% del dominio quedaba fijado; el optimizador no tenía volumen
libre y el único material visible eran esos slabs alineados a la rejilla ->
la "caja". El halo topológico de carga/fijación multiplicaba el efecto.

### 1b. Colapso del volumen por el piso OC absoluto

Aun con dominio libre, el optimizador **no respetaba `volfrac`**. Evidencia
instrumentando la bisección de `_oc_update` (`core/topopt.py`):

```
OC target_vol=155447 got=79663.9 ratio=0.512   (iter 1)
OC target_vol=155447 got=17632.3 ratio=0.113   (iter 2)
...
l1=0 l2=7.9e-25  ratio_xmin=0.0004   <- dc ~ 1e-19
```

La fórmula OC `x·sqrt(|dc| / max(|mid·dv|, 1e-12))` usaba un **piso absoluto
1e-12**. Con mallas rígidas (compliance ~1e-6) y el filtro de sensibilidad, `dc`
queda ~1e-14..1e-19; el piso impedía que `mid` (multiplicador de Lagrange)
bajara lo suficiente y la bisección devolvía volumen muy por debajo del
objetivo. El resultado: densidades ~`rho_min` en todo el dominio activo y el
sólido era **solo los slabs preservados** -> el "bulto cuadrado" era, en gran
parte, el material forzado, no el optimizado.

---

## 2. Fix (FASE D)

### 2a. `generative_engine.py` — ENV-BAND (capa fina por lado)

Nuevos helpers: `_env_band`, `_point_inside_shape`, `_band_once`,
`_band_elements_for_faces`, `_bc_face_indices`, `_halo_layer_envelope`
(+ `_env_resolution`, `_band_cache`).

Para envelope/bridge se clasifica el **centroide** de cada elemento por:

- distancia a la cara CAD `<= banda` (~`0.75·voxel`, con reintento `2×` por
  cara si la rejilla queda desplazada), y
- lado respecto al sólido CAD (`Shape.isInside`):
  - `side="inside"` (Preservada): material del sólido detrás de la cara ->
    la cara se conserva.
  - `side="outside"` (Keep-out): volumen libre/cavidad junto a la cara ->
    se vacía (paso de tornillo, holgura).

El halo de cargas/fijaciones usa la misma capa `inside`
(`_halo_layer_envelope`, `_halo_mode="band_1voxel_inside"`); los nodos BC sin
cara (fallback de extremo de eje) conservan el halo topológico clásico. El modo
`part` no cambia (`_surface_matches_mesh=True`).

Efecto medido tras el fix (mismas caras): lateral 2613 (4.6%), base 1133
(2.0%), tapa 430 (0.8%); keep-out 3514/2133/804.

### 2b. `topopt.py` — OC-BISECTION-FLOOR (piso relativo)

El piso `1e-12` pasa a `np.finfo(np.float64).tiny`. Restaura la invariancia de
escala del OC (`dc` y `λ` escalan juntos): la bisección puede alcanzar el
volumen objetivo aunque las sensibilidades sean diminutas. Solo afecta al
denominador de la bisección; no cambia la matemática cuando `dc` es O(1).

---

## 3. Verificación (FASE E)

Run headless `cono.step`, envelope, load=tapa / supp=base / preservada=lateral
/ keep-out=tapa, volfrac 0.35, 6 iteraciones:

| métrica | antes | después |
|---|---|---|
| `volume_fraction_history` | 0.35 → 0.179 → 0.024 | **0.35 constante** |
| `final_volume_fraction` | 0.022 | **0.35** |
| `_preserved_elements` | 24587 (43.7%) | 3878 (6.9%) |
| `_halo_mode` | topological_1layer (losa) | **band_1voxel_inside** |
| `_unsupported_conditions` | [] | [] |
| `reconstruction.stage` | (surface_mesh en el caso expuesto) | **brep_solid** |

Tests backend (sin cambios de contrato): `test_keepout_faces`,
`test_design_space_halo`, `test_generativa_flujo`, `test_generative_organic`,
`test_gcmma` = **24 passed**.

Nota: no se agregó test específico (pedido explícito del usuario); queda como
pendiente §4.

---

## 4. Pendientes reales

1. Test de regresión de envelope con preserve/keep-out + piso OC (reproduce
   §1: volumen objetivo mantenido, cada cara < 15% del dominio, `brep_solid`).
   Verificado manualmente en esta sesión pero no versionado.
2. Keep-out de cavidades mayores que ~1 voxel: la capa `outside` vacía el
   contorno de la cara, no necesariamente todo el hueco si su radio supera la
   banda. Evaluar propagación del componente libre conectado (flood-fill)
   manteniendo acotado el costo.
3. `_env_band` es `0.75·voxel`; exponerlo/afinarlo si el usuario reporta capas
   demasiado finas o gruesas en mallas muy no conformes.
4. Confirmar que el piso OC relativo no altera `min_volume`/MMA/GCMMA (usan
   pisos propios `vt`/`fscale`): la suite pasó, pero conviene un barrido de
   volfrac alto (0.6-0.8) en envelope.
