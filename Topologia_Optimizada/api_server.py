import os
import sys
import json
import logging
import requests
import asyncio
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import uuid

# Importar módulos de optimización
from topopt_solver import TopOptSolver, run_topology_optimization
from geometry_processor import GeometryProcessor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv(find_dotenv())

app = FastAPI(title="Optimización Topológica API", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominio de Onshape
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de credenciales
ACCESS_KEY = os.getenv('ONSHAPE_ACCESS_KEY') or os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('ONSHAPE_SECRET_KEY') or os.getenv('SECRET_KEY')
DID = os.getenv('DID')
WID = os.getenv('WID')
MID = os.getenv('MID') or os.getenv('EID')

# Estado global de trabajos
JOBS = {}  # jobId -> job_status

class JobStatus:
    """Almacena el estado de una tarea de optimización."""
    def __init__(self, job_id: str, document_id: str):
        self.job_id = job_id
        self.document_id = document_id
        self.status = "queued"  # queued, processing, completed, failed
        self.progress = 0
        self.message = "En cola de espera"
        self.start_time = datetime.now()
        self.end_time = None
        self.result = None
        self.error = None
    
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'document_id': self.document_id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'result': self.result
        }


# Modelos Pydantic
class Load(BaseModel):
    directionX: float
    directionY: float
    directionZ: float
    magnitude: Any  # Puede ser string o número
    unit: str


class Optimization(BaseModel):
    volumeFraction: float
    maxIterations: int


class TopologyConfig(BaseModel):
    schemaVersion: str
    anchors: list = Field(default_factory=list)
    loads: list[Load]
    optimization: Optimization
    timestamp: Optional[str] = None


class OptimizationRequest(BaseModel):
    documentId: str
    workspaceId: str
    elementId: str
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


# Verificación de credenciales
def verificar_credenciales() -> bool:
    """Verifica que todas las credenciales estén configuradas."""
    if not all([ACCESS_KEY, SECRET_KEY, DID, WID, MID]):
        print("❌ ERROR: Faltan credenciales en .env")
        print(f"   ACCESS_KEY: {bool(ACCESS_KEY)}")
        print(f"   SECRET_KEY: {bool(SECRET_KEY)}")
        print(f"   DID: {bool(DID)}")
        print(f"   WID: {bool(WID)}")
        print(f"   MID: {bool(MID)}")
        return False
    return True


# Sesión de Onshape API
def obtener_sesion_onshape() -> requests.Session:
    """Crea una sesión autenticada con la API de Onshape."""
    session = requests.Session()
    session.auth = (ACCESS_KEY, SECRET_KEY)
    session.headers.update({
        'Accept': 'application/vnd.onshape.v2+json',
        'Content-Type': 'application/json'
    })
    return session


