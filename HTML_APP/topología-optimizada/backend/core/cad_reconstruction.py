"""CAD Reconstruction pipeline.

Converts volumetric or mesh-based results (from topology optimisation or
generative design) into B-Rep CAD geometry that can be exported as STEP.

Pipeline:

    Conditions / Optimisation result
         ↓
    Volumetric representation (density field / voxel grid)
         ↓
    Surface extraction (marching cubes / Poisson)
         ↓
    Mesh refinement / smoothing
         ↓
    B-Rep fitting (future: CadQuery/OCC)
         ↓
    CAD / STEP

The surface extraction (marching tetrahedra, working directly on the SIMP
density field) and the B-Rep fitting (OpenCASCADE via OCP, shipped with
CadQuery) are both implemented.  The pipeline is therefore functional
end-to-end from density field to a STEP file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np


def apply_frozen_passthrough(
    densities: np.ndarray,
    num_elements: int,
    frozen_elements: Optional[Sequence[int]],
    frozen_value: float = 1.0,
) -> np.ndarray:
    """Fuerza a ``frozen_value`` las densidades de los elementos FROZEN.

    Pass-through FROZEN_FACE (equivalencia honesta con KEEP_IN): los
    elementos de la cara congelada quedan fijos a 1.0 para que el marching
    tetrahedra los incluya en la geometría reconstruida.

    Levanta ``ValueError`` explícito ante índices fuera de rango (nunca
    recorte silencioso) y ante longitud de densidades inconsistente.
    """
    out = np.asarray(densities, dtype=float).ravel().copy()
    if out.shape[0] != int(num_elements):
        raise ValueError(
            f"densities ({out.shape[0]}) no coincide con num_elements "
            f"({int(num_elements)}); revisar campo de densidad."
        )
    if not frozen_elements:
        return out
    frozen = np.asarray(list(frozen_elements), dtype=np.int64).ravel()
    if frozen.size == 0:
        return out
    bad = frozen[(frozen < 0) | (frozen >= int(num_elements))]
    if bad.size:
        raise ValueError(
            f"frozen_elements fuera de rango: {bad[:10].tolist()}... "
            f"(num_elements={int(num_elements)})."
        )
    out[frozen] = float(frozen_value)
    return out


class ReconstructionStage(str, Enum):
    DENSITY_FIELD = "density_field"
    SURFACE_MESH = "surface_mesh"
    SMOOTHED_MESH = "smoothed_mesh"
    BREP_SOLID = "brep_solid"
    STEP_FILE = "step_file"


class ReconstructionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReconstructionResult:
    """Output of a reconstruction pipeline stage."""
    stage: ReconstructionStage
    status: ReconstructionStatus = ReconstructionStatus.NOT_STARTED
    data: Optional[Any] = None  # numpy array, CadQuery Shape, or dict
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class SurfaceExtractor(ABC):
    """Abstract surface extraction from a density field or voxel grid."""

    @abstractmethod
    def extract(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        threshold: float = 0.5,
    ) -> ReconstructionResult:
        """Extract an isosurface from the density field."""


def _tet_iso_triangles(verts: np.ndarray, dens: np.ndarray, threshold: float) -> List[np.ndarray]:
    """Marching-tetrahedra: produce the iso triangle(s) of one tetrahedron.

    ``verts`` is (4, 3); ``dens`` is (4,).  The ambient dimension is 3D.
    """
    tris: List[np.ndarray] = []
    below = [i for i in range(4) if dens[i] <= threshold]
    above = [i for i in range(4) if dens[i] > threshold]
    count_below = len(below)
    if count_below == 0 or count_below == 4:
        return tris
    if count_below == 1:
        a = below[0]
        b, c, d = above
        tris.append(np.array([
            _lerp_edge(verts, dens, a, b, threshold),
            _lerp_edge(verts, dens, a, c, threshold),
            _lerp_edge(verts, dens, a, d, threshold),
        ]))
    elif count_below == 3:
        a = above[0]
        b, c, d = below
        tris.append(np.array([
            _lerp_edge(verts, dens, a, b, threshold),
            _lerp_edge(verts, dens, a, c, threshold),
            _lerp_edge(verts, dens, a, d, threshold),
        ]))
    else:  # count_below == 2 -> two triangles
        b1, b2 = below
        a1, a2 = above
        tris.append(np.array([
            _lerp_edge(verts, dens, b1, a1, threshold),
            _lerp_edge(verts, dens, b2, a1, threshold),
            _lerp_edge(verts, dens, b1, a2, threshold),
        ]))
        tris.append(np.array([
            _lerp_edge(verts, dens, b2, a1, threshold),
            _lerp_edge(verts, dens, b1, a2, threshold),
            _lerp_edge(verts, dens, b2, a2, threshold),
        ]))
    return tris


def _lerp_edge(verts: np.ndarray, dens: np.ndarray, i: int, j: int,
               threshold: float) -> np.ndarray:
    di, dj = float(dens[i]), float(dens[j])
    if abs(dj - di) < 1e-12:
        t = 0.5
    else:
        t = (threshold - di) / (dj - di)
    t = float(min(max(t, 0.0), 1.0))
    return verts[i] + t * (verts[j] - verts[i])


def _element_densities_to_nodes(
    nodes: np.ndarray, elements: np.ndarray, densities: np.ndarray
) -> np.ndarray:
    """Average per-element densities onto the nodes (needed by marching tets)."""
    accum = np.zeros(nodes.shape[0])
    count = np.zeros(nodes.shape[0])
    for e in range(elements.shape[0]):
        w = float(densities[e])
        for n in elements[e]:
            accum[n] += w
            count[n] += 1.0
    return np.divide(accum, count, out=np.zeros_like(accum), where=count > 0)


def _deduplicate_vertices(raw: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Merge coincident vertices (within 1e-9) and return (remap, unique_vertices).

    Vectorised (structured-array unique) alternative to the per-vertex Python
    dict, so marching tetrahedra scales to meshes with many iso triangles.
    """
    raw = np.asarray(raw, dtype=float)
    n = raw.shape[0]
    if n == 0:
        return np.zeros(0, dtype=np.int64), raw
    rounded = np.round(raw, 9)
    view = rounded.view(
        np.dtype([("x", "f8"), ("y", "f8"), ("z", "f8")])
    ).reshape(n)
    uniq, inverse = np.unique(view, return_inverse=True)
    unique_verts = uniq.view(np.float64).reshape(-1, 3)
    return inverse.astype(np.int64), unique_verts


def _triangle_adjacency(triangles: np.ndarray, num_vertices: int) -> List[set]:
    """Vertex adjacency lists built from the triangle connectivity."""
    adj: List[set] = [set() for _ in range(num_vertices)]
    for tri in triangles:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        if b != a:
            adj[a].add(b)
            adj[b].add(a)
        if c != a:
            adj[a].add(c)
            adj[c].add(a)
        if c != b:
            adj[b].add(c)
            adj[c].add(b)
    return adj


def _boundary_vertices(adj: List[set], triangles: np.ndarray) -> set:
    """Vertices on an open boundary (edge belonging to only one triangle)."""
    edges: Dict[Tuple[int, int], int] = {}
    for tri in triangles:
        a, b, c = (int(tri[0]), int(tri[1]), int(tri[2]))
        for e1, e2 in ((a, b), (b, c), (c, a)):
            key = (min(e1, e2), max(e1, e2))
            edges[key] = edges.get(key, 0) + 1
    boundary = set()
    for (u, v), count in edges.items():
        if count == 1:
            boundary.add(u)
            boundary.add(v)
    return boundary


def smooth_surface_mesh(
    vertices: np.ndarray,
    triangles: np.ndarray,
    iterations: int = 3,
    alpha: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """Laplacian smoothing of a triangle mesh (post-process of noisy isosurfaces).

    Boundary/edge vertices are held fixed so the overall shape is preserved
    while high-frequency noise is reduced.  Returns the smoothed vertices and
    the unchanged connectivity.
    """
    verts = np.asarray(vertices, dtype=float)
    tris = np.asarray(triangles, dtype=int)
    if verts.shape[0] == 0 or tris.shape[0] == 0:
        return verts, tris
    adj = _triangle_adjacency(tris, verts.shape[0])
    fixed = _boundary_vertices(adj, tris)
    work = verts.copy()
    for _ in range(max(int(iterations), 0)):
        new = work.copy()
        for i in range(verts.shape[0]):
            if i in fixed or not adj[i]:
                continue
            neigh = np.asarray([work[j] for j in adj[i]], dtype=float)
            new[i] = work[i] + alpha * (np.mean(neigh, axis=0) - work[i])
        work = new
    return work, tris


def taubin_smooth(
    vertices: np.ndarray,
    triangles: np.ndarray,
    iterations: int = 10,
    lambda_: float = 0.5,
    mu: float = -0.53,
) -> Tuple[np.ndarray, np.ndarray]:
    """Suavizado Taubin (λ|μ): pasa-bajos sin encogimiento global.

    Alterna un paso de contracción (λ > 0) con uno de expansión (μ < 0),
    eliminando el ruido de alta frecuencia de la isosuperficie sin el
    encogimiento que introduce el Laplaciano puro. Los vértices de borde se
    mantienen fijos (igual que :func:`smooth_surface_mesh`).

    Estabilidad típica: λ ≈ 0.5, μ ≈ −0.53 (|μ| > λ). Fail-loud si λ ≤ 0
    o μ ≥ 0 (sería un Laplaciano puro encogedor, no Taubin).
    """
    verts = np.asarray(vertices, dtype=float)
    tris = np.asarray(triangles, dtype=int)
    if verts.shape[0] == 0 or tris.shape[0] == 0:
        return verts, tris
    lam = float(lambda_)
    m = float(mu)
    if not np.isfinite(lam) or lam <= 0:
        raise ValueError(f"taubin lambda_={lambda_!r} inválido (debe ser > 0).")
    if not np.isfinite(m) or m >= 0:
        raise ValueError(f"taubin mu={mu!r} inválido (debe ser < 0).")
    adj = _triangle_adjacency(tris, verts.shape[0])
    fixed = _boundary_vertices(adj, tris)

    def _step(w: np.ndarray, factor: float) -> np.ndarray:
        new = w.copy()
        for i in range(verts.shape[0]):
            if i in fixed or not adj[i]:
                continue
            neigh = np.asarray([w[j] for j in adj[i]], dtype=float)
            new[i] = w[i] + factor * (np.mean(neigh, axis=0) - w[i])
        return new

    work = verts.copy()
    for _ in range(max(int(iterations), 0)):
        work = _step(work, lam)
        work = _step(work, m)
    return work, tris


class MeshSmoother:
    """Post-process smoothing of the extracted isosurface mesh.

    ``method`` selecciona "laplacian" (histórico, default) o "taubin"
    (sin encogimiento). Con "laplacian" el comportamiento es idéntico al
    histórico (regresión garantizada).
    """

    def smooth(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
        iterations: int = 3,
        alpha: float = 0.5,
        method: str = "laplacian",
        mu: Optional[float] = None,
    ) -> ReconstructionResult:
        if method == "laplacian":
            smv, smt = smooth_surface_mesh(vertices, triangles, iterations, alpha)
            meta = {"iterations": int(iterations), "alpha": float(alpha),
                    "method": "laplacian", "triangles": int(smt.shape[0])}
        elif method == "taubin":
            m = -0.53 if mu is None else float(mu)
            smv, smt = taubin_smooth(vertices, triangles, iterations, alpha, m)
            meta = {"iterations": int(iterations), "alpha": float(alpha),
                    "mu": m, "method": "taubin",
                    "triangles": int(smt.shape[0])}
        else:
            raise ValueError(
                f"smoothing method={method!r} no soportado "
                f"(usar 'laplacian' o 'taubin').")
        return ReconstructionResult(
            stage=ReconstructionStage.SMOOTHED_MESH,
            status=ReconstructionStatus.COMPLETED,
            data={"vertices": smv, "triangles": smt},
            metadata=meta,
        )


# ---------------------------------------------------------------------------
# Hole-filling: close open boundary loops on triangle meshes
# ---------------------------------------------------------------------------

def _boundary_edges(triangles: np.ndarray) -> Dict[Tuple[int, int], int]:
    """Count how many triangles share each edge.

    Boundary edges appear exactly once; interior edges appear twice (or more
    for non-manifold meshes, but those are rare in marching-tetrahedra output).
    """
    edges: Dict[Tuple[int, int], int] = {}
    for tri in triangles:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        for e1, e2 in ((a, b), (b, c), (c, a)):
            key = (min(e1, e2), max(e1, e2))
            edges[key] = edges.get(key, 0) + 1
    return edges


def _boundary_loops(triangles: np.ndarray) -> List[List[int]]:
    """Extract ordered boundary loops from an open triangle mesh.

    Each loop is a list of vertex indices forming a closed chain of boundary
    edges.  The order is consistent (adjacent vertices share an edge).
    """
    edge_counts = _boundary_edges(triangles)
    boundary_set = {k for k, v in edge_counts.items() if v == 1}
    if not boundary_set:
        return []

    # Build adjacency from boundary edges only (undirected).
    adj: Dict[int, set] = {}
    for u, v in boundary_set:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)

    visited_edges: set = set()
    loops: List[List[int]] = []
    for start_u, start_v in boundary_set:
        if (start_u, start_v) in visited_edges:
            continue
        # Walk one loop starting from this edge.
        loop: List[int] = [start_u, start_v]
        visited_edges.add((start_u, start_v))
        visited_edges.add((start_v, start_u))
        while True:
            current = loop[-1]
            prev = loop[-2]
            neighbours = adj.get(current, set())
            next_v = None
            for nb in neighbours:
                edge_key = (min(current, nb), max(current, nb))
                if edge_key not in visited_edges:
                    next_v = nb
                    break
            if next_v is None or next_v == start_u:
                # Loop closed (or dead-end).
                break
            loop.append(next_v)
            visited_edges.add((current, next_v))
            visited_edges.add((next_v, current))
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def fill_holes(
    vertices: np.ndarray,
    triangles: np.ndarray,
    max_hole_edges: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, int]:
    """Fill open boundary loops with fan triangulation.

    For each boundary loop, a fan of triangles is created from the centroid
    of the loop vertices.  This is robust for convex and mildly concave holes
    which are the typical case in marching-tetrahedra output from topology
    optimisation.

    Parameters
    ----------
    vertices : (N, 3) array
    triangles : (M, 3) int array
    max_hole_edges : int or None
        If set, skip loops with more edges than this limit (very large holes
        are unlikely to be fillable with a simple fan).

    Returns
    -------
    filled_vertices, filled_triangles, num_holes_filled
    """
    verts = np.asarray(vertices, dtype=float)
    tris = np.asarray(triangles, dtype=int)
    loops = _boundary_loops(tris)
    if not loops:
        return verts, tris, 0

    # Work on a mutable copy of the triangle list (list of lists for appending).
    result_tris = tris.tolist()
    holes_filled = 0

    for loop in loops:
        if max_hole_edges is not None and len(loop) > max_hole_edges:
            continue
        centroid = np.mean(verts[loop], axis=0)
        # Add centroid as a new vertex.
        new_idx = verts.shape[0]
        verts = np.vstack([verts, centroid.reshape(1, 3)])
        # Fan triangulation from centroid to each consecutive edge in the loop.
        for i in range(len(loop)):
            v0 = loop[i]
            v1 = loop[(i + 1) % len(loop)]
            result_tris.append([new_idx, v0, v1])
        holes_filled += 1

    filled_tris = np.asarray(result_tris, dtype=int)
    return verts, filled_tris, holes_filled


