"""Agnostic internal CAD domain models for the Core.

These models represent CAD geometry, topology, units, and source metadata
without any dependency on specific CAD systems (such as Onshape).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Unit(str, Enum):
    MILLIMETER = "mm"
    METER = "m"
    CENTIMETER = "cm"
    INCH = "in"


class SourceType(str, Enum):
    STEP = "step"
    IGES = "iges"
    BREP = "brep"
    ONSHAPE = "onshape"
    UPLOAD = "upload"
    SYNTHETIC = "synthetic"


@dataclass
class BoundingBox3D:
    """Axis-aligned bounding box in 3D space."""
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float

    @property
    def dx(self) -> float:
        return self.xmax - self.xmin

    @property
    def dy(self) -> float:
        return self.ymax - self.ymin

    @property
    def dz(self) -> float:
        return self.zmax - self.zmin

    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            0.5 * (self.xmin + self.xmax),
            0.5 * (self.ymin + self.ymax),
            0.5 * (self.zmin + self.zmax),
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "xmin": float(self.xmin),
            "xmax": float(self.xmax),
            "ymin": float(self.ymin),
            "ymax": float(self.ymax),
            "zmin": float(self.zmin),
            "zmax": float(self.zmax),
        }


@dataclass
class CADVertex:
    """Internal representation of a topological vertex."""
    id: str
    x: float
    y: float
    z: float

    def to_list(self) -> List[float]:
        return [float(self.x), float(self.y), float(self.z)]


@dataclass
class CADEdge:
    """Internal representation of a topological edge."""
    id: str
    length: float
    start_vertex_id: Optional[str] = None
    end_vertex_id: Optional[str] = None


@dataclass
class CADFace:
    """Internal representation of a B-Rep face with geometric metadata."""
    id: str
    face_index: int
    area: float
    center: Tuple[float, float, float]
    normal: Tuple[float, float, float]
    bbox: BoundingBox3D
    surface_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "face_index": self.face_index,
            "area": float(self.area),
            "center": [float(c) for c in self.center],
            "normal": [float(n) for n in self.normal],
            "bbox": self.bbox.to_dict(),
            "surface_type": self.surface_type,
            "metadata": self.metadata,
        }


@dataclass
class CADSolid:
    """Internal representation of a 3D solid body."""
    id: str
    name: str
    volume: float
    bbox: BoundingBox3D
    faces: List[CADFace] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "volume": float(self.volume),
            "bbox": self.bbox.to_dict(),
            "faces_count": len(self.faces),
            "faces": [f.to_dict() for f in self.faces],
            "metadata": self.metadata,
        }


@dataclass
class SourceReference:
    """Provenance and origin tracking for CAD geometry."""
    source_type: SourceType
    source_id: Optional[str] = None
    filename: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "filename": self.filename,
            "metadata": self.metadata,
        }


@dataclass
class TessellatedMesh:
    """Triangulated surface representation for rendering (Three.js)."""
    vertices: List[float]  # [x0, y0, z0, x1, y1, z1, ...]
    indices: List[int]     # [t0_a, t0_b, t0_c, ...]
    num_vertices: int
    num_triangles: int
    normals: Optional[List[float]] = None
    faces_metadata: List[Dict[str, Any]] = field(default_factory=list)
    bbox: Optional[BoundingBox3D] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": "triangle_mesh",
            "num_vertices": self.num_vertices,
            "num_triangles": self.num_triangles,
            "vertices": self.vertices,
            "indices": self.indices,
            "normals": self.normals,
            "faces": self.faces_metadata,
            "bbox": self.bbox.to_dict() if self.bbox else None,
        }


@dataclass
class CADModel:
    """Agnostic root CAD model representation within the Core."""
    id: str
    name: str
    units: Unit = Unit.MILLIMETER
    solids: List[CADSolid] = field(default_factory=list)
    faces: List[CADFace] = field(default_factory=list)
    bbox: Optional[BoundingBox3D] = None
    total_volume: float = 0.0
    total_area: float = 0.0
    source: Optional[SourceReference] = None
    tessellation: Optional[TessellatedMesh] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "units": self.units.value,
            "total_volume": float(self.total_volume),
            "total_area": float(self.total_area),
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "solids_count": len(self.solids),
            "solids": [s.to_dict() for s in self.solids],
            "faces_count": len(self.faces),
            "faces": [f.to_dict() for f in self.faces],
            "source": self.source.to_dict() if self.source else None,
            "tessellation": self.tessellation.to_dict() if self.tessellation else None,
            "metadata": self.metadata,
        }
