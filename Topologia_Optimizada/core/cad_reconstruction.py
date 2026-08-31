"""CAD Reconstruction pipeline.

Converts volumetric or mesh-based results (from topology optimisation or
generative design) into B-Rep CAD geometry that can be exported as STEP.

Pipeline:

    Conditions / Optimisation result
         ↓
    Volumetric representation (density field / voxel grid)
         ↓
    Surface extraction (marching cubes / Poisson)
         ↓
    Mesh refinement / smoothing
         ↓
    B-Rep fitting (future: CadQuery/OCC)
         ↓
    CAD / STEP

Neither the surface extraction nor the B-Rep fitting algorithms are
implemented in this phase.  This module provides the architectural
backbone so they can be integrated without rewriting the pipeline.

The key design decision is that the output of generative design / topology
optimisation is NOT assumed to be just a mesh.  The architecture allows
the result to flow through reconstruction into a proper CAD solid.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class ReconstructionStage(str, Enum):
    DENSITY_FIELD = "density_field"
    SURFACE_MESH = "surface_mesh"
    SMOOTHED_MESH = "smoothed_mesh"
    BREP_SOLID = "brep_solid"
    STEP_FILE = "step_file"


class ReconstructionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReconstructionResult:
    """Output of a reconstruction pipeline stage."""
    stage: ReconstructionStage
    status: ReconstructionStatus = ReconstructionStatus.NOT_STARTED
    data: Optional[Any] = None  # numpy array, CadQuery Shape, or dict
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class SurfaceExtractor(ABC):
    """Abstract surface extraction from a density field or voxel grid."""

    @abstractmethod
    def extract(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        threshold: float = 0.5,
    ) -> ReconstructionResult:
        """Extract an isosurface from the density field."""


class DummySurfaceExtractor(SurfaceExtractor):
    """Placeholder that returns the mesh surface without real isosurface extraction."""

    def extract(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        threshold: float = 0.5,
    ) -> ReconstructionResult:
        return ReconstructionResult(
            stage=ReconstructionStage.SURFACE_MESH,
            status=ReconstructionStatus.NOT_STARTED,
            metadata={"note": "Surface extraction not yet implemented"},
        )


class BRepFitter(ABC):
    """Abstract B-Rep fitting from a triangle mesh."""

    @abstractmethod
    def fit(self, vertices: np.ndarray, triangles: np.ndarray) -> ReconstructionResult:
        """Fit a B-Rep solid to the triangle mesh."""


class DummyBRepFitter(BRepFitter):
    """Placeholder for future CadQuery/OCC B-Rep fitting."""

    def fit(self, vertices: np.ndarray, triangles: np.ndarray) -> ReconstructionResult:
        return ReconstructionResult(
            stage=ReconstructionStage.BREP_SOLID,
            status=ReconstructionStatus.NOT_STARTED,
            metadata={"note": "B-Rep fitting not yet implemented"},
        )


class ReconstructionPipeline:
    """Orchestrates the conversion from density field to CAD geometry.

    Stages:
    1. density_field  -- the raw optimisation result (per-element densities)
    2. surface_mesh   -- isosurface extraction (marching cubes, etc.)
    3. smoothed_mesh  -- mesh smoothing / decimation
    4. brep_solid     -- B-Rep fitting (CadQuery/OCC)
    5. step_file      -- STEP export

    Each stage is optional and pluggable.  The pipeline records
    intermediate results so the UI can display progress.
    """

    def __init__(
        self,
        surface_extractor: Optional[SurfaceExtractor] = None,
        brep_fitter: Optional[BRepFitter] = None,
    ) -> None:
        self._surface_extractor = surface_extractor or DummySurfaceExtractor()
        self._brep_fitter = brep_fitter or DummyBRepFitter()
        self._stages: Dict[ReconstructionStage, ReconstructionResult] = {}
        self._status = ReconstructionStatus.NOT_STARTED

    @property
    def status(self) -> ReconstructionStatus:
        return self._status

    def get_stage_result(self, stage: ReconstructionStage) -> Optional[ReconstructionResult]:
        return self._stages.get(stage)

    def run(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        densities: np.ndarray,
        threshold: float = 0.5,
    ) -> ReconstructionResult:
        """Run the full reconstruction pipeline.

        Returns the final stage result (B-Rep or surface mesh depending
        on what is implemented).
        """
        self._status = ReconstructionStatus.IN_PROGRESS

        # Stage 1: record density field
        self._stages[ReconstructionStage.DENSITY_FIELD] = ReconstructionResult(
            stage=ReconstructionStage.DENSITY_FIELD,
            status=ReconstructionStatus.COMPLETED,
            data={"nodes": nodes, "elements": elements, "densities": densities},
        )

        # Stage 2: surface extraction
        try:
            surface_result = self._surface_extractor.extract(
                nodes, elements, densities, threshold
            )
            self._stages[ReconstructionStage.SURFACE_MESH] = surface_result
        except Exception as exc:
            self._status = ReconstructionStatus.FAILED
            result = ReconstructionResult(
                stage=ReconstructionStage.SURFACE_MESH,
                status=ReconstructionStatus.FAILED,
                error_message=str(exc),
            )
            self._stages[ReconstructionStage.SURFACE_MESH] = result
            return result

        # Stage 3: skip smoothing for now
        self._stages[ReconstructionStage.SMOOTHED_MESH] = ReconstructionResult(
            stage=ReconstructionStage.SMOOTHED_MESH,
            status=ReconstructionStatus.NOT_STARTED,
        )

        # Stage 4: B-Rep fitting
        if surface_result.status == ReconstructionStatus.COMPLETED and surface_result.data:
            try:
                mesh_data = surface_result.data
                if isinstance(mesh_data, dict):
                    verts = mesh_data.get("vertices")
                    tris = mesh_data.get("triangles")
                    if verts is not None and tris is not None:
                        brep_result = self._brep_fitter.fit(
                            np.asarray(verts), np.asarray(tris)
                        )
                    else:
                        brep_result = ReconstructionResult(
                            stage=ReconstructionStage.BREP_SOLID,
                            status=ReconstructionStatus.NOT_STARTED,
                        )
                else:
                    brep_result = ReconstructionResult(
                        stage=ReconstructionStage.BREP_SOLID,
                        status=ReconstructionStatus.NOT_STARTED,
                    )
                self._stages[ReconstructionStage.BREP_SOLID] = brep_result
            except Exception as exc:
                brep_result = ReconstructionResult(
                    stage=ReconstructionStage.BREP_SOLID,
                    status=ReconstructionStatus.FAILED,
                    error_message=str(exc),
                )
                self._stages[ReconstructionStage.BREP_SOLID] = brep_result
        else:
            self._stages[ReconstructionStage.BREP_SOLID] = ReconstructionResult(
                stage=ReconstructionStage.BREP_SOLID,
                status=ReconstructionStatus.NOT_STARTED,
            )

        # Stage 5: STEP export (placeholder)
        self._stages[ReconstructionStage.STEP_FILE] = ReconstructionResult(
            stage=ReconstructionStage.STEP_FILE,
            status=ReconstructionStatus.NOT_STARTED,
        )

        self._status = ReconstructionStatus.COMPLETED
        # Return the best available result
        for stage in [
            ReconstructionStage.BREP_SOLID,
            ReconstructionStage.SURFACE_MESH,
            ReconstructionStage.DENSITY_FIELD,
        ]:
            r = self._stages.get(stage)
            if r and r.status == ReconstructionStatus.COMPLETED:
                return r
        return ReconstructionResult(
            stage=ReconstructionStage.DENSITY_FIELD,
            status=ReconstructionStatus.COMPLETED,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self._status.value,
            "stages": {
                k.value: v.to_dict() for k, v in self._stages.items()
            },
        }
