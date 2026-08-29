"""Advanced geometric selection engine for FEM mesh nodes and CAD geometry.

Declarative, CAD-agnostic selection of **mesh nodes** (0-based indices into a
``nodes`` array) and of **geometric entities** (CAD faces) using rich criteria:

* arbitrary planes (a point on the plane plus a normal),
* axis-aligned boxes,
* spheres,
* cylinders (axis + radius + bounded height),
* CAD B-Rep faces (exact, via :class:`BoundaryConditionMapper`),
* automatic face matching by normal orientation (e.g. "the Z- faces"),
* boolean composition of any of the above (union / intersection / exclusion).

Regions are described with JSON-compatible dicts so they can travel through the
API / the UI / study persistence exactly as :class:`ConstraintDefinition` and
:class:`LoadDefinition` do (the ``GeometryReference.geometry`` contract of
``api_server.py``).

The engine does NOT depend on a CAD platform: face-based regions only need an
optional CadQuery/OpenCASCADE ``Shape`` (provided by the STEP adapter).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Region models
# --------------------------------------------------------------------------- #

class RegionType:
    """Registry of supported geometric region types (matches ``geometry.type``)."""

    ALL = "all"
    PLANE = "plane"
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    FACE = "face"
    NORMAL = "normal"
    COMPOSITION = "composition"

    SUPPORTED = {ALL, PLANE, BOX, SPHERE, CYLINDER, FACE, NORMAL, COMPOSITION}


@dataclass
class PlaneRegion:
    """Nodes within ``tolerance`` of the plane defined by ``point`` and ``normal``."""
    point: Tuple[float, float, float]
    normal: Tuple[float, float, float]
    tolerance: float = 0.01

    def contains(self, p: np.ndarray) -> bool:
        n = _normalize(self.normal)
        d = float(np.dot(p - np.asarray(self.point, dtype=float), n))
        return abs(d) <= self.tolerance

    def to_dict(self) -> Dict[str, Any]:
        return {"type": RegionType.PLANE, "point": list(self.point),
                "normal": list(self.normal), "tolerance": float(self.tolerance)}


@dataclass
class BoxRegion:
    """Nodes inside an (inflated) axis-aligned box."""
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float
    tolerance: float = 0.0

    def contains(self, p: np.ndarray) -> bool:
        return bool(
            (self.xmin - self.tolerance <= p[0] <= self.xmax + self.tolerance)
            and (self.ymin - self.tolerance <= p[1] <= self.ymax + self.tolerance)
            and (self.zmin - self.tolerance <= p[2] <= self.zmax + self.tolerance)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": RegionType.BOX,
            "bbox": {"xmin": self.xmin, "xmax": self.xmax, "ymin": self.ymin,
                     "ymax": self.ymax, "zmin": self.zmin, "zmax": self.zmax},
            "tolerance": float(self.tolerance),
        }


@dataclass
class SphereRegion:
    """Nodes inside a sphere (radius inflated by ``tolerance``)."""
    center: Tuple[float, float, float]
    radius: float
    tolerance: float = 0.0

    def contains(self, p: np.ndarray) -> bool:
        return float(np.linalg.norm(p - np.asarray(self.center, dtype=float))) <= self.radius + self.tolerance

    def to_dict(self) -> Dict[str, Any]:
        return {"type": RegionType.SPHERE, "center": list(self.center),
                "radius": float(self.radius), "tolerance": float(self.tolerance)}


@dataclass
class CylinderRegion:
    """Nodes inside a (optionally height-bounded) cylinder.

    ``point`` is any point on the axis and ``axis`` its direction. When ``height``
    is ``None`` the cylinder is unbounded along the axis. ``tolerance`` is added
    both radially and axially.
    """
    point: Tuple[float, float, float]
    axis: Tuple[float, float, float]
    radius: float
    height: Optional[float] = None
    tolerance: float = 0.0

    def contains(self, p: np.ndarray) -> bool:
        n = _normalize(self.axis)
        origin = np.asarray(self.point, dtype=float)
        rel = p - origin
        t_axial = float(np.dot(rel, n))
        radial = float(np.linalg.norm(rel - t_axial * n))
        if radial > self.radius + self.tolerance:
            return False
        if self.height is not None:
            if not (-self.tolerance <= t_axial <= self.height + self.tolerance):
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {"type": RegionType.CYLINDER, "point": list(self.point),
                "axis": list(self.axis), "radius": float(self.radius),
                "height": self.height, "tolerance": float(self.tolerance)}


@dataclass
class FaceRegion:
    """Exact CAD B-Rep faces -> the mesh nodes lying on those faces.

    Requires a ``cad_shape`` (CadQuery Shape) to map faces to nodes.
    """
    face_indices: List[int]
    tolerance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {"type": RegionType.FACE, "face_indices": list(self.face_indices),
                "tolerance": float(self.tolerance)}


@dataclass
class NormalRegion:
    """Auto-match CAD faces whose (outward) reference normal points within
    ``angle_tolerance_deg`` of ``normal``, then select the nodes on those faces.

    Requires a ``cad_shape``.
    """
    normal: Tuple[float, float, float]
    angle_tolerance_deg: float = 15.0
    tolerance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {"type": RegionType.NORMAL, "normal": list(self.normal),
                "angle_tolerance_deg": float(self.angle_tolerance_deg),
                "tolerance": float(self.tolerance)}


@dataclass
class AllRegion:
    """Every mesh node (useful in compositions)."""

    def to_dict(self) -> Dict[str, Any]:
        return {"type": RegionType.ALL}


@dataclass
class CompositionRegion:
    """Boolean combination of sub-regions."""
    operator: str  # union | intersection | exclusion
    regions: List["GeometricRegion"] = field(default_factory=list)
    cad_shape: Any = None
    tolerance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"type": RegionType.COMPOSITION, "operator": self.operator,
                "regions": [r.to_dict() for r in self.regions]}


GeometricRegion = Union[
    PlaneRegion, BoxRegion, SphereRegion, CylinderRegion,
    FaceRegion, NormalRegion, AllRegion, CompositionRegion,
]


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def _normalize(v) -> np.ndarray:
    arr = np.asarray(v, dtype=float)
    norm = float(np.linalg.norm(arr))
    if norm < 1e-12:
        raise ValueError("direction vector cannot be zero")
    return arr / norm


def parse_region(desc: Any, cad_shape: Any = None) -> GeometricRegion:
    """Parse a JSON-compatible region descriptor into a region object.

    Accepts both plain dicts (API/UI contract) and already-constructed regions.
    ``cad_shape`` is attached to face/normal regions for node resolution.

    Raises:
        ValueError: on an unsupported or malformed descriptor.
    """
    if isinstance(desc, (PlaneRegion, BoxRegion, SphereRegion, CylinderRegion,
                         FaceRegion, NormalRegion, AllRegion, CompositionRegion)):
        return desc

    if not isinstance(desc, dict):
        raise ValueError(f"Invalid region descriptor: {desc!r}")

    # Shortcut: a bare boolean descriptor {"operator": ..., "regions": [...]} is
    # a composition without requiring an explicit "type" field.
    if "operator" in desc and "regions" in desc and "type" not in desc:
        return parse_region({**desc, "type": RegionType.COMPOSITION}, cad_shape=cad_shape)

    rtype = str(desc.get("type", "")).lower()
    if rtype == RegionType.ALL:
        return AllRegion()
    if rtype == RegionType.PLANE:
        return PlaneRegion(
            point=tuple(desc["point"]),
            normal=tuple(desc["normal"]),
            tolerance=float(desc.get("tolerance", 0.01)),
        )
    if rtype == RegionType.BOX:
        bbox = desc["bbox"]
        return BoxRegion(
            xmin=float(bbox["xmin"]), xmax=float(bbox["xmax"]),
            ymin=float(bbox["ymin"]), ymax=float(bbox["ymax"]),
            zmin=float(bbox["zmin"]), zmax=float(bbox["zmax"]),
            tolerance=float(desc.get("tolerance", 0.0)),
        )
    if rtype == RegionType.SPHERE:
        return SphereRegion(
            center=tuple(desc["center"]),
            radius=float(desc["radius"]),
            tolerance=float(desc.get("tolerance", 0.0)),
        )
    if rtype == RegionType.CYLINDER:
        height = desc.get("height")
        return CylinderRegion(
            point=tuple(desc["point"]),
            axis=tuple(desc["axis"]),
            radius=float(desc["radius"]),
            height=float(height) if height is not None else None,
            tolerance=float(desc.get("tolerance", 0.0)),
        )
    if rtype == RegionType.FACE:
        return FaceRegion(
            face_indices=[int(i) for i in desc["face_indices"]],
            tolerance=float(desc.get("tolerance", 0.5)),
        )
    if rtype == RegionType.NORMAL:
        return NormalRegion(
            normal=tuple(desc["normal"]),
            angle_tolerance_deg=float(desc.get("angle_tolerance_deg", 15.0)),
            tolerance=float(desc.get("tolerance", 0.5)),
        )
    if rtype == RegionType.COMPOSITION:
        operator = str(desc.get("operator", "union")).lower()
        if operator not in ("union", "intersection", "exclusion"):
            raise ValueError(f"Unsupported operator '{operator}'")
        sub = [parse_region(r, cad_shape=cad_shape) for r in desc.get("regions", [])]
        if not sub:
            raise ValueError("composition region requires at least one sub-region")
        return CompositionRegion(operator=operator, regions=sub, cad_shape=cad_shape,
                                 tolerance=float(desc.get("tolerance", 0.0)))

    available = ", ".join(sorted(RegionType.SUPPORTED))
    raise ValueError(f"Unsupported region type '{rtype}'. Available: {available}")


# --------------------------------------------------------------------------- #
# Node selection engine
# --------------------------------------------------------------------------- #

class NodeSelectionEngine:
    """Selects 0-based mesh node indices using geometric regions."""

    @staticmethod
    def select_nodes(
        nodes: Any,
        selection: Any,
        cad_shape: Any = None,
        default_tolerance: Optional[float] = None,
    ) -> List[int]:
        """Resolve a selection (single region or composition) to node indices.

        Args:
            nodes: (N, 3) coordinate array / list of lists.
            selection: region descriptor or composition descriptor.
            cad_shape: optional CadQuery Shape required by face-based regions.
            default_tolerance: tolerance applied to regions that do not define one.

        Returns:
            Sorted list of 0-based node indices.
        """
        if selection is None:
            raise ValueError("selection cannot be None")

        selection = _apply_default_tolerance(selection, default_tolerance)
        region = parse_region(selection, cad_shape=cad_shape)
        nodes_arr = np.asarray(nodes, dtype=float)
        if nodes_arr.ndim != 2 or nodes_arr.shape[1] != 3:
            raise ValueError(f"nodes must be (N, 3), got {nodes_arr.shape}")

        indices = NodeSelectionEngine._select_region(nodes_arr, region, cad_shape)
        indices.discard(-1)
        return sorted(indices)

    # -- internals ---------------------------------------------------------- #

    @staticmethod
    def _select_region(nodes: np.ndarray, region: GeometricRegion,
                       cad_shape: Any) -> set:
        if isinstance(region, AllRegion):
            return set(range(nodes.shape[0]))
        if isinstance(region, FaceRegion):
            return _map_faces_to_nodes(cad_shape, nodes, region.face_indices, region.tolerance)
        if isinstance(region, NormalRegion):
            face_indices = _match_faces_by_normal(cad_shape, region.normal,
                                                  region.angle_tolerance_deg)
            if not face_indices:
                return set()
            return _map_faces_to_nodes(cad_shape, nodes, face_indices, region.tolerance)
        if isinstance(region, CompositionRegion):
            return NodeSelectionEngine._compose(nodes, region, cad_shape)
        if isinstance(region, (PlaneRegion, BoxRegion, SphereRegion, CylinderRegion)):
            return {
                i for i in range(nodes.shape[0]) if region.contains(nodes[i])
            }
        raise ValueError(f"Unsupported region for selection: {region!r}")

    @staticmethod
    def _compose(nodes: np.ndarray, region: CompositionRegion, cad_shape: Any) -> set:
        sets = [NodeSelectionEngine._select_region(nodes, sub, cad_shape)
                for sub in region.regions]
        if not sets:
            return set()
        if region.operator == "union":
            return set().union(*sets)
        if region.operator == "intersection":
            return set.intersection(*sets)
        # exclusion: first minus the rest
        if len(sets) == 1:
            return sets[0]
        excluded = set().union(*sets[1:])
        return sets[0] - excluded

    # -- helpers ------------------------------------------------------------ #

    @staticmethod
    def box_from_bounds(bounds: Any, tolerance: float = 0.0) -> BoxRegion:
        """Build a BoxRegion from a BoundingBox3D-like object (xmin..zmax)."""
        return BoxRegion(
            xmin=float(bounds.xmin), xmax=float(bounds.xmax),
            ymin=float(bounds.ymin), ymax=float(bounds.ymax),
            zmin=float(bounds.zmin), zmax=float(bounds.zmax),
            tolerance=tolerance,
        )

    @staticmethod
    def plane(axis: int, value: float, tolerance: float = 0.01) -> PlaneRegion:
        """Convenience: a plane orthogonal to an axis (0=X, 1=Y, 2=Z)."""
        normal = [0.0, 0.0, 0.0]
        point = [0.0, 0.0, 0.0]
        normal[axis] = 1.0
        point[axis] = value
        return PlaneRegion(point=tuple(point), normal=tuple(normal), tolerance=tolerance)


def _apply_default_tolerance(selection: Any, default_tolerance: Optional[float]) -> Any:
    """Inject a default tolerance into point-based leaf regions that don't define one.

    Face-based regions (``face``/``normal``) keep their own documented default
    (0.5) because they need mapping to the CAD mesh, so the tight per-condition
    tolerance is never forced onto them.
    """
    point_based = {RegionType.PLANE, RegionType.BOX, RegionType.SPHERE, RegionType.CYLINDER}
    if default_tolerance is None or not isinstance(selection, dict):
        return selection
    if selection.get("tolerance") is not None:
        return selection
    clone = dict(selection)
    regions = clone.get("regions")
    if regions is not None:
        if isinstance(regions, list) and all(isinstance(r, dict) for r in regions):
            clone["regions"] = [
                r if r.get("tolerance") is not None or r.get("type") not in point_based
                else {**r, "tolerance": default_tolerance}
                for r in regions
            ]
        return clone
    if clone.get("type") in point_based:
        clone["tolerance"] = default_tolerance
    return clone


def _map_faces_to_nodes(cad_shape: Any, nodes: np.ndarray, face_indices: List[int],
                        tolerance: float) -> set:
    """Map a list of CAD face indices to node indices via BoundaryConditionMapper."""
    if cad_shape is None:
        logger.warning("Face-based region requires cad_shape; no nodes matched")
        return set()
    from core.boundary import BoundaryConditionMapper

    selected: set = set()
    for face_index in face_indices:
        try:
            mapped = BoundaryConditionMapper.map_faces_to_nodes(
                cad_shape, nodes.tolist(), face_indices=[face_index], tolerance=tolerance
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Face mapping failed for face %s: %s", face_index, exc)
            continue
        if mapped and mapped[0].node_indices:
            selected.update(mapped[0].node_indices)
    if not selected:
        logger.warning("No mesh nodes matched faces %s", face_indices)
    return selected


def _match_faces_by_normal(cad_shape: Any, normal: Tuple[float, float, float],
                           angle_tolerance_deg: float) -> List[int]:
    """Return B-Rep face indices whose reference normal ≈ target normal."""
    if cad_shape is None:
        logger.warning("normal-based region requires cad_shape; no faces matched")
        return []
    from core.geometry import _robust_face_reference_point

    n = _normalize(normal)
    max_angle = float(np.deg2rad(angle_tolerance_deg))
    matched: List[int] = []
    for idx, face in enumerate(cad_shape.Faces()):
        _center, f_normal = _robust_face_reference_point(face)
        if f_normal is None:
            continue
        fn = _normalize([f_normal.x, f_normal.y, f_normal.z])
        angle = float(np.arccos(np.clip(float(np.dot(fn, n)), -1.0, 1.0)))
        if angle <= max_angle:
            matched.append(idx)
    return matched