# Ejecutar optimización en background
async def ejecutar_optimizacion(job: JobStatus, request: OptimizationRequest):
    """Ejecuta la optimización topológica en background."""
    try:
        job.status = "processing"
        job.message = "Iniciando procesamiento de geometría..."
        job.progress = 10
        logger.info(f"[{job.job_id}] Iniciando optimización")
        
        # Crear sesión de Onshape
        session = obtener_sesion_onshape()
        
        # Procesar geometría
        geo_processor = GeometryProcessor(
            session,
            request.documentId,
            request.workspaceId,
            request.elementId
        )
        
        job.message = "Descargando y procesando geometría..."
        job.progress = 20
        logger.info(f"[{job.job_id}] Descargando Part Studio")
        
        # Descargar y procesar
        geo_result = geo_processor.process_full_pipeline(
            target_element_size=1.0,
            output_file=None
        )
        
        if not geo_result['success']:
            raise Exception(f"Error procesando geometría: {geo_result.get('error')}")
        
        # Extraer parámetros de optimización
        config = request.topologyConfig
        volume_fraction = config.optimization.volumeFraction
        max_iterations = config.optimization.maxIterations
        
        job.message = "Ejecutando análisis de optimización topológica..."
        job.progress = 30
        logger.info(f"[{job.job_id}] Iniciando TopOpt")
        
        # Crear callback para actualizar progreso
        def topopt_callback(progress_data):
            job.progress = 30 + int((progress_data['progress'] / 100) * 60)  # 30-90%
            job.message = (
                f"TopOpt: Iter {progress_data['iteration']}, "
                f"Cambio={progress_data['change']:.4f}"
            )
            logger.info(f"[{job.job_id}] {job.message}")
        
        # Ejecutar optimización topológica
        topopt_result = run_topology_optimization(
            volume_fraction=volume_fraction,
            max_iterations=max_iterations,
            nelx=20,
            nely=20,
            nelz=None,  # 2D por ahora
            callback=topopt_callback
        )
        
        job.progress = 90
        job.message = "Reconstruyendo geometría optimizada..."
        logger.info(f"[{job.job_id}] Reconstruyendo geometría")
        
        # Reconstruir geometría optimizada
        if 'geometry' in topopt_result:
            geo_optimized = topopt_result['geometry']
            logger.info(
                f"[{job.job_id}] Geometría optimizada: "
                f"{geo_optimized['num_active']} elementos activos de {geo_optimized['num_total']}"
            )
        
        # Preparar resultado final
        job.progress = 100
        job.status = "completed"
        job.message = "✓ Optimización completada exitosamente"
        job.end_time = datetime.now()
        job.result = {
            'iterations': topopt_result['iterations'],
            'final_compliance': topopt_result['final_compliance'],
            'final_volume_fraction': topopt_result['final_volume_fraction'],
            'geometry_stats': topopt_result.get('geometry', {}),
            'mesh_info': geo_result['mesh'],
            'download_url': f"/api/result/{job.job_id}/geometry.step"
        }
        
        logger.info(f"[{job.job_id}] ✓ OPTIMIZACIÓN COMPLETADA")
        
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.message = f"❌ Error: {str(e)}"
        job.end_time = datetime.now()
        logger.error(f"[{job.job_id}] ❌ Error: {e}", exc_info=True)


# Endpoints
@app.get("/health")
async def health_check():
    """Verifica el estado de la API."""
    credenciales_ok = verificar_credenciales()
    return {
        "status": "ok" if credenciales_ok else "error",
        "credenciales_configuradas": credenciales_ok,
        "message": "API de Optimización Topológica operativa"
    }


