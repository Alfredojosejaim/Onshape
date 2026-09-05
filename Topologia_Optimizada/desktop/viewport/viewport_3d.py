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

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QRubberBand
from PySide6.QtCore import Qt, Signal, QRect, QPoint


#: Sentinel de resolve_pick_entity: el rayo golpeo al modelo pero en un
#: hueco/arista sin cara atribuible -> conservar la seleccion previa
#: (no limpiar, no reemplazar).
KEEP_SELECTION = object()


def resolve_pick_entity(picked_actor, cell_id, scene):
    """Traduce (actor, cell_id) del vtkCellPicker a entidad o accion.

    - Actor None / cell -1 / actor no-modelo (grid, ejes, overlays, malla):
      ``None`` -> tratar como vacio (limpia salvo aditivo).
    - Actor modelo + cara valida: ``CadEntityRef`` de la cara.
    - Actor modelo + celda sin cara (hueco, face -1): ``KEEP_SELECTION``.

    prompts.md (actor-pick): sin esta validacion, un click sobre el grid
    devolvia un cell_id de ESA malla que face_index_for_cell indexaba
    ciegamente como triangulo del modelo -> cara arbitraria ("desmarca una
    pero marca otra").
    """
    if picked_actor is None or int(cell_id) < 0:
        return None
    model_key = getattr(scene, "_model_actor_key", None)
    hit_key = scene.actor_key_for(picked_actor)
    if hit_key != model_key:
        return None
    face_id = scene.face_index_for_cell(int(cell_id))
    if face_id is None:
        return KEEP_SELECTION
    from core.cad_entity import CadEntityRef
    try:
        meta = scene.face_meta(int(face_id))
    except Exception:
        meta = None
    return CadEntityRef.from_face(
        face_index=int(face_id),
        model_id=model_key,
        center=(meta.get("center") if meta else None),
        normal=(meta.get("normal") if meta else None),
        area=(meta.get("area") if meta else None),
    )


