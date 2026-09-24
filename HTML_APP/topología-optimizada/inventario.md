# Inventario real — Topología Optimizada / HTML_APP

Auditoría directa del código (`backend/core`, `backend/api.py`, `backend/desktop/pipeline/controller.py`). El core es **compartido** entre `HTML_APP` y `Topologia_Optimizada` (vendorizado); solo 3 archivos difieren entre ambos: `generative_engine.py`, `topo_problem.py`, `topopt.py`. Esta auditoría usa el core de `HTML_APP` como referencia.

**Leyenda de estado:**
- ✅ **Implementado y conectado** — solver real, llamado desde `api.py` y/o `controller.py` (llega al usuario si hay UI)
- 🔶 **Implementado, sin UI** — solver real, conectado a API/pipeline, pero sin panel/ribbon que lo exponga
- ⚪ **Scaffold** — modelo de datos + validación, `execute()` lanza `NotImplementedError` a propósito
- 🔲 **Planteado/futuro** — sin código, solo mencionado en docs o roadmap

---

## 0. PREPARACIÓN / MODELO

| Herramienta | Estado | Evidencia |
|---|---|---|
| Import STEP (OCCT) | ✅ | `adapters/cad/step_adapter.py` |
| Selección por cara CAD | ✅ | `selection.py: FaceRegion` |
| Selección por plano | ✅ | `selection.py: PlaneRegion` |
| Selección por caja | ✅ | `selection.py: BoxRegion` |
| Selección por esfera | ✅ | `selection.py: SphereRegion` |
| Selección por cilindro | ✅ | `selection.py: CylinderRegion` |
| Selección por normal de cara | ✅ | `selection.py: NormalRegion` |
| Selección "todo" | ✅ | `selection.py: AllRegion` |
| Composición booleana (∪ ∩ −) | ✅ | `selection.py: CompositionRegion` |
| Material (mecánico) | ✅ | `materials.py: Material` (E, ν, ρ, σy) |
| Material (térmico, opcional) | ✅ | `materials.py`: `thermal_conductivity`, `specific_heat`, `thermal_expansion` — mismo objeto `Material`, no uno aparte |
| Design tree / árbol de piezas | ✅ | `desktop/ui_legacy/panels/design_tree.py` |
| Timeline por pieza | ✅ (parcial) | `desktop/ui_legacy/panels/timeline.py` — ramificación en paralelo por pieza sigue pendiente (confirmado en tus notas) |

---

## 1. OPTIMIZACIÓN

### 1.1 Jerarquía de nivel superior (correcta, como aclaraste)

```
Optimización estructural   ─┐
Optimización generativa     ├─ Tipos de estudio (menú aparte)
                             ┘
Carga / Fijación / Elasticidad / Región protegida / Obstrucción
                             → condiciones que consumen ambos estudios
```

### 1.2 Optimización estructural (SIMP)

