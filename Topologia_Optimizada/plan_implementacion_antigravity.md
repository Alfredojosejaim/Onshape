Migración Arquitectónica: CAD-Agnostic Core + CAD Connectors
Este plan detalla la migración arquitectónica del proyecto Topologia_Optimizada desde un enfoque centrado en Onshape hacia una arquitectura modular desacoplada: CAD-Agnostic Core + CAD Adapters + CAD Connectors, permitiendo el uso de la aplicación en modo Standalone (mediante archivos STEP) y preservando Onshape como un conector independiente.

User Review Required
IMPORTANT

Independencia del Core: Ningún archivo dentro de core/ importará ni dependerá de OnshapeClient, credenciales OAuth, ni IDs propietarios de Onshape (documentId, workspaceId, elementId).
Modo Standalone: Se agrega soporte completo para importar archivos STEP directamente desde la interfaz web sin requerir credenciales ni conexión a Onshape.
Compatibilidad Hacia Atrás: Se mantienen los módulos raíz (geometry_processor.py, onshape_client.py, topopt_solver.py, api_server.py) y endpoints existentes para evitar regresiones con integraciones existentes.
Sin Solver FEA / SIMP definitivo: Conforme a la especificación, esta iteración no implementa Gmsh definitivo ni FEA/SIMP real, dejando preparada la arquitectura para la etapa posterior: STEP → CADModel → Gmsh → Tet4 → FEA → SIMP.
Proposed Architecture
CAD-Agnostic Core
CAD Adapters
CAD Connectors
Application Layer (FastAPI & Services)
Frontend
Upload STEP / Configure
OAuth / Select Parts
Export STEP bytes
Standalone UI (/app)
Onshape App Extension (/)
API Server (api_server.py)
CAD Service (services/cad_service.py)
Study Service (services/study_service.py)
Onshape Connector (connectors/onshape/)
OAuth Client & Session Store
STEP Adapter (adapters/cad/step_adapter.py)
(Future) IGES Adapter
CADModel / CADSolid / CADFace (core/models.py)
Geometry Engine (core/geometry.py)
Provisional Mesher (core/meshing.py)
Boundary Condition Mapper (core/boundary.py)
Study / Material / Loads (core/study.py)
TopOpt / FEA Interfaces (core/solver_interface.py)
Proposed Changes
1. CAD-Agnostic Core Layer (core/)
[NEW] 
core/
init
.py
Exports the public Core domain interfaces and models.

[NEW] 
core/models.py
Agnostic internal domain models:

BoundingBox3D: Bounding box dimensions, extents, and helpers.
CADVertex, CADEdge, CADFace: Internal representations with geometric metadata (normals, centers, areas, bounding box, internal IDs like face_0, face_1).
CADSolid: Solid volume, name, internal ID, child faces.
SourceReference: Origin tracking (source_type="step"|"onshape"|"upload", source_id, filename, metadata).
CADModel: Root agnostic container for solids, faces, units, source reference, and tessellated mesh representation (vertices, triangles, normals) for 3D viewers.
[NEW] 
core/geometry.py
Core geometric processing independent of CAD origin:

B-Rep query functions, volume calculation, surface area evaluation, centroid calculation using OpenCASCADE/CadQuery primitives.
[NEW] 
core/meshing.py
Meshing interfaces and provisional mesher:

MeshResult: Dataclass containing nodes, elements, element type, statistics.
ProvisionalTet4Mesher: Kuhn-triangulation voxelized tetrahedral mesher (clearly documented as provisional, preparing interfaces for Gmsh).
CustomMesherCallable interface contract.
[NEW] 
core/boundary.py
Mapping CAD faces to FEM mesh nodes:

BoundaryConditionMapper: Euclidean distance projection of CAD B-Rep faces to FEM mesh nodes without knowing the CAD origin.
[NEW] 
core/study.py
Core study domain models:

Material: Physical properties (Young's modulus, Poisson's ratio, density, yield strength).
LoadDefinition: Magnitude, direction vector, application face/point, type.
ConstraintDefinition: Types (fixed, pinned, roller), degrees of freedom constraints.
Study: Complete optimization study entity (CADModel, Material, Loads, Constraints, Mesh, SolverSettings, Objectives).
[NEW] 
core/solver_interface.py
TopOpt and FEA interface contracts and SIMP parameter validation.

2. CAD Adapters Layer (adapters/)
[NEW] 
adapters/
init
.py
[NEW] 
adapters/cad/base.py
Base abstract class BaseCADAdapter:

load_from_bytes(data: bytes, metadata: dict) -> CADModel
load_from_file(file_path: str, metadata: dict) -> CADModel
tessellate(cad_model: CADModel, linear_deflection: float, angular_deflection: float) -> dict
[NEW] 
adapters/cad/step_adapter.py
STEP format adapter implementing BaseCADAdapter using OpenCASCADE / CadQuery:

