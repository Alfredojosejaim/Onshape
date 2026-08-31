"""FastAPI backend for Topologia Optimizada - Standalone Application.

Handles local STEP file import, CAD model management, tessellation for Three.js,
real volumetric FEM meshing, boundary conditions, and study persistence in SQLite.
This is a standalone application that does NOT require Onshape, OAuth, or any external CAD platform.
"""

import base64
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from geometry_processor import GeometryProcessor
from services.cad_service import CADService
from services.study_service import StudyService

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("JOB_DB_PATH", "jobs.sqlite3")

app = FastAPI(title="Topologia Optimizada API - Standalone", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "https://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                session_id TEXT,
                request_json TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                end_time TEXT,
                result_json TEXT,
                error_code TEXT,
                error_message TEXT
            )
            """
        )


init_database()


# Standalone services (independent of Onshape)
cad_service = CADService()
study_service = StudyService(DB_PATH)

# Session-scoped state for the standalone UI flow.
# Because this is a local single-user application, a module-level dict keyed by
# session id is a sufficient in-memory store for the active model/mesh/boundary
# state. It is intentionally independent of any CAD platform.
SESSION_STATE: Dict[str, Dict[str, Any]] = {}


def get_session_state(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSION_STATE:
        SESSION_STATE[session_id] = {
            "model_id": None,
            "mesh": None,
            "forces": [],
            "constraints": [],
            "material": "steel",
        }
    return SESSION_STATE[session_id]


# --- Pydantic Data Models ---

class GeometryReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(pattern="^(body|face|edge|vertex|reference)$")
    reference: str = Field(min_length=1, max_length=2048)
    role: str = Field(min_length=1, max_length=32)
    context: Dict[str, str] = Field(min_length=1)
    geometry: Optional[Dict[str, Any]] = None


class GeometrySelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: Dict[str, str] = Field(min_length=1)
    designSpace: list[str] = Field(min_length=1)
    keepOut: list[str] = Field(default_factory=list)


class MeshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_data: Optional[str] = None
    target_element_size: float = Field(default=2.0, gt=0)
    element_type: str = Field(default="tet4", pattern="^(tet4|tet10|hex8)$")


class LoadDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(default="force", pattern="^force$")
    selection: list[GeometryReference] = Field(min_length=1)
    magnitude: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=32)
    directionMode: str = Field(default="vector", pattern="^(vector|face_normal)$")
    directionX: float
    directionY: float
    directionZ: float
    inverted: bool = False

    @model_validator(mode="after")
    def non_zero_direction(self) -> "LoadDto":
        if self.directionX == self.directionY == self.directionZ == 0:
            raise ValueError("load direction cannot be zero")
        return self


class ConstraintDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(default="fixed", pattern="^fixed$")
    selection: list[GeometryReference] = Field(min_length=1)
    ux: bool = True
    uy: bool = True
    uz: bool = True

    @model_validator(mode="after")
    def one_axis_required(self) -> "ConstraintDto":
        if not any((self.ux, self.uy, self.uz)):
            raise ValueError("a constraint must restrict at least one axis")
        return self


class LoadCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    constraints: list[ConstraintDto] = Field(min_length=1)
    loads: list[LoadDto] = Field(min_length=1)


class MaterialDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=512)
    youngModulus: float = Field(gt=0)
    poisson: float = Field(gt=-1, lt=0.5)
    density: float = Field(gt=0)
    yieldStrength: float = Field(gt=0)


class ObjectivesDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    volumeFraction: float = Field(gt=0, le=1)


class SolverSettingsDto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maxIterations: int = Field(gt=0, le=10000)
    convergenceTolerance: float = Field(gt=0, lt=1, default=0.01)


class DesignSpace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preserve: list[GeometryReference] = Field(min_length=1)
    obstacle: list[GeometryReference] = Field(default_factory=list)
    initialShape: list[GeometryReference] = Field(default_factory=list)
    symmetry: Optional[str] = None
    obstacleOffset: Optional[float] = Field(default=None, ge=0)


class TopologyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: str = Field(min_length=1, max_length=32)
    studyName: str = Field(min_length=1, max_length=128)
    context: Dict[str, str] = Field(min_length=1)
    designSpace: DesignSpace
    loadCases: list[LoadCase] = Field(min_length=1)
    material: MaterialDto
    objectives: ObjectivesDto
    solverSettings: SolverSettingsDto
    timestamp: str = Field(default_factory=utc_now)


class OptimizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topologyConfig: TopologyConfig
    timestamp: str = Field(default_factory=utc_now)


class OptimizationResponse(BaseModel):
    status: str
    message: str
    jobId: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    end_time: Optional[str] = None


class JobStatus:
    """Persistent job representation."""

    def __init__(self, job_id: str, request: OptimizationRequest, session_id: str):
        self.job_id = job_id
        self.session_id = session_id
        self.status = "queued"
        self.progress = 0
        self.message = "En cola de espera"
        self.created_at = utc_now()
        self.updated_at = self.created_at
        self.end_time: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[Dict[str, str]] = None
        with db_connection() as connection:
            connection.execute(
                """
                INSERT INTO jobs
                (job_id, session_id, request_json, status, progress, message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    self.session_id,
                    request.model_dump_json(),
                    self.status,
                    self.progress,
                    self.message,
                    self.created_at,
                    self.updated_at,
                ),
            )

    def update(
        self,
        *,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, str]] = None,
        finished: bool = False,
    ) -> None:
        if status is not None:
            self.status = status
        if progress is not None:
            self.progress = max(0, min(100, progress))
        if message is not None:
            self.message = message
        if result is not None:
            self.result = result
        if error is not None:
            self.error = error
        self.updated_at = utc_now()
        if finished:
            self.end_time = self.updated_at
        with db_connection() as connection:
            connection.execute(
                """
                UPDATE jobs SET status=?, progress=?, message=?, updated_at=?,
                    end_time=?, result_json=?, error_code=?, error_message=?
                WHERE job_id=?
                """,
                (
                    self.status,
                    self.progress,
                    self.message,
                    self.updated_at,
                    self.end_time,
                    json.dumps(self.result) if self.result is not None else None,
                    self.error.get("code") if self.error else None,
                    self.error.get("message") if self.error else None,
                    self.job_id,
                ),
            )