@app.post("/api/optimize", response_model=OptimizationResponse)
async def optimizar_topologia(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """
    Endpoint principal para ejecutar optimización topológica.
    Lanza una tarea en background y retorna jobId para polling.
    """
    try:
        # Validar credenciales
        if not verificar_credenciales():
            raise HTTPException(
                status_code=500,
                detail="Credenciales de Onshape no configuradas"
            )
        
        # Validar datos de entrada
        config = request.topologyConfig
        
        if config.optimization.volumeFraction < 0 or config.optimization.volumeFraction > 1:
            raise HTTPException(
                status_code=400,
                detail="volumeFraction debe estar entre 0 y 1"
            )
        
        if config.optimization.maxIterations <= 0:
            raise HTTPException(
                status_code=400,
                detail="maxIterations debe ser mayor a 0"
            )
        
        # Crear Job ID único
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = JobStatus(job_id, request.documentId)
        JOBS[job_id] = job
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📨 SOLICITUD DE OPTIMIZACIÓN RECIBIDA - Job {job_id}")
        logger.info(f"{'='*60}")
        logger.info(f"Documento: {request.documentId}")
        logger.info(f"Workspace: {request.workspaceId}")
        logger.info(f"Elemento: {request.elementId}")
        logger.info(f"Anclajes: {len(config.anchors)}")
        logger.info(f"Carga: {config.loads[0].magnitude} {config.loads[0].unit}")
        logger.info(f"Dirección: ({config.loads[0].directionX:.3f}, "
                   f"{config.loads[0].directionY:.3f}, "
                   f"{config.loads[0].directionZ:.3f})")
        logger.info(f"Fracción volumen: {config.optimization.volumeFraction}")
        logger.info(f"Máx iteraciones: {config.optimization.maxIterations}")
        logger.info(f"{'='*60}\n")
        
        # Lanzar optimización en background
        background_tasks.add_task(ejecutar_optimizacion, job, request)
        
        return OptimizationResponse(
            status="queued",
            message="Optimización encolada - monitorear con /api/optimize/status",
            jobId=job_id,
            data={
                "config_recibida": {
                    "anchors_count": len(config.anchors),
                    "volume_fraction": config.optimization.volumeFraction,
                    "max_iterations": config.optimization.maxIterations
                },
                "documentId": request.documentId,
                "status_url": f"/api/optimize/status?jobId={job_id}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en optimización: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@app.get("/api/optimize/status")
async def estado_optimizacion(jobId: str) -> JobStatusResponse:
    """
    Consulta el estado de una tarea de optimización en ejecución.
    
    Retorna:
    - status: "queued", "processing", "completed", "failed"
    - progress: Porcentaje de avance (0-100)
    - result: Datos del resultado cuando está completado
    """
    if jobId not in JOBS:
        raise HTTPException(
            status_code=404,
            detail=f"Job {jobId} no encontrado"
        )
    
    job = JOBS[jobId]
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        result=job.result
    )


@app.get("/api/jobs")
async def listar_trabajos():
    """Lista todos los trabajos (para debugging)."""
    return {
        "total_jobs": len(JOBS),
        "jobs": {
            jid: {
                "status": j.status,
                "progress": j.progress,
                "document": j.document_id
            }
            for jid, j in JOBS.items()
        }
    }


@app.get("/api/docs")
async def documentacion():
    """Retorna la documentación de la API."""
    return {
        "nombre": "API de Optimización Topológica",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/optimize": {
                "descripcion": "Envía un trabajo de optimización topológica",
                "parametros": {
                    "documentId": "ID del documento de Onshape",
                    "workspaceId": "ID del workspace",
                    "elementId": "ID del Part Studio",
                    "topologyConfig": "Configuración del feature"
                }
            },
            "GET /api/optimize/status": {
                "descripcion": "Consulta el estado de una optimización",
                "parametros": {
                    "jobId": "ID de la tarea"
                }
            },
            "GET /health": {
                "descripcion": "Verifica el estado de la API"
            }
        }
    }


if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("🚀 INICIANDO SERVIDOR DE OPTIMIZACIÓN TOPOLÓGICA")
    logger.info("="*60)
    logger.info(f"Versión: 1.0.0")
    logger.info(f"Motor: TopOpt SIMP")
    logger.info(f"Backend: FastAPI + Uvicorn")
    logger.info(f"Puerto: 8000")
    
    if verificar_credenciales():
        logger.info("✓ Credenciales de Onshape configuradas correctamente")
    else:
        logger.warning("⚠ ADVERTENCIA: Falta configurar credenciales en .env")
        logger.warning("  Las siguientes variables son requeridas:")
        logger.warning("  - ONSHAPE_ACCESS_KEY o ACCESS_KEY")
        logger.warning("  - ONSHAPE_SECRET_KEY o SECRET_KEY")
        logger.warning("  - DID (Document ID)")
        logger.warning("  - WID (Workspace ID)")
        logger.warning("  - MID (Part Studio ID)")
    
    logger.info("\n📚 Documentación disponible en:")
    logger.info("  - API Docs: http://localhost:8000/docs")
    logger.info("  - ReDoc: http://localhost:8000/redoc")
    logger.info("  - Health: http://localhost:8000/health")
    logger.info("="*60 + "\n")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
