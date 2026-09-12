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
| Design tree / árbol de piezas | ✅ | `desktop/ui/panels/design_tree.py` |
| Timeline por pieza | ✅ (parcial) | `desktop/ui/panels/timeline.py` — ramificación en paralelo por pieza sigue pendiente (confirmado en tus notas) |

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
| Objetivo: minimizar volumen sujeto a compliance | ⚪ | Enum existe (`MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE`), pero el solver **rechaza explícitamente** cualquier objetivo ≠ `MINIMIZE_COMPLIANCE` (línea 362-365 de `topo_problem.py`) |
| **Optimizador ESO / Level-Set** | 🔲 | `optimization_studies.py: OptimizerType` declara `ESO` y `LEVEL_SET`, pero no existe implementación en `topopt.py` — es un enum sin motor detrás |
| **Múltiples casos de carga (multicarga ponderada)** | ✅ — *corrección al chat* | `topopt.py: set_loads()` implementa `c(ρ)=Σ wᵢ·uᵢᵀKuᵢ`; agrupación real por `load_case_id` en `controller.py: _load_case_vectors()`; llega hasta `api.py` y `generative_engine.py`. **Esto ya está operativo de punta a punta**, no es una prioridad futura como planteaba el chat — lo que falta confirmar es si el panel de condiciones ya permite asignar `load_case_id` desde la UI |
| Fracción de volumen, iteraciones, penalización, radio de filtro, tolerancia | ✅ | `TopOptParameters` |
| `volfrac_mode` (dominio activo vs. volumen total) | ⚪ (P3 de tu lista) | `topo_problem.py: VolfracMode` — modelo existe, semántica de infeasibility explícita pendiente según tus notas |
| Regiones preservadas / vacías | ✅ | `topopt.py: set_preserved_elements()`, `set_void_elements()` |
| Halo de protección alrededor de nodos de carga | ⚪ (bug P4) | `protect_elements_near_nodes()` — implementado pero con el bug conocido (usa `filter_radius` en vez de tamaño de elemento real) |
| MMA / GCMMA (Kratos OptimizationApplication) | 🔲 | Instalado según tus notas, pero **no hay ninguna llamada a ese módulo** en `topopt.py` ni `kratos_adapter.py` — sigue siendo trabajo de integración pendiente |
| Restricción de tensión máxima (von Mises) | 🔲 | No hay código; el propio repo lo documenta como extensión avanzada no soportada |
| Manufacturing constraints (overhang, espesor mínimo, etc.) | 🔲 | No existe en el core |

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
| Resultados: von Mises, tensión principal, deformación | 🔶 | Presentes en el pipeline de `StructuralAnalysis`, visualización en `desktop/ui/panels/results.py` — confirmar cobertura completa de mapas de tensión |
| Factor de seguridad como herramienta de postproceso | 🔲 | No hay clase/función dedicada; sería cálculo derivado (σy / σ_von_Mises) no implementado aún |
| Comparación de resultados (original vs. optimizado, o A vs B vs C) | 🔲 | No existe en el core |
| `execute()` sin malla para Térmico/Modal | ⚪ (intencional) | Ambos lanzan `StudyNotImplementedError` a propósito cuando se invoca sin mesh — es el contrato "explícito, nunca fallback silencioso" que ya usás en el resto del proyecto |

---

## 3. MALLADO Y RECONSTRUCCIÓN

| Herramienta | Estado | Evidencia |
|---|---|---|
| Mallado volumétrico Tet4 (Gmsh + OCCT) | ✅ | `meshing.py: GmshTet4Mesher` |
| Mallador provisional (voxelización + Kuhn) | ✅ | `meshing.py: ProvisionalTet4Mesher` — usado como fallback/test, según tus notas causa el bug P2 (face_id no propagado) |
| Mallado adaptativo | ✅ | `meshing.py: GmshTet4Mesher.generate_adaptive_mesh()` — refinamiento por campo escalar |
| Hex8 | — | Confirmado removido, no queda clase en `meshing.py` (coincide con tus notas) |
| Tet10 | 🔲 | No hay clase — roadmap-disabled, coincide con tus notas |
| Correspondencia de caras OCCT↔Gmsh | ⚪ (bug P1) | `face_correspondence.py: FaceSignature` — existe el mecanismo de matching geométrico, es justamente el que hay que terminar de conectar en `GmshTet4Mesher._extract_all_surface_elements()` |
| Mapeo de condiciones de contorno a caras de malla | ✅ | `boundary.py: BoundaryConditionMapper`, `MappedFace` |
| Extracción de superficie (Marching Tetrahedra) | ✅ | `cad_reconstruction.py: MarchingTetrahedraExtractor` |
| Extractor "dummy" (testing) | ✅ (por diseño) | `cad_reconstruction.py: DummySurfaceExtractor` — para tests sin dependencias pesadas |
| Suavizado de malla | ✅ | `cad_reconstruction.py: MeshSmoother` |
| Reparación de agujeros | ✅ | `cad_reconstruction.py: MeshHoleFiller` |
| Ajuste B-Rep (fitting real, OCCT) | ✅ | `cad_reconstruction.py: OCPBRepFitter` |
| Ajuste B-Rep "dummy" (testing) | ✅ (por diseño) | `cad_reconstruction.py: DummyBRepFitter` |
| Pipeline completo malla→B-Rep | ✅ | `cad_reconstruction.py: ReconstructionPipeline` |
| Remallado (remesh) | 🔲 | No existe como herramienta independiente |
| Decimación / reducción de malla | 🔲 | No existe |
| Reparación avanzada (non-manifold, self-intersections, shells abiertos) | 🔲 | `MeshHoleFiller` cubre agujeros; el resto no está |

---

## 4. Motores — tabla resumen (corregida)

| Motor | Estado real | Nota |
|---|---|---|
| SIMP (OC) | ✅ Operativo | Único optimizador con motor real; ESO/Level-Set son enum sin implementación |
| Multicarga ponderada | ✅ Operativo | Contradice al chat — no es un "futuro", ya corre de punta a punta |
| MMA/GCMMA (Kratos) | 🔲 No conectado | Instalado en el entorno, cero llamadas desde el core |
| FEA estructural (Tet4/Kratos) | ✅ Operativo | Con UI |
| FEA térmico | 🔶 Backend listo, sin UI | — |
| FEA modal | 🔶 Backend listo, sin UI | Corrige al chat: no es "pendiente", es "sin exponer" |
| Mallado Gmsh Tet4 + adaptativo | ✅ Operativo | — |
| Selección geométrica (`NodeSelectionEngine`) | ✅ Operativo | 7 tipos de región + composición booleana |
| Reconstrucción B-Rep | ✅ Operativo | Con fallback dummy para tests |
| Diseño generativo (A y B) | ✅ Operativo | Incluye multicarga |

---

## 5. Lo que esto cambia respecto a la lista de prioridades del chat

- **"Prioridad 2 — múltiples casos de carga"**: no es prioridad futura, ya está implementada y conectada. La prioridad real ahí sería *exponerla en la UI* (definir `load_case_id` desde el panel de condiciones), no construir el motor.
- **"Prioridad 6 — modal real"**: no es "integrar el eigen-solver", el eigen-solver ya está. La prioridad real es construir el panel/ribbon para Térmico y Modal — ambos están al mismo nivel de madurez backend, cero nivel de UI.
- El resto de las prioridades del chat (fabricación, MMA, reconstrucción, acoplamiento térmico-estructural, ESO/Level-Set) sí están confirmadas como no implementadas — ahí la lectura del chat es correcta.