def row_to_response(row: sqlite3.Row) -> JobStatusResponse:
    result = json.loads(row["result_json"]) if row["result_json"] else None
    error = None
    if row["error_code"] or row["error_message"]:
        error = {"code": row["error_code"] or "JOB_FAILED", "message": row["error_message"] or ""}
    return JobStatusResponse(
        job_id=row["job_id"],
        status=row["status"],
        progress=row["progress"],
        message=row["message"],
        result=result,
        error=error,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        end_time=row["end_time"],
    )


# --- Application Endpoints ---

@app.get("/")
async def local_interface() -> FileResponse:
    return FileResponse("optimization-app.html")


@app.get("/app")
async def optimization_interface() -> FileResponse:
    return FileResponse("optimization-app.html")


@app.get("/app/")
async def optimization_interface_trailing() -> FileResponse:
    return FileResponse("optimization-app.html")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "mode": "standalone",
        "message": "Topologia Optimizada API - Standalone operational",
    }


# --- Standalone Endpoints (Independent of Onshape) ---

class StepUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_data: str = Field(min_length=1)
    model_name: str = Field(default="Imported STEP", min_length=1)


class StandaloneMeshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = Field(min_length=1)
    target_element_size: float = Field(default=2.0, gt=0)
    element_type: str = Field(default="tet4", pattern="^(tet4|tet10|hex8)$")


class StandaloneTessellationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = Field(min_length=1)
    linear_deflection: float = Field(default=0.1, gt=0)
    angular_deflection: float = Field(default=0.1, gt=0)


class BoundaryMappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = Field(min_length=1)
    nodes: List[List[float]] = Field(min_length=1)
    face_indices: Optional[List[int]] = None
    tolerance: float = Field(default=0.5, gt=0)


