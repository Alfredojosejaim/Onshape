"""Renderer - centralized communication layer with the graphics system (VTK).

The UI, viewport, and scene never talk directly to VTK objects: they delegate
all rendering concerns to this module. This isolates GPU/rendering calls in a
single place so the graphics backend can be swapped later without rewriting the
interface (see prompt "RENDERER").

Request flow:  UI -> Viewport -> Scene -> Renderer -> GPU
"""

from __future__ import annotations

import numpy as np
from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkActor,
    vtkPolyDataMapper,
)
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkCellArray
from vtkmodules.vtkCommonCore import vtkPoints, vtkFloatArray, vtkIdTypeArray, VTK_ID_TYPE
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.util.numpy_support import numpy_to_vtk

try:
    from vtkmodules.vtkRenderingCore import vtkGPUInfoList
    _HAS_GPU_INFO = True
except Exception:  # pragma: no cover
    _HAS_GPU_INFO = False


class DisplayMode:
    """Pending render representation modes (rendered via an IncludeEdge extraction)."""
    SURFACED = "surfaced"
    SURFACED_EDGES = "surfaced_edges"
    WIREFRAME = "wireframe"
    TRANSPARENT = "transparent"


class Renderer:
    """Owns the VTK renderer and scene-level GPU primitives.

    Conceptually this is the bottom layer of the graphics stack. All actor /
    mapper / data construction happens here under a small, intent-revealing API
    consumed by :class:`Scene`.
    """

    def __init__(self) -> None:
        self._vtk_renderer = vtkRenderer()
        self._renderer = self._vtk_renderer

        colors = vtkNamedColors()
        self._renderer.SetBackground(colors.GetColor3d("DarkSlateGray"))  # placeholder
        self._renderer.SetBackground2(colors.GetColor3d("DarkSlateGray"))
        self._renderer.GradientBackgroundOn()

        self._actors: list[vtkActor] = []
        self._grid_actor: vtkActor | None = None
        self._axes_widget_actor: vtkActor = None
        self._axes_actor: vtkActor = None
        self._camera = self._renderer.GetActiveCamera()
        self._camera.SetPosition(1, 1, 1)
        self._camera.SetFocalPoint(0, 0, 0)
        self._camera.ParallelProjectionOff()

    # ------------------------------------------------------------------ #
    # Actor registry
    # ------------------------------------------------------------------ #
    @property
    def actors(self) -> list[vtkActor]:
        return list(self._actors)

    def add_actor(self, actor: vtkActor) -> None:
        self._actors.append(actor)
        self._renderer.AddActor(actor)

    def remove_actor(self, actor: vtkActor) -> None:
        if actor in self._actors:
            self._actors.remove(actor)
        self._renderer.RemoveActor(actor)

    def clear_actors(self) -> None:
        for actor in list(self._actors):
            self._renderer.RemoveActor(actor)
        self._actors = []

    def reset_camera(self) -> None:
        self._renderer.ResetCamera()

    def reset_camera_clipping(self) -> None:
        self._renderer.ResetCameraClippingRange()

    def render(self) -> None:
        self._renderer.GetRenderWindow().Render()

    @property
    def vtk_renderer(self) -> vtkRenderer:
        return self._vtk_renderer

    # ------------------------------------------------------------------ #
    # Background
    # ------------------------------------------------------------------ #
    def set_background(self, top: tuple, bottom: tuple) -> None:
        self._renderer.SetBackground(bottom)
        self._renderer.SetBackground2(top)
        self._renderer.GradientBackgroundOn()
        self.render()

    # ------------------------------------------------------------------ #
    # Grid
    # ------------------------------------------------------------------ #
    def create_grid(self, size: float, subdivisions: int, color=(0.28, 0.29, 0.32)) -> vtkActor:
        from vtkmodules.vtkFiltersSources import vtkPlaneSource
        from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
        from vtkmodules.vtkRenderingCore import vtkActor as _vtkActor, vtkPolyDataMapper as _vtkPolyDataMapper

        half = size / 2.0
        plane = vtkPlaneSource()
        plane.SetOrigin(-half, -half, 0)
        plane.SetPoint1(half, -half, 0)
        plane.SetPoint2(-half, half, 0)
        plane.SetXResolution(subdivisions)
        plane.SetYResolution(subdivisions)

        mapper = _vtkPolyDataMapper()
        mapper.SetInputConnection(plane.GetOutputPort())

        actor = _vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color[0], color[1], color[2])
        actor.GetProperty().SetRepresentationToWireframe()
        actor.GetProperty().SetLineWidth(1)
        actor.GetProperty().LightingOff()
        return actor

    def set_grid(self, size: float, subdivisions: int) -> None:
        if self._grid_actor is not None:
            self.remove_actor(self._grid_actor)
            self._grid_actor = None
        self._grid_actor = self.create_grid(size, subdivisions)
        self.add_actor(self._grid_actor)

    def remove_grid(self) -> None:
        if self._grid_actor is not None:
            self.remove_actor(self._grid_actor)
            self._grid_actor = None

    # ------------------------------------------------------------------ #
    # Axes
    # ------------------------------------------------------------------ #
    def create_axes(self, length: float) -> vtkActor:
        axes = vtkAxesActor()
        axes.SetTotalLength(length, length, length)
        axes.AxisLabelsOff()
        return axes

    def set_axes(self, length: float) -> None:
        if self._axes_actor is not None:
            self.remove_actor(self._axes_actor)
            self._axes_actor = None
        self._axes_actor = self.create_axes(length)
        self.add_actor(self._axes_actor)

    def remove_axes(self) -> None:
        if self._axes_actor is not None:
            self.remove_actor(self._axes_actor)
            self._axes_actor = None

    # ------------------------------------------------------------------ #
    # Camera proxy (delegated to Camera layer but exposed for renderer init)
    # ------------------------------------------------------------------ #
    def make_triangle_actor(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
        color=(0.55, 0.62, 0.74),
        opacity: float = 1.0,
        edge_color=(0.05, 0.07, 0.1),
        edge_visibility: bool = True,
        cell_data: Optional[Dict[str, np.ndarray]] = None,
    ) -> vtkActor:
        """Build a lit, phong-shaded triangle-mesh actor (GPU-represented).

        ``cell_data`` maps array names to one-value-per-cell arrays (e.g.
        ``{"face_index": [...]}``) stored on the output poly for entity picking.
        """
        poly = self._build_polydata(vertices, triangles, compute_normals=True,
                                    cell_data=cell_data)
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(poly)
        mapper.SetScalarVisibility(False)
        actor = vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(color[0], color[1], color[2])
        prop.SetOpacity(opacity)
        prop.SetInterpolationToPhong()
        prop.SetSpecular(0.2)
        prop.SetSpecularPower(20)
        prop.SetAmbient(0.25)
        prop.SetDiffuse(0.8)
        prop.EdgeVisibilityOn() if edge_visibility else prop.EdgeVisibilityOff()
        prop.SetEdgeColor(edge_color[0], edge_color[1], edge_color[2])
        prop.SetLineWidth(1.0)
        return actor

    def _build_polydata(
        self,
        vertices: np.ndarray,
        triangles: np.ndarray,
        compute_normals: bool = True,
        cell_data: Optional[Dict[str, np.ndarray]] = None,
    ) -> vtkPolyData:
        verts = np.asarray(vertices, dtype=float)
        tris = np.asarray(triangles, dtype=np.int64)
        if verts.ndim != 2 or verts.shape[1] != 3:
            raise ValueError("vertices must be (N, 3)")
        points = vtkPoints()
        points.SetData(vtk_points_array(verts))
        cells = vtkCellArray()
        cells.SetCells(tris.shape[0], vtk_connectivity(tris))
        poly = vtkPolyData()
        poly.SetPoints(points)
        poly.SetPolys(cells)
        if compute_normals:
            from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
            normals = vtkPolyDataNormals()
            normals.SetInputData(poly)
            normals.ComputePointNormalsOn()
            normals.ComputeCellNormalsOn()
            normals.SplittingOff()
            normals.Update()
            poly = normals.GetOutput()
        if cell_data:
            from vtkmodules.vtkCommonCore import vtkIntArray
            for name, arr in cell_data.items():
                arr = np.ascontiguousarray(arr)
                if arr.ndim != 1 or arr.shape[0] != tris.shape[0]:
                    continue
                carr = vtkIntArray()
                carr.SetName(str(name))
                for v in arr:
                    carr.InsertNextValue(int(v))
                poly.GetCellData().AddArray(carr)
        return poly


def vtk_points_array(verts: np.ndarray) -> vtkFloatArray:
    """Build a 3-component float array for vtkPoints.SetData()."""
    arr = numpy_to_vtk(np.ascontiguousarray(verts, dtype=np.float32), deep=True)
    arr.SetNumberOfComponents(3)
    return arr


def vtk_connectivity(tris: np.ndarray) -> vtkIdTypeArray:
    """Build a vtkIdTypeArray describing triangle cell connectivity."""
    tris = np.asarray(tris, dtype=np.int64)
    n = int(tris.shape[0])
    conn = np.empty(n * 4, dtype=np.int64)
    conn[0::4] = 3
    conn[1::4] = tris[:, 0]
    conn[2::4] = tris[:, 1]
    conn[3::4] = tris[:, 2]
    arr = numpy_to_vtk(np.ascontiguousarray(conn), deep=True, array_type=VTK_ID_TYPE)
    arr.SetNumberOfComponents(1)
    return arr
