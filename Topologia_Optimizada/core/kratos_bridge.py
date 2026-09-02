"""Bridge from reusable Conditions to Kratos FEA definitions.

This module provides the translation layer that lets the optional Kratos FEA
backend consume the *same* reusable :class:`Condition` objects used by the
generative-design / topology-optimization paths.

It converts:

- :class:`LoadCondition` -> :class:`~core.study.LoadDefinition`
- :class:`ElasticityCondition` -> :class:`~core.study.ConstraintDefinition`

using the exact same geometric semantics as ``GenerativeDesignEngine``
(the ``direction_vector`` function and the CAD ``FaceRegion`` selection), so a
Kratos solve and the local (NumPy) solve agree on which nodes a load/support
acts on.

Obstruction / protected-region conditions are *not* FEA conditions (they affect
the SIMP design subdomain, not the static equilibrium) and are skipped; a
top-level helper exposes which condition kinds are applicable to the FEA step.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.cad_entity import EntityType
from core.conditions import (
    Condition,
    ConditionType,
    ElasticityCondition,
    LoadCondition,
)
from core.study import (
    ConstraintDefinition,
    ConstraintType,
    LoadDefinition,
    LoadType,
)

#: Condition kinds that can be translated to the static FEA step.
_FEA_CONDITION_KINDS = (ConditionType.LOAD, ConditionType.ELASTICITY)


def _face_indices(condition: Condition) -> List[int]:
    """0-based CAD face indices selected by a condition (B-Rep face refs)."""
    faces = condition.selection()
    if faces is None:
        return []
    indices: List[int] = []
    for entity in faces.entities:
        if entity.entity_type == EntityType.FACE and entity.face_index is not None:
            indices.append(int(entity.face_index))
    return sorted(indices)


def _face_selection(face_indices: List[int], tolerance: float = 0.5) -> Dict[str, Any]:
    """A JSON-compatible ``FaceRegion`` selection descriptor."""
    return {
        "type": "face",
        "face_indices": list(face_indices),
        "tolerance": float(tolerance),
    }


def load_condition_to_definition(load: LoadCondition) -> LoadDefinition:
    """Translate a reusable load condition into a Kratos/FEA ``LoadDefinition``.

    The direction is derived with the shared ``direction_vector`` (identical to
    the local solver path); the magnitude defaults to 1000 N when indeterminate,
    again matching ``GenerativeDesignEngine``.
    """
    from core.generative_engine import direction_vector

    vec = direction_vector(load)
    magnitude = float(load.magnitude if load.magnitude is not None else 1000.0)
    face_indices = _face_indices(load)

    selection: Optional[Dict[str, Any]] = None
    application_face_id: Optional[str] = None
    if face_indices:
        selection = _face_selection(face_indices, tolerance=0.5)
        # Reference the first selected face for the geometry-aware strategies.
        first_face = next(
            (e for e in (load.selection().entities if load.selection() else [])
             if e.entity_type == EntityType.FACE and e.face_index is not None),
            None,
        )
        if first_face is not None:
            application_face_id = str(int(first_face.face_index))

    return LoadDefinition(
        id=load.id,
        magnitude=magnitude,
        direction=(float(vec[0]), float(vec[1]), float(vec[2])),
        application_face_id=application_face_id,
        load_type=LoadType.DISTRIBUTED,
        unit=load.unit,
        tolerance=0.5,
        selection=selection,
    )


def elasticity_condition_to_definition(elasticity: ElasticityCondition) -> ConstraintDefinition:
    """Translate a reusable elasticity condition into a fixed ``ConstraintDefinition``.

    Elasticity models a (rigid) support on the selected faces: every
    translational degree of freedom is constrained.  When faces are selected they
    are emitted as a CAD ``FaceRegion`` selection so the Kratos advanced-selection
    / CAD-face strategies select those *exact* nodes (and fail loudly if they
    cannot be mapped).  With no selected face the definition carries no selection,
    letting the Kratos coordinate fallback apply (matching the local solver).
    """
    face_indices = _face_indices(elasticity)

    selection: Optional[Dict[str, Any]] = None
    location_face_id: str = ""
    if face_indices:
        selection = _face_selection(face_indices, tolerance=0.5)
        first_face = next(
            (e for e in (elasticity.selection().entities if elasticity.selection() else [])
             if e.entity_type == EntityType.FACE and e.face_index is not None),
            None,
        )
        if first_face is not None:
            location_face_id = str(int(first_face.face_index))

    return ConstraintDefinition(
        id=elasticity.id,
        constraint_type=ConstraintType.FIXED,
        location_face_id=location_face_id,
        degrees_of_freedom={
            "ux": True, "uy": True, "uz": True,
            "rx": True, "ry": True, "rz": True,
        },
        tolerance=0.5,
        selection=selection,
    )


def conditions_to_kratos_definitions(
    conditions: List[Condition],
) -> Tuple[List[LoadDefinition], List[ConstraintDefinition], List[str]]:
    """Translate reusable conditions into Kratos load/constraint definitions.

    Args:
        conditions: The resolved, *deduplicated* reusable conditions (e.g. the
            output of ``ConditionManager.resolve`` / ``consume_conditions``).

    Returns:
        ``(loads, constraints, skipped)`` where ``skipped`` lists the ids of the
        conditions that are not FEA applicable (obstruction / protected region).

    Raises:
        ValueError: on a malformed or unsupported condition object.
    """
    loads: List[LoadDefinition] = []
    constraints: List[ConstraintDefinition] = []
    skipped: List[str] = []

    for condition in conditions:
        if isinstance(condition, LoadCondition):
            loads.append(load_condition_to_definition(condition))
        elif isinstance(condition, ElasticityCondition):
            constraints.append(elasticity_condition_to_definition(condition))
        elif isinstance(condition, Condition) and condition.condition_type in _FEA_CONDITION_KINDS:
            # Exhaustively handled above; defensive fallback for the enum kinds.
            skip_reason = (
                f"condition {condition.id} has FEA kind {condition.condition_type.value!r} "
                f"but no concrete handler"
            )
            skipped.append(skip_reason)
        elif isinstance(condition, Condition):
            skipped.append(str(condition.id))
        else:
            raise ValueError(f"Cannot translate object to a Kratos FEA definition: {condition!r}")

    return loads, constraints, skipped