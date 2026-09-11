"""CameraController - independent camera transformation and standard views.

This layer owns all the math and view-algebra around the renderer's active
camera. It is an independent system that is NOT part of ``NavigationManager``:

    NavigationManager   ->  determines WHAT action the user asks for
    CameraController    ->  determines HOW the camera is transformed in 3D

It exposes CAD-like navigation primitives (orbit, zoom, pan, fit, and the six
standard orthographic views plus isometric) without the interface knowing
anything about the underlying graphics API.

The camera is deliberately free: orbit is a trackball rotation around the
focal point (not locked to world axes), pan moves in camera space, and zoom is
aligned with the view direction.  Standard views and fit-to-view are one-shot
repositionings and never permanently restrict subsequent free navigation.
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


class CameraController:
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
        """Free trackball orbit around the focal point (Onshape-style).

        Any (dx, dy) mouse displacement is mapped to a single rotation about
        the screen-plane axis perpendicular to the drag direction, so the view
        follows the pointer along a great circle instead of being locked to
        fixed world axes. The view-up is rotated together with the view
        direction and re-orthonormalized, which lets the camera reach any
        orientation (including rolled) without gimbal hangups.
        """
        forward = self.focal_point - self.position
        dist = float(np.linalg.norm(forward))
        if dist < 1e-12:
            return
        forward = forward / dist

        up = np.array(self._cam.GetViewUp())
        right = np.cross(forward, up)
        nr = float(np.linalg.norm(right))
        if nr < 1e-9:
            right = np.cross(forward, np.array([0.0, 1.0, 0.0]))
            nr = float(np.linalg.norm(right))
            if nr < 1e-9:
                right = np.cross(forward, np.array([1.0, 0.0, 0.0]))
                nr = float(np.linalg.norm(right))
        right = right / nr
        up = np.cross(right, forward)

        # drag vector in the view plane.
        # VTK's QVTKRenderWindowInteractor flips Qt's Y (y_vtk = h - y_qt - 1),
        # so dy > 0 means drag UP on screen.  The -dx sign makes the model
        # follow the pointer horizontally (drag right -> the camera orbits
        # right, the model appears to rotate right).  The -dy sign makes the
        # camera drop when dragging up, so the model moves up on screen.
        drag = right * (-dx) + up * (-dy)
        dmg = float(np.linalg.norm(drag))
        if dmg < 1e-12:
            return
        drag = drag / dmg

        # rotation axis: perpendicular to the drag, within the view plane
        axis = np.cross(drag, forward)
        axis = axis / np.linalg.norm(axis)
        angle = dmg * sensitivity

        rot = _rodrigues(axis, angle)
        new_forward = rot @ forward
        new_forward = new_forward / np.linalg.norm(new_forward)

        new_up = rot @ up
        new_up = new_up - new_forward * float(np.dot(new_up, new_forward))
        if np.linalg.norm(new_up) < 1e-9:
            new_up = np.array([0.0, 1.0, 0.0])
        else:
            new_up = new_up / np.linalg.norm(new_up)

        self._cam.SetPosition(*(self.focal_point - new_forward * dist))
        self._cam.SetViewUp(*new_up)

    def dolly(self, steps: float, sensitivity: float = 0.8) -> None:
        """Zoom by scaling the camera distance along the view direction.

        Works from the camera's actual current state (position + focal point),
        so the step size is always correct regardless of the starting view or
        previously applied navigation.
        """
        factor = math.exp(-steps * sensitivity)
        dist = max(1e-4, self.distance * factor)
        self._distance = dist  # keep the fit anchor in sync
        forward = self.focal_point - self.position
        forward = forward / (np.linalg.norm(forward) + 1e-12)
        self._cam.SetPosition(*(self.focal_point - forward * dist))
        self._fit_plane(dist)

    def pan(self, dx: float, dy: float, sensitivity: float = 0.002) -> None:
        """Translate the focal point (and camera) in the image plane.

        ``dx``/``dy`` come from the VTK interactor whose Y axis is bottom-up
        (QVTKRenderWindowInteractor flips Qt's top-down Y).  The ``-dy``
        correction compensates so dragging DOWN on screen moves the model DOWN
        (the model follows the pointer).
        """
        distance = self.distance
        forward = self.focal_point - self.position
        forward = forward / np.linalg.norm(forward)
        up = np.array(self._cam.GetViewUp())
        right = np.cross(forward, up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)

        scale = distance * sensitivity
        delta = right * (-dx * scale) + up * (-dy * scale)
        focal = self.focal_point + delta
        self._focal = focal
        self._cam.SetFocalPoint(*focal)
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
        focal = self.focal_point
        distance = self.distance
        self._cam.SetPosition(*(focal - direction * distance))
        self._cam.SetViewUp(*up)
        self._cam.SetFocalPoint(*focal)
        self._fit_plane(distance)

    def fit(self) -> None:
        """Re-anchor on the current target and distance (used after geometry load)."""
        self._cam.SetFocalPoint(*self._focal)
        self._cam.SetPosition(*(self._focal + np.array([self._distance, 0, 0])))
        self._cam.SetViewUp(0, 0, 1)
        self._fit_plane(self._distance)
