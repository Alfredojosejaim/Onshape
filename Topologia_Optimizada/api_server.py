"""FastAPI backend for Onshape topology optimization.

Handles OAuth 2.0 sessions, Onshape Part Studio querying, STEP geometry download
and tessellation for Three.js, real volumetric FEM meshing, boundary conditions,
and job persistence in SQLite.
"""

import base64
import json
import logging
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from dotenv import find_dotenv, load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from geometry_processor import GeometryProcessor
from onshape_client import OAuthTokenStore, OnshapeAPIError, OnshapeClient
from topopt_solver import run_topology_optimization

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

app = FastAPI(title="Optimizacion Topologica API", version="1.3.0")
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
                step_cache BLOB,
                tessellation_json TEXT,
                mesh_json TEXT,
                forces_json TEXT,
                constraints_json TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        session_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(oauth_sessions)").fetchall()
        }
        for col, col_type in [
            ("step_cache", "BLOB"),
            ("tessellation_json", "TEXT"),
            ("mesh_json", "TEXT"),
            ("forces_json", "TEXT"),
            ("constraints_json", "TEXT"),
        ]:
            if col not in session_columns:
                connection.execute(f"ALTER TABLE oauth_sessions ADD COLUMN {col} {col_type}")

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

    @model_validator(mode="after")
    def context_is_complete(self) -> "OptimizationRequest":
        required = ("documentId", "workspaceId", "elementId")
        if any(not self.topologyConfig.context.get(key) for key in required):
            raise ValueError("context requires documentId, workspaceId and elementId")
        return self


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
        context = request.topologyConfig.context
        self.document_id = context["documentId"]
        self.workspace_id = context["workspaceId"]
        self.element_id = context["elementId"]
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


# --- Application Endpoints ---

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


@app.get("/app")
async def optimization_interface() -> FileResponse:
    return FileResponse("optimization-app.html")


@app.get("/app/")
async def optimization_interface_trailing() -> FileResponse:
    return FileResponse("optimization-app.html")


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
    response = RedirectResponse("/app", status_code=303)
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
    return {
        "status": "saved",
        "context": {key: context[key] for key in required},
        "message": "Contexto CAD guardado correctamente",
    }


