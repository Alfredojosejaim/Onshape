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
from urllib.parse import urlencode
import secrets
import time

from dotenv import find_dotenv, load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from geometry_processor import GeometryProcessor
from topopt_solver import run_topology_optimization
from onshape_client import OAuthTokenStore, OnshapeAPIError, OnshapeClient

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("JOB_DB_PATH", "jobs.sqlite3")
OAUTH_CLIENT_ID = os.getenv("ONSHAPE_OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.getenv("ONSHAPE_OAUTH_CLIENT_SECRET", "")
OAUTH_REDIRECT_URI = os.getenv("ONSHAPE_OAUTH_REDIRECT_URI", "https://localhost:8000/oauth/callback")
OAUTH_SCOPES = os.getenv("ONSHAPE_OAUTH_SCOPES", "OAuth2Read OAuth2Write")
OAUTH_AUTHORIZE_URL = "https://oauth.onshape.com/oauth/authorize"
OAUTH_TOKEN_URL = "https://oauth.onshape.com/oauth/token"
OAUTH_API_URL = "https://cad.onshape.com/api"
SESSION_COOKIE = "topologia_session"

app = FastAPI(title="Optimizacion Topologica API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "https://localhost:8000").split(","),
    allow_credentials=True,
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
                session_id TEXT,
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
        job_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
        }
        if "session_id" not in job_columns:
            connection.execute("ALTER TABLE jobs ADD COLUMN session_id TEXT")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_sessions (
                session_id TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at REAL NOT NULL,
                token_type TEXT NOT NULL,
                scope TEXT,
                user_json TEXT,
                document_id TEXT,
                workspace_id TEXT,
                element_id TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )


init_database()


class SQLiteTokenStore(OAuthTokenStore):
    def get_token(self, session_id: str) -> Optional[Dict[str, Any]]:
        with db_connection() as connection:
            row = connection.execute(
                "SELECT access_token, refresh_token, expires_at, token_type, scope "
                "FROM oauth_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def save_token(self, session_id: str, token: Dict[str, Any]) -> None:
        with db_connection() as connection:
            connection.execute(
                """
                INSERT INTO oauth_sessions
                (session_id, access_token, refresh_token, expires_at, token_type, scope, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    access_token=excluded.access_token,
                    refresh_token=excluded.refresh_token,
                    expires_at=excluded.expires_at,
                    token_type=excluded.token_type,
                    scope=excluded.scope,
                    updated_at=excluded.updated_at
                """,
                (
                    session_id,
                    token["access_token"],
                    token.get("refresh_token"),
                    token["expires_at"],
                    token.get("token_type", "Bearer"),
                    token.get("scope"),
                    utc_now(),
                ),
            )


token_store = SQLiteTokenStore()


def session_id_from_request(request: Request) -> str:
    return request.cookies.get(SESSION_COOKIE) or secrets.token_urlsafe(32)


def authenticated_session_id(request: Request) -> str:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id or not token_store.get_token(session_id):
        raise HTTPException(status_code=401, detail="Onshape OAuth authentication is required")
    return session_id


def oauth_configured() -> bool:
    return bool(OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET and OAUTH_REDIRECT_URI)


def onshape_client(request: Request) -> OnshapeClient:
    return OnshapeClient(
        token_store,
        session_id_from_request(request),
        OAUTH_CLIENT_ID,
        OAUTH_CLIENT_SECRET,
        token_url=OAUTH_TOKEN_URL,
        api_url=OAUTH_API_URL,
    )


def set_session_cookie(response: RedirectResponse, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "true").lower() == "true",
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )


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
    timestamp: str = Field(default_factory=utc_now)


class OptimizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documentId: str = Field(min_length=1, max_length=256)
    workspaceId: str = Field(min_length=1, max_length=256)
    elementId: str = Field(min_length=1, max_length=256)
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
    """A small persistent view of one job."""

    def __init__(self, job_id: str, request: OptimizationRequest, session_id: str):
        self.job_id = job_id
        self.session_id = session_id
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
                (job_id, session_id, document_id, workspace_id, element_id, request_json,
                 status, progress, message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    self.session_id,
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


@app.get("/login")
async def login(request: Request) -> RedirectResponse:
    if not oauth_configured():
        raise HTTPException(status_code=503, detail="OAuth is not configured")
    session_id = session_id_from_request(request)
    state = secrets.token_urlsafe(32)
    with db_connection() as connection:
        connection.execute("DELETE FROM oauth_states WHERE expires_at < ?", (time.time(),))
        connection.execute(
            "INSERT INTO oauth_states (state, session_id, expires_at) VALUES (?, ?, ?)",
            (state, session_id, time.time() + 600),
        )
    query = urlencode(
        {
            "client_id": OAUTH_CLIENT_ID,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": OAUTH_SCOPES,
            "state": state,
        }
    )
    response = RedirectResponse(f"{OAUTH_AUTHORIZE_URL}?{query}", status_code=302)
    set_session_cookie(response, session_id)
    return response


@app.get("/")
async def local_interface() -> FileResponse:
    return FileResponse("app-extension.html")


@app.get("/oauth/callback")
async def oauth_callback(
    request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=401, detail=f"Onshape authorization denied: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="OAuth callback requires code and state")
    session_id = session_id_from_request(request)
    with db_connection() as connection:
        state_row = connection.execute(
            "SELECT session_id, expires_at FROM oauth_states WHERE state = ?", (state,)
        ).fetchone()
        connection.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    if state_row is None or state_row["session_id"] != session_id or state_row["expires_at"] < time.time():
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    client = OnshapeClient(
        token_store,
        session_id,
        OAUTH_CLIENT_ID,
        OAUTH_CLIENT_SECRET,
        token_url=OAUTH_TOKEN_URL,
        api_url=OAUTH_API_URL,
    )
    try:
        client.exchange_code(code, OAUTH_REDIRECT_URI)
        user = client.get_json("/users/sessioninfo")
    except OnshapeAPIError as exc:
        raise HTTPException(status_code=502, detail={"code": exc.code, "message": exc.message}) from exc
    with db_connection() as connection:
        connection.execute(
            "UPDATE oauth_sessions SET user_json = ?, updated_at = ? WHERE session_id = ?",
            (json.dumps(user), utc_now(), session_id),
        )
    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, session_id)
    return response


@app.post("/api/auth/logout")
async def auth_logout(request: Request) -> RedirectResponse:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        with db_connection() as connection:
            connection.execute("DELETE FROM oauth_sessions WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM oauth_states WHERE session_id = ?", (session_id,))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/api/auth/status")
async def auth_status(request: Request) -> Dict[str, Any]:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return {"authenticated": False, "status": "disconnected"}
    with db_connection() as connection:
        row = connection.execute(
            "SELECT user_json, expires_at, document_id, workspace_id, element_id "
            "FROM oauth_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        return {"authenticated": False, "status": "disconnected"}
    return {
        "authenticated": True,
        "status": "connected",
        "user": json.loads(row["user_json"]) if row["user_json"] else None,
        "token_expires_at": row["expires_at"],
        "context": {
            "documentId": row["document_id"],
            "workspaceId": row["workspace_id"],
            "elementId": row["element_id"],
        },
    }


@app.get("/api/onshape/documents")
async def list_onshape_documents(request: Request) -> Any:
    authenticated_session_id(request)
    try:
        return onshape_client(request).get_json("/documents")
    except OnshapeAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@app.post("/api/context")
async def save_context(request: Request, context: Dict[str, str]) -> Dict[str, Any]:
    required = ("documentId", "workspaceId", "elementId")
    if any(not context.get(key) for key in required):
        raise HTTPException(status_code=422, detail="documentId, workspaceId and elementId are required")
    session_id = authenticated_session_id(request)
    with db_connection() as connection:
        connection.execute(
            "UPDATE oauth_sessions SET document_id=?, workspace_id=?, element_id=?, updated_at=? "
            "WHERE session_id=?",
            (context["documentId"], context["workspaceId"], context["elementId"], utc_now(), session_id),
        )
    return {"status": "saved", "context": {key: context[key] for key in required}}


def ejecutar_optimizacion(job: JobStatus, request: OptimizationRequest, session_id: str) -> None:
    try:
        job.update(status="processing", progress=5, message="Iniciando procesamiento de geometria")
        if not oauth_configured() or not token_store.get_token(session_id):
            set_configuration_pending(job)
            return

        client = OnshapeClient(
            token_store,
            session_id,
            OAUTH_CLIENT_ID,
            OAUTH_CLIENT_SECRET,
            token_url=OAUTH_TOKEN_URL,
            api_url=OAUTH_API_URL,
        )
        processor = GeometryProcessor(
            client,
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
    credentials_ready = oauth_configured()
    return {
        "status": "ok" if credentials_ready else "error",
        "oauth_configurado": credentials_ready,
        "message": "API de Optimizacion Topologica operativa",
    }


@app.post("/api/optimize", response_model=OptimizationResponse)
async def optimizar_topologia(
    request: OptimizationRequest, background_tasks: BackgroundTasks, http_request: Request
) -> OptimizationResponse:
    session_id = authenticated_session_id(http_request)
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = JobStatus(job_id, request, session_id)
    JOBS[job_id] = job
    background_tasks.add_task(ejecutar_optimizacion, job, request, session_id)
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
async def estado_optimizacion(jobId: str, request: Request) -> JobStatusResponse:
    session_id = authenticated_session_id(request)
    with db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ? AND session_id = ?",
            (jobId, session_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return row_to_response(row)


@app.get("/api/jobs")
async def listar_trabajos(request: Request) -> Dict[str, Any]:
    session_id = authenticated_session_id(request)
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT job_id, status, progress, document_id FROM jobs "
            "WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
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

    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        ssl_certfile=os.getenv("SSL_CERTFILE") or None,
        ssl_keyfile=os.getenv("SSL_KEYFILE") or None,
    )
