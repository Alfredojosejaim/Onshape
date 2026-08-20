"""Onshape geometry adapter.

The adapter downloads real STEP/properties data.  Meshing and STEP
reconstruction are deliberately explicit integration points: this MVP does
not claim to perform FEA preprocessing without a configured real mesher.
"""

import logging
from typing import Any, Callable, Dict, Optional

import numpy as np
import requests

logger = logging.getLogger(__name__)


class GeometryProcessor:
    """Download Onshape geometry and delegate meshing to an external adapter."""

    def __init__(
        self,
        onshape_session: requests.Session,
        did: str,
        wid: str,
        eid: str,
        mesher: Optional[Callable[..., Any]] = None,
    ):
        self.session = onshape_session
        self.did = did
        self.wid = wid
        self.eid = eid
        self.base_url = "https://cad.onshape.com/api"
        self.mesher = mesher
        self.last_download_error_code: Optional[str] = None

    @staticmethod
    def _http_error_code(status_code: int) -> str:
        return {
            401: "ONSHAPE_UNAUTHORIZED",
            403: "ONSHAPE_FORBIDDEN",
            404: "ONSHAPE_NOT_FOUND",
            429: "ONSHAPE_RATE_LIMITED",
        }.get(status_code, "ONSHAPE_HTTP_ERROR")

    def download_part_studio(self, output_format: str = "step") -> Optional[bytes]:
        """Download a real Part Studio export from Onshape."""
        try:
            url = (
                f"{self.base_url}/partstudios/d/{self.did}/w/{self.wid}"
                f"/e/{self.eid}/export"
            )
            response = self.session.get(
                url,
                params={"formatName": output_format.upper(), "version": "latest"},
                timeout=30,
            )
            if response.status_code == 200:
                logger.info("Part Studio export downloaded (%d bytes)", len(response.content))
                return response.content
            self.last_download_error_code = self._http_error_code(response.status_code)
            logger.warning(
                "Part Studio export failed: %s",
                self.last_download_error_code,
            )
        except requests.RequestException:
            self.last_download_error_code = "ONSHAPE_REQUEST_FAILED"
            logger.exception("Part Studio export request failed")
        return None

    def get_part_properties(self) -> Dict[str, Any]:
        """Get properties from Onshape without exposing response contents."""
        try:
            url = (
                f"{self.base_url}/partstudios/d/{self.did}/w/{self.wid}"
                f"/e/{self.eid}/properties"
            )
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                logger.warning(
                    "Part properties failed: %s",
                    self._http_error_code(response.status_code),
                )
                return {}
            data = response.json()
            return {
                key: data.get(key)
                for key in ("volume", "area", "mass", "centroid", "bounds")
                if key in data
            }
        except (requests.RequestException, ValueError):
            logger.exception("Part properties request failed")
            return {}

    def create_mesh(
        self,
        step_data: bytes,
        target_element_size: float = 1.0,
        element_type: str = "tet10",
    ) -> Dict[str, Any]:
        """Create a mesh with a configured real mesher.

        No mesh is fabricated when no mesher is configured.  A caller can
        inject a mesher callable with signature ``(step, size, element_type)``
        that returns ``(nodes, elements)``.
        """
        if not step_data:
            return {
                "success": False,
                "status": "failed",
                "stage": "meshing",
                "code": "STEP_DATA_REQUIRED",
                "message": "STEP data is required before meshing",
            }
        if self.mesher is None:
            return {
                "success": False,
                "status": "pending",
                "stage": "meshing",
                "code": "MESHER_REQUIRED",
                "message": "A real mesh adapter is required; no mesh was generated",
            }
        try:
            nodes, elements = self.mesher(step_data, target_element_size, element_type)
            nodes = np.asarray(nodes)
            elements = np.asarray(elements)
            if nodes.ndim != 2 or elements.ndim != 2 or not len(nodes) or not len(elements):
                raise ValueError("mesher returned empty or invalid arrays")
            return {
                "success": True,
                "status": "ready",
                "nodes": nodes,
                "elements": elements,
                "num_nodes": len(nodes),
                "num_elements": len(elements),
            }
        except Exception:
            logger.exception("Configured mesh adapter failed")
            return {
                "success": False,
                "status": "failed",
                "stage": "meshing",
                "code": "MESHER_FAILED",
                "message": "Configured mesh adapter failed",
            }

    def identify_boundary_conditions(
        self, nodes: np.ndarray, anchor_faces: list, load_faces: Optional[list] = None
    ) -> Dict[str, Any]:
        """Require a real face-to-mesh mapping instead of guessing nodes."""
        if not anchor_faces or not load_faces:
            return {
                "success": False,
                "status": "pending",
                "stage": "boundary_conditions",
                "code": "BOUNDARY_MAPPING_REQUIRED",
                "message": "Onshape face references must be mapped to mesh nodes",
            }
        return {
            "success": False,
            "status": "not_implemented",
            "stage": "boundary_conditions",
            "code": "BOUNDARY_MAPPING_NOT_IMPLEMENTED",
            "message": "Face-to-mesh boundary mapping requires external integration",
        }

    def reconstruct_step_from_densities(
        self,
        densities: np.ndarray,
        nodes: np.ndarray,
        elements: np.ndarray,
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """Report the missing real CAD reconstruction adapter."""
        return {
            "success": False,
            "status": "not_implemented",
            "stage": "reconstruction",
            "code": "STEP_RECONSTRUCTOR_REQUIRED",
            "message": "No STEP reconstruction adapter is configured; no dummy STEP returned",
        }

    def process_full_pipeline(
        self, target_element_size: float = 1.0, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Download geometry and stop explicitly at unavailable critical stages."""
        step_data = self.download_part_studio()
        if not step_data:
            return {
                "success": False,
                "status": "failed",
                "stage": "download",
                "code": self.last_download_error_code or "STEP_DOWNLOAD_FAILED",
                "error": "No se pudo descargar Part Studio",
            }

        properties = self.get_part_properties()
        if output_file:
            with open(output_file, "wb") as output:
                output.write(step_data)

        mesh_result = self.create_mesh(step_data, target_element_size)
        if not mesh_result["success"]:
            return {
                "success": False,
                "status": mesh_result["status"],
                "stage": mesh_result["stage"],
                "code": mesh_result["code"],
                "error": mesh_result["message"],
                "properties": properties,
                "step_size": len(step_data),
            }

        bcs = self.identify_boundary_conditions(mesh_result["nodes"], [], [])
        if not bcs.get("success"):
            return {
                "success": False,
                "status": bcs["status"],
                "stage": bcs["stage"],
                "code": bcs["code"],
                "error": bcs["message"],
                "properties": properties,
                "mesh": {
                    "num_nodes": mesh_result["num_nodes"],
                    "num_elements": mesh_result["num_elements"],
                },
            }

        return {
            "success": True,
            "status": "ready",
            "properties": properties,
            "mesh": {
                "nodes": mesh_result["nodes"],
                "elements": mesh_result["elements"],
                "num_nodes": mesh_result["num_nodes"],
                "num_elements": mesh_result["num_elements"],
            },
            "boundary_conditions": bcs,
        }
