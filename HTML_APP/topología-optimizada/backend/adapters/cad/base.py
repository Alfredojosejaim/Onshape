"""Abstract base CAD adapter interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.models import CADModel, TessellatedMesh


class BaseCADAdapter(ABC):
    """Abstract interface for importing and exporting CAD formats to/from Core CADModel."""

    @abstractmethod
    def load_from_bytes(
        self,
        data: bytes,
        model_name: str = "Imported Model",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CADModel:
        """Parse raw CAD binary/text bytes into internal CADModel."""
        pass

    @abstractmethod
    def load_from_file(
        self,
        file_path: str,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CADModel:
        """Parse a CAD file from disk into internal CADModel."""
        pass

    @abstractmethod
    def tessellate(
        self,
        cad_model: CADModel,
        linear_deflection: float | None = None,
        angular_deflection: float | None = None,
    ) -> TessellatedMesh:
        """Generate triangular mesh tessellation for 3D visualization."""
        pass
