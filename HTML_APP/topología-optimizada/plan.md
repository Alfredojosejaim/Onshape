# Plan de ejecución — huecos del inventario

Basado en `inventario_motores_herramientas.md`. Orden por dependencia real y relación riesgo/beneficio, no por orden en que aparecen en el inventario. Sigue tu flujo: Claude arma diff/spec → vos aprobás → Muse Spark ejecuta vía ECC (`/plan` → aprobar → TDD → `/code-review` → `/build-fix`).

---

## Fase 0 — Higiene inmediata (antes que nada, riesgo casi cero)

**0.1 Ocultar/deshabilitar ESO y Level-Set en cualquier selector de UI**
Si `OptimizerType.ESO` / `LEVEL_SET` aparecen como opciones elegibles en algún combo, eso viola tu propio principio de "no fallback silencioso": el usuario elegiría un motor que no existe y probablemente caería en SIMP sin avisar, o rompería. Fix: restringir el combo a `SIMP` únicamente, o si ya están ocultos, no hace falta tocar nada — solo confirmar.
- Riesgo: nulo. Candidato ideal para Muse Spark sin supervisión estrecha.
- No depende de nada.

**0.2 Confirmar que `ObjectiveType.MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE` no es seleccionable en UI**
Mismo motivo: el solver la rechaza explícitamente (`topo_problem.py:362-365`), así que si es elegible en algún panel, es una trampa silenciosa disfrazada de opción válida.
- Riesgo: nulo.

---

## Fase 1 — Exponer lo que YA funciona en backend (mayor ROI, menor riesgo)

Estos tres ítems no requieren tocar ningún solver: el motor ya está validado y corre. El trabajo es UI + wiring, no matemática.

**1.1 Panel de estudio Térmico**
- Agregar `ThermalAnalysis` a `study_panel.py` (mismo patrón que `TopologyOptimizationStudy`)
- Exponer `ThermalBoundary` (temperatura / flujo / convección) como condición seleccionable, reusando `NodeSelectionEngine` que ya tenés
- Conectar al `execute_on_mesh()` que ya existe en `cae_studies.py`
- Resultado esperado: temperatura nodal + flujo por elemento visibles en `results.py`

**1.2 Panel de estudio Modal**
- Mismo patrón: agregar `ModalAnalysis` a `study_panel.py`
- UI mínima: cantidad de modos, frecuencia mín/máx (`ModalParameters` ya existe)
- Requiere que el usuario defina al menos una fijación (ya validado en `validate_with_message()` — exige constraints para evitar K singular)
- Resultado esperado: lista de frecuencias + posibilidad futura de animar modo (la animación queda para después, no bloquea esta fase)

**1.3 UI de `load_case_id` en el panel de Carga**
- Agregar campo opcional "caso de carga" (agrupador) + peso relativo a `LoadCondition`
- Sin este campo, todas las cargas caen en el mismo caso (`__single_{n}` en `controller.py`) — comportamiento actual, no rompe nada, es aditivo
- Esto activa multicarga real sin tocar el solver

**Orden interno sugerido dentro de la fase:** 1.3 primero (más chico, un solo campo nuevo), después 1.1 y 1.2 en paralelo si querés repartir entre sesiones — no dependen entre sí.

**Riesgo:** bajo-medio. Es el primer tramo de esta fase donde recomendaría diff revisado por vos antes de aplicar (no delegación ciega a Muse Spark), porque toca paneles con más superficie de UI que los bugs P1-P4.

---

## Fase 2 — Bugs conocidos (ya tenés el orden, lo mantengo sin cambios)

Tu cadena ya establecida: **P1 → P2 → P4 → P3**

- **P1** — Correspondencia de tags OCCT↔Gmsh (`face_correspondence.py` ya tiene el mecanismo de `FaceSignature`; falta conectarlo en `GmshTet4Mesher._extract_all_surface_elements()`)
- **P2** — Propagación de `face_id` a triángulos de frontera (depende de P1 resuelto)
- **P4** — Halo derivado de `filter_radius` en vez de tamaño de elemento real (independiente, buen candidato de bajo riesgo para probar el pipeline ECC)
- **P3** — Semántica de `volfrac_mode` + detección de infeasibility explícita

