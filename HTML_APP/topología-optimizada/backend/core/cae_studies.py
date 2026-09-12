"""CAE Study abstractions.

A Study represents an engineering analysis attached to a CAD model.
Studies are separate from Features: Features transform geometry, Studies
analyse it.

This module provides the base Study class and common study types:
- StructuralAnalysis (linear static FEA)
- ThermalAnalysis (scaffold: data model + validation; solver not integrated)
- ModalAnalysis    (scaffold: data model + validation; solver not integrated)

Thermal/Modal are shaped for future integration: their configuration, boundary
conditions and validation are defined so wiring a real solver later is a small,
localized change. Their ``execute()`` raises :class:`StudyNotImplementedError`,
which the pipeline reports clearly instead of a generic failure.

The existing ``core.study.Study`` is an optimization-specific study.
This module generalises the concept so different kinds of analyses can
coexist under a unified architecture.

    Study (base)
    ├── StructuralAnalysis
    ├── ThermalAnalysis
    ├── ModalAnalysis
    └── ... future study types
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.cad_entity import CadEntityRef, SelectionSet
from core.materials import Material, STANDARD_MATERIALS


class StudyType(str, Enum):
    STRUCTURAL = "structural"
    THERMAL = "thermal"
    MODAL = "modal"
    TOPOLOGY_OPTIMIZATION = "topology_optimization"
    GENERATIVE_DESIGN = "generative_design"
    CUSTOM = "custom"


class StudyStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LoadCase:
    """A single load application: entity + magnitude + direction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    magnitude: float = 1000.0
    direction: tuple = (0.0, 0.0, -1.0)
    load_type: str = "point"  # point | distributed | pressure
    unit: str = "N"
    selection: Optional[SelectionSet] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "magnitude": self.magnitude,
            "direction": list(self.direction),
            "load_type": self.load_type,
            "unit": self.unit,
            "selection": self.selection.to_dict() if self.selection else None,
        }


@dataclass
class ConstraintCase:
    """A single constraint application: entity + constrained DOFs."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    constraint_type: str = "fixed"  # fixed | pinned | roller | symmetry
    dof: Dict[str, bool] = field(default_factory=lambda: {
        "ux": True, "uy": True, "uz": True, "rx": True, "ry": True, "rz": True
    })
    selection: Optional[SelectionSet] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "constraint_type": self.constraint_type,
            "dof": dict(self.dof),
            "selection": self.selection.to_dict() if self.selection else None,
        }


# ====================================================================== #
# Thermal boundary conditions (scaffolding for future thermal solver)
# ====================================================================== #

class ThermalBoundaryType(str, Enum):
    TEMPERATURE = "temperature"      # fixed temperature (Dirichlet)
    HEAT_FLUX = "heat_flux"          # imposed heat flux q'' (Neumann)
    CONVECTION = "convection"        # convective cooling h * (T - T_inf) (Robin)


@dataclass
class ThermalBoundary:
    """A single thermal boundary condition.

    For future steady-state heat-transfer solving:
    - TEMPERATURE : fixed temperature [K] on ``selection`` (Dirichlet).
    - HEAT_FLUX   : imposed normal heat flux [W/m^2] (Neumann), positive = inflow.
    - CONVECTION  : convection coefficient ``h`` [W/(m^2.K)] with ambient ``T_inf`` [K].
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    boundary_type: ThermalBoundaryType = ThermalBoundaryType.TEMPERATURE
    magnitude: float = 0.0        # K for temperature, W/m^2 for heat flux
    h: float = 0.0                # W/(m^2.K) — convection coefficient (CONVECTION)
    T_inf: float = 0.0            # K — ambient temperature (CONVECTION)
    selection: Optional[SelectionSet] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.boundary_type is None:
            self.boundary_type = ThermalBoundaryType.TEMPERATURE
        if self.boundary_type == ThermalBoundaryType.CONVECTION:
            if self.h is None or self.h < 0:
                raise ValueError("Convection coefficient h must be >= 0")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "boundary_type": self.boundary_type.value,
            "magnitude": self.magnitude,
            "h": self.h,
            "T_inf": self.T_inf,
            "selection": self.selection.to_dict() if self.selection else None,
        }


