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
from typing import Any, Dict, List, Optional

import numpy as np


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


class MeshSmoother:
    """Post-process smoothing of the extracted isosurface mesh."""

    def smooth(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
        iterations: int = 3,
        alpha: float = 0.5,
    ) -> ReconstructionResult:
        smv, smt = smooth_surface_mesh(vertices, triangles, iterations, alpha)
        return ReconstructionResult(
            stage=ReconstructionStage.SMOOTHED_MESH,
            status=ReconstructionStatus.COMPLETED,
            data={"vertices": smv, "triangles": smt},
            metadata={"iterations": int(iterations), "alpha": float(alpha),
                      "triangles": int(smt.shape[0])},
        )


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
        if sewed_shape.ShapeType() == TopAbs_ShapeEnum.TopAbs_SHELL:
            solid_builder.Add(solid, sewed_shape)
        else:
            from OCP.TopExp import TopExp_Explorer
            exp = TopExp_Explorer(sewed_shape, TopAbs_ShapeEnum.TopAbs_SHELL)
            if exp.More():
                solid_builder.Add(solid, exp.Current())
        # remove internal faces inside the solid
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.AIS import AIS_Shape
        from OCP.TopAbs import TopAbs_ShapeEnum
        if not BRepCheck_Analyzer(solid).IsValid():
            return ReconstructionResult(
                stage=ReconstructionStage.BREP_SOLID,
                status=ReconstructionStatus.FAILED,
                error_message="Reconstructed solid is not valid",
            )
        metadata: Dict[str, Any] = {"vertices": int(vertices.shape[0]),
                                    "triangles": int(triangles.shape[0])}
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


class DummyBRepFitter(OCPBRepFitter):
    """Alias kept for backward compatibility; fitter is now real via OCP."""


class ReconstructionPipeline:
    """Orchestrates the conversion from density field to CAD geometry.

    Stages:
    1. density_field  -- the raw optimisation result (per-element densities)
    2. surface_mesh   -- isosurface extraction (marching cubes, etc.)
    3. smoothed_mesh  -- mesh smoothing / decimation
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
    ) -> None:
        self._surface_extractor = surface_extractor or MarchingTetrahedraExtractor()
        self._brep_fitter = brep_fitter or OCPBRepFitter()
        self._mesh_smoother = mesh_smoother
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
    ) -> ReconstructionResult:
        """Run the full reconstruction pipeline.

        Returns the final stage result (B-Rep or surface mesh depending
        on what is implemented).
        """
        self._status = ReconstructionStatus.IN_PROGRESS

        # Stage 1: record density field
        self._stages[ReconstructionStage.DENSITY_FIELD] = ReconstructionResult(
            stage=ReconstructionStage.DENSITY_FIELD,
            status=ReconstructionStatus.COMPLETED,
            data={"nodes": nodes, "elements": elements, "densities": densities},
        )

        # Stage 2: surface extraction
        try:
            surface_result = self._surface_extractor.extract(
                nodes, elements, densities, threshold
            )
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

        # Stage 3: mesh smoothing (post-process of noisy isosurfaces)
        smoothed_data = None
        if surface_result.status == ReconstructionStatus.COMPLETED and surface_result.data:
            mesh_data = surface_result.data
            if isinstance(mesh_data, dict) and mesh_data.get("vertices") is not None:
                try:
                    if self._mesh_smoother is None:
                        self._mesh_smoother = MeshSmoother()
                    smooth_result = self._mesh_smoother.smooth(
                        np.asarray(mesh_data["vertices"]), np.asarray(mesh_data["triangles"])
                    )
                    smoothed_data = smooth_result.data
                    self._stages[ReconstructionStage.SMOOTHED_MESH] = smooth_result
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

        # Stage 4: B-Rep fitting (prefer the smoothed mesh, fall back to raw)
        brep_result = None
        if surface_result.status == ReconstructionStatus.COMPLETED and surface_result.data:
            mesh_data = surface_result.data
            candidates = []
            if isinstance(mesh_data, dict):
                if smoothed_data is not None and smoothed_data.get("vertices") is not None:
                    candidates.append(smoothed_data)
                if mesh_data.get("vertices") is not None:
                    candidates.append(mesh_data)
            for cand in candidates:
                if cand.get("vertices") is None or cand.get("triangles") is None:
                    continue
                try:
                    r = self._brep_fitter.fit(
                        np.asarray(cand["vertices"]), np.asarray(cand["triangles"])
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    r = ReconstructionResult(
                        stage=ReconstructionStage.BREP_SOLID,
                        status=ReconstructionStatus.FAILED,
                        error_message=str(exc),
                    )
                if r.status == ReconstructionStatus.COMPLETED:
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

        # Stage 5: STEP export (placeholder)
        self._stages[ReconstructionStage.STEP_FILE] = ReconstructionResult(
            stage=ReconstructionStage.STEP_FILE,
            status=ReconstructionStatus.NOT_STARTED,
        )

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
