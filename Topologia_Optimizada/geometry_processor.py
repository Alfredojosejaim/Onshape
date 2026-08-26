"""Geometry processor - Standalone CAD/FEM mesh adapter.

Provides:
1. B-Rep parsing and tessellation (triangles, vertices, normals, face metadata) for Three.js.
2. Volumetric finite element mesh generation (nodes and tetrahedral elements).
3. Geometric boundary condition mapping from CAD B-Rep faces to FEM mesh nodes.

This is a backward compatibility shim that delegates to the new services layer.
For new code, use services.cad_service.CADService directly.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

import cadquery as cq

from services.cad_service import CADService
from connectors.onshape.client import OnshapeAPIError, OnshapeClient

logger = logging.getLogger(__name__)


class GeometryProcessor:
    """Standalone geometry processor for CAD tessellation, meshing and face mapping.

    This class now provides backward compatibility while delegating to the new
    services layer. For Onshape-specific functionality, use connectors.onshape.service.
    """

    def __init__(
        self,
        onshape_session: Optional[OnshapeClient] = None,
        did: Optional[str] = None,
        wid: Optional[str] = None,
        eid: Optional[str] = None,
        mesher: Optional[Callable[..., Any]] = None,
    ):
        # Onshape-specific parameters (deprecated, for backward compatibility)
        self.session = onshape_session
        self.did = did
        self.wid = wid
        self.eid = eid
        self.base_url = "https://cad.onshape.com/api"
        self.mesher = mesher
        self.last_download_error_code: Optional[str] = None

        # New standalone service
        self.cad_service = CADService()

    # --- Onshape-specific methods (deprecated, use connectors.onshape.service) ---

    def get_parts_list(self) -> List[Dict[str, Any]]:
        """DEPRECATED: Use connectors.onshape.service.OnshapeService.get_parts_list instead."""
        if not self.session or not self.did or not self.wid or not self.eid:
            logger.warning("get_parts_list requires Onshape session and document IDs")
            return []

        from connectors.onshape.service import OnshapeService
        service = OnshapeService(self.session)
        return service.get_parts_list(self.did, self.wid, self.eid)

    def download_part_studio(
        self,
        output_format: str = "step",
        part_ids: Optional[List[str]] = None,
    ) -> Optional[bytes]:
        """DEPRECATED: Use connectors.onshape.service.OnshapeService.download_part_studio instead."""
        if not self.session or not self.did or not self.wid or not self.eid:
            self.last_download_error_code = "NO_ACTIVE_SESSION"
            return None

        from connectors.onshape.service import OnshapeService
        service = OnshapeService(self.session)
        return service.download_part_studio(self.did, self.wid, self.eid, output_format, part_ids)

    def get_part_properties(self) -> Dict[str, Any]:
        """DEPRECATED: Use connectors.onshape.service instead."""
        if not self.session or not self.did or not self.wid or not self.eid:
            return {}

        try:
            url = f"/partstudios/d/{self.did}/w/{self.wid}/e/{self.eid}/properties"
            response = self.session.request("GET", url, timeout=10)
            if response.status_code != 200:
                logger.warning("Part properties failed: HTTP %d", response.status_code)
                return {}
            data = response.json()
            return {
                key: data.get(key)
                for key in ("volume", "area", "mass", "centroid", "bounds")
                if key in data
            }
        except (OnshapeAPIError, ValueError):
            logger.exception("Part properties request failed")
            return {}

    # --- Standalone STEP processing methods (use services.cad_service instead) ---

    @staticmethod
    def load_shape_from_step(step_data: bytes) -> cq.Shape:
        """Parse STEP binary data into a CadQuery/OCP Shape."""
        import os
        import tempfile

        if not step_data or len(step_data) == 0:
            raise ValueError("STEP data is empty")
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            tmp.write(step_data)
            tmp_path = tmp.name
        try:
            imported = cq.importers.importStep(tmp_path)
            shape = imported.val()
            if shape is None or shape.isNull():
                raise ValueError("Could not parse valid 3D shape from STEP")
            return shape
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def tessellate_step(
        self,
        step_data: bytes,
        linear_deflection: float = 0.1,
        angular_deflection: float = 0.1,
    ) -> Dict[str, Any]:
        """Tessellate real STEP geometry into vertices, normals, and triangle indices for Three.js."""
        try:
            shape = self.load_shape_from_step(step_data)
            points, triangles = shape.tessellate(
                tolerance=linear_deflection,
                angularTolerance=angular_deflection,
            )

            vertices = []
            for p in points:
                vertices.extend([float(p.x), float(p.y), float(p.z)])

            indices = []
            for tri in triangles:
                indices.extend([int(tri[0]), int(tri[1]), int(tri[2])])

            # Extract per-face information for boundary condition identification
            faces_meta = []
            faces = shape.Faces()
            for idx, face in enumerate(faces):
                try:
                    center = face.Center()
                    normal = face.normalAt(center)
                    bbox = face.BoundingBox()
                    faces_meta.append({
                        "face_index": idx,
                        "area": float(face.Area()),
                        "center": [float(center.x), float(center.y), float(center.z)],
                        "normal": [float(normal.x), float(normal.y), float(normal.z)],
                        "bbox": {
                            "xmin": float(bbox.xmin), "xmax": float(bbox.xmax),
                            "ymin": float(bbox.ymin), "ymax": float(bbox.ymax),
                            "zmin": float(bbox.zmin), "zmax": float(bbox.zmax),
                        }
                    })
                except Exception as ex:
                    logger.debug("Failed to extract metadata for face %d: %s", idx, ex)

            bbox = shape.BoundingBox()

            return {
                "success": True,
                "status": "ready",
                "format": "triangle_mesh",
                "num_vertices": len(points),
                "num_triangles": len(triangles),
                "vertices": vertices,
                "indices": indices,
                "volume": float(shape.Volume()),
                "faces": faces_meta,
                "bbox": {
                    "xmin": float(bbox.xmin), "xmax": float(bbox.xmax),
                    "ymin": float(bbox.ymin), "ymax": float(bbox.ymax),
                    "zmin": float(bbox.zmin), "zmax": float(bbox.zmax),
                },
            }
        except Exception as exc:
            logger.exception("Tessellation of STEP failed")
            return {
                "success": False,
                "status": "failed",
                "code": "STEP_TESSELLATION_FAILED",
                "error": str(exc),
            }

    def create_mesh(
        self,
        step_data: bytes,
        target_element_size: float = 2.0,
        element_type: str = "tet4",
    ) -> Dict[str, Any]:
        """Generate a volumetric finite element mesh from STEP data."""
        if not step_data:
            return {
                "success": False,
                "status": "failed",
                "stage": "meshing",
                "code": "STEP_DATA_REQUIRED",
                "message": "STEP data is required before meshing",
            }

        # If a custom external mesher callable is provided, use it
        if self.mesher is not None:
            try:
                nodes, elements = self.mesher(step_data, target_element_size, element_type)
                import numpy as np
                nodes_arr = np.asarray(nodes, dtype=float)
                elements_arr = np.asarray(elements, dtype=int)
                return {
                    "success": True,
                    "status": "ready",
                    "nodes": nodes_arr.tolist(),
                    "elements": elements_arr.tolist(),
                    "num_nodes": len(nodes_arr),
                    "num_elements": len(elements_arr),
                    "element_type": element_type,
                }
            except Exception as exc:
                logger.exception("Custom mesher failed")
                return {
                    "success": False,
                    "status": "failed",
                    "code": "CUSTOM_MESHER_FAILED",
                    "error": str(exc),
                }

        # Import STEP to get a model, then use the CAD service
        try:
            cad_model = self.cad_service.import_step_from_bytes(
                step_data,
                model_name="Temp_for_meshing",
            )
            return self.cad_service.generate_mesh(
                cad_model.id,
                target_element_size=target_element_size,
                element_type=element_type,
            )
        except Exception as exc:
            logger.exception("Volumetric meshing failed")
            return {
                "success": False,
                "status": "failed",
                "stage": "meshing",
                "code": "MESHER_FAILED",
                "error": str(exc),
            }

    def identify_boundary_conditions(
        self,
        nodes: List[List[float]],
        step_data: bytes,
        face_indices: Optional[List[int]] = None,
        tolerance: float = 0.5,
    ) -> Dict[str, Any]:
        """Map CAD B-Rep faces to FEM mesh nodes using exact Euclidean distance."""
        try:
            cad_model = self.cad_service.import_step_from_bytes(
                step_data,
                model_name="Temp_for_boundary",
            )
            return self.cad_service.map_boundary_conditions(
                cad_model.id,
                nodes,
                face_indices=face_indices,
                tolerance=tolerance,
            )
        except Exception as exc:
            logger.exception("Boundary condition mapping failed")
            return {
                "success": False,
                "status": "failed",
                "code": "BOUNDARY_MAPPING_FAILED",
                "error": str(exc),
            }

    def reconstruct_step_from_densities(
        self,
        densities: Any,  # np.ndarray
        nodes: Any,  # np.ndarray
        elements: Any,  # np.ndarray
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Contract for CAD solid reconstruction (Hito 3)."""
        return {
            "success": False,
            "status": "not_implemented",
            "stage": "reconstruction",
            "code": "STEP_RECONSTRUCTOR_REQUIRED",
            "message": "CAD solid reconstruction from density field will be integrated in future phases",
        }