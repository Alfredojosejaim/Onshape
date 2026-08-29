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
        self._camera.set_target(self._center, self._radius, delta=2.2)
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
    def set_model_geometry(self, vertices: np.ndarray, triangles: np.ndarray) -> None:
        """Build the shaded triangle-mesh actor for the imported CAD surface."""
        self.remove_by_kind("model")
        actor = self._renderer.make_triangle_actor(
            vertices,
            triangles,
            color=(0.42, 0.48, 0.60),
        )
        self.add_object(SceneObject("Modelo CAD", "model"), actor)
        self._apply_display_mode(actor)
        self._notify()

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
    ) -> None:
        """Render the Tet4 mesh colored by material density (blue=low, red=high)."""
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

        ctf = vtkColorTransferFunction()
        ctf.AddRGBPoint(0.0, 0.20, 0.35, 0.70)   # blue -> low density
        ctf.AddRGBPoint(1.0, 0.85, 0.20, 0.15)   # red  -> high density

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
        extent = self._radius if self._radius else 1.0
        if visible:
            self._renderer.set_axes(extent * 1.2)
        else:
            self._renderer.remove_axes()
        self._renderer.render()

    def set_grid_visible(self, visible: bool) -> None:
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
