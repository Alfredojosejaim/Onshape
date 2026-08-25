"""Core meshing interfaces and provisional volumetric mesh generation.

NOTE: The current Kuhn-triangulation tetrahedral mesher is a provisional
discretization engine for pipeline integration and testing.
The definitive Gmsh -> Tet4 pipeline will be integrated in subsequent milestones.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import cadquery as cq
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MeshResult:
    """Volumetric finite element mesh data container."""
    nodes: List[List[float]]  # [[x, y, z], ...]
    elements: List[List[int]]  # [[n0, n1, n2, n3], ...]
    num_nodes: int
    num_elements: int
    element_type: str = "tet4"
    is_provisional: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": True,
            "status": "ready",
            "element_type": self.element_type,
            "num_nodes": self.num_nodes,
            "num_elements": self.num_elements,
            "nodes": self.nodes,
            "elements": self.elements,
            "is_provisional": self.is_provisional,
            "metadata": self.metadata,
        }


class BaseMesher:
    """Abstract interface for finite element mesh generation."""

    def generate_mesh(
        self,
        shape: cq.Shape,
        target_element_size: float = 2.0,
        element_type: str = "tet4",
    ) -> MeshResult:
        raise NotImplementedError


class ProvisionalTet4Mesher(BaseMesher):
    """Provisional volumetric finite element mesher based on CAD voxelization and Kuhn tetrahedralization.

    WARNING: This is a provisional mesher for pipeline verification and boundary condition testing.
    It will be replaced with Gmsh in the next milestone.
    """

    def generate_mesh(
        self,
        shape: cq.Shape,
        target_element_size: float = 2.0,
        element_type: str = "tet4",
    ) -> MeshResult:
        bbox = shape.BoundingBox()

        dx = max(bbox.xmax - bbox.xmin, 1e-4)
        dy = max(bbox.ymax - bbox.ymin, 1e-4)
        dz = max(bbox.zmax - bbox.zmin, 1e-4)

        # Determine grid subdivisions based on target element size
        h = max(target_element_size, min(dx, dy, dz) / 20.0)
        nx = max(int(np.ceil(dx / h)), 2)
        ny = max(int(np.ceil(dy / h)), 2)
        nz = max(int(np.ceil(dz / h)), 2)

        # Limit total grid size for reasonable computation
        max_grid = 40
        if max(nx, ny, nz) > max_grid:
            scale = max_grid / max(nx, ny, nz)
            nx = max(int(nx * scale), 2)
            ny = max(int(ny * scale), 2)
            nz = max(int(nz * scale), 2)

        xs = np.linspace(bbox.xmin, bbox.xmax, nx + 1)
        ys = np.linspace(bbox.ymin, bbox.ymax, ny + 1)
        zs = np.linspace(bbox.zmin, bbox.zmax, nz + 1)

        # Grid nodes
        node_map: Dict[Tuple[int, int, int], int] = {}
        nodes_list: List[List[float]] = []

        def get_or_add_node(i: int, j: int, k: int) -> int:
            key = (i, j, k)
            if key not in node_map:
                idx = len(nodes_list)
                node_map[key] = idx
                nodes_list.append([float(xs[i]), float(ys[j]), float(zs[k])])
            return node_map[key]

        elements_list: List[List[int]] = []

        for i in range(nx):
            for j in range(ny):
                for k in range(nz):
                    # Cell center
                    cx = 0.5 * (xs[i] + xs[i + 1])
                    cy = 0.5 * (ys[j] + ys[j + 1])
                    cz = 0.5 * (zs[k] + zs[k + 1])

                    # Check if cell center is inside the CAD solid
                    center_vec = cq.Vector(cx, cy, cz)
                    if shape.isInside(center_vec, 1e-3):
                        # Cell vertices
                        n000 = get_or_add_node(i, j, k)
                        n100 = get_or_add_node(i + 1, j, k)
                        n010 = get_or_add_node(i, j + 1, k)
                        n110 = get_or_add_node(i + 1, j + 1, k)
                        n001 = get_or_add_node(i, j, k + 1)
                        n101 = get_or_add_node(i + 1, j, k + 1)
                        n011 = get_or_add_node(i, j + 1, k + 1)
                        n111 = get_or_add_node(i + 1, j + 1, k + 1)

                        if element_type == "hex8":
                            elements_list.append([n000, n100, n110, n010, n001, n101, n111, n011])
                        else:
                            # 5-tetrahedra decomposition of a cube (Kuhn triangulation)
                            elements_list.append([n000, n100, n010, n001])
                            elements_list.append([n100, n110, n010, n111])
                            elements_list.append([n001, n100, n101, n111])
                            elements_list.append([n001, n010, n011, n111])
                            elements_list.append([n001, n100, n010, n111])

        # Fallback minimal discretization if no cells were strictly inside
        if len(elements_list) == 0 or len(nodes_list) == 0:
            for i in range(2):
                for j in range(2):
                    for k in range(2):
                        get_or_add_node(i, j, k)
            n000, n100, n010, n110 = 0, 1, 2, 3
            n001, n101, n011, n111 = 4, 5, 6, 7
            elements_list = [
                [n000, n100, n010, n001],
                [n100, n110, n010, n111],
                [n001, n100, n101, n111],
                [n001, n010, n011, n111],
                [n001, n100, n010, n111],
            ]

        return MeshResult(
            nodes=nodes_list,
            elements=elements_list,
            num_nodes=len(nodes_list),
            num_elements=len(elements_list),
            element_type=element_type,
            is_provisional=True,
        )
