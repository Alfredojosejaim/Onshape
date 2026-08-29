"""Viewport3D - the central Qt widget that hosts the GPU-accelerated 3D view.

Composition:  Viewport3D -> Scene -> Renderer -> GPU
                          -> Camera -> (renderer active camera)
                          -> SelectionManager

Navigation is driven through VTK interactor observers (so it works regardless of
how Qt routes mouse events to the embedded window) and follows the standard
AutoCAD scheme: scroll wheel = zoom, middle button drag = pan, Shift+middle
button drag = orbit, left click = select/pick, N = fit view to model.
Right click is left unbound for a future context menu.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser

from desktop.viewport.renderer import Renderer
from desktop.viewport.camera import Camera, StandardView
from desktop.viewport.scene import Scene
from desktop.viewport.selection import SelectionManager


class Viewport3D(QWidget):
    selectionChanged = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._last_x = 0.0
        self._last_y = 0.0
        self._mode = "idle"  # idle | orbit | pan | zoom
        self._click_start = True

        self._interactor = QVTKRenderWindowInteractor(self)
        self._interactor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._interactor)

        # ---- Rendering stack ----
        self.renderer = Renderer()
        rw = self._interactor.GetRenderWindow()
        self.renderer.vtk_renderer.SetRenderWindow(rw)
        rw.AddRenderer(self.renderer.vtk_renderer)

        self.camera = Camera(self.renderer.vtk_renderer.GetActiveCamera())
        self.scene = Scene(self.renderer, self.camera)
        self.selection = SelectionManager(self.renderer.vtk_renderer)
        self.selection.attach(self.scene)
        self.selection.set_selection_callback(self._emit_selection)

        # Use a passive interactor style so the VTK default navigation
        # (Trackball: left=rotate, middle=pan, right=zoom) is fully disabled
        # and the AutoCAD scheme handled by our observers is the only one.
        self._interactor.SetInteractorStyle(vtkInteractorStyleUser())
        self._install_observers()

        self.renderer.set_background((0.17, 0.18, 0.21), (0.06, 0.07, 0.08))
        self.scene.set_grid_visible(True)
        self.scene.set_axes_visible(True)
        self.scene.fit_camera()
        self._interactor_enabled = False

    def showEvent(self, event) -> None:
        # Enable the interactor once the widget has a native window, otherwise
        # VTK drops all mouse/keyboard events (the style handlers registered in
        # _install_observers would never be reached).
        if not self._interactor_enabled:
            try:
                self._interactor.Initialize()
            except Exception:
                pass
            self._interactor_enabled = True
        super().showEvent(event)

    # ------------------------------------------------------------------ #
    # VTK interactor observers (drive navigation + picking)
    # ------------------------------------------------------------------ #
    def _install_observers(self) -> None:
        style = self._interactor.GetInteractorStyle()
        if style is None:
            return
        for event, handler in [
            (vtkCommand.LeftButtonPressEvent, self._on_left_press),
            (vtkCommand.MiddleButtonPressEvent, self._on_middle_press),
            (vtkCommand.LeftButtonReleaseEvent, self._on_left_release),
            (vtkCommand.MiddleButtonReleaseEvent, self._generic_release),
            (vtkCommand.MouseMoveEvent, self._on_move),
            (vtkCommand.MouseWheelForwardEvent, self._on_wheel_forward),
            (vtkCommand.MouseWheelBackwardEvent, self._on_wheel_backward),
            (vtkCommand.KeyPressEvent, self._on_key_press),
        ]:
            style.AddObserver(event, handler)

    def _xy(self) -> tuple[float, float]:
        inter = self._interactor
        return float(inter.GetEventPosition()[0]), float(inter.GetEventPosition()[1])

    def _shift_held(self) -> bool:
        inter = self._interactor
        try:
            return bool(inter.GetShiftKey())
        except Exception:
            return False

    def _on_left_press(self, obj, ev) -> None:
        # AutoCAD: left button = select/pick, no navigation
        self._mode = "idle"
        self._click_start = True
        self._last_x, self._last_y = self._xy()

    def _on_middle_press(self, obj, ev) -> None:
        # AutoCAD: middle button = pan; Shift+middle button = orbit
        self._mode = "orbit" if self._shift_held() else "pan"
        self._last_x, self._last_y = self._xy()

    def _generic_release(self, obj, ev) -> None:
        self._mode = "idle"

    def _on_left_release(self, obj, ev) -> None:
        if self._click_start:
            x, y = self._xy()
            window_height = self._interactor.size().height()
            self.selection.pick(int(x), int(y))
        self._mode = "idle"

    def _on_move(self, obj, ev) -> None:
        if self._mode == "idle":
            return
        x, y = self._xy()
        dx = x - self._last_x
        dy = y - self._last_y
        self._last_x, self._last_y = x, y
        if dx == 0 and dy == 0:
            return
        self._click_start = False
        if self._mode == "orbit":
            self.camera.orbit(dx, dy)
        elif self._mode == "pan":
            self.camera.pan(dx, dy)
        self.renderer.render()

    def _on_wheel_forward(self, obj, ev) -> None:
        self.camera.dolly(-0.8)
        self.renderer.render()

    def _on_wheel_backward(self, obj, ev) -> None:
        self.camera.dolly(0.8)
        self.renderer.render()

    def _on_key_press(self, obj, ev) -> None:
        try:
            key = self._interactor.GetKeySym() or ""
        except Exception:
            return
        if key in ("n", "N"):
            self.fit_to_view()

    def _emit_selection(self, key) -> None:
        try:
            self.selectionChanged.emit(key)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Public viewport operations (used by the UI)
    # ------------------------------------------------------------------ #
    def set_view(self, view: str) -> None:
        self.camera.set_view(view)
        self.renderer.render()

    def fit_to_view(self) -> None:
        self.scene.reset_fit()

    def center_model(self) -> None:
        self.scene.center_model()

    def set_display_mode(self, mode: str) -> None:
        self.scene.set_display_mode(mode)

    def toggle_axes(self, visible: bool) -> None:
        self.scene.set_axes_visible(visible)

    def toggle_grid(self, visible: bool) -> None:
        self.scene.set_grid_visible(visible)

    def clear_selection(self) -> None:
        self.selection.clear()

    def load_model(self, vertices: np.ndarray, triangles: np.ndarray, bbox) -> None:
        self.scene.set_bounds(bbox)
        self.scene.set_model_geometry(vertices, triangles)
        self.scene.fit_camera()
        self.renderer.render()

    def show_mesh(self, nodes: np.ndarray, elements: np.ndarray, fit: bool = False) -> None:
        self.scene.set_mesh(nodes, elements)
        if fit:
            self.scene.fit_camera()
        self.renderer.render()

    def show_density(self, nodes: np.ndarray, elements: np.ndarray, densities: np.ndarray) -> None:
        self.scene.set_density_field(nodes, elements, densities)
        self.renderer.render()

    def finalize(self) -> None:
        try:
            self._interactor.Finalize()
        except Exception:
            pass
