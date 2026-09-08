"""Esquema de datos del problema de optimización topológica (SIMP) + adaptador.

Fase 1 de integración del esquema externo ``topopt_schema``:

* Las dataclasses son la **especificación** del problema completo (cargas,
  BCs, material, regiones, obstáculos, restricción de volumen, filtros,
  objetivo). Todo objeto geométrico referencia por ``selection_id`` a los
  physical groups / submodelparts que el pipeline de picking ya resuelve;
  este módulo no duplica lógica de selección.
* :meth:`TopologyOptimizationProblem.validate` es el punto de entrada de
  chequeos duros antes del solver (principio del proyecto: sin fallbacks
  silenciosos).
* :func:`problem_to_solver_inputs` traduce el problema a lo que el
  :class:`~core.topopt.SIMPSolver` existente soporta hoy y levanta
  :class:`~core.topopt.TopOptError` explícito para lo que no (Fase 2+).

Correspondencias ya decididas en el proyecto (P3/P4):

* ``VolfracMode.ACTIVE_DOMAIN`` == semántica actual del solver
  (``V_active = V_total - V_preserved - V_void``, traceback.md PROBLEMA 3).
  ``TOTAL_VOLUME`` se declara en el esquema pero el solver no lo soporta.
* ``halo_radius_source="mesh_element_size"`` == P4 ya resuelto: el halo se
  deriva del tamaño real de elemento de malla, nunca de ``filter_radius``.
  ``halo_radius=None`` significa "auto desde la malla" (camino preferido),
  no un dato faltante.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.topopt import TopOptError


@dataclass
class GeometrySelection:
    """Referencia a una selección ya resuelta por el pipeline existente.

    No duplica lógica de selección, solo la referencia por id estable
    (nombre de physical group / submodelpart, o ``face_<i>``).
    """
    selection_id: str
    entity_type: str                      # "face" | "edge" | "vertex" | "solid" | "region"
    label: Optional[str] = None


class LoadType(Enum):
    POINT_FORCE = "point_force"
    SURFACE_PRESSURE = "surface_pressure"
    SURFACE_FORCE = "surface_force"
    LINE_FORCE = "line_force"
    SELF_WEIGHT = "self_weight"


@dataclass
class Load:
    id: str
    type: LoadType
    target: GeometrySelection
    vector: Optional[tuple[float, float, float]] = None   # (Fx, Fy, Fz) en N
    magnitude: Optional[float] = None                     # escalar, ej. Pa
    load_case_id: str = "default"


@dataclass
class LoadCase:
    """Cargas evaluadas simultáneamente (compliance promedio ponderado)."""
    id: str
    loads: List[Load] = field(default_factory=list)
    weight: float = 1.0


class BCType(Enum):
    FIXED = "fixed"
    PINNED = "pinned"
    SLIDING = "sliding"
    SYMMETRY = "symmetry"


@dataclass
class BoundaryCondition:
    id: str
    type: BCType
    target: GeometrySelection
    constrained_axes: tuple[bool, bool, bool] = (True, True, True)  # (X, Y, Z)


@dataclass
class Material:
    id: str
    name: str
    young_modulus: float          # E, en Pa
    poisson_ratio: float          # nu
    density: float                # kg/m^3
    simp_penalty: float = 3.0
    density_min: float = 1e-3     # "ersatz material", evita matriz singular


class RegionRole(Enum):
    DESIGN_SPACE = "design_space"
    KEEP_IN = "keep_in"                  # siempre sólido, densidad = 1 fija
    KEEP_OUT = "keep_out"                # siempre vacío, densidad = 0 fija
    FROZEN_FACE = "frozen_face"          # cara intacta en reconstrucción;
                                         # el volumen interior SI se optimiza


@dataclass
class DesignRegion:
    """Dominio donde el SIMP varía densidad libremente."""
    id: str
    target: GeometrySelection
    role: RegionRole = RegionRole.DESIGN_SPACE


@dataclass
class ObstacleRegion:
    """Volumen o cara no modificable por el optimizador.

    KEEP_OUT / KEEP_IN: densidad fija (0 o 1), excluidos de la variable de
    diseño (``set_void_elements`` / ``set_preserved_elements`` existentes).
    FROZEN_FACE: no toca densidades; pass-through CAD en reconstrucción
    (Fase 2, aún no implementado).
    """
    id: str
    role: RegionRole
    target: GeometrySelection
    label: Optional[str] = None
    # None + "mesh_element_size" = auto desde la malla (P4, preferido).
    halo_radius: Optional[float] = None
    halo_radius_source: str = "mesh_element_size"   # "mesh_element_size" | "manual"


class VolfracMode(Enum):
    """Qué volumen es la base del 100% (decisión P3).

    El solver existente solo implementa ACTIVE_DOMAIN.
    """
    TOTAL_VOLUME = "total_volume"
    ACTIVE_DOMAIN = "active_domain"


@dataclass
class VolumeConstraint:
    target_fraction: float
    mode: VolfracMode = VolfracMode.ACTIVE_DOMAIN
    validate_feasibility: bool = True


@dataclass
class StressConstraint:
    """Opcional avanzado (Fase 3+: el SIMPSolver OC no lo soporta)."""
    max_von_mises: float
    target: Optional[GeometrySelection] = None


@dataclass
class DisplacementConstraint:
    """Opcional avanzado (Fase 3+: el SIMPSolver OC no lo soporta)."""
    target: GeometrySelection
    max_displacement: float
    direction: Optional[tuple[float, float, float]] = None


@dataclass
class FilterSettings:
    filter_radius: float
    filter_type: str = "density"           # "density" | "sensitivity"
    use_heaviside_projection: bool = False
    heaviside_beta: float = 1.0


class ObjectiveType(Enum):
    MINIMIZE_COMPLIANCE = "minimize_compliance"
    MINIMIZE_VOLUME_SUBJECT_TO_COMPLIANCE = "minimize_volume_subject_to_compliance"


@dataclass
class Objective:
    type: ObjectiveType = ObjectiveType.MINIMIZE_COMPLIANCE
    max_compliance: Optional[float] = None
    load_case_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class TopologyOptimizationProblem:
    """Unidad serializable que se pasa al backend (SIMP local / Kratos)."""
    id: str
    material: Material

    design_regions: List[DesignRegion] = field(default_factory=list)
    obstacles: List[ObstacleRegion] = field(default_factory=list)

    load_cases: List[LoadCase] = field(default_factory=list)
    boundary_conditions: List[BoundaryCondition] = field(default_factory=list)

    volume_constraint: Optional[VolumeConstraint] = None
    stress_constraints: List[StressConstraint] = field(default_factory=list)
    displacement_constraints: List[DisplacementConstraint] = field(default_factory=list)

    filter_settings: FilterSettings = field(
        default_factory=lambda: FilterSettings(filter_radius=1.5)
    )
    objective: Objective = field(default_factory=Objective)

    symmetry_planes: List[GeometrySelection] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Chequeos duros antes del solver. Sin fallbacks silenciosos."""
        errors: List[str] = []

        if not self.design_regions:
            errors.append("No hay design_regions definidas.")

        if not self.load_cases or not any(lc.loads for lc in self.load_cases):
            errors.append("No hay cargas definidas en ningún load_case.")

        if not self.boundary_conditions:
            errors.append("No hay boundary_conditions definidas (modelo sin restringir).")

        if self.volume_constraint is None:
            errors.append("No hay volume_constraint definida.")

        if self.volume_constraint and self.volume_constraint.validate_feasibility:
            keep_in_ids = [o.id for o in self.obstacles if o.role == RegionRole.KEEP_IN]
            if keep_in_ids and self.volume_constraint.target_fraction < 0.05:
                errors.append(
                    f"target_fraction={self.volume_constraint.target_fraction} es muy bajo "
                    f"con keep_in regions activas ({keep_in_ids}); "
                    f"posible infactibilidad. Verificar volumen combinado de keep_in "
                    f"contra target_fraction en modo {self.volume_constraint.mode.value}."
                )

        # Halo: None + mesh_element_size = auto desde la malla (P4, válido).
        # Solo es error "manual" sin valor o fuente desconocida.
        for obs in self.obstacles:
            if obs.role in (RegionRole.KEEP_OUT, RegionRole.KEEP_IN):
                if obs.halo_radius_source not in ("mesh_element_size", "manual"):
                    errors.append(
                        f"ObstacleRegion '{obs.id}': halo_radius_source desconocido "
                        f"({obs.halo_radius_source!r}); usar 'mesh_element_size' o 'manual'."
                    )
                elif obs.halo_radius_source == "manual" and obs.halo_radius is None:
                    errors.append(
                        f"ObstacleRegion '{obs.id}' ({obs.role.value}) pide halo manual "
                        f"pero no tiene halo_radius."
                    )

        return errors


