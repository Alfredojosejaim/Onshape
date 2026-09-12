"""Copia vendorizada de Topologia_Optimizada/core/topopt.py con solver inyectable.

UNICA diferencia funcional frente al original: ``SIMPSolver.__init__`` acepta
``fea_solver`` (interfaz: num_dofs/num_nodes/num_elements/D/elements/nodes,
``apply_bc_and_solve(F, fixed, densities)``, ``element_stiffness(e)``).
Con ``fea_solver=None`` el comportamiento es identico al original.
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
        fea_solver: Any = None,
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

        # VENDORED-CHANGE: solver FEA inyectable (default = local, identico).
        if fea_solver is None:
            fea_solver = FEASolver(nodes, elements, young_modulus, poisson_ratio)
        self.fea = fea_solver
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
        self._load_cases: Optional[List[Tuple[np.ndarray, float]]] = None
        self._fixed_dofs: Optional[np.ndarray] = None
        self._volumes = self._element_volumes()
        self._vol0 = float(self._volumes.sum())

        self._preserved: Optional[np.ndarray] = None
        self._void: Optional[np.ndarray] = None
        self._active: np.ndarray = np.ones(self.num_elements, dtype=bool)
        self._vol0_free = float(self._vol0)

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
            coords = self.nodes[con]
            vol, _ = _tet_volume_and_B(coords)
            vols[i] = abs(vol)
        return vols

    def _build_weighted_filter(self) -> np.ndarray:
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

    def set_load(self, force: np.ndarray) -> None:
        f = np.asarray(force, dtype=float).ravel()
        if f.shape[0] != self.fea.num_dofs:
            raise TopOptError("force length must equal the mesh DOF count")
        self._forces = f
        # Compat: caso unico con peso 1.
        self._load_cases = [(f, 1.0)]

    def set_loads(
        self,
        forces: List[np.ndarray],
        weights: Optional[List[float]] = None,
    ) -> None:
        """MULTICARGA: N casos evaluados simultaneamente.

        Objetivo ponderado (estandar SIMP multicarga):
            c(rho) = sum_i w_i * u_i^T K(rho) u_i,
            dc/de  = sum_i w_i * dc_i/de,
        con K(rho)·u_i = F_i por caso. Kratos (KratosSimpFEA) resuelve
        cada caso con su propio RHS secuencialmente; el motor local hace
        lo mismo. Pesos normalizados a suma 1 (si todos son 0 -> error).
        """
        if not forces:
            raise TopOptError("set_loads() requires at least one force vector")
        n = len(forces)
        if weights is None:
            weights = [1.0] * n
        if len(weights) != n:
            raise TopOptError("forces and weights length mismatch")
        w = [float(x) for x in weights]
        if any(not np.isfinite(x) or x < 0 for x in w):
            raise TopOptError("load weights must be finite and >= 0")
        if sum(w) <= 0:
            raise TopOptError("at least one load weight must be > 0")
        total = sum(w)
        w = [x / total for x in w]
        cases = []
        for f in forces:
            fv = np.asarray(f, dtype=float).ravel()
            if fv.shape[0] != self.fea.num_dofs:
                raise TopOptError("force length must equal the mesh DOF count")
            cases.append(fv)
        self._load_cases = list(zip(cases, w))
        # _forces conserva la suma ponderada (solo informativo / compat).
        self._forces = sum(fv * wi for fv, wi in self._load_cases)

    def set_fixed_dofs(self, fixed_dofs: np.ndarray) -> None:
        self._fixed_dofs = np.sort(np.asarray(fixed_dofs, dtype=np.int64))

    def _finalize_active(self) -> None:
        preserved = self._preserved if self._preserved is not None else \
            np.zeros(self.num_elements, dtype=bool)
        void = self._void if self._void is not None else \
            np.zeros(self.num_elements, dtype=bool)
        self._active = ~(preserved | void)
        self._vol0_free = float(self._volumes[self._active].sum())
        if self.volfrac * self._vol0_free < self.rho_min * self._vol0_free:
            raise TopOptError(
                "Volume fraction infeasible: volfrac={} over the active "
                "domain (V_active={:.4g}) requires less than the minimum "
                "material (rho_min * V_active = {:.4g}). Lower rho_min, raise "
                "volfrac, or shrink preserved/void regions."
                .format(self.volfrac, self._vol0_free, self.rho_min * self._vol0_free)
            )

    def set_preserved_elements(self, indices) -> None:
        mask = np.zeros(self.num_elements, dtype=bool)
        mask[np.asarray(indices, dtype=np.int64)] = True
        self._preserved = mask
        self._finalize_active()

    def set_void_elements(self, indices) -> None:
        mask = np.zeros(self.num_elements, dtype=bool)
        mask[np.asarray(indices, dtype=np.int64)] = True
        self._void = mask
        self._finalize_active()

    def protect_elements_near_nodes(
        self,
        node_indices,
        radius: Optional[float] = None,
    ) -> None:
        if radius is None:
            if self.num_elements >= 1:
                _v_mean = float(np.mean(self._volumes))
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

    def _solve(self, x: np.ndarray) -> np.ndarray:
        # Compat single-load: primer caso (peso aplicado en sensibilidades).
        if self._forces is None:
            raise TopOptError("load vector not set; call set_load()/set_loads() first")
        cases = getattr(self, "_load_cases", None)
        F = cases[0][0] if cases else self._forces
        fixed = self._fixed_dofs if self._fixed_dofs is not None else np.array([], dtype=np.int64)
        weights = np.power(x, self.penalization)
        u = self.fea.apply_bc_and_solve(F, fixed, densities=weights)
        return u

    def _solve_all(self, x: np.ndarray) -> List[np.ndarray]:
        """Resuelve K(rho)·u_i = F_i para cada caso de carga."""
        cases = getattr(self, "_load_cases", None)
        if not cases:
            raise TopOptError("load vector not set; call set_load()/set_loads() first")
        fixed = self._fixed_dofs if self._fixed_dofs is not None else np.array([], dtype=np.int64)
        weights = np.power(x, self.penalization)
        return [self.fea.apply_bc_and_solve(F, fixed, densities=weights) for F, _ in cases]

    def _compliance_and_sensitivities(self, x: np.ndarray) -> Tuple[float, np.ndarray]:
        cases = getattr(self, "_load_cases", None) or []
        if not cases:
            raise TopOptError("load vector not set; call set_load()/set_loads() first")
        us = self._solve_all(x)
        compliance = 0.0
        dc = np.zeros(self.num_elements)
        for (F, w), u in zip(cases, us):
            for e in range(self.num_elements):
                dm = self.dof_map[e]
                ue = u[dm]
                ke = self.fea.element_stiffness(e)
                ukeu = ue @ ke @ ue
                compliance += float(w * ukeu) * (x[e] ** self.penalization)
                dc[e] += float(w * -self.penalization * (x[e] ** (self.penalization - 1)) * ukeu)
        return compliance, dc

    def _oc_update(
        self,
        x: np.ndarray,
        dc: np.ndarray,
        dv: Optional[np.ndarray],
    ) -> np.ndarray:
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
        if self._preserved is not None:
            xnew[self._preserved] = 1.0
        if self._void is not None:
            xnew[self._void] = xmin
        return xnew

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

        final_us = self._solve_all(x)
        final_u = final_us[0]
        weight = np.power(x, self.penalization)
        ke_term = np.zeros(self.num_elements)
        compliance_final = 0.0
        cases = getattr(self, "_load_cases", None) or []
        per_case = []
        for (F, w), uu in zip(cases, final_us):
            cc = 0.0
            for e in range(self.num_elements):
                dm = self.dof_map[e]
                ue = uu[dm]
                ke = self.fea.element_stiffness(e)
                ukeu = float(ue @ ke @ ue) * weight[e]
                cc += ukeu
            per_case.append({"weight": float(w), "compliance": float(cc)})
            compliance_final += float(w) * float(cc)
        # ke_term / VM del caso dominante (mayor peso; desempate: primero).
        dom = max(range(len(final_us)), key=lambda i: cases[i][1]) if final_us else 0
        final_u = final_us[dom]
        for e in range(self.num_elements):
            dm = self.dof_map[e]
            ue = final_u[dm]
            ke = self.fea.element_stiffness(e)
            ke_term[e] = float(ue @ ke @ ue)

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
            "num_load_cases": len(cases),
            "load_weights": [float(w) for _, w in cases],
            "per_case_compliance": per_case,
            # VENDORED-CHANGE: etiqueta segun el motor inyectado.
            "engine": getattr(self.fea, "engine_tag", "self-contained-simp-numpy"),
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
