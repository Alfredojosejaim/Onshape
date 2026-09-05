"""Selection - mouse picking and visual identification of selected entities.

Pipeline (prompts.md): Qt mouse event -> Viewport3D -> vtkCellPicker ->
CellId -> scene.face_index_for_cell() -> CadEntityRef.from_face() ->
SelectionManager.handle_pick() -> selectionChanged -> highlight/ConditionPanel.

El estado logico (Set[CadEntityRef]) vive en SelectionManager sin logica de
Qt ni VTK. El picking (evento) lo inicia Viewport3D y el render (highlight
por celda via HighlightRenderer/Scene) solo reacciona a selectionChanged.
Se mantiene compatibilidad legacy (pick/toggle/multi_selection/callback dict)
para la UI y los tests existentes.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set

from PySide6.QtCore import QObject, Signal

from vtkmodules.vtkRenderingCore import vtkCellPicker, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors

from core.cad_entity import CadEntityRef, EntityType, SelectionSet

#: Tolerancia del vtkCellPicker (fraccion del bbox de escena). El default VTK
#: (0.025) es demasiado permisivo en fillets/caras coplanares o tangentes
#: cerca de aristas compartidas: el rayo intersecta ambas caras casi al mismo
#: t y devuelve la vecina. prompts.md §2 fija 0.0005 (resuelve ~90% de casos).
PICK_TOLERANCE = 0.0005


class SelectionManager(QObject):
    """Estado puro de seleccion: Set[CadEntityRef] + compat legacy."""

    selectionChanged = Signal(object)  # emite frozenset(Set[CadEntityRef])

    def __init__(self, renderer=None, parent=None) -> None:
        super().__init__(parent)
        self._renderer = renderer  # vtkRenderer (puede ser None/fake en tests)
        self._picker = vtkCellPicker()
        self._picker.SetTolerance(PICK_TOLERANCE)
        self._picked_actor: Optional[vtkActor] = None
        self._picked_key: Optional[str] = None
        self._last_payload: Optional[Dict[str, Any]] = None
        self._identification: Optional[vtkActor] = None
        self._on_selection: Callable[[Optional[Dict[str, Any]]], None] | None = None
        self._scene = None

        self._solid_resolver: Optional[Callable[[Optional[str], int], Optional[Dict[str, Any]]]] = None

        # Estado logico nuevo (prompts.md §1): Set, nunca variable singular.
        self._selected: Set[CadEntityRef] = set()

        # Estado legacy (payloads dict con actor refs) derivado del Set.
        self._multi_selection: List[Dict[str, Any]] = []
        self._multi_identifications: List[vtkActor] = []

    # ------------------------------------------------------------------ #
    # Nuevo nucleo (prompts.md §1)
    # ------------------------------------------------------------------ #
    @property
    def selected(self) -> frozenset:
        return frozenset(self._selected)

    def handle_pick(self, entity: Optional[CadEntityRef], additive: bool) -> None:
        """Actualiza el Set segun semantica Onshape y emite selectionChanged.

        - entity None + no additive: limpia.
        - click vacio con additive (Shift): no hace nada.
        - additive: toggle ON/OFF.
        - no additive: reemplaza (no-op si ya es exactamente {entity}).
        """
        if entity is None:
            if not additive:
                if self._selected:
                    self._selected.clear()
                    self._sync_legacy_after_set_change()
                    self.selectionChanged.emit(self.selected)
                    self._emit_legacy()
                else:
                    self._emit_legacy()
            return  # click vacio con Shift no hace nada (Onshape)

        if additive:
            if entity in self._selected:
                self._selected.remove(entity)
            else:
                self._selected.add(entity)
        else:
            if self._selected == {entity}:
                return  # no-op, evita reflow innecesario
            self._selected = {entity}

        self._sync_legacy_after_set_change(entity)
        self.selectionChanged.emit(self.selected)
        self._emit_legacy()

    def clear(self, notify: bool = True) -> None:
        if self._identification is not None and self._renderer is not None:
            try:
                self._renderer.RemoveActor(self._identification)
            except Exception:
                pass
            self._identification = None
        for actor in self._multi_identifications:
            try:
                if self._renderer is not None:
                    self._renderer.RemoveActor(actor)
            except Exception:
                pass
        self._multi_identifications.clear()
        self._multi_selection.clear()
        had = bool(self._selected)
        self._selected.clear()
        if self._scene is not None:
            try:
                self._scene.clear_highlight()
            except Exception:
                pass
        self._picked_actor = None
        self._picked_key = None
        self._last_payload = None
        if notify:
            if had:
                try:
                    self.selectionChanged.emit(self.selected)
                except Exception:
                    pass
            if self._on_selection:
                self._on_selection(None)
        if self._renderer is not None:
            try:
                self._renderer.Render()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Wiring
    # ------------------------------------------------------------------ #
    def attach(self, scene) -> None:
        self._scene = scene
        # Conectar highlight por celda al cambio logico (prompts.md §3/§4.6).
        try:
            self.selectionChanged.connect(self._on_logical_selection_changed)
        except Exception:
            pass

    def set_selection_callback(self, cb: Callable[[Optional[Dict[str, Any]]], None]) -> None:
        self._on_selection = cb

    def set_solid_resolver(self, resolver) -> None:
        self._solid_resolver = resolver

    def _on_logical_selection_changed(self, selected) -> None:
        """Traduce Set[CadEntityRef] -> Set[cell_id] y actualiza highlight."""
        try:
            faces = [e.face_index for e in (selected or set())
                     if getattr(e, "entity_type", None) == EntityType.FACE
                     and getattr(e, "face_index", None) is not None]
            if self._scene is not None and faces:
                self._scene.highlight_faces([int(f) for f in faces])
            elif self._scene is not None:
                self._scene.clear_highlight()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Picking legacy (CellId -> face -> entity -> handle_pick)
    # ------------------------------------------------------------------ #
    def pick(self, display_x: int, display_y: int, ctrl: bool = False) -> Optional[Dict[str, Any]]:
        """Convert a Qt display coordinate to a VTK world pick and update state.

        Plain click acumula (toggle). ``ctrl`` se mantiene por compatibilidad
        y comporta identico toggle.
        """
        if self._renderer is None or self._picker is None:
            return self._last_payload
        x = float(display_x)
        try:
            y_win = self._renderer.GetSize()[1] - float(display_y)
        except Exception:
            y_win = float(display_y)
        try:
            picked = self._picker.Pick(x, y_win, 0.0, self._renderer)
        except Exception:
            picked = False
        if not picked:
            # Click al vacio: additive (Shift/Ctrl) no limpia (Onshape).
            if not ctrl:
                self.handle_pick(None, additive=False)
            return None

        actor = self._picker.GetActor()
        if actor is None or self._scene is None:
            if not ctrl:
                self.handle_pick(None, additive=False)
            return None

        key = self._actor_to_key(actor)
        payload = {"key": key, "kind": "actor", "actor": actor}

        if key is not None and getattr(self._scene, "_model_actor_key", None) == key:
            cell_id = self._picker.GetCellId()
            if cell_id is None or int(cell_id) < 0:
                return self._last_payload
            face_index = self._scene.face_index_for_cell(int(cell_id))
            if face_index is not None:
                self._enrich_face_payload(payload, key, int(face_index))

        self._toggle_multi(payload)
        return self._last_payload

    def _enrich_face_payload(self, payload: Dict[str, Any], key: str, face_index: int) -> None:
        try:
            meta = self._scene.face_meta(face_index)
        except Exception:
            meta = None
        payload.update({"kind": "face", "face_index": face_index})
        if meta:
            payload.update({
                "id": meta.get("id", f"face_{face_index}"),
                "center": meta.get("center", []),
                "normal": meta.get("normal", []),
                "area": meta.get("area", 0.0),
            })
        payload["cad_entity"] = CadEntityRef.from_face(
            face_index=face_index,
            model_id=key,
            center=(meta.get("center") if meta else None),
            normal=(meta.get("normal") if meta else None),
            area=(meta.get("area") if meta else None),
        )
        if self._solid_resolver is not None:
            try:
                solid = self._solid_resolver(key, face_index)
            except Exception:
                solid = None
            if solid:
                payload["solid_entity"] = CadEntityRef.from_solid(
                    solid_id=solid.get("solid_id", "solid_0"),
                    model_id=key,
                    index=solid.get("index"),
                )

    # ------------------------------------------------------------------ #
    # Multi-entity selection (derivado del Set, compat con tests/UI)
    # ------------------------------------------------------------------ #
    def _toggle_multi(self, payload: Dict[str, Any]) -> None:
        identifier = self._selection_key(payload)
        existing_idx = None
        for i, sel in enumerate(self._multi_selection):
            if self._selection_key(sel) == identifier:
                existing_idx = i
                break

        entity = payload.get("cad_entity")
        if existing_idx is not None:
            self._multi_selection.pop(existing_idx)
            if entity is not None and entity in self._selected:
                self._selected.remove(entity)
            self._rebuild_multi_highlights()
            self._last_payload = self._multi_selection[-1] if self._multi_selection else None
        else:
            self._multi_selection.append(payload)
            if entity is not None:
                self._selected.add(entity)
            if payload.get("kind") == "face" and self._scene is not None:
                try:
                    self._scene.highlight_faces([
                        s["face_index"] for s in self._multi_selection
                        if s.get("kind") == "face"
                    ])
                except Exception:
                    pass
            elif payload.get("actor") is not None:
                try:
                    self._build_identification(payload["actor"])
                except Exception:
                    pass
            self._last_payload = payload
        try:
            self.selectionChanged.emit(self.selected)
        except Exception:
            pass
        self._emit_legacy()

    def _emit_legacy(self) -> None:
        if not self._on_selection:
            return
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

    def _sync_legacy_after_set_change(self, last_entity=None) -> None:
        """Reconstruye _multi_selection desde _selected (usado por handle_pick)."""
        if not self._selected:
            self._multi_selection.clear()
            self._last_payload = None
            if self._scene is not None:
                try:
                    self._scene.clear_highlight()
                except Exception:
                    pass
            return
        # Mantener payloads existentes que sigan seleccionados; sintetizar los
        # que vengan solo como CadEntityRef (p. ej. desde Viewport3D).
        keep = []
        selected_entities = set(self._selected)
        for sel in self._multi_selection:
            ce = sel.get("cad_entity")
            if ce is not None and ce in selected_entities:
                keep.append(sel)
                selected_entities.discard(ce)
        for entity in selected_entities:
            keep.append(self._payload_for_entity(entity))
        # Orden determinista por face_index para highlight estable.
        def _sort_key(p):
            return (p.get("face_index", 10**9), str(p.get("key", "")))
        keep.sort(key=_sort_key)
        self._multi_selection = keep
        self._last_payload = keep[-1] if keep else None
        if self._scene is not None:
            faces = [s["face_index"] for s in keep if s.get("kind") == "face"]
            try:
                if faces:
                    self._scene.highlight_faces(faces)
                else:
                    self._scene.clear_highlight()
            except Exception:
                pass

    def _payload_for_entity(self, entity: CadEntityRef) -> Dict[str, Any]:
        key = getattr(entity, "model_id", None)
        if getattr(entity, "entity_type", None) == EntityType.FACE:
            fi = int(entity.face_index)
            payload: Dict[str, Any] = {
                "key": key, "kind": "face", "face_index": fi,
                "cad_entity": entity,
            }
            try:
                meta = self._scene.face_meta(fi) if self._scene else None
            except Exception:
                meta = None
            if meta:
                payload.update({
                    "id": meta.get("id", f"face_{fi}"),
                    "center": meta.get("center", []),
                    "normal": meta.get("normal", []),
                    "area": meta.get("area", 0.0),
                })
            if self._solid_resolver is not None and key is not None:
                try:
                    solid = self._solid_resolver(key, fi)
                except Exception:
                    solid = None
                if solid:
                    payload["solid_entity"] = CadEntityRef.from_solid(
                        solid_id=solid.get("solid_id", "solid_0"),
                        model_id=key, index=solid.get("index"))
            return payload
        return {"key": key, "kind": "actor", "actor": None, "cad_entity": entity}

    @staticmethod
    def _selection_key(payload: Dict[str, Any]) -> str:
        if payload.get("kind") == "face":
            return f"face:{payload.get('face_index')}:{payload.get('key')}"
        return f"actor:{payload.get('key')}"

    def _rebuild_multi_highlights(self) -> None:
        if self._renderer is not None:
            for actor in self._multi_identifications:
                try:
                    self._renderer.RemoveActor(actor)
                except Exception:
                    pass
        self._multi_identifications.clear()
        if self._scene is not None:
            try:
                self._scene.clear_highlight()
            except Exception:
                pass
        face_indices = []
        for sel in self._multi_selection:
            if sel.get("kind") == "face":
                face_indices.append(sel["face_index"])
            elif sel.get("actor") is not None and self._renderer is not None:
                try:
                    self._build_identification(sel["actor"])
                except Exception:
                    pass
        if face_indices and self._scene is not None:
            try:
                self._scene.highlight_faces(face_indices)
            except Exception:
                pass
        if self._renderer is not None:
            try:
                self._renderer.Render()
            except Exception:
                pass

    @property
    def multi_selection(self) -> List[Dict[str, Any]]:
        return [{k: v for k, v in s.items() if k != "actor"} for s in self._multi_selection]

    @property
    def selection_set(self) -> SelectionSet:
        ss = SelectionSet(name="Viewport Selection")
        for e in self._selected:
            ss.add(e)
        for sel in self._multi_selection:
            ce = sel.get("cad_entity")
            if ce is not None and ce not in self._selected:
                ss.add(ce)
        return ss

    def clear_multi(self) -> None:
        self.clear(notify=False)
        if self._on_selection:
            self._on_selection(None)

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
            try:
                self._scene.highlight_faces([payload["face_index"]])
            except Exception:
                pass
        elif actor is not None and self._renderer is not None:
            try:
                self._build_identification(actor)
            except Exception:
                pass
        if self._on_selection:
            self._on_selection({k: v for k, v in payload.items() if k != "actor"})

    def _build_identification(self, actor: vtkActor) -> None:
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
        if self._renderer is not None:
            self._renderer.AddActor(outline)
        self._identification = outline
        self._multi_identifications.append(outline)
        if self._renderer is not None:
            try:
                self._renderer.Render()
            except Exception:
                pass

    @property
    def selected_key(self) -> Optional[str]:
        return self._picked_key

    @property
    def last_payload(self) -> Optional[Dict[str, Any]]:
        return self._last_payload