# ---------------------------------------------------------------------------
# Adaptador Fase 1: problema -> entradas del SIMPSolver existente
# ---------------------------------------------------------------------------

#: Firma del resolvedor selección -> índices de malla. Recibe un
#: GeometrySelection y el dict de malla y devuelve
#: ``{"node_indices": [...], "element_indices": [...]}``. Debe levantar
#: TopOptError si la selección no es resoluble (nunca lista vacía
#: silenciosa para sólidos/regiones).
SelectionResolver = Callable[[GeometrySelection, Dict[str, Any]], Dict[str, List[int]]]


def _face_id(selection_id: str) -> Optional[int]:
    from core.boundary import parse_face_id
    return parse_face_id(selection_id)


def default_face_resolver(sel: GeometrySelection,
                          mesh: Dict[str, Any]) -> Dict[str, List[int]]:
    """Resolvedor por defecto: caras via physical groups / superficies.

    Acepta ``selection_id`` como ``face_<i>``, ``face:<i>``, ``<i>`` o
    nombre de physical group. Devuelve nodos de la cara y elementos que
    tocan esos nodos. Sólidos/regiones exigen resolvedor propio.
    """
    if sel.entity_type not in ("face", "edge", "vertex"):
        raise TopOptError(
            f"entity_type={sel.entity_type!r} requiere resolvedor propio "
            f"(pasar selection_resolver a problem_to_solver_inputs)."
        )
    nodes = mesh.get("nodes", [])
    elements = mesh.get("elements", [])
    pgroups = mesh.get("physical_groups", {}) or {}
    surfs = mesh.get("face_surface_elements", {}) or {}

    # Provenance check (P1): keys may come from deterministic geometric
    # correspondence or from Gmsh enumeration order (see MeshResult.metadata
    # "face_correspondence"). Order-based labels are only valid for the mesh
    # they were generated with — warn loudly when consuming them.
    metadata = mesh.get("metadata", {}) or {}
    if metadata.get("face_correspondence") != "deterministic":
        import logging
        logging.getLogger(__name__).warning(
            "default_face_resolver: mesh face keys are ORDER-BASED "
            "(face_correspondence=%r), not geometric. Selection identity is "
            "only valid for the generating mesh; re-meshing may remap faces.",
            metadata.get("face_correspondence"),
        )

    node_set: set = set()
    fi = _face_id(sel.selection_id)
    if fi is not None:
        for key in (f"face_{fi}", f"face:{fi}", str(fi)):
            if key in surfs:
                for tri in surfs[key]:
                    node_set.update(int(n) for n in tri)
            if key in pgroups:
                node_set.update(int(n) for n in pgroups[key])
    if sel.selection_id in pgroups:
        node_set.update(int(n) for n in pgroups[sel.selection_id])
    if not node_set:
        raise TopOptError(
            f"selection_id={sel.selection_id!r} sin nodos en la malla "
            f"(revisar physical groups / face_surface_elements)."
        )
    elems = [e for e, el in enumerate(elements)
             if any(int(n) in node_set for n in el)]
    return {"node_indices": sorted(node_set), "element_indices": elems}


