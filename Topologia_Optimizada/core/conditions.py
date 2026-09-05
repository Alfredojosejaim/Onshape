"""Reusable CAD/CAE conditions.

Conditions are independent, reusable objects that can be created through the
normal ``Command -> Feature -> FeatureHistory`` flow and later *consumed* by an
optimization / generative study:

    Estudio
    └── Optimización estructural
        ├── Pieza(s)
        ├── Carga 1
        ├── Elasticidad 1
        ├── Obstrucción 1
        └── Región protegida 1

An optimization never recreates these conditions internally: it references the
ones previously created by id and resolves them through the
:class:`ConditionManager` (owned by the pipeline controller), so the same
condition object is shared, never duplicated.

Supported condition types:

- ``load``            -- Carga: one or more faces + orientation relative to a
  reference plane (parallel / perpendicular / angle) + direction sense +
  numeric magnitude. An *indeterminate* magnitude is a valid model value.
- ``elasticity``      -- Elasticidad: one or more faces + flex range in mm.
- ``obstruction``     -- Obstrucción: one or more solid bodies + optional
  offset in mm.
- ``protected_region``- Región protegida: one or more faces stored as geometry
  that optimization must not modify.  The model is extensible toward more
  complex protected regions through ``geometry_refs``.

Conditions reuse the existing selection model (``CadEntityRef`` /
``SelectionSet``), so no parallel selection or history system is introduced.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.cad_entity import CadEntityRef, SelectionSet


class ConditionType(str, Enum):
    """Discriminator for the reusable condition kinds."""
    LOAD = "load"
    ELASTICITY = "elasticity"
    OBSTRUCTION = "obstruction"
    PROTECTED_REGION = "protected_region"


class LoadOrientation(str, Enum):
    """Orientation of a load direction relative to a reference plane."""
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    ANGLE = "angle"


class LoadSense(str, Enum):
    """Direction sense of a load."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    INDETERMINATE = "indeterminate"


def _faces_selection(faces: Iterable[CadEntityRef], name: str) -> SelectionSet:
    """Build a multi-entity SelectionSet from a list of face references."""
    sel = SelectionSet(name=name)
    for f in faces:
        sel.add(f)
    return sel


def _solids_selection(bodies: Iterable[CadEntityRef], name: str) -> SelectionSet:
    """Build a multi-entity SelectionSet from a list of solid references."""
    sel = SelectionSet(name=name)
    for b in bodies:
        sel.add(b)
    return sel