| Elemento | Estado | Evidencia |
|---|---|---|
| Motor SIMP + OC (optimality criteria) | ✅ | `topopt.py: _oc_update()`, `optimize()` |
| Objetivo: minimizar compliance | ✅ | `topo_problem.py: ObjectiveType.MINIMIZE_COMPLIANCE` |
| Objetivo: minimizar volumen sujeto a compliance | ✅ | `topopt.py: optimize(objective="min_volume", compliance_limit=)` (bisección externa, solo oc/mma/gcmma); `topo_problem.py` lo propaga (`objective/compliance_limit`, FASE-1 2026-09-23); UI en `AdvancedOptPanel.tsx` |
| **Optimizador ESO / Level-Set** | ✅ | Implementados en `topopt.py` (ESO hard-kill + criterio stress, Level-Set Hamilton-Jacobi) y expuestos en `AdvancedOptPanel.tsx` (solo rama estructural/generativa core; el path vendored los rechaza explícito) |
| **Múltiples casos de carga (multicarga ponderada)** | ✅ — *corrección al chat* | `topopt.py: set_loads()` implementa `c(ρ)=Σ wᵢ·uᵢᵀKuᵢ`; agrupación real por `load_case_id` en `controller.py: _load_case_vectors()`; llega hasta `api.py` y `generative_engine.py`. **Esto ya está operativo de punta a punta**, no es una prioridad futura como planteaba el chat — lo que falta confirmar es si el panel de condiciones ya permite asignar `load_case_id` desde la UI |
| Fracción de volumen, iteraciones, penalización, radio de filtro, tolerancia | ✅ | `TopOptParameters` |
| `volfrac_mode` (dominio activo vs. volumen total) | ✅ | `topo_problem.py: VolfracMode` + propagación `objective/compliance_limit` (FASE-1 2026-09-23); vendored acepta `active_domain\|total_volume` |
| Regiones preservadas / vacías | ✅ | `topopt.py: set_preserved_elements()`, `set_void_elements()` |
| Halo de protección alrededor de nodos de carga | ✅ | `topopt.py:640-649` deriva `h_element` de volumen medio (independiente de `filter_radius`); corregido, ver docstring |
| MMA / GCMMA (propios, numpy) | ✅ | `topopt.py: _mma_update/_gcmma_update` (Svanberg; Kratos 10.4 no expone optimizador standalone); expuestos en UI; el path vendored rechaza gcmma explícito (`test_gcmma.py`) |
| Restricción de tensión máxima (von Mises) | 🔶 | Sin restricción local implementada (el schema la rechaza explícito por decisión, FASE-1); ESO-criterio `stress` es ranking evolutivo, no restricción; `factor_of_safety` existe como postproceso (`cae_studies.py:504`, tarjeta `SafetyCard.tsx`) |
| Manufacturing constraints (overhang, espesor mínimo, simetría) | ✅ | Penalización overhang activa + `overhang_report` (diagnóstico), espesor mínimo, planos de simetría — todo en `AdvancedOptPanel.tsx` + core |

### 1.3 Optimización generativa

| Elemento | Estado | Evidencia |
|---|---|---|
| Escenario A (optimizar pieza existente) | ✅ | `generative_engine.py`, rama `scenario == "A"` |
| Escenario B (generar conexión entre 2 piezas) | ✅ | `generative_engine.py: BridgeMesh`, rama `scenario == "B"` |
| Parámetros: resolución, padding | ✅ | `generative_engine.py` (`resolution`, `padding`) |
| Multicarga en generativo | ✅ | `generative_engine.py:648` también llama `solver.set_loads()` |

### 1.4 Condiciones (compartidas entre ambos estudios)

| Condición | Estado | Evidencia |
|---|---|---|
| Carga (puntual/distribuida/presión, dirección, sentido, indeterminado) | ✅ | `conditions.py: LoadCondition`, `LoadOrientation`, `LoadSense` |
| Fijación (Fixed/Pinned/Roller/Symmetry, 6 DOF) | ✅ | `topo_problem.py: BCType` + tu `conditions.py` |
| Elasticidad (flexión, cara, rango) | ✅ | `conditions.py: ElasticityCondition` |
| Región protegida | ✅ | `conditions.py: ProtectedRegion` |
| Obstrucción (cuerpo + offset) | ✅ | `conditions.py: ObstructionCondition` |
| Dominio de diseño explícito como herramienta de UI | 🔲 | Existe a nivel de datos (`RegionRole` en `topo_problem.py`), no como herramienta independiente de la ribbon |

---

## 2. ANÁLISIS

Hallazgo importante que corrige al chat de ChatGPT: **tanto Térmico como Modal tienen el mismo nivel real de madurez** — solver matemático completo y conectado a `api.py`/`controller.py`, pero **sin ningún panel de UI** que los exponga (no aparecen ni en `study_panel.py` ni en el frontend React). El chat decía que Térmico está "operativo" y Modal "pendiente"; en el código ambos están en el mismo estado: 🔶.

