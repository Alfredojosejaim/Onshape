"""STEP CAD Format Adapter.

Converts STEP (ISO 10303) binary/text streams into the Core agnostic CADModel,
extracts topological entities, and provides tessellation for Three.js rendering.
"""

import logging
import os
import tempfile
import uuid
from typing import Any, Dict, Optional

import cadquery as cq

from adapters.cad.base import BaseCADAdapter
from core.geometry import GeometryEngine
from core.models import (
    BoundingBox3D,
    CADFace,
    CADModel,
    CADSolid,
    SourceReference,
    SourceType,
    TessellatedMesh,
    Unit,
)

logger = logging.getLogger(__name__)


class StepAdapter(BaseCADAdapter):
    """Adapter for importing STEP files into CAD-agnostic Core domain models."""

    def __init__(self):
        # Cache of parsed cq.Shape objects by CADModel id for efficient downstream operations
        self._shape_cache: Dict[str, cq.Shape] = {}

    def get_shape(self, model_id: str) -> Optional[cq.Shape]:
        """Retrieve the cached CadQuery Shape by CADModel ID."""
        return self._shape_cache.get(model_id)

    def cache_shape(self, model_id: str, shape: cq.Shape) -> None:
        """Cache a CadQuery Shape for a given CADModel ID."""
        self._shape_cache[model_id] = shape

    @staticmethod
    def _parse_step_bytes(data: bytes) -> cq.Shape:
        """Parse raw STEP byte buffer into a CadQuery/OpenCASCADE Shape."""
        if not data or len(data) == 0:
            raise ValueError("STEP data is empty")
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            imported = cq.importers.importStep(tmp_path)
            shape = imported.val()
            if shape is None or shape.isNull():
                raise ValueError("Could not parse valid 3D shape from STEP data")
            return shape
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    @staticmethod
    def _parse_step_file(file_path: str) -> cq.Shape:
        """Parse STEP file from disk into a CadQuery Shape."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"STEP file not found: {file_path}")
        imported = cq.importers.importStep(file_path)
        shape = imported.val()
        if shape is None or shape.isNull():
            raise ValueError(f"Could not parse valid 3D shape from STEP file: {file_path}")
        return shape

    def _build_cad_model_from_shape(
        self,
        shape: cq.Shape,
        model_id: str,
        model_name: str,
        source_ref: SourceReference,
        metadata: Optional[Dict[str, Any]] = None,
        generate_tessellation: bool = True,
    ) -> CADModel:
        """Construct a CADModel from a parsed CadQuery/OpenCASCADE Shape."""
        self.cache_shape(model_id, shape)

        bbox_3d = GeometryEngine.calculate_bounding_box(shape)
        cad_faces = GeometryEngine.extract_faces_metadata(shape)

        total_vol = float(shape.Volume())
        total_area = sum(f.area for f in cad_faces)

        # Build solid representation
        solid = CADSolid(
            id=f"solid_0",
            name=model_name,
            volume=total_vol,
            bbox=bbox_3d,
            faces=cad_faces,
            metadata=metadata or {},
        )

        tessellation: Optional[TessellatedMesh] = None
        if generate_tessellation:
            tessellation = GeometryEngine.tessellate_shape(shape)

        return CADModel(
            id=model_id,
            name=model_name,
            units=Unit.MILLIMETER,
            solids=[solid],
            faces=cad_faces,
            bbox=bbox_3d,
            total_volume=total_vol,
            total_area=total_area,
            source=source_ref,
            tessellation=tessellation,
            metadata=metadata or {},
        )

    def load_from_bytes(
        self,
        data: bytes,
        model_name: str = "Imported STEP",
        metadata: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> CADModel:
        """Parse raw STEP byte buffer into CADModel."""
        shape = self._parse_step_bytes(data)
        uid = model_id or str(uuid.uuid4())
        source_type = SourceType.STEP
        if metadata and metadata.get("source_type"):
            try:
                source_type = SourceType(metadata["source_type"])
            except ValueError:
                pass

        source_ref = SourceReference(
            source_type=source_type,
            source_id=metadata.get("source_id") if metadata else None,
            filename=metadata.get("filename") if metadata else None,
            metadata=metadata or {},
        )
        return self._build_cad_model_from_shape(
            shape=shape,
            model_id=uid,
            model_name=model_name,
            source_ref=source_ref,
            metadata=metadata,
        )

    def load_from_file(
        self,
        file_path: str,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
    ) -> CADModel:
        """Parse STEP file from disk into CADModel."""
        shape = self._parse_step_file(file_path)
        uid = model_id or str(uuid.uuid4())
        name = model_name or os.path.splitext(os.path.basename(file_path))[0]
        source_ref = SourceReference(
            source_type=SourceType.STEP,
            filename=os.path.basename(file_path),
            metadata={"path": file_path, **(metadata or {})},
        )
        return self._build_cad_model_from_shape(
            shape=shape,
            model_id=uid,
            model_name=name,
            source_ref=source_ref,
            metadata=metadata,
        )

    def tessellate(
        self,
        cad_model: CADModel,
        linear_deflection: float = 0.1,
        angular_deflection: float = 0.1,
    ) -> TessellatedMesh:
        """Generate/refresh triangulated mesh tessellation for the given model."""
        shape = self.get_shape(cad_model.id)
        if shape is None:
            raise ValueError(f"Shape for model {cad_model.id} is not cached")
        tess = GeometryEngine.tessellate_shape(
            shape,
            linear_deflection=linear_deflection,
            angular_deflection=angular_deflection,
        )
        cad_model.tessellation = tess
        return tess
