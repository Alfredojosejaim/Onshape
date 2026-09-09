"""Steady-state thermal finite element solver (Tet4, linear).

Self-contained 3D 4-node tetrahedral solver for the stationary heat equation
using only NumPy and SciPy — the thermal counterpart of ``core.fea``. It does
NOT depend on Kratos or any external platform.

Governing equation (no volumetric source)::

    -div(k * grad T) = 0   in  Omega

Element conductivity matrix (scalar analogue of the elastic stiffness)::

    ke = k * V * G^T G      (4x4)

where G holds the shape-function gradients (dN_i/dx, dN_i/dy, dN_i/dz).

Boundary conditions
-------------------
- TEMPERATURE (Dirichlet): prescribed nodal temperature [K].
- HEAT_FLUX (Neumann): imposed normal flux q'' [W/m^2] on surface
  triangles, positive = inflow. Assembled as ``F += q * A / 3`` per node.
- CONVECTION (Robin): ``-k dT/dn = h (T - T_inf)`` on surface triangles.
  Assembled as ``Kc = h * A / 12 * [[2,1,1],[1,2,1],[1,1,2]]`` and
  ``Fc = h * T_inf * A / 3`` per node.

Principle: no silent fallback. Missing conductivity, missing boundary
conditions, unresolvable CAD selections and singular systems all raise an
explicit :class:`ThermalError` (or a validation-failed ``StudyResult`` at the
study layer) — never a hidden default.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

logger = logging.getLogger(__name__)


class ThermalError(Exception):
    """Raised when the thermal solver cannot produce a valid result."""


def _tet_conductivity(
    coords: np.ndarray, conductivity: float
) -> Tuple[float, np.ndarray, np.ndarray]:
    """Conductivity matrix of a single 4-node tetrahedron.

    Args:
        coords: (4, 3) array with the four tetrahedron vertices.
        conductivity: thermal conductivity k [W/(m.K)], must be > 0.

    Returns:
        (volume, ke, grads) where ke is the 4x4 element conductivity matrix
        and grads is the (3, 4) shape-function gradient matrix G.
    """
    if not np.isfinite(conductivity) or conductivity <= 0:
        raise ThermalError(
            f"Thermal conductivity must be positive, got {conductivity!r}."
        )
    X = np.array(
        [
            [1, coords[0, 0], coords[0, 1], coords[0, 2]],
            [1, coords[1, 0], coords[1, 1], coords[1, 2]],
            [1, coords[2, 0], coords[2, 1], coords[2, 2]],
            [1, coords[3, 0], coords[3, 1], coords[3, 2]],
        ],
        dtype=float,
    )
    det = np.linalg.det(X)
    # Same orientation-robust convention as core.fea: the physical volume is
    # always positive; a negative determinant only means non-right-handed
    # node ordering from the mesher.
    volume = abs(det) / 6.0
    if volume < 1e-15:
        raise ThermalError("Degenerate (zero-volume) tetrahedron encountered.")
    invX = np.linalg.inv(X)
    grads = invX[1:, :]  # (3, 4): rows dN/dx, dN/dy, dN/dz
    ke = float(conductivity) * float(volume) * (grads.T @ grads)
    return volume, ke, grads


def _triangle_area(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> float:
    """Area of a surface triangle."""
    area = 0.5 * float(np.linalg.norm(np.cross(p1 - p0, p2 - p0)))
    if area < 1e-18:
        raise ThermalError("Degenerate (zero-area) boundary triangle encountered.")
    return area


class ThermalSolver:
    """Solve a 3D Tet4 steady-state thermal problem K*T = F."""

    def __init__(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        conductivity: float,
    ):
        nodes = np.asarray(nodes, dtype=float)
        elements = np.asarray(elements, dtype=int)
        if nodes.ndim != 2 or nodes.shape[1] != 3:
            raise ThermalError("nodes must be an (N, 3) array")
        if elements.ndim != 2 or elements.shape[1] != 4:
            raise ThermalError("elements must be an (M, 4) array")
        if elements.size and (elements.min() < 0 or elements.max() >= nodes.shape[0]):
            raise ThermalError("elements contain out-of-range node indices")
        if not (nodes.shape[0] > 0 and elements.shape[0] > 0):
            raise ThermalError("empty mesh")
        if not np.isfinite(conductivity) or float(conductivity) <= 0:
            raise ThermalError(
                "El material no tiene conductividad térmica definida. "
                "Asigne un material con propiedades térmicas "
                "(thermal_conductivity > 0)."
            )
        self.nodes = nodes
        self.elements = elements
        self.num_nodes = nodes.shape[0]
        self.num_elements = elements.shape[0]
        self.conductivity = float(conductivity)
        self._K: Optional[sp.csc_matrix] = None

    # ------------------------------------------------------------------ #
    # Assembly
    # ------------------------------------------------------------------ #
    def assemble_conductivity(self) -> sp.csc_matrix:
        """Assemble the global sparse conductivity matrix (N x N, CSC)."""
        n_el = self.num_elements
        ii = np.empty((n_el, 4, 4), dtype=np.int64)
        jj = np.empty((n_el, 4, 4), dtype=np.int64)
        data = np.empty((n_el, 4, 4))
        for e in range(n_el):
            con = self.elements[e]
            _, ke, _ = _tet_conductivity(self.nodes[con], self.conductivity)
            data[e] = ke
            ii[e] = con[:, None]
            jj[e] = con[None, :]
        K = sp.csc_matrix(
            (data.ravel(), (ii.ravel(), jj.ravel())),
            shape=(self.num_nodes, self.num_nodes),
        )
        K = (K + K.T) * 0.5
        K.sort_indices()
        self._K = K
        return K

    def apply_bc_and_solve(
        self,
        dirichlet: Dict[int, float],
        neumann_faces: Optional[Sequence[Tuple[Sequence[int], float]]] = None,
        convection_faces: Optional[Sequence[Tuple[Sequence[int], float, float]]] = None,
    ) -> Dict[str, Any]:
        """Assemble BCs, solve K*T = F and post-process heat flux.

        Args:
            dirichlet: {node_index: temperature [K]} (at least one entry).
            neumann_faces: list of ((n0, n1, n2), q) with heat flux q [W/m^2],
                positive = inflow.
            convection_faces: list of ((n0, n1, n2), h, T_inf) with ``h``
                [W/(m^2.K)] and ambient temperature ``T_inf`` [K].

        Returns:
            Dict with ``temperatures`` (N,), ``heat_flux`` per element (M, 3),
            ``nodal_heat_flux_norm`` (N,) and assembly metadata.
        """
        if not dirichlet:
            raise ThermalError(
                "El problema térmico no tiene ninguna temperatura impuesta "
                "(Dirichlet). Sin al menos un nodo con temperatura fijada el "
                "sistema es singular: añada una condición TEMPERATURE."
            )
        K = self._K if self._K is not None else self.assemble_conductivity()
        # Work on LIL for the symmetric Robin contributions, then CSC.
        K_mod = K.tolil()
        F = np.zeros(self.num_nodes)

        for tri, q in neumann_faces or []:
            n0, n1, n2 = (int(tri[0]), int(tri[1]), int(tri[2]))
            area = _triangle_area(self.nodes[n0], self.nodes[n1], self.nodes[n2])
            if not np.isfinite(q):
                raise ThermalError(f"Heat flux must be finite, got {q!r}.")
            contrib = float(q) * area / 3.0
            F[n0] += contrib
            F[n1] += contrib
            F[n2] += contrib

        for tri, h, t_inf in convection_faces or []:
            n0, n1, n2 = (int(tri[0]), int(tri[1]), int(tri[2]))
            area = _triangle_area(self.nodes[n0], self.nodes[n1], self.nodes[n2])
            if not np.isfinite(h) or h < 0:
                raise ThermalError(
                    f"Convection coefficient h must be >= 0, got {h!r}."
                )
            if not np.isfinite(t_inf):
                raise ThermalError(f"Ambient temperature must be finite, got {t_inf!r}.")
            coef = float(h) * area / 12.0
            stiff = np.array([[2.0, 1.0, 1.0], [1.0, 2.0, 1.0], [1.0, 1.0, 2.0]])
            idx = (n0, n1, n2)
            for a in range(3):
                for b in range(3):
                    K_mod[idx[a], idx[b]] += coef * stiff[a, b]
                F[idx[a]] += float(h) * float(t_inf) * area / 3.0

        K_mod = K_mod.tocsc()
        fixed = np.array(sorted(dirichlet.keys()), dtype=np.int64)
        if fixed.min() < 0 or fixed.max() >= self.num_nodes:
            raise ThermalError("Dirichlet node indices out of range.")
        t_fixed = np.array([float(dirichlet[int(i)]) for i in fixed])
        if not np.all(np.isfinite(t_fixed)):
            raise ThermalError("Dirichlet temperatures must be finite.")
        all_nodes = np.arange(self.num_nodes)
        free = np.setdiff1d(all_nodes, fixed)
        if free.size == 0:
            temperatures = t_fixed[np.argsort(np.argsort(fixed))]
            # All nodes prescribed: still compute flux from the field.
            t_full = np.empty(self.num_nodes)
            t_full[fixed] = t_fixed
            return self._post_process(t_full)

        Kff = K_mod[np.ix_(free, free)]
        Ff = F[free] - K_mod[np.ix_(free, fixed)] @ t_fixed
        try:
            t_free = spla.spsolve(Kff, Ff)
        except Exception as exc:
            raise ThermalError(
                "El sistema térmico no pudo resolverse (matriz singular o "
                f"mal condicionada). Revise las condiciones de contorno: {exc}"
            ) from exc
        t_free = np.asarray(t_free, dtype=float).ravel()
        if t_free.shape[0] != free.size or not np.all(np.isfinite(t_free)):
            raise ThermalError(
                "El sistema térmico devolvió una solución no finita "
                "(matriz singular o BCs insuficientes). Añada condiciones "
                "TEMPERATURE para fijar el nivel térmico."
            )
        t_full = np.empty(self.num_nodes)
        t_full[fixed] = t_fixed
        t_full[free] = t_free
        return self._post_process(t_full)

    # ------------------------------------------------------------------ #
    # Post-processing
    # ------------------------------------------------------------------ #
    def _post_process(self, temperatures: np.ndarray) -> Dict[str, Any]:
        """Per-element heat-flux vectors q = -k * grad(T) + nodal average."""
        heat_flux = np.zeros((self.num_elements, 3))
        nodal_accum = np.zeros((self.num_nodes, 3))
        nodal_count = np.zeros(self.num_nodes)
        for e in range(self.num_elements):
            con = self.elements[e]
            _, _, grads = _tet_conductivity(self.nodes[con], self.conductivity)
            grad_t = grads @ temperatures[con]
            q = -self.conductivity * grad_t
            heat_flux[e] = q
            for node in con:
                nodal_accum[int(node)] += q
                nodal_count[int(node)] += 1.0
        nodal_flux = nodal_accum / np.maximum(nodal_count, 1.0)[:, None]
        return {
            "temperatures": np.asarray(temperatures, dtype=float),
            "heat_flux": heat_flux,
            "nodal_heat_flux": nodal_flux,
            "nodal_heat_flux_norm": np.linalg.norm(nodal_flux, axis=1),
            "min_temperature": float(np.min(temperatures)),
            "max_temperature": float(np.max(temperatures)),
            "num_nodes": self.num_nodes,
            "num_elements": self.num_elements,
            "conductivity": self.conductivity,
            "engine": "self-contained-numpy-tet4-thermal",
        }


def solve_steady_thermal(
    nodes: np.ndarray,
    elements: np.ndarray,
    conductivity: float,
    dirichlet: Dict[int, float],
    neumann_faces: Optional[Sequence[Tuple[Sequence[int], float]]] = None,
    convection_faces: Optional[Sequence[Tuple[Sequence[int], float, float]]] = None,
) -> Dict[str, Any]:
    """High-level entry point: assemble, apply BCs, solve, post-process."""
    solver = ThermalSolver(nodes, elements, conductivity)
    solver.assemble_conductivity()
    result = solver.apply_bc_and_solve(
        dirichlet, neumann_faces=neumann_faces, convection_faces=convection_faces
    )
    result["success"] = True
    result["status"] = "completed"
    return result


# ---------------------------------------------------------------------- #
# Study bridge: ThermalBoundary list -> solver inputs
# ---------------------------------------------------------------------- #
def _boundary_node_ids(boundary) -> Optional[List[int]]:
    """Explicit node ids from ``boundary.metadata['nodes']``, if present."""
    meta = getattr(boundary, "metadata", None) or {}
    nodes = meta.get("nodes")
    if nodes is None:
        return None
    return [int(i) for i in nodes]


def _boundary_faces(boundary) -> Optional[List[Tuple[int, int, int]]]:
    """Explicit surface triangles from ``boundary.metadata['faces']``."""
    meta = getattr(boundary, "metadata", None) or {}
    faces = meta.get("faces")
    if faces is None:
        return None
    return [(int(t[0]), int(t[1]), int(t[2])) for t in faces]


def solve_thermal_study(study, nodes, elements) -> Dict[str, Any]:
    """Solve a :class:`ThermalAnalysis` study on an explicit mesh.

    CAD ``selection`` sets cannot be resolved here: mapping CAD faces to mesh
    nodes requires the mesher's physical-group tables, which this layer does
    not own. Each :class:`ThermalBoundary` must therefore carry an explicit
    mesh mapping in its ``metadata``:

    - TEMPERATURE: ``metadata['nodes']`` = [node ids] (temperature taken
      from ``boundary.magnitude`` [K]).
    - HEAT_FLUX: ``metadata['faces']`` = [(n0, n1, n2), ...] (flux from
      ``boundary.magnitude`` [W/m^2], positive = inflow).
    - CONVECTION: ``metadata['faces']`` + ``boundary.h`` + ``boundary.T_inf``.

    A boundary with a non-empty CAD ``selection`` but no explicit mesh
    mapping raises :class:`ThermalError` telling the caller to resolve the
    mapping first — never a silent empty BC.
    """
    from core.cae_studies import ThermalBoundaryType  # local import: no cycle

    nodes = np.asarray(nodes, dtype=float)
    elements = np.asarray(elements, dtype=int)

    validation_msg = study.validate_with_message()
    if validation_msg is not None:
        raise ThermalError(validation_msg)
    conductivity = study.material.thermal_conductivity
    if conductivity is None or conductivity <= 0:
        raise ThermalError(
            "El material del estudio no tiene conductividad térmica definida. "
            "Asigne un material con propiedades térmicas (thermal_conductivity > 0)."
        )

    dirichlet: Dict[int, float] = {}
    neumann_faces: List[Tuple[Tuple[int, int, int], float]] = []
    convection_faces: List[Tuple[Tuple[int, int, int], float, float]] = []

    for boundary in study.thermal_boundaries:
        btype = boundary.boundary_type
        has_selection = (
            boundary.selection is not None and len(boundary.selection.entities) > 0
        )
        if btype == ThermalBoundaryType.TEMPERATURE:
            node_ids = _boundary_node_ids(boundary)
            if node_ids is None:
                raise ThermalError(
                    f"La condición TEMPERATURE '{boundary.name}' no tiene mapeo "
                    "a nodos de malla (metadata['nodes']). "
                    + (
                        "Resuelva su CAD selection a nodos vía los physical "
                        "groups del mallador antes de ejecutar."
                        if has_selection
                        else "Añada metadata['nodes'] con los ids de nodo."
                    )
                )
            for nid in node_ids:
                dirichlet[nid] = float(boundary.magnitude)
        elif btype == ThermalBoundaryType.HEAT_FLUX:
            faces = _boundary_faces(boundary)
            if faces is None:
                raise ThermalError(
                    f"La condición HEAT_FLUX '{boundary.name}' no tiene mapeo "
                    "a triángulos de superficie (metadata['faces']). "
                    + (
                        "Resuelva su CAD selection a elementos de superficie "
                        "vía los physical groups del mallador antes de ejecutar."
                        if has_selection
                        else "Añada metadata['faces'] con los triángulos."
                    )
                )
            for tri in faces:
                neumann_faces.append((tri, float(boundary.magnitude)))
        elif btype == ThermalBoundaryType.CONVECTION:
            faces = _boundary_faces(boundary)
            if faces is None:
                raise ThermalError(
                    f"La condición CONVECTION '{boundary.name}' no tiene mapeo "
                    "a triángulos de superficie (metadata['faces']). "
                    + (
                        "Resuelva su CAD selection a elementos de superficie "
                        "vía los physical groups del mallador antes de ejecutar."
                        if has_selection
                        else "Añada metadata['faces'] con los triángulos."
                    )
                )
            for tri in faces:
                convection_faces.append((tri, float(boundary.h), float(boundary.T_inf)))
        else:  # pragma: no cover — defensive: unknown future BC type
            raise ThermalError(f"Tipo de condición térmica desconocido: {btype!r}.")

    if not dirichlet:
        raise ThermalError(
            "El estudio térmico no define ninguna temperatura impuesta "
            "(TEMPERATURE con metadata['nodes']). Sin Dirichlet el sistema es "
            "singular: añada al menos una condición de temperatura."
        )

    return solve_steady_thermal(
        nodes,
        elements,
        float(conductivity),
        dirichlet,
        neumann_faces=neumann_faces,
        convection_faces=convection_faces,
    )