def faces_fully_in_rect(face_vertex_cache, vertices, rect, project_fn) -> set[int]:
    """Caras FULLY-contained estilo Onshape: entra solo si TODOS sus
    vertices proyectados caen dentro del rect (no interseccion de bbox:
    evita seleccionar geometria de fondo parcialmente visible).

    ``project_fn(x, y, z)`` devuelve ``(sx, sy)`` en coords Qt del viewport.
    """
    result: set[int] = set()
    verts = np.asarray(vertices, dtype=float)
    for face_idx, vids in face_vertex_cache.items():
        if not vids:
            continue
        inside = True
        for vid in vids:
            p = verts[int(vid)]
            sx, sy = project_fn(float(p[0]), float(p[1]), float(p[2]))
            if not rect.contains(int(round(sx)), int(round(sy))):
                inside = False
                break
        if inside:
            result.add(int(face_idx))
    return result

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
        self._press_x = 0.0
        self._press_y = 0.0
        # Rubber-band select (Onshape): drag con boton izquierdo en modo
        # select muestra QRubberBand; al soltar se resuelve por rectangulo.
        self._left_held = False
        self._rubber_active = False
        self._rubber_band: QRubberBand | None = None
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

    def _is_drag(self, x0: float, y0: float, x1: float, y1: float,
                 threshold_px: float = 4.0) -> bool:
        dx = float(x1) - float(x0)
        dy = float(y1) - float(y0)
        return (dx * dx + dy * dy) ** 0.5 > float(threshold_px)

    def _qt_additive(self) -> bool:
        """Detecta modificador aditivo (Shift/Ctrl) combinando Qt Y VTK.

        prompts.md (nuevo §1.1): QVTKRenderWindowInteractor captura el teclado
        a nivel VTK y QApplication.keyboardModifiers() puede devolver
        NoModifier porque el foco lo tiene el interactor, no el widget Qt.
        La alternativa confiable es OR de ambas fuentes.
        """
        qt_add = False
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import Qt as _Qt
            mods = QApplication.keyboardModifiers()
            qt_add = bool(mods & (_Qt.ShiftModifier | _Qt.ControlModifier))
        except Exception:
            qt_add = False
        try:
            vtk_add = bool(self._interactor.GetShiftKey()) or bool(
                self._interactor.GetControlKey())
        except Exception:
            try:
                vtk_add = bool(self._ctrl_held() or self._shift_held())
            except Exception:
                vtk_add = False
        return bool(qt_add or vtk_add)

    def _on_left_press(self, obj, ev) -> None:
        event = self._make_input_event(mouse_button=MouseButton.LEFT)
        self._resolve_and_execute(event)
        self._last_x, self._last_y = self._xy()
        self._press_x, self._press_y = self._last_x, self._last_y
        self._left_held = True
        self._rubber_active = False

    def _on_middle_press(self, obj, ev) -> None:
        event = self._make_input_event(mouse_button=MouseButton.MIDDLE)
        self._resolve_and_execute(event)
        self._last_x, self._last_y = self._xy()

    def _generic_release(self, obj, ev) -> None:
        self._mode = "idle"

    def _display_height(self) -> float:
        """Altura del viewport en px (para convertir Y VTK->Qt)."""
        try:
            h = float(self._interactor.height())
            if h > 0:
                return h
        except Exception:
            pass
        try:
            return float(self.renderer.vtk_renderer.GetSize()[1])
        except Exception:
            return 600.0

    def _vtk_to_qt(self, x: float, y: float) -> tuple[float, float]:
        return float(x), float(self._display_height() - float(y))

    def _drag_modifiers(self) -> tuple[bool, bool]:
        """(additive=Shift, subtractive=Ctrl), OR de Qt y VTK.

        Igual que _qt_additive: el foco cautivo del QVTK interactor puede
        dejar QApplication.keyboardModifiers() en NoModifier.
        """
        qshift = qctrl = False
        try:
            mods = QApplication.keyboardModifiers()
            qshift = bool(mods & Qt.ShiftModifier)
            qctrl = bool(mods & Qt.ControlModifier)
        except Exception:
            pass
        try:
            vshift = bool(self._interactor.GetShiftKey())
        except Exception:
            vshift = False
        try:
            vctrl = bool(self._interactor.GetControlKey())
        except Exception:
            vctrl = False
        return (qshift or vshift), (qctrl or vctrl)

    def _update_rubber_band(self, vtk_x: float, vtk_y: float) -> None:
        try:
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(QRubberBand.Rectangle, self._interactor)
            x0, y0 = self._vtk_to_qt(self._press_x, self._press_y)
            x1, y1 = self._vtk_to_qt(vtk_x, vtk_y)
            self._rubber_band.setGeometry(
                QRect(QPoint(int(x0), int(y0)), QPoint(int(x1), int(y1))).normalized())
            self._rubber_band.show()
        except Exception:
            pass

    def _faces_in_rect(self, rect, project_fn=None) -> set[int]:
        """Caras fully-contained en el rect Qt (proyeccion world->display)."""
        cache = self.scene.face_vertex_cache
        verts = self.scene.model_vertices
        if not cache or verts is None:
            return set()
        if project_fn is None:
            from vtkmodules.vtkRenderingCore import vtkCoordinate
            ren = self.renderer.vtk_renderer
            h = self._display_height()
            coord = vtkCoordinate()
            coord.SetCoordinateSystemToWorld()

            def project_fn(x: float, y: float, z: float):
                coord.SetValue(float(x), float(y), float(z))
                sx, sy = coord.GetComputedDisplayValue(ren)
                return float(sx), float(h - sy)  # VTK Y invertido vs Qt

        return faces_fully_in_rect(cache, verts, rect, project_fn)

    def _finish_rubber_band(self) -> None:
        self._rubber_active = False
        try:
            if self._rubber_band is not None:
                self._rubber_band.hide()
        except Exception:
            logger.debug("rubber-band hide failed", exc_info=True)
        try:
            x, y = self._xy()
            x0, y0 = self._vtk_to_qt(self._press_x, self._press_y)
            x1, y1 = self._vtk_to_qt(x, y)
            rect = QRect(QPoint(int(x0), int(y0)), QPoint(int(x1), int(y1))).normalized()
            additive, subtractive = self._drag_modifiers()
            contained = self._faces_in_rect(rect)
            self.selection.handle_rubber_band(
                contained, additive=additive, subtractive=subtractive)
        except Exception:
            logger.exception("rubber-band selection failed")
        self._mode = "idle"
        self._click_start = False

    def _on_left_release(self, obj, ev) -> None:
        self._left_held = False
        if self._rubber_active:
            # Drag con banda activa: resolver por rectangulo, no pick puntual.
            self._finish_rubber_band()
            return
        # Distincion click/drag: si hubo arrastre, lo maneja rubber-band,
        # no es un pick (prompts.md §2).
        try:
            x, y = self._xy()
            px = getattr(self, "_press_x", self._last_x)
            py = getattr(self, "_press_y", self._last_y)
            if self._is_drag(px, py, x, y, threshold_px=4):
                self._mode = "idle"
                return
            if not self._click_start:
                self._mode = "idle"
                return
        except Exception:
            pass
        if self._click_start:
            try:
                self._do_pick_release()
            except Exception:
                # Fallback legacy si algo falla en el pipeline nuevo.
                try:
                    x, y = self._xy()
                    self.selection.pick(int(x), int(y), ctrl=self._ctrl_held())
                except Exception:
                    pass
        self._mode = "idle"

    def _do_pick_release(self) -> None:
        """Pipeline prompts.md §2 + actor-pick: picker -> (actor, CellId) ->
        validacion de actor -> face -> entity -> handle_pick."""
        from PySide6.QtWidgets import QApplication  # noqa: F401 (asegura contexto Qt)
        click_pos = self._interactor.GetEventPosition()
        self.selection._picker.Pick(
            click_pos[0], click_pos[1], 0, self.renderer.vtk_renderer)
        picked_actor = self.selection._picker.GetActor()
        cell_id = int(self.selection._picker.GetCellId())
        additive = self._qt_additive()
        entity = resolve_pick_entity(picked_actor, cell_id, self.scene)
        if entity is KEEP_SELECTION:
            # Hit en hueco/arista del modelo sin cara: conserva seleccion.
            return
        self.selection.handle_pick(entity, additive=additive)

    def _on_move(self, obj, ev) -> None:
        if self._mode == "idle":
            # En modo select (click pendiente) con boton aun abajo: si supera
            # el umbral de 4px pasa a rubber-band en vez de pick puntual.
            if self._click_start and self._left_held and not self._rubber_active:
                x, y = self._xy()
                if self._is_drag(self._press_x, self._press_y, x, y, threshold_px=4):
                    self._click_start = False
                    self._rubber_active = True
                    self._update_rubber_band(x, y)
            elif self._rubber_active:
                x, y = self._xy()
                self._update_rubber_band(x, y)
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