# ====================================================================== #
# Modal configuration (scaffolding for future eigen-solver)
# ====================================================================== #

@dataclass
class ModalParameters:
    """Settings for a natural-frequency / mode-shape study.

    For future eigen-analysis the solver must return ``mode_count`` natural
    frequencies (descending) with their mode shapes; ``frequency_min`` and
    ``frequency_max`` optionally narrow the search window.
    """
    mode_count: int = 5
    frequency_min: Optional[float] = None  # Hz — lowest frequency of interest
    frequency_max: Optional[float] = None  # Hz — highest frequency of interest

    def __post_init__(self):
        if self.mode_count is None or self.mode_count < 1:
            raise ValueError("mode_count must be >= 1")
        if self.frequency_min is not None and self.frequency_min < 0:
            raise ValueError("frequency_min must be >= 0")
        if self.frequency_max is not None and self.frequency_max < 0:
            raise ValueError("frequency_max must be >= 0")
        if (self.frequency_min is not None and self.frequency_max is not None
                and self.frequency_min >= self.frequency_max):
            raise ValueError("frequency_min must be < frequency_max")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode_count": self.mode_count,
            "frequency_min": self.frequency_min,
            "frequency_max": self.frequency_max,
        }


class StudyNotImplementedError(NotImplementedError):
    """Raised by a study type whose solver is not integrated yet.

    The pipeline catches this and reports a clear ``not_implemented`` result
    instead of a confusing generic failure. Once a real solver is wired up,
    ``execute()`` stops raising it.
    """


@dataclass
class StudyResult:
    """Generic result container for any study."""
    success: bool = False
    status: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "data": self.data,
            "error_message": self.error_message,
        }


