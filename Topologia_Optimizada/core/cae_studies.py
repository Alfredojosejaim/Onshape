"""CAE Study abstractions.

A Study represents an engineering analysis attached to a CAD model.
Studies are separate from Features: Features transform geometry, Studies
analyse it.

This module provides the base Study class and common study types:
- StructuralAnalysis (linear static FEA)
- ThermalAnalysis (placeholder)
- ModalAnalysis (placeholder)

The existing ``core.study.Study`` is an optimization-specific study.
This module generalises the concept so different kinds of analyses can
coexist under a unified architecture.

    Study (base)
    ├── StructuralAnalysis
    ├── ThermalAnalysis
    ├── ModalAnalysis
    └── ... future study types
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.cad_entity import CadEntityRef, SelectionSet
from core.materials import Material, STANDARD_MATERIALS


class StudyType(str, Enum):
    STRUCTURAL = "structural"
    THERMAL = "thermal"
    MODAL = "modal"
    TOPOLOGY_OPTIMIZATION = "topology_optimization"
    GENERATIVE_DESIGN = "generative_design"
    CUSTOM = "custom"


class StudyStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LoadCase:
    """A single load application: entity + magnitude + direction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    magnitude: float = 1000.0
    direction: tuple = (0.0, 0.0, -1.0)
    load_type: str = "point"  # point | distributed | pressure
    unit: str = "N"
    selection: Optional[SelectionSet] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "magnitude": self.magnitude,
            "direction": list(self.direction),
            "load_type": self.load_type,
            "unit": self.unit,
            "selection": self.selection.to_dict() if self.selection else None,
        }


@dataclass
class ConstraintCase:
    """A single constraint application: entity + constrained DOFs."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    constraint_type: str = "fixed"  # fixed | pinned | roller | symmetry
    dof: Dict[str, bool] = field(default_factory=lambda: {
        "ux": True, "uy": True, "uz": True, "rx": True, "ry": True, "rz": True
    })
    selection: Optional[SelectionSet] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "constraint_type": self.constraint_type,
            "dof": dict(self.dof),
            "selection": self.selection.to_dict() if self.selection else None,
        }


@dataclass
class StudyResult:
    """Generic result container for any study."""
    success: bool = False
    status: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "data": self.data,
            "error_message": self.error_message,
        }


class Study(ABC):
    """Abstract base class for all engineering studies.

    Subclasses must implement:
    - ``study_type``          class-level StudyType
    - ``display_name``       human-readable name
    - ``validate()``         check preconditions
    - ``execute()``          run the analysis, return StudyResult
    """

    study_type: StudyType = StudyType.CUSTOM
    display_name: str = "Custom Study"
    description: str = ""

    def __init__(self, name: str = "") -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name or self.display_name
        self.status: StudyStatus = StudyStatus.DRAFT
        self.model_id: Optional[str] = None
        self.material: Material = STANDARD_MATERIALS["steel"]
        self.loads: List[LoadCase] = []
        self.constraints: List[ConstraintCase] = []
        self.result: Optional[StudyResult] = None
        self.metadata: Dict[str, Any] = {}

    def add_load(self, load: LoadCase) -> None:
        self.loads.append(load)

    def add_constraint(self, constraint: ConstraintCase) -> None:
        self.constraints.append(constraint)

    @abstractmethod
    def validate(self) -> bool:
        """Check that the study is ready to run."""

    @abstractmethod
    def execute(self) -> StudyResult:
        """Execute the study.  Returns a StudyResult."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "study_type": self.study_type.value,
            "status": self.status.value,
            "model_id": self.model_id,
            "material": self.material.to_dict() if self.material else None,
            "loads": [l.to_dict() for l in self.loads],
            "constraints": [c.to_dict() for c in self.constraints],
            "result": self.result.to_dict() if self.result else None,
            "metadata": self.metadata,
        }


# ====================================================================== #
# Structural Analysis
# ====================================================================== #

class StructuralAnalysis(Study):
    """Linear static structural analysis using the existing FEA solver.

    This study wraps ``core.fea.solve_fea`` and bridges the existing
    Study data model with the new architectural framework.
    """

    study_type = StudyType.STRUCTURAL
    display_name = "Structural Analysis"
    description = "Linear static FEA (3D Tet4)"

    def __init__(self, name: str = "Structural Analysis") -> None:
        super().__init__(name=name)

    def validate(self) -> bool:
        if self.model_id is None:
            return False
        if not self.loads and not self.constraints:
            return False
        return True

    def execute(self) -> StudyResult:
        """Execute structural analysis.

        The actual FEA solve is delegated to the pipeline/controller layer
        because it requires access to the mesh and solver infrastructure.
        This method marks the study as ready for execution.
        """
        if not self.validate():
            self.status = StudyStatus.FAILED
            return StudyResult(
                success=False,
                status="validation_failed",
                error_message="Model not set or no loads/constraints defined.",
            )
        self.status = StudyStatus.READY
        return StudyResult(
            success=True,
            status="ready_for_pipeline",
            data={"study_id": self.id, "type": self.study_type.value},
        )


# ====================================================================== #
# Thermal Analysis (placeholder)
# ====================================================================== #

class ThermalAnalysis(Study):
    """Thermal analysis study (placeholder for future implementation)."""

    study_type = StudyType.THERMAL
    display_name = "Thermal Analysis"
    description = "Steady-state thermal analysis"

    def __init__(self, name: str = "Thermal Analysis") -> None:
        super().__init__(name=name)

    def validate(self) -> bool:
        return self.model_id is not None

    def execute(self) -> StudyResult:
        self.status = StudyStatus.FAILED
        return StudyResult(
            success=False,
            status="not_implemented",
            error_message="Thermal analysis is not yet implemented.",
        )


# ====================================================================== #
# Modal Analysis (placeholder)
# ====================================================================== #

class ModalAnalysis(Study):
    """Modal / frequency analysis study (placeholder)."""

    study_type = StudyType.MODAL
    display_name = "Modal Analysis"
    description = "Natural frequency / mode shape analysis"

    def __init__(self, name: str = "Modal Analysis") -> None:
        super().__init__(name=name)

    def validate(self) -> bool:
        return self.model_id is not None

    def execute(self) -> StudyResult:
        self.status = StudyStatus.FAILED
        return StudyResult(
            success=False,
            status="not_implemented",
            error_message="Modal analysis is not yet implemented.",
        )