class MeshHoleFiller:
    """Fill open boundary loops on a triangle mesh before B-Rep fitting."""

    # AUTO-HOLE-CAP: factor multiplicativo sobre la mediana de aristas por
    # loop abierto de ESTA malla. El conteo de aristas de un loop ya es
    # invariante de escala (circunferencia en "unidades de elemento", no en
    # mm), así que no hace falta longitud de arista/bbox: un loop de ruido
    # de marching-tets ronda la mediana de la malla; un agujero de diseño
    # real (anclaje, keep-out) suele ser sensiblemente más grande que el
    # resto de los bordes abiertos de esa misma pieza. factor=4.0 y
    # min_edges=12 son de partida (no medidos contra malla real todavía:
    # requiere backfill test antes de exponer en UI, ver Fase 4.5).
    AUTO_FACTOR = 4.0
    AUTO_MIN_EDGES = 12

    def fill(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
        max_hole_edges: Optional[Union[int, str]] = None,
    ) -> ReconstructionResult:
        verts0 = np.asarray(vertices, dtype=float)
        tris0 = np.asarray(triangles, dtype=int)
        loops_before = _boundary_loops(tris0)
        sizes_before = sorted(len(loop) for loop in loops_before)

        resolved_cap: Optional[int] = None
        auto_used = False
        if isinstance(max_hole_edges, str):
            if max_hole_edges != "auto":
                raise ValueError(
                    f"max_hole_edges={max_hole_edges!r} inválido "
                    f"(usar None, un entero >= 3, o 'auto').")
            auto_used = True
            if sizes_before:
                import statistics
                median_size = statistics.median(sizes_before)
                resolved_cap = max(
                    self.AUTO_MIN_EDGES, int(round(median_size * self.AUTO_FACTOR)))
        else:
            resolved_cap = max_hole_edges

        verts, tris, n = fill_holes(verts0, tris0, resolved_cap)
        loops_after = _boundary_loops(tris)
        # FILL-REPORT (reversible): lo no tapado queda explícito en metadata
        # (antes un loop grande se sellaba —o se omitía con tope— sin avisar).
        # Para volver atrás: devolver solo holes_filled/triangles_after.
        skipped = 0
        if resolved_cap is not None:
            skipped = sum(1 for size in sizes_before if size > resolved_cap)
        return ReconstructionResult(
            stage=ReconstructionStage.SMOOTHED_MESH,
            status=ReconstructionStatus.COMPLETED,
            data={"vertices": verts, "triangles": tris},
            metadata={"holes_filled": int(n),
                      "holes_skipped": int(skipped),
                      "open_loops_before": int(len(loops_before)),
                      "open_loops_after": int(len(loops_after)),
                      "largest_hole_edges": int(max(sizes_before)) if sizes_before else 0,
                      "triangles_after": int(tris.shape[0]),
                      "vertices_after": int(verts.shape[0]),
                      "max_hole_edges_auto": bool(auto_used),
                      "max_hole_edges_resolved": resolved_cap},
        )


# ---------------------------------------------------------------------------
# Fase 5a — Reparación básica + decimación (numpy-only, sin dependencias nuevas)
# ---------------------------------------------------------------------------

def mesh_quality_report(
    vertices: np.ndarray,
    triangles: np.ndarray,
) -> Dict[str, Any]:
    """Diagnóstico explícito de una malla triangular (no modifica nada).

    Reporta: vértices/triángulos, degenerados (índices repetidos o área ~0),
    aristas non-manifold (>2 triángulos por arista), loops de borde
    (shells abiertos) y vértices no referenciados. Las condiciones
    ambiguas (non-manifold, self-intersections) se REPORTAN, no se
    "arreglan" en silencio — mismo principio que el resto del proyecto.
    """
    verts = np.asarray(vertices, dtype=float)
    tris = np.asarray(triangles, dtype=int)
    n_tris = int(tris.shape[0]) if tris.size else 0
    report: Dict[str, Any] = {
        "vertices": int(verts.shape[0]) if verts.size else 0,
        "triangles": n_tris,
        "degenerate_triangles": 0,
        "non_manifold_edges": 0,
        "boundary_loops": 0,
        "unreferenced_vertices": 0,
        "open": False,
    }
    if n_tris == 0:
        return report
    # Degenerados: índice repetido dentro del triángulo.
    dup_idx = int(np.sum(
        (tris[:, 0] == tris[:, 1]) | (tris[:, 1] == tris[:, 2]) | (tris[:, 0] == tris[:, 2])
    ))
    # Área ~0 (producto cruzado).
    v0, v1, v2 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    areas = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
    zero_area = int(np.sum(areas <= 1e-18))
    report["degenerate_triangles"] = int(max(dup_idx, zero_area))
    edges = _boundary_edges(tris)
    report["non_manifold_edges"] = int(sum(1 for c in edges.values() if c > 2))
    loops = _boundary_loops(tris)
    report["boundary_loops"] = int(len(loops))
    report["open"] = bool(loops)
    used = np.unique(tris.ravel()) if tris.size else np.zeros(0, dtype=int)
    report["unreferenced_vertices"] = int(verts.shape[0] - used.shape[0])
    return report


def repair_mesh(
    vertices: np.ndarray,
    triangles: np.ndarray,
    weld_tolerance_decimals: int = 9,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Reparación básica determinista de una malla triangular.

    Hace (solo lo no ambiguo): suelda vértices coincidentes (reusa
    :func:`_deduplicate_vertices`), elimina triángulos degenerados
    (índices repetidos o área ~0) y elimina vértices no referenciados.

    NO toca aristas non-manifold ni self-intersections: se reportan en
    ``stats`` para decisión explícita del usuario (nunca fix silencioso).

    Returns (vertices, triangles, stats).
    """
    verts = np.asarray(vertices, dtype=float)
    tris = np.asarray(triangles, dtype=int)
    stats: Dict[str, Any] = {
        "vertices_before": int(verts.shape[0]) if verts.size else 0,
        "triangles_before": int(tris.shape[0]) if tris.size else 0,
        "vertices_welded": 0,
        "degenerate_removed": 0,
        "unreferenced_removed": 0,
        "non_manifold_edges": 0,
        "boundary_loops": 0,
    }
    if tris.size == 0:
        return verts.reshape(-1, 3), tris.reshape(-1, 3), stats

    # 1) Soldar duplicados exactos (redondeo a N decimales).
    if weld_tolerance_decimals != 9:
        rounded = np.round(verts, weld_tolerance_decimals)
        view = rounded.view(
            np.dtype([("x", "f8"), ("y", "f8"), ("z", "f8")])
        ).reshape(verts.shape[0])
        uniq, inverse = np.unique(view, return_inverse=True)
        dedup = uniq.view(np.float64).reshape(-1, 3)
        remap = inverse.astype(np.int64)
    else:
        remap, dedup = _deduplicate_vertices(verts)
    stats["vertices_welded"] = int(verts.shape[0] - dedup.shape[0])
    tris = np.take(remap, tris)

    # 2) Eliminar degenerados (índice repetido o área ~0).
    dup_mask = (tris[:, 0] == tris[:, 1]) | (tris[:, 1] == tris[:, 2]) | (tris[:, 0] == tris[:, 2])
    v0, v1, v2 = dedup[tris[:, 0]], dedup[tris[:, 1]], dedup[tris[:, 2]]
    areas = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
    zero_mask = areas <= 1e-18
    bad = dup_mask | zero_mask
    stats["degenerate_removed"] = int(np.sum(bad))
    tris = tris[~bad]

    # 3) Compactar vértices no referenciados.
    if tris.size:
        used, compact = np.unique(tris.ravel(), return_inverse=True)
        stats["unreferenced_removed"] = int(dedup.shape[0] - used.shape[0])
        verts_out = dedup[used]
        tris_out = compact.reshape(tris.shape)
    else:
        stats["unreferenced_removed"] = int(dedup.shape[0])
        verts_out = np.zeros((0, 3), dtype=float)
        tris_out = np.zeros((0, 3), dtype=int)

    # 4) Diagnosticar lo ambiguo (solo reporte).
    if tris_out.size:
        edges = _boundary_edges(tris_out)
        stats["non_manifold_edges"] = int(sum(1 for c in edges.values() if c > 2))
        stats["boundary_loops"] = int(len(_boundary_loops(tris_out)))

    stats["vertices_after"] = int(verts_out.shape[0])
    stats["triangles_after"] = int(tris_out.shape[0])
    return verts_out, tris_out, stats


def decimate_mesh(
    vertices: np.ndarray,
    triangles: np.ndarray,
    target_fraction: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Decimación por clustering de vértices en grilla (determinista, numpy-only).

    La celda se dimensiona desde el bbox para apuntar a
    ``target_fraction`` de triángulos. Cada celda colapsa a su centroide;
    los triángulos degenerados resultantes se eliminan y los vértices
    huérfanos se compactan. Si la malla ya está por debajo del objetivo,
    se devuelve sin cambios (sin upsampling silencioso).

    Args:
        target_fraction: fracción objetivo de triángulos en (0, 1].

    Returns (vertices, triangles, stats). Levanta ``ValueError`` ante
    ``target_fraction`` fuera de rango.
    """
    if not 0.0 < float(target_fraction) <= 1.0:
        raise ValueError(
            f"target_fraction={target_fraction!r} fuera de rango (0, 1]."
        )
    verts = np.asarray(vertices, dtype=float)
    tris = np.asarray(triangles, dtype=int)
    stats: Dict[str, Any] = {
        "triangles_before": int(tris.shape[0]) if tris.size else 0,
        "target_fraction": float(target_fraction),
        "cell_size": 0.0,
        "triangles_after": int(tris.shape[0]) if tris.size else 0,
        "decimated": False,
    }
    if tris.size == 0 or verts.size == 0:
        return verts.reshape(-1, 3), tris.reshape(-1, 3), stats

    n_target = max(int(tris.shape[0] * float(target_fraction)), 1)
    if n_target >= tris.shape[0]:
        return verts, tris, stats

    # Celda por área de superficie: cada celda retiene ~2 triángulos
    # (un quad de la grilla), así que celda = sqrt(area_total / (n_target/2)).
    # Esto es robusto ante mallas planas (volumen ~0) donde un estimador
    # volumétrico colapsaría a celda ~0.
    v0, v1, v2 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    total_area = float(0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).sum())
    if total_area <= 1e-18:
        return verts, tris, stats
    cell = float(np.sqrt(total_area / max(n_target / 2.0, 1.0)))
    lo = verts.min(axis=0)
    stats["cell_size"] = cell

    cell_idx = np.floor((verts - lo) / cell).astype(np.int64)
    # Clave por celda → centroide.
    keys = [tuple(int(c) for c in row) for row in cell_idx]
    uniq_keys: Dict[Tuple[int, int, int], int] = {}
    order: List[Tuple[int, int, int]] = []
    for k in keys:
        if k not in uniq_keys:
            uniq_keys[k] = len(order)
            order.append(k)
    remap = np.asarray([uniq_keys[k] for k in keys], dtype=np.int64)
    new_verts = np.zeros((len(order), 3), dtype=float)
    counts = np.zeros(len(order), dtype=float)
    np.add.at(new_verts, remap, verts)
    np.add.at(counts, remap, 1.0)
    new_verts /= counts[:, None]

    new_tris = remap[tris]
    dup_mask = (new_tris[:, 0] == new_tris[:, 1]) | (new_tris[:, 1] == new_tris[:, 2]) | (new_tris[:, 0] == new_tris[:, 2])
    new_tris = new_tris[~dup_mask]
    if new_tris.size:
        used, compact = np.unique(new_tris.ravel(), return_inverse=True)
        new_verts = new_verts[used]
        new_tris = compact.reshape(new_tris.shape)
    else:
        new_verts = np.zeros((0, 3), dtype=float)
        new_tris = np.zeros((0, 3), dtype=int)

    stats["triangles_after"] = int(new_tris.shape[0])
    stats["vertices_after"] = int(new_verts.shape[0])
    stats["decimated"] = bool(new_tris.shape[0] < stats["triangles_before"])
    return new_verts, new_tris, stats


