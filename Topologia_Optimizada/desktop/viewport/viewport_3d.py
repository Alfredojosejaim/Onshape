"""Viewport3D - the central Qt widget that hosts the GPU-accelerated 3D view.

Composition:  Viewport3D -> Scene -> Renderer -> GPU
                          -> CameraController -> (renderer active camera)
                          -> SelectionManager
                          -> NavigationManager  (profiles drive WHAT to do)

Navigation is driven through VTK interactor observers (so it works regardless of
how Qt routes mouse events to the embedded window) and follows the standard
AutoCAD scheme by default: scroll wheel = zoom, middle button drag = pan,
Shift+middle button drag = orbit, left click = select/pick, N = fit view to
model.  Right click is left unbound for a future context menu.

The orbit itself is a free trackball rotation (Onshape-style field motion): the
camera follows the pointer along a great circle and can reach any orientation
without being locked to fixed axes.

Architecture integration:
    A ``NavigationManager`` from ``core.navigation`` is created at init time
    with the default AutoCAD profile.  It only decides WHAT action the user
    requests (orbit/pan/zoom/select/fit).  The actual camera transformation
    is performed by the independent ``CameraController``.  The existing VTK
    observer handlers resolve events through the NavigationManager and execute
    the resulting action on the CameraController; the NavigationManager is
    available for the UI to query and swap profiles without touching the
    viewport or the camera.

IMPORTANT: Los imports de VTK se hacen de forma lazy (dentro de __init__) para
que importar este módulo no cargue VTK. Esto permite que la aplicación use
SoftwareViewport sin importar VTK cuando no hay GPU disponible.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal

# StandardView NO depende de VTK — se puede importar a nivel de módulo.
from desktop.viewport.camera import StandardView

from core.navigation import NavigationManager, InputEvent, MouseButton, ViewportAction


# ──────────────────────────────────────────────────────────────────────
# Detección de soporte GL (se ejecuta una sola vez, cacheada)
# ──────────────────────────────────────────────────────────────────────
_GL_AVAILABLE: bool | None = None


def _probe_gl_subprocess() -> bool:
    """Lanza un subprocess que intenta crear ventana VTK y renderizar.

    Retorna True solo si el renderizado funciona realmente.
    SupportsOpenGL() solo verifica la presencia del driver, no si funciona.
    El subprocess puede crashear si GL no funciona, pero el proceso principal
    sobrevive porque no importa VTK.
    """
    import subprocess
    import sys
    probe_code = (
        "import vtkmodules.vtkRenderingOpenGL2 as g; "
        "rw = g.vtkOpenGLRenderWindow(); "
        "rw.SetOffScreenRendering(1); rw.SetSize(4,4); "
        "rw.MakeCurrent(); "
        "print('OK' if rw.SupportsOpenGL() else 'FAIL')"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", probe_code],
            capture_output=True, text=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "OK" in result.stdout and result.returncode == 0
    except Exception:
        return False


def is_gl_available() -> bool:
    """Prueba si el sistema tiene soporte OpenGL funcional para VTK.

    Usa un subprocess para evitar que un crash de VTK destruya el proceso
    principal. Cachea el resultado para no repetir la prueba.

    Returns:
        True si OpenGL funciona, False si no (usar SoftwareViewport).
    """
    global _GL_AVAILABLE
    if _GL_AVAILABLE is not None:
        return _GL_AVAILABLE
    _GL_AVAILABLE = _probe_gl_subprocess()
    return _GL_AVAILABLE


class Viewport3D(QWidget):
    """Viewport 3D acelerado por GPU via VTK.

    Los imports de VTK se hacen de forma lazy dentro de __init__ para que
    importar esta clase no cargue VTK en el proceso. Si VTK no está
    disponible o GL falla, se debe usar SoftwareViewport en su lugar.
    """

    selectionChanged = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._last_x = 0.0
        self._last_y = 0.0
        self._mode = "idle"  # idle | orbit | pan | zoom
        self._click_start = True

        # ── Imports de VTK (lazy — solo se cargan si se construye Viewport3D) ──
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
        from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser
        from desktop.viewport.renderer import Renderer
        from desktop.viewport.camera import CameraController
        from desktop.viewport.scene import Scene
        from desktop.viewport.selection import SelectionManager

        self._vtkCommand = __import__("vtkmodules.vtkCommonCore", fromlist=["vtkCommand"]).vtkCommand

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

        # Independent camera system (CameraController) — how the camera moves.
        # It is kept separate from NavigationManager, which only decides WHAT
        # action (orbit/pan/zoom/select/fit) the user is requesting.
        self.camera = CameraController(self.renderer.vtk_renderer.GetActiveCamera())
        self.scene = Scene(self.renderer, self.camera)
        self.selection = SelectionManager(self.renderer.vtk_renderer)
        self.selection.attach(self.scene)
        self.selection.set_selection_callback(self._emit_selection)

        # Architecture layer: navigation profile manager
        self.navigation = NavigationManager(profile_name="autocad")

        # Use a passive interactor style so the VTK default navigation
        # (Trackball: left=rotate, middle=pan, right=zoom) is fully disabled
        # and the AutoCAD scheme handled by our observers is the only one.
        self._interactor.SetInteractorStyle(vtkInteractorStyleUser())
        self._install_observers()

        # Background matches the native viewport palette (theme-driven)
        from desktop.ui.style import PALETTE, hex_to_rgb_float
        self.renderer.set_background(
            hex_to_rgb_float(PALETTE["bg_viewport_top"]),
            hex_to_rgb_float(PALETTE["bg_viewport_bottom"]),
        )
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
        vtkCommand = self._vtkCommand
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

    def _ctrl_held(self) -> bool:
        inter = self._interactor
        try:
            return bool(inter.GetControlKey())
        except Exception:
            return False

    def _alt_held(self) -> bool:
        inter = self._interactor
        try:
            return bool(inter.GetAltKey())
        except Exception:
            return False

    def _make_input_event(
        self,
        mouse_button: MouseButton | None = None,
        wheel_delta: float = 0.0,
        key_sym: str | None = None,
        double_click: bool = False,
    ) -> InputEvent:
        """Build a normalised InputEvent from the current VTK modifier state."""
        return InputEvent(
            mouse_button=mouse_button,
            shift=self._shift_held(),
            ctrl=self._ctrl_held(),
            alt=self._alt_held(),
            wheel_delta=wheel_delta,
            key_sym=key_sym,
            double_click=double_click,
        )

    def _resolve_and_execute(self, event: InputEvent) -> None:
        """Resolve an input event through the NavigationManager and act."""
        action = self.navigation.resolve(event)
        act = action.action
        if act == ViewportAction.ORBIT:
            self._mode = "orbit"
        elif act == ViewportAction.PAN:
            self._mode = "pan"
        elif act == ViewportAction.ZOOM_IN:
            self.camera.dolly(0.8)
            self.renderer.render()
            self._mode = "idle"
        elif act == ViewportAction.ZOOM_OUT:
            self.camera.dolly(-0.8)
            self.renderer.render()
            self._mode = "idle"
        elif act == ViewportAction.SELECT:
            self._mode = "idle"
            self._click_start = True
        elif act == ViewportAction.FIT:
            self.fit_to_view()
            self._mode = "idle"
        elif act == ViewportAction.CONTEXT_MENU:
            self._mode = "idle"
        else:
            self._mode = "idle"

    def _on_left_press(self, obj, ev) -> None:
        event = self._make_input_event(mouse_button=MouseButton.LEFT)
        self._resolve_and_execute(event)
        self._last_x, self._last_y = self._xy()

    def _on_middle_press(self, obj, ev) -> None:
        event = self._make_input_event(mouse_button=MouseButton.MIDDLE)
        self._resolve_and_execute(event)
        self._last_x, self._last_y = self._xy()

    def _generic_release(self, obj, ev) -> None:
        self._mode = "idle"

    def _on_left_release(self, obj, ev) -> None:
        if self._click_start:
            x, y = self._xy()
            self.selection.pick(int(x), int(y), ctrl=self._ctrl_held())
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
        event = self._make_input_event(wheel_delta=1.0)
        self._resolve_and_execute(event)

    def _on_wheel_backward(self, obj, ev) -> None:
        event = self._make_input_event(wheel_delta=-1.0)
        self._resolve_and_execute(event)

    def _on_key_press(self, obj, ev) -> None:
        try:
            key = self._interactor.GetKeySym() or ""
        except Exception:
            return
        event = self._make_input_event(key_sym=key)
        self._resolve_and_execute(event)

    def _emit_selection(self, payload) -> None:
        try:
            self.selectionChanged.emit(payload)
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

    def load_model(self, vertices: np.ndarray, triangles: np.ndarray, bbox,
                   face_index_map: Optional[np.ndarray] = None,
                   faces_meta: Optional[list] = None) -> None:
        self.scene.set_bounds(bbox)
        self.scene.set_model_geometry(vertices, triangles,
                                      face_index_map=face_index_map,
                                      faces_meta=faces_meta)
        self.scene.fit_camera()
        self.renderer.render()

    def show_mesh(self, nodes: np.ndarray, elements: np.ndarray, fit: bool = False) -> None:
        self.scene.set_mesh(nodes, elements)
        if fit:
            self.scene.fit_camera()
        self.renderer.render()

    def show_density(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        colormap: str = "jet",
    ) -> None:
        self.scene.set_density_field(nodes, elements, densities, colormap=colormap)
        self.renderer.render()

    def finalize(self) -> None:
        try:
            self._interactor.Finalize()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Navigation profile (architecture layer)
    # ------------------------------------------------------------------ #
    def set_navigation_profile(self, profile_name: str) -> bool:
        """Swap the navigation profile at runtime without touching observers."""
        return self.navigation.set_profile(profile_name)

    @property
    def navigation_profile_name(self) -> str:
        return self.navigation.profile_name

    @property
    def selection_manager(self):
        """Alias for the SelectionManager (UI code references ``selection_manager``)."""
        return self.selection
