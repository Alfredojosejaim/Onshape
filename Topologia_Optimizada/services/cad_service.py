"""CAD Service - Application-level CAD model management.

This service handles CAD model import, validation, tessellation, and meshing
without any dependency on external CAD platforms. It works with local STEP files.
"""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from adapters.cad.step_adapter import StepAdapter
from core.geometry import GeometryEngine
from core.meshing import GmshTet4Mesher, ProvisionalTet4Mesher, MeshResult
from core.boundary import BoundaryConditionMapper
from core.models import CADModel, SourceType, SourceReference
from core.commands import BooleanOperation
import cadquery as cq

logger = logging.getLogger(__name__)


class CADService:
    """Application service for CAD model operations."""

    def __init__(self):
        self.step_adapter = StepAdapter()
        self.gmsh_mesher = GmshTet4Mesher()
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
        face_mapping: bool = False,
    ) -> Dict[str, Any]:
        """Generate triangular tessellation for 3D visualization.

        ``face_mapping=True`` builds the mesh per face so the desktop viewport
        can attribute every triangle to a B-Rep face (entity-level picking).
        """
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
                face_mapping=face_mapping,
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

    def generate_mesh_for_shape(
        self,
        shape: Optional["cq.Shape"],
        target_element_size: float = 2.0,
        element_type: str = "tet4",
        physical_groups: Optional[Dict[str, List[int]]] = None,
        domain_label: str = "model",
    ) -> Dict[str, Any]:
        """Generate a volumetric FE mesh from an arbitrary CadQuery shape.

        This is the shared meshing core used both for a whole model and for a
        single selected solid body (see ``generate_mesh`` /
        ``generate_mesh_for_solid``).  It reuses the exact same gmsh/provisional
        meshers -- no new meshing system is introduced.

        ``physical_groups`` (``{name: [face_indices]}``) is forwarded to the
        Gmsh mesher so the returned mesh exposes exact per-boundary node sets
        (Fase 2).
        """
        if shape is None:
            return {
                "success": False,
                "status": "failed",
                "code": "SHAPE_NOT_FOUND",
                "error": f"CAD shape for {domain_label} not found in cache",
            }

        try:
            if element_type != "tet4":
                # GmshTet4Mesher only supports tet4; use the provisional mesher otherwise.
                mesh_result = self.provisional_mesher.generate_mesh(
                    shape,
                    target_element_size=target_element_size,
                    element_type=element_type,
                )
            else:
                # Prefer the definitive Gmsh-Tet4 pipeline, which produces a
                # boundary-conforming real mesh. Fall back to the provisional
                # voxelization mesher if gmsh is unavailable or fails.
                try:
                    mesh_result = self.gmsh_mesher.generate_mesh(
                        shape,
                        target_element_size=target_element_size,
                        element_type=element_type,
                        physical_groups=physical_groups,
                    )
                except (ImportError, RuntimeError, ValueError, FileNotFoundError) as exc:
                    logger.warning(
                        "GmshTet4Mesher failed (%s); falling back to ProvisionalTet4Mesher.", exc
                    )
                    mesh_result = self.provisional_mesher.generate_mesh(
                        shape,
                        target_element_size=target_element_size,
                        element_type=element_type,
                    )
            logger.info(
                "Generated mesh for %s: %d nodes, %d elements (mesher=%s)",
                domain_label,
                mesh_result.num_nodes,
                mesh_result.num_elements,
                mesh_result.metadata.get("mesher", "ProvisionalTet4Mesher"),
            )
            return mesh_result.to_dict()
        except Exception as exc:
            logger.exception("Mesh generation failed for %s", domain_label)
            return {
                "success": False,
                "status": "failed",
                "code": "MESHING_FAILED",
                "error": str(exc),
            }

    def generate_mesh(
        self,
        model_id: str,
        target_element_size: float = 2.0,
        element_type: str = "tet4",
        physical_groups: Optional[Dict[str, List[int]]] = None,
    ) -> Dict[str, Any]:
        """Generate volumetric finite element mesh from CAD model.

        ``physical_groups`` (``{name: [face_indices]}``) is forwarded to the
        Gmsh mesher so the returned mesh exposes exact per-boundary node sets
        (Fase 2).
        """
        shape = self.get_model_shape(model_id)
        if not shape:
            return {
                "success": False,
                "status": "failed",
                "code": "MODEL_NOT_FOUND",
                "error": f"Model {model_id} not found in cache",
            }
        return self.generate_mesh_for_shape(
            shape,
            target_element_size=target_element_size,
            element_type=element_type,
            physical_groups=physical_groups,
            domain_label=f"model {model_id}",
        )

    def generate_mesh_for_solid(
        self,
        model_id: str,
        solid_index: int,
        target_element_size: float = 2.0,
        element_type: str = "tet4",
        physical_groups: Optional[Dict[str, List[int]]] = None,
    ) -> Dict[str, Any]:
        """Generate a volumetric FE mesh for a single solid body of a model.

        This is the deterministic domain mesh used by structural-topology
        studies: the solid selected on ``study.parts`` is meshed alone so the
        analysis domain is exactly that body (never an implicit "first solid").
        Reuses ``generate_mesh_for_shape`` -- no new meshing system.
        """
        solid_shape = self.get_solid_shape(model_id, solid_index)
        if solid_shape is None:
            return {
                "success": False,
                "status": "failed",
                "code": "SOLID_NOT_FOUND",
                "error": f"Solid index {solid_index} could not be resolved for model {model_id}",
            }
        return self.generate_mesh_for_shape(
            solid_shape,
            target_element_size=target_element_size,
            element_type=element_type,
            physical_groups=physical_groups,
            domain_label=f"solid {solid_index} of model {model_id}",
        )

    # ------------------------------------------------------------------ #
    # Fase 2: Boolean operations, solid queries, STEP export
    # ------------------------------------------------------------------ #
    def list_solids(self, model_id: str) -> List[Dict[str, Any]]:
        """Enumerate the solid bodies of a model with their stable ids.

        Returns a list of dicts: ``{"solid_id", "index", "volume",
        "faces_count", "center", "name"}``.
        """
        shape = self.get_model_shape(model_id)
        if shape is None:
            return []
        try:
            solids = list(shape.Solids())
            out = []
            for idx, solid in enumerate(solids):
                center = None
                try:
                    bb = solid.BoundingBox()
                    center = [bb.xmin + (bb.xmax - bb.xmin) / 2.0,
                              bb.ymin + (bb.ymax - bb.ymin) / 2.0,
                              bb.zmin + (bb.zmax - bb.zmin) / 2.0]
                except Exception:
                    center = None
                try:
                    volume = solid.Volume()
                except Exception:
                    volume = None
                try:
                    faces_count = len(list(solid.Faces()))
                except Exception:
                    faces_count = 0
                out.append({
                    "solid_id": f"solid_{idx}",
                    "index": idx,
                    "volume": volume,
                    "faces_count": faces_count,
                    "center": center,
                    "name": f"Cuerpo {idx + 1}",
                })
            return out
        except Exception as exc:
            logger.exception("list_solids failed for model %s", model_id)
            return []

    def get_solid_shape(self, model_id: str, index: int) -> Optional["cq.Shape"]:
        """Return the B-Rep shape of a single solid body (by index) of a model."""
        shape = self.get_model_shape(model_id)
        if shape is None:
            return None
        try:
            solids = list(shape.Solids())
        except Exception as exc:
            logger.debug("get_solid_shape: no solids %s", exc)
            return None
        if 0 <= index < len(solids):
            return solids[index]
        return None

    def boolean_bodies(
        self,
        model_id: str,
        operation: str,
        target_index: int,
        tool_indices: List[int],
        keep_tools: bool = False,
    ) -> Dict[str, Any]:
        """Perform a body-level boolean operation on the solids of a model.

        The current model's B-Rep is split into its constituent solids.  The
        solid at ``target_index`` is the target; the solids at
        ``tool_indices`` are the tools.  The operation (union/difference/
        intersection) is applied to the target using each tool.  The result is
        stored as a new model in the cache and returned.

        ``keep_tools`` controls whether the tool bodies are retained alongside
        the modified target body in the resulting model:

        * ``keep_tools=True``  -> tools remain available after the operation.
        * ``keep_tools=False`` -> tools are consumed by the operation.

        Returns a dict with ``{"success", "model_id", "error"}``.  On failure
        the original model is left untouched.
        """
        shape = self.get_model_shape(model_id)
        if shape is None:
            return {"success": False, "error": "Model not found in cache."}
        try:
            solids = list(shape.Solids())
        except Exception as exc:
            logger.exception("boolean_bodies: could not enumerate solids")
            return {"success": False, "error": f"Could not enumerate solids: {exc}"}

        if not solids:
            return {"success": False, "error": "The model contains no solid bodies."}
        if not (0 <= target_index < len(solids)):
            return {"success": False,
                    "error": f"Target body index {target_index} out of range."}
        bad_tools = [i for i in tool_indices if not (0 <= i < len(solids))]
        if bad_tools:
            return {"success": False,
                    "error": f"Tool body index(es) out of range: {bad_tools}"}
        if target_index in tool_indices:
            return {"success": False,
                    "error": "A tool body cannot also be the target body."}

        try:
            result_solid = solids[target_index]
            for t_idx in tool_indices:
                tool = solids[t_idx]
                if operation == BooleanOperation.UNION.value:
                    result_solid = result_solid.fuse(tool)
                elif operation == BooleanOperation.DIFFERENCE.value:
                    result_solid = result_solid.cut(tool)
                elif operation == BooleanOperation.INTERSECTION.value:
                    result_solid = result_solid.intersect(tool)
                else:
                    return {"success": False,
                            "error": f"Unsupported boolean operation: {operation}"}

            # Reassemble the model: the modified target plus every body that is
            # not a tool (and, if keep_tools, the tools themselves).
            keep_indices = [i for i in range(len(solids)) if i != target_index]
            if not keep_tools:
                keep_indices = [i for i in keep_indices if i not in tool_indices]
            out_solids = [result_solid] + [solids[i] for i in keep_indices]
            new_shape = cq.Compound.makeCompound(out_solids)

            new_model_id = self.store_computed_shape(
                new_shape, model_name=f"Boolean {operation}"
            )
            return {"success": True, "model_id": new_model_id}
        except Exception as exc:
            logger.exception("boolean_bodies failed")
            return {"success": False, "error": str(exc)}

    def resolve_solid_for_face(self, model_id: str, face_index: int) -> Optional[Dict[str, Any]]:
        """Determine which solid a given face (by global face index) belongs to.

        Returns a dict with ``solid_id``/``index`` or ``None``.  Used by the
        viewport to resolve body-level selection when a face is picked, so the
        selection can refer to the whole solid rather than the single face.
        """
        shape = self.get_model_shape(model_id)
        if shape is None:
            return None
        try:
            solids = list(shape.Solids())
            if not solids:
                return None
            if len(solids) == 1:
                return {"solid_id": "solid_0", "index": 0}
            try:
                all_faces = list(shape.Faces())
                if 0 <= face_index < len(all_faces):
                    center = all_faces[face_index].Center()
                    vec = cq.Vector(center.x, center.y, center.z)
                    for idx, solid in enumerate(solids):
                        try:
                            if solid.isInside(vec):
                                return {"solid_id": f"solid_{idx}", "index": idx}
                        except Exception:
                            continue
            except Exception:
                logger.debug("face->solid containment failed for face %d", face_index)
            # Fall back to the first solid.
            return {"solid_id": "solid_0", "index": 0}
        except Exception as exc:
            logger.exception("resolve_solid_for_face failed for model %s", model_id)
            return None

    def store_computed_shape(self, shape: cq.Shape, model_name: str = "Resultado CAD") -> str:
        """Store a computed CadQuery Shape in the cache and return a new model_id."""
        model_id = str(uuid.uuid4())
        cad_model = CADModel(
            id=model_id,
            name=model_name,
            source=SourceReference(source_type=SourceType.SYNTHETIC, metadata={"origin": "computed"}),
        )
        # Keep both caches (service + adapter) in sync so tessellation works.
        self._model_cache[model_id] = (cad_model, shape)
        self.step_adapter.cache_shape(model_id, shape)
        logger.info("Stored computed shape: %s (ID: %s)", model_name, model_id)
        return model_id

    def export_step(self, model_id: str, file_path: str) -> bool:
        """Export a model's B-Rep shape to a STEP file using CadQuery/OCC."""
        shape = self.get_model_shape(model_id)
        if shape is None:
            return False
        try:
            import cadquery as cq
            # cq.exporters.export expects a Workplane or Shape; values support exportType="STEP".
            cq.exporters.export(shape.val() if hasattr(shape, "val") else shape,
                                file_path, exportType="STEP")
            logger.info("Exported STEP for model %s -> %s", model_id, file_path)
            return True
        except Exception as exc:
            logger.exception("export_step failed for model %s", model_id)
            return False

    def generate_adaptive_mesh(
        self,
        model_id: str,
        densities: Optional[Any] = None,
        elements: Optional[Any] = None,
        nodes: Optional[Any] = None,
        base_size: float = 5.0,
        min_size: float = 0.5,
        element_type: str = "tet4",
        refinement: str = "density",
        physical_groups: Optional[Dict[str, List[int]]] = None,
    ) -> Dict[str, Any]:
        """Generate an adaptively refined FE mesh, optionally driven by the
        topology-optimization density field.

        When ``densities`` (per-element), ``elements`` (tet connectivity) and
        ``nodes`` are supplied, element centroids are computed and the element
        size is scaled by density so that solid/dense regions get a finer mesh
        (density-driven local refinement).  Falls back to a uniform Gmsh mesh.
        """
        shape = self.get_model_shape(model_id)
        if not shape:
            return {"success": False, "status": "failed", "code": "MODEL_NOT_FOUND",
                    "error": f"Model {model_id} not found in cache"}
        try:
            size_points = None
            if densities is not None and elements is not None and nodes is not None:
                import numpy as _np
                nparr = _np.asarray(nodes, dtype=float)
                elems = _np.asarray(elements, dtype=int)
                dens = _np.asarray(densities, dtype=float)
                size_points = []
                for k, tet in enumerate(elems):
                    if k >= len(dens):
                        break
                    d = float(dens[k])
                    if d < 1e-6:
                        continue
                    verts = nparr[tet]
                    cx = float(verts[:, 0].mean())
                    cy = float(verts[:, 1].mean())
                    cz = float(verts[:, 2].mean())
                    # Elements with high density (solid, structural) get finer.
                    s = base_size * (1.0 - 0.7 * d)
                    s = max(s, min_size)
                    size_points.append([cx, cy, cz, s])
                if len(size_points) < 8:
                    size_points = None

            # Export to temp STEP for Gmsh
            import tempfile, os as _os
            import cadquery as _cq
            fd, tmp = tempfile.mkstemp(suffix=".step")
            _os.close(fd)
            try:
                _cq.exporters.export(shape, tmp, exportType="STEP")
                if size_points:
                    mesh_result = self.gmsh_mesher.generate_adaptive_mesh(
                        tmp, size_points=size_points,
                        base_size=base_size, min_size=min_size, element_type=element_type,
                        physical_groups=physical_groups,
                    )
                else:
                    mesh_result = self.gmsh_mesher.generate_mesh_from_step(
                        tmp, target_element_size=base_size, element_type=element_type,
                        physical_groups=physical_groups,
                    )
            finally:
                if _os.path.exists(tmp):
                    try:
                        _os.unlink(tmp)
                    except OSError:
                        pass
            logger.info("Adaptive mesh for %s: %d nodes, %d elems (refinement=%s)",
                        model_id, mesh_result.num_nodes, mesh_result.num_elements, refinement)
            return mesh_result.to_dict()
        except (ImportError, RuntimeError, ValueError, FileNotFoundError) as exc:
            logger.warning("Adaptive mesh failed (%s); falling back to uniform mesh.", exc)
            return self.generate_mesh(model_id, target_element_size=base_size, element_type=element_type)
        except Exception as exc:
            logger.exception("generate_adaptive_mesh failed for model %s", model_id)
            return {"success": False, "status": "failed", "code": "MESHING_FAILED", "error": str(exc)}

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