@app.post("/api/cad/step/upload")
async def upload_step_file(request: Request, req_body: StepUploadRequest) -> Dict[str, Any]:
    """Import STEP file directly without Onshape/OAuth (standalone)."""
    try:
        step_bytes = base64.b64decode(req_body.step_data)
        cad_model = cad_service.import_step_from_bytes(
            step_bytes,
            model_name=req_body.model_name,
            metadata={"source": "standalone_upload"},
        )
        study_service.save_cad_model(cad_model)
        session_id = request.query_params.get("session_id") or "default"
        state = get_session_state(session_id)
        state["model_id"] = cad_model.id
        return {
            "success": True,
            "status": "ready",
            "model_id": cad_model.id,
            "model_name": cad_model.name,
            "model": cad_model.to_dict(),
        }
    except Exception as exc:
        logger.exception("STEP upload failed")
        raise HTTPException(status_code=400, detail=f"STEP import failed: {str(exc)}")


@app.get("/api/cad/models/{model_id}")
async def get_cad_model(model_id: str) -> Dict[str, Any]:
    """Retrieve model and tessellation data (standalone)."""
    cad_model = cad_service.get_model(model_id)
    if not cad_model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return cad_model.to_dict()


@app.post("/api/cad/models/{model_id}/tessellate")
async def tessellate_model(model_id: str, request: StandaloneTessellationRequest) -> Dict[str, Any]:
    """Generate tessellation for Three.js visualization (standalone)."""
    if model_id != request.model_id:
        raise HTTPException(status_code=400, detail="Model ID mismatch")
    return cad_service.tessellate_model(
        model_id,
        linear_deflection=request.linear_deflection,
        angular_deflection=request.angular_deflection,
    )


@app.post("/api/cad/models/{model_id}/mesh")
async def generate_mesh_standalone(model_id: str, request: StandaloneMeshRequest) -> Dict[str, Any]:
    """Generate mesh on imported CAD (standalone)."""
    if model_id != request.model_id:
        raise HTTPException(status_code=400, detail="Model ID mismatch")
    return cad_service.generate_mesh(
        model_id,
        target_element_size=request.target_element_size,
        element_type=request.element_type,
    )


@app.post("/api/cad/models/{model_id}/boundary/map")
async def map_boundary_conditions_standalone(model_id: str, request: BoundaryMappingRequest) -> Dict[str, Any]:
    """Map boundary conditions (standalone)."""
    if model_id != request.model_id:
        raise HTTPException(status_code=400, detail="Model ID mismatch")
    return cad_service.map_boundary_conditions(
        model_id,
        request.nodes,
        face_indices=request.face_indices,
        tolerance=request.tolerance,
    )


@app.get("/api/studies")
async def list_studies() -> List[Dict[str, Any]]:
    """List all studies (standalone)."""
    return study_service.list_studies()


