"""Scene - owns the model geometry, mesh and result representations in the viewport.

Separates (per prompt) the concepts of: scene / camera / geometry / visual
representation / selection / renderer. This module manages *what* is displayed
and *how* (shaded / wireframe / transparent / density color map). It talks only
to the :class:`Renderer`; it never touches the raw VTK API directly beyond what
the renderer exposes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import numpy as np


# Multi-stop density colormaps: list of (t, r, g, b) with t in [0, 1].
_COLORMAPS: Dict[str, list] = {
    "jet": [
        (0.0, 0.00, 0.00, 0.50), (0.15, 0.00, 0.00, 1.00),
        (0.35, 0.00, 0.50, 1.00), (0.5, 0.00, 1.00, 1.00),
        (0.65, 0.50, 1.00, 0.00), (0.85, 1.00, 1.00, 0.00),
        (1.0, 0.85, 0.20, 0.15),
    ],
    "viridis": [
        (0.0, 0.267, 0.004, 0.329), (0.25, 0.223, 0.322, 0.568),
        (0.5, 0.127, 0.567, 0.550), (0.75, 0.267, 0.784, 0.439),
        (1.0, 0.993, 0.906, 0.145),
    ],
    "coolwarm": [
        (0.0, 0.230, 0.299, 0.754), (0.5, 0.867, 0.867, 0.867),
        (1.0, 0.706, 0.016, 0.150),
    ],
    "inferno": [
        (0.0, 0.000, 0.000, 0.216), (0.25, 0.253, 0.086, 0.517),
        (0.5, 0.568, 0.152, 0.434), (0.75, 0.866, 0.303, 0.196),
        (1.0, 0.987, 0.741, 0.063),
    ],
}



@dataclass
class SceneObject:
    """Base record for a renderable object in the scene."""
    name: str
    kind: str            # "model" | "mesh" | "density" | "force" | "constraint"
    actor_key: str = ""
    visible: bool = True
    props: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.actor_key:
            self.actor_key = f"{self.kind}:{self.name}"


class Scene:
    def __init__(self, renderer, camera) -> None:
        self._renderer = renderer
        self._camera = camera
        self._objects: Dict[str, SceneObject] = {}
        self._actors: Dict[str, Any] = {}
        self._bbox = None
        self._center = np.array([0.0, 0.0, 0.0])
        self._radius = 1.0
        self.display_mode = "surfaced"
        self._on_change: Callable[[], None] | None = None
        self._grid_visible = True
        self._axes_visible = True

        # Entity-level geometry (model actor) for cell -> CAD face resolution
        self._model_vertices: Optional[np.ndarray] = None
        self._model_triangles: Optional[np.ndarray] = None
        self._tri_face_index: Optional[np.ndarray] = None   # per-triangle face_index (-1 = unknown)
        self._faces_meta: Dict[int, Dict[str, Any]] = {}
        self._model_actor_key: Optional[str] = None
        self._highlight_actor_key: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #
    def set_change_callback(self, cb: Callable[[], None]) -> None:
        self._on_change = cb

    def _notify(self) -> None:
        if self._on_change:
            self._on_change()

    # ------------------------------------------------------------------ #
    # Bounding / fit
    # ------------------------------------------------------------------ #
    def set_bounds(self, bbox):
        """Set scene extents from a BoundingBox3D-like object and refit camera."""
        if bbox is None:
            return
        self._bbox = bbox
        if hasattr(bbox, "center") and not callable(getattr(bbox, "center")):
            center = np.array(bbox.center, dtype=float).ravel()
        else:
            center = np.array([
                0.5 * (bbox.xmin + bbox.xmax),
                0.5 * (bbox.ymin + bbox.ymax),
                0.5 * (bbox.zmin + bbox.zmax),
            ])
        dx = bbox.dx if hasattr(bbox, "dx") else (bbox.xmax - bbox.xmin)
        dy = bbox.dy if hasattr(bbox, "dy") else (bbox.ymax - bbox.ymin)
        dz = bbox.dz if hasattr(bbox, "dz") else (bbox.zmax - bbox.zmin)
        radius = 0.5 * float(np.sqrt(dx * dx + dy * dy + dz * dz))
        radius = max(radius, 1e-4)
        self._center = center
        self._radius = radius
        if self._grid_visible:
            self.set_grid_visible(True)
        if self._axes_visible:
            self.set_axes_visible(True)

    @property
    def bounds(self):
        return self._bbox

    @property
    def center(self) -> np.ndarray:
        return self._center

    @property
    def radius(self) -> float:
        return self._radius

    def fit_camera(self) -> None:
        self._camera.set_target(self._center, self._radius, delta=4.0)
        self._camera.fit()

    def reset_fit(self) -> None:
        self.fit_camera()
        self._renderer.reset_camera()
        self._renderer.render()

    def center_model(self) -> None:
        self._camera.set_target(self._center, self._radius, delta=1.6)
        self._renderer.render()

    # ------------------------------------------------------------------ #
    # Object management
    # ------------------------------------------------------------------ #
    def add_object(self, scene_obj: SceneObject, actor) -> None:
        if scene_obj.actor_key in self._actors:
            return
        self._objects[scene_obj.actor_key] = scene_obj
        self._actors[scene_obj.actor_key] = actor
        self._renderer.add_actor(actor)

    def remove_object(self, key: str) -> None:
        if key in self._actors:
            self._renderer.remove_actor(self._actors.pop(key))
            self._objects.pop(key, None)

    def remove_by_kind(self, kind: str) -> None:
        for key in [k for k, o in self._objects.items() if o.kind == kind]:
            self.remove_object(key)

    def clear(self) -> None:
        keys = list(self._actors.keys())
        for key in keys:
            self.remove_object(key)
        self._bbox = None

    def set_visibility(self, key: str, visible: bool) -> None:
        scene_obj = self._objects.get(key)
        actor = self._actors.get(key)
        if scene_obj is None or actor is None:
            return
        scene_obj.visible = visible
        actor.SetVisibility(1 if visible else 0)
        self._notify()

    def get_actor(self, key: str):
        return self._actors.get(key)

    # ------------------------------------------------------------------ #
    # High-level geometry / mesh / results
    # ------------------------------------------------------------------ #
    def set_model_geometry(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
        face_index_map: Optional[np.ndarray] = None,
        faces_meta: Optional[list] = None,
    ) -> None:
        """Build the shaded triangle-mesh actor for the imported CAD surface.

        ``face_index_map`` is an optional per-triangle B-Rep face index (-1 for
        unknown) enabling entity-level (face) picking via the renderer cell data.
        """
        self.remove_by_kind("model")
        vertices = np.asarray(vertices, dtype=float)
        triangles = np.asarray(triangles, dtype=np.int64)
        self._model_vertices = vertices
        self._model_triangles = triangles
        self._tri_face_index = None
        self._faces_meta = {}
        self._build_faces_meta(faces_meta)

        cell_data = None
        if face_index_map is not None:
            face_index_map = np.asarray(face_index_map, dtype=np.int64)
            if face_index_map.shape[0] == triangles.shape[0]:
                self._tri_face_index = face_index_map
                cell_data = {"face_index": face_index_map}

        from desktop.ui.style import PALETTE, hex_to_rgb_float

        actor = self._renderer.make_triangle_actor(
            vertices,
            triangles,
            color=hex_to_rgb_float(PALETTE["solid_cad"]),
            cell_data=cell_data,
        )
        obj = SceneObject("Modelo CAD", "model")
        self.add_object(obj, actor)
        self._model_actor_key = obj.actor_key
        self._apply_display_mode(actor)
        self._notify()

    def _build_faces_meta(self, faces_meta: Optional[list]) -> None:
        if not faces_meta:
            return
        for meta in faces_meta:
            if not isinstance(meta, dict) or meta.get("face_index") is None:
                continue
            self._faces_meta[int(meta["face_index"])] = meta

    # ------------------------------------------------------------------ #
    # Entity-level selection helpers (sólido / cara / actor)
    # ------------------------------------------------------------------ #
    @property
    def model_actor_key(self) -> Optional[str]:
        return self._model_actor_key

    def face_index_for_cell(self, cell_id: int) -> Optional[int]:
        """Map a picked VTK triangle cell id back to a B-Rep face index."""
        if self._tri_face_index is None or cell_id < 0:
            return None
        if cell_id >= self._tri_face_index.shape[0]:
            return None
        fi = int(self._tri_face_index[cell_id])
        return fi if fi >= 0 else None

    def face_meta(self, face_index: int) -> Optional[Dict[str, Any]]:
        return self._faces_meta.get(int(face_index))

    def highlight_faces(self, face_indices: list) -> None:
        """Draw a translucent gold overlay on the given B-Rep face triangles.

        The overlay reuses the model triangles, so it is exactly coplanar with
        the shaded mesh. Without a small offset it z-fights the opaque mesh,
        which is why planar (front-facing) faces failed the depth test and
        curved faces showed only partial coverage. We therefore nudge the
        overlay vertices slightly outward (+normal) to lift it off the surface.
        """
        self.clear_highlight()
        if not face_indices or self._tri_face_index is None:
            return
        wanted = set(int(f) for f in face_indices)
        mask = np.isin(self._tri_face_index, np.array(sorted(wanted), dtype=np.int64))
        tris = self._model_triangles[mask]
        if tris.shape[0] == 0:
            self._renderer.render()
            return
        verts = self._model_vertices
        overlay_verts, overlay_tris = self._offset_overlay(verts, tris)
        actor = self._renderer.make_triangle_actor(
            overlay_verts,
            overlay_tris,
            color=(0.95, 0.72, 0.08),
            opacity=0.55,
            edge_color=(0.98, 0.9, 0.4),
            edge_visibility=True,
        )
        obj = SceneObject("Cara seleccionada", "selection_highlight")
        self.add_object(obj, actor)
        self._highlight_actor_key = obj.actor_key
        self._renderer.render()

    @staticmethod
    def _offset_overlay(verts: np.ndarray, tris: np.ndarray) -> tuple:
        """Return a copy of the overlay geometry lifted off the surface.

        Displaces the vertices used by ``tris`` along their (area-weighted
        average) face normal by a small epsilon proportional to the bounding
        box diagonal. The returned vertex array shares layout with ``verts`` so
        the tri indices remain valid. Degenerate triangles are skipped.
        """
        verts = np.asarray(verts, dtype=float)
        tris = np.asarray(tris, dtype=np.int64)
        overlay_verts = verts.copy()
        if tris.shape[0] == 0:
            return overlay_verts, tris

        extent = float(np.ptp(verts, axis=0).max())
        eps = (extent * 0.001) if extent > 0 else 1e-4

        v0 = verts[tris[:, 0]]
        v1 = verts[tris[:, 1]]
        v2 = verts[tris[:, 2]]
        n = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(n, axis=1, keepdims=True)
        norm[norm < 1e-12] = 1.0
        n = n / norm

        counts = np.zeros(verts.shape[0], dtype=np.int64)
        sums = np.zeros((verts.shape[0], 3), dtype=float)
        for k in range(3):
            idx = tris[:, k]
            np.add.at(sums, idx, n)
            np.add.at(counts, idx, 1)
        ok = counts > 0
        vnorm = np.zeros_like(verts)
        vnorm[ok] = sums[ok] / counts[ok][:, None]
        vnorm[ok] /= np.linalg.norm(vnorm[ok], axis=1, keepdims=True)

        overlay_verts[ok] += vnorm[ok] * eps
        return overlay_verts, tris

    def clear_highlight(self) -> None:
        if self._highlight_actor_key is not None:
            self.remove_object(self._highlight_actor_key)
            self._highlight_actor_key = None
            self._renderer.render()

    def clear(self) -> None:
        keys = list(self._actors.keys())
        for key in keys:
            self.remove_object(key)
        self._bbox = None
        self._model_vertices = None
        self._model_triangles = None
        self._tri_face_index = None
        self._faces_meta = {}
        self._model_actor_key = None
        self._highlight_actor_key = None

    def set_mesh(self, nodes: np.ndarray, elements: np.ndarray, color=(0.6, 0.65, 0.75)) -> None:
        """Render the volumetric FE mesh as an outlined surface."""
        tris = self._extract_mesh_surface(elements)
        self.remove_by_kind("mesh")
        actor = self._renderer.make_triangle_actor(
            nodes,
            tris,
            color=color,
            edge_color=(0.0, 0.0, 0.0),
            edge_visibility=True,
        )
        self.add_object(SceneObject("Malla FEM", "mesh"), actor)
        self._apply_display_mode(actor)
        self._notify()

    def _extract_mesh_surface(self, elements: np.ndarray) -> np.ndarray:
        """Collect the (potentially non-manifold) outer triangle soup of a Tet4 mesh."""
        tri_edges = []
        for tet in elements:
            a, b, c, d = int(tet[0]), int(tet[1]), int(tet[2]), int(tet[3])
            tri_edges.extend(
                [
                    tuple(sorted((a, b, c))),
                    tuple(sorted((a, b, d))),
                    tuple(sorted((a, c, d))),
                    tuple(sorted((b, c, d))),
                ]
            )
        count: Dict[tuple, int] = {}
        for t in tri_edges:
            count[t] = count.get(t, 0) + 1
        tris = [list(t) for t, c in count.items() if c == 1]
        return np.asarray(tris, dtype=np.int64).reshape(-1, 3) if tris else np.empty((0, 3), dtype=np.int64)

    # ------------------------------------------------------------------ #
    # Density field (topology result) — per-element scalar color map
    # ------------------------------------------------------------------ #
    def set_density_field(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        opacity: float = 0.92,
        colormap: str = "jet",
    ) -> None:
        """Render the Tet4 mesh colored by material density.

        ``colormap`` selects a multi-stop color transfer function (default
        ``"jet"`` used to be a simple blue->red; now a richer gradient is used
        for better readability).  Supported: ``"jet"``, ``"viridis"``,
        ``"coolwarm"``, ``"inferno"``.
        """
        from vtkmodules.vtkCommonDataModel import (
            vtkUnstructuredGrid, vtkCellArray,
        )
        from vtkmodules.vtkCommonCore import vtkFloatArray, vtkPoints
        from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper
        from vtkmodules.vtkRenderingCore import vtkColorTransferFunction

        nodes = np.asarray(nodes, dtype=float)
        elements = np.asarray(elements, dtype=int)
        densities = np.asarray(densities, dtype=float)

        # Tet4 mesh rendered as an unstructured grid (one vtkTetra per element)
        # so that each element carries its own density scalar for the color map.
        n = int(elements.shape[0])

        points = vtkPoints()
        points.SetData(self._points_array(nodes))
        cells = vtkCellArray()
        cells.SetCells(n, self._vtu_connectivity(elements))

        grid = vtkUnstructuredGrid()
        grid.SetPoints(points)
        grid.SetCells(10, cells)  # VTK_TETRA == 10

        scalar = vtkFloatArray()
        scalar.SetName("density")
        scalar.SetNumberOfComponents(1)
        scalar.SetNumberOfTuples(n)
        for i, d in enumerate(densities):
            scalar.SetValue(i, float(d))
        grid.GetCellData().SetScalars(scalar)

        ctf = self._density_colormap(colormap)

        mapper = vtkDataSetMapper()
        mapper.SetInputData(grid)
        mapper.SetScalarModeToUseCellData()
        mapper.SetColorModeToMapScalars()
        mapper.SetLookupTable(ctf)
        mapper.SetScalarRange(0.0, 1.0)
        mapper.ScalarVisibilityOn()

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetOpacity(opacity)
        actor.GetProperty().SetInterpolationToGouraud()
        actor.GetProperty().SetAmbient(0.35)
        actor.GetProperty().SetDiffuse(0.75)

        self.remove_by_kind("density")
        self.add_object(SceneObject("Densidad de material", "density"), actor)
        self._notify()

    @staticmethod
    def _density_colormap(colormap: str) -> "vtkColorTransferFunction":
        """Build a multi-stop density color transfer function."""
        from vtkmodules.vtkRenderingCore import vtkColorTransferFunction

        ctf = vtkColorTransferFunction()
        stops = _COLORMAPS.get(colormap, _COLORMAPS["jet"])
        for t, r, g, b in stops:
            ctf.AddRGBPoint(t, r, g, b)
        return ctf

    # ------------------------------------------------------------------ #
    # Display modes
    # ------------------------------------------------------------------ #
    def set_display_mode(self, mode: str) -> None:
        self.display_mode = mode
        for key, actor in self._actors.items():
            self._apply_display_mode(actor)

    def _apply_display_mode(self, actor) -> None:
        prop = actor.GetProperty()
        if self.display_mode == "wireframe":
            prop.SetRepresentationToWireframe()
            prop.SetEdgeVisibility(False)
        elif self.display_mode == "transparent":
            prop.SetRepresentationToSurface()
            prop.SetEdgeVisibility(False)
            prop.SetOpacity(0.45)
        elif self.display_mode == "surfaced_edges":
            prop.SetRepresentationToSurface()
            prop.SetEdgeVisibility(True)
            prop.SetOpacity(1.0)
        else:  # surfaced
            prop.SetRepresentationToSurface()
            prop.SetEdgeVisibility(False)
            prop.SetOpacity(1.0)
        self._renderer.render()

    # ------------------------------------------------------------------ #
    # Axes / grid (managed by renderer, toggled through scene for symmetry)
    # ------------------------------------------------------------------ #
    def set_axes_visible(self, visible: bool) -> None:
        self._axes_visible = visible
        extent = self._radius if self._radius else 1.0
        if visible:
            self._renderer.set_axes(extent * 1.2)
        else:
            self._renderer.remove_axes()
        self._renderer.render()

    def set_grid_visible(self, visible: bool) -> None:
        self._grid_visible = visible
        extent = self._radius if self._radius else 10.0
        if visible:
            self._renderer.set_grid(extent * 2.0, 10)
        else:
            self._renderer.remove_grid()
        self._renderer.render()

    # ------------------------------------------------------------------ #
    # Small helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _points_array(verts: np.ndarray):
        from vtkmodules.util.numpy_support import numpy_to_vtk
        arr = numpy_to_vtk(np.ascontiguousarray(verts, dtype=np.float32), deep=True)
        arr.SetNumberOfComponents(3)
        return arr

    @staticmethod
    def _vtu_connectivity(tets: np.ndarray):
        """Connectivity array for a vtkCellArray of Tet4 cells."""
        from vtkmodules.util.numpy_support import numpy_to_vtk
        from vtkmodules.vtkCommonCore import VTK_ID_TYPE
        n = int(tets.shape[0])
        conn = np.empty(n * 5, dtype=np.int64)
        conn[0::5] = 4
        conn[1::5] = tets[:, 0]
        conn[2::5] = tets[:, 1]
        conn[3::5] = tets[:, 2]
        conn[4::5] = tets[:, 3]
        arr = numpy_to_vtk(np.ascontiguousarray(conn), deep=True, array_type=VTK_ID_TYPE)
        arr.SetNumberOfComponents(1)
        return arr
