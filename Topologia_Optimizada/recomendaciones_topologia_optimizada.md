# Recomendaciones sobre `Topologia_Optimizada` (revisión del repo subido, `Onshape-master.zip`)

> Revisé el código real (no solo `PROJECT_STATUS.md`) y lo crucé contra `docs/investigacion_cad_generativo.md`. El proyecto está considerablemente más maduro de lo que reflejaba mi memoria de conversaciones anteriores: ya tienen physical groups → submodelparts, condiciones reutilizables (`ObstructionCondition`/`ProtectedRegion` = keep-out/keep-in), reconstrucción B-Rep real (Marching Tetrahedra + suavizado + `OCPBRepFitter` + STEP), motor dual FEA local/Kratos con RHS corregido, y una cultura de "no declarar implementado sin verificar" que se nota en cada archivo. Por eso esta lista es corta y quirúrgica: solo lo que la investigación señala como brecha real contra lo que hacen Fusion/Altair/Ansys/PTC/Siemens, contrastado línea por línea contra el código que ya tienen.

---

## P0 — Impacto alto, esfuerzo bajo-medio

### 1. Reparto de carga: uniforme por nodo → ponderado por área tributaria

**Dónde está hoy:**
- `core/kratos_adapter.py:729-730` — `apply_distributed_load()`: `force_per_node = [f / len(node_indices) for f in force_vector]`.
- El motor local (`core/generative_engine.py`) usa la misma semántica `mag / len(nodos)` (documentado explícitamente en `PROJECT_STATUS.md`, sección "Motor Dual FEA").

**Por qué es una brecha real (no cosmética):** en §6.5 de la investigación, la patente de Autodesk (US 12,430,483) documenta por qué la división uniforme por nodo es la fuente clásica de error en BC distribuidas: si la malla de la cara tiene densidad de nodos no uniforme (zonas finas y gruesas mezcladas — típico en Gmsh con refinamiento local), dos nodos reciben la misma fuerza aunque representen áreas tributarias muy distintas, lo que **no conserva la distribución física real de la carga** aunque sí conserve la magnitud total. Esto afecta directamente a la calidad de las sensibilidades SIMP cerca de la carga, que es justo la zona más sensible del resultado de optimización.

**Fix concreto** (mismo cálculo sirve para local y Kratos — un solo lugar de verdad):

```python
# core/boundary.py (nueva función, junto a BoundaryConditionMapper)

import numpy as np
from typing import Dict, Iterable, Sequence

def nodal_area_weights(
    nodes: np.ndarray,
    face_triangles: Sequence[Sequence[int]],
    node_indices: Iterable[int],
) -> Dict[int, float]:
    """Pesos por área tributaria para repartir una carga total sobre un
    conjunto de nodos de una cara triangulada (Physical Group de Gmsh).

    Usa reparto tipo "lumped mass" (1/3 del área de cada triángulo a cada
    uno de sus 3 vértices) — el mismo principio que Autodesk documenta en
    su patente de aplicación de BC en malla vóxel (Eq. 1: F_i = -(P·A/N)·n_i)
    pero aplicado a nodos de una malla conforme (Gmsh), no a vóxeles.

    Si no hay triangulación disponible (ej. selección legacy por coordenada,
    sin cara real), cae a reparto uniforme — el comportamiento actual — sin
    romper nada existente.
    """
    node_indices = list(node_indices)
    idx_set = set(node_indices)
    area_per_node = {n: 0.0 for n in node_indices}

    for tri in face_triangles:
        tri = [int(t) for t in tri]
        if not any(t in idx_set for t in tri):
            continue
        p0, p1, p2 = nodes[tri[0]], nodes[tri[1]], nodes[tri[2]]
        tri_area = 0.5 * float(np.linalg.norm(np.cross(p1 - p0, p2 - p0)))
        for t in tri:
            if t in idx_set:
                area_per_node[t] += tri_area / 3.0

    total = sum(area_per_node.values())
    if total <= 0.0:
        n = len(node_indices)
        return {ni: 1.0 / n for ni in node_indices}  # fallback = comportamiento actual
    return {ni: a / total for ni, a in area_per_node.items()}
```

```python
# core/kratos_adapter.py — apply_distributed_load(), reemplazo mínimo

def apply_distributed_load(self, model_part, node_indices, force_vector,
                            distribute: bool = True, face_triangles=None) -> None:
    if distribute and len(node_indices) > 0:
        if face_triangles is not None:
            from core.boundary import nodal_area_weights
            weights = nodal_area_weights(self._nodes_coords, face_triangles, node_indices)
            for node_idx in node_indices:
                w = weights[node_idx]
                self.apply_point_load(model_part, node_idx, [f * w for f in force_vector])
            return
        # Sin triangulación: comportamiento previo (reparto uniforme), sin romper nada.
        force_per_node = [f / len(node_indices) for f in force_vector]
    else:
        force_per_node = force_vector
    for node_idx in node_indices:
        self.apply_point_load(model_part, node_idx, force_per_node)
```

