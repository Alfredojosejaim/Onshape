"""Selection - mouse picking and visual identification of selected entities.

The selection system is deliberately extensible: today it distinguishes whole
renderable objects (model / mesh / density / force / constraint), but the
architecture is prepared to later differentiate geometric entities such as
solids, faces, edges and vertices by mapping the picked render data back to the
underlying CAD topology.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from vtkmodules.vtkRenderingCore import vtkCellPicker, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors


class SelectionManager:
    def __init__(self, renderer) -> None:
        self._renderer = renderer  # vtkRenderer
        self._picker = vtkCellPicker()
        self._picker.SetTolerance(0.005)
        self._picked_actor: Optional[vtkActor] = None
        self._picked_key: Optional[str] = None
        self._identification: Optional[vtkActor] = None
        self._on_selection: Callable[[Optional[str]], None] | None = None
        self._scene = None

    def attach(self, scene) -> None:
        self._scene = scene

    def set_selection_callback(self, cb: Callable[[Optional[str]], None]) -> None:
        self._on_selection = cb

    def pick(self, display_x: int, display_y: int) -> Optional[str]:
        """Convert a Qt display coordinate to a VTK world pick and update state."""
        x = float(display_x)
        y_win = self._renderer.GetSize()[1] - float(display_y)
        picked = self._picker.Pick(x, y_win, 0.0, self._renderer)
        if not picked:
            self.clear()
            return None

        actor = self._picker.GetActor()
        if actor is None or self._scene is None:
            self.clear()
            return None

        key = self._actor_to_key(actor)
        self.set_selected(key, actor)
        return key

    def _actor_to_key(self, actor: vtkActor) -> Optional[str]:
        for key, scene_actor in (self._scene._actors.items() if hasattr(self._scene, "_actors") else []):
            if scene_actor is actor:
                return key
        return None

    def set_selected(self, key: Optional[str], actor: Optional[vtkActor] = None) -> None:
        self.clear(notify=False)
        if key is None or actor is None:
            self._picked_key = None
            self._picked_actor = None
            if self._on_selection:
                self._on_selection(None)
            return
        self._picked_key = key
        self._picked_actor = actor
        self._build_identification(actor)
        if self._on_selection:
            self._on_selection(key)

    def _build_identification(self, actor: vtkActor) -> None:
        """Highlight the selected actor by drawing its oriented bounds box."""
        from vtkmodules.vtkFiltersSources import vtkCubeSource
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper

        box = vtkCubeSource()
        box.SetBounds(actor.GetBounds())
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(box.GetOutputPort())
        outline = vtkActor()
        outline.SetMapper(mapper)
        colors = vtkNamedColors()
        outline.GetProperty().SetColor(colors.GetColor3d("Gold"))
        outline.GetProperty().SetEdgeVisibility(True)
        outline.GetProperty().SetLineWidth(3)
        outline.GetProperty().SetRepresentationToWireframe()
        self._renderer.AddActor(outline)
        self._identification = outline
        self._renderer.Render()

    def clear(self, notify: bool = True) -> None:
        if self._identification is not None:
            self._renderer.RemoveActor(self._identification)
            self._identification = None
        self._picked_actor = None
        self._picked_key = None
        if notify and self._on_selection:
            self._on_selection(None)
        self._renderer.Render()

    @property
    def selected_key(self) -> Optional[str]:
        return self._picked_key