def problem_to_solver_inputs(
    problem: TopologyOptimizationProblem,
    mesh: Dict[str, Any],
    selection_resolver: Optional[SelectionResolver] = None,
) -> Dict[str, Any]:
    """Traduce el problema a entradas del SIMPSolver existente.

    Devuelve material, volfrac, filtro, ``preserved_elements`` (KEEP_IN),
    ``void_elements`` (KEEP_OUT) y spec de halo. Las cargas/BCs se
    resuelven pero su *aplicación* sigue en el pipeline existente
    (ConditionManager); aquí solo se validan y se exponen sus nodos.

    Levanta TopOptError ante lo no soportado en Fase 1 (sin silencios).
    """
    resolve = selection_resolver or default_face_resolver

    errors = problem.validate()
    if errors:
        raise TopOptError("Problema inválido: " + " | ".join(errors))

    vc = problem.volume_constraint
    if vc.mode != VolfracMode.ACTIVE_DOMAIN:
        raise TopOptError(
            f"VolfracMode.{vc.mode.name} no implementado por el SIMPSolver "
            f"(solo ACTIVE_DOMAIN, decisión P3)."
        )
    if problem.stress_constraints or problem.displacement_constraints:
        raise TopOptError(
            "stress/displacement constraints no soportadas por el "
            "SIMPSolver OC (Fase 3)."
        )
    if problem.objective.type != ObjectiveType.MINIMIZE_COMPLIANCE:
        raise TopOptError(
            f"Objective.{problem.objective.type.name} no soportado "
            f"(solo MINIMIZE_COMPLIANCE)."
        )
    if problem.filter_settings.use_heaviside_projection:
        raise TopOptError("Heaviside projection no soportada (Fase 3).")
    if problem.filter_settings.filter_type != "density":
        raise TopOptError(
            f"filter_type={problem.filter_settings.filter_type!r} no "
            f"soportado (solo 'density')."
        )

    non_empty = [lc for lc in problem.load_cases if lc.loads]
    if len(non_empty) > 1 or any(abs(lc.weight - 1.0) > 1e-12 for lc in non_empty):
        raise TopOptError(
            "Multi-load ponderado no soportado por el SIMPSolver "
            "single-load (Fase 3)."
        )
    for lc in non_empty:
        for ld in lc.loads:
            if ld.type not in (LoadType.SURFACE_FORCE, LoadType.SURFACE_PRESSURE,
                               LoadType.POINT_FORCE):
                raise TopOptError(
                    f"LoadType.{ld.type.name} no soportado "
                    f"(solo SURFACE_FORCE/SURFACE_PRESSURE/POINT_FORCE)."
                )
    for bc in problem.boundary_conditions:
        if bc.type != BCType.FIXED:
            raise TopOptError(
                f"BCType.{bc.type.name} no soportado "
                f"(solo FIXED: el pipeline actual solo fija DOFs)."
            )

    for obs in problem.obstacles:
        if obs.role == RegionRole.FROZEN_FACE:
            raise TopOptError(
                f"ObstacleRegion '{obs.id}' FROZEN_FACE: pass-through en "
                f"reconstrucción aún no implementado (Fase 2)."
            )

    preserved: set = set()
    void: set = set()
    halos: List[Dict[str, Any]] = []
    for obs in problem.obstacles:
        res = resolve(obs.target, mesh)
        if obs.role == RegionRole.KEEP_IN:
            preserved.update(res["element_indices"])
        else:  # KEEP_OUT
            void.update(res["element_indices"])
        halos.append({
            "id": obs.id,
            "role": obs.role.value,
            "radius": obs.halo_radius,  # None = auto desde la malla (P4)
            "radius_source": obs.halo_radius_source,
            "node_indices": res["node_indices"],
        })
    if preserved & void:
        raise TopOptError(
            f"Elementos en KEEP_IN y KEEP_OUT a la vez: "
            f"{sorted(preserved & void)[:10]}... (conjunto infactible)."
        )

    loads_out: List[Dict[str, Any]] = []
    for lc in non_empty:
        for ld in lc.loads:
            res = resolve(ld.target, mesh)
            loads_out.append({
                "id": ld.id,
                "type": ld.type.value,
                "node_indices": res["node_indices"],
                "vector": ld.vector,
                "magnitude": ld.magnitude,
            })
    bcs_out: List[Dict[str, Any]] = []
    for bc in problem.boundary_conditions:
        res = resolve(bc.target, mesh)
        bcs_out.append({
            "id": bc.id,
            "type": bc.type.value,
            "node_indices": res["node_indices"],
            "constrained_axes": bc.constrained_axes,
        })

    mat = problem.material
    return {
        "problem_id": problem.id,
        "material": {
            "young_modulus": float(mat.young_modulus),
            "poisson_ratio": float(mat.poisson_ratio),
            "penalization": float(mat.simp_penalty),
            "rho_min": float(mat.density_min),
        },
        "volfrac": float(vc.target_fraction),
        "volfrac_mode": vc.mode.value,  # siempre "active_domain" en Fase 1
        "filter_radius": float(problem.filter_settings.filter_radius),
        "preserved_elements": sorted(preserved),
        "void_elements": sorted(void),
        "halos": halos,
        "loads": loads_out,
        "boundary_conditions": bcs_out,
    }
