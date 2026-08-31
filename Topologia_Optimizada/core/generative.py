"""Generative Design study.

Generative design is fundamentally different from topology optimisation:
it can *create* geometry in empty space between existing parts, not just
remove material from an existing part.

Two scenarios are supported:

SCENARIO A -- Optimise existing geometry (like SIMP but with richer output):
    Existing CAD → Conditions → Design space → Optimisation → Optimised geometry

SCENARIO B -- Connect parts with generated geometry:
    Part A + Part B → Available space → Conditions → Generation + Optimisation → Generated CAD

The architecture separates:
- ``geometry_generation`` -- algorithms that propose material placement
- ``optimisation``        -- algorithms that refine the proposal
- ``cad_reconstruction``  -- conversion from volumetric/mesh result to B-Rep

Neither the generation algorithm nor the reconstruction algorithm is
implemented in this phase.  This module provides the architectural
backbone so they can be plugged in later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.cae_studies import Study, StudyType, StudyStatus, StudyResult, LoadCase, ConstraintCase
from core.cad_entity import CadEntityRef, SelectionSet
from core.optimization_studies import TopOptParameters


class GenerationMethod(str, Enum):
    VOXEL_FILL = "voxel_fill"
    LEVEL_SET = "level_set"
    GROWTH_METHOD = "growth_method"
    AI_GUIDED = "ai_guided"


class ReconstructionMethod(str, Enum):
    MARCHING_CUBES = "marching_cubes"
    POISSON = "poisson"
    BREP_FITTING = "brep_fitting"
    NONE = "none"


@dataclass
class DesignSpace:
    """Defines the volumetric region where geometry can be generated.

    For Scenario A this is derived from the existing model bounding box.
    For Scenario B this is the convex hull or bounding region between
    the connection targets.
    """
    bounds: Optional[Dict[str, float]] = None  # xmin/xmax/ymin/ymax/zmin/zmax
    exclusion_zones: List[Dict[str, Any]] = field(default_factory=list)
    resolution: float = 1.0  # voxel size for voxel-based generation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bounds": self.bounds,
            "exclusion_zones": self.exclusion_zones,
            "resolution": self.resolution,
        }


@dataclass
class GeometryGenerationConfig:
    """Configuration for the geometry generation stage."""
    method: GenerationMethod = GenerationMethod.VOXEL_FILL
    resolution: float = 1.0
    symmetry: Optional[str] = None  # none | x | y | z | xy | xz | yz | xyz
    min_thickness: float = 0.5
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "resolution": self.resolution,
            "symmetry": self.symmetry,
            "min_thickness": self.min_thickness,
            "parameters": self.parameters,
        }


@dataclass
class ReconstructionConfig:
    """Configuration for converting volumetric results to CAD B-Rep."""
    method: ReconstructionMethod = ReconstructionMethod.NONE
    smoothing_iterations: int = 5
    target_triangle_count: Optional[int] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "smoothing_iterations": self.smoothing_iterations,
            "target_triangle_count": self.target_triangle_count,
            "parameters": self.parameters,
        }


class GenerativeDesignStudy(Study):
    """Generative design study supporting both Scenario A and B.

    Scenario A (optimise existing):
        The user provides a geometry CAD and conditions; the system
        optimises material distribution within that geometry.

    Scenario B (connect parts):
        The user provides two or more parts (connection_targets); the
        system generates geometry in the space between them.
    """

    study_type = StudyType.GENERATIVE_DESIGN
    display_name = "Generative Design"
    description = "Geometry generation + optimisation for structural design"

    def __init__(self, name: str = "Generative Design") -> None:
        super().__init__(name=name)
        self.scenario: str = "A"  # "A" = optimise existing, "B" = connect parts
        self.connection_targets: List[CadEntityRef] = []
        self.design_space = DesignSpace()
        self.optimization_params = TopOptParameters()
        self.generation_config = GeometryGenerationConfig()
        self.reconstruction_config = ReconstructionConfig()
        self._generated_geometry: Optional[Dict[str, Any]] = None  # volumetric/mesh result
        self._reconstructed_cad: Optional[Dict[str, Any]] = None   # B-Rep result

    def set_scenario_a(self, model_id: str) -> None:
        """Configure for Scenario A: optimise existing geometry."""
        self.scenario = "A"
        self.model_id = model_id

    def set_scenario_b(self, targets: List[CadEntityRef]) -> None:
        """Configure for Scenario B: generate geometry between parts."""
        self.scenario = "B"
        self.connection_targets = targets

    def validate(self) -> bool:
        if self.scenario == "A" and self.model_id is None:
            return False
        if self.scenario == "B" and len(self.connection_targets) < 2:
            return False
        if not self.loads:
            return False
        return True

    def execute(self) -> StudyResult:
        """Mark as ready for pipeline execution.

        The actual generation + optimisation + reconstruction pipeline
        requires the mesh, solvers, and geometry backends -- all handled
        by the pipeline/controller layer.
        """
        if not self.validate():
            self.status = StudyStatus.FAILED
            return StudyResult(
                success=False,
                status="validation_failed",
                error_message="Invalid generative design configuration.",
            )
        self.status = StudyStatus.READY
        return StudyResult(
            success=True,
            status="ready_for_pipeline",
            data={
                "study_id": self.id,
                "scenario": self.scenario,
                "generation": self.generation_config.to_dict(),
                "optimization": self.optimization_params.to_dict(),
                "reconstruction": self.reconstruction_config.to_dict(),
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["scenario"] = self.scenario
        base["connection_targets"] = [t.to_dict() for t in self.connection_targets]
        base["design_space"] = self.design_space.to_dict()
        base["optimization_params"] = self.optimization_params.to_dict()
        base["generation_config"] = self.generation_config.to_dict()
        base["reconstruction_config"] = self.reconstruction_config.to_dict()
        return base
