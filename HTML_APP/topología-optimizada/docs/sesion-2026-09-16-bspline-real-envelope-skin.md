# Acta de sesión — 16-sep-2026: B-spline real por parches, skin de envelope y endurecimiento

**Proyecto:** `HTML_APP/topología-optimizada`
**Alcance:** `backend/core/cad_reconstruction.py`, `backend/core/generative_engine.py`,
`backend/api.py`, `backend/app_desktop.py`, tests nuevos. `vendored/` y el
solver SIMP **sin tocar**.
**Responde a:** reportes del usuario sobre el diseño generativo (regiones
preservadas, keep-out, "no cierra STEP", "el B-spline sigue facetado").

---

## 1. B-spline REAL por parches — IMPLEMENTADO Y PARCIAL

`OCPBSplineFitter` ahora hace reverse-engineering por parches
(`_fit_patches_solid`):

1. **Segmentación** BFS compacto por desviación angular respecto a la
   normal de la **semilla** (no vecino-a-vecino: eso fusionaba toda una
   superficie cerrada en una región sin borde, imposible de rellenar).
   `region_angle_deg=35`, `min_region_faces=3`, `max_region_faces=600`.
2. Cada región se reemplaza por **una cara B-spline suave** con
   `BRepOffsetAPI_MakeFilling` (multi-bucle = soporta huecos).
3. Reensambla, cose, extrae cáscara y construye sólido.

**Guardas (nunca geometría inválida ni silencio):**
- `BRepCheck_Analyzer` sobre el sólido.
- **VOL-GUARD**: el volumen debe conservarse (75%–133%). Atrapa sólidos
  "válidos" pero con volumen ~0 (parches plegados).
- **ALL-OR-NOTHING**: si alguna región no se pudo parchear, se descarta el
  ajuste completo (mezclar parches con triángulos deja costuras abiertas).
- Todo se reporta en `metadata`: `bspline_fit`, `bspline_regions*`,
  `bspline_volume_ratio`, `bspline_fit_stats`.

**HECHO medido:** esfera de 1520 triángulos → **30 caras B-spline reales,
válidas, volumen conservado** (test `test_bspline_patch_fit.py`).

**LÍMITE HONESTO:** en el isosuperficie real del envelope (captura: 2461 v /
5296 t) cae a `fallback_mixed`: de 318 regiones, 166 son diminutas (1–2
caras) y ~15 fallan el relleno. La causa raíz es el isosuperficie
fragmentado/ruidoso del SIMP, no la reconstrucción. Aplicarlo a resultados
TO requiere una fase dedicada de limpieza/segmentación del isosuperficie.

**Alternativas probadas y DESCARTADAS (medidas):**
- Reemplazo de superficie por región + wire original (`MakeFace` +
  `ShapeFix_Face`): válido por región, pero reducción pobre (744 vs 30) y
  costuras abiertas (316 aristas libres).
- Cerrar con `ShapeFix_Shell`: **se cuelga** en mallas grandes.

## 2. Envelope: bug de isosuperficie ABIERTA — CORREGIDO

El material del envelope crecía **hasta la pared** de la caja de diseño, el
isosuperficie quedaba abierto y la reconstrucción B-Rep fallaba:
- 8 iters → cerraba pero fragmentado (77 cáscaras).
- 30 iters → `brep_error="isosuperficie abierta/degenerada"` → **ningún STEP**.

**Fix (`ENV-SKIN`):** capa de vacío en la pared del dominio (`void_skin`,
elementos que tocan la bbox forzados a `xmin`). Ahora 8 y 30 iters →
`stage=brep_solid` cerrado. Reportado en `_design_space.void_skin_elements`.

## 3. Endurecimientos relacionados (misma sesión)

- **Timeout del puente** (`BRIDGE-TIMEOUTS`, `app_desktop.py`): métodos
  científicos bloqueantes (`registerReconstruction`, `exportStep`,
  `generateMesh`, `importStep`, `getSurfaceMesh`, `remeshMesh`) usan 1200 s;
  el polling y el resto siguen en 120 s. Era la causa del
  `TimeoutError: timed out` en STEP grandes.
- **Tope de triángulos pre-fit** (`BREPCAP`, `max_brep_triangles=6000`):
  diezma antes del cosido OCP; un isosuperficie de envelope (24k tris →
  STEP 29 MB) tardaba 106 s y superaba el puente.
- **Envelope orgánico**: filtro auto a `1.5×voxel` (evita checkerboard) y
  `heaviside_eta` propagado desde la API.
- **Mapeo cara→nodo FSE-FIRST** y **keep-out por caras** (`obstruction` con
  `faces`), con reporte `_condition_mapping` visible en la UI.

## 4. Cómo quedó el flujo (HECHO)

`brep_style="bspline"` intenta el ajuste por parches; si no puede
(`fallback_mixed` / `fallback_volume` / `fallback_invalid`), cae a la cadena
histórica unify→restriction→continuidad y exporta igual el STEP facetado.
**Nunca se exporta geometría inválida ni se oculta el motivo.**

## 5. Verificación

- `python -m pytest backend/tests -q`: **93 passed**, 3 warnings.
- `npm run lint` (`tsc --noEmit`): OK. `npm run build` (Vite): OK.
- Tests nuevos: `test_bspline_patch_fit.py` (3), `test_generative_organic.py`
  (envelope cierra con skin), `test_keepout_faces.py`,
  `test_generative_step_roundtrip.py`, `test_mock_fallback_contract.py`.

## 6. Pendiente real (no cerrado)

- Fase dedicada para aplicar B-spline a isosuperficies TO ruidosos
  (limpieza/segmentación del isosuperficie o mayor suavizado del campo SIMP).
- El envelope con skin subió el tiempo de corrida (~250–300 s en 30 iters).
