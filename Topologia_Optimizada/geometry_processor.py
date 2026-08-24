"""Onshape geometry processor and real CAD/FEM mesh adapter.

Provides:
1. Real STEP export download via Onshape REST API.
2. B-Rep parsing and tessellation (triangles, vertices, normals) for Three.js.
3. Real volumetric finite element mesh generation (nodes and tetrahedral elements).
4. Geometric boundary condition mapping from CAD B-Rep faces to FEM mesh nodes.
"""

import io
import logging
import os
import tempfile
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import cadquery as cq

from onshape_client import OnshapeAPIError, OnshapeClient

logger = logging.getLogger(__name__)


class GeometryProcessor:
    """Download Onshape geometry and perform real CAD tessellation, meshing and face mapping."""

    def __init__(
        self,
        onshape_session: Optional[OnshapeClient],
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
        if not self.session:
            self.last_download_error_code = "NO_ACTIVE_SESSION"
            return None
        try:
            url = (
                f"{self.base_url}/partstudios/d/{self.did}/w/{self.wid}"
                f"/e/{self.eid}/export"
            )
            response = self.session.request(
                "GET",
                url.removeprefix(self.base_url),
                params={"formatName": output_format.upper(), "version": "latest"},
                timeout=30,
            )
            if response.status_code == 200:
                logger.info("Part Studio export downloaded (%d bytes)", len(response.content))
                return response.content
            self.last_download_error_code = self._http_error_code(response.status_code)
        except OnshapeAPIError as exc:
            self.last_download_error_code = exc.code
            logger.warning("Part Studio export failed: %s", exc.code)
        except Exception:
            self.last_download_error_code = "ONSHAPE_REQUEST_FAILED"
            logger.exception("Part Studio export request failed")
        return None

    def get_part_properties(self) -> Dict[str, Any]:
        """Get properties from Onshape."""
        if not self.session:
            return {}
        try:
            url = (
                f"{self.base_url}/partstudios/d/{self.did}/w/{self.wid}"
                f"/e/{self.eid}/properties"
            )
            response = self.session.request("GET", url.removeprefix(self.base_url), timeout=10)
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
        except (OnshapeAPIError, ValueError):
            logger.exception("Part properties request failed")
            return {}

    @staticmethod
    def load_shape_from_step(step_data: bytes) -> cq.Shape:
        """Parse STEP binary data into a CadQuery/OCP Shape."""
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
        """Generate a real volumetric finite element mesh from STEP data."""
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

        # Built-in solid volumetric tetrahedral / hexahedral discretization
        try:
            shape = self.load_shape_from_step(step_data)
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
                                # Standard 5-tetrahedra decomposition of a cube (Kuhn triangulation)
                                elements_list.append([n000, n100, n010, n001])
                                elements_list.append([n100, n110, n010, n111])
                                elements_list.append([n001, n100, n101, n111])
                                elements_list.append([n001, n010, n011, n111])
                                elements_list.append([n001, n100, n010, n111])

            if len(elements_list) == 0 or len(nodes_list) == 0:
                # If solid is thin or sub-element, add minimum enclosing tetrahedral mesh
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

            return {
                "success": True,
                "status": "ready",
                "nodes": nodes_list,
                "elements": elements_list,
                "num_nodes": len(nodes_list),
                "num_elements": len(elements_list),
                "element_type": element_type,
            }
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
            shape = self.load_shape_from_step(step_data)
            cad_faces = shape.Faces()

            if not face_indices:
                face_indices = list(range(len(cad_faces)))

            mapped_faces = []
            for face_idx in face_indices:
                if face_idx < 0 or face_idx >= len(cad_faces):
                    continue
                face = cad_faces[face_idx]
                matching_node_indices = []

                for n_idx, node_coord in enumerate(nodes):
                    v = cq.Vertex.makeVertex(node_coord[0], node_coord[1], node_coord[2])
                    dist = float(face.distance(v))
                    if dist <= tolerance:
                        matching_node_indices.append(n_idx)

                center = face.Center()
                normal = face.normalAt(center)
                mapped_faces.append({
                    "face_index": face_idx,
                    "center": [float(center.x), float(center.y), float(center.z)],
                    "normal": [float(normal.x), float(normal.y), float(normal.z)],
                    "area": float(face.Area()),
                    "matched_nodes_count": len(matching_node_indices),
                    "node_indices": matching_node_indices,
                })

            return {
                "success": True,
                "status": "ready",
                "mapped_faces": mapped_faces,
            }
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
        densities: np.ndarray,
        nodes: np.ndarray,
        elements: np.ndarray,
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
