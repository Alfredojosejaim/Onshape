"""Regression guards for the Viewport3D public contract used by the UI.

The crash ``'Viewport3D' object has no attribute 'selection_manager'`` happened
because the UI layer references ``viewport.selection_manager`` while the
viewport stored it as ``viewport.selection``.  These tests pin the contract so
that breakage is caught at import/collection time (no GL context required).
"""

import inspect

from vtkmodules.vtkRenderingCore import vtkRenderer

from desktop.viewport.viewport_3d import Viewport3D
from desktop.viewport.selection import SelectionManager


def test_selection_manager_property_defined_on_viewport():
    # The public accessor used throughout desktop/ui must exist on the class,
    # regardless of whether we can instantiate a GL window headless.
    assert isinstance(inspect.getattr_static(Viewport3D, "selection_manager", None), property), (
        "Viewport3D must expose a 'selection_manager' property"
    )


def test_selection_manager_ui_contract():
    """The SelectionManager methods the UI consumes must exist."""
    sm = SelectionManager(vtkRenderer())
    for name in ("set_solid_resolver", "pick", "clear_multi", "selection_set", "last_payload"):
        assert hasattr(sm, name), f"SelectionManager missing '{name}'"
    # multi_selection is a property returning a list-ish; ensure it is accessible
    assert isinstance(inspect.getattr_static(SelectionManager, "multi_selection", None), property), (
        "SelectionManager must expose 'multi_selection'"
    )


def test_ui_uses_only_available_contract():
    """Static scan: desktop/ui must reference the selection via the viewport
    alias and only call methods that exist on SelectionManager."""
    src = open("desktop/ui/main_window.py", encoding="utf-8").read()

    # The UI must go through the 'selection_manager' alias (the thing that
    # was missing and caused the crash).
    assert "viewport.selection_manager" in src, "UI must use viewport.selection_manager"
    assert "sel = self.viewport.selection_manager" in src
    assert "viewport.selection_manager.set_solid_resolver(" in src

    # And the methods it calls on the surfaced object must exist on
    # SelectionManager (covered by test_selection_manager_ui_contract too).
    assert "sel.multi_selection" in src
    assert "sel.last_payload" in src


def test_highlight_overlay_is_offset_off_the_surface():
    """The face-selection overlay must not z-fight the opaque mesh.

    ``highlight_faces`` builds a gold overlay on the *same* triangles as the
    model, which is exactly coplanar and would fail the depth test (the reason
    planar faces were invisible and curved faces only partially highlighted).
    ``_offset_overlay`` must lift the overlay vertices off the surface.
    """
    import numpy as np
    from desktop.viewport.scene import Scene

    # Planar quad on z=0 (2 triangles). Outward normal +z.
    verts = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=float,
    )
    tris = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)

    overlay_verts, overlay_tris = Scene._offset_overlay(verts, tris)

    # Triangle indices are preserved (same layout/order).
    assert np.array_equal(overlay_tris, tris)
    # The overlay must be lifted in +z (moved toward the viewer / off the face).
    assert np.all(overlay_verts[:, 2] > 0.0), "overlay must lift off the planar face"
    # Only the involved vertices move; the offset is tiny (proportional to bbox).
    assert np.allclose(overlay_verts[:, 2], 0.001, atol=1e-6)


def test_highlight_overlay_offset_preserves_remaining_vertices():
    """Vertices not referenced by the selected triangles must stay untouched."""
    import numpy as np
    from desktop.viewport.scene import Scene

    verts = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0],
         [0.0, 1.0, 0.0], [5.0, 5.0, 5.0]],  # unreferenced far vertex
        dtype=float,
    )
    tris = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)

    overlay_verts, _ = Scene._offset_overlay(verts, tris)
    # Vertex 4 (index 4) is not in any triangle, so it must be unchanged.
    assert np.array_equal(overlay_verts[4], verts[4])