`face_triangles` ya existe conceptualmente: `core/meshing.py` genera `physical_groups` desde Gmsh, y la triangulación de superficie de cada physical group de tipo cara (dim=2) es la misma que usa `desktop/viewport/scene.py::face_index_for_cell` para el picking — es cuestión de exponerla también hacia `boundary.py`/`kratos_adapter.py` en vez de solo hacia el viewport.

**No toca:** `LoadType.PRESSURE` sigue lanzando `ValueError` (correcto, no se toca — sigue siendo honesto sobre la falta de modelo de área real vs. área tributaria por nodo, que son cosas distintas: aquí seguimos repartiendo una **fuerza total ya conocida**, no derivando una fuerza desde presión × área).

### 2. Halo de elementos no-optimizables alrededor de cargas/apoyos

**Dónde está hoy:** `core/topopt.py` ya tiene `set_preserved_elements()` / `set_void_elements()` (líneas 184-201) y `element_centers` precalculado (línea 55), pero **nada llama automáticamente a `set_preserved_elements` con los elementos cercanos a los nodos de carga/apoyo** — el usuario tendría que hacerlo manualmente si quiere evitar el artefacto clásico de SIMP (sensibilidad singular/spuria justo en el punto de aplicación de la carga).

**Por qué importa:** es el patrón que documenté en la investigación (§5.3) como "keep-out zone automática" de SolidWorks Topology Study alrededor de cada carga/fijación — evita que el optimizador intente eliminar material justo donde se transmiten fuerzas concentradas, que produce tensiones sin sentido físico y ensucia visualmente el resultado cerca de las BCs (justo donde después entra tu pipeline de reconstrucción B-Rep — menos ruido ahí = mejor sewing/fitting en `core/cad_reconstruction.py`).

**Fix concreto**, reutilizando el mismo `cKDTree` que ya usa `_build_weighted_filter` (línea 124):

```python
# core/topopt.py — nuevo método en SIMPSolver, junto a set_preserved_elements/set_void_elements

def protect_elements_near_nodes(self, node_indices, radius: Optional[float] = None) -> None:
    """Marca como preservados (rho=1, no-optimizables) los elementos dentro de
    ``radius`` de los nodos dados (típicamente nodos de carga o de apoyo).

    Patrón estándar de la industria (SolidWorks Topology Study crea una zona
    de exclusión automática alrededor de cada BC; Autodesk invoca el mismo
    razonamiento vía el principio de Saint-Venant: el error/singularidad local
    se disipa a una distancia de pocas veces el tamaño característico de malla,
    así que protegiendo un halo pequeño no se pierde generalidad del resultado).

    Se une (nunca reemplaza) con cualquier ``preserved_elements`` ya definido.
    """
    if radius is None:
        radius = 2.0 * self.filter_radius  # heurística: 2 vecindarios del filtro
    node_indices = np.asarray(list(node_indices), dtype=np.int64)
    if node_indices.size == 0:
        return
    from scipy.spatial import cKDTree
    tree = cKDTree(self.nodes[node_indices])
    dist, _ = tree.query(self.element_centers, k=1)
    halo = np.nonzero(dist <= radius)[0]
    if self._preserved is not None:
        halo = np.union1d(halo, np.nonzero(self._preserved)[0])
    self.set_preserved_elements(halo)
```

Punto de enganche sugerido: en `core/generative_engine.py`, justo antes de invocar `solve_simp` (donde ya se traducen `LoadCondition`/`ElasticityCondition` a fuerzas/fijaciones), llamar `protect_elements_near_nodes` con la unión de nodos con carga y nodos con restricción. Como parámetro opt-in con default sensato (para no romper resultados/tests existentes que ya comparan compliance entre motor local y Kratos con tolerancia ajustada).

---

## P1 — Impacto alto, esfuerzo medio (roadmap, no fix puntual)

### 3. `KratosOptimizationApplication` está instalado pero desconectado del núcleo SIMP

Confirmado en `PROJECT_STATUS.md`: *"la optimización SIMP sigue siendo local (sin reemplazar ni refactorizar su núcleo): el gap se cerró en la etapa de análisis FEM"*. Es decir, ya hicieron exactamente el patrón `backend="local"|"kratos"` para FEA (`run_fea`), pero **no** para la optimización topológica en sí — el `KratosOptimizationApplication==10.4.3` que ya está en `pyproject.toml` corre solo en tests/benchmarks, nunca en el pipeline del desktop.