| Estudio | Estado | Evidencia |
|---|---|---|
| Análisis estructural estático (Tet4 + Kratos) | ✅ | `cae_studies.py: StructuralAnalysis`, conectado y con UI (`study_panel.py`) |
| Análisis térmico estacionario | 🔶 | `thermal.py: solve_thermal_study()` completo (temp impuesta, flujo, convección); `cae_studies.py: ThermalAnalysis.execute_on_mesh()` lo invoca; llamado desde `api.py:689` y `controller.py:1446` — **pero sin UI** |
| Análisis modal (autovalores) | 🔶 — *corrección al chat* | `fea.py: solve_modal()` completo (ensambla K y M, `scipy.sparse.linalg.eigsh`, filtro de ventana de frecuencia); `ModalAnalysis.execute_on_mesh()` lo invoca; llamado desde `api.py:720` y `controller.py:1475`. **No es "arquitectura preparada sin solver" — el solver ya existe y corre.** Solo falta exponerlo |
| Resultados: von Mises, tensión principal, deformación | 🔶 | Presentes en el pipeline de `StructuralAnalysis`, visualización en `desktop/ui_legacy/panels/results.py` — confirmar cobertura completa de mapas de tensión |
| Factor de seguridad como herramienta de postproceso | ✅ | `cae_studies.py:504 factor_of_safety` (σy/σ_vM por entidad) + tarjeta `SafetyCard.tsx` — postproceso, no restricción local |
| Comparación de resultados (original vs. optimizado, o A vs B vs C) | ✅ | `CompareTable` en flujo principal (`RightPanel.tsx`) — verificar cobertura A/B/C |
| `execute()` sin malla para Térmico/Modal | ⚪ (intencional) | Ambos lanzan `StudyNotImplementedError` a propósito cuando se invoca sin mesh — es el contrato "explícito, nunca fallback silencioso" que ya usás en el resto del proyecto |

---

## 3. MALLADO Y RECONSTRUCCIÓN

| Herramienta | Estado | Evidencia |
|---|---|---|
| Mallado volumétrico Tet4 (Gmsh + OCCT) | ✅ | `meshing.py: GmshTet4Mesher` |
| Mallador provisional (voxelización + Kuhn) | ✅ (fallback explícito) | `meshing.py: ProvisionalTet4Mesher` — fallback opt-in con metadata `face_correspondence=order-fallback`; face_id no propagado en este path (P2 conocido, warning a UI) |
| Mallado adaptativo | ✅ | `meshing.py: GmshTet4Mesher.generate_adaptive_mesh()` — refinamiento por campo escalar |
| Hex8 | — | Soporte honesto en `fea.py:798` (`solve_fea_hex8`, sin dependencias nuevas) |
| Tet10 | ✅ | `fea.py: solve_fea_tet10` por subdivisión en 8 Tet4 + interpolación (documentado, sin silencios) |
| Correspondencia de caras OCCT↔Gmsh | ✅ parcial | `face_correspondence.py: FaceSignature` conectado cuando hay `cq_shape` (`meshing.py:396-398,574-576`, metadata `deterministic`); path sin shape sigue en order-fallback con warning explícito + `warnings` en salida del problema |
| Mapeo de condiciones de contorno a caras de malla | ✅ | `boundary.py: BoundaryConditionMapper`, `MappedFace` |
| Mapeo de condiciones de contorno a caras de malla | ✅ | `boundary.py: BoundaryConditionMapper`, `MappedFace` |
| Extracción de superficie (Marching Tetrahedra) | ✅ | `cad_reconstruction.py: MarchingTetrahedraExtractor` |
| Extractor "dummy" (testing) | ✅ (por diseño) | `cad_reconstruction.py: DummySurfaceExtractor` — para tests sin dependencias pesadas |
| Suavizado de malla | ✅ | `cad_reconstruction.py: MeshSmoother` |
| Reparación de agujeros | ✅ | `cad_reconstruction.py: MeshHoleFiller` |
| Ajuste B-Rep (fitting real, OCCT) | ✅ | `cad_reconstruction.py: OCPBRepFitter` |
| Ajuste B-Rep "dummy" (testing) | ✅ (por diseño) | `cad_reconstruction.py: DummyBRepFitter` |
| Pipeline completo malla→B-Rep | ✅ | `cad_reconstruction.py: ReconstructionPipeline` |
| Remallado (remesh) | ✅ | `uniform_remesh` en `cad_reconstruction.py:906` (Fase 5a, opt-in) |
| Decimación / reducción de malla | ✅ | Cubierta en el pipeline (Fase 5a + `brep_decimated_from` en metadata) |
| Reparación avanzada (non-manifold, self-intersections, shells abiertos) | 🔶 | `MeshHoleFiller` + cierre forzado (`CIERRE-FORZADO`) + `DOMAIN-CUT` cubren agujeros/cortes; non-manifold/self-intersections genéricos siguen sin cobertura |

