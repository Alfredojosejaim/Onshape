"""CAD Entity selection model.

This module defines how CAD entities (solids, faces, edges, vertices) are
represented as selection references, independent of the VTK viewport.

A CadEntityRef contains enough stable information to identify a CAD entity
regardless of how the viewport renders it.  The viewport *translates* a
VTK pick into a CadEntityRef; the rest of the system works only with
CadEntityRef objects.

Entity types:

- ``solid``   -- a 3D solid body (identified by model_id + solid_id or index)
- ``face``    -- a B-Rep face (identified by face_index within a solid)
- ``edge``    -- a B-Rep edge (identified by edge_index within a solid)
- ``vertex``  -- a B-Rep vertex (identified by vertex coordinates or index)

A SelectionSet groups multiple CadEntityRefs and supports composition
(union, intersection, difference) for defining regions of interest.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EntityType(str, Enum):
    SOLID = "solid"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"


class SelectionMode(str, Enum):
    SINGLE = "single"
    MULTI = "multi"


@dataclass(eq=False)
class CadEntityRef:
    """Stable reference to a CAD entity.

    Unlike the viewport payload (which carries VTK actor pointers), a
    CadEntityRef is serialisable and survives model reloads as long as
    the topology does not change.
    """
    entity_type: EntityType
    model_id: Optional[str] = None
    solid_id: Optional[str] = None
    face_index: Optional[int] = None
    edge_index: Optional[int] = None
    vertex_index: Optional[int] = None
    coordinates: Optional[Tuple[float, float, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        if self.entity_type == EntityType.SOLID:
            return f"Solid {self.solid_id or '?'}"
        if self.entity_type == EntityType.FACE:
            return f"Face {self.face_index if self.face_index is not None else '?'}"
        if self.entity_type == EntityType.EDGE:
            return f"Edge {self.edge_index if self.edge_index is not None else '?'}"
        if self.entity_type == EntityType.VERTEX:
            return f"Vertex {self.vertex_index if self.vertex_index is not None else '?'}"
        return "Unknown"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"entity_type": self.entity_type.value}
        if self.model_id:
            d["model_id"] = self.model_id
        if self.solid_id:
            d["solid_id"] = self.solid_id
        if self.face_index is not None:
            d["face_index"] = self.face_index
        if self.edge_index is not None:
            d["edge_index"] = self.edge_index
        if self.vertex_index is not None:
            d["vertex_index"] = self.vertex_index
        if self.coordinates:
            d["coordinates"] = list(self.coordinates)
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CadEntityRef":
        coords = d.get("coordinates")
        return cls(
            entity_type=EntityType(d["entity_type"]),
            model_id=d.get("model_id"),
            solid_id=d.get("solid_id"),
            face_index=d.get("face_index"),
            edge_index=d.get("edge_index"),
            vertex_index=d.get("vertex_index"),
            coordinates=tuple(coords) if coords else None,
            metadata=d.get("metadata", {}),
        )

    @classmethod
    def from_face(cls, face_index: int, model_id: Optional[str] = None,
                  **meta: Any) -> "CadEntityRef":
        return cls(
            entity_type=EntityType.FACE,
            model_id=model_id,
            face_index=face_index,
            metadata=meta,
        )

    @classmethod
    def from_solid(cls, solid_id: str, model_id: Optional[str] = None,
                   **meta: Any) -> "CadEntityRef":
        return cls(
            entity_type=EntityType.SOLID,
            model_id=model_id,
            solid_id=solid_id,
            metadata=meta,
        )

    def _identity(self):
        return (
            self.entity_type.value if isinstance(self.entity_type, EntityType) else str(self.entity_type),
            self.model_id,
            self.solid_id,
            self.face_index,
            self.edge_index,
            self.vertex_index,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CadEntityRef):
            return NotImplemented
        return self._identity() == other._identity()

    def __hash__(self) -> int:
        return hash(self._identity())

    def __repr__(self) -> str:
        return f"CadEntityRef({self.entity_type.value}: {self.display_name})"


@dataclass
class SelectionSet:
    """A group of CAD entity references.

    Used by commands and studies to describe which entities are involved
    in an operation (e.g. which faces receive a load, which solids participate
    in a boolean).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    entities: List[CadEntityRef] = field(default_factory=list)
    mode: SelectionMode = SelectionMode.MULTI

    def add(self, entity: CadEntityRef) -> None:
        self.entities.append(entity)

    def remove(self, index: int) -> bool:
        if 0 <= index < len(self.entities):
            self.entities.pop(index)
            return True
        return False

    def clear(self) -> None:
        self.entities.clear()

    @property
    def is_empty(self) -> bool:
        return len(self.entities) == 0

    @property
    def count(self) -> int:
        return len(self.entities)

    @property
    def primary(self) -> Optional[CadEntityRef]:
        """Return the first entity (useful when mode is SINGLE)."""
        return self.entities[0] if self.entities else None

    def filter_by_type(self, entity_type: EntityType) -> List[CadEntityRef]:
        return [e for e in self.entities if e.entity_type == entity_type]

    @property
    def solids(self) -> List[CadEntityRef]:
        return self.filter_by_type(EntityType.SOLID)

    @property
    def faces(self) -> List[CadEntityRef]:
        return self.filter_by_type(EntityType.FACE)

    @property
    def edges(self) -> List[CadEntityRef]:
        return self.filter_by_type(EntityType.EDGE)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entities": [e.to_dict() for e in self.entities],
            "mode": self.mode.value,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SelectionSet":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", ""),
            entities=[CadEntityRef.from_dict(e) for e in d.get("entities", [])],
            mode=SelectionMode(d.get("mode", "multi")),
        )

    def __repr__(self) -> str:
        return f"SelectionSet(name={self.name!r}, count={len(self.entities)})"