class Study(ABC):
    """Abstract base class for all engineering studies.

    Subclasses must implement:
    - ``study_type``          class-level StudyType
    - ``display_name``       human-readable name
    - ``validate()``         check preconditions
    - ``execute()``          run the analysis, return StudyResult
    """

    study_type: StudyType = StudyType.CUSTOM
    display_name: str = "Custom Study"
    description: str = ""

    def __init__(self, name: str = "") -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name or self.display_name
        self.status: StudyStatus = StudyStatus.DRAFT
        self.model_id: Optional[str] = None
        self.material: Material = STANDARD_MATERIALS["steel"]
        self.loads: List[LoadCase] = []
        self.constraints: List[ConstraintCase] = []
        self.thermal_boundaries: List[ThermalBoundary] = []
        self.modal: Optional[ModalParameters] = None
        self.result: Optional[StudyResult] = None
        self.metadata: Dict[str, Any] = {}

    def add_load(self, load: LoadCase) -> None:
        self.loads.append(load)

    def add_constraint(self, constraint: ConstraintCase) -> None:
        self.constraints.append(constraint)

    def add_thermal_boundary(self, boundary: ThermalBoundary) -> None:
        self.thermal_boundaries.append(boundary)

    @abstractmethod
    def validate(self) -> bool:
        """Check that the study is ready to run."""

    @abstractmethod
    def execute(self) -> StudyResult:
        """Execute the study.  Returns a StudyResult."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "study_type": self.study_type.value,
            "status": self.status.value,
            "model_id": self.model_id,
            "material": self.material.to_dict() if self.material else None,
            "loads": [l.to_dict() for l in self.loads],
            "constraints": [c.to_dict() for c in self.constraints],
            "thermal_boundaries": [b.to_dict() for b in self.thermal_boundaries],
            "modal": self.modal.to_dict() if self.modal else None,
            "result": self.result.to_dict() if self.result else None,
            "metadata": self.metadata,
        }


# ====================================================================== #
# Structural Analysis
# ====================================================================== #

class StructuralAnalysis(Study):
    """Linear static structural analysis using the existing FEA solver.

    This study wraps ``core.fea.solve_fea`` and bridges the existing
    Study data model with the new architectural framework.
    """

    study_type = StudyType.STRUCTURAL
    display_name = "Structural Analysis"
    description = "Linear static FEA (3D Tet4)"

    def __init__(self, name: str = "Structural Analysis") -> None:
        super().__init__(name=name)

    def validate(self) -> bool:
        if self.model_id is None:
            return False
        if not self.loads and not self.constraints:
            return False
        return True

    def execute(self) -> StudyResult:
        """Execute structural analysis.

        The actual FEA solve is delegated to the pipeline/controller layer
        because it requires access to the mesh and solver infrastructure.
        This method marks the study as ready for execution.
        """
        if not self.validate():
            self.status = StudyStatus.FAILED
            return StudyResult(
                success=False,
                status="validation_failed",
                error_message="Model not set or no loads/constraints defined.",
            )
        self.status = StudyStatus.READY
        return StudyResult(
            success=True,
            status="ready_for_pipeline",
            data={"study_id": self.id, "type": self.study_type.value},
        )


# ====================================================================== #
# Thermal Analysis (scaffold for future steady-state heat-transfer solver)
# ====================================================================== #

class ThermalAnalysis(Study):
    """Steady-state thermal analysis (real Tet4 solver in ``core.thermal``).

    ``execute()`` without a mesh keeps raising :class:`StudyNotImplementedError`
    (the pipeline reports ``not_implemented``); use ``execute_on_mesh(nodes,
    elements)`` — or ``core.thermal.solve_thermal_study`` — to run the real
    steady-state solve. Result data carries ``temperatures`` (nodal field [K])
    and ``heat_flux`` (per-element vectors [W/m^2]).
    """

    study_type = StudyType.THERMAL
    display_name = "Thermal Analysis"
    description = "Steady-state thermal analysis"

    def __init__(self, name: str = "Thermal Analysis") -> None:
        super().__init__(name=name)

    def validate(self) -> bool:
        return self.validate_with_message() is None

    def validate_with_message(self) -> Optional[str]:
        """Return a description of the first problem, or None if valid.

        This matches the pattern used elsewhere (fail with a clear message
        instead of a bare False)."""
        if self.model_id is None:
            return "El estudio térmico no tiene un modelo asociado (model_id)."
        if self.material is None or not self.material.has_thermal_properties:
            return (
                "El material del estudio no tiene conductividad térmica definida. "
                "Asigne un material con propiedades térmicas (thermal_conductivity > 0)."
            )
        if not self.thermal_boundaries:
            return "El estudio térmico requiere al menos una condición de contorno térmica."
        return None

    def execute(self) -> StudyResult:
        if not self.validate():
            msg = self.validate_with_message() or "Configuración térmica inválida."
            self.status = StudyStatus.FAILED
            return StudyResult(success=False, status="validation_failed", error_message=msg)
        # Mesh-less path: no mesh to solve on — clear, structured boundary.
        raise StudyNotImplementedError("Steady-state thermal solver not yet integrated.")

    def execute_on_mesh(self, nodes, elements) -> StudyResult:
        """Run the real steady-state thermal solve on an explicit mesh.

        Each ThermalBoundary must carry its mesh mapping in ``metadata``
        (``'nodes'`` for TEMPERATURE, ``'faces'`` for HEAT_FLUX/CONVECTION);
        see :func:`core.thermal.solve_thermal_study`. Validation failures
        return a ``validation_failed`` result; solver failures an explicit
        ``failed`` result — never a silent default.
        """
        from core.thermal import ThermalError, solve_thermal_study

        if not self.validate():
            msg = self.validate_with_message() or "Configuración térmica inválida."
            self.status = StudyStatus.FAILED
            return StudyResult(success=False, status="validation_failed", error_message=msg)
        try:
            data = solve_thermal_study(self, nodes, elements)
        except ThermalError as exc:
            self.status = StudyStatus.FAILED
            return StudyResult(success=False, status="failed", error_message=str(exc))
        self.status = StudyStatus.COMPLETED
        serializable = {
            k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in data.items()
        }
        result = StudyResult(success=True, status="completed", data=serializable)
        self.result = result
        return result


# ====================================================================== #
# Modal Analysis (scaffold for future eigen-solver)
# ====================================================================== #

class ModalAnalysis(Study):
    """Natural-frequency / mode-shape analysis.

    Scaffolding contract for the future eigen-solver integration.
    The data model (``modal``/``ModalParameters``) and validation are already
    in place; the actual eigen-solve is delegated to the pipeline, which
    currently reports ``not_implemented`` via :class:`StudyNotImplementedError`.

    Future integration must:
    - build the stiffness ``K`` and (consistent/lumped) mass ``M`` matrices
      from ``material`` (E, nu, density),
    - solve the generalized eigenproblem ``K*phi = w^2*M*phi``,
    - return result.data["frequencies"] (Hz, descending by norm) and
      result.data["mode_shapes"].
    """

    study_type = StudyType.MODAL
    display_name = "Modal Analysis"
    description = "Natural frequency / mode shape analysis"

    def __init__(self, name: str = "Modal Analysis", mode_count: int = 5) -> None:
        super().__init__(name=name)
        self.modal = ModalParameters(mode_count=mode_count)

    def validate(self) -> bool:
        return self.validate_with_message() is None

    def validate_with_message(self) -> Optional[str]:
        if self.model_id is None:
            return "El estudio modal no tiene un modelo asociado (model_id)."
        if self.modal is None:
            return "Faltan los parámetros modales (modal)."
        try:
            self.modal.__post_init__()
        except ValueError as exc:
            return f"Parámetros modales inválidos: {exc}."
        if not self.constraints:
            return (
                "El estudio modal requiere al menos una condición de soporte "
                "(constraint) para eliminar los modos de cuerpo rígido."
            )
        return None

    def execute_on_mesh(self, nodes, elements, fixed_dofs) -> StudyResult:
        """Run the real eigen-solver on a concrete mesh.

        Args:
            nodes: (N,3) node coordinates.
            elements: (M,4) Tet4 connectivity.
            fixed_dofs: global DOF indices held at zero (anti-rigid-body
                constraints resolved by the pipeline). Must be non-empty.

        Returns:
            StudyResult with ``data`` = :func:`core.fea.solve_modal` output
            (``frequencies`` Hz ascending, ``mode_shapes``, ``warnings``).

        Raises:
            core.fea.FEAError: on invalid ``mode_count`` or empty
                ``fixed_dofs`` — explicit, never a silent fallback.
        """
        from core.fea import solve_modal
        msg = self.validate_with_message()
        if msg is not None:
            self.status = StudyStatus.FAILED
            return StudyResult(success=False, status="validation_failed",
                               error_message=msg)
        if fixed_dofs is None or len(list(fixed_dofs)) == 0:
            self.status = StudyStatus.FAILED
            return StudyResult(
                success=False, status="validation_failed",
                error_message=(
                    "El estudio modal requiere DOFs fijos resueltos de la malla "
                    "(fixed_dofs vacío): sin constraints K es singular."
                ),
            )
        data = solve_modal(
            nodes, elements,
            self.material.young_modulus, self.material.poisson_ratio,
            self.material.density, fixed_dofs,
            mode_count=self.modal.mode_count,
            frequency_min=self.modal.frequency_min,
            frequency_max=self.modal.frequency_max,
        )
        self.status = StudyStatus.COMPLETED
        sr = StudyResult(success=True, status="completed", data=data)
        self.result = sr
        return sr

    def execute(self) -> StudyResult:
        if not self.validate():
            msg = self.validate_with_message() or "Configuración modal inválida."
            self.status = StudyStatus.FAILED
            return StudyResult(success=False, status="validation_failed", error_message=msg)
        # The real eigen-solve needs a mesh + resolved fixed DOFs, which live
        # in the pipeline layer: use ModalAnalysis.execute_on_mesh(...) or the
        # controller's execute_study (which calls solve when a mesh exists).
        # Without a mesh there is nothing to assemble K/M from.
        raise StudyNotImplementedError("Modal (eigen) solver not yet integrated.")


# ====================================================================== #
# Fase 3 (plan.md): postproceso puro — no toca ningún solver.
# ====================================================================== #

def factor_of_safety(von_mises, yield_strength: float):
    """FoS por entidad: ``yield_strength / von_mises`` (adimensional).

    Args:
        von_mises: array-like de tensiones equivalentes [Pa] (por elemento
            o nodales — la función no distingue, opera por entidad).
        yield_strength: límite elástico del material [Pa] (> 0).

    Returns:
        ``np.ndarray`` de FoS; donde ``von_mises <= 0`` el FoS es ``+inf``
        (sin tensión → sin riesgo), nunca NaN ni silencioso.
    """
    import numpy as np

    sy = float(yield_strength)
    if not np.isfinite(sy) or sy <= 0:
        raise ValueError(f"yield_strength debe ser finito y > 0, got {yield_strength!r}.")
    vm = np.asarray(list(von_mises), dtype=float)
    out = np.full(vm.shape, np.inf, dtype=float)
    positive = np.isfinite(vm) & (vm > 0)
    out[positive] = sy / vm[positive]
    return out


def safety_summary(von_mises, yield_strength: float,
                   threshold: float = 1.0) -> dict:
    """Resumen de FoS: mínimo + conteo bajo umbral (mapa de zonas críticas).

    Nunca inventa datos: si no hay entidades finitas, ``min_fos`` es None.
    """
    import numpy as np

    fos = factor_of_safety(von_mises, yield_strength)
    finite = fos[np.isfinite(fos)]
    below = int(np.count_nonzero(fos < float(threshold)))
    return {
        "min_fos": float(finite.min()) if finite.size else None,
        "mean_fos": float(finite.mean()) if finite.size else None,
        "count": int(fos.size),
        "below_threshold": below,
        "threshold": float(threshold),
    }


def study_snapshot(study, result=None) -> dict:
    """Snapshot comparable de un estudio: {masa, volumen, compliance,
    desplazamiento máx, FoS mín} — solo las claves con dato real.

    ``result`` puede ser un ``StudyResult`` o un dict plano de resultado;
    las claves ausentes se omiten (nunca se inventan ceros).
    """
    data = {}
    if result is not None:
        raw = getattr(result, "data", result)
        if isinstance(raw, dict):
            data = raw
    snap = {
        "study_id": getattr(study, "id", None),
        "name": getattr(study, "name", None),
        "study_type": getattr(getattr(study, "study_type", None), "value",
                              getattr(study, "study_type", None)),
        "status": getattr(getattr(study, "status", None), "value",
                          getattr(study, "status", None)),
    }
    for key in ("mass_kg", "volume", "volume_cm3", "final_volume_fraction",
                "compliance", "final_compliance", "total_strain_energy",
                "max_displacement", "max_von_mises", "min_fos",
                "num_nodes", "num_elements", "iterations"):
        if key in data:
            try:
                import numpy as np
                v = data[key]
                if isinstance(v, np.ndarray):
                    v = v.tolist()
                if isinstance(v, (int, float)):
                    snap[key] = float(v)
                else:
                    snap[key] = v
            except Exception:
                continue
    return snap
