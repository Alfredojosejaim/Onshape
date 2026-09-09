"""CAD/CAE Document abstraction.

A Document represents the full state of a design session: the geometry model,
the feature history that produced it, the engineering studies attached to it,
and any results produced by those studies.

Conceptual structure:

    Document
    ├── Models        (CAD geometry snapshots)
    ├── Features      (operations that produced each model state)
    ├── Studies       (engineering analyses)
    ├── Results       (outputs of studies)
    └── Metadata      (name, description, timestamps, etc.)

The Document is the root container for the CAD/CAE data model.  It does NOT
perform I/O or heavy computation -- those responsibilities belong to the
services and pipeline layers.

This module introduces the abstraction *without* breaking the existing
PipelineController workflow.  The controller can create a Document from its
current in-memory state and progressively migrate toward it as the single
source of truth.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.models import CADModel


class DocumentState(str, Enum):
    EMPTY = "empty"
    HAS_MODEL = "has_model"
    HAS_FEATURES = "has_features"
    HAS_STUDIES = "has_studies"
    HAS_RESULTS = "has_results"


@dataclass
class DocumentMetadata:
    """Lightweight document-level metadata."""
    name: str = "Untitled"
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    author: str = ""
    tags: List[str] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()


class Document:
    """Root container for a CAD/CAE design session.

    A Document owns:
    * **models** -- the CAD geometry states (at minimum the current imported
      model; future: intermediate model snapshots produced by Features).
    * **features** -- the ordered history of operations (import, boolean,
      transform, etc.) that have been applied.
    * **studies** -- engineering analyses (structural, thermal, optimisation,
      generative design) attached to a particular model state.
    * **results** -- outputs produced by running studies.

    The Document does not prescribe how features or studies are *executed*;
    that responsibility stays with the pipeline/controller layer.

    Lifecycle
    ---------
    1. ``doc = Document()``                       -- empty
    2. ``doc.set_model(cad_model)``               -- geometry loaded
    3. ``doc.add_feature(ImportFeature(...))``     -- history recorded
    4. ``doc.add_study(StructuralStudy(...))``    -- study attached
    5. ``doc.add_result(study_id, result_dict)``  -- result stored
    """

    def __init__(self, name: str = "Untitled") -> None:
        self.id: str = str(uuid.uuid4())
        self.metadata = DocumentMetadata(name=name)

        # ---- Models ----
        self._models: Dict[str, CADModel] = {}
        self._active_model_id: Optional[str] = None

        # ---- Features (history) ----
        self._features: List[Any] = []  # List[Feature] -- Any avoids circular import

        # ---- Conditions (reusable, shared) ----
        self._conditions: Dict[str, Any] = {}  # Dict[condition_id, Condition]

        # ---- Studies ----
        self._studies: Dict[str, Any] = {}  # Dict[study_id, Study]

        # ---- Results ----
        self._results: Dict[str, Any] = {}  # Dict[study_id, result_dict]

    # ================================================================== #
    # State queries
    # ================================================================== #
    @property
    def state(self) -> DocumentState:
        if self._results:
            return DocumentState.HAS_RESULTS
        if self._studies:
            return DocumentState.HAS_STUDIES
        if self._features:
            return DocumentState.HAS_FEATURES
        if self._conditions:
            return DocumentState.HAS_FEATURES
        if self._models:
            return DocumentState.HAS_MODEL
        return DocumentState.EMPTY

    @property
    def is_empty(self) -> bool:
        return self.state == DocumentState.EMPTY

    # ================================================================== #
    # Models
    # ================================================================== #
    def set_model(self, model: CADModel) -> str:
        """Register a CAD model and make it the active model.

        Returns the model id.
        """
        self._models[model.id] = model
        self._active_model_id = model.id
        self.metadata.touch()
        return model.id

    def get_model(self, model_id: Optional[str] = None) -> Optional[CADModel]:
        mid = model_id or self._active_model_id
        return self._models.get(mid) if mid else None

    @property
    def active_model_id(self) -> Optional[str]:
        return self._active_model_id

    @property
    def active_model(self) -> Optional[CADModel]:
        return self.get_model()

    @property
    def models(self) -> List[CADModel]:
        return list(self._models.values())

    # ================================================================== #
    # Features (history)
    # ================================================================== #
    def add_feature(self, feature: Any) -> None:
        """Append a Feature to the history.

        ``feature`` must expose ``id``, ``name``, ``feature_type`` and
        ``to_dict()``.  We use ``Any`` here to avoid a circular import with
        ``core.features``; the feature protocol is duck-typed.
        """
        self._features.append(feature)
        self.metadata.touch()

    def remove_feature(self, feature_id: str) -> bool:
        before = len(self._features)
        self._features = [f for f in self._features if getattr(f, "id", None) != feature_id]
        if len(self._features) < before:
            self.metadata.touch()
            return True
        return False

    @property
    def features(self) -> List[Any]:
        return list(self._features)

    def feature_index(self, feature_id: str) -> int:
        for i, f in enumerate(self._features):
            if getattr(f, "id", None) == feature_id:
                return i
        return -1

    # ================================================================== #
    # Conditions (reusable, shared across studies)
    # ================================================================== #
    def add_condition(self, condition: Any) -> str:
        """Register a reusable Condition and return its id."""
        cid = getattr(condition, "id", str(uuid.uuid4()))
        self._conditions[cid] = condition
        self.metadata.touch()
        return cid

    def get_condition(self, condition_id: str) -> Optional[Any]:
        return self._conditions.get(condition_id)

    def remove_condition(self, condition_id: str) -> bool:
        removed = self._conditions.pop(condition_id, None) is not None
        if removed:
            self.metadata.touch()
        return removed

    @property
    def conditions(self) -> List[Any]:
        return list(self._conditions.values())

    # ================================================================== #
    # Studies
    # ================================================================== #
    def add_study(self, study: Any) -> str:
        """Register a Study and return its id."""
        sid = getattr(study, "id", str(uuid.uuid4()))
        self._studies[sid] = study
        self.metadata.touch()
        return sid

    def get_study(self, study_id: str) -> Optional[Any]:
        return self._studies.get(study_id)

    def remove_study(self, study_id: str) -> bool:
        removed = self._studies.pop(study_id, None) is not None
        if removed:
            self._results.pop(study_id, None)
            self.metadata.touch()
        return removed

    @property
    def studies(self) -> List[Any]:
        return list(self._studies.values())

    # ================================================================== #
    # Results
    # ================================================================== #
    def add_result(self, study_id: str, result: Any) -> None:
        self._results[study_id] = result
        self.metadata.touch()

    def get_result(self, study_id: str) -> Optional[Any]:
        return self._results.get(study_id)

    @property
    def results(self) -> Dict[str, Any]:
        return dict(self._results)

    def clear(self) -> None:
        """Reset the document to an empty session (used by Cerrar modelo)."""
        self._models.clear()
        self._active_model_id = None
        self._features.clear()
        self._conditions.clear()
        self._studies.clear()
        self._results.clear()
        self.metadata.touch()

    # ================================================================== #
    # Serialisation helpers
    # ================================================================== #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "metadata": {
                "name": self.metadata.name,
                "description": self.metadata.description,
                "created_at": self.metadata.created_at,
                "updated_at": self.metadata.updated_at,
            },
            "state": self.state.value,
            "active_model_id": self._active_model_id,
            "models_count": len(self._models),
            "features_count": len(self._features),
            "conditions_count": len(self._conditions),
            "studies_count": len(self._studies),
            "results_count": len(self._results),
        }

    def __repr__(self) -> str:
        return (
            f"Document(id={self.id!r}, name={self.metadata.name!r}, "
            f"state={self.state.value})"
        )