Esto es relevante contra la investigación por dos motivos:
- **Robustez del optimizador**: hoy usan OC clásico (`core/topopt.py`, "Optimality criteria update (OC)", línea 232) con filtro de **sensibilidad** (`_apply_filter` se aplica sobre `dc`, línea 298) — es la combinación del "99-line code" de Sigmund, válida pero menos robusta que MMA/GCMMA con filtro de **densidad** en el rango amplio de restricciones múltiples (ver §4.2-4.3 de la investigación). Mientras el problema sea compliance + volumen puro, OC es perfectamente adecuado — pero **no escala** el día que quieran añadir restricción de tensión máxima o desplazamiento máximo (`ProtectedRegion`/manufactura ya existen como conceptos en `conditions.py`, faltaría el objetivo/restricción multi-criterio).
- **Es exactamente el mismo patrón dual que ya validaron para FEA**: mismo problema → dos motores → comparación automatizada (`test_cae_cross_engine.py`). Repetirlo para SIMP (local OC vs. Kratos MMA) les da, gratis, la misma auditoría cruzada que ya usan de red de seguridad de regresión.

**No es un fix de una tarde** — requiere: (a) confirmar qué algoritmos expone su versión de `OptimizationApplication` via `GetDefaultParameters()` (como ya hacen con AMGCL, ver `_DEFAULT_AMGCL_SETTINGS`), (b) un `StrainEnergyResponseFunction` + configuración JSON de `OptimizationAnalysis` (`simp_control`, `execution_policies`), (c) mapear `preserved_elements`/`void_elements` del dominio activo al equivalente de Kratos (probablemente vía densidades iniciales fijas + máscara de elementos no-designables, si la versión instalada lo soporta — verificar). Vale la pena documentarlo como el siguiente hito grande, no como P0.

---

## P2 — Impacto medio, exploratorio

### 4. Proyección Heaviside (opcional, mejora de nitidez 0/1)

`core/topopt.py` no aplica ninguna proyección — el resultado converge por penalización SIMP pura (`p=3`) + filtro de sensibilidad, que típicamente deja una banda de densidades "grises" más ancha que con proyección Heaviside + continuation de `beta` (ver §4.2 de la investigación). Como ya invierten esfuerzo real en post-proceso de la isosuperficie (`MeshSmoother` Laplaciano, hole-filling, `OCPBRepFitter`), una banda gris más angosta en origen probablemente **reduzca el trabajo que le pasan hoy al suavizado/fitting**, no es puramente cosmético en el optimizador — es una mejora que se propaga a la calidad del STEP final. Prioridad baja porque el post-proceso actual ya compensa razonablemente bien (a diferencia del punto 1 y 2, que son errores de origen, esto es una optimización de calidad).

### 5. Agrupación explícita `Design Space / Preserve / Obstacle / Loads / Supports` en el árbol de diseño

Conceptualmente ya existe — `ObstructionCondition` = keep-out, `ProtectedRegion` = keep-in, `LoadCondition`/`ElasticityCondition` = Neumann/Dirichlet (`core/conditions.py`) — pero no confirmé si `desktop/ui/panels/design_tree.py` los agrupa visualmente bajo esas categorías o los lista sin jerarquía. Si es lo segundo, es el patrón que documenté en §5.2 (los 5 programas comerciales separan esto estrictamente en el árbol) y reduce el error de usuario más citado en la literatura ("preservar demasiada geometría"). Esfuerzo bajo si `design_tree.py` ya soporta grupos/carpetas (no confirmé la API del panel en esta pasada).

---

## Lo que NO toqué (ya está a la par o por encima de la industria revisada)

- **Reconstrucción de salida** (`core/cad_reconstruction.py`): Marching Tetrahedra + dedup vectorizado + suavizado Laplaciano + hole-filling + `OCPBRepFitter` → STEP real. Esto es más completo que lo que hacen SolidWorks (exporta STL/mesh aproximado) o Ansys Mechanical (reconstrucción manual/semi-automática) — solo Siemens NX (Convergent Modeling) evita el paso de reconstrucción por completo al mantener facetas y B-Rep coexistiendo, pero eso es un cambio de kernel geométrico completo (Parasolid vs. OCP/OCCT), no algo justificable a este nivel de madurez del proyecto.
- **Physical groups → submodelparts, BC estrictas sin fallback silencioso**: ya resuelto exactamente como documenté que lo resuelve toda la industria (§3.2), incluyendo el detalle fino de que una cara que no mapea a nodos **falla con error claro** en vez de reubicarse silenciosamente — más estricto que varios de los productos comerciales revisados.
- **Licencia/IP**: `core/license.py` ya separa correctamente "todo funciona offline, la validación de licencia es la única pieza que tocaría red" — coincide con el patrón de toda la industria de mantener el core de optimización fuera del alcance de scripting de usuario.