No repito el detalle porque ya está fijado; solo lo ubico en la secuencia general porque P1/P2 bloquean que la Fase 1.1 (térmico) tenga distribución de flujo confiable si algún día usás caras para condiciones de contorno térmicas por flujo — ahí sí hay dependencia cruzada: si vas a exponer `HEAT_FLUX`/`CONVECTION` en 1.1 con selección por cara, conviene tener P1 resuelto antes, porque ambos dependen del mismo mapeo cara↔malla. Si en 1.1 solo usás `TEMPERATURE` (por nodos) al principio, podés adelantar la Fase 1 sin esperar P1.

---

## Fase 3 — Postproceso nuevo (autocontenido, sin dependencias del solver)

**3.1 Factor de seguridad**
- Función derivada: `FoS = yield_strength / von_mises` por elemento
- Input: resultado de `StructuralAnalysis` (ya tenés von Mises) + `Material.yield_strength` (ya existe)
- Visualización: mapa de zonas bajo el mínimo, reusando el mismo pipeline de color que ya usás para tensión
- No toca ningún solver, es post-cálculo puro

**3.2 Comparación de resultados (original vs. optimizado)**
- Estructura de datos nueva: snapshot de {masa, volumen, compliance, desplazamiento máx, FoS mín} por estudio
- UI: tabla comparativa simple primero (A vs B), sin animaciones ni gráficos todavía
- Extensible después a A vs B vs C

**Riesgo:** bajo. Buenos candidatos para Muse Spark con TDD, ninguno toca código de solver existente.

---

## Fase 4 — MMA/GCMMA (mayor esfuerzo, ya está en tu roadmap)

- Conectar `KratosOptimizationApplication` (MMA/GCMMA) al núcleo SIMP, replicando el patrón dual-backend que ya usás en FEA (`fea_solver` inyectable en `VendoredSIMP`, visto en `api.py: _simp_loop`)
- Esto es lo único de esta lista que yo trataría con diff-first estricto y revisión tuya en cada paso, no delegación amplia a Muse Spark — toca el núcleo del optimizador
- Depende de: nada técnicamente bloqueante de fases anteriores, pero tiene sentido hacerlo después de estabilizar Fase 1-3 para no mezclar cambios de UI con cambios de solver en la misma ventana de trabajo

---

## Fase 5 — Herramientas de malla nuevas (remesh, decimación, reparación avanzada)

- Remallado, decimación y reparación no-manifold/self-intersections no existen aún
- Recomendación: no arrancar esta fase hasta que P1/P2 estén cerrados — cualquier herramienta nueva de malla que dependa de correspondencia cara↔malla hereda el mismo riesgo que ya tenés diagnosticado
- Prioridad relativa baja: no bloquea ningún flujo actual, es calidad de geometría de salida

---

## Fase 6 — Largo plazo / sin código todavía

- Restricción de tensión máxima (von Mises) en el optimizador
- Manufacturing constraints (overhang, espesor mínimo, dirección de impresión, etc.)
- Acoplamiento térmico-estructural
- ESO / Level-Set como motores reales (hoy son enum vacío)
- Animación de modos (depende de Fase 1.2)

Sin fecha ni orden interno todavía — quedan documentados para no perderlos, pero no entran en el plan activo hasta cerrar Fases 1-4.

---

## Resumen de secuencia recomendada

```
Fase 0 (higiene)
   ↓
Fase 1.3 (UI load_case_id) ──┐
Fase 1.1 (panel térmico)      ├─ pueden repartirse, no dependen entre sí
Fase 1.2 (panel modal)       ─┘
   ↓
Fase 2 (P1 → P2 → P4 → P3)   — ya en curso según tu cadena existente
   ↓
Fase 3 (FoS + comparación)   — puede adelantarse en paralelo a Fase 2, es independiente
   ↓
Fase 4 (MMA/GCMMA)
   ↓
Fase 5 (malla nueva)
   ↓
Fase 6 (futuro sin código)
```

Nota: Fase 3 es realmente paralela a Fase 2 — no hay dependencia técnica entre postproceso nuevo y los bugs de mallado. Si en algún momento querés repartir carga entre dos sesiones de trabajo, esa es la pareja natural para hacerlo en simultáneo.