---

## 4. Motores — tabla resumen (corregida)

| Motor | Estado real | Nota |
|---|---|---|
| SIMP (OC) | ✅ Operativo | Piso de bisección relativo a máquina (`OC-BISECTION-FLOOR`); espejado en vendored (FASE-2) |
| ESO / Level-Set | ✅ Operativos | Path core + vendored acepta `oc/mma/eso/level_set` (`vendored/simp.py:525`); solo `gcmma` se rechaza explícito en vendored (temprano en `api.runSimpLoop`) |
| Multicarga ponderada | ✅ Operativo | De punta a punta + `load_case_id` asignable en UI (`ToolParamsPanel.tsx`) |
| MMA/GCMMA (propios) | ✅ Operativos | Implementación numpy propia (Kratos no expone optimizador standalone) |
| FEA estructural (Tet4/Kratos) | ✅ Operativo | Con UI; Kratos con material en mm (FASE-3 2026-09-23) |
| FEA térmico | 🔶 Backend listo, UI en panel V2 | `V2Panel.tsx` (oculto: `V2_ENABLED=false`); acoplado térmico one-way expuesto en panel Avanzado |
| FEA modal | 🔶 Backend listo, UI en panel V2 | Igual que térmico; animación de modos como postproceso (`cae_studies.py`) |
| Mallado Gmsh Tet4 + adaptativo | ✅ Operativo | — |
| Selección geométrica (`NodeSelectionEngine`) | ✅ Operativo | 7 tipos de región + composición booleana |
| Reconstrucción B-Rep | ✅ Operativo | Con fallback dummy para tests |
| Diseño generativo (A y B) | ✅ Operativo | Incluye multicarga |

---

## 5. Actualización 2026-09-23 (FASE-5.1): lo que cambió desde la auditoría

- **Multicarga**: `load_case_id` ya asignable desde la UI (`ToolParamsPanel.tsx`) — prioridad cerrada.
- **Térmico/Modal**: backend listo + panel V2 funcional pero oculto (`V2_ENABLED=false`); falta decidir si se exponen en el flujo principal.
- **Fabricación, MMA/GCMMA, ESO/Level-Set, Tet10, remesh, FoS, comparación**: todos implementados y (salvo V2) expuestos en UI — la lectura vieja del chat quedó obsoleta.
- **Cierres 2026-09-23 (plan vigente `plan.md`)**: schema `topo_problem` acepta `TOTAL_VOLUME` + propaga objetivo (FASE-1); vendored espeja piso OC + rechaza `volfrac_mode` explícito (FASE-2); Kratos convierte material a mm (FASE-3); guard carga-en-preservada como degradada sin error duro (FASE-4).
- **Pendiente real restante**: restricción local de tensión (von Mises), remallado adaptativo por campo fuera de Gmsh, exponer Térmico/Modal en UI principal, reparación non-manifold genérica.