@dataclass
class Condition:
    """Base class for all reusable conditions.

    Every condition is fully serialisable (``to_dict`` / ``from_dict``), stores
    its selection using the existing ``SelectionSet`` model, and can be
    registered as a :class:`~core.features.Feature` in the feature history.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Condición"

    @property
    def condition_type(self) -> ConditionType:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def selection(self) -> Optional[SelectionSet]:
        """Return the geometric selection of this condition (if any)."""
        return None


@dataclass
class LoadCondition(Condition):
    """Reusable load condition.

    Configuration stored:
    - one or more selected faces;
    - orientation relative to a reference plane (parallel / perpendicular /
      angle, ``reference_plane_normal``, ``angle_deg``);
    - direction sense (``sense``);
    - numeric magnitude (``magnitude``);
    - the *indeterminate* state as a valid model value (``indeterminate``),
      allowing magnitude to be left unknown until the study is defined.
    """
    faces: SelectionSet = field(default_factory=lambda: SelectionSet(name="Caras de carga"))
    orientation: LoadOrientation = LoadOrientation.PERPENDICULAR
    reference_plane_normal: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    angle_deg: Optional[float] = None
    sense: LoadSense = LoadSense.INDETERMINATE
    magnitude: Optional[float] = None
    indeterminate: bool = True
    unit: str = "N"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.LOAD

    def selection(self) -> Optional[SelectionSet]:
        return self.faces

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.condition_type.value,
            "id": self.id,
            "name": self.name,
            "faces": self.faces.to_dict(),
            "orientation": self.orientation.value,
            "reference_plane_normal": [float(v) for v in self.reference_plane_normal],
            "angle_deg": self.angle_deg,
            "sense": self.sense.value,
            "magnitude": self.magnitude,
            "indeterminate": bool(self.indeterminate),
            "unit": self.unit,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LoadCondition":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Carga"),
            faces=SelectionSet.from_dict(d["faces"]),
            orientation=LoadOrientation(d.get("orientation", LoadOrientation.PERPENDICULAR.value)),
            reference_plane_normal=tuple(d.get("reference_plane_normal", (0.0, 0.0, 1.0))),
            angle_deg=d.get("angle_deg"),
            sense=LoadSense(d.get("sense", LoadSense.INDETERMINATE.value)),
            magnitude=d.get("magnitude"),
            indeterminate=bool(d.get("indeterminate", True)),
            unit=d.get("unit", "N"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class ElasticityCondition(Condition):
    """Reusable elasticity condition.

    Configuration stored:
    - one or more selected faces;
    - flex range / magnitude in mm (``flex_range_mm``).
    """
    faces: SelectionSet = field(default_factory=lambda: SelectionSet(name="Caras de elasticidad"))
    flex_range_mm: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.ELASTICITY

    def selection(self) -> Optional[SelectionSet]:
        return self.faces

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.condition_type.value,
            "id": self.id,
            "name": self.name,
            "faces": self.faces.to_dict(),
            "flex_range_mm": self.flex_range_mm,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ElasticityCondition":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Elasticidad"),
            faces=SelectionSet.from_dict(d["faces"]),
            flex_range_mm=d.get("flex_range_mm"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class ObstructionCondition(Condition):
    """Reusable obstruction condition.

    Configuration stored:
    - one or more selected solid bodies (``bodies``);
    - optional offset in mm (``offset_mm``).
    """
    bodies: SelectionSet = field(default_factory=lambda: SelectionSet(name="Cuerpos de obstrucción"))
    offset_mm: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.OBSTRUCTION

    def selection(self) -> Optional[SelectionSet]:
        return self.bodies

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.condition_type.value,
            "id": self.id,
            "name": self.name,
            "bodies": self.bodies.to_dict(),
            "offset_mm": self.offset_mm,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ObstructionCondition":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Obstrucción"),
            bodies=SelectionSet.from_dict(d["bodies"]),
            offset_mm=d.get("offset_mm"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class ProtectedRegion(Condition):
    """Reusable protected region.

    Uses the *Región protegida* concept instead of "Caras a conservar": the
    selected faces are stored as geometry that optimization must not modify.

    ``geometry_refs`` makes the model extensible toward protecting more complex
    geometric regions (descriptors such as boxes / spheres / CAD regions from
    ``core.selection``), not only flat faces.
    """
    faces: SelectionSet = field(default_factory=lambda: SelectionSet(name="Caras protegidas"))
    geometry_refs: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def condition_type(self) -> ConditionType:
        return ConditionType.PROTECTED_REGION

    def selection(self) -> Optional[SelectionSet]:
        return self.faces

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.condition_type.value,
            "id": self.id,
            "name": self.name,
            "faces": self.faces.to_dict(),
            "geometry_refs": list(self.geometry_refs),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProtectedRegion":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Región protegida"),
            faces=SelectionSet.from_dict(d["faces"]),
            geometry_refs=list(d.get("geometry_refs", [])),
            metadata=d.get("metadata", {}),
        )


CONDITION_CLASSES = {
    ConditionType.LOAD: LoadCondition,
    ConditionType.ELASTICITY: ElasticityCondition,
    ConditionType.OBSTRUCTION: ObstructionCondition,
    ConditionType.PROTECTED_REGION: ProtectedRegion,
}


def condition_from_dict(d: Dict[str, Any]) -> Condition:
    """Rebuild a typed Condition from its serialised dict."""
    ctype = ConditionType(d.get("type"))
    cls = CONDITION_CLASSES.get(ctype)
    if cls is None:
        raise ValueError(f"Unsupported condition type: {d.get('type')!r}")
    return cls.from_dict(d)


class ConditionManager:
    """Owns the set of reusable conditions created during a session.

    Optimization / generative studies reference conditions *by id* and resolve
    them here, so the same object is shared and never duplicated.
    """

    def __init__(self) -> None:
        self._conditions: Dict[str, Condition] = {}

    def add(self, condition: Condition) -> str:
        self._conditions[condition.id] = condition
        return condition.id

    def get(self, condition_id: str) -> Optional[Condition]:
        return self._conditions.get(condition_id)

    def resolve(self, condition_ids: Iterable[str]) -> List[Condition]:
        """Resolve a list of ids to the existing objects (unknown ids skipped).

        Each resolved condition is returned exactly once (shared objects are
        never duplicated).
        """
        seen: Dict[str, Condition] = {}
        for cid in condition_ids:
            cond = self._conditions.get(str(cid))
            if cond is not None and cond.id not in seen:
                seen[cond.id] = cond
        return list(seen.values())

    def conditions_by_type(self, ctype: ConditionType) -> List[Condition]:
        return [c for c in self._conditions.values() if c.condition_type == ctype]

    def remove(self, condition_id: str) -> bool:
        return self._conditions.pop(condition_id, None) is not None

    def clear(self) -> None:
        """Remove all reusable conditions (used by Cerrar modelo)."""
        self._conditions.clear()

    @property
    def all(self) -> List[Condition]:
        return list(self._conditions.values())

    def __len__(self) -> int:
        return len(self._conditions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": len(self._conditions),
            "conditions": [c.to_dict() for c in self._conditions.values()],
            "order": list(self._conditions.keys()),
        }