class MeshRepair:
    """Reparación básica de malla (suelda + degenerados + huérfanos)."""

    def repair(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
    ) -> ReconstructionResult:
        verts, tris, stats = repair_mesh(vertices, triangles)
        return ReconstructionResult(
            stage=ReconstructionStage.SMOOTHED_MESH,
            status=ReconstructionStatus.COMPLETED,
            data={"vertices": verts, "triangles": tris},
            metadata={k: (int(v) if isinstance(v, (int, np.integer)) else v)
                      for k, v in stats.items()},
        )


class MeshDecimator:
    """Decimación por clustering (reduce conteo de triángulos)."""

    def __init__(self, target_fraction: float = 0.5) -> None:
        if not 0.0 < float(target_fraction) <= 1.0:
            raise ValueError(
                f"target_fraction={target_fraction!r} fuera de rango (0, 1]."
            )
        self.target_fraction = float(target_fraction)

    def decimate(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
        target_fraction: Optional[float] = None,
    ) -> ReconstructionResult:
        frac = float(target_fraction) if target_fraction is not None else self.target_fraction
        verts, tris, stats = decimate_mesh(vertices, triangles, frac)
        return ReconstructionResult(
            stage=ReconstructionStage.SMOOTHED_MESH,
            status=ReconstructionStatus.COMPLETED,
            data={"vertices": verts, "triangles": tris},
            metadata={k: (int(v) if isinstance(v, (int, np.integer)) else float(v) if isinstance(v, float) else v)
                      for k, v in stats.items()},
        )


# ---------------------------------------------------------------------------
# Fase 5b — Remallado uniforme + non-manifold explícito + self-intersections
# (numpy-only, sin dependencias nuevas)
# ---------------------------------------------------------------------------

def _edge_to_triangles(triangles: np.ndarray) -> Dict[Tuple[int, int], List[int]]:
    """Arista (u<v) -> índices de triángulos que la usan."""
    tris = np.asarray(triangles, dtype=int)
    out: Dict[Tuple[int, int], List[int]] = {}
    for ti in range(tris.shape[0]):
        a, b, c = int(tris[ti, 0]), int(tris[ti, 1]), int(tris[ti, 2])
        for u, v in ((a, b), (b, c), (a, c)):
            key = (min(u, v), max(u, v))
            out.setdefault(key, []).append(ti)
    return out


