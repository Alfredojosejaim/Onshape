"""Self-contained SIMP topology optimisation engine.

Implements the Solid Isotropic Material with Penalization (SIMP) method for
minimum compliance subject to a volume constraint, using the self-contained
Tet4 FEA solver in :mod:`core.fea`. It does NOT depend on Kratos or any
external optimisation framework, in accordance with the project's standalone
architecture.

The design variables are the per-element pseudo-densities ``rho`` in [xmin, 1].
Each FEA solve uses ``ke(rho) = rho**penalization * Ke0`` so that
intermediate densities are penalised toward 0/1.

A density filter is applied to avoid checker-boarding.

Volume constraint semantics (volfrac)
-------------------------------------
``volfrac`` constrains a fraction of the **active (optimizable) subdomain**
``V_active = V_total - V_preserved - V_void`` only (Option A in
``traceback.md`` "PROBLEMA 3"). Protected regions and halos are pinned at
``rho = 1`` (no design variable), void/obstruction elements at ``rho_min``;
neither participates in the OC bisection, whose target is ``volfrac * V_active``.

Consequence: when protected regions exist the fraction of the *physical total*
volume actually occupied is strictly higher than ``volfrac`` (e.g. 30% of the
free domain + 10% protected != 30% of the model). That is expected and matches
the SIMP literature, but the solver MUST report both numbers so the user is
never misled: :meth:`SIMPSolver.optimize` returns ``final_volume_fraction``
(active) and ``physical_volume_fraction`` (occupied rho-weighted volume over
the whole mesh, including preserved=1 and void=rho_min).
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from core.fea import FEASolver

logger = logging.getLogger(__name__)

XC_MIN = 1e-3


class TopOptError(Exception):
    """Raised when topology optimization cannot run."""


class SIMPSolver:
    """Minimise compliance:  min rho  c = u^T K u   s.t.  V(rho)/V0 <= volfrac.

    ``volfrac`` is a fraction of the ACTIVE (designable) subdomain only;
    preserved/protected elements stay at rho=1 and void at rho_min, so the
    physical (total-mesh) volume fraction is >= volfrac whenever protected
    regions exist. See the module docstring for the full semantics.
    """

    def __init__(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        young_modulus: float,
        poisson_ratio: float,
        volfrac: float = 0.3,
        penalization: float = 3.0,
        filter_radius: float = 1.5,
        element_densities0: Optional[np.ndarray] = None,
        rho_min: float = XC_MIN,
    ):
        if not 0.0 < volfrac <= 1.0:
            raise TopOptError("volfrac must be in (0, 1]")
        self.nodes = np.asarray(nodes, dtype=float)
        self.elements = np.asarray(elements, dtype=int)
        self.num_elements = self.elements.shape[0]
        self.volfrac = float(volfrac)
        self.penalization = float(penalization)
        self.filter_radius = float(filter_radius)
        self.rho_min = float(rho_min)

        self.fea = FEASolver(nodes, elements, young_modulus, poisson_ratio)
        self.dof_map = self._compute_dof_map()
        self.element_centers = self._compute_element_centers()
        self._filter = self._build_weighted_filter()

        if element_densities0 is not None:
            self.x = np.clip(np.asarray(element_densities0, dtype=float).ravel(), self.rho_min, 1.0)
            if self.x.shape[0] != self.num_elements:
                raise TopOptError("element_densities0 length must equal element count")
        else:
            self.x = np.full(self.num_elements, min(volfrac, 1.0))

        self._forces: Optional[np.ndarray] = None
        self._fixed_dofs: Optional[np.ndarray] = None
        self._volumes = self._element_volumes()
        self._vol0 = float(self._volumes.sum())

        # Design-subdomain masks (protected / void).  Protected elements are
        # forced to stay dense (material always present); void elements (e.g.
        # obstructions) stay at rho_min (no material).  Neither participates in
        # the volume-constrained OC update.
        self._preserved: Optional[np.ndarray] = None
        self._void: Optional[np.ndarray] = None
        self._active: np.ndarray = np.ones(self.num_elements, dtype=bool)
        self._vol0_free = float(self._vol0)

    # ------------------------------------------------------------------ #
    # Mesh helpers
    # ------------------------------------------------------------------ #
    def _compute_dof_map(self) -> np.ndarray:
        dof_map = np.empty((self.num_elements, 12), dtype=np.int64)
        for i, con in enumerate(self.elements):
            base = con * 3
            dof_map[i] = np.array(
                [
                    base[0], base[0] + 1, base[0] + 2,
                    base[1], base[1] + 1, base[1] + 2,
                    base[2], base[2] + 1, base[2] + 2,
                    base[3], base[3] + 1, base[3] + 2,
                ],
                dtype=np.int64,
            )
        return dof_map

    def _compute_element_centers(self) -> np.ndarray:
        centers = np.zeros((self.num_elements, 3))
        for i, con in enumerate(self.elements):
            centers[i] = self.nodes[con].mean(axis=0)
        return centers

    def _element_volumes(self) -> np.ndarray:
        from core.fea import _tet_volume_and_B

        vols = np.zeros(self.num_elements)
        for i, con in enumerate(self.elements):
            _, B = None, None
            coords = self.nodes[con]
            vol, _ = _tet_volume_and_B(coords)
            vols[i] = abs(vol)
        return vols

    def _build_weighted_filter(self) -> np.ndarray:
        """Weighted density filter H (num_elements x num_elements, sparse).

        H[i, j] = rmin - dist(c_i, c_j), for neighbours within the filter
        radius, otherwise 0. Applications smooth the density field.
        """
        from scipy.spatial import cKDTree

        if self.filter_radius is None or self.filter_radius <= 0:
            return None
        tree = cKDTree(self.element_centers)
        pairs = tree.query_pairs(r=self.filter_radius + 1e-9)
        rmin = float(self.filter_radius)
        rows: List[int] = []
        cols: List[int] = []
        vals: List[float] = []
        for i, j in pairs:
            d = np.linalg.norm(self.element_centers[i] - self.element_centers[j])
            w = max(0.0, rmin - d)
            if w > 0:
                rows.append(i); cols.append(j); vals.append(w)
                rows.append(j); cols.append(i); vals.append(w)
        # self-weight
        for i in range(self.num_elements):
            rows.append(i); cols.append(i); vals.append(rmin)
        from scipy import sparse as sp

        H = sp.coo_matrix(
            (vals, (rows, cols)), shape=(self.num_elements, self.num_elements)
        ).tocsr()
        self._Hs_col = np.asarray(H.sum(axis=1)).ravel()
        return H

    def _apply_filter(self, dcdx: np.ndarray, x: np.ndarray) -> np.ndarray:
        if self._filter is None:
            return dcdx
        dcdx = self._filter.dot(dcdx)
        xf = np.asarray(self._filter.dot(x)).ravel()
        Hs = self._Hs_col
        return np.divide(dcdx, np.maximum(Hs * xf, 1e-12))

    # ------------------------------------------------------------------ #
    # Boundary conditions
    # ------------------------------------------------------------------ #
    def set_load(self, force: np.ndarray) -> None:
        f = np.asarray(force, dtype=float).ravel()
        if f.shape[0] != self.fea.num_dofs:
            raise TopOptError("force length must equal the mesh DOF count")
        self._forces = f

    def set_fixed_dofs(self, fixed_dofs: np.ndarray) -> None:
        self._fixed_dofs = np.sort(np.asarray(fixed_dofs, dtype=np.int64))

    # ------------------------------------------------------------------ #
    # Design subdomains
    # ------------------------------------------------------------------ #
    def _finalize_active(self) -> None:
        """Recompute the active (designable) mask and free volume after the
        protected/void element sets change."""
        preserved = self._preserved if self._preserved is not None else \
            np.zeros(self.num_elements, dtype=bool)
        void = self._void if self._void is not None else \
            np.zeros(self.num_elements, dtype=bool)
        self._active = ~(preserved | void)
        self._vol0_free = float(self._volumes[self._active].sum())
        # Feasibility: with every active element at its lower bound rho_min the
        # minimal achievable active volume is rho_min * V_active. If the user's
        # volfrac demands less than that, the volume constraint is infeasible
        # (OC bisection could never converge below it). Surface that loudly
        # instead of silently returning an impossible optimum.
        if self.volfrac * self._vol0_free < self.rho_min * self._vol0_free:
            raise TopOptError(
                "Volume fraction infeasible: volfrac={} over the active "
                "domain (V_active={:.4g}) requires less than the minimum "
                "material (rho_min * V_active = {:.4g}). Lower rho_min, raise "
                "volfrac, or shrink preserved/void regions."
                .format(self.volfrac, self._vol0_free, self.rho_min * self._vol0_free)
            )

    def set_preserved_elements(self, indices) -> None:
        """Mark elements that must keep material (protected regions).

        These elements are pinned at density 1.0 and excluded from the
        volume-constrained OC update.
        """
        mask = np.zeros(self.num_elements, dtype=bool)
        mask[np.asarray(indices, dtype=np.int64)] = True
        self._preserved = mask
        self._finalize_active()

    def set_void_elements(self, indices) -> None:
        """Mark elements that must stay empty (obstructions / no-go zones).

        These elements are pinned at ``rho_min`` and excluded from the
        volume-constrained OC update.
        """
        mask = np.zeros(self.num_elements, dtype=bool)
        mask[np.asarray(indices, dtype=np.int64)] = True
        self._void = mask
        self._finalize_active()

    def protect_elements_near_nodes(
        self,
        node_indices,
        radius: Optional[float] = None,
    ) -> None:
        """Mark as preserved (rho=1, non-optimisable) every element whose
        centroid lies within *radius* of any node in *node_indices*.

        This creates an automatic keep-out zone around load / support nodes,
        preventing the SIMP optimiser from removing material precisely where
        forces are applied or reactions are concentrated (the classic spurious
        sensitivity artifact near boundary conditions).

        The halo **unites** with any previously preserved elements and never
        replaces them.

        Args:
            node_indices: Iterable of 0-based mesh node indices (typically the
                union of load and support node sets).
            radius: Keep-out radius in mesh length units.  When ``None``,
                defaults to 2x the characteristic element size (h_element),
                computed as the 95th percentile of nearest-centroid distances.
                This matches the Saint-Venant dissipation length which is
                proportional to mesh element size, not the density filter radius.
        """
        if radius is None:
            # Characteristic element size from element volume (length scale that
            # grows/shrinks with mesh resolution, independent of filter_radius).
            if self.num_elements >= 1:
                _v_mean = float(np.mean(self._volumes))
                # Regular-tet edge length: V = a^3 / (6 sqrt(2))  ->  a ~ 2.04 V^(1/3)
                h_element = 2.0 * max(float(_v_mean) ** (1.0 / 3.0), 1e-9)
            else:
                h_element = 1.0
            radius = 2.0 * h_element
        node_indices = np.asarray(list(node_indices), dtype=np.int64)
        if node_indices.size == 0:
            return
        from scipy.spatial import cKDTree
        tree = cKDTree(self.nodes[node_indices])
        dist, _ = tree.query(self.element_centers, k=1)
        halo = np.nonzero(dist <= radius)[0]
        if self._preserved is not None:
            halo = np.union1d(halo, np.nonzero(self._preserved)[0])
        self.set_preserved_elements(halo)

    # ------------------------------------------------------------------ #
    # Objective / sensitivity
    # ------------------------------------------------------------------ #
    def _solve(self, x: np.ndarray) -> np.ndarray:
        if self._forces is None:
            raise TopOptError("load vector not set; call set_load() first")
        fixed = self._fixed_dofs if self._fixed_dofs is not None else np.array([], dtype=np.int64)
        weights = np.power(x, self.penalization)
        u = self.fea.apply_bc_and_solve(self._forces, fixed, densities=weights)
        return u

    def _compliance_and_sensitivities(self, x: np.ndarray) -> Tuple[float, np.ndarray]:
        u = self._solve(x)
        compliance = 0.0
        dc = np.zeros(self.num_elements)
        # compliance = sum_e rho_e^p * u_e^T Ke0 u_e
        for e in range(self.num_elements):
            dm = self.dof_map[e]
            ue = u[dm]
            ke = self.fea.element_stiffness(e)
            ukeu = ue @ ke @ ue
            compliance += float(ukeu) * (x[e] ** self.penalization)
            dc[e] = float(-self.penalization * (x[e] ** (self.penalization - 1)) * ukeu)
        return compliance, dc

    # ------------------------------------------------------------------ #
    # Optimality criteria update (OC)
    # ------------------------------------------------------------------ #
    def _oc_update(
        self,
        x: np.ndarray,
        dc: np.ndarray,
        dv: Optional[np.ndarray],
    ) -> np.ndarray:
        """Optimality criteria (Bendsoe & Sigmund) with bisection on the
        Lagrange multiplier for the volume constraint and a 99-line-like OC.

        Only the *active* subdomain participates.  Protected elements stay at
        1.0 and void elements stay at ``rho_min``.
        """
        move = 0.2
        if dv is None:
            dv = self._volumes
        active = self._active
        l1, l2 = 0.0, 1e6
        xnew = np.copy(x)
        xmin = self.rho_min
        xmax = 1.0
        target_vol = self.volfrac * self._vol0_free
        for _ in range(100):
            mid = 0.5 * (l1 + l2)
            xnew[active] = np.maximum(
                xmin,
                np.minimum(
                    xmax,
                    np.maximum(
                        xmin,
                        x[active] * np.sqrt(
                            np.abs(-dc[active]) / np.maximum(np.abs(mid * dv[active]), 1e-12)
                        ),
                    ),
                ),
            )
            xnew[active] = np.maximum(x[active] - move, np.minimum(x[active] + move, xnew[active]))
            vol = float(np.dot(xnew[active], dv[active]))
            if vol > target_vol + 1e-12:
                l1 = mid
            elif vol < target_vol - 1e-12:
                l2 = mid
            else:
                break
        # Re-pin the pinned subdomains
        if self._preserved is not None:
            xnew[self._preserved] = 1.0
        if self._void is not None:
            xnew[self._void] = xmin
        return xnew

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def optimize(
        self,
        max_iterations: int = 50,
        tolerance: float = 0.01,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        x = np.copy(self.x)
        converged = False
        history: List[Dict[str, Any]] = []
        for it in range(max_iterations):
            compliance, dc = self._compliance_and_sensitivities(x)
            dc_f = self._apply_filter(dc, x)
            xnew = self._oc_update(x, dc_f, self._volumes)

            change = float(np.max(np.abs(xnew - x)))
            # volume fraction relative to the active, designable subdomain
            vol_frac = float(np.dot(xnew[self._active], self._volumes[self._active]) / max(self._vol0_free, 1e-12))

            history.append(
                {
                    "iteration": it + 1,
                    "compliance": float(compliance),
                    "volume_fraction": vol_frac,
                    "max_change": change,
                }
            )
            if callback:
                callback(
                    {
                        "iteration": it + 1,
                        "compliance": float(compliance),
                        "volume_fraction": vol_frac,
                        "max_change": change,
                        "densities": xnew.copy(),
                    }
                )
            x = xnew
            if change < tolerance:
                converged = True
                break

        # Final analysis with converged density field
        final_u = self._solve(x)
        weight = np.power(x, self.penalization)
        ke_term = np.zeros(self.num_elements)
        compliance_final = 0.0
        for e in range(self.num_elements):
            dm = self.dof_map[e]
            ue = final_u[dm]
            ke = self.fea.element_stiffness(e)
            ukeu = ue @ ke @ ue
            compliance_final += float(ukeu) * weight[e]
            ke_term[e] = float(ukeu)

        nodal_vm = self._nodal_vm(final_u)
        max_disp = float(np.max(np.abs(final_u))) if final_u.size else 0.0

        result = {
            "success": True,
            "status": "completed",
            "converged": bool(converged),
            "iterations": len(history),
            "max_iterations": max_iterations,
            "tolerance": tolerance,
            "final_volume_fraction": float(np.dot(x[self._active], self._volumes[self._active]) / max(self._vol0_free, 1e-12)),
            "physical_volume_fraction": float(
                np.dot(x, self._volumes) / max(self._vol0, 1e-12)
            ),
            "target_volume_fraction": float(self.volfrac),
            "final_compliance": float(compliance_final),
            "compliance_history": [h["compliance"] for h in history],
            "volume_fraction_history": [h["volume_fraction"] for h in history],
            "max_density_change": float(np.max(np.abs(x - self.x))),
            "densities": x.tolist(),
            "preserved_elements": (self._preserved.tolist() if self._preserved is not None else None),
            "void_elements": (self._void.tolist() if self._void is not None else None),
            "displacements": final_u.tolist(),
            "max_displacement": max_disp,
            "element_strain_energy": ke_term.tolist(),
            "nodal_von_mises": nodal_vm.tolist(),
            "penalization": float(self.penalization),
            "filter_radius": float(self.filter_radius),
            "engine": "self-contained-simp-numpy",
        }
        self.x = x
        return result

    def _nodal_vm(self, u: np.ndarray) -> np.ndarray:
        nodal_accum = np.zeros(self.fea.num_nodes)
        nodal_count = np.zeros(self.fea.num_nodes)
        D = self.fea.D
        for e in range(self.fea.num_elements):
            con = self.fea.elements[e]
            coords = self.fea.nodes[con]
            from core.fea import _tet_volume_and_B

            _, B = _tet_volume_and_B(coords)
            ue = u[self.dof_map[e]]
            stress = D @ (B @ ue)
            sv = np.sqrt(
                stress[0] ** 2 + stress[1] ** 2 + stress[2] ** 2
                - stress[0] * stress[1] - stress[0] * stress[2] - stress[1] * stress[2]
                + 3.0 * (stress[3] ** 2 + stress[4] ** 2 + stress[5] ** 2)
            )
            for node in con:
                nodal_accum[node] += float(sv)
                nodal_count[node] += 1.0
        return np.divide(nodal_accum, nodal_count, out=np.zeros_like(nodal_accum), where=nodal_count > 0)


def run_topology_optimization(
    nodes: np.ndarray,
    elements: np.ndarray,
    young_modulus: float,
    poisson_ratio: float,
    force_vector: np.ndarray,
    fixed_dofs: np.ndarray,
    volfrac: float = 0.3,
    penalization: float = 3.0,
    filter_radius: float = 1.5,
    max_iterations: int = 50,
    tolerance: float = 0.01,
    callback=None,
) -> Dict[str, Any]:
    """Convenience high-level SIMP entry point (self-contained)."""
    solver = SIMPSolver(
        nodes=nodes,
        elements=elements,
        young_modulus=young_modulus,
        poisson_ratio=poisson_ratio,
        volfrac=volfrac,
        penalization=penalization,
        filter_radius=filter_radius,
    )
    solver.set_load(force_vector)
    solver.set_fixed_dofs(fixed_dofs)
    return solver.optimize(max_iterations=max_iterations, tolerance=tolerance, callback=callback)
