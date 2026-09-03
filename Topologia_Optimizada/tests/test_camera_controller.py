"""Validation of the independent CameraController (prompt §17).

The CameraController is the layer that transforms the camera in 3D space; it is
kept separate from the NavigationManager (which only decides WHAT action the
user requests).  These tests exercise the 15 explicit validation cases from the
prompt using a bare ``vtkCamera`` (no rendering window or GUI required).
"""

import math

import numpy as np
import pytest

from vtkmodules.vtkRenderingCore import vtkCamera

from desktop.viewport.camera import CameraController, StandardView
from core.navigation import (
    InputEvent,
    MouseButton,
    NavigationManager,
    ViewportAction,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

@pytest.fixture
def controller():
    """A CameraController wrapped around a bare vtkCamera (headless-friendly)."""
    return CameraController(vtkCamera())


def _norm(v):
    return np.asarray(v, dtype=float) / (np.linalg.norm(v) + 1e-12)


def _view_dir(cam):
    """Unit vector pointing from camera position toward the focal point."""
    fwd = np.array(cam.focal_point) - np.array(cam.position)
    return _norm(fwd)


def _assert_focal_fixed(cam, before):
    assert np.allclose(cam.focal_point, before), "focal point must not move"


def _assert_orientation_changed(cam, before_dir):
    assert not np.allclose(_view_dir(cam), _norm(before_dir)), (
        "view direction should have changed after orbit"
    )


def _set_arbitrary(cam):
    """Put the camera in an orientation not aligned with any global axis."""
    cam.set_view(StandardView.ISO)
    cam.orbit(0.313, -0.771, sensitivity=0.03)
    cam.orbit(0.11, 0.4, sensitivity=0.02)


# --------------------------------------------------------------------------- #
# 1-4. Orbit from different starting orientations
# --------------------------------------------------------------------------- #

def test_orbit_from_isometric(controller):
    controller.set_view(StandardView.ISO)
    before = controller.focal_point
    before_dir = _view_dir(controller)
    controller.orbit(0.2, -0.15)
    _assert_focal_fixed(controller, before)
    _assert_orientation_changed(controller, before_dir)


def test_orbit_from_front(controller):
    controller.set_view(StandardView.FRONT)
    before = controller.focal_point
    before_dir = _view_dir(controller)
    controller.orbit(0.3, 0.1)
    _assert_focal_fixed(controller, before)
    _assert_orientation_changed(controller, before_dir)


def test_orbit_from_top(controller):
    controller.set_view(StandardView.TOP)
    before = controller.focal_point
    before_dir = _view_dir(controller)
    controller.orbit(-0.1, 0.25)
    _assert_focal_fixed(controller, before)
    _assert_orientation_changed(controller, before_dir)


def test_orbit_from_arbitrary(controller):
    _set_arbitrary(controller)
    before = controller.focal_point
    before_dir = _view_dir(controller)
    controller.orbit(0.4, 0.3)
    _assert_focal_fixed(controller, before)
    _assert_orientation_changed(controller, before_dir)


# --------------------------------------------------------------------------- #
# Vertical orbit sense (follow-the-pointer; horizontal must be unaffected)
# --------------------------------------------------------------------------- #

def test_orbit_vertical_sense_follows_pointer(controller):
    """Dragging UP on screen (dy<0) must make the view move up: the camera
    drops (its world-space normal-to-view offset decreases) so the model goes
    up on screen. This pins the fix for the reported inverted vertical orbit.
    Horizontal and vertical use independent senses; we only assert vertical.
    """
    controller.set_view(StandardView.FRONT)
    cam_z0 = controller.position[2]
    controller.orbit(0.0, -5.0, sensitivity=0.01)   # drag up on screen
    cam_z1 = controller.position[2]
    assert cam_z1 < cam_z0, (
        "dragging up should lower the camera in the view-normal direction"
    )


def test_orbit_horizontal_sense_unaffected(controller):
    """Flipping the vertical sense must NOT change the horizontal one.

    The horizontal drag sign is left as the original (user-reported correct)
    behaviour: dragging right on screen moves the camera toward -X in FRONT view.
    """
    right_pos = _orbit_drag(controller, dx=6.0, dy=0.0)
    assert right_pos[0] < 0, "drag right must keep its original -X motion"


def _orbit_drag(controller, dx, dy, sensitivity=0.01):
    """Return the camera position after a single orbit drag."""
    controller.set_view(StandardView.FRONT)
    controller.orbit(dx, dy, sensitivity=sensitivity)
    return controller.position


# --------------------------------------------------------------------------- #
# 5. Rotation stays anchored on the model (focal point + distance preserved)
# --------------------------------------------------------------------------- #

def test_rotation_keeps_focal_and_distance(controller):
    controller.set_target([5.0, -2.0, 3.0], 4.0, delta=2.0)
    before_dist = controller.distance
    before_focal = controller.focal_point
    for _ in range(5):
        controller.orbit(0.1, -0.2)
    _assert_focal_fixed(controller, before_focal)
    assert np.allclose(controller.distance, before_dist), (
        "orbit must keep the camera at a constant distance from the target"
    )


# --------------------------------------------------------------------------- #
# 6. Pan with an inclined camera
# --------------------------------------------------------------------------- #

def test_pan_inclined_camera(controller):
    _set_arbitrary(controller)
    before_dir = _view_dir(controller)
    before_focal = controller.focal_point
    before_pos = controller.position
    before_dist = controller.distance
    controller.pan(40, -20)
    # focal and position translate together, keeping the same relative geometry
    assert np.allclose(_view_dir(controller), before_dir), (
        "pan must not change the camera orientation"
    )
    delta_focal = controller.focal_point - before_focal
    delta_pos = controller.position - before_pos
    assert np.allclose(delta_focal, delta_pos), "pan must move camera + target together"
    assert np.allclose(controller.distance, before_dist), (
        "pan must keep the lens distance constant"
    )


# --------------------------------------------------------------------------- #
# 7-8. Zoom
# --------------------------------------------------------------------------- #

def test_zoom_inclined_camera(controller):
    _set_arbitrary(controller)
    before_dir = _view_dir(controller)
    before_focal = controller.focal_point
    before_dist = controller.distance
    controller.dolly(2.0, sensitivity=0.5)
    assert controller.distance < before_dist, "dolly(+) must bring the camera closer"
    _assert_focal_fixed(controller, before_focal)
    assert np.allclose(_view_dir(controller), before_dir), (
        "zoom must stay aligned with the camera view direction"
    )


def test_zoom_toward_point_of_interest(controller):
    controller.set_target([1.0, 1.0, 1.0], 5.0, delta=2.0)
    focal = controller.focal_point
    d0 = controller.distance
    for _ in range(3):
        controller.dolly(1.0, sensitivity=0.5)
    assert controller.distance < d0 * 0.999
    _assert_focal_fixed(controller, focal)
    # camera must keep heading straight at the focal point (view direction along
    # focal - position, i.e. pointing at the point of interest)
    fwd = _view_dir(controller)
    assert np.allclose(fwd, _norm(focal - np.array(controller.position)))


# --------------------------------------------------------------------------- #
# 9-11. Fit to view + predefined views
# --------------------------------------------------------------------------- #

def test_fit_to_view(controller):
    controller.set_target([2.0, -1.0, 4.0], 3.0, delta=4.0)
    assert np.allclose(controller.focal_point, [2.0, -1.0, 4.0])
    assert controller.distance == pytest.approx(3.0 * 4.0)


def test_change_predefined_view(controller):
    controller.set_view(StandardView.ISO)
    iso_dir = _view_dir(controller)
    controller.set_view(StandardView.TOP)
    top_dir = _view_dir(controller)
    assert not np.allclose(iso_dir, top_dir)
    # TOP looks straight down the +Z axis (camera above, looking at origin)
    assert np.allclose(top_dir, [0.0, 0.0, 1.0], atol=1e-6)


def test_orbit_after_predefined_view(controller):
    controller.set_view(StandardView.FRONT)
    before_dir = _view_dir(controller)
    controller.orbit(0.2, 0.1)
    assert not np.allclose(_view_dir(controller), before_dir)


# --------------------------------------------------------------------------- #
# 12-13. Combined sequences (freedom maintained)
# --------------------------------------------------------------------------- #

def test_orbit_pan_zoom(controller):
    controller.set_view(StandardView.ISO)
    controller.orbit(0.2, -0.2)
    controller.pan(30, 10)
    d1 = controller.distance
    controller.dolly(1.0, sensitivity=0.5)
    assert controller.distance < d1
    # still fully free: another orbit must change orientation
    dir_before = _view_dir(controller)
    controller.orbit(0.25, 0.05)
    assert not np.allclose(_view_dir(controller), dir_before)


def test_pan_orbit_zoom(controller):
    _set_arbitrary(controller)
    focal_b = controller.focal_point
    controller.pan(-25, 15)
    assert not np.allclose(controller.focal_point, focal_b), "pan must move the target"
    controller.orbit(0.15, -0.3)
    d1 = controller.distance
    controller.dolly(1.0, sensitivity=0.5)
    assert controller.distance < d1


# --------------------------------------------------------------------------- #
# 14. Motion in orientations not aligned with X/Y/Z
# --------------------------------------------------------------------------- #

def test_motion_in_non_axis_aligned_orientation(controller):
    _set_arbitrary(controller)
    # ensure the orientation truly isn't axis-aligned
    v = _view_dir(controller)
    axis_aligned = any(np.allclose(np.abs(v), np.eye(3)[i]) for i in range(3))
    assert not axis_aligned, "precondition: camera should be in a free orientation"
    before_focal = controller.focal_point
    controller.orbit(0.1, 0.1)
    controller.pan(20, -5)
    controller.dolly(1.0, sensitivity=0.4)
    assert controller.distance > 0


# --------------------------------------------------------------------------- #
# 15. Changing navigation profile does not break the camera
# --------------------------------------------------------------------------- #

def test_switching_profile_keeps_camera(controller):
    nav = NavigationManager(profile_name="autocad")
    cam_pos = np.array(controller.position)
    cam_focal = np.array(controller.focal_point)

    # Swap profiles; resolve actions must reflect each profile and the camera
    # must be untouched (swapping a profile never moves the camera).
    ev_orbit = InputEvent(mouse_button=MouseButton.MIDDLE, shift=True)
    ev_pan = InputEvent(mouse_button=MouseButton.MIDDLE)

    assert nav.set_profile("onshape")
    assert nav.resolve(InputEvent(mouse_button=MouseButton.RIGHT)).action == ViewportAction.ORBIT
    assert nav.set_profile("fusion360")
    assert nav.resolve(ev_orbit).action == ViewportAction.ORBIT
    assert nav.resolve(ev_pan).action == ViewportAction.PAN
    assert nav.set_profile("blender")
    assert nav.resolve(InputEvent(mouse_button=MouseButton.MIDDLE)).action == ViewportAction.ORBIT

    assert np.allclose(controller.position, cam_pos)
    assert np.allclose(controller.focal_point, cam_focal)


def test_all_profiles_available():
    names = {p["name"] for p in NavigationManager.available_profiles()}
    assert {"autocad", "onshape", "fusion360", "blender"} <= names
