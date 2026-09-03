"""SoftwareViewport — un viewport 3D completamente por software (QPainter)

Implementa la misma API pública que Viewport3D (VTK) para que MainWindow,
overlays, panel de propiedades y navegación funcionen sin cambiar una sola
línea de código en ellos. La detección automática en _ViewportHost selecciona
VTK si hay GPU disponible; si no, usa este widget.

El renderizado se hace con QPainter + proyección ortográfica:
  - Triángulos rellenos + aristas (Phong simplificado con iluminación flat)
  - Rejilla y ejes dibujados como polilíneas
  - Selección por ray-casting 2D (point-in-triangle en pantalla)
  - Navegación completa: órbita, paneo, zoom, selección
"""

from __future__ import annotations

import math
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath,
    QPolygonF, QMouseEvent, QWheelEvent, QPaintEvent, QResizeEvent,
)

from core.navigation import NavigationManager, InputEvent, MouseButton, ViewportAction


# ──────────────────────────────────────────────────────────────────────
# Matemática 3D básica (sin dependencias externas)
# ──────────────────────────────────────────────────────────────────────
def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else np.zeros(3)


def _rotation_x(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _rotation_y(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rotation_z(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _apply_rotation(rot: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Aplica rotación a (N, 3)."""
    return (rot @ pts.T).T


def _point_in_triangle_2d(px: float, py: float,
                           ax: float, ay: float,
                           bx: float, by: float,
                           cx: float, cy: float) -> bool:
    """Determina si el punto (px, py) está dentro del triángulo ABC en 2D."""
    v0x, v0y = cx - ax, cy - ay
    v1x, v1y = bx - ax, by - ay
    v2x, v2y = px - ax, py - ay
    dot00 = v0x * v0x + v0y * v0y
    dot01 = v0x * v1x + v0y * v1y
    dot02 = v0x * v2x + v0y * v2y
    dot11 = v1x * v1x + v1y * v1y
    dot12 = v1x * v2x + v1y * v2y
    inv = dot00 * dot11 - dot01 * dot01
    if abs(inv) < 1e-12:
        return False
    u = (dot11 * dot02 - dot01 * dot12) / inv
    v = (dot00 * dot12 - dot01 * dot02) / inv
    return u >= 0 and v >= 0 and u + v <= 1.0


def _face_normal(v0: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    return _normalize(np.cross(v1 - v0, v2 - v0))


# ──────────────────────────────────────────────────────────────────────
# SelectionManager compatible con la interfaz de VTK (mismos métodos)
# ──────────────────────────────────────────────────────────────────────
class _SoftwareSelectionManager:
    """SelectionManager mínimo para el viewport por software.

    Implementa la misma API pública que SelectionManager de VTK:
    - attach(scene), set_selection_callback(fn), clear(), pick(x, y, ctrl)
    """

    def __init__(self) -> None:
        self._scene = None
        self._callback = None
        self._selected_faces: list[int] = []
        self._selected_solids: set[int] = set()
        self._solid_resolver = None

    def attach(self, scene) -> None:
        self._scene = scene

    def set_selection_callback(self, fn) -> None:
        self._callback = fn

    def set_solid_resolver(self, resolver) -> None:
        """Registra un callable opcional para promover una cara a su sólido padre."""
        self._solid_resolver = resolver

    def clear(self) -> None:
        self._selected_faces.clear()
        self._selected_solids.clear()
        if self._callback:
            self._callback(None)

    def pick(self, x: int, y: int, ctrl: bool = False) -> None:
        """Selecciona la cara en las coordenadas de pantalla (x, y)."""
        if self._scene is None:
            return
        face = self._scene.pick_face(x, y)
        if face is None:
            self.clear()
            return
        if ctrl:
            if face in self._selected_faces:
                self._selected_faces.remove(face)
            else:
                self._selected_faces.append(face)
        else:
            self._selected_faces = [face]
        solid = self._scene.face_to_solid(face)
        if solid is not None:
            self._selected_solids = {solid}
        self._emit(face, ctrl)

    def _emit(self, face: int, ctrl: bool) -> None:
        if self._callback is None:
            return
        solid = self._scene.face_to_solid(face) if self._scene else None
        meta = self._scene.face_meta(face) if self._scene else None
        payload = {
            "kind": "face",
            "type": "face",
            "face_index": face,
            "solid_index": solid,
            "id": (meta or {}).get("id", f"face_{face}"),
            "center": (meta or {}).get("center", []),
            "normal": (meta or {}).get("normal", []),
            "area": (meta or {}).get("area", 0.0),
            "ctrl": ctrl,
            "multi": len(self._selected_faces) > 1,
        }
        self._callback(payload)


# ──────────────────────────────────────────────────────────────────────
# Escena interna del viewport por software
# ──────────────────────────────────────────────────────────────────────
class _SoftwareScene:
    """Almacena geometría del modelo, malla y campos de densidad."""

    def __init__(self) -> None:
        self._vertices: np.ndarray | None = None
        self._triangles: np.ndarray | None = None
        self._face_index_map: np.ndarray | None = None
        self._faces_meta: list | None = None

        self._mesh_nodes: np.ndarray | None = None
        self._mesh_elements: np.ndarray | None = None

        self._density_nodes: np.ndarray | None = None
        self._density_elements: np.ndarray | None = None
        self._density_values: np.ndarray | None = None

        self._bbox = np.array([[-1, -1, -1], [1, 1, 1]], dtype=float)
        self._display_mode = "surfaced"
        self._grid_visible = True
        self._axes_visible = True

        # Cache de centroides y normales para picking
        self._centroids: np.ndarray | None = None
        self._normals: np.ndarray | None = None
        self._solid_index_map: dict[int, int] = {}  # face_idx → solid_idx

        # Para picking 3D: puntos transformados y proyectados (actualizados en paint)
        self._transformed_verts: np.ndarray | None = None
        self._projected_pts: np.ndarray | None = None  # (N, 3): pantalla_x, pantalla_y, profundidad

    # -- Geometría CAD --
    def set_model_geometry(self, vertices, triangles, face_index_map=None,
                           faces_meta=None) -> None:
        self._vertices = np.asarray(vertices, dtype=float)
        self._triangles = np.asarray(triangles, dtype=np.int64)
        self._face_index_map = face_index_map
        self._faces_meta = faces_meta
        self._invalidate_cache()

        # Mapeo cara→sólido
        self._solid_index_map = {}
        if faces_meta is not None:
            for i, meta in enumerate(faces_meta):
                if meta and "solid_index" in meta:
                    self._solid_index_map[i] = int(meta["solid_index"])
        self._recalc_centroids()

    def _recalc_centroids(self) -> None:
        if self._vertices is None or self._triangles is None:
            return
        v = self._vertices
        t = self._triangles
        self._centroids = (v[t[:, 0]] + v[t[:, 1]] + v[t[:, 2]]) / 3.0
        v0, v1, v2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
        self._normals = _normalize(np.cross(v1 - v0, v2 - v0))

    def face_to_solid(self, face_idx: int) -> int | None:
        return self._solid_index_map.get(face_idx)

    def face_meta(self, face_idx: int) -> dict | None:
        if self._faces_meta is None:
            return None
        for meta in self._faces_meta:
            if meta and int(meta.get("face_index", -1)) == int(face_idx):
                return meta
        return None

    # -- Malla --
    def set_mesh(self, nodes, elements) -> None:
        self._mesh_nodes = np.asarray(nodes, dtype=float)
        self._mesh_elements = np.asarray(elements, dtype=np.int64)

    # -- Densidad --
    def set_density_field(self, nodes, elements, densities, colormap="jet") -> None:
        self._density_nodes = np.asarray(nodes, dtype=float)
        self._density_elements = np.asarray(elements, dtype=np.int64)
        self._density_values = np.asarray(densities, dtype=float)

    # -- BBox --
    def set_bounds(self, bbox) -> None:
        """Set scene extents (BoundingBox3D-like, ``_BBox`` or array) and refit."""
        if bbox is None:
            return
        if isinstance(bbox, dict):
            self._bbox = np.array(
                [
                    [bbox.get("xmin", -1), bbox.get("ymin", -1), bbox.get("zmin", -1)],
                    [bbox.get("xmax", 1), bbox.get("ymax", 1), bbox.get("zmax", 1)],
                ],
                dtype=float,
            )
        elif hasattr(bbox, "xmin"):
            self._bbox = np.array(
                [[bbox.xmin, bbox.ymin, bbox.zmin],
                 [bbox.xmax, bbox.ymax, bbox.zmax]],
                dtype=float,
            )
        else:
            self._bbox = np.asarray(bbox, dtype=float)

    # -- Modo de display --
    def set_display_mode(self, mode: str) -> None:
        self._display_mode = mode

    # -- Visibilidad --
    def set_grid_visible(self, visible: bool) -> None:
        self._grid_visible = visible

    def set_axes_visible(self, visible: bool) -> None:
        self._axes_visible = visible

    def _invalidate_cache(self) -> None:
        self._centroids = None
        self._normals = None
        self._transformed_verts = None
        self._projected_pts = None

    # -- Picking por coordenadas de pantalla --
    def pick_face(self, sx: float, sy: float) -> int | None:
        """Devuelve el índice B-Rep de la cara más cercana al punto de pantalla (sx, sy).

        El punto de pantalla se resuelve primero al triángulo 3D más cercano (por
        profundidad) y ese triángulo se asigna a su cara B-Rep vía ``_face_index_map``
        (equivalente al ``face_index_for_cell`` del viewport VTK).
        """
        if (self._triangles is None or self._vertices is None
                or self._projected_pts is None):
            return None
        pts2d = self._projected_pts
        tris = self._triangles
        best_tri = None
        best_depth = float("inf")
        for i in range(tris.shape[0]):
            t = tris[i]
            ax, ay = pts2d[t[0], 0], pts2d[t[0], 1]
            bx, by = pts2d[t[1], 0], pts2d[t[1], 1]
            cx, cy = pts2d[t[2], 0], pts2d[t[2], 1]
            if _point_in_triangle_2d(sx, sy, ax, ay, bx, by, cx, cy):
                depth = (pts2d[t[0], 2] + pts2d[t[1], 2] + pts2d[t[2], 2]) / 3.0
                if depth < best_depth:
                    best_depth = depth
                    best_tri = int(i)
        if best_tri is None:
            return None
        # Atribuir el triángulo a su cara B-Rep; si no hay mapeo, devolver el
        # índice del propio triángulo como fallback (comportamiento previo).
        fm = self._face_index_map
        if fm is not None and best_tri < len(fm):
            face = int(fm[best_tri])
            return face if face >= 0 else best_tri
        return best_tri

    def face_to_triangles(self, face_index: int) -> list[int]:
        """Índices de los triángulos que pertenecen a la cara B-Rep dada."""
        fm = self._face_index_map
        if fm is None or self._triangles is None:
            return []
        return [int(i) for i in range(fm.shape[0]) if int(fm[i]) == int(face_index)]


# ──────────────────────────────────────────────────────────────────────
# SoftwareViewport — widget Qt QPainter sin GPU
# ──────────────────────────────────────────────────────────────────────
class SoftwareViewport(QWidget):
    """Viewport 3D por software que reemplaza Viewport3D cuando no hay GPU.

    Misma API pública:
      - selectionChanged(object) signal
      - set_view, fit_to_view, center_model, set_display_mode,
        toggle_axes, toggle_grid, clear_selection, load_model,
        show_mesh, show_density, finalize, set_navigation_profile,
        navigation_profile_name, selection_manager
    """

    selectionChanged = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(True)

        # Cámara (orbit/pan/zoom)
        self._rot_x: float = 30.0  # grados alrededor del eje X
        self._rot_z: float = -45.0  # grados alrededor del eje Z
        self._cam_x: float = 0.0  # pan en X
        self._cam_y: float = 0.0  # pan en Y
        self._zoom: float = 100.0  # unidades por pixel

        # Interacción
        self._mode: str = "idle"  # idle | orbit | pan
        self._last_x: float = 0.0
        self._last_y: float = 0.0
        self._click_start: bool = True

        # Escena y selección
        self._scene = _SoftwareScene()
        self._selection_mgr = _SoftwareSelectionManager()
        self._selection_mgr.attach(self._scene)

        # Navegación (reutiliza NavigationManager existente)
        self.navigation = NavigationManager(profile_name="autocad")

        # Estado de visibilidad
        self._grid_visible: bool = True
        self._axes_visible: bool = True

        # Colores (del tema)
        self._bg_top = QColor("#3c3d41")
        self._bg_bottom = QColor("#333437")
        self._model_color = QColor("#3b82f6")
        self._model_edge = QColor("#0d1117")
        self._grid_color = QColor("#47484c")
        self._axes_colors = [QColor("#e06c6c"), QColor("#b9f2c4"), QColor("#61afef")]  # R G B
        self._selection_color = QColor("#f2c94c")
        self._mesh_color = QColor("#9a9ba0")

        try:
            from desktop.ui.style import PALETTE
            self._bg_top = QColor(PALETTE.get("bg_viewport_top", "#3c3d41"))
            self._bg_bottom = QColor(PALETTE.get("bg_viewport_bottom", "#333437"))
            self._model_color = QColor(PALETTE.get("solid_cad", "#3b82f6"))
            self._grid_color = QColor(PALETTE.get("grid", "#47484c"))
        except Exception:
            pass

    # ── Señales / propiedades públicas ────────────────────────────────

    @property
    def selection_manager(self):
        return self._selection_mgr

    @property
    def navigation_profile_name(self) -> str:
        return self.navigation.profile_name

    def set_navigation_profile(self, profile_name: str) -> bool:
        return self.navigation.set_profile(profile_name)

    # ── API pública (idéntica a Viewport3D) ───────────────────────────

    def set_view(self, view: str) -> None:
        v = view.lower()
        if "front" in v or "frontal" in v:
            self._rot_x, self._rot_z = 0.0, 0.0
        elif "back" in v or "posterior" in v:
            self._rot_x, self._rot_z = 0.0, 180.0
        elif "top" in v or "superior" in v:
            self._rot_x, self._rot_z = 90.0, 0.0
        elif "bottom" in v or "inferior" in v:
            self._rot_x, self._rot_z = -90.0, 0.0
        elif "left" in v or "izquierda" in v:
            self._rot_x, self._rot_z = 0.0, 90.0
        elif "right" in v or "derecha" in v:
            self._rot_x, self._rot_z = 0.0, -90.0
        elif "iso" in v or "isométrica" in v:
            self._rot_x, self._rot_z = 30.0, -45.0
        self.update()

    def fit_to_view(self) -> None:
        verts = self._scene._vertices
        if verts is None or verts.shape[0] == 0:
            self.update()
            return
        span = np.max(verts, axis=0) - np.min(verts, axis=0)
        max_span = float(np.max(span))
        if max_span < 1e-9:
            max_span = 1.0
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        self._zoom = max_span / min(w, h) * 0.8
        center = (np.max(verts, axis=0) + np.min(verts, axis=0)) / 2.0
        self._cam_x = -center[0]
        self._cam_y = -center[1]
        self.update()

    def center_model(self) -> None:
        self.fit_to_view()

    def set_display_mode(self, mode: str) -> None:
        self._scene.set_display_mode(mode)
        self.update()

    def toggle_axes(self, visible: bool) -> None:
        self._axes_visible = visible
        self.update()

    def toggle_grid(self, visible: bool) -> None:
        self._grid_visible = visible
        self.update()

    def clear_selection(self) -> None:
        self._selection_mgr.clear()
        self.update()

    def load_model(self, vertices, triangles, bbox,
                   face_index_map=None, faces_meta=None) -> None:
        self._scene.set_bounds(bbox)
        self._scene.set_model_geometry(vertices, triangles,
                                       face_index_map=face_index_map,
                                       faces_meta=faces_meta)
        self.fit_to_view()

    def show_mesh(self, nodes, elements, fit: bool = False) -> None:
        self._scene.set_mesh(nodes, elements)
        if fit:
            self.fit_to_view()
        self.update()

    def show_density(self, nodes, elements, densities, colormap="jet") -> None:
        self._scene.set_density_field(nodes, elements, densities, colormap=colormap)
        self.update()

    def finalize(self) -> None:
        pass  # No hay recursos GPU que liberar

    # ── Input: ratón ─────────────────────────────────────────────────

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        ev.accept()
        self._last_x = float(ev.position().x())
        self._last_y = float(ev.position().y())
        self._click_start = True
        event = self._make_input_event(ev)
        action = self.navigation.resolve(event)
        act = action.action
        if act == ViewportAction.ORBIT:
            self._mode = "orbit"
        elif act == ViewportAction.PAN:
            self._mode = "pan"
        elif act == ViewportAction.SELECT:
            self._mode = "idle"
            self._click_start = True
        elif act == ViewportAction.FIT:
            self.fit_to_view()
            self._mode = "idle"
        else:
            self._mode = "idle"

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        ev.accept()
        if self._mode == "idle":
            return
        x, y = float(ev.position().x()), float(ev.position().y())
        dx, dy = x - self._last_x, y - self._last_y
        self._last_x, self._last_y = x, y
        if dx == 0 and dy == 0:
            return
        self._click_start = False
        if self._mode == "orbit":
            self._rot_z += dx * 0.5
            self._rot_x = max(-89.0, min(89.0, self._rot_x + dy * 0.5))
        elif self._mode == "pan":
            self._cam_x += dx * self._zoom * 0.002
            self._cam_y -= dy * self._zoom * 0.002
        self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        ev.accept()
        if self._click_start and self._mode == "idle":
            x, y = float(ev.position().x()), float(ev.position().y())
            self._selection_mgr.pick(x, y,
                                      ctrl=bool(ev.modifiers() & Qt.KeyboardModifier.ControlModifier))
            self.update()
        self._mode = "idle"

    def wheelEvent(self, ev: QMouseEvent) -> None:
        ev.accept()
        delta = ev.angleDelta().y() / 120.0
        factor = 1.0 - delta * 0.15
        self._zoom = max(0.01, self._zoom * factor)
        self.update()

    def keyPressEvent(self, ev) -> None:
        key = ev.text().lower() if ev.text() else ""
        event = self._make_input_event(key_sym=key)
        action = self.navigation.resolve(event)
        if action.action == ViewportAction.FIT:
            self.fit_to_view()
        super().keyPressEvent(ev)

    def _make_input_event(self, ev: QMouseEvent = None, key_sym: str = None,
                          mouse_button: MouseButton = None,
                          wheel_delta: float = 0.0) -> InputEvent:
        shift = False
        ctrl = False
        alt = False
        if ev is not None:
            mods = ev.modifiers()
            shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
            ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
            alt = bool(mods & Qt.KeyboardModifier.AltModifier)
            if mouse_button is None:
                btn = ev.button()
                if btn == Qt.MouseButton.LeftButton:
                    mouse_button = MouseButton.LEFT
                elif btn == Qt.MouseButton.MiddleButton:
                    mouse_button = MouseButton.MIDDLE
                elif btn == Qt.MouseButton.RightButton:
                    mouse_button = MouseButton.RIGHT
        return InputEvent(
            mouse_button=mouse_button,
            shift=shift,
            ctrl=ctrl,
            alt=alt,
            wheel_delta=wheel_delta,
            key_sym=key_sym,
        )

    def _emit_selection(self, payload) -> None:
        try:
            self.selectionChanged.emit(payload)
        except Exception:
            pass

    # ── Paint ────────────────────────────────────────────────────────

    def paintEvent(self, ev: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        cx, cy = w / 2.0, h / 2.0

        # Fondo degradado
        for i in range(int(h)):
            t = i / max(h - 1, 1)
            r = int(self._bg_top.red() * (1 - t) + self._bg_bottom.red() * t)
            g = int(self._bg_top.green() * (1 - t) + self._bg_bottom.green() * t)
            b = int(self._bg_top.blue() * (1 - t) + self._bg_bottom.blue() * t)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(r, g, b))
            painter.drawRect(0, int(i), int(w), 1)

        # Matriz de rotación
        rot = _rotation_z(math.radians(self._rot_z)) @ _rotation_x(math.radians(self._rot_x))

        # Dibujar rejilla
        if self._grid_visible:
            self._draw_grid(painter, rot, cx, cy, w, h)

        # Dibujar ejes
        if self._axes_visible:
            self._draw_axes(painter, rot, cx, cy)

        # Dibujar modelo
        if self._scene._vertices is not None and self._scene._triangles is not None:
            self._draw_model(painter, rot, cx, cy, w, h)

        # Dibujar malla
        if self._scene._mesh_nodes is not None and self._scene._mesh_elements is not None:
            self._draw_mesh(painter, rot, cx, cy)

        # Dibujar densidad
        if (self._scene._density_nodes is not None
                and self._scene._density_elements is not None
                and self._scene._density_values is not None):
            self._draw_density(painter, rot, cx, cy)

        painter.end()

    # ── Métodos de dibujo internos ───────────────────────────────────

    def _draw_grid(self, painter: QPainter, rot: np.ndarray,
                   cx: float, cy: float, w: float, h: float) -> None:
        size = 10.0
        step = 1.0
        pen = QPen(self._grid_color, 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        half = size / 2.0
        n = int(size / step)
        for i in range(n + 1):
            v = -half + i * step
            for start, end in [((-half, v, 0), (half, v, 0)),
                               ((v, -half, 0), (v, half, 0))]:
                p0 = _apply_rotation(rot, np.array([start]))[0]
                p1 = _apply_rotation(rot, np.array([end]))[0]
                x0 = cx + (p0[0] + self._cam_x) / self._zoom
                y0 = cy - (p0[1] + self._cam_y) / self._zoom
                x1 = cx + (p1[0] + self._cam_x) / self._zoom
                y1 = cy - (p1[1] + self._cam_y) / self._zoom
                painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))

    def _draw_axes(self, painter: QPainter, rot: np.ndarray,
                   cx: float, cy: float) -> None:
        length = 2.0
        axis_len = 50  # pixeles en pantalla
        axes = [
            (np.array([length, 0, 0]), self._axes_colors[0], "X"),
            (np.array([0, length, 0]), self._axes_colors[1], "Y"),
            (np.array([0, 0, length]), self._axes_colors[2], "Z"),
        ]
        ox, oy = 40.0, float(self.height()) - 40.0  # esquina inferior izquierda
        for vec, color, label in axes:
            p = _apply_rotation(rot, vec.reshape(1, 3))[0]
            # Proyectar: eje X → horizontal, eje Y → vertical (invertido)
            dx = p[0] * axis_len / length
            dy = -p[1] * axis_len / length
            pen = QPen(color, 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawLine(QPointF(ox, oy), QPointF(ox + dx, oy + dy))
            painter.setPen(color)
            painter.drawText(QPointF(ox + dx * 1.2, oy + dy * 1.2), label)

    def _draw_model(self, painter: QPainter, rot: np.ndarray,
                    cx: float, cy: float, w: float, h: float) -> None:
        verts = self._scene._vertices
        tris = self._scene._triangles
        if verts is None or tris is None:
            return

        # Transformar todos los vértices
        transformed = _apply_rotation(rot, verts)
        self._scene._transformed_verts = transformed

        # Proyectar con z usando la misma convencion que malla/densidad/rejilla:
        # X = cx + (rx + cam_x) / zoom, Y = cy - (ry + cam_y) / zoom.
        projected = np.empty((transformed.shape[0], 3))
        projected[:, 0] = cx + (transformed[:, 0] + self._cam_x) / self._zoom
        projected[:, 1] = cy - (transformed[:, 1] + self._cam_y) / self._zoom
        projected[:, 2] = transformed[:, 2]  # profundidad para z-sort
        self._scene._projected_pts = projected

        # Ordenar caras por profundidad (back-to-front, mayor z = más lejos)
        centroids = (projected[tris[:, 0]] + projected[tris[:, 1]] + projected[tris[:, 2]]) / 3.0
        order = np.argsort(-centroids[:, 2])  # mayor z primero (más lejos → dibujar primero)

        light_dir = _normalize(np.array([0.3, 0.6, 1.0]))

        face_index_map = self._scene._face_index_map
        selected_faces = set(self._selection_mgr._selected_faces)
        # Cuando hay mapeo por cara, los triángulos seleccionados son los que
        # pertenecen a las caras B-Rep seleccionadas (resalta la cara completa).
        if face_index_map is not None:
            selected_tris = set(
                int(fi) for fi in face_index_map
                if int(fi) in selected_faces
            )
        else:
            selected_tris = selected_faces

        mode = self._scene._display_mode
        draw_fill = mode in ("surfaced", "surfaced_edges", "transparent")
        draw_edges = mode in ("surfaced_edges", "wireframe")
        opacity = 0.4 if mode == "transparent" else 1.0

        for i in order:
            t = tris[i]
            poly = QPolygonF([
                QPointF(projected[t[0], 0], projected[t[0], 1]),
                QPointF(projected[t[1], 0], projected[t[1], 1]),
                QPointF(projected[t[2], 0], projected[t[2], 1]),
            ])

            # Color de la cara
            selected = i in selected_tris
            if selected:
                fc = self._selection_color
            else:
                fc = self._model_color

            if draw_fill:
                if selected:
                    # Cara seleccionada: dorado brillante y uniforme (sin sombra
                    # flat) para que toda la cara se distinga inequívocamente.
                    fill_color = QColor(fc.red(), fc.green(), fc.blue())
                    if opacity < 1.0:
                        fill_color.setAlphaF(opacity)
                else:
                    # Iluminación flat
                    v0, v1, v2 = verts[t[0]], verts[t[1]], verts[t[2]]
                    n = _face_normal(v0, v1, v2)
                    n_rot = _apply_rotation(rot, n.reshape(1, 3))[0]
                    n_rot = _normalize(n_rot)
                    dot = max(0.0, np.dot(n_rot, light_dir))
                    ambient = 0.3
                    intensity = min(1.0, ambient + (1.0 - ambient) * dot)
                    r = int(fc.red() * intensity)
                    g = int(fc.green() * intensity)
                    b = int(fc.blue() * intensity)
                    fill_color = QColor(r, g, b)
                    if opacity < 1.0:
                        fill_color.setAlphaF(opacity)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(fill_color))
                painter.drawPolygon(poly)

            if draw_edges:
                edge_pen = QPen(self._model_edge, 1, Qt.PenStyle.SolidLine)
                painter.setPen(edge_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPolygon(poly)

    def _draw_mesh(self, painter: QPainter, rot: np.ndarray,
                   cx: float, cy: float) -> None:
        nodes = self._scene._mesh_nodes
        elements = self._scene._mesh_elements
        if nodes is None or elements is None:
            return
        transformed = _apply_rotation(rot, nodes)
        pen = QPen(self._mesh_color, 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for elem in elements:
            for j in range(len(elem)):
                n0, n1 = elem[j], elem[(j + 1) % len(elem)]
                p0 = transformed[n0]
                p1 = transformed[n1]
                x0 = cx + (p0[0] + self._cam_x) / self._zoom
                y0 = cy - (p0[1] + self._cam_y) / self._zoom
                x1 = cx + (p1[0] + self._cam_x) / self._zoom
                y1 = cy - (p1[1] + self._cam_y) / self._zoom
                painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))

    def _draw_density(self, painter: QPainter, rot: np.ndarray,
                      cx: float, cy: float) -> None:
        nodes = self._scene._density_nodes
        elements = self._scene._density_elements
        values = self._scene._density_values
        if nodes is None or elements is None or values is None:
            return
        transformed = _apply_rotation(rot, nodes)
        vmin, vmax = float(np.min(values)), float(np.max(values))
        vrange = vmax - vmin if vmax > vmin else 1.0
        painter.setPen(Qt.PenStyle.NoPen)
        for i, elem in enumerate(elements):
            t_val = (float(values[i]) - vmin) / vrange
            r = int(255 * min(1.0, max(0.0, 2 * (1 - t_val))))
            g = int(255 * min(1.0, max(0.0, 2 * t_val - 0.5)))
            b = int(255 * min(1.0, max(0.0, 2 * t_val - 1.0)))
            color = QColor(r, g, b)
            painter.setBrush(QBrush(color))
            poly = QPolygonF()
            for n_idx in elem:
                p = transformed[n_idx]
                poly.append(QPointF(cx + (p[0] + self._cam_x) / self._zoom,
                                    cy - (p[1] + self._cam_y) / self._zoom))
            painter.drawPolygon(poly)