@app.post("/api/studies")
async def create_study_standalone(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create a study (standalone)."""
    try:
        study = study_service.create_study(
            name=request.get("name", "New Study"),
            metadata=request.get("metadata"),
        )
        return study.to_dict()
    except Exception as exc:
        logger.exception("Study creation failed")
        raise HTTPException(status_code=400, detail=f"Study creation failed: {str(exc)}")


@app.get("/api/studies/{study_id}")
async def get_study_standalone(study_id: str) -> Dict[str, Any]:
    """Get a study (standalone)."""
    study = study_service.get_study(study_id)
    if not study:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")
    return study.to_dict()


@app.delete("/api/studies/{study_id}")
async def delete_study_standalone(study_id: str) -> Dict[str, Any]:
    """Delete a study (standalone)."""
    deleted = study_service.delete_study(study_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")
    return {"success": True, "message": f"Study {study_id} deleted"}


# ---------------------------------------------------------------------------
# Session-scoped standalone workflow endpoints (used by optimization-app.html)
# ---------------------------------------------------------------------------

class SessionMeshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_element_size: float = Field(default=2.0, gt=0)
    element_type: str = Field(default="tet4", pattern="^(tet4|tet10|hex8)$")


class BoundaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # The frontend stores the whole current list; accept it as-is.
    forces: Optional[List[Dict[str, Any]]] = None
    constraints: Optional[List[Dict[str, Any]]] = None


class OptimizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    volume_fraction: float = Field(default=0.3, gt=0, le=1)
    max_iterations: int = Field(default=50, gt=0, le=10000)
    penalization: float = Field(default=3.0, gt=0)
    filter_radius: float = Field(default=1.5, gt=0)
    tolerance: float = Field(default=1e-3, gt=0, lt=1)


class FEARequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    material: str = Field(default="steel")


def _session(session_id: str) -> Dict[str, Any]:
    return get_session_state(session_id or "default")


def _resolve_material(name: str):
    from core.materials import STANDARD_MATERIALS
    if name not in STANDARD_MATERIALS:
        raise HTTPException(status_code=400, detail=f"Unknown material: {name}")
    return STANDARD_MATERIALS[name]


def _apply_mesh_to_session(session_id: str, model_id: str, target_element_size: float = 2.0) -> Dict[str, Any]:
    """Generate a volumetric mesh for the active model and store it in the session."""
    state = _session(session_id)
    result = cad_service.generate_mesh(model_id, target_element_size=target_element_size)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Meshing failed"))
    state["model_id"] = model_id
    state["mesh"] = result
    return result


def _mesh_to_numpy(mesh: Dict[str, Any]):
    import numpy as np
    nodes = np.array(mesh["nodes"], dtype=float)
    elements = np.array(mesh["elements"], dtype=int)
    return nodes, elements


def _build_fea_problem(state: Dict[str, Any], material):
    """Build (force_vector, fixed_dofs) from the session mesh + boundaries.

    Constraints and loads from the UI are mapped onto real mesh nodes through
    the Core ``BoundaryConditionMapper`` (CAD face -> nodes). When a boundary
    carries no resolvable face, the load is distributed over the nodes at the
    free end (max coordinate along the load axis) and constraints default to the
    minimum-coordinate extreme.
    """
    import numpy as np
    from core.boundary import BoundaryConditionMapper, resolve_face_index

    mesh = state["mesh"]
    if not mesh:
        raise HTTPException(status_code=400, detail="No mesh generated yet")

    nodes, elements = _mesh_to_numpy(mesh)
    num_dofs = int(nodes.shape[0] * 3)
    force_vector = np.zeros(num_dofs)
    fixed_dofs: List[int] = []

    # Adaptive face-mapping tolerance: derive it from the actual node spacing so
    # that a face only captures the surface nodes that truly lie on it. A fixed
    # tolerance (e.g. 0.5) over-constrains small parts by matching nodes from all
    # faces, driving the FEA displacement to ~1e-9 (the over-constraint bug).
    sample = nodes[:: max(1, len(nodes) // 500)]
    bbox = sample.max(axis=0) - sample.min(axis=0)
    char_length = max(float(np.linalg.norm(bbox) / max(1.0, float(len(nodes)) ** (1.0 / 3.0))), 1e-9)
    face_tolerance = 1.5 * char_length

    model_id = state.get("model_id")
    shape = cad_service.get_model_shape(model_id) if model_id else None

    # --- Constraints (fixed DOFs) ---
    for c in state.get("constraints", []):
        ctype = c.get("constraint_type", "fixed")
        location = c.get("location", "")
        face_index = resolve_face_index(str(location)) if location else None
        node_indices: List[int] = []
        if shape is not None and face_index is not None:
            mapped = BoundaryConditionMapper.map_faces_to_nodes(
                shape, nodes.tolist(), face_indices=[face_index], tolerance=face_tolerance
            )
            if mapped and mapped[0].node_indices:
                node_indices = mapped[0].node_indices
        if not node_indices:
            axis = c.get("fixed_axis", 2)
            coord = c.get("fixed_coordinate")
            if coord is None:
                coord = float(nodes[:, axis].min())
            node_indices = [
                i for i in range(nodes.shape[0])
                if abs(float(nodes[i, axis]) - coord) <= 1e-6 * max(1.0, nodes[:, axis].ptp())
            ]
        dof = c.get("degrees_of_freedom") or {"ux": True, "uy": True, "uz": True}
        fix_xyz = [bool(dof.get("ux", True)), bool(dof.get("uy", True)), bool(dof.get("uz", True))]
        if ctype != "fixed":
            # pinned/roller only block translations (this 3D solid Tet4 has no
            # rotational DOFs; pinning == fixing translations here)
            fix_xyz = [True, True, True]
        for ni in node_indices:
            for ax in range(3):
                if fix_xyz[ax]:
                    fixed_dofs.append(ni * 3 + ax)
        state["_constraint_nodes"] = node_indices

    # --- Loads (distributed point loads) ---
    for ld in state.get("forces", []):
        mag = float(ld.get("magnitude", 0))
        direction = [float(ld.get("direction_x", 0)), float(ld.get("direction_y", 0)), float(ld.get("direction_z", 0))]
        norm = np.linalg.norm(direction)
        if norm == 0:
            continue
        direction = np.array(direction) / norm
        fvec = direction * mag

        face_index = resolve_face_index(str(ld.get("application_face_id", ""))) if ld.get("application_face_id") else None
        node_indices: List[int] = []
        if shape is not None and face_index is not None:
            mapped = BoundaryConditionMapper.map_faces_to_nodes(
                shape, nodes.tolist(), face_indices=[face_index], tolerance=face_tolerance
            )
            if mapped and mapped[0].node_indices:
                node_indices = mapped[0].node_indices
        if not node_indices:
            # distribute over the free-end extreme along the strongest load axis
            axis = int(np.argmax(np.abs(direction)))
            coord = float(nodes[:, axis].max())
            node_indices = [
                i for i in range(nodes.shape[0])
                if abs(float(nodes[i, axis]) - coord) <= 1e-6 * max(1.0, nodes[:, axis].ptp())
            ]
        for ni in node_indices:
            force_vector[ni * 3: ni * 3 + 3] += np.array(fvec) / max(len(node_indices), 1)
        state["_load_nodes"] = node_indices

    return force_vector, np.sort(np.unique(np.asarray(fixed_dofs, dtype=int))), nodes, elements


@app.get("/api/geometry/current")
async def geometry_current(request: Request) -> Dict[str, Any]:
    """Return the tessellation of the currently active model (standalone UI)."""
    session_id = request.query_params.get("session_id") or "default"
    state = _session(session_id)
    model_id = state.get("model_id")
    if not model_id:
        return {"status": "success", "success": True, "tessellation": None}
    cad_model = cad_service.get_model(model_id)
    if not cad_model or not cad_model.tessellation:
        return {"status": "success", "success": True, "tessellation": None}
    return {
        "status": "success",
        "success": True,
        "tessellation": cad_model.tessellation.to_dict(),
    }


@app.post("/api/boundary/forces")
async def boundary_forces(request: Request, payload: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Store the current load list for the active session."""
    session_id = request.query_params.get("session_id") or "default"
    state = _session(session_id)
    state["forces"] = payload
    return {"success": True, "message": f"{len(payload)} fuerza(s) registrada(s)", "count": len(payload)}


@app.post("/api/boundary/constraints")
async def boundary_constraints(request: Request, payload: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Store the current constraint list for the active session."""
    session_id = request.query_params.get("session_id") or "default"
    state = _session(session_id)
    state["constraints"] = payload
    return {"success": True, "message": f"{len(payload)} restricción(es) registrada(s)", "count": len(payload)}


@app.post("/api/mesh/generate")
async def session_mesh_generate(request: Request, payload: SessionMeshRequest) -> Dict[str, Any]:
    """Generate a mesh for the active model and store it in the session."""
    session_id = request.query_params.get("session_id") or "default"
    state = _session(session_id)
    if not state.get("model_id"):
        raise HTTPException(status_code=400, detail="No model imported. Import a STEP file first.")
    mesh = _apply_mesh_to_session(session_id, state["model_id"], target_element_size=payload.target_element_size)
    return {
        "status": "success",
        "message": f"Malla FEM generada: {mesh['num_nodes']} nodos, {mesh['num_elements']} tetraedros",
        "mesh": {
            "num_nodes": mesh["num_nodes"],
            "num_elements": mesh["num_elements"],
            "element_type": mesh["element_type"],
            "is_provisional": mesh["is_provisional"],
            "nodes": mesh["nodes"],
            "elements": mesh["elements"],
        },
    }


def _parameters_from_body(payload: Dict[str, Any], state: Dict[str, Any]) -> None:
    material = payload.get("material") or state.get("material") or "steel"
    state["material"] = material


@app.post("/api/fea/run")
async def run_fea(request: Request, payload: FEARequest) -> Dict[str, Any]:
    """Run a linear static FEA on the active mesh with the current boundaries."""
    session_id = request.query_params.get("session_id") or "default"
    state = _session(session_id)
    if not state.get("mesh"):
        raise HTTPException(status_code=400, detail="No mesh generated. Generate a mesh first.")
    if not state.get("constraints"):
        raise HTTPException(status_code=400, detail="Add at least one constraint first.")

    material = _resolve_material(payload.material or state.get("material", "steel"))
    force_vector, fixed_dofs, nodes, elements = _build_fea_problem(state, material)

    from core.fea import solve_fea
    result = solve_fea(
        nodes=nodes,
        elements=elements,
        young_modulus=material.young_modulus,
        poisson_ratio=material.poisson_ratio,
        forces_dofs=[(int(i), float(v)) for i, v in enumerate(force_vector) if v != 0.0],
        fixed_dofs=fixed_dofs.tolist(),
    )
    return {
        "success": result["success"],
        "status": result["status"],
        "result": result,
        "material": material.name,
    }


@app.post("/api/optimize")
async def run_optimization(request: Request, payload: OptimizeRequest) -> Dict[str, Any]:
    """Run SIMP topology optimisation on the active mesh (self-contained engine)."""
    session_id = request.query_params.get("session_id") or "default"
    state = _session(session_id)
    if not state.get("mesh"):
        raise HTTPException(status_code=400, detail="No mesh generated. Generate a mesh first.")
    if not state.get("constraints"):
        raise HTTPException(status_code=400, detail="Add at least one constraint first.")

    material = _resolve_material(state.get("material", "steel"))
    force_vector, fixed_dofs, nodes, elements = _build_fea_problem(state, material)

    from core.topopt import SIMPSolver
    solver = SIMPSolver(
        nodes=nodes,
        elements=elements,
        young_modulus=material.young_modulus,
        poisson_ratio=material.poisson_ratio,
        volfrac=payload.volume_fraction,
        penalization=payload.penalization,
        filter_radius=payload.filter_radius,
    )
    solver.set_load(force_vector)
    solver.set_fixed_dofs(fixed_dofs)
    try:
        result = solver.optimize(
            max_iterations=payload.max_iterations,
            tolerance=payload.tolerance,
        )
    except Exception as exc:
        logger.exception("Optimization failed")
        raise HTTPException(status_code=400, detail=f"Optimization failed: {exc}")
    return {
        "success": result["success"],
        "status": result["status"],
        "result": result,
        "material": material.name,
    }


if __name__ == "__main__":
    import uvicorn

    certfile = os.getenv("SSL_CERTFILE")
    keyfile = os.getenv("SSL_KEYFILE")

    # Auto-detect certs/localhost.pem and certs/localhost-key.pem if present
    if not certfile and os.path.exists("certs/localhost.pem"):
        certfile = os.path.abspath("certs/localhost.pem")
    elif certfile and not os.path.isabs(certfile):
        resolved = os.path.abspath(certfile)
        if os.path.exists(resolved):
            certfile = resolved

    if not keyfile and os.path.exists("certs/localhost-key.pem"):
        keyfile = os.path.abspath("certs/localhost-key.pem")
    elif keyfile and not os.path.isabs(keyfile):
        resolved = os.path.abspath(keyfile)
        if os.path.exists(resolved):
            keyfile = resolved

    ssl_cert = certfile if certfile and os.path.exists(certfile) else None
    ssl_key = keyfile if keyfile and os.path.exists(keyfile) else None

    if ssl_cert and ssl_key:
        logger.info("Iniciando servidor HTTPS con certificados locales: %s", ssl_cert)
    else:
        logger.info("Iniciando servidor HTTP (sin certificados SSL)")

    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        ssl_certfile=ssl_cert,
        ssl_keyfile=ssl_key,
    )