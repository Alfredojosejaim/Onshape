"""Core meshing interfaces and volumetric mesh generation.

Two mesh generators are provided:

* :class:`GmshTet4Mesher` — the definitive volumetric mesh generator. It drives
  Gmsh's OpenCASCADE kernel to produce a conforming tetrahedral (Tet4) mesh
  anchored to the real CAD boundary from a STEP geometry. This is the
  recommended pipeline (same one validated end-to-end for the FEA flow).

* :class:`ProvisionalTet4Mesher` — a provisional voxelization + Kuhn
  triangulation fallback kept for boundary-condition pipeline testing and as a
  dependency-free alternative when Gmsh is unavailable. It is NOT the definitive
  mesh generator and its tetrahedra are not guaranteed conforming.
"""

from dataclasses import dataclass, field
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

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


class GmshTet4Mesher(BaseMesher):
    """Definitive volumetric Tet4 mesher driven by Gmsh (OpenCASCADE kernel).

    This is the recommended mesh generator. It produces a conforming,
    boundary-conforming tetrahedral (Tet4) mesh from real STEP geometry using
    Gmsh, following the exact pipeline that was validated end-to-end for the FEA
    flow (see ``RESUMEN_IMPLEMENTACION.md``).

    The primary entry point is :meth:`generate_mesh_from_step`, which meshes a
    STEP file directly. :meth:`generate_mesh` (the :class:`BaseMesher`
    interface) is also supported: it exports the given CAD shape to a temporary
    STEP file and delegates to :meth:`generate_mesh_from_step`, so the mesher is
    usable from a pure ``cq.Shape`` as well.

    The resulting :class:`MeshResult` is marked ``is_provisional=False``.
    """

    def __init__(self, mesh_size_max: float = 5.0, mesh_order: int = 1):
        self.mesh_size_max = mesh_size_max
        self.mesh_order = mesh_order

    def generate_mesh_from_step(
        self,
        step_file: str,
        target_element_size: Optional[float] = None,
        element_type: str = "tet4",
    ) -> MeshResult:
        """Generate a Tet4 volumetric mesh from a real STEP file via Gmsh.

        Args:
            step_file: Path to the STEP (.step/.stp) file to mesh.
            target_element_size: Optional characteristic target size. When
                provided it is applied as ``Mesh.CharacteristicLengthMin`` /
                ``Mesh.CharacteristicLengthMax``; otherwise Gmsh's default
                characteristic length (``self.mesh_size_max``) is used.
            element_type: Mesh element type. Only ``"tet4"`` is supported by this
                generator; any other value raises ``ValueError``.

        Returns:
            :class:`MeshResult` with real nodes/elements (``is_provisional=False``).

        Raises:
            ValueError: if the element type is not ``"tet4"`` or the input
                contains no solid/volume entities to mesh.
        """
        if not os.path.exists(step_file):
            raise FileNotFoundError(f"STEP file not found: {step_file}")
        if element_type != "tet4":
            raise ValueError(f"GmshTet4Mesher only supports element_type='tet4', got {element_type!r}")

        try:
            import gmsh
        except ImportError as e:  # pragma: no cover - depends on optional dependency
            raise RuntimeError(
                "gmsh is not installed. Install it with 'pip install gmsh' to use "
                "the definitive GmshTet4Mesher, or fall back to ProvisionalTet4Mesher."
            ) from e

        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add("topologia_optimizada_mesh")
            gmsh.option.setNumber("Geometry.OCCImportLabels", 1)

            imported = gmsh.model.occ.importShapes(step_file, format="step")
            gmsh.model.occ.synchronize()

            volumes = gmsh.model.getEntities(dim=3)
            if not volumes:
                raise ValueError(
                    f"STEP '{step_file}' contains no 3D solid/volume to mesh"
                )

            if target_element_size and target_element_size > 0:
                gmsh.option.setNumber("Mesh.CharacteristicLengthMin", float(target_element_size))
                gmsh.option.setNumber("Mesh.CharacteristicLengthMax", float(target_element_size))
            else:
                gmsh.option.setNumber("Mesh.CharacteristicLengthMax", float(self.mesh_size_max))

            gmsh.model.mesh.generate(3)

            _, node_coords, _ = gmsh.model.mesh.getNodes()
            nodes = [
                [node_coords[3 * i], node_coords[3 * i + 1], node_coords[3 * i + 2]]
                for i in range(len(node_coords) // 3)
            ]

            element_types = gmsh.model.mesh.getElementTypes()
            _, _, element_connectivity = gmsh.model.mesh.getElements()

            tet_connectivity = None
            for i, et in enumerate(element_types):
                if et == 4:  # Gmsh element type 4 == 4-node tetrahedron (Tet4)
                    tet_connectivity = element_connectivity[i]
                    break

            if tet_connectivity is None or len(tet_connectivity) == 0:
                raise ValueError(
                    f"Gmsh produced no Tet4 elements for '{step_file}'"
                )

            elements = (np.array(tet_connectivity).reshape(-1, 4) - 1).tolist()

            return MeshResult(
                nodes=nodes,
                elements=elements,
                num_nodes=len(nodes),
                num_elements=len(elements),
                element_type="tet4",
                is_provisional=False,
                metadata={
                    "mesher": "GmshTet4Mesher",
                    "step_file": os.path.basename(step_file),
                    "mesh_size_max": self.mesh_size_max,
                    "gmsh_volumes": len(volumes),
                },
            )
        finally:
            gmsh.finalize()

    def generate_adaptive_mesh(
        self,
        step_file: str,
        size_points: Optional[list] = None,
        base_size: float = 5.0,
        min_size: float = 0.5,
        element_type: str = "tet4",
        density: Optional[list] = None,
    ) -> MeshResult:
        """Generate a Tet4 mesh adaptively refined according to a scalar field.

        ``size_points`` is a list of ``[x, y, z, size]`` providing an element
        size at arbitrary 3D points.  A Gmsh "Distance" background field built
        around those points maps local distance to element size, giving smooth
        density-driven local refinement (dense/solid regions refine more).

        Falls back to a uniform mesh (base_size) if no refinement points and no
        gmsh field support are available.
        """
        if not os.path.exists(step_file):
            raise FileNotFoundError(f"STEP file not found: {step_file}")
        if element_type != "tet4":
            raise ValueError(f"GmshTet4Mesher only supports element_type='tet4', got {element_type!r}")
        try:
            import gmsh
        except ImportError as e:
            raise RuntimeError("gmsh is not installed.") from e

        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add("topologia_optimizada_mesh_adaptive")
            gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
            gmsh.model.occ.importShapes(step_file, format="step")
            gmsh.model.occ.synchronize()

            volumes = gmsh.model.getEntities(dim=3)
            if not volumes:
                raise ValueError(f"STEP '{step_file}' contains no 3D solid/volume to mesh")

            if size_points and len(size_points) >= 4:
                # Robust density-driven refinement using a Gmsh background
                # "Distance" field around the refinement points combined with a
                # "MathEval" size mapping and a "Min" clamp.  Works on all
                # Gmsh builds (unlike the PostView field).
                gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
                gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
                gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

                # Create the refinement points geometry.
                point_tags = []
                for p in size_points:
                    t = gmsh.model.occ.addPoint(
                        float(p[0]), float(p[1]), float(p[2]))
                    point_tags.append(t)
                gmsh.model.occ.synchronize()

                # Estimate the domain extent for the distance->size mapping.
                x0 = gmsh.model.getBoundingBox(-1, -1)
                import math as _math
                bb = x0  # (-1,-1) is the whole model bounding box
                extent = _math.sqrt(
                    (bb[3] - bb[0]) ** 2 + (bb[4] - bb[1]) ** 2 + (bb[5] - bb[2]) ** 2
                ) or base_size
                maxdist = max(extent, 1e-6)

                df = gmsh.model.mesh.field.add("Distance")
                gmsh.model.mesh.field.setNumbers(df, "PointsList", point_tags)
                gmsh.model.mesh.field.setNumber(df, "Sampling", 100)

                # size = min_size + (base_size - min_size) * (dist / maxdist)
                scale = max(base_size - min_size, 0.0)
                formula = f"{min_size:.6f} + {scale:.6f} * (F1 / {maxdist:.6f})"
                me = gmsh.model.mesh.field.add("MathEval")
                gmsh.model.mesh.field.setString(me, "F", formula)

                base = gmsh.model.mesh.field.add("MathEval")
                gmsh.model.mesh.field.setString(base, "F", f"{base_size:.6f}")

                small = gmsh.model.mesh.field.add("Min")
                gmsh.model.mesh.field.setNumbers(small, "FieldsList", [me, base])
                gmsh.model.mesh.field.setAsBackgroundMesh(small)
            else:
                gmsh.option.setNumber("Mesh.CharacteristicLengthMax", float(base_size))

            gmsh.model.mesh.generate(3)

            _, node_coords, _ = gmsh.model.mesh.getNodes()
            nodes = [
                [node_coords[3 * i], node_coords[3 * i + 1], node_coords[3 * i + 2]]
                for i in range(len(node_coords) // 3)
            ]
            element_types = gmsh.model.mesh.getElementTypes()
            _, _, element_connectivity = gmsh.model.mesh.getElements()
            tet_connectivity = None
            for i, et in enumerate(element_types):
                if et == 4:
                    tet_connectivity = element_connectivity[i]
                    break
            if tet_connectivity is None or len(tet_connectivity) == 0:
                raise ValueError(f"Gmsh produced no Tet4 elements for '{step_file}'")
            elements = (np.array(tet_connectivity).reshape(-1, 4) - 1).tolist()

            return MeshResult(
                nodes=nodes,
                elements=elements,
                num_nodes=len(nodes),
                num_elements=len(elements),
                element_type="tet4",
                is_provisional=False,
                metadata={
                    "mesher": "GmshTet4Mesher(adaptive)",
                    "mesh_size_max": base_size,
                    "min_size": min_size,
                    "adaptive": True,
                    "n_size_points": len(size_points) if size_points else 0,
                },
            )
        finally:
            gmsh.finalize()

    def generate_mesh(
        self,
        shape: cq.Shape,
        target_element_size: float = 2.0,
        element_type: str = "tet4",
    ) -> MeshResult:
        """Mesh a CAD shape by exporting it to a temporary STEP file first.

        Keeps the uniform :class:`BaseMesher` interface while delegating to the
        Gmsh pipeline. Raises ``ValueError`` if the shape is null/empty.
        """
        if shape is None or shape.isNull():
            raise ValueError("Cannot mesh a null/empty CAD shape")
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            cq.exporters.export(shape, tmp_path, exportType="STEP")
            return self.generate_mesh_from_step(
                tmp_path,
                target_element_size=target_element_size,
                element_type=element_type,
            )
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


class ProvisionalTet4Mesher(BaseMesher):
    """Provisional volumetric finite element mesher based on CAD voxelization and Kuhn tetrahedralization.

    WARNING: This is a provisional fallback mesher for pipeline verification and
    boundary condition testing. Its tetrahedra are NOT guaranteed conforming and
    may contain inverted elements. The definitive Gmsh -> Tet4 pipeline
    (:class:`GmshTet4Mesher`) is the recommended mesh generator.
    """

    def __init__(self, max_grid: int = 18):
        # ``max_grid`` caps the voxel grid per axis. A smaller value keeps the
        # (pure-Python, single-threaded) provisional FEA responsive: ~18^3 grid
        # yields a few thousand tets which the solver assembles + solves in under
        # a second, whereas the previous 40^3 default produced 50k+ elements and
        # multi-minute solves/optimizations.
        self.max_grid = max(2, int(max_grid))

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
        max_grid = self.max_grid
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
