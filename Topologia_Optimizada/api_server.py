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


class ForceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    magnitude: float = Field(gt=0)
    direction_x: float
    direction_y: float
    direction_z: float
    application_point: Optional[str] = None
    force_type: str = Field(default="point", pattern="^(point|distributed|pressure)$")

    @model_validator(mode="after")
    def non_zero_direction(self) -> "ForceDefinition":
        if self.direction_x == self.direction_y == self.direction_z == 0:
            raise ValueError("La dirección de la fuerza no puede ser cero")
        return self


class ConstraintDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_type: str = Field(pattern="^(fixed|pinned|roller|symmetry)$")
    location: str
    degrees_of_freedom: Dict[str, bool] = Field(default_factory=lambda: {
        "ux": True, "uy": True, "uz": True, "rx": True, "ry": True, "rz": True
    })

    @model_validator(mode="after")
    def one_axis_required(self) -> "ConstraintDefinition":
        if not any(self.degrees_of_freedom.values()):
            raise ValueError("Al menos un grado de libertad debe estar restringido")
        return self


class Load(BaseModel):
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
    def non_zero_direction(self) -> "Load":
        if self.directionX == self.directionY == self.directionZ == 0:
            raise ValueError("load direction cannot be zero")
        return self


class Constraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(default="fixed", pattern="^fixed$")
    selection: list[GeometryReference] = Field(min_length=1)
    ux: bool = True
    uy: bool = True
    uz: bool = True

    @model_validator(mode="after")
    def one_axis_required(self) -> "Constraint":
        if not any((self.ux, self.uy, self.uz)):
            raise ValueError("a constraint must restrict at least one axis")
        return self


class LoadCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    constraints: list[Constraint] = Field(min_length=1)
    loads: list[Load] = Field(min_length=1)


class Material(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=512)
    youngModulus: float = Field(gt=0)
    poisson: float = Field(gt=-1, lt=0.5)
    density: float = Field(gt=0)
    yieldStrength: float = Field(gt=0)


class Objectives(BaseModel):
    model_config = ConfigDict(extra="forbid")

    volumeFraction: float = Field(gt=0, le=1)


class SolverSettings(BaseModel):
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
    material: Material
    objectives: Objectives
    solverSettings: SolverSettings
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
async def upload_step_file(request: StepUploadRequest) -> Dict[str, Any]:
    """Import STEP file directly without Onshape/OAuth (standalone)."""
    try:
        step_bytes = base64.b64decode(request.step_data)
        cad_model = cad_service.import_step_from_bytes(
            step_bytes,
            model_name=request.model_name,
            metadata={"source": "standalone_upload"},
        )
        study_service.save_cad_model(cad_model)
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