Parses STEP files or byte buffers into CADModel with complete hierarchy of solids and faces.
Generates Three.js-compatible tessellation data.
3. Connectors Layer (connectors/)
[NEW] 
connectors/
init
.py
[NEW] 
connectors/onshape/client.py
Onshape OAuth 2.0 client, token store interfaces, and exception definitions (migrated and isolated from core).

[NEW] 
connectors/onshape/service.py
Onshape connector service:

Encapsulates queries for Part Studio parts, properties, and STEP export downloading.
Converts downloaded STEP into the Core CADModel via StepAdapter.
4. Application Services & API Layer (services/ & api_server.py)
[NEW] 
services/cad_service.py
Application service coordinating CAD loading, caching, meshing, and boundary condition mapping.

[NEW] 
services/study_service.py
Application service managing standalone and connector-linked studies and persistence in SQLite (cad_models, studies, jobs).

[MODIFY] 
api_server.py
Refactor routes into clean modular structure.
Add standalone endpoints:
POST /api/cad/step/upload: Import STEP file directly without Onshape/OAuth.
GET /api/cad/models/{model_id}: Retrieve model and tessellation data.
POST /api/cad/models/{model_id}/mesh: Generate mesh on imported CAD.
POST /api/cad/models/{model_id}/boundary/map: Map boundary conditions.
Maintain full backward compatibility for legacy routes (/api/geometry/download, /api/mesh/generate, /api/boundary/forces, /api/boundary/constraints, /api/geometry/current, /api/partstudios/parts, /login, /oauth/callback).
Update database schema to store standalone CAD models and studies independently from oauth_sessions.
5. Backward Compatibility Wrappers
[MODIFY] 
geometry_processor.py
Provide backward compatibility shim delegating to core.geometry, adapters.cad.step_adapter, and connectors.onshape.

[MODIFY] 
onshape_client.py
Provide backward compatibility shim importing from connectors.onshape.client.

[MODIFY] 
topopt_solver.py
Provide backward compatibility shim delegating to core.solver_interface.

6. Frontend Standalone & Connector UI
[MODIFY] 
optimization-app.html
Add standalone STEP file upload section (drag & drop / file chooser) in the UI sidebar.
Allow full 3D viewing, face inspection, meshing, and load/constraint configuration without Onshape connection.
Display CAD source metadata badge ("Standalone STEP" or "Onshape: Doc/Elem").
Seamlessly handle both standalone models and models fetched from Onshape.
7. Test Suite (tests/)
[NEW] 
test_core_cad.py
Tests verifying that the entire Core (models, geometry, meshing, boundary, study, solver_interface) operates 100% without Onshape modules or imports.

[NEW] 
test_step_adapter.py
Tests verifying STEP import, CADModel creation, B-Rep metadata extraction, tessellation, and boundary condition node mapping.

[NEW] 
test_standalone_api.py
Integration tests for the standalone FastAPI endpoints (uploading STEP, meshing, boundary mapping without OAuth).

[NEW] 
test_architecture_boundaries.py
Static/dynamic AST test checking that no module in core/ or adapters/ imports onshape_client, connectors.onshape, or references Onshape-specific concepts.

[MODIFY] 
test_pipeline_hito1.py
Ensure all 13 original Hito 1 tests continue passing without regression.

8. Documentation
[MODIFY] 
README.md
Update documentation to explain the CAD-Agnostic Core + Adapters + Connectors architecture, the standalone STEP workflow, and Onshape connector.

[MODIFY] 
metodologia.md
Add mandatory rules for CAD core independence and connector decoupling.

[MODIFY] 
RESUMEN_IMPLEMENTACION.md
Complete record of the architectural migration, test results, and pending tasks for subsequent iterations.

Verification Plan
Automated Tests
Execute the comprehensive test suite with Python 3.11 in the active .venv:

powershell

.venv\Scripts\python.exe -m unittest discover -v
Expected: All existing tests (36 tests) + new Core tests + Standalone API tests + Architecture boundary tests must pass (100% pass rate).

Architecture Boundary Verification
Run the AST boundary test ensuring no Core module imports Onshape:

powershell

.venv\Scripts\python.exe -m unittest test_architecture_boundaries.py -v
Standalone End-to-End Test
Run standalone API tests simulating STEP file upload, CADModel generation, Three.js tessellation retrieval, and volumetric meshing without any OAuth credentials.

Backend Startup Verification
Start the backend server and verify /health and /app:

powershell

.venv\Scripts\python.exe -c "import api_server; print('api_server loaded successfully')"
