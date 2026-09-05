"""Selection - mouse picking and visual identification of selected entities.

The selection system is deliberately extensible: it distinguishes whole
renderable objects (model / mesh / density / force / constraint) AND geometric
entities (CAD faces) by mapping the picked render data back to the underlying
CAD topology through the scene's per-triangle face index (from a per-face
tessellation).

``pick`` returns (and every callback emits) a JSON-ish payload dict or ``None``:

    * ``{"key": "...", "kind": "actor", "actor": <vtkActor>}``       whole object
    * ``{"key": "...", "kind": "face", "face_index": N, "center": [..],
         "normal": [..], "area": .., "cad_entity": <CadEntityRef>}`` CAD face

Architecture integration (Phase 1):
    When a face is picked, the payload now includes a ``cad_entity`` key
    holding a ``CadEntityRef`` object.  This gives the rest of the system a
    stable, serialisable reference to the CAD entity that is independent of
    the VTK viewport.  The existing ``kind``/``face_index`` keys are
    preserved for backward compatibility.

    Multi-entity selection: clicking (with or without Ctrl) toggles the
    picked entity in the current selection set (accumulative click-select).
    The callback receives the last picked payload dict via
    ``selectionChanged``; the full set is available via ``multi_selection``.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from vtkmodules.vtkRenderingCore import vtkCellPicker, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors

from core.cad_entity import CadEntityRef, EntityType, SelectionSet

#: VTK cell-picker tolerance in pixels. 0.005 proved too strict for small /
#: curved faces (sub-pixel triangles never picked); 0.025 matches the VTK
#: default behaviour and keeps neighbour-face mis-picks low.
PICK_TOLERANCE = 0.025


class SelectionManager:
    def __init__(self, renderer) -> None:
        self._renderer = renderer  # vtkRenderer
        self._picker = vtkCellPicker()
        self._picker.SetTolerance(PICK_TOLERANCE)
        self._picked_actor: Optional[vtkActor] = None
        self._picked_key: Optional[str] = None
        self._last_payload: Optional[Dict[str, Any]] = None
        self._identification: Optional[vtkActor] = None
        self._on_selection: Callable[[Optional[Dict[str, Any]]], None] | None = None
        self._scene = None

        # Optional body-level resolver: ``callable(model_id, face_index) -> 
        # Optional[Dict]`` returning ``{"solid_id", "index"}`` so a picked face
        # can be promoted to its parent solid for body-level selection.
        self._solid_resolver: Optional[Callable[[Optional[str], int], Optional[Dict[str, Any]]]] = None

        # Multi-entity selection state
        self._multi_selection: List[Dict[str, Any]] = []
        self._multi_identifications: List[vtkActor] = []

    def attach(self, scene) -> None:
        self._scene = scene

    def set_selection_callback(self, cb: Callable[[Optional[Dict[str, Any]]], None]) -> None:
        self._on_selection = cb

    def set_solid_resolver(self, resolver: Optional[Callable[[Optional[str], int], Optional[Dict[str, Any]]]]) -> None:
        """Register an optional callable to promote a picked face to its solid."""
        self._solid_resolver = resolver

    def pick(self, display_x: int, display_y: int, ctrl: bool = False) -> Optional[Dict[str, Any]]:
        """Convert a Qt display coordinate to a VTK world pick and update state.

        Plain click accumulates (toggle): clicking an unselected face adds
        it, clicking it again removes it. ``ctrl`` is kept for backward
        compatibility and behaves identically.
        """
        x = float(display_x)
        y_win = self._renderer.GetSize()[1] - float(display_y)
        picked = self._picker.Pick(x, y_win, 0.0, self._renderer)
        if not picked:
            if not ctrl:
                self.clear()
                self.clear_multi()
            return None

        actor = self._picker.GetActor()
        if actor is None or self._scene is None:
            if not ctrl:
                self.clear()
                self.clear_multi()
            return None

        key = self._actor_to_key(actor)
        payload = {"key": key, "kind": "actor", "actor": actor}

        # Entity-level resolution: when the picked actor is the CAD model and the
        # scene holds a per-triangle face index, attribute the picked triangle to
        # a B-Rep face.
        if key is not None and self._scene._model_actor_key == key:
            cell_id = self._picker.GetCellId()
            if cell_id is None or int(cell_id) < 0:
                # No valid triangle hit (e.g. edge/gap between triangles):
                # keep previous selection instead of silently failing.
                return self._last_payload
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
                # Architecture layer: stable CAD entity reference
                payload["cad_entity"] = CadEntityRef.from_face(
                    face_index=face_index,
                    model_id=key,
                    center=meta.get("center") if meta else None,
                    normal=meta.get("normal") if meta else None,
                    area=meta.get("area") if meta else None,
                )
                # Body-level promotion: resolve the parent solid so the
                # selection can refer to a whole body (Fase 2).
                if self._solid_resolver is not None:
                    solid = self._solid_resolver(key, face_index)
                    if solid:
                        payload["solid_entity"] = CadEntityRef.from_solid(
                            solid_id=solid.get("solid_id", "solid_0"),
                            model_id=key,
                            index=solid.get("index"),
                        )

        # Plain click accumulates via toggle (P0 requirement); Ctrl keeps
        # legacy behaviour (identical toggle) for backward compatibility.
        self._toggle_multi(payload)
        return self._last_payload

    # ------------------------------------------------------------------ #
    # Multi-entity selection
    # ------------------------------------------------------------------ #
    def _toggle_multi(self, payload: Dict[str, Any]) -> None:
        """Add or remove an entity from the multi-selection set."""
        identifier = self._selection_key(payload)
        existing_idx = None
        for i, sel in enumerate(self._multi_selection):
            if self._selection_key(sel) == identifier:
                existing_idx = i
                break

        if existing_idx is not None:
            # Remove from selection
            self._multi_selection.pop(existing_idx)
            self._rebuild_multi_highlights()
            self._last_payload = self._multi_selection[-1] if self._multi_selection else None
        else:
            # Add to selection; the visual highlight must mirror the FULL
            # accumulative set (highlight_faces clears first, so passing
            # only the new face would un-highlight the previous ones).
            self._multi_selection.append(payload)
            if payload.get("kind") == "face" and self._scene is not None:
                self._scene.highlight_faces([
                    s["face_index"] for s in self._multi_selection
                    if s.get("kind") == "face"
                ])
            elif payload.get("actor") is not None:
                self._build_identification(payload["actor"])
            self._last_payload = payload
        if self._on_selection:
            # Emit the last-picked payload as a dict (MainWindow /
            # Properties expect ``payload.get(...)``) enriched with the
            # COMPLETE current selection under ``"selection"`` so the
            # callback alone carries the full state (P0 §4/§6). Extra
            # keys are ignored by existing consumers.
            if self._multi_selection:
                last = self._multi_selection[-1]
                emitted = {k: v for k, v in last.items() if k != "actor"}
                emitted["selection"] = [
                    {k: v for k, v in s.items() if k != "actor"}
                    for s in self._multi_selection
                ]
                emitted["selection_count"] = len(self._multi_selection)
                self._on_selection(emitted)
            else:
                self._on_selection(None)

    @staticmethod
    def _selection_key(payload: Dict[str, Any]) -> str:
        """Return a hashable key for de-duplicating multi-selection."""
        if payload.get("kind") == "face":
            return f"face:{payload.get('face_index')}:{payload.get('key')}"
        return f"actor:{payload.get('key')}"

    def _rebuild_multi_highlights(self) -> None:
        """Remove all current highlight actors and re-add for the remaining selection."""
        # Remove old identifications
        for actor in self._multi_identifications:
            self._renderer.RemoveActor(actor)
        self._multi_identifications.clear()
        if self._scene is not None:
            self._scene.clear_highlight()
        # Re-add highlights for remaining selection
        face_indices = []
        for sel in self._multi_selection:
            if sel.get("kind") == "face":
                face_indices.append(sel["face_index"])
            elif sel.get("actor") is not None:
                self._build_identification(sel["actor"])
        if face_indices and self._scene is not None:
            self._scene.highlight_faces(face_indices)
        self._renderer.Render()

    @property
    def multi_selection(self) -> List[Dict[str, Any]]:
        """Return the current multi-entity selection (without actor refs)."""
        return [{k: v for k, v in s.items() if k != "actor"} for s in self._multi_selection]

    @property
    def selection_set(self) -> SelectionSet:
        """Return the current selection as a core SelectionSet."""
        ss = SelectionSet(name="Viewport Selection")
        for sel in self._multi_selection:
            ce = sel.get("cad_entity")
            if ce is not None:
                ss.add(ce)
        return ss

    def clear_multi(self) -> None:
        """Clear the multi-entity selection set."""
        for actor in self._multi_identifications:
            self._renderer.RemoveActor(actor)
        self._multi_identifications.clear()
        self._multi_selection.clear()

    # ------------------------------------------------------------------ #
    # Single-entity selection (backward compatible)
    # ------------------------------------------------------------------ #
    def _actor_to_key(self, actor: vtkActor) -> Optional[str]:
        for key, scene_actor in (self._scene._actors.items() if hasattr(self._scene, "_actors") else []):
            if scene_actor is actor:
                return key
        return None

    def set_selected(self, payload: Optional[Dict[str, Any]]) -> None:
        self.clear(notify=False)
        self.clear_multi()
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
        self._multi_identifications.append(outline)
        self._renderer.Render()

    def clear(self, notify: bool = True) -> None:
        if self._identification is not None:
            self._renderer.RemoveActor(self._identification)
            self._identification = None
        # Full clear: single highlight + accumulative multi set.
        for actor in self._multi_identifications:
            try:
                self._renderer.RemoveActor(actor)
            except Exception:
                pass
        self._multi_identifications.clear()
        self._multi_selection.clear()
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
