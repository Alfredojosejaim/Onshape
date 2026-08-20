"""FastAPI backend for the Onshape topology MVP.

Jobs and their state are stored in SQLite so a process restart does not lose
the queue history.  API credentials are read only on the backend and are
never returned or written to logs.
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import find_dotenv, load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from geometry_processor import GeometryProcessor
from topopt_solver import run_topology_optimization

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("JOB_DB_PATH", "jobs.sqlite3")
ACCESS_KEY = os.getenv("ONSHAPE_ACCESS_KEY") or os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("ONSHAPE_SECRET_KEY") or os.getenv("SECRET_KEY")

app = FastAPI(title="Optimizacion Topologica API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

JOBS: Dict[str, "JobStatus"] = {}


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
                document_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                element_id TEXT NOT NULL,
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


class Load(BaseModel):
    model_config = ConfigDict(extra="forbid")

    directionX: float
    directionY: float
    directionZ: float
    magnitude: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def non_zero_direction(self) -> "Load":
        if self.directionX == self.directionY == self.directionZ == 0:
            raise ValueError("load direction cannot be zero")
        return self


class Optimization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    volumeFraction: float = Field(gt=0, le=1)
    maxIterations: int = Field(gt=0, le=10000)


class TopologyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: str = Field(min_length=1, max_length=32)
    anchors: list[Any] = Field(default_factory=list)
    loads: list[Load] = Field(min_length=1)
    optimization: Optimization
    timestamp: Optional[str] = None


class OptimizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documentId: str = Field(min_length=1, max_length=256)
    workspaceId: str = Field(min_length=1, max_length=256)
    elementId: str = Field(min_length=1, max_length=256)
    topologyConfig: TopologyConfig
    timestamp: Optional[str] = None


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
    """A small persistent view of one job."""

    def __init__(self, job_id: str, request: OptimizationRequest):
        self.job_id = job_id
        self.document_id = request.documentId
        self.workspace_id = request.workspaceId
        self.element_id = request.elementId
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
                (job_id, document_id, workspace_id, element_id, request_json,
                 status, progress, message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    self.document_id,
                    self.workspace_id,
                    self.element_id,
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


def verificar_credenciales() -> bool:
    """Return whether backend-only Onshape credentials are configured."""
    return bool(ACCESS_KEY and SECRET_KEY)


def obtener_sesion_onshape() -> requests.Session:
    session = requests.Session()
    session.auth = (ACCESS_KEY, SECRET_KEY)
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {"Accept": "application/vnd.onshape.v2+json", "Content-Type": "application/json"}
    )
    return session


def set_configuration_pending(job: JobStatus) -> None:
    job.update(
        status="pending",
        progress=0,
        message="REQUIERE CONFIGURACION EXTERNA: credenciales de Onshape en el backend",
        error={
            "code": "ONSHAPE_CONFIGURATION_REQUIRED",
            "message": "Configure backend Onshape credentials before running this job",
        },
    )


def ejecutar_optimizacion(job: JobStatus, request: OptimizationRequest) -> None:
    try:
        job.update(status="processing", progress=5, message="Iniciando procesamiento de geometria")
        if not verificar_credenciales():
            set_configuration_pending(job)
            return

        processor = GeometryProcessor(
            obtener_sesion_onshape(),
            request.documentId,
            request.workspaceId,
            request.elementId,
        )
        job.update(status="processing", progress=15, message="Descargando geometria de Onshape")
        geo_result = processor.process_full_pipeline()
        if not geo_result.get("success"):
            geo_status = geo_result.get("status", "pending")
            job.update(
                status=geo_status,
                progress=20,
                message=geo_result.get("error", "Geometry stage is not available"),
                error={
                    "code": geo_result.get("code", "GEOMETRY_STAGE_UNAVAILABLE"),
                    "message": geo_result.get("error", "Geometry stage is not available"),
                },
                finished=geo_status == "failed",
            )
            return

        job.update(status="processing", progress=30, message="Ejecutando solver")
        topopt_result = run_topology_optimization(
            volume_fraction=request.topologyConfig.optimization.volumeFraction,
            max_iterations=request.topologyConfig.optimization.maxIterations,
            forces=None,
            supports=None,
        )
        if not topopt_result.get("success") or topopt_result.get("status") != "completed":
            job.update(
                status=topopt_result.get("status", "pending"),
                progress=30,
                message=topopt_result.get("error", "TopOpt stage is not available"),
                error={
                    "code": topopt_result.get("code", "TOPOPT_STAGE_UNAVAILABLE"),
                    "message": topopt_result.get("error", "TopOpt stage is not available"),
                },
            )
            return

        job.update(
            status="completed",
            progress=100,
            message="Optimizacion completada",
            result=topopt_result,
            finished=True,
        )
    except Exception:
        logger.exception("[%s] job failed", job.job_id)
        job.update(
            status="failed",
            message="Error interno procesando el trabajo",
            error={"code": "INTERNAL_JOB_ERROR", "message": "Internal job error"},
            finished=True,
        )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    credentials_ready = verificar_credenciales()
    return {
        "status": "ok" if credentials_ready else "error",
        "credenciales_configuradas": credentials_ready,
        "message": "API de Optimizacion Topologica operativa",
    }


@app.post("/api/optimize", response_model=OptimizationResponse)
async def optimizar_topologia(
    request: OptimizationRequest, background_tasks: BackgroundTasks
) -> OptimizationResponse:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = JobStatus(job_id, request)
    JOBS[job_id] = job
    background_tasks.add_task(ejecutar_optimizacion, job, request)
    return OptimizationResponse(
        status="queued",
        message="Optimizacion encolada - monitorear con /api/optimize/status",
        jobId=job_id,
        data={
            "config_recibida": {
                "anchors_count": len(request.topologyConfig.anchors),
                "volume_fraction": request.topologyConfig.optimization.volumeFraction,
                "max_iterations": request.topologyConfig.optimization.maxIterations,
            },
            "documentId": request.documentId,
            "status_url": f"/api/optimize/status?jobId={job_id}",
        },
    )


@app.get("/api/optimize/status", response_model=JobStatusResponse)
async def estado_optimizacion(jobId: str) -> JobStatusResponse:
    with db_connection() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (jobId,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return row_to_response(row)


@app.get("/api/jobs")
async def listar_trabajos() -> Dict[str, Any]:
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT job_id, status, progress, document_id FROM jobs ORDER BY created_at DESC"
        ).fetchall()
    return {
        "total_jobs": len(rows),
        "jobs": {
            row["job_id"]: {
                "status": row["status"],
                "progress": row["progress"],
                "document": row["document_id"],
            }
            for row in rows
        },
    }


@app.get("/api/docs")
async def documentacion() -> Dict[str, Any]:
    return {
        "nombre": "API de Optimizacion Topologica",
        "version": "1.1.0",
        "note": "MVP: mesher y solver FEA reales requieren configuracion externa",
        "endpoints": {
            "POST /api/optimize": {"descripcion": "Envia un trabajo de optimizacion"},
            "GET /api/optimize/status": {"descripcion": "Consulta el estado de un trabajo"},
            "GET /api/jobs": {"descripcion": "Lista trabajos persistentes"},
            "GET /health": {"descripcion": "Verifica la API y configuracion"},
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
