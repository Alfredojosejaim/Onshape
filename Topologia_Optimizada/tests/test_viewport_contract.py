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
