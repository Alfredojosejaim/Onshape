"""Selection - mouse picking and visual identification of selected entities.

The selection system is deliberately extensible: it distinguishes whole
renderable objects (model / mesh / density / force / constraint) AND geometric
entities (CAD faces) by mapping the picked render data back to the underlying
CAD topology through the scene's per-triangle face index (from a per-face
tessellation).

``pick`` returns (and every callback emits) a JSON-ish payload dict or ``None``:

    * ``{"key": "...", "kind": "actor", "actor": <vtkActor>}``       whole object
    * ``{"key": "...", "kind": "face", "face_index": N, "center": [..],
         "normal": [..], "area": ..}``                              CAD face
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from vtkmodules.vtkRenderingCore import vtkCellPicker, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors


class SelectionManager:
    def __init__(self, renderer) -> None:
        self._renderer = renderer  # vtkRenderer
        self._picker = vtkCellPicker()
        self._picker.SetTolerance(0.005)
        self._picked_actor: Optional[vtkActor] = None
        self._picked_key: Optional[str] = None
        self._last_payload: Optional[Dict[str, Any]] = None
        self._identification: Optional[vtkActor] = None
        self._on_selection: Callable[[Optional[Dict[str, Any]]], None] | None = None
        self._scene = None

    def attach(self, scene) -> None:
        self._scene = scene

    def set_selection_callback(self, cb: Callable[[Optional[Dict[str, Any]]], None]) -> None:
        self._on_selection = cb

    def pick(self, display_x: int, display_y: int) -> Optional[Dict[str, Any]]:
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
        payload = {"key": key, "kind": "actor", "actor": actor}

        # Entity-level resolution: when the picked actor is the CAD model and the
        # scene holds a per-triangle face index, attribute the picked triangle to
        # a B-Rep face.
        if key is not None and self._scene._model_actor_key == key:
            cell_id = self._picker.GetCellId()
            face_index = self._scene.face_index_for_cell(int(cell_id)) if cell_id is not None else None
            if face_index is not None:
                meta = self._scene.face_meta(face_index)
                payload.update({"kind": "face", "face_index": face_index})
                if meta:
                    payload.update({
                        "id": meta.get("id", f"face_{face_index}"),
                        "center": meta.get("center", []),
                        "normal": meta.get("normal", []),
                        "area": meta.get("area", 0.0),
                    })

        self.set_selected(payload)
        return self._last_payload

    def _actor_to_key(self, actor: vtkActor) -> Optional[str]:
        for key, scene_actor in (self._scene._actors.items() if hasattr(self._scene, "_actors") else []):
            if scene_actor is actor:
                return key
        return None

    def set_selected(self, payload: Optional[Dict[str, Any]]) -> None:
        self.clear(notify=False)
        if payload is None:
            self._picked_key = None
            self._picked_actor = None
            self._last_payload = None
            if self._on_selection:
                self._on_selection(None)
            return

        actor = payload.get("actor")
        self._picked_key = payload.get("key")
        self._picked_actor = actor
        self._last_payload = payload

        if payload.get("kind") == "face" and self._scene is not None:
            self._scene.highlight_faces([payload["face_index"]])
        elif actor is not None:
            self._build_identification(actor)
        if self._on_selection:
            self._on_selection({k: v for k, v in payload.items() if k != "actor"})

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
        if self._scene is not None:
            self._scene.clear_highlight()
        self._picked_actor = None
        self._picked_key = None
        self._last_payload = None
        if notify and self._on_selection:
            self._on_selection(None)
        self._renderer.Render()

    @property
    def selected_key(self) -> Optional[str]:
        return self._picked_key

    @property
    def last_payload(self) -> Optional[Dict[str, Any]]:
        return self._last_payload