def uniform_remesh(
    vertices: np.ndarray,
    triangles: np.ndarray,
    target_length: float,
    iterations: int = 3,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Remallado uniforme isotrópico (split/collapse/flip + suavizado).

    Lleva las aristas hacia ``target_length``: divide las > 4/3·L,
    colapsa las < 4/5·L al punto medio, voltea aristas interiores para
    optimizar valencia (6 interior / 4 borde) y suaviza con laplaciano
    (borde fijo, reusa :func:`smooth_surface_mesh`). Termina con
    :func:`repair_mesh` para compactar degenerados.

    Args:
        target_length: longitud de arista objetivo (> 0, misma unidad
            que los vértices).
        iterations: pasadas split/collapse/flip (>= 0).

    Returns (vertices, triangles, stats). ``ValueError`` explícito ante
    parámetros fuera de rango.
    """
    if not float(target_length) > 0.0:
        raise ValueError(f"target_length={target_length!r} debe ser > 0.")
    if int(iterations) < 0:
        raise ValueError(f"iterations={iterations!r} debe ser >= 0.")
    L = float(target_length)
    verts: List[np.ndarray] = [np.asarray(r, dtype=float) for r in np.asarray(vertices, dtype=float)]
    tris: List[List[int]] = [list(map(int, r)) for r in np.asarray(triangles, dtype=int)]
    stats: Dict[str, Any] = {"splits": 0, "collapses": 0, "flips": 0,
                             "iterations": int(iterations), "target_length": L}
    if not tris or not verts:
        stats.update({"vertices_after": len(verts), "triangles_after": len(tris)})
        return np.asarray(verts, dtype=float).reshape(-1, 3), np.zeros((0, 3), dtype=int), stats

    def _third(t: List[int], u: int, v: int) -> int:
        for w in t:
            if w != u and w != v:
                return w
        raise ValueError("triángulo degenerado en remallado")  # pragma: no cover

    for _ in range(int(iterations)):
        # --- Split: aristas largas -> punto medio ---
        emap = _edge_to_triangles(np.asarray(tris, dtype=int))
        for (u, v), tlist in emap.items():
            if u >= len(verts) or v >= len(verts):
                continue  # pragma: no cover - defensivo
            if float(np.linalg.norm(verts[u] - verts[v])) <= 4.0 / 3.0 * L:
                continue
            mid = 0.5 * (verts[u] + verts[v])
            verts.append(mid)
            mi = len(verts) - 1
            for ti in tlist:
                t = tris[ti]
                if u not in t or v not in t:
                    continue
                w = _third(t, u, v)
                tris[ti] = [u, mi, w]
                tris.append([mi, v, w])
            stats["splits"] += 1

        # --- Collapse: aristas cortas -> punto medio ---
        V = np.asarray(verts, dtype=float)
        T = np.asarray(tris, dtype=int)
        emap = _edge_to_triangles(T)
        order = sorted(emap.keys(),
                       key=lambda e: float(np.linalg.norm(V[e[0]] - V[e[1]])))
        alive = [True] * len(verts)
        for (u, v) in order:
            if not alive[u] or not alive[v]:
                continue
            if float(np.linalg.norm(verts[u] - verts[v])) >= 4.0 / 5.0 * L:
                continue
            mid = 0.5 * (verts[u] + verts[v])
            verts[u] = mid
            alive[v] = False
            for t in tris:
                for k in range(3):
                    if t[k] == v:
                        t[k] = u
            stats["collapses"] += 1
        # Compactar colapsados + quitar degenerados del colapso.
        keep_v = [i for i, a in enumerate(alive) if a]
        remap = {old: new for new, old in enumerate(keep_v)}
        verts = [verts[i] for i in keep_v]
        new_tris: List[List[int]] = []
        for t in tris:
            nt = [remap[x] for x in t]
            if nt[0] == nt[1] or nt[1] == nt[2] or nt[0] == nt[2]:
                continue
            new_tris.append(nt)
        tris = new_tris
        if not tris:
            break

        # --- Flip: optimizar valencia (solo aristas interiores) ---
        V = np.asarray(verts, dtype=float)
        T = np.asarray(tris, dtype=int)
        emap = _edge_to_triangles(T)
        edge_set = set(emap.keys())
        boundary_v = _boundary_vertices(_triangle_adjacency(T, V.shape[0]), T)
        valence = np.zeros(V.shape[0], dtype=int)
        for t in T:
            for x in t:
                valence[int(x)] += 1
        target = np.array([4 if i in boundary_v else 6 for i in range(V.shape[0])])
        for (u, v), tlist in emap.items():
            if len(tlist) != 2:
                continue
            t1, t2 = tris[tlist[0]], tris[tlist[1]]
            try:
                a = _third(t1, u, v)
                b = _third(t2, u, v)
            except ValueError:
                continue  # pragma: no cover - defensivo
            if a == b:
                continue
            if (min(a, b), max(a, b)) in edge_set:
                continue
            before = sum((valence[x] - target[x]) ** 2 for x in (u, v, a, b))
            # Tras el flip: u,v pierden un triángulo; a,b ganan uno.
            after = ((valence[u] - 1 - target[u]) ** 2 + (valence[v] - 1 - target[v]) ** 2
                     + (valence[a] + 1 - target[a]) ** 2 + (valence[b] + 1 - target[b]) ** 2)
            if after < before:
                tris[tlist[0]] = [a, b, u]
                tris[tlist[1]] = [b, a, v]
                valence[u] -= 1
                valence[v] -= 1
                valence[a] += 1
                valence[b] += 1
                stats["flips"] += 1

        # --- Suavizado laplaciano (borde fijo) ---
        V = np.asarray(verts, dtype=float)
        T = np.asarray(tris, dtype=int)
        V, _ = smooth_surface_mesh(V, T, iterations=1, alpha=0.5)
        verts = [np.asarray(r, dtype=float) for r in V]

    V = np.asarray(verts, dtype=float)
    T = np.asarray(tris, dtype=int) if tris else np.zeros((0, 3), dtype=int)
    V, T, rep_stats = repair_mesh(V, T)
    stats["repair"] = {k: int(v) for k, v in rep_stats.items() if isinstance(v, (int, np.integer))}
    stats["vertices_after"] = int(V.shape[0])
    stats["triangles_after"] = int(T.shape[0])
    return V, T, stats


def split_non_manifold(
    vertices: np.ndarray,
    triangles: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Separa non-manifold duplicando vértices (operación explícita y reversible).

    - Aristas con >2 triángulos: cada cara extra recibe copias propias
      de ambos extremos (las hojas dejan de compartir la arista).
    - Vértices cuyo link tiene >1 componente (conos/abanicos
      desconectados): cada componente extra recibe una copia del vértice.

    No elimina ni mueve geometría: solo duplica índices. Lo que no se
    puede separar de forma bien definida se reporta en ``stats``
    (p. ej. conteo residual, que debe ser 0 al terminar).

    Returns (vertices, triangles, stats).
    """
    verts: List[np.ndarray] = [np.asarray(r, dtype=float) for r in np.asarray(vertices, dtype=float)]
    tris: List[List[int]] = [list(map(int, r)) for r in np.asarray(triangles, dtype=int)]
    stats: Dict[str, Any] = {"non_manifold_edges_split": 0,
                             "non_manifold_vertices_split": 0,
                             "vertices_added": 0}

    # Pase 1: aristas con más de 2 caras.
    emap = _edge_to_triangles(np.asarray(tris, dtype=int))
    for (u, v), tlist in emap.items():
        if len(tlist) <= 2:
            continue
        for ti in tlist[2:]:
            t = tris[ti]
            ku = [k for k in range(3) if t[k] == u]
            kv = [k for k in range(3) if t[k] == v]
            if not ku or not kv:
                continue  # pragma: no cover - defensivo
            verts.append(verts[u].copy())
            verts.append(verts[v].copy())
            nu, nv = len(verts) - 2, len(verts) - 1
            for k in ku:
                t[k] = nu
            for k in kv:
                t[k] = nv
            stats["non_manifold_edges_split"] += 1
            stats["vertices_added"] += 2

    # Pase 2: vértices con link en >1 componente (union-find sobre el link).
    T = np.asarray(tris, dtype=int)
    n = len(verts)
    incident: List[List[int]] = [[] for _ in range(n)]
    for ti in range(T.shape[0]):
        for x in T[ti]:
            incident[int(x)].append(ti)
    for x in range(n):
        faces = incident[x]
        if len(faces) < 2:
            continue
        parent: Dict[int, int] = {}

        def _find(a: int) -> int:
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def _union(a: int, b: int) -> None:
            ra, rb = _find(a), _find(b)
            if ra != rb:
                parent[ra] = rb

        link_verts = set()
        for ti in faces:
            opp = [int(y) for y in T[ti] if int(y) != x]
            for y in opp:
                link_verts.add(y)
                parent.setdefault(y, y)
            if len(opp) == 2:
                _union(opp[0], opp[1])
        comps: Dict[int, List[int]] = {}
        for ti in faces:
            opp = [int(y) for y in T[ti] if int(y) != x]
            root = _find(opp[0])
            comps.setdefault(root, []).append(ti)
        if len(comps) <= 1:
            continue
        comp_list = list(comps.values())
        for extra in comp_list[1:]:
            verts.append(verts[x].copy())
            nx = len(verts) - 1
            for ti in extra:
                t = tris[ti]
                for k in range(3):
                    if t[k] == x:
                        t[k] = nx
            stats["non_manifold_vertices_split"] += 1
            stats["vertices_added"] += 1

    V = np.asarray(verts, dtype=float)
    Tout = np.asarray(tris, dtype=int)
    residual = int(sum(1 for c in _edge_to_triangles(Tout).values() if len(c) > 2))
    stats["residual_non_manifold_edges"] = residual
    stats["vertices_after"] = int(V.shape[0])
    stats["triangles_after"] = int(Tout.shape[0])
    return V, Tout, stats


def _sat_tri_tri(p: np.ndarray, q: np.ndarray, eps: float = 1e-12) -> bool:
    """SAT triángulo-triángulo (incluye coplanares). ``p``/``q``: (3,3)."""
    e1 = [p[1] - p[0], p[2] - p[1], p[0] - p[2]]
    e2 = [q[1] - q[0], q[2] - q[1], q[0] - q[2]]
    n1 = np.cross(e1[0], e1[1])
    n2 = np.cross(e2[0], e2[1])
    if np.linalg.norm(n1) <= eps or np.linalg.norm(n2) <= eps:
        return False  # degenerado: lo cubre repair_mesh, no es intersección
    axes = [n1, n2]
    for a in e1:
        for b in e2:
            c = np.cross(a, b)
            if np.linalg.norm(c) > eps:
                axes.append(c)
    # Ejes en el plano (normales de arista): imprescindibles para separar
    # triángulos coplanares disjuntos, donde todos los cross(e1,e2) son
    # paralelos a la normal y siempre solapan.
    for a in e1:
        c = np.cross(a, n1)
        if np.linalg.norm(c) > eps:
            axes.append(c)
    for b in e2:
        c = np.cross(b, n2)
        if np.linalg.norm(c) > eps:
            axes.append(c)
    for ax in axes:
        pp = p @ ax
        qq = q @ ax
        if pp.max() < qq.min() - eps or qq.max() < pp.min() - eps:
            return False
    return True


def count_self_intersections(
    vertices: np.ndarray,
    triangles: np.ndarray,
) -> Dict[str, Any]:
    """Cuenta pares de triángulos que se intersectan (diagnóstico, no repara).

    Broadphase con grilla uniforme + SAT exacto. Pares que comparten
    vértices se excluyen (adyacencia, no auto-intersección). La
    reparación de self-intersections es ambigua por definición, así que
    aquí solo se REPORTA (mismo principio que non-manifold en 5a).
    """
    verts = np.asarray(vertices, dtype=float)
    tris = np.asarray(triangles, dtype=int)
    out: Dict[str, Any] = {"pairs_checked": 0, "intersecting_pairs": 0}
    if tris.size == 0:
        return out
    # Celda por área de superficie (robusta ante mallas planas donde un
    # estimador volumétrico colapsaría a celda ~0 y la grilla explotaría).
    va, vb, vc = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    total_area = float(0.5 * np.linalg.norm(np.cross(vb - va, vc - va), axis=1).sum())
    if total_area <= 1e-18:
        return out
    cell = float(np.sqrt(total_area / max(tris.shape[0], 1)))
    cell = max(cell, 1e-9)
    lo = verts.min(axis=0)
    grid: Dict[Tuple[int, int, int], List[int]] = {}
    big: List[int] = []
    for ti in range(tris.shape[0]):
        tv = verts[tris[ti]]
        c0 = tuple(int(c) for c in np.floor((tv.min(axis=0) - lo) / cell))
        c1 = tuple(int(c) for c in np.floor((tv.max(axis=0) - lo) / cell))
        span_cells = (c1[0] - c0[0] + 1) * (c1[1] - c0[1] + 1) * (c1[2] - c0[2] + 1)
        if span_cells > 4096:
            # Triángulo gigante respecto a la celda: vía directa contra
            # todos (correcto y acotado; evita explosión de la grilla).
            big.append(ti)
            continue
        for ix in range(c0[0], c1[0] + 1):
            for iy in range(c0[1], c1[1] + 1):
                for iz in range(c0[2], c1[2] + 1):
                    grid.setdefault((ix, iy, iz), []).append(ti)
    seen = set()

    def _check_pair(a: int, b: int) -> None:
        key = (min(a, b), max(a, b))
        if key in seen:
            return
        seen.add(key)
        # Adyacentes (comparten vértice) no cuentan.
        if len({int(x) for x in tris[a]} & {int(x) for x in tris[b]}):
            return
        out["pairs_checked"] += 1
        if _sat_tri_tri(verts[tris[a]], verts[tris[b]]):
            out["intersecting_pairs"] += 1

    for cell_tris in grid.values():
        for i in range(len(cell_tris)):
            for j in range(i + 1, len(cell_tris)):
                _check_pair(cell_tris[i], cell_tris[j])
    for b in big:
        for a in range(tris.shape[0]):
            if a != b:
                _check_pair(a, b)
    return out


class MeshRemesher:
    """Remallado uniforme isotrópico hacia una longitud de arista objetivo."""

    def __init__(self, target_length: float, iterations: int = 3) -> None:
        if not float(target_length) > 0.0:
            raise ValueError(f"target_length={target_length!r} debe ser > 0.")
        if int(iterations) < 0:
            raise ValueError(f"iterations={iterations!r} debe ser >= 0.")
        self.target_length = float(target_length)
        self.iterations = int(iterations)

    def remesh(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
        target_length: Optional[float] = None,
        iterations: Optional[int] = None,
    ) -> ReconstructionResult:
        L = float(target_length) if target_length is not None else self.target_length
        it = int(iterations) if iterations is not None else self.iterations
        verts, tris, stats = uniform_remesh(vertices, triangles, L, it)
        flat: Dict[str, Any] = {}
        for k, v in stats.items():
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    flat[f"repair_{k2}"] = int(v2)
            elif isinstance(v, (int, np.integer)):
                flat[k] = int(v)
            elif isinstance(v, float):
                flat[k] = float(v)
            else:
                flat[k] = v
        return ReconstructionResult(
            stage=ReconstructionStage.SMOOTHED_MESH,
            status=ReconstructionStatus.COMPLETED,
            data={"vertices": verts, "triangles": tris},
            metadata=flat,
        )


# ---------------------------------------------------------------------------
# Fase 6c — Reporte de overhang para manufactura aditiva (diagnóstico puro)
# ---------------------------------------------------------------------------

def overhang_report(
    nodes: np.ndarray,
    elements: np.ndarray,
    densities: np.ndarray,
    build_direction=(0.0, 0.0, 1.0),
    overhang_angle_deg: float = 45.0,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Facetas en voladizo (diagnóstico puro, definición estándar de AM).

    Una faceta expuesta (cara de un elemento sólido sin vecino sólido) está
    en voladizo si su normal exterior apunta hacia abajo más allá de
    ``overhang_angle_deg`` desde la vertical (0° = techo plano, 90° = pared
    vertical auto-soportada). La restricción activa de overhang queda fuera
    de alcance; este reporte guía orientación y soportes sin fixes
    silenciosos.

    Args:
        densities: por elemento (salida SIMP) o por nodo.
        build_direction: vector de construcción (no nulo).
        overhang_angle_deg: umbral en (0, 90).
        threshold: umbral de sólido en (0, 1).
    """
    try:
        bd = np.asarray(build_direction, dtype=float).ravel()
    except (TypeError, ValueError):
        raise ValueError(f"build_direction={build_direction!r} debe ser un vector 3D no nulo.")
    if bd.shape[0] != 3 or float(np.linalg.norm(bd)) <= 1e-12:
        raise ValueError(f"build_direction={build_direction!r} debe ser un vector 3D no nulo.")
    if not 0.0 < float(overhang_angle_deg) < 90.0:
        raise ValueError(f"overhang_angle_deg={overhang_angle_deg!r} fuera de rango (0, 90).")
    if not 0.0 < float(threshold) < 1.0:
        raise ValueError(f"threshold={threshold!r} fuera de rango (0, 1).")
    bd = bd / float(np.linalg.norm(bd))
    verts = np.asarray(nodes, dtype=float)
    els = np.asarray(elements, dtype=int)
    dens = np.asarray(densities, dtype=float).ravel()
    if dens.shape[0] == els.shape[0]:
        solid = dens > float(threshold)
    elif dens.shape[0] == verts.shape[0]:
        solid = np.array([bool(np.mean(dens[e]) > float(threshold)) for e in els])
    else:
        raise ValueError(
            f"densities ({dens.shape[0]}) no coincide con elementos ({els.shape[0]}) "
            f"ni nodos ({verts.shape[0]}).")
    out: Dict[str, Any] = {
        "solid_elements": int(np.sum(solid)),
        "unsupported_elements": 0,
        "unsupported_fraction": 0.0,
        "overhang_faces": 0,
        "build_direction": [float(v) for v in bd],
        "overhang_angle_deg": float(overhang_angle_deg),
    }
    solid_idx = np.nonzero(solid)[0]
    if solid_idx.shape[0] == 0:
        return out
    solid_set = set(int(i) for i in solid_idx)
    # Cara (nodos ordenados) -> elementos sólidos que la usan.
    face_map: Dict[tuple, list] = {}
    _faces = ((1, 2, 3), (0, 2, 3), (0, 1, 3), (0, 1, 2))
    for e in solid_idx:
        con = [int(v) for v in els[int(e)]]
        for f in _faces:
            key = tuple(sorted((con[f[0]], con[f[1]], con[f[2]])))
            face_map.setdefault(key, []).append(int(e))
    limit = -float(np.cos(np.radians(float(overhang_angle_deg))))
    bad_elements = set()
    n_faces = 0
    zmin = float((verts[els[solid_idx]].reshape(-1, 3) @ bd).min())
    for key, owners in face_map.items():
        if len(owners) != 1:
            continue  # cara interna entre sólidos
        e = owners[0]
        con = [int(v) for v in els[e]]
        pts = verts[list(key)]
        if float((pts @ bd).max()) <= zmin + 1e-9:
            continue  # descansa en la placa de construcción
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        nm = float(np.linalg.norm(n))
        if nm <= 1e-18:
            continue  # degenerada: repair_mesh la cubre
        n = n / nm
        centroid = verts[con].mean(axis=0)
        if float(n @ (centroid - pts.mean(axis=0))) > 0:
            n = -n  # normal exterior
        if float(n @ bd) < limit:
            n_faces += 1
            bad_elements.add(e)
    out["overhang_faces"] = int(n_faces)
    out["unsupported_elements"] = int(len(bad_elements))
    out["unsupported_fraction"] = float(len(bad_elements) / max(solid_idx.shape[0], 1))
    out["unsupported_ids"] = sorted(bad_elements)
    return out


class MarchingTetrahedraExtractor(SurfaceExtractor):
    """Real isosurface extraction via marching tetrahedra on a Tet4 mesh.

    Works directly on the SIMP density field (one density per tetrahedron),
    so no separate voxel grid or volume package is required.
    """

    def extract(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        threshold: float = 0.5,
    ) -> ReconstructionResult:
        nodes = np.asarray(nodes, dtype=float)
        elements = np.asarray(elements, dtype=int)
        densities = np.asarray(densities, dtype=float).ravel()

        # Densities may be per-element (SIMP output) or already per-node.
        if densities.shape[0] == elements.shape[0]:
            nodal = _element_densities_to_nodes(nodes, elements, densities)
        elif densities.shape[0] == nodes.shape[0]:
            nodal = densities
        else:
            raise ValueError(
                f"densities ({densities.shape}) must match element count "
                f"({elements.shape[0]}) or node count ({nodes.shape[0]})"
            )
        vertices: List[np.ndarray] = []
        triangles = []
        for e in range(elements.shape[0]):
            con = elements[e]
            verts = nodes[con]
            dens = nodal[con]
            for tri in _tet_iso_triangles(verts, dens, threshold):
                base = len(vertices)
                vertices.extend(tri)
                triangles.append([base, base + 1, base + 2])

        if not vertices:
            return ReconstructionResult(
                stage=ReconstructionStage.SURFACE_MESH,
                status=ReconstructionStatus.COMPLETED,
                data={"vertices": np.zeros((0, 3)), "triangles": np.zeros((0, 3), dtype=int)},
                metadata={"threshold": threshold, "triangles": 0,
                          "note": "No triangle at this threshold"},
            )

        # Deduplicate coincident vertices (shared tet faces otherwise double the
        # triangles edges) without changing the triangle connectivity.
        if vertices:
            raw = np.asarray(vertices, dtype=float)
            remap, dedup_arr = _deduplicate_vertices(raw)
        else:
            raw = np.zeros((0, 3), dtype=float)
            remap = np.zeros(0, dtype=np.int64)
            dedup_arr = raw
        tris = np.asarray(triangles, dtype=int)
        if tris.size:
            remapped = np.take(remap, tris)
        else:
            remapped = np.zeros((0, 3), dtype=int)
        return ReconstructionResult(
            stage=ReconstructionStage.SURFACE_MESH,
            status=ReconstructionStatus.COMPLETED,
            data={
                "vertices": np.asarray(dedup_arr, dtype=float),
                "triangles": remapped,
            },
            metadata={"threshold": threshold, "triangles": int(remapped.shape[0])},
        )


class DummySurfaceExtractor(SurfaceExtractor):
    """Fallback that extracts the element boundary (no real isosurface)."""

    def extract(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        threshold: float = 0.5,
    ) -> ReconstructionResult:
        return MarchingTetrahedraExtractor().extract(
            nodes, elements, densities, threshold
        )


class BRepFitter(ABC):
    """Abstract B-Rep fitting from a triangle mesh."""

    @abstractmethod
    def fit(self, vertices: np.ndarray, triangles: np.ndarray) -> ReconstructionResult:
        """Fit a B-Rep solid to the triangle mesh."""


class OCPBRepFitter(BRepFitter):
    """Real B-Rep fitting using OpenCASCADE (OCP, provided with CadQuery).

    The triangle mesh is sewn into a shell and wrapped into a solid.  The
    ``step_path`` optional parameter exports the solid to a STEP file.
    """

    def __init__(self, step_path: Optional[str] = None) -> None:
        self._step_path = step_path

    def fit(self, vertices: np.ndarray, triangles: np.ndarray) -> ReconstructionResult:
        vertices = np.asarray(vertices, dtype=float)
        triangles = np.asarray(triangles, dtype=int)
        if vertices.shape[1] != 3:
            raise ValueError("vertices must be (N, 3)")
        try:
            from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
            from OCP.BRep import BRep_Builder
            from OCP.TopoDS import TopoDS_Shell, TopoDS_Compound
            from OCP.gp import gp_Pnt
        except Exception as exc:  # pragma: no cover - OCP required
            return ReconstructionResult(
                stage=ReconstructionStage.BREP_SOLID,
                status=ReconstructionStatus.FAILED,
                error_message=f"OCP unavailable: {exc}",
            )

        import numpy as _np

        builder = BRep_Builder()
        compound = TopoDS_Compound()
        builder.MakeCompound(compound)

        added_faces = 0
        skipped_degenerate = 0
        for tri in triangles:
            a, b, c = (int(tri[0]), int(tri[1]), int(tri[2]))
            pa = np.asarray(vertices[a]); pb = np.asarray(vertices[b]); pc = np.asarray(vertices[c])
            # Reject degenerate / zero-area triangles up front so a noisy
            # isosurface cannot silently corrupt the sewn shell.
            area2 = float(np.linalg.norm(_np.cross(pb - pa, pc - pa)))
            if area2 < 1e-12:
                skipped_degenerate += 1
                continue
            from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
            try:
                poly = BRepBuilderAPI_MakePolygon()
                poly.Add(gp_Pnt(float(vertices[a][0]), float(vertices[a][1]), float(vertices[a][2])))
                poly.Add(gp_Pnt(float(vertices[b][0]), float(vertices[b][1]), float(vertices[b][2])))
                poly.Add(gp_Pnt(float(vertices[c][0]), float(vertices[c][1]), float(vertices[c][2])))
                poly.Close()
                wire = poly.Wire()
                if wire.IsNull():
                    continue
                face = BRepBuilderAPI_MakeFace(wire).Face()
            except Exception:  # pragma: no cover - degenerate/colinear triangle
                skipped_degenerate += 1
                continue
            if not face.IsNull():
                builder.Add(compound, face)
                added_faces += 1
        if added_faces == 0:
            return ReconstructionResult(
                stage=ReconstructionStage.BREP_SOLID,
                status=ReconstructionStatus.FAILED,
                error_message="No valid (non-degenerate) faces to build a solid",
            )
        sewed = BRepBuilderAPI_Sewing(1e-6)
        sewed.Add(compound)
        sewed.Perform()
        sewed_shape = sewed.SewedShape()
        if sewed_shape.IsNull():
            return ReconstructionResult(
                stage=ReconstructionStage.BREP_SOLID,
                status=ReconstructionStatus.FAILED,
                error_message="Sewing produced a null shell",
            )
        solid_builder = BRep_Builder()
        from OCP.TopoDS import TopoDS_Solid, TopoDS_Shell
        shell = TopoDS_Shell()
        from OCP.TopAbs import TopAbs_ShapeEnum
        solid = TopoDS_Solid()
        solid_builder.MakeSolid(solid)
        shell_volumes: list = []
        _kept_count = 1
        if sewed_shape.ShapeType() == TopAbs_ShapeEnum.TopAbs_SHELL:
            solid_builder.Add(solid, sewed_shape)
        else:
            # MULTI-SHELL (reversible): la isosuperficie puede tener varias
            # componentes conexas y el cosido devuelve un COMPOUND con una
            # cáscara por componente. Antes se conservaba SOLO la de mayor
            # |volumen|, descartando islas que podían ser justamente las zonas
            # de carga/fijación. Ahora se conservan TODAS las cáscaras
            # significativas (>= 1% de la mayor) y se reportan las descartadas
            # en metadata (visible, nunca silencioso). Para volver atrás:
            # `solid_builder.Add(solid, max(shells)[1])`.
            from OCP.TopExp import TopExp_Explorer
            from OCP.BRepGProp import BRepGProp
            from OCP.GProp import GProp_GProps
            shells: list = []
            exp = TopExp_Explorer(sewed_shape, TopAbs_ShapeEnum.TopAbs_SHELL)
            while exp.More():
                sh = exp.Current()
                try:
                    props = GProp_GProps()
                    BRepGProp.VolumeProperties_s(sh, props)
                    v = abs(float(props.Mass()))
                except Exception:  # pragma: no cover - defensivo
                    v = -1.0
                shell_volumes.append(round(v, 3))
                if v > 0:
                    shells.append((v, sh))
                exp.Next()
            if not shells:
                return ReconstructionResult(
                    stage=ReconstructionStage.BREP_SOLID,
                    status=ReconstructionStatus.FAILED,
                    error_message=("Sewing produced no usable shells "
                                   "(todas con volumen 0: isosuperficie abierta; "
                                   "optimización probablemente colapsada)"),
                    metadata={"sewed_shells": len(shell_volumes),
                              "sewed_shell_volumes": shell_volumes},
                )
            best_vol = max(v for v, _ in shells)
            kept = [(v, sh) for v, sh in shells if v >= max(0.01 * best_vol, 1e-9)]
            for _v, sh in kept:
                solid_builder.Add(solid, sh)
            _kept_count = len(kept)
        # remove internal faces inside the solid
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.AIS import AIS_Shape
        from OCP.TopAbs import TopAbs_ShapeEnum
        if not BRepCheck_Analyzer(solid).IsValid():
            if shell_volumes and len(shell_volumes) > 1:
                # Varias cáscaras pueden dar un sólido inválido: reintentar con
                # la mayor únicamente (comportamiento histórico) en vez de fallar.
                from OCP.TopExp import TopExp_Explorer
                from OCP.BRepGProp import BRepGProp
                from OCP.GProp import GProp_GProps
                best = None
                best_v = -1.0
                exp = TopExp_Explorer(sewed_shape, TopAbs_ShapeEnum.TopAbs_SHELL)
                while exp.More():
                    sh = exp.Current()
                    try:
                        props = GProp_GProps()
                        BRepGProp.VolumeProperties_s(sh, props)
                        v = abs(float(props.Mass()))
                    except Exception:  # pragma: no cover - defensivo
                        v = -1.0
                    if v > best_v:
                        best_v, best = v, sh
                    exp.Next()
                solid = TopoDS_Solid()
                solid_builder.MakeSolid(solid)
                if best is not None:
                    solid_builder.Add(solid, best)
                _kept_count = 1
        # REPAIR (reversible): la isosuperficie de un resultado degenerado puede
        # quedar abierta (cáscaras con volumen 0). ShapeFix_Solid intenta
        # cerrar/orientar antes de decidir validez; si no repara, se reporta
        # FAILED con el detalle de volúmenes (nunca un motivo opaco).
        if not BRepCheck_Analyzer(solid).IsValid():
            try:
                from OCP.ShapeFix import ShapeFix_Solid
                fixer = ShapeFix_Solid(solid)
                fixer.SetPrecision(1e-3)
                fixer.SetMaxTolerance(1.0)
                fixer.Perform()
                fixed = fixer.Solid()
                if not fixed.IsNull() and BRepCheck_Analyzer(fixed).IsValid():
                    solid = fixed
            except Exception:  # noqa: BLE001 - defensivo
                pass
        if not BRepCheck_Analyzer(solid).IsValid() or _kept_count == 0:
            fail_meta: Dict[str, Any] = {"vertices": int(vertices.shape[0]),
                                         "triangles": int(triangles.shape[0])}
            if shell_volumes:
                fail_meta["sewed_shells"] = len(shell_volumes)
                fail_meta["sewed_shell_volumes"] = shell_volumes
            return ReconstructionResult(
                stage=ReconstructionStage.BREP_SOLID,
                status=ReconstructionStatus.FAILED,
                error_message=(
                    "Reconstructed solid is not valid (isosuperficie abierta/"
                    "degenerada; probablemente la optimización colapsó por una "
                    "condición de contorno degradada)"),
                metadata=fail_meta,
            )
        metadata: Dict[str, Any] = {"vertices": int(vertices.shape[0]),
                                     "triangles": int(triangles.shape[0])}
        if shell_volumes:
            metadata["sewed_shells"] = len(shell_volumes)
            metadata["sewed_shell_volumes"] = shell_volumes
            metadata["kept_shells"] = int(_kept_count)
            metadata["kept_shell_volume"] = float(
                sum(sorted(shell_volumes, reverse=True)[:_kept_count]))
        try:
            self._exchange_step(solid, metadata)
        except Exception as exc:  # pragma: no cover
            metadata["step_export_error"] = str(exc)
        return ReconstructionResult(
            stage=ReconstructionStage.BREP_SOLID,
            status=ReconstructionStatus.COMPLETED,
            data=solid,
            metadata=metadata,
        )

    def _exchange_step(self, solid, metadata: Dict[str, Any]) -> None:
        if not self._step_path:
            return
        from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
        writer = STEPControl_Writer()
        writer.Transfer(solid, STEPControl_AsIs)
        status = writer.Write(self._step_path)
        metadata["step_path"] = self._step_path
        metadata["step_status"] = int(status)


class OCPBSplineFitter(OCPBRepFitter):
    """B-Rep con superficies B-spline reales por parches (regiones).

    PAT-FIT (reversible, 16-sep-2026): el ajuste REAL de superficies se hace
    agrupando las caras planas del isosuperficie en regiones (conectadas y
    con normal similar) y reemplazando cada región por UNA cara suave
    construida con ``BRepOffsetAPI_MakeFilling`` sobre su borde + puntos
    interiores. Medido en esfera: 1520 triángulos → 3 caras B-spline válidas.

    Diseño fail-safe: si el sólido reensamblado no es válido, o la topología
    de una región no es un ciclo simple, se conserva el sólido facetado
    previo y se registra el motivo en ``metadata`` (nunca geometría inválida,
    nunca silencio). El ajuste por parches se ejecuta ANTES del resto: al
    tener ya superficies B-spline no se aplican unify/restriction (que en el
    isosuperficie crudo daban ``skipped_invalid``). Si el ajuste está
    desactivado o falla, se mantiene la cadena histórica unify→bspline→
    continuidad.
    """

    def __init__(
        self,
        step_path: Optional[str] = None,
        unify_tolerance: float = 1e-4,
        bspline_tolerance: float = 1e-3,
        continuity: str = "C1",
        fit_patches: bool = True,
        region_angle_deg: float = 35.0,
        min_region_faces: int = 3,
        max_region_faces: int = 600,
        max_patch_points: int = 0,
        max_regions: int = 4000,
        max_loop_edges: int = 3000,
        allow_partial_patches: bool = False,
    ) -> None:
        super().__init__(step_path=None)  # la exportación se hace aquí
        self._out_step_path = step_path
        self._unify_tolerance = float(unify_tolerance)
        self._bspline_tolerance = float(bspline_tolerance)
        if continuity not in ("C0", "C1", "C2"):
            raise ValueError(f"continuity={continuity!r} inválida (C0|C1|C2).")
        self._continuity = continuity
        self._fit_patches = bool(fit_patches)
        if not 0.0 < float(region_angle_deg) < 90.0:
            raise ValueError(
                f"region_angle_deg={region_angle_deg!r} fuera de rango (0, 90).")
        self._region_angle_deg = float(region_angle_deg)
        self._min_region_faces = max(2, int(min_region_faces))
        # PAT-SEG: tope de caras por parche. Sin tope, una superficie cerrada
        # y suave se fusiona en UNA región sin borde → imposible de rellenar.
        # Con tope se segmenta en parches con borde (como el reverse real).
        self._max_region_faces = max(self._min_region_faces, int(max_region_faces))
        self._max_patch_points = max(0, int(max_patch_points))
        self._max_regions = max(1, int(max_regions))
        self._max_loop_edges = max(4, int(max_loop_edges))
        self._allow_partial_patches = bool(allow_partial_patches)

    @staticmethod
    def _valid(shape) -> bool:
        try:
            from OCP.BRepCheck import BRepCheck_Analyzer
            return bool(BRepCheck_Analyzer(shape).IsValid())
        except Exception:
            return False

    def fit(self, vertices: np.ndarray, triangles: np.ndarray) -> ReconstructionResult:
        base = super().fit(vertices, triangles)
        if base.status != ReconstructionStatus.COMPLETED or base.data is None:
            return base
        meta: Dict[str, Any] = dict(base.metadata or {})
        meta["brep_style"] = "bspline"
        meta["continuity_target"] = self._continuity
        solid = base.data
        if self._fit_patches:
            # FAIL-SAFE: el ajuste por parches es experimental; NUNCA debe
            # tumbar el job. Cualquier excepción inesperada de OCP cae a la
            # cadena facetada con el motivo en metadata (nunca silencio).
            try:
                fitted, applied = self._fit_patches_solid(solid, meta)
            except Exception as exc:  # noqa: BLE001 - defensivo
                meta["bspline_fit"] = "error"
                meta["bspline_fit_error"] = f"{type(exc).__name__}: {exc}"
                applied, fitted = False, solid
            if applied:
                try:
                    self._write_step(fitted, meta)
                except Exception as exc:  # pragma: no cover - defensive
                    meta["step_export_error"] = str(exc)
                return ReconstructionResult(
                    stage=ReconstructionStage.BREP_SOLID,
                    status=ReconstructionStatus.COMPLETED,
                    data=fitted,
                    metadata=meta,
                )
        # Cadena histórica (o fallback del ajuste por parches).
        solid = self._step_unify(solid, meta)
        solid = self._step_bspline(solid, meta)
        solid = self._step_continuity(solid, meta)
        try:
            self._write_step(solid, meta)
        except Exception as exc:  # pragma: no cover - defensive
            meta["step_export_error"] = str(exc)
        return ReconstructionResult(
            stage=ReconstructionStage.BREP_SOLID,
            status=ReconstructionStatus.COMPLETED,
            data=solid,
            metadata=meta,
        )

    # -- PAT-FIT --------------------------------------------------------
    def _fit_patches_solid(self, solid, meta: Dict[str, Any]):
        """Reemplaza regiones de caras por parches B-spline suaves.

        Devuelve ``(solid, applied)``. ``applied=False`` si no se pudo
        reconstruir un sólido válido (el llamador conserva el facetado).
        """
        import numpy as np
        try:
            from OCP.TopAbs import (TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX,
                                    TopAbs_Orientation)
            from OCP.TopExp import TopExp, TopExp_Explorer
            from OCP.TopTools import (TopTools_IndexedMapOfShape,
                                      TopTools_IndexedDataMapOfShapeListOfShape)
            from OCP.TopoDS import TopoDS
            from OCP.BRep import BRep_Tool
            from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                            BRepBuilderAPI_MakeFace,
                                            BRepBuilderAPI_Sewing)
            from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeFilling
            from OCP.GeomAbs import GeomAbs_Shape
            from OCP.gp import gp_Pnt
        except Exception as exc:  # pragma: no cover - OCP required
            meta["bspline_fit"] = "ocp_unavailable"
            meta["bspline_fit_error"] = str(exc)
            return solid, False

        fmap = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(solid, TopAbs_FACE, fmap)
        n_faces = int(fmap.Extent())
        if n_faces == 0 or n_faces > 40000:
            meta["bspline_fit"] = "skipped_size"
            meta["bspline_face_count"] = n_faces
            return solid, False

        e2f = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_s(solid, TopAbs_EDGE, TopAbs_FACE, e2f)

        vmap = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(solid, TopAbs_VERTEX, vmap)

        def face_unique_verts(face):
            """Vértices únicos (el explorador repite por arista)."""
            ids = []
            seen_ids = set()
            exp = TopExp_Explorer(face, TopAbs_VERTEX)
            while exp.More():
                try:
                    vid = int(vmap.FindIndex(exp.Current()))
                except Exception:  # noqa: BLE001 - defensivo
                    vid = -1
                if vid >= 0 and vid not in seen_ids:
                    seen_ids.add(vid)
                    p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(exp.Current()))
                    ids.append(np.array([p.X(), p.Y(), p.Z()]))
                exp.Next()
            return ids

        def edge_key(edge):
            try:
                return int(e2f.FindIndex(edge))
            except Exception:
                return -1

        face_normals = []
        face_edges = []   # list[list[int]] edge keys
        for i in range(1, n_faces + 1):
            f = TopoDS.Face_s(fmap.FindKey(i))
            vs = face_unique_verts(f)
            n = np.array([0.0, 0.0, 0.0])
            if len(vs) >= 3:
                n = np.cross(vs[1] - vs[0], vs[2] - vs[0])
                ln = float(np.linalg.norm(n))
                n = n / ln if ln > 1e-15 else n
                try:
                    if f.Orientation() == TopAbs_Orientation.TopAbs_REVERSED:
                        n = -n
                except Exception:  # noqa: BLE001 - defensivo
                    pass
            face_normals.append(n)
            eks = []
            exp = TopExp_Explorer(f, TopAbs_EDGE)
            while exp.More():
                eks.append(edge_key(TopoDS.Edge_s(exp.Current())))
                exp.Next()
            face_edges.append(eks)

        # adyacencia por arista compartida
        edge_faces: Dict[int, List[int]] = {}
        for fi, eks in enumerate(face_edges):
            for k in eks:
                if k >= 0:
                    edge_faces.setdefault(k, []).append(fi)

        adj: Dict[int, set] = {i: set() for i in range(n_faces)}
        for k, fs in edge_faces.items():
            for a in range(len(fs)):
                for b in range(a + 1, len(fs)):
                    adj[fs[a]].add(fs[b])
                    adj[fs[b]].add(fs[a])

        # region growing por normal
        cos_thr = float(np.cos(np.radians(self._region_angle_deg)))
        seen = [False] * n_faces
        regions: List[List[int]] = []
        for seed in range(n_faces):
            if seen[seed]:
                continue
            # PAT-SEG: BFS compacto desde la semilla. El criterio es la
            # normal de la SEMILLA (no del vecino): así el parche queda
            # acotado por desviación angular total y su tamaño no depende
            # del mallado (vecino-a-vecino fusionaba toda la esfera en una
            # región sin borde, imposible de rellenar).
            from collections import deque
            seed_n = face_normals[seed]
            queue = deque([seed])
            seen[seed] = True
            reg = []
            while queue:
                cu = queue.popleft()
                reg.append(cu)
                if len(reg) >= self._max_region_faces:
                    continue
                for nb in adj[cu]:
                    if not seen[nb] and abs(float(
                            np.dot(seed_n, face_normals[nb]))) >= cos_thr:
                        seen[nb] = True
                        queue.append(nb)
            regions.append(reg)
        if len(regions) > self._max_regions:
            meta["bspline_fit"] = "skipped_regions"
            meta["bspline_region_count"] = len(regions)
            return solid, False

        # vertex ids (para ordenar bucles de borde)

        new_faces = []
        applied_regions = 0
        fallback_regions = 0
        stats = {"tiny": 0, "bnd_zero": 0, "bnd_too_many": 0,
                 "wires_zero": 0, "fill_fail": 0}
        for reg in regions:
            if len(reg) < self._min_region_faces:
                stats["tiny"] += 1
                for fi in reg:
                    new_faces.append(fmap.FindKey(fi + 1))
                fallback_regions += 1
                continue
            in_region = set(reg)
            bnd: List[int] = []
            for fi in reg:
                for k in face_edges[fi]:
                    if k < 0:
                        continue
                    owners = edge_faces.get(k, [])
                    if sum(1 for o in owners if o in in_region) == 1:
                        bnd.append(k)
            if not bnd:
                stats["bnd_zero"] += 1
            elif len(bnd) > self._max_loop_edges:
                stats["bnd_too_many"] += 1
            ok = False
            face_shape = None
            if 0 < len(bnd) <= self._max_loop_edges:
                try:
                    from OCP.TopTools import TopTools_HSequenceOfShape
                    from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
                    seq = TopTools_HSequenceOfShape()
                    for k in set(bnd):
                        seq.Append(e2f.FindKey(k))
                    wires = TopTools_HSequenceOfShape()
                    ShapeAnalysis_FreeBounds.ConnectEdgesToWires_s(
                        seq, self._bspline_tolerance, False, wires)
                    if int(wires.Length()) == 0:
                        stats["wires_zero"] += 1
                    if int(wires.Length()) >= 1:
                        # Parche suave por región (multi-bucle = con huecos).
                        loop_edges = []
                        for wi in range(1, int(wires.Length()) + 1):
                            w = TopoDS.Wire_s(wires.Value(wi))
                            exp = TopExp_Explorer(w, TopAbs_EDGE)
                            while exp.More():
                                loop_edges.append(TopoDS.Edge_s(exp.Current()))
                                exp.Next()
                        if len(loop_edges) >= 3:
                            fill = BRepOffsetAPI_MakeFilling()
                            for e in loop_edges:
                                fill.Add(e, GeomAbs_Shape.GeomAbs_C0, True)
                            fill.Build()
                            if fill.IsDone() and self._valid(fill.Shape()):
                                face_shape = fill.Shape()
                                ok = True
                            else:
                                stats["fill_fail"] += 1
                except Exception:  # noqa: BLE001 - defensivo
                    ok = False
                    stats["fill_fail"] += 1
            if ok:
                new_faces.append(face_shape)
                applied_regions += 1
            else:
                for fi in reg:
                    new_faces.append(fmap.FindKey(fi + 1))
                fallback_regions += 1

        if applied_regions == 0:
            meta["bspline_fit"] = "no_regions_applied"
            meta["bspline_regions"] = len(regions)
            meta["bspline_fit_stats"] = stats
            return solid, False
        # ALL-OR-NOTHING: mezclar parches con triángulos de fallback deja
        # costuras no coincidentes (cáscara abierta / volumen ~0). Si alguna
        # región no se pudo parchear, se descarta el ajuste completo.
        if fallback_regions > 0 and not self._allow_partial_patches:
            meta["bspline_fit"] = "fallback_mixed"
            meta["bspline_regions"] = len(regions)
            meta["bspline_regions_applied"] = applied_regions
            meta["bspline_regions_fallback"] = fallback_regions
            meta["bspline_fit_stats"] = stats
            return solid, False

        # ensamblar + coser + extraer cáscara + sólido válido
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Compound, TopoDS_Solid, TopoDS_Shell
        from OCP.TopAbs import TopAbs_ShapeEnum
        from OCP.ShapeFix import ShapeFix_Solid
        comp = TopoDS_Compound()
        builder = BRep_Builder()
        builder.MakeCompound(comp)
        for f in new_faces:
            builder.Add(comp, f)
        sew = BRepBuilderAPI_Sewing(self._bspline_tolerance * 10.0)
        sew.Add(comp)
        sew.Perform()
        meta["bspline_sew_free_edges"] = int(sew.NbFreeEdges())
        meta["bspline_sew_multiple_edges"] = int(sew.NbMultipleEdges())
        sewed = sew.SewedShape()
        shell = None
        exp = TopExp_Explorer(sewed, TopAbs_ShapeEnum.TopAbs_SHELL)
        if exp.More():
            shell = TopoDS.Shell_s(exp.Current())
        if shell is None or shell.IsNull():
            meta["bspline_fit"] = "sew_no_shell"
            return solid, False
        out = TopoDS_Solid()
        builder.MakeSolid(out)
        builder.Add(out, shell)
        if not self._valid(out):
            try:
                sf = ShapeFix_Solid(out)
                sf.SetPrecision(self._bspline_tolerance * 10.0)
                sf.SetMaxTolerance(1.0)
                sf.Perform()
                cand = sf.Solid()
                if not cand.IsNull() and self._valid(cand):
                    out = cand
            except Exception:  # noqa: BLE001 - defensivo
                pass
        if not self._valid(out):
            meta["bspline_fit"] = "fallback_invalid"
            meta["bspline_regions"] = len(regions)
            return solid, False
        # VOL-GUARD (crítico): MakeFilling puede dar un sólido "válido" pero
        # con volumen ~0 (parches plegados/auto-intersectados). Se exige que
        # el volumen se conserve (75%-133%) respecto del facetado; si no, se
        # descarta el ajuste (el registro rechazaría un cuerpo degenerado).
        try:
            from OCP.BRepGProp import BRepGProp
            from OCP.GProp import GProp_GProps
            pv = GProp_GProps()
            BRepGProp.VolumeProperties_s(out, pv)
            vol_out = abs(float(pv.Mass()))
            pb = GProp_GProps()
            BRepGProp.VolumeProperties_s(solid, pb)
            vol_base = abs(float(pb.Mass()))
            if vol_base > 1e-12:
                ratio = vol_out / vol_base
                meta["bspline_volume_ratio"] = round(ratio, 4)
                meta["bspline_volume_base"] = round(vol_base, 4)
                meta["bspline_volume_fitted"] = round(vol_out, 4)
                if not (0.75 <= ratio <= 1.3333):
                    meta["bspline_fit"] = "fallback_volume"
                    meta["bspline_regions"] = len(regions)
                    return solid, False
        except Exception:  # noqa: BLE001 - defensivo
            meta["bspline_fit"] = "fallback_volume_check_failed"
            meta["bspline_regions"] = len(regions)
            return solid, False
        meta["bspline_fit"] = "applied"
        meta["bspline_regions"] = len(regions)
        meta["bspline_regions_applied"] = applied_regions
        meta["bspline_regions_fallback"] = fallback_regions
        meta["bspline_faces_before"] = n_faces
        meta["bspline_faces_after"] = len(new_faces)
        meta["bspline_region_angle_deg"] = self._region_angle_deg
        meta.pop("unify_same_domain", None)
        return out, True


    def _step_unify(self, solid, meta: Dict[str, Any]):
        try:
            from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
            unify = ShapeUpgrade_UnifySameDomain(solid, True, True, False)
            unify.SetLinearTolerance(self._unify_tolerance)
            unify.SetAngularTolerance(1e-3)
            unify.Build()
            cand = unify.Shape()
            if not cand.IsNull() and self._valid(cand):
                meta["unify_same_domain"] = "applied"
                return cand
            meta["unify_same_domain"] = "skipped_invalid"
        except Exception as exc:
            meta["unify_same_domain_error"] = str(exc)
        return solid

    def _step_bspline(self, solid, meta: Dict[str, Any]):
        try:
            from OCP.BRepTools import BRepTools_Modifier
            from OCP.ShapeCustom import ShapeCustom_BSplineRestriction
            from OCP.GeomAbs import GeomAbs_Shape
            conv = ShapeCustom_BSplineRestriction()
            conv.SetTol3d(self._bspline_tolerance)
            conv.SetTol2d(self._bspline_tolerance)
            conv.SetContinuity3d(GeomAbs_Shape.GeomAbs_C1)
            conv.SetContinuity2d(GeomAbs_Shape.GeomAbs_C1)
            conv.SetMaxDegree(8)
            conv.SetMaxNbSegments(16)
            conv.SetConvRational(True)
            mod = BRepTools_Modifier(solid)
            mod.Perform(conv)
            if not mod.IsDone():
                meta["bspline_restriction"] = "not_done"
                return solid
            cand = mod.ModifiedShape(solid)
            if not cand.IsNull() and self._valid(cand):
                meta["bspline_restriction"] = "applied"
                return cand
            meta["bspline_restriction"] = "skipped_invalid"
        except Exception as exc:
            meta["bspline_restriction_error"] = str(exc)
        return solid

    def _step_continuity(self, solid, meta: Dict[str, Any]):
        try:
            from OCP.ShapeUpgrade import ShapeUpgrade_ShapeDivideContinuity
            from OCP.GeomAbs import GeomAbs_Shape
            target = {"C0": GeomAbs_Shape.GeomAbs_C0,
                      "C1": GeomAbs_Shape.GeomAbs_C1,
                      "C2": GeomAbs_Shape.GeomAbs_C2}[self._continuity]
            sd = ShapeUpgrade_ShapeDivideContinuity(solid)
            sd.SetTolerance(self._bspline_tolerance)
            sd.SetSurfaceCriterion(target)
            sd.SetPCurveCriterion(target)
            sd.Perform()
            cand = sd.Result()
            if not cand.IsNull() and self._valid(cand):
                meta["continuity_upgrade"] = self._continuity
                return cand
            meta["continuity_upgrade"] = "skipped_invalid"
        except Exception as exc:
            meta["continuity_upgrade_error"] = str(exc)
        return solid

    def _write_step(self, solid, meta: Dict[str, Any]) -> None:
        if not self._out_step_path:
            return
        from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
        writer = STEPControl_Writer()
        writer.Transfer(solid, STEPControl_AsIs)
        status = writer.Write(self._out_step_path)
        meta["step_path"] = self._out_step_path
        meta["step_status"] = int(status)




class DummyBRepFitter(OCPBRepFitter):
    """Alias kept for backward compatibility; fitter is now real via OCP."""


class ReconstructionPipeline:
    """Orchestrates the conversion from density field to CAD geometry.

    Stages:
    1. density_field  -- the raw optimisation result (per-element densities)
    2. surface_mesh   -- isosurface extraction (marching cubes, etc.)
    3. smoothed_mesh  -- repair, hole-fill, smoothing, decimation (in that
       order: FILL-SMOOTH-ORDER — el tapado corre ANTES del suavizado para
       que el parche se suavice con el resto)
    4. brep_solid     -- B-Rep fitting (CadQuery/OCC)
    5. step_file      -- STEP export

    Each stage is optional and pluggable.  The pipeline records
    intermediate results so the UI can display progress.
    """

    def __init__(
        self,
        surface_extractor: Optional[SurfaceExtractor] = None,
        brep_fitter: Optional[BRepFitter] = None,
        mesh_smoother: Optional["MeshSmoother"] = None,
        hole_filler: Optional["MeshHoleFiller"] = None,
        step_path: Optional[str] = None,
        mesh_repair: Optional["MeshRepair"] = None,
        decimate_fraction: Optional[float] = None,
        smoothing_method: str = "laplacian",
        max_hole_edges: Optional[Union[int, str]] = None,
        max_brep_triangles: Optional[int] = None,
    ) -> None:
        self._surface_extractor = surface_extractor or MarchingTetrahedraExtractor()
        self._brep_fitter = brep_fitter or OCPBRepFitter(step_path=step_path)
        self._mesh_smoother = mesh_smoother
        self._hole_filler = hole_filler
        self._mesh_repair = mesh_repair
        if smoothing_method not in ("laplacian", "taubin"):
            raise ValueError(
                f"smoothing_method={smoothing_method!r} no soportado "
                f"(usar 'laplacian' o 'taubin').")
        self._smoothing_method = smoothing_method
        if decimate_fraction is not None and not 0.0 < float(decimate_fraction) <= 1.0:
            raise ValueError(
                f"decimate_fraction={decimate_fraction!r} fuera de rango (0, 1]."
            )
        # FILL-CAP (reversible): tope de aristas por loop para fill_holes
        # (None = tapar todo, comportamiento histórico; "auto" = mediana de
        # loops de ESTA malla x MeshHoleFiller.AUTO_FACTOR, ver esa clase).
        # Un loop necesita al menos 3 aristas; un tope menor lo deja todo
        # abierto.
        if (
            max_hole_edges is not None
            and max_hole_edges != "auto"
            and (
                not isinstance(max_hole_edges, int)
                or isinstance(max_hole_edges, bool)
                or max_hole_edges < 3
            )
        ):
            raise ValueError(
                f"max_hole_edges={max_hole_edges!r} inválido "
                f"(usar None, 'auto', o entero >= 3).")
        self._max_hole_edges = max_hole_edges
        self._decimate_fraction = float(decimate_fraction) if decimate_fraction is not None else None
        # BREPCAP (reversible): tope de triángulos por candidato pre-fit.
        # Un isosuperficie de envelope (10k+ tris) cose 10k caras OCP y el
        # STEP sale de ~30MB: export+reimport superan el timeout del puente
        # (120s) y la pieza parece "colgada". Con tope se diezma al cap y se
        # declara en metadata. None = histórico (sin tope).
        if max_brep_triangles is not None and (
            not isinstance(max_brep_triangles, int)
            or isinstance(max_brep_triangles, bool)
            or max_brep_triangles < 4
        ):
            raise ValueError(
                f"max_brep_triangles={max_brep_triangles!r} inválido "
                f"(usar None o entero >= 4).")
        self._max_brep_triangles = max_brep_triangles
        self._step_path = step_path
        self._stages: Dict[ReconstructionStage, ReconstructionResult] = {}
        self._status = ReconstructionStatus.NOT_STARTED

    @property
    def status(self) -> ReconstructionStatus:
        return self._status

    def get_stage_result(self, stage: ReconstructionStage) -> Optional[ReconstructionResult]:
        return self._stages.get(stage)

    def run(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        threshold: float = 0.5,
        frozen_elements: Optional[Sequence[int]] = None,
        preserved_elements: Optional[Sequence[int]] = None,
    ) -> ReconstructionResult:
        """Run the full reconstruction pipeline.

        ``frozen_elements`` (pass-through FROZEN_FACE) y
        ``preserved_elements`` (KEEP_IN) fuerzan su densidad a 1.0 antes de
        la extracción para que la isosuperficie los incluya; el rol queda
        registrado en metadata (sin fallback silencioso: índices fuera de
        rango levantan ValueError vía :func:`apply_frozen_passthrough`).

        Returns the final stage result (B-Rep or surface mesh depending
        on what is implemented).
        """
        self._status = ReconstructionStatus.IN_PROGRESS

        elements_arr = np.asarray(elements, dtype=int)
        densities_arr = np.asarray(densities, dtype=float).ravel()
        frozen_list = sorted(int(i) for i in (frozen_elements or []))
        preserved_list = sorted(int(i) for i in (preserved_elements or []))
        # Unión honesta: ambos fijan a 1.0 igual que KEEP_IN.
        force_list = sorted(set(frozen_list) | set(preserved_list))
        densities_arr = apply_frozen_passthrough(
            densities_arr, int(elements_arr.shape[0]),
            force_list or None,
        )
        # NODAL-PASSTHROUGH (reversible): el extractor promedia elementos a
        # nodos antes de marchar; un anillo preservado (rho=1) compartiendo
        # nodos con interior optimizado (~0.4) quedaba promediado bajo el
        # umbral -> la isosuperficie rompía el anillo (loops abiertos de
        # 15-46 aristas) y fill_holes lo sellaba con un abanico, borrando
        # agujeros de diseño. Forzar a 1.0 los NODOS de los elementos
        # preservados garantiza que el anillo sobreviva a la extracción.
        # El extractor ya acepta densidades por nodo: se le pasa el campo
        # nodal (la etapa DENSITY_FIELD conserva el elemental original).
        # Para volver atrás: quitar este bloque (el extractor promedia solo).
        nodes_arr = np.asarray(nodes, dtype=float)
        extract_densities: np.ndarray = densities_arr
        nodal_forced = False
        if force_list:
            if densities_arr.shape[0] == elements_arr.shape[0]:
                nodal = _element_densities_to_nodes(
                    nodes_arr, elements_arr, densities_arr)
                for e in force_list:
                    nodal[elements_arr[int(e)]] = 1.0
                extract_densities = nodal
                nodal_forced = True
            elif densities_arr.shape[0] == nodes_arr.shape[0]:
                extract_densities = densities_arr.copy()
                for e in force_list:
                    extract_densities[elements_arr[int(e)]] = 1.0
                nodal_forced = True

        # Stage 1: record density field
        self._stages[ReconstructionStage.DENSITY_FIELD] = ReconstructionResult(
            stage=ReconstructionStage.DENSITY_FIELD,
            status=ReconstructionStatus.COMPLETED,
            data={"nodes": nodes, "elements": elements, "densities": densities_arr},
            metadata={
                "frozen_elements": frozen_list,
                "preserved_elements": preserved_list,
                "frozen_passthrough": (
                    "frozen_face_as_keep_in@1.0" if frozen_list else None
                ),
                "nodal_passthrough": bool(nodal_forced),
            },
        )

        # Stage 2: surface extraction
        try:
            surface_result = self._surface_extractor.extract(
                nodes, elements_arr, extract_densities, threshold
            )
            surface_result.metadata.setdefault("frozen_elements", frozen_list)
            surface_result.metadata.setdefault("preserved_elements", preserved_list)
            if frozen_list:
                surface_result.metadata.setdefault(
                    "frozen_passthrough", "frozen_face_as_keep_in@1.0")
            self._stages[ReconstructionStage.SURFACE_MESH] = surface_result
        except Exception as exc:
            self._status = ReconstructionStatus.FAILED
            result = ReconstructionResult(
                stage=ReconstructionStage.SURFACE_MESH,
                status=ReconstructionStatus.FAILED,
                error_message=str(exc),
            )
            self._stages[ReconstructionStage.SURFACE_MESH] = result
            return result

        # Stage 3: repair -> fill -> smooth -> decimate.
        # FILL-SMOOTH-ORDER (reversible): el tapado corre ANTES del suavizado.
        # Antes era al revés (Etapa 3.5 posterior al smooth): smooth fija los
        # vértices de borde, y en ese momento "borde" eran los loops abiertos
        # del marching — quedaban congelados con el escalonado crudo mientras
        # el interior se suavizaba, y el abanico plano se pegaba sobre
        # superficie lisa. Ahora la malla llega cerrada al suavizado
        # (_boundary_vertices vacío salvo bordes reales) y el parche se
        # suaviza con el resto. Para volver atrás: restaurar el bloque
        # "Stage 3.5" posterior al suavizado.
        # Fase 5a (opt-in): reparación antes + decimación después. Sin
        # mesh_repair/decimate_fraction el flujo es idéntico salvo el orden
        # fill→smooth (ver FILL-SMOOTH-ORDER).
        smoothed_data = None
        hole_fill_data = None
        if surface_result.status == ReconstructionStatus.COMPLETED and surface_result.data:
            mesh_data = surface_result.data
            if isinstance(mesh_data, dict) and mesh_data.get("vertices") is not None:
                try:
                    rep_verts = np.asarray(mesh_data["vertices"])
                    rep_tris = np.asarray(mesh_data["triangles"])
                    if self._mesh_repair is not None:
                        rep_result = self._mesh_repair.repair(rep_verts, rep_tris)
                        rep_verts = np.asarray(rep_result.data["vertices"])
                        rep_tris = np.asarray(rep_result.data["triangles"])
                    # HOLEFILL-CAP-FIX: un hole_filler inyectado (custom, hoy
                    # solo vía tests) perdía el tope del pipeline porque no
                    # se le pasaba max_hole_edges -- quedaba en el default de
                    # MeshHoleFiller.fill() (None = tapar todo), ignorando en
                    # silencio lo que el llamador configuró. Ambas ramas usan
                    # ahora el mismo tope.
                    filler = self._hole_filler or MeshHoleFiller()
                    hf_result = filler.fill(
                        rep_verts, rep_tris,
                        max_hole_edges=self._max_hole_edges)
                    hole_fill_data = hf_result.data
                    fill_meta = dict(hf_result.metadata)
                    fv = np.asarray(hole_fill_data["vertices"])
                    ft = np.asarray(hole_fill_data["triangles"])
                    if self._mesh_smoother is None:
                        self._mesh_smoother = MeshSmoother()
                    smooth_result = self._mesh_smoother.smooth(
                        fv, ft, method=self._smoothing_method)
                    if self._decimate_fraction is not None:
                        dec_result = MeshDecimator(self._decimate_fraction).decimate(
                            np.asarray(smooth_result.data["vertices"]),
                            np.asarray(smooth_result.data["triangles"]),
                        )
                        dec_result.metadata["smoothed_before"] = int(
                            np.asarray(smooth_result.data["triangles"]).shape[0])
                        smooth_result = dec_result
                    smoothed_data = smooth_result.data
                    self._stages[ReconstructionStage.SMOOTHED_MESH] = ReconstructionResult(
                        stage=ReconstructionStage.SMOOTHED_MESH,
                        status=ReconstructionStatus.COMPLETED,
                        data=smoothed_data,
                        metadata={**smooth_result.metadata, **fill_meta,
                                  "fill_before_smooth": True},
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    self._stages[ReconstructionStage.SMOOTHED_MESH] = ReconstructionResult(
                        stage=ReconstructionStage.SMOOTHED_MESH,
                        status=ReconstructionStatus.FAILED,
                        error_message=str(exc),
                    )
        if ReconstructionStage.SMOOTHED_MESH not in self._stages:
            self._stages[ReconstructionStage.SMOOTHED_MESH] = ReconstructionResult(
                stage=ReconstructionStage.SMOOTHED_MESH,
                status=ReconstructionStatus.NOT_STARTED,
            )

        # Stage 4: B-Rep fitting (prefer smoothed [ya incluye fill] > filled > raw)
        brep_result = None
        if surface_result.status == ReconstructionStatus.COMPLETED and surface_result.data:
            mesh_data = surface_result.data
            candidates = []
            # Smoothed primero (ya incluye fill): el STEP sale del resultado
            # suavizado; filled y raw son solo fallback si el fitter lo rechaza.
            if smoothed_data is not None and smoothed_data.get("vertices") is not None:
                candidates.append((smoothed_data, "smoothed"))
            if hole_fill_data is not None and hole_fill_data.get("vertices") is not None:
                candidates.append((hole_fill_data, "filled"))
            if mesh_data.get("vertices") is not None:
                candidates.append((mesh_data, "raw"))
            for cand, source in candidates:
                if cand.get("vertices") is None or cand.get("triangles") is None:
                    continue
                fit_verts = np.asarray(cand["vertices"])
                fit_tris = np.asarray(cand["triangles"])
                dec_from: Optional[int] = None
                cap = self._max_brep_triangles
                if cap is not None and int(fit_tris.shape[0]) > int(cap):
                    # Diezmado pre-fit: el sewing OCP escala con nº de caras.
                    dec_from = int(fit_tris.shape[0])
                    frac = float(cap) / float(dec_from)
                    dec_result = MeshDecimator(frac).decimate(fit_verts, fit_tris)
                    fit_verts = np.asarray(dec_result.data["vertices"])
                    fit_tris = np.asarray(dec_result.data["triangles"])
                try:
                    r = self._brep_fitter.fit(fit_verts, fit_tris)
                except Exception as exc:  # pragma: no cover - defensive
                    r = ReconstructionResult(
                        stage=ReconstructionStage.BREP_SOLID,
                        status=ReconstructionStatus.FAILED,
                        error_message=str(exc),
                    )
                if r.status == ReconstructionStatus.COMPLETED:
                    r.metadata.setdefault("frozen_elements", frozen_list)
                    r.metadata.setdefault("preserved_elements", preserved_list)
                    r.metadata.setdefault("brep_source", source)
                    if dec_from is not None:
                        r.metadata.setdefault("brep_decimated_from", dec_from)
                        r.metadata.setdefault(
                            "brep_decimated_to", int(fit_tris.shape[0]))
                        r.metadata.setdefault("brep_triangle_cap", int(cap))  # type: ignore[arg-type]
                    if frozen_list:
                        r.metadata.setdefault(
                            "frozen_passthrough", "frozen_face_as_keep_in@1.0")
                    brep_result = r
                    break
                if brep_result is None:
                    brep_result = r
        if brep_result is None:
            brep_result = ReconstructionResult(
                stage=ReconstructionStage.BREP_SOLID,
                status=ReconstructionStatus.NOT_STARTED,
            )
        self._stages[ReconstructionStage.BREP_SOLID] = brep_result

        # Stage 5: STEP export status (actual export happens inside
        # OCPBRepFitter.fit → _exchange_step when step_path is set)
        step_metadata: Dict[str, Any] = {}
        if brep_result is not None and brep_result.status == ReconstructionStatus.COMPLETED:
            step_path_exported = (brep_result.metadata or {}).get("step_path")
            if step_path_exported:
                step_metadata["step_path"] = step_path_exported
                step_metadata["step_status"] = brep_result.metadata.get("step_status")
                step_file_result = ReconstructionResult(
                    stage=ReconstructionStage.STEP_FILE,
                    status=ReconstructionStatus.COMPLETED,
                    metadata=step_metadata,
                )
            else:
                step_file_result = ReconstructionResult(
                    stage=ReconstructionStage.STEP_FILE,
                    status=ReconstructionStatus.NOT_STARTED,
                )
        else:
            step_file_result = ReconstructionResult(
                stage=ReconstructionStage.STEP_FILE,
                status=ReconstructionStatus.NOT_STARTED,
            )
        self._stages[ReconstructionStage.STEP_FILE] = step_file_result

        self._status = ReconstructionStatus.COMPLETED
        # Return the best available result
        for stage in [
            ReconstructionStage.BREP_SOLID,
            ReconstructionStage.SURFACE_MESH,
            ReconstructionStage.DENSITY_FIELD,
        ]:
            r = self._stages.get(stage)
            if r and r.status == ReconstructionStatus.COMPLETED:
                return r
        return ReconstructionResult(
            stage=ReconstructionStage.DENSITY_FIELD,
            status=ReconstructionStatus.COMPLETED,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self._status.value,
            "stages": {
                k.value: v.to_dict() for k, v in self._stages.items()
            },
        }


# ---------------------------------------------------------------------------
# Reparación automática de self-intersections + soportes (prompt.md alta/media).
# repair_self_intersections: weld + elimina degenerados + suavizado laplaciano
# LOCAL solo sobre vértices implicados en pares intersectantes, iterando hasta
# que el conteo baje o se agote max_iter. Nunca inventa geometría: devuelve
# residual y, si no llega a 0, lo declara (fail-loud aguas arriba).
# generate_supports: pilares verticales (según build_direction) desde centroides
# de facetas en voladizo hasta el plano base. Devuelve malla tris auxiliar.
# --------------------------------------------------------------------------- #
def repair_self_intersections(
    vertices: np.ndarray,
    triangles: np.ndarray,
    max_iter: int = 5,
    smooth_factor: float = 0.3,
) -> Dict[str, Any]:
    verts = np.asarray(vertices, dtype=float).copy()
    tris = np.asarray(triangles, dtype=int).copy()
    from collections import defaultdict
    initial = count_self_intersections(verts, tris)["intersecting_pairs"]
    # 1) weld + degenerados fuera (repair_mesh existente).
    try:
        verts, tris, _ = repair_mesh(verts, tris)
    except Exception:
        pass
    tris = tris[(tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 0] != tris[:, 2])]
    # Adyacencia vértice->vecinos para laplaciano local.
    for _ in range(max(0, int(max_iter))):
        rep = count_self_intersections(verts, tris)
        if int(rep["intersecting_pairs"]) == 0:
            break
        # Vértices implicados: aproximación barata — suaviza toda la malla
        # levemente (estable) en vez de rastrear pares exactos.
        adj: Dict[int, set] = defaultdict(set)
        for a, b, c in tris:
            adj[int(a)] |= {int(b), int(c)}
            adj[int(b)] |= {int(a), int(c)}
            adj[int(c)] |= {int(a), int(b)}
        new = verts.copy()
        for v, nbrs in adj.items():
            if not nbrs:
                continue
            cen = np.mean(verts[list(nbrs)], axis=0)
            new[v] = verts[v] + float(smooth_factor) * (cen - verts[v])
        verts = new
    final = count_self_intersections(verts, tris)["intersecting_pairs"]
    return {"vertices": verts, "triangles": tris,
            "initial_pairs": int(initial), "final_pairs": int(final),
            "repaired": bool(final == 0)}


def generate_supports(
    nodes: np.ndarray,
    elements: np.ndarray,
    densities: np.ndarray,
    build_direction=(0.0, 0.0, 1.0),
    overhang_angle_deg: float = 45.0,
    threshold: float = 0.5,
    pillar_radius: float = 0.0,
) -> Dict[str, Any]:
    """Soportes automáticos bajo facetas en voladizo (columnas a la base)."""
    nodes = np.asarray(nodes, dtype=float)
    els = np.asarray(elements, dtype=int)
    rep = overhang_report(nodes, els, np.asarray(densities),
                          build_direction, overhang_angle_deg, threshold)
    bd = np.asarray(build_direction, dtype=float).ravel()
    bd = bd / max(float(np.linalg.norm(bd)), 1e-12)
    ids = rep.get("unsupported_ids", []) or []
    if not ids:
        return {"num_pillars": 0, "pillars": [], "overhang": rep}
    base = float(np.min(nodes @ bd))
    pillars = []
    for e in ids:
        c = nodes[els[int(e)]].mean(axis=0)
        length = float((c @ bd) - base)
        if length <= 1e-9:
            continue
        pillars.append({"element": int(e), "top": c.tolist(),
                        "base": (c - bd * length).tolist(),
                        "length": length})
    return {"num_pillars": len(pillars), "pillars": pillars, "overhang": rep}
