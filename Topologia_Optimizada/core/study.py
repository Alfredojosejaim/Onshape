"""Core Study domain models: loads, constraints, objectives, and optimization settings.

These models represent an engineering topology optimization study independently of any CAD source.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.materials import Material, STANDARD_MATERIALS
from core.models import CADModel


class LoadType(str, Enum):
    POINT = "point"
    DISTRIBUTED = "distributed"
    PRESSURE = "pressure"


class ConstraintType(str, Enum):
    FIXED = "fixed"
    PINNED = "pinned"
    ROLLER = "roller"
    SYMMETRY = "symmetry"


@dataclass
class LoadDefinition:
    """Applied structural load."""
    id: str
    magnitude: float
    direction: Tuple[float, float, float]
    application_face_id: Optional[str] = None
    load_type: LoadType = LoadType.POINT
    unit: str = "N"

    def __post_init__(self):
        if self.magnitude <= 0:
            raise ValueError("Load magnitude must be positive")
        if self.direction[0] == 0 and self.direction[1] == 0 and self.direction[2] == 0:
            raise ValueError("Load direction vector cannot be zero")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "magnitude": float(self.magnitude),
            "direction_x": float(self.direction[0]),
            "direction_y": float(self.direction[1]),
            "direction_z": float(self.direction[2]),
            "application_face_id": self.application_face_id,
            "load_type": self.load_type.value,
            "unit": self.unit,
        }


@dataclass
class ConstraintDefinition:
    """Structural kinematic constraint."""
    id: str
    constraint_type: ConstraintType
    location_face_id: str
    degrees_of_freedom: Dict[str, bool] = field(default_factory=lambda: {
        "ux": True, "uy": True, "uz": True, "rx": True, "ry": True, "rz": True
    })

    def __post_init__(self):
        if not any(self.degrees_of_freedom.values()):
            raise ValueError("At least one degree of freedom must be constrained")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "constraint_type": self.constraint_type.value,
            "location_face_id": self.location_face_id,
            "degrees_of_freedom": self.degrees_of_freedom,
        }


@dataclass
class Objectives:
    """Optimization objectives and constraints."""
    volume_fraction: float = 0.3

    def __post_init__(self):
        if not (0.0 < self.volume_fraction <= 1.0):
            raise ValueError("Volume fraction must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volume_fraction": float(self.volume_fraction),
        }


@dataclass
class SolverSettings:
    """Numerical optimization solver configuration."""
    max_iterations: int = 50
    convergence_tolerance: float = 0.01
    penalization: float = 3.0
    filter_radius: float = 1.5

    def __post_init__(self):
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if self.convergence_tolerance <= 0:
            raise ValueError("convergence_tolerance must be positive")
        if self.penalization <= 0:
            raise ValueError("penalization must be positive")
        if self.filter_radius <= 0:
            raise ValueError("filter_radius must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "convergence_tolerance": float(self.convergence_tolerance),
            "penalization": float(self.penalization),
            "filter_radius": float(self.filter_radius),
        }


@dataclass
class Study:
    """Complete, self-contained optimization study entity."""
    id: str
    name: str
    cad_model_id: Optional[str] = None
    cad_model: Optional[CADModel] = None
    material: Material = field(default_factory=lambda: STANDARD_MATERIALS["steel"])
    loads: List[LoadDefinition] = field(default_factory=list)
    constraints: List[ConstraintDefinition] = field(default_factory=list)
    objectives: Objectives = field(default_factory=Objectives)
    solver_settings: SolverSettings = field(default_factory=SolverSettings)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cad_model_id": self.cad_model_id,
            "material": self.material.to_dict() if self.material else None,
            "loads": [l.to_dict() for l in self.loads],
            "constraints": [c.to_dict() for c in self.constraints],
            "objectives": self.objectives.to_dict(),
            "solver_settings": self.solver_settings.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }
