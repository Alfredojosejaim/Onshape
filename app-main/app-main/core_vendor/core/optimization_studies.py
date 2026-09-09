"""Optimization study types.

This module wraps the existing SIMP topology optimisation engine and the
upcoming generative design engine as specific Study subtypes within the
new architectural framework.

The existing ``core.study.Study`` data model continues to work as-is.
These classes add the architectural layer that connects features, commands,
and the document model to the optimisation workflow.

    OptimizationStudy (base)
    ├── TopologyOptimizationStudy   (wraps SIMP)
    └── GenerativeDesignStudy       (defined in generative.py)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.cae_studies import Study, StudyType, StudyStatus, StudyResult, LoadCase, ConstraintCase
from core.cad_entity import CadEntityRef, EntityType
from core.conditions import Condition, ConditionManager
from core.materials import Material, STANDARD_MATERIALS


class OptimizerType(str, Enum):
    SIMP = "simp"
    ESO = "eso"          # Evolutionary Structural Optimization
    LEVEL_SET = "level_set"


@dataclass
class TopOptParameters:
    """Parameters for topology optimisation (SIMP)."""
    volume_fraction: float = 0.3
    max_iterations: int = 50
    penalization: float = 3.0
    filter_radius: float = 1.5
    convergence_tolerance: float = 1e-3
    xmin: float = 1e-3
    optimizer: OptimizerType = OptimizerType.SIMP

    def to_dict(self) -> Dict[str, Any]:
        return {
            "volume_fraction": self.volume_fraction,
            "max_iterations": self.max_iterations,
            "penalization": self.penalization,
            "filter_radius": self.filter_radius,
            "convergence_tolerance": self.convergence_tolerance,
            "xmin": self.xmin,
            "optimizer": self.optimizer.value,
        }


class TopologyOptimizationStudy(Study):
    """Topology optimization study wrapping the existing SIMP engine.

    This study connects the architectural framework to the working SIMP
    implementation in ``core.topopt``.  The actual solve is delegated to
    the pipeline/controller layer which has access to the mesh.
    """

    study_type = StudyType.TOPOLOGY_OPTIMIZATION
    display_name = "Topology Optimization (SIMP)"
    description = "Minimum compliance topology optimization with volume constraint"

    def __init__(self, name: str = "Topology Optimization") -> None:
        super().__init__(name=name)
        self.optimization_params = TopOptParameters()
        self.design_region: Optional[Dict[str, Any]] = None  # future: restrict optimization domain
        self._iteration_history: List[Dict[str, Any]] = []

        # Structural optimization inputs (reuse pre-created conditions):
        # - one or more parts (pieces) to optimize;
        # - condition ids resolved against the shared ConditionManager.
        self.parts: List[CadEntityRef] = []
        self.conditions: List[str] = []

    # ------------------------------------------------------------------ #
    # Parts
    # ------------------------------------------------------------------ #
    def add_part(self, ref: CadEntityRef) -> None:
        """Add a part/piece to be optimised (consumed, not copied)."""
        if ref not in self.parts:
            self.parts.append(ref)

    def remove_part(self, solid_id: str) -> bool:
        before = len(self.parts)
        self.parts = [p for p in self.parts if str(getattr(p, "solid_id", "")) != str(solid_id)]
        return len(self.parts) < before

    # ------------------------------------------------------------------ #
    # Conditions (shared, never duplicated)
    # ------------------------------------------------------------------ #
    def add_condition(self, condition_id: str) -> None:
        """Reference a pre-created condition by id."""
        cid = str(condition_id)
        if cid not in self.conditions:
            self.conditions.append(cid)

    def remove_condition(self, condition_id: str) -> bool:
        cid = str(condition_id)
        before = len(self.conditions)
        self.conditions = [c for c in self.conditions if c != cid]
        return len(self.conditions) < before

    def consume_conditions(self, manager: ConditionManager) -> List[Condition]:
        """Resolve the referenced conditions without duplicating them.

        The study references condition ids; the shared ConditionManager owns
        the actual objects.  Unknown ids are skipped.
        """
        return manager.resolve(self.conditions)

    def set_params(
        self,
        volume_fraction: Optional[float] = None,
        max_iterations: Optional[int] = None,
        penalization: Optional[float] = None,
        filter_radius: Optional[float] = None,
    ) -> None:
        if volume_fraction is not None:
            self.optimization_params.volume_fraction = volume_fraction
        if max_iterations is not None:
            self.optimization_params.max_iterations = max_iterations
        if penalization is not None:
            self.optimization_params.penalization = penalization
        if filter_radius is not None:
            self.optimization_params.filter_radius = filter_radius

    def add_iteration(self, iteration: int, volume_fraction: float,
                      compliance: float, max_change: float) -> None:
        self._iteration_history.append({
            "iteration": iteration,
            "volume_fraction": volume_fraction,
            "compliance": compliance,
            "max_change": max_change,
        })

    @property
    def iteration_history(self) -> List[Dict[str, Any]]:
        return list(self._iteration_history)

    def validate(self) -> bool:
        # Must have at least one part (solid) selected.
        if not self.parts:
            return False
        # All parts must be SOLID type.
        for ref in self.parts:
            if ref.entity_type != EntityType.SOLID:
                return False
        # All parts must reference the same model.
        model_ids = {p.model_id for p in self.parts if p.model_id}
        if len(model_ids) > 1:
            return False
        # Must have at least one condition or legacy load/constraint.
        if not self.conditions and not self.loads and not self.constraints:
            return False
        p = self.optimization_params
        if not (0.0 < p.volume_fraction <= 1.0):
            return False
        if p.max_iterations <= 0:
            return False
        return True

    def execute(self) -> StudyResult:
        """Mark study as ready for pipeline execution.

        The actual SIMP solve happens in the pipeline layer because it
        requires the mesh and the FEA solver infrastructure.
        """
        if not self.validate():
            self.status = StudyStatus.FAILED
            return StudyResult(
                success=False,
                status="validation_failed",
                error_message="Model not set or invalid optimization parameters.",
            )
        self.status = StudyStatus.READY
        return StudyResult(
            success=True,
            status="ready_for_pipeline",
            data={
                "study_id": self.id,
                "type": self.study_type.value,
                "params": self.optimization_params.to_dict(),
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["optimization_params"] = self.optimization_params.to_dict()
        base["iteration_history"] = self._iteration_history
        base["parts"] = [p.to_dict() for p in self.parts]
        base["conditions"] = [str(c) for c in self.conditions]
        return base
