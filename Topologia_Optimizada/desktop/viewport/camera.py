"""Camera - view transformation, navigation and preset standard views.

This layer owns all the math and view-algebra around the renderer's active
camera. It exposes CAD-like navigation primitives (orbit, zoom, pan, fit, and
the six standard orthographic views plus isometric) without the interface
knowing anything about the underlying graphics API.
"""

from __future__ import annotations

import math

import numpy as np


class StandardView:
    FRONT = "front"
    BACK = "back"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    ISO = "isometric"


# camera position for each standard view (target at origin assumed; we
# re-anchor to the scene focal point at call time).
_VIEW_DIRS = {
    StandardView.FRONT: (0.0, -1.0, 0.0),
    StandardView.BACK: (0.0, 1.0, 0.0),
    StandardView.TOP: (0.0, 0.0, 1.0),
    StandardView.BOTTOM: (0.0, 0.0, -1.0),
    StandardView.LEFT: (-1.0, 0.0, 0.0),
    StandardView.RIGHT: (1.0, 0.0, 0.0),
    StandardView.ISO: (1.0, 1.0, 1.0),
}

# view up vector per standard view
_VIEW_UPS = {
    StandardView.FRONT: (0.0, 0.0, 1.0),
    StandardView.BACK: (0.0, 0.0, 1.0),
    StandardView.TOP: (0.0, 1.0, 0.0),
    StandardView.BOTTOM: (0.0, 1.0, 0.0),
    StandardView.LEFT: (0.0, 0.0, 1.0),
    StandardView.RIGHT: (0.0, 0.0, 1.0),
    StandardView.ISO: (0.0, 0.0, 1.0),
}


def _rodrigues(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotation matrix (3x3) about ``axis`` by ``angle`` radians."""
    a = np.asarray(axis, dtype=float)
    a = a / (np.linalg.norm(a) + 1e-12)
    x, y, z = a
    c, s = math.cos(angle), math.sin(angle)
    one_c = 1.0 - c
    return np.array(
        [
            [c + x * x * one_c, x * y * one_c - z * s, x * z * one_c + y * s],
            [y * x * one_c + z * s, c + y * y * one_c, y * z * one_c - x * s],
            [z * x * one_c - y * s, z * y * one_c + x * s, c + z * z * one_c],
        ]
    )


class Camera:
    def __init__(self, vtk_camera) -> None:
        self._cam = vtk_camera
        self._focal = np.array([0.0, 0.0, 0.0])
        self._distance = 10.0

    # ------------------------------------------------------------------ #
    # Positional queries (used by views + scene fit)
    # ------------------------------------------------------------------ #

    @property
    def focal_point(self) -> np.ndarray:
        return np.array(self._cam.GetFocalPoint())

    @property
    def position(self) -> np.ndarray:
        return np.array(self._cam.GetPosition())

    @property
    def distance(self) -> float:
        return float(self._cam.GetDistance())

    def set_target(self, center, radius: float, delta: float = 1.2) -> None:
        """Recenter the camera on ``center`` at a sensible distance from ``radius``."""
        self._focal = np.asarray(center, dtype=float)
        self._distance = radius * delta
        self._cam.SetFocalPoint(*self._focal)
        self._cam.SetPosition(*(self._focal + np.array([self._distance, 0, 0])))
        self._cam.SetViewUp(0, 0, 1)
        self._fit_plane(self._distance)

    def _fit_plane(self, distance: float) -> None:
        self._cam.SetClippingRange(distance / 50.0, distance * 50.0)

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def orbit(self, dx: float, dy: float, sensitivity: float = 0.008) -> None:
        """Rotate the camera around the focal point from pixel deltas."""
        forward = self._focal - self._cam.GetPosition()
        forward = forward / np.linalg.norm(forward)
        up = np.array(self._cam.GetViewUp())
        right = np.cross(forward, up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)

        # yaw around "up", then pitch around "right"
        yaw = -dx * sensitivity
        pitch = dy * sensitivity

        dir_vec = forward
        if yaw:
            dir_vec = (_rodrigues(up, yaw) @ dir_vec)
        if pitch:
            dir_vec = (_rodrigues(right, pitch) @ dir_vec)
        dir_vec = dir_vec / np.linalg.norm(dir_vec)

        pos = self._focal - dir_vec * self.distance
        self._cam.SetPosition(*pos)

        # rebuild a stable up-vector
        new_right = np.cross(dir_vec, np.array([0, 0, 1.0]))
        if np.linalg.norm(new_right) > 1e-6:
            new_right = new_right / np.linalg.norm(new_right)
            new_up = np.cross(new_right, dir_vec)
            new_up = new_up / np.linalg.norm(new_up)
        else:
            new_up = np.array([0.0, 1.0, 0.0])
        self._cam.SetViewUp(*new_up)

    def dolly(self, steps: float, sensitivity: float = 0.8) -> None:
        """Zoom by scaling the camera distance along the view direction."""
        factor = math.exp(-steps * sensitivity)
        self._distance = max(1e-4, self._distance * factor)
        forward = self._focal - self._cam.GetPosition()
        forward = forward / np.linalg.norm(forward)
        self._cam.SetPosition(*(self._focal - forward * self._distance))
        self._fit_plane(self._distance)

    def pan(self, dx: float, dy: float, sensitivity: float = 0.002) -> None:
        """Translate the focal point (and camera) in the image plane."""
        distance = self.distance
        forward = self._focal - self._cam.GetPosition()
        forward = forward / np.linalg.norm(forward)
        up = np.array(self._cam.GetViewUp())
        right = np.cross(forward, up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)

        scale = distance * sensitivity
        delta = right * (-dx * scale) + up * (dy * scale)
        self._focal = self._focal + delta
        self._cam.SetFocalPoint(*self._focal)
        self._cam.SetPosition(*(self.position + delta))
        self._fit_plane(distance)

    # ------------------------------------------------------------------ #
    # Standard views
    # ------------------------------------------------------------------ #

    def set_view(self, view: str | None) -> None:
        if view not in _VIEW_DIRS:
            view = StandardView.ISO
        direction = np.array(_VIEW_DIRS[view], dtype=float)
        direction = direction / np.linalg.norm(direction)
        up = np.array(_VIEW_UPS[view], dtype=float)
        distance = self.distance
        self._cam.SetPosition(*(self._focal - direction * distance))
        self._cam.SetViewUp(*up)
        self._cam.SetFocalPoint(*self._focal)
        self._fit_plane(distance)

    def fit(self) -> None:
        """Re-anchor on the current target and distance (used after geometry load)."""
        self._cam.SetFocalPoint(*self._focal)
        self._cam.SetPosition(*(self._focal + np.array([self._distance, 0, 0])))
        self._cam.SetViewUp(0, 0, 1)
        self._fit_plane(self._distance)