@app.get("/api/partstudios/parts")
async def get_partstudio_parts(
    request: Request,
    document_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    element_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch the real list of parts/bodies in the active Part Studio from Onshape."""
    session_id = authenticated_session_id(request)
    if not oauth_configured():
        raise HTTPException(status_code=503, detail="OAuth no configurado en backend")

    # If context is not fully passed in query parameters, fallback to saved session context
    if not (document_id and workspace_id and element_id):
        with db_connection() as connection:
            row = connection.execute(
                "SELECT document_id, workspace_id, element_id FROM oauth_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row and row["document_id"] and row["workspace_id"] and row["element_id"]:
                document_id = document_id or row["document_id"]
                workspace_id = workspace_id or row["workspace_id"]
                element_id = element_id or row["element_id"]

    if not (document_id and workspace_id and element_id):
        raise HTTPException(status_code=400, detail="Faltan documentId, workspaceId o elementId")

    client = onshape_client(request)
    processor = GeometryProcessor(client, document_id, workspace_id, element_id)

    try:
        parts = processor.get_parts_list()
        return {
            "status": "success",
            "context": {
                "documentId": document_id,
                "workspaceId": workspace_id,
                "elementId": element_id,
            },
            "parts": parts,
            "count": len(parts),
        }
    except OnshapeAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
    except Exception as exc:
        logger.exception("Error al consultar lista de piezas en Part Studio")
        raise HTTPException(status_code=500, detail={"code": "ONSHAPE_PARTS_QUERY_ERROR", "message": str(exc)}) from exc


@app.post("/api/geometry/selection")
async def save_geometry_selection(request: Request, selection: GeometrySelection) -> Dict[str, Any]:
    session_id = authenticated_session_id(request)
    required = ("documentId", "workspaceId", "elementId")
    if any(not selection.context.get(key) for key in required):
        raise HTTPException(status_code=422, detail="context requires documentId, workspaceId and elementId")
    with db_connection() as connection:
        connection.execute(
            "UPDATE oauth_sessions SET document_id=?, workspace_id=?, element_id=?, updated_at=? "
            "WHERE session_id=?",
            (selection.context["documentId"], selection.context["workspaceId"], selection.context["elementId"], utc_now(), session_id),
        )
    return {
        "status": "received",
        "message": "Selección de geometría recibida correctamente",
        "selection": {
            "designSpace_count": len(selection.designSpace),
            "keepOut_count": len(selection.keepOut),
            "context": selection.context,
        },
        "next_step": "geometry_download",
    }


@app.post("/api/geometry/download")
async def download_geometry(request: Request, selection: GeometrySelection) -> Dict[str, Any]:
    """Download real STEP from Onshape and perform CAD tessellation for Three.js."""
    session_id = authenticated_session_id(request)
    if not oauth_configured():
        raise HTTPException(status_code=503, detail="OAuth no configurado en backend")

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
        selection.context["documentId"],
        selection.context["workspaceId"],
        selection.context["elementId"],
    )

    try:
        # If user selected specific part IDs, pass them; if "all" or entire studio, part_ids is None
        part_ids = [p.strip() for p in selection.designSpace if p and p.strip() and p.strip().lower() != "all"]
        step_data = processor.download_part_studio(output_format="step", part_ids=part_ids or None)
        if not step_data:
            raise HTTPException(
                status_code=500,
                detail={"code": "GEOMETRY_DOWNLOAD_FAILED", "message": "No se pudo descargar STEP desde Onshape"},
            )

        tess_result = processor.tessellate_step(step_data)
        if not tess_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail={"code": tess_result.get("code", "STEP_TESSELLATION_FAILED"), "message": tess_result.get("error", "Error procesando STEP")},
            )

        properties = processor.get_part_properties()

        # Cache step and tessellation in SQLite session
        with db_connection() as connection:
            connection.execute(
                "UPDATE oauth_sessions SET step_cache=?, tessellation_json=?, updated_at=? WHERE session_id=?",
                (step_data, json.dumps(tess_result), utc_now(), session_id),
            )

        return {
            "status": "success",
            "message": "Geometría STEP descargada y procesada correctamente",
            "geometry": {
                "format": "step",
                "size_bytes": len(step_data),
                "properties": properties,
                "tessellation": tess_result,
            },
            "selection": {
                "designSpace": selection.designSpace,
                "keepOut": selection.keepOut,
            },
            "next_step": "meshing",
        }
    except OnshapeAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error descargando y procesando geometría")
        raise HTTPException(status_code=500, detail={"code": "GEOMETRY_PROCESSING_ERROR", "message": str(exc)}) from exc


@app.get("/api/geometry/current")
async def get_current_geometry(request: Request) -> Dict[str, Any]:
    """Retrieve the cached real CAD tessellation for the 3D viewer."""
    session_id = authenticated_session_id(request)
    with db_connection() as connection:
        row = connection.execute(
            "SELECT tessellation_json, document_id, workspace_id, element_id FROM oauth_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if not row or not row["tessellation_json"]:
        return {"status": "no_geometry", "message": "No hay geometría cargada en la sesión"}
    return {
        "status": "success",
        "tessellation": json.loads(row["tessellation_json"]),
        "context": {
            "documentId": row["document_id"],
            "workspaceId": row["workspace_id"],
            "elementId": row["element_id"],
        },
    }


@app.post("/api/mesh/generate")
async def generate_mesh(request: Request, mesh_request: MeshRequest) -> Dict[str, Any]:
    """Generate volumetric finite element mesh (nodes & elements) from STEP."""
    session_id = authenticated_session_id(request)

    step_bytes: Optional[bytes] = None
    if mesh_request.step_data:
        try:
            step_bytes = base64.b64decode(mesh_request.step_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato Base64 de STEP inválido")
    else:
        with db_connection() as connection:
            row = connection.execute(
                "SELECT step_cache FROM oauth_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row and row["step_cache"]:
                step_bytes = row["step_cache"]

    if not step_bytes:
        raise HTTPException(status_code=400, detail="No se encontró geometría STEP para mallar")

    processor = GeometryProcessor(None, "", "", "")
    mesh_result = processor.create_mesh(
        step_bytes,
        target_element_size=mesh_request.target_element_size,
        element_type=mesh_request.element_type,
    )

    if not mesh_result.get("success"):
        return {
            "status": "failed",
            "message": mesh_result.get("error", "Fallo al generar la malla"),
            "code": mesh_result.get("code", "MESHER_FAILED"),
        }

    # Cache mesh in session
    with db_connection() as connection:
        connection.execute(
            "UPDATE oauth_sessions SET mesh_json=?, updated_at=? WHERE session_id=?",
            (json.dumps(mesh_result), utc_now(), session_id),
        )

    return {
        "status": "success",
        "message": "Malla volumétrica generada correctamente",
        "mesh": {
            "num_nodes": mesh_result["num_nodes"],
            "num_elements": mesh_result["num_elements"],
            "element_type": mesh_result["element_type"],
            "nodes": mesh_result["nodes"],
            "elements": mesh_result["elements"],
        },
        "next_step": "boundary_conditions",
    }


@app.post("/api/boundary/forces")
async def save_forces(request: Request, forces: List[ForceDefinition]) -> Dict[str, Any]:
    session_id = authenticated_session_id(request)
    forces_data = [f.model_dump() for f in forces]
    with db_connection() as connection:
        connection.execute(
            "UPDATE oauth_sessions SET forces_json=?, updated_at=? WHERE session_id=?",
            (json.dumps(forces_data), utc_now(), session_id),
        )
    return {
        "status": "saved",
        "message": f"{len(forces)} fuerza(s) guardada(s) correctamente",
        "forces_count": len(forces),
        "forces": forces_data,
    }


@app.post("/api/boundary/constraints")
async def save_constraints(request: Request, constraints: List[ConstraintDefinition]) -> Dict[str, Any]:
    session_id = authenticated_session_id(request)
    constraints_data = [c.model_dump() for c in constraints]
    with db_connection() as connection:
        connection.execute(
            "UPDATE oauth_sessions SET constraints_json=?, updated_at=? WHERE session_id=?",
            (json.dumps(constraints_data), utc_now(), session_id),
        )
    return {
        "status": "saved",
        "message": f"{len(constraints)} restricción(es) guardada(s) correctamente",
        "constraints_count": len(constraints),
        "constraints": constraints_data,
    }


@app.get("/api/boundary/summary")
async def get_boundary_summary(request: Request) -> Dict[str, Any]:
    session_id = authenticated_session_id(request)
    with db_connection() as connection:
        row = connection.execute(
            "SELECT forces_json, constraints_json FROM oauth_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    forces = json.loads(row["forces_json"]) if row and row["forces_json"] else []
    constraints = json.loads(row["constraints_json"]) if row and row["constraints_json"] else []
    return {
        "status": "ready",
        "forces": {"count": len(forces), "items": forces},
        "constraints": {"count": len(constraints), "items": constraints},
        "message": f"{len(forces)} cargas y {len(constraints)} fijaciones configuradas",
    }


@app.post("/api/study/validate")
async def validate_study(config: TopologyConfig, request: Request) -> Dict[str, Any]:
    authenticated_session_id(request)
    missing = []
    if not config.designSpace.preserve:
        missing.append("Geometría a conservar")
    if not config.loadCases:
        missing.append("Caso de carga")
    else:
        if not any(case.constraints for case in config.loadCases):
            missing.append("Restricción")
        if not any(case.loads for case in config.loadCases):
            missing.append("Carga")
    if not config.material:
        missing.append("Material")
    context_keys = ("documentId", "workspaceId", "elementId")
    if any(not config.context.get(key) for key in context_keys):
        missing.append("Contexto CAD")
    return {"valid": not missing, "missing": missing}


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    credentials_ready = oauth_configured()
    return {
        "status": "ok" if credentials_ready else "error",
        "oauth_configurado": credentials_ready,
        "message": "API de Optimizacion Topologica operativa",
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
