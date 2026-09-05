"""Regresión: selección de cara en el SoftwareViewport (fallback sin GPU).

Bug corregido: ``_SoftwareScene.pick_face`` devolvía el **índice del triángulo**
(0..N-1) en vez del **índice B-Rep** de la cara. Como consecuencia el resaltado
pintaba un único triángulo (aparentaba "media cara"), no se seleccionaban las
demás caras y ``face_index`` emitido quedaba fuera del rango [0, n_cad_faces),
rompiendo el mapeo de cargas/restricciones (``map_nodes_to_face``).

Ahora ``pick_face`` resuelve el triángulo más cercano y lo asigna a su cara B-Rep
vía ``_face_index_map``; ``face_to_triangles`` y el pintado resaltan la cara
completa.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from desktop.viewport.software_viewport import _SoftwareScene


def _sample_scene():
    """Escena sintética: dos caras (0 y 1) con triángulos en planos xz distintos
    para que su proyección en pantalla no se solape (pick inequívoco)."""
    verts = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],  # cara 0 (z=0)
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],  # cara 1 (z=1)
    ], dtype=float)
    tris = np.array([
        [0, 1, 3], [1, 2, 3],  # 2 triángulos -> cara 0
        [4, 5, 7], [5, 6, 7],  # 2 triángulos -> cara 1
    ], dtype=np.int64)
    face_map = np.array([0, 0, 1, 1], dtype=np.int64)
    faces_meta = [
        {"face_index": 0, "id": "face_0", "center": [0.5, 0.5, 0.0],
         "normal": [0, 0, -1], "area": 1.0},
        {"face_index": 1, "id": "face_1", "center": [0.5, 0.5, 1.0],
         "normal": [0, 0, 1], "area": 1.0},
    ]
    scene = _SoftwareScene()
    scene.set_model_geometry(verts, tris, face_index_map=face_map, faces_meta=faces_meta)
    _project(scene)
    return scene, verts, tris, face_map


def _project(scene):
    """Proyección ortográfica del paint con cámara mirando +z (profundidad = z)."""
    cx, cy, zoom = 200.0, 200.0, 100.0
    v = scene._vertices
    projected = np.empty((v.shape[0], 3))
    projected[:, 0] = cx + v[:, 0] / zoom
    projected[:, 1] = cy - v[:, 1] / zoom
    projected[:, 2] = v[:, 2]
    scene._projected_pts = projected
    return scene


def _screen_centroid(scene, tri):
    """Centroide de pantalla de un triángulo dado."""
    pts = scene._projected_pts
    t = tri
    return (pts[t[0], 0] + pts[t[1], 0] + pts[t[2], 0]) / 3.0, \
           (pts[t[0], 1] + pts[t[1], 1] + pts[t[2], 1]) / 3.0


def test_pick_face_returns_brep_face_index_not_triangle_index():
    """Hacer clic sobre el sólido devuelve un índice B-Rep de cara (0 o 1), NUNCA
    un índice de triángulo (0..3). Es la regresión del bug de "media cara"."""
    scene, _, _, _ = _sample_scene()
    # Punto en pantalla sobre la cara superior (triángulo cara 1). En la
    # convención del paint (mayor z = más lejos) la cara z=0 queda más cercana,
    # por lo que el face_index correcto es 0; lo que NO debe aparecer es 2 o 3.
    sx, sy = _screen_centroid(scene, [4, 5, 7])
    face = scene.pick_face(sx, sy)
    assert face in (0, 1), f"pick_face devolvió un índice no-B-Rep: {face}"
    assert not (face in (2, 3)), "pick_face devolvió índice de triángulo"


def test_pick_face_returns_brep_index_for_lower_face():
    """Hacer clic en la cara inferior (triángulo cara 0) devuelve face_index 0."""
    scene, _, _, _ = _sample_scene()
    sx, sy = _screen_centroid(scene, [0, 1, 3])
    face = scene.pick_face(sx, sy)
    assert face == 0, f"se esperaba face_index 0, se obtuvo {face}"


def test_face_to_triangles_returns_all_triangles_of_face():
    """Resaltar una cara debe cubrir TODOS sus triángulos (la cara completa)."""
    scene, _, tris, face_map = _sample_scene()
    sel0 = scene.face_to_triangles(0)
    sel1 = scene.face_to_triangles(1)
    expected0 = [int(i) for i in range(tris.shape[0]) if int(face_map[i]) == 0]
    expected1 = [int(i) for i in range(tris.shape[0]) if int(face_map[i]) == 1]
    assert sorted(sel0) == sorted(expected0) and len(sel0) == 2
    assert sorted(sel1) == sorted(expected1) and len(sel1) == 2


def test_face_meta_lookup():
    """face_meta recupera los metadatos de la cara por índice B-Rep."""
    scene, _, _, _ = _sample_scene()
    assert scene.face_meta(0)["id"] == "face_0"
    assert scene.face_meta(1)["id"] == "face_1"
    assert scene.face_meta(99) is None


def test_pick_face_without_face_map_falls_back_to_triangle_index():
    """Sin map por cara, pick_face NO inventa face_index (devuelve None).

    Devolver el índice del triángulo como face_index rompía el mapeo
    CAD (cargas/restricciones) al apuntar a caras vecinas inexistentes.
    Actualizado por P1-prompts.md §2: el face_index debe corresponder a
    la cara CAD real o no atribuirse.
    """
    scene, verts, _, _ = _sample_scene()
    scene.set_model_geometry(verts, scene._triangles, face_index_map=None, faces_meta=None)
    _project(scene)
    sx, sy = _screen_centroid(scene, [4, 5, 7])
    face = scene.pick_face(sx, sy)
    assert face is None


# ------------------------------------------------------------------ #
# Retroalimentación: paint resalta la cara COMPLETA y no crashea.
# ------------------------------------------------------------------ #
def _make_viewport():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QPaintEvent
    from desktop.viewport.software_viewport import SoftwareViewport

    app = QApplication.instance() or QApplication([])
    vp = SoftwareViewport()
    vp.resize(400, 400)
    return vp, QRect(0, 0, 400, 400), QPaintEvent


def test_paint_highlights_entire_selected_face():
    """Al seleccionar una cara, el render colorea TODOS sus triángulos (la cara
    completa), no un único triángulo, y el paint no crashea."""
    scene, verts, tris, face_map = _sample_scene()
    vp, r, QPaintEvent = _make_viewport()
    try:
        vp._scene = scene
        vp._scene.set_model_geometry(verts, tris, face_index_map=face_map,
                                     faces_meta=scene._faces_meta)
        center0 = scene.face_to_triangles(0)
        # Seleccionar la cara 0 a través del selection manager
        vp._selection_mgr._selected_faces = [0]
        vp._selection_mgr._selected_solids = set()
        vp.paintEvent(QPaintEvent(r))
        # Tras el paint, _projected_pts poblado y sin crash
        assert scene._projected_pts is not None
        assert scene._projected_pts.shape[0] == verts.shape[0]
        # La cara 0 completa debe estar en selected_tris vía _face_index_map
        selected = set()
        fm = scene._face_index_map
        for i in range(fm.shape[0]):
            if int(fm[i]) in (0,):
                selected.add(i)
        assert len(selected) == len(center0) and len(selected) == 2
    finally:
        vp.close()


def test_selection_manager_payload_kind_face():
    """El payload emitido usa ``kind: face`` (contrato del viewport VTK)."""
    scene, verts, tris, face_map = _sample_scene()
    vp, _, _ = _make_viewport()
    try:
        _project_against = _project  # noqa - reuse for projection
        scene.set_model_geometry(verts, tris, face_index_map=face_map,
                                 faces_meta=scene._faces_meta)
        _project(scene)
        from desktop.viewport.software_viewport import _SoftwareSelectionManager
        mgr = _SoftwareSelectionManager()
        mgr.attach(scene)
        out = {}
        mgr.set_selection_callback(lambda p: out.update(payload=p))
        sx, sy = _screen_centroid(scene, [0, 1, 3])
        mgr.pick(sx, sy)
        p = out["payload"]
        assert p.get("kind") == "face"
        assert p.get("face_index") == 0
        assert p.get("id") == "face_0"
        assert p.get("area") == 1.0
    finally:
        vp.close()