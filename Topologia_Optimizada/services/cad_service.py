"""CAD Service - Application-level CAD model management.

This service handles CAD model import, validation, tessellation, and meshing
without any dependency on external CAD platforms. It works with local STEP files.
"""

import logging
import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional

from adapters.cad.step_adapter import StepAdapter
from core.geometry import GeometryEngine
from core.meshing import ProvisionalTet4Mesher, MeshResult
from core.boundary import BoundaryConditionMapper
from core.models import CADModel, SourceType, SourceReference
import cadquery as cq

logger = logging.getLogger(__name__)


class CADService:
    """Application service for CAD model operations."""

    def __init__(self):
        self.step_adapter = StepAdapter()
        self.provisional_mesher = ProvisionalTet4Mesher()
        self._model_cache: Dict[str, tuple[CADModel, cq.Shape]] = {}

    def import_step_from_bytes(
        self,
        step_data: bytes,
        model_name: str = "Imported STEP",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CADModel:
        """Import CAD model from STEP byte data (standalone, no Onshape required)."""
        model_id = str(uuid.uuid4())
        source_ref = SourceReference(
            source_type=SourceType.STEP,
            filename=metadata.get("filename") if metadata else None,
            metadata=metadata or {},
        )
        cad_model = self.step_adapter.load_from_bytes(
            step_data,
            model_name=model_name,
            metadata=metadata,
            model_id=model_id,
        )
        cad_model.source = source_ref

        # Cache the model and its shape for later operations
        shape = self.step_adapter.get_shape(model_id)
        if shape:
            self._model_cache[model_id] = (cad_model, shape)

        logger.info("Imported STEP model: %s (ID: %s)", model_name, model_id)
        return cad_model

    def import_step_from_file(
        self,
        file_path: str,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CADModel:
        """Import CAD model from STEP file (standalone, no Onshape required)."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"STEP file not found: {file_path}")

        with open(file_path, "rb") as f:
            step_data = f.read()

        file_metadata = metadata or {}
        file_metadata["filename"] = os.path.basename(file_path)
        file_metadata["path"] = file_path

        return self.import_step_from_bytes(
            step_data,
            model_name=model_name or os.path.splitext(os.path.basename(file_path))[0],
            metadata=file_metadata,
        )

    def get_model(self, model_id: str) -> Optional[CADModel]:
        """Retrieve a cached CAD model by ID."""
        if model_id in self._model_cache:
            return self._model_cache[model_id][0]
        return None

    def get_model_shape(self, model_id: str) -> Optional[cq.Shape]:
        """Retrieve the cached CadQuery Shape for a model."""
        if model_id in self._model_cache:
            return self._model_cache[model_id][1]
        return None

    def tessellate_model(
        self,
        model_id: str,
        linear_deflection: float = 0.1,
        angular_deflection: float = 0.1,
    ) -> Dict[str, Any]:
        """Generate triangular tessellation for 3D visualization."""
        cad_model = self.get_model(model_id)
        if not cad_model:
            return {
                "success": False,
                "status": "failed",
                "code": "MODEL_NOT_FOUND",
                "error": f"Model {model_id} not found in cache",
            }

        try:
            tessellation = self.step_adapter.tessellate(
                cad_model,
                linear_deflection=linear_deflection,
                angular_deflection=angular_deflection,
            )
            cad_model.tessellation = tessellation
            return tessellation.to_dict()
        except Exception as exc:
            logger.exception("Tessellation failed for model %s", model_id)
            return {
                "success": False,
                "status": "failed",
                "code": "TESSELLATION_FAILED",
                "error": str(exc),
            }

    def generate_mesh(
        self,
        model_id: str,
        target_element_size: float = 2.0,
        element_type: str = "tet4",
    ) -> Dict[str, Any]:
        """Generate volumetric finite element mesh from CAD model."""
        shape = self.get_model_shape(model_id)
        if not shape:
            return {
                "success": False,
                "status": "failed",
                "code": "MODEL_NOT_FOUND",
                "error": f"Model {model_id} not found in cache",
            }

        try:
            mesh_result = self.provisional_mesher.generate_mesh(
                shape,
                target_element_size=target_element_size,
                element_type=element_type,
            )
            logger.info(
                "Generated mesh for model %s: %d nodes, %d elements",
                model_id,
                mesh_result.num_nodes,
                mesh_result.num_elements,
            )
            return mesh_result.to_dict()
        except Exception as exc:
            logger.exception("Mesh generation failed for model %s", model_id)
            return {
                "success": False,
                "status": "failed",
                "code": "MESHING_FAILED",
                "error": str(exc),
            }

    def map_boundary_conditions(
        self,
        model_id: str,
        nodes: List[List[float]],
        face_indices: Optional[List[int]] = None,
        tolerance: float = 0.5,
    ) -> Dict[str, Any]:
        """Map CAD faces to FEM mesh nodes for boundary conditions."""
        shape = self.get_model_shape(model_id)
        if not shape:
            return {
                "success": False,
                "status": "failed",
                "code": "MODEL_NOT_FOUND",
                "error": f"Model {model_id} not found in cache",
            }

        try:
            mapped_faces = BoundaryConditionMapper.map_faces_to_nodes(
                shape,
                nodes,
                face_indices=face_indices,
                tolerance=tolerance,
            )
            return {
                "success": True,
                "status": "ready",
                "mapped_faces": [f.to_dict() for f in mapped_faces],
            }
        except Exception as exc:
            logger.exception("Boundary condition mapping failed for model %s", model_id)
            return {
                "success": False,
                "status": "failed",
                "code": "BOUNDARY_MAPPING_FAILED",
                "error": str(exc),
            }

    def clear_cache(self, model_id: Optional[str] = None) -> None:
        """Clear cached models. If model_id is provided, only clear that model."""
        if model_id:
            if model_id in self._model_cache:
                del self._model_cache[model_id]
                logger.info("Cleared cache for model %s", model_id)
        else:
            self._model_cache.clear()
            logger.info("Cleared all model cache")