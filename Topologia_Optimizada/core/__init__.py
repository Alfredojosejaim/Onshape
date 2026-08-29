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
]
