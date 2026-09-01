"""CAD-Agnostic Core for Topologia Optimizada.

This package contains the core domain models, geometry analysis, meshing,
boundary condition mapping, material definitions, and study management.
It has ZERO dependencies on any specific CAD system (e.g. Onshape).
"""

from core.models import (
    BoundingBox3D,
    CADEdge,
    CADFace,
    CADModel,
    CADSolid,
    CADVertex,
    SourceReference,
    SourceType,
    TessellatedMesh,
    Unit,
)
from core.geometry import GeometryEngine
from core.meshing import BaseMesher, GmshTet4Mesher, MeshResult, ProvisionalTet4Mesher
from core.boundary import BoundaryConditionMapper, MappedFace
from core.selection import (
    AllRegion,
    BoxRegion,
    CompositionRegion,
    CylinderRegion,
    FaceRegion,
    NodeSelectionEngine,
    NormalRegion,
    PlaneRegion,
    RegionType,
    SphereRegion,
    parse_region,
)
from core.materials import Material, STANDARD_MATERIALS
from core.study import (
    ConstraintDefinition,
    ConstraintType,
    LoadDefinition,
    LoadType,
    Objectives,
    SolverSettings,
    Study,
)
from core.solver_interface import TopOptSolver, run_topology_optimization
from core.license import (
    LicenseConfig,
    LicenseManager,
    LicenseServerProtocol,
    LicenseState,
    NoOpLicenseServer,
)
from core.user_preferences import UserPreferences

# Reusable CAD/CAE conditions (Carga, Elasticidad, Obstrucción, Región protegida)
from core.conditions import (
    Condition,
    ConditionManager,
    ConditionType,
    ElasticityCondition,
    LoadCondition,
    LoadOrientation,
    LoadSense,
    ObstructionCondition,
    ProtectedRegion,
    condition_from_dict,
)

# Pruebas - extensible base category
from core.testing import (
    TestCase,
    TestKind,
    TestRegistry,
    TestResult,
    TestStatus,
    TestSuite,
    DEFAULT_TEST_REGISTRY,
)

# Generative design engine + CAD reconstruction (B-Rep / STEP)
from core.cad_reconstruction import (
    BRepFitter,
    DummyBRepFitter,
    MarchingTetrahedraExtractor,
    OCPBRepFitter,
    ReconstructionPipeline,
    ReconstructionResult,
    ReconstructionStage,
    ReconstructionStatus,
    SurfaceExtractor,
)
from core.generative_engine import (
    GenerativeDesignEngine,
    BridgeMesh,
    consume_conditions,
    direction_vector,
    generate_bridge_mesh,
    run_generative_design,
)

__all__ = [
    "BoundingBox3D",
    "CADEdge",
    "CADFace",
    "CADModel",
    "CADSolid",
    "CADVertex",
    "SourceReference",
    "SourceType",
    "TessellatedMesh",
    "Unit",
    "GeometryEngine",
    "BaseMesher",
    "MeshResult",
    "GmshTet4Mesher",
    "ProvisionalTet4Mesher",
    "BoundaryConditionMapper",
    "MappedFace",
    "RegionType",
    "AllRegion",
    "PlaneRegion",
    "BoxRegion",
    "SphereRegion",
    "CylinderRegion",
    "FaceRegion",
    "NormalRegion",
    "CompositionRegion",
    "NodeSelectionEngine",
    "parse_region",
    "Material",
    "STANDARD_MATERIALS",
    "ConstraintDefinition",
    "ConstraintType",
    "LoadDefinition",
    "LoadType",
    "Objectives",
    "SolverSettings",
    "Study",
    "TopOptSolver",
    "run_topology_optimization",
    "LicenseState",
    "LicenseServerProtocol",
    "LicenseConfig",
    "LicenseManager",
    "NoOpLicenseServer",
    "UserPreferences",
    "Condition",
    "ConditionManager",
    "ConditionType",
    "LoadOrientation",
    "LoadSense",
    "LoadCondition",
    "ElasticityCondition",
    "ObstructionCondition",
    "ProtectedRegion",
    "condition_from_dict",
    "TestStatus",
    "TestKind",
    "TestResult",
    "TestCase",
    "TestSuite",
    "TestRegistry",
    "DEFAULT_TEST_REGISTRY",
    "SurfaceExtractor",
    "MarchingTetrahedraExtractor",
    "OCPBRepFitter",
    "BRepFitter",
    "ReconstructionPipeline",
    "ReconstructionResult",
    "ReconstructionStage",
    "ReconstructionStatus",
    "DummyBRepFitter",
    "GenerativeDesignEngine",
    "BridgeMesh",
    "consume_conditions",
    "direction_vector",
    "generate_bridge_mesh",
    "run_generative_design",
]
