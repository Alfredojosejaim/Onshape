"""Feature history system.

A Feature represents a single operation that transforms the CAD model.
Features are ordered in a list (the history) and each one carries enough
information to be reproduced.

Every Feature has:
- ``id``          unique identifier
- ``name``        human-readable label
- ``feature_type`` discriminator for the kind of operation
- ``parameters``  dict of operation-specific inputs
- ``status``      pending | executed | failed | rolled_back
- ``result_model_id``  the model state produced by this feature (if any)

Supported feature types (architecture ready, not all implemented now):
- ``import_step``       STEP file import
- ``boolean``           union / difference / intersection
- ``transform``         translation, rotation, scale
- ``mirror``            mirror about a plane
- ``pattern``           linear / circular pattern
- ``fillet``            edge rounding
- ``chamfer``           edge chamfer
- ``shell``             hollow out
- ``measurement``       measure distance / angle / area

The Feature classes are pure data -- they do NOT execute geometry
operations.  Execution is delegated to the command / pipeline layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FeatureStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class FeatureType(str, Enum):
    IMPORT_STEP = "import_step"
    BOOLEAN = "boolean"
    TRANSFORM = "transform"
    MIRROR = "mirror"
    PATTERN = "pattern"
    FILLET = "fillet"
    CHAMFER = "chamfer"
    SHELL = "shell"
    MEASUREMENT = "measurement"
    CUSTOM = "custom"


@dataclass
class Feature:
    """A single CAD operation in the feature history.

    This is a lightweight data container.  The ``parameters`` dict holds
    feature-type-specific data (e.g. for a boolean: operation type,
    target body id, tool body ids, keep_tools flag).

    The pipeline / controller layer is responsible for interpreting
    ``parameters`` and performing the actual geometry operation.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    feature_type: FeatureType = FeatureType.CUSTOM
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: FeatureStatus = FeatureStatus.PENDING
    result_model_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ---- Convenience constructors ---- #

    @classmethod
    def import_step(cls, filename: str, model_id: Optional[str] = None, **kw: Any) -> "Feature":
        return cls(
            name=f"Import {filename}",
            feature_type=FeatureType.IMPORT_STEP,
            parameters={"filename": filename, **kw},
            result_model_id=model_id,
            status=FeatureStatus.EXECUTED,
        )

    @classmethod
    def boolean_op(
        cls,
        operation: str,
        target_body_id: str,
        tool_body_ids: List[str],
        keep_tools: bool = False,
        **kw: Any,
    ) -> "Feature":
        return cls(
            name=f"Boolean ({operation})",
            feature_type=FeatureType.BOOLEAN,
            parameters={
                "operation": operation,
                "target_body_id": target_body_id,
                "tool_body_ids": tool_body_ids,
                "keep_tools": keep_tools,
                **kw,
            },
        )

    @classmethod
    def transform(cls, matrix: List[float], target_body_id: str, **kw: Any) -> "Feature":
        return cls(
            name="Transform",
            feature_type=FeatureType.TRANSFORM,
            parameters={"matrix": matrix, "target_body_id": target_body_id, **kw},
        )

    @classmethod
    def mirror(cls, plane_point: List[float], plane_normal: List[float],
               target_body_id: str, **kw: Any) -> "Feature":
        return cls(
            name="Mirror",
            feature_type=FeatureType.MIRROR,
            parameters={
                "plane_point": plane_point,
                "plane_normal": plane_normal,
                "target_body_id": target_body_id,
                **kw,
            },
        )

    # ---- Serialisation ---- #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "feature_type": self.feature_type.value,
            "parameters": self.parameters,
            "status": self.status.value,
            "result_model_id": self.result_model_id,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"Feature(id={self.id!r}, type={self.feature_type.value!r}, "
            f"name={self.name!r}, status={self.status.value!r})"
        )


class FeatureHistory:
    """Ordered list of Features that produced the current model state.

    The history is append-only during normal operation.  Rollback is
    supported by marking features as ``ROLLED_BACK`` and rebuilding from
    the remaining executed features.

    ``rebuild_order`` returns only the features that should be replayed
    to reconstruct a given model state.
    """

    def __init__(self) -> None:
        self._features: List[Feature] = []

    def append(self, feature: Feature) -> None:
        self._features.append(feature)

    def remove(self, feature_id: str) -> bool:
        before = len(self._features)
        self._features = [f for f in self._features if f.id != feature_id]
        return len(self._features) < before

    def rollback(self, feature_id: str) -> bool:
        for f in self._features:
            if f.id == feature_id:
                f.status = FeatureStatus.ROLLED_BACK
                return True
        return False

    def index_of(self, feature_id: str) -> int:
        for i, f in enumerate(self._features):
            if f.id == feature_id:
                return i
        return -1

    @property
    def features(self) -> List[Feature]:
        return list(self._features)

    @property
    def executed_features(self) -> List[Feature]:
        return [f for f in self._features if f.status == FeatureStatus.EXECUTED]

    def rebuild_order(self) -> List[Feature]:
        """Return features in execution order, excluding rolled-back ones."""
        return [f for f in self._features if f.status not in (
            FeatureStatus.ROLLED_BACK, FeatureStatus.FAILED,
        )]

    def last_executed_model_id(self) -> Optional[str]:
        for f in reversed(self._features):
            if f.status == FeatureStatus.EXECUTED and f.result_model_id:
                return f.result_model_id
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": len(self._features),
            "features": [f.to_dict() for f in self._features],
        }

    def __len__(self) -> int:
        return len(self._features)

    def __iter__(self):
        return iter(self._features)

    def __repr__(self) -> str:
        return f"FeatureHistory({len(self._features)} features)"
