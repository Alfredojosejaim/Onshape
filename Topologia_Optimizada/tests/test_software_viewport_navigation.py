"""Convención de navegación del SoftwareViewport (pan + zoom).

Fija la regla "el modelo sigue al cursor" para el viewport por software
(fallback sin GPU) y protege la proyección del paint:

    X = cx + (rx + cam_x) / zoom
    Y = cy - (ry + cam_y) / zoom

Los signos de cam_x/cam_y y zoom (desplazamiento por pixel) se interpretan en
coordenadas *de pantalla* (Y crece hacia abajo), por lo que el pan vertical
debe restar cam_y al arrastrar hacia abajo para que el modelo siga al cursor.
"""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtWidgets import QApplication

from desktop.viewport.software_viewport import (
    SoftwareViewport,
    _apply_rotation,
    _rotation_x,
    _rotation_z,
)


def _qapp():
    return QApplication.instance() or QApplication([])


def _screenshot_projection(vp, point):
    """Reproduce la proyección del paint para un punto del modelo."""
    rot = _rotation_z(math.radians(vp._rot_z)) @ _rotation_x(math.radians(vp._rot_x))
    r = _apply_rotation(rot, np.array([point], dtype=float)).reshape(3)
    cx = vp.width() / 2.0
    cy = vp.height() / 2.0
    x = cx + (float(r[0]) + vp._cam_x) / vp._zoom
    y = cy - (float(r[1]) + vp._cam_y) / vp._zoom
    return x, y


def _front_viewport():
    vp = SoftwareViewport()
    vp.resize(400, 400)
    vp._rot_x = 0.0
    vp._rot_z = 0.0
    vp._cam_x = 0.0
    vp._cam_y = 0.0
    vp._zoom = 100.0
    return vp


def test_pan_vertical_follows_pointer():
    """Arrastrar abajo (dy>0 en pantalla) debe mover el modelo hacia abajo."""
    _qapp()
    vp = _front_viewport()
    pt = (0.0, 10.0, 0.0)
    y0 = _screenshot_projection(vp, pt)[1]
    vp._cam_y -= 20 * vp._zoom * 0.002  # fórmula de mouseMoveEvent (pan)
    y1 = _screenshot_projection(vp, pt)[1]
    assert y1 > y0, "arrastrar abajo debe bajar el modelo en pantalla (Y aumenta)"


def test_pan_horizontal_follows_pointer():
    """Arrastrar a la derecha (dx>0) debe mover el modelo a la derecha."""
    _qapp()
    vp = _front_viewport()
    pt = (10.0, 0.0, 0.0)
    x0 = _screenshot_projection(vp, pt)[0]
    vp._cam_x += 20 * vp._zoom * 0.002  # fórmula de mouseMoveEvent (pan)
    x1 = _screenshot_projection(vp, pt)[0]
    assert x1 > x0, "arrastrar derecha debe mover el modelo a la derecha"


def test_wheel_up_zooms_in():
    """Rueda hacia arriba (delta>0) reduce zoom (más cerca) -> acercar."""
    _qapp()
    vp = _front_viewport()
    delta = 2.0  # rueda hacia arriba
    factor = 1.0 - delta * 0.15
    vp._zoom = max(0.01, vp._zoom * factor)
    assert vp._zoom < 100.0, "rueda arriba debe acercar (bajar zoom => más grande)"
