"""Onshape connector service.

This module provides high-level Onshape integration services.
This is part of the optional Onshape connector.
The standalone application works WITHOUT this connector.
"""

import logging
from typing import Any, Dict, List, Optional

from connectors.onshape.client import OnshapeAPIError, OnshapeClient
from adapters.cad.step_adapter import StepAdapter

logger = logging.getLogger(__name__)


class OnshapeService:
    """High-level Onshape integration service."""

    def __init__(self, onshape_client: OnshapeClient):
        self.client = onshape_client
        self.step_adapter = StepAdapter()

    def get_parts_list(self, document_id: str, workspace_id: str, element_id: str) -> List[Dict[str, Any]]:
        """Query Onshape REST API for the real list of parts in this Part Studio."""
        try:
            url = f"/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/parts"
            response = self.client.get_json(url)
            if isinstance(response, list):
                return response
            return []
        except Exception:
            logger.exception("Failed to get parts list from Onshape Part Studio")
            return []

    def download_part_studio(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        output_format: str = "step",
        part_ids: Optional[List[str]] = None,
    ) -> Optional[bytes]:
        """Download a real Part Studio STEP export from Onshape (full studio or specific part IDs)."""
        try:
            url = f"/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/export"
            params: Dict[str, str] = {
                "formatName": output_format.upper(),
                "version": "latest",
            }
            if part_ids:
                # Filter out empty or whitespace strings
                valid_ids = [p.strip() for p in part_ids if p and p.strip()]
                if valid_ids:
                    params["partIds"] = ",".join(valid_ids)

            response = self.client.request(
                "GET",
                url,
                params=params,
                timeout=30,
            )
            if response.status_code == 200:
                logger.info("Part Studio export downloaded (%d bytes)", len(response.content))
                return response.content
            return None
        except OnshapeAPIError as exc:
            logger.warning("Part Studio export failed: %s", exc.code)
            return None
        except Exception:
            logger.exception("Part Studio export request failed")
            return None

    def download_to_cad_model(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        part_ids: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """Download Onshape geometry and convert to Core CADModel."""
        step_data = self.download_part_studio(document_id, workspace_id, element_id, "step", part_ids)
        if not step_data:
            return None

        try:
            cad_model = self.step_adapter.load_from_bytes(
                step_data,
                model_name=f"Onshape_{document_id}_{element_id}",
                metadata={
                    "source_type": "onshape",
                    "source_id": f"{document_id}/{workspace_id}/{element_id}",
                    "document_id": document_id,
                    "workspace_id": workspace_id,
                    "element_id": element_id,
                }
            )
            return cad_model
        except Exception:
            logger.exception("Failed to convert Onshape STEP to CADModel")
            return None