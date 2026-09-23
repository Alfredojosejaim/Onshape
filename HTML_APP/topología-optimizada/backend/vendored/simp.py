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
        volfrac_mode: str = "active_domain",
    ):
        if not 0.0 < volfrac <= 1.0:
            raise TopOptError("volfrac must be in (0, 1]")
        # Estado de init primero: la bandera debe existir antes de cualquier
        # manejo de self.x (la usa _finalize_active vía set_preserved/void).
        self._x_from_user = element_densities0 is not None
        self.nodes = np.asarray(nodes, dtype=float)
        self.elements = np.asarray(elements, dtype=int)
        self.num_elements = self.elements.shape[0]
        self.volfrac = float(volfrac)
        # VOLFRAC-MODE (espejo de core/topopt.py): "active_domain" = fracción
        # del subdominio diseñable (histórico); "total_volume" = fracción del
        # volumen TOTAL de la malla descontando lo fijado.
        self.volfrac_mode = str(volfrac_mode).strip().lower()
        if self.volfrac_mode not in ("active_domain", "total_volume"):
            raise TopOptError(
                f"volfrac_mode={volfrac_mode!r} no soportado "
                f"(usar 'active_domain' o 'total_volume').")
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

    def _preserved_volume(self) -> float:
        if self._preserved is None:
            return 0.0
        return float(self._volumes[self._preserved].sum())

    def _void_volume(self) -> float:
        if self._void is None:
            return 0.0
        return float(self._volumes[self._void].sum())

    def _target_active_volume(self) -> float:
        """Volumen objetivo sobre el subdominio activo (espejo core/topopt)."""
        if self.volfrac_mode == "total_volume":
            return (self.volfrac * self._vol0
                    - self._preserved_volume()
                    - self.rho_min * self._void_volume())
        return self.volfrac * self._vol0_free

    def _finalize_active(self) -> None:
        preserved = self._preserved if self._preserved is not None else \
            np.zeros(self.num_elements, dtype=bool)
        void = self._void if self._void is not None else \
            np.zeros(self.num_elements, dtype=bool)
        self._active = ~(preserved | void)
        self._vol0_free = float(self._volumes[self._active].sum())
        target_active = self._target_active_volume()
        vmin = self.rho_min * self._vol0_free
        if target_active < vmin - 1e-12 * max(self._vol0, 1.0):
            raise TopOptError(
                "Volume fraction infeasible: mode={} volfrac={} needs active "
                "volume {:.4g} but the minimum material over the active domain "
                "is {:.4g}. Lower rho_min, raise volfrac, or shrink "
                "preserved/void regions."
                .format(self.volfrac_mode, self.volfrac, target_active, vmin)
            )
        if target_active > self._vol0_free + 1e-12 * max(self._vol0, 1.0):
            raise TopOptError(
                "Volume fraction infeasible: mode={} volfrac={} needs active "
                "volume {:.4g} > V_active={:.4g} (preserved/void already exceed "
                "the requested total). Lower volfrac or shrink preserved/void."
                .format(self.volfrac_mode, self.volfrac, target_active, self._vol0_free)
            )
        if self.volfrac_mode == "total_volume" and not self._x_from_user:
            frac = float(np.clip(target_active / max(self._vol0_free, 1e-12),
                                 self.rho_min, 1.0))
            self.x[self._active] = frac
            self.x[preserved] = 1.0
            self.x[void] = self.rho_min

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

    # NOTA Fase 4.5b (decisión explícita): este archivo vuelve a estar
    # CONGELADO. La simetría (set_symmetry_planes + espejo) vive SOLO en
    # core/topopt.py. Si se piden symmetry_planes por este path, api._simp_loop
    # falla explícito en vez de ignorarlo en silencio.
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
        target_vol = self._target_active_volume()
        # FASE-2 (2026-09-23, reversible): piso relativo a la máquina, espejo
        # de OC-BISECTION-FLOOR en core/topopt.py. El piso absoluto (1e-12)
        # rompía la invariancia de escala del OC en mallas rígidas. Para
        # volver atrás: restaurar el piso 1e-12.
        _den_floor = float(np.finfo(np.float64).tiny)
        for _ in range(100):
            mid = 0.5 * (l1 + l2)
            xnew[active] = np.maximum(
                xmin,
                np.minimum(
                    xmax,
                    np.maximum(
                        xmin,
                        x[active] * np.sqrt(
                            np.abs(-dc[active]) / np.maximum(np.abs(mid * dv[active]), _den_floor)
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

    # ------------------------------------------------------------------ #
    # MMA propio (Fase 4, espejo de core/topopt.py).
    # Solo el subdominio activo participa; fijos se re-pinean igual que OC.
    # ------------------------------------------------------------------ #
    _MMA_ASYINIT = 0.5
    _MMA_ASYINCR = 1.2
    _MMA_ASYDECR = 0.7
    _MMA_ALBEFA = 0.1

    def _mma_reset_state(self, x: np.ndarray) -> None:
        n = self.num_elements
        self._mma_xold1 = np.copy(x)
        self._mma_xold2 = np.copy(x)
        self._mma_low = np.zeros(n)
        self._mma_upp = np.ones(n)
        self._mma_iter = 0

    def _mma_update(
        self,
        x: np.ndarray,
        df0: np.ndarray,
        dv: Optional[np.ndarray],
        fscale: float,
    ) -> np.ndarray:
        xmin = self.rho_min
        xmax = 1.0
        active = self._active
        idx = np.nonzero(active)[0]
        if idx.size == 0:
            return np.copy(x)
        if dv is None:
            dv = self._volumes
        fs = max(float(fscale), 1e-12)

        xa = x[idx]
        df0a = np.asarray(df0, dtype=float)[idx] / fs
        dva = np.asarray(dv, dtype=float)[idx]
        xa_min = np.full_like(xa, xmin)
        xa_max = np.full_like(xa, xmax)

        if not hasattr(self, "_mma_low") or self._mma_low is None \
                or self._mma_low.shape[0] != self.num_elements:
            self._mma_reset_state(x)
        self._mma_iter = int(getattr(self, "_mma_iter", 0)) + 1
        it = self._mma_iter
        xold1 = self._mma_xold1[idx]
        xold2 = self._mma_xold2[idx]
        low = self._mma_low[idx]
        upp = self._mma_upp[idx]

        if it < 3:
            low = xa - self._MMA_ASYINIT * (xa_max - xa_min)
            upp = xa + self._MMA_ASYINIT * (xa_max - xa_min)
        else:
            zzz1 = (xa - xold1) * (xold1 - xold2)
            factor = np.ones_like(xa)
            factor[zzz1 > 0] = self._MMA_ASYINCR
            factor[zzz1 < 0] = self._MMA_ASYDECR
            low = xa - factor * (xold1 - low)
            upp = xa + factor * (upp - xold1)
            span = xa_max - xa_min
            low = np.minimum(np.maximum(low, xa - 10.0 * span), xa - 0.01 * span)
            upp = np.maximum(np.minimum(upp, xa + 10.0 * span), xa + 0.01 * span)

        alfa = np.maximum(low + self._MMA_ALBEFA * (xa - low), xa_min)
        beta = np.minimum(upp - self._MMA_ALBEFA * (upp - xa), xa_max)

        ux = upp - xa
        lx = xa - low
        p0 = ux * ux * np.maximum(df0a, 0.0) + 1e-9
        q0 = lx * lx * np.maximum(-df0a, 0.0) + 1e-9
        vt = max(float(self._target_active_volume()), 1e-12)
        dg = dva / vt
        p1 = ux * ux * np.maximum(dg, 0.0)
        q1 = lx * lx * np.maximum(-dg, 0.0)
        g0 = float(np.dot(xa, dva) / vt) - 1.0

        def _primal(lam: float):
            P = p0 + lam * p1
            Q = q0 + lam * q1
            sqP = np.sqrt(np.maximum(P, 1e-18))
            sqQ = np.sqrt(np.maximum(Q, 1e-18))
            xn = (sqP * low + sqQ * upp) / (sqP + sqQ)
            xn = np.minimum(np.maximum(xn, alfa), beta)
            return xn, sqP, sqQ

        def _g_approx(lam: float) -> float:
            xn, _, _ = _primal(lam)
            return g0 + float(np.dot(xn - xa, dg))

        if _g_approx(0.0) <= 0.0:
            lam = 0.0
        else:
            lo, hi = 0.0, 1.0
            while _g_approx(hi) > 0.0 and hi < 1e12:
                hi *= 2.0
            for _ in range(100):
                mid = 0.5 * (lo + hi)
                if _g_approx(mid) > 0.0:
                    lo = mid
                else:
                    hi = mid
                if hi - lo <= 1e-12 * max(hi, 1.0):
                    break
            lam = 0.5 * (lo + hi)

        xnew_a, _, _ = _primal(lam)

        self._mma_xold2[idx] = xold1
        self._mma_xold1[idx] = xa
        self._mma_low[idx] = low
        self._mma_upp[idx] = upp

        xnew = np.copy(x)
        xnew[idx] = xnew_a
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
        optimizer: str = "oc",
        evolutionary_rate: float = 0.02,
        eso_criterion: str = "compliance",
        ls_cfl: float = 0.5,
        ls_hole_period: int = 3,
    ) -> Dict[str, Any]:
        """Run the SIMP loop.

        Args:
            optimizer: "oc" (default histórico), "mma" (espejo de
                core/topopt.py, Fase 4), "eso" (hard-kill, Fase 6a) o
                "level_set" (delegado al núcleo, Fase 6f: el level-set es
                nuevo sin legado que espejar; la delegación garantiza
                comportamiento idéntico). Otro valor → TopOptError
                explícito, sin fallback silencioso.
        """
        if optimizer not in ("oc", "mma", "eso", "level_set"):
            raise TopOptError(
                f"optimizer={optimizer!r} no soportado (usar 'oc', 'mma', 'eso' o 'level_set')."
            )
        if optimizer == "level_set":
            from core.topopt import SIMPSolver as _CoreSIMP
            from core.topopt import TopOptError as _CoreErr
            try:
                return _CoreSIMP._level_set_optimize(
                    self,
                    max_iterations=max_iterations,
                    tolerance=tolerance,
                    callback=callback,
                    ls_cfl=ls_cfl,
                    ls_hole_period=ls_hole_period,
                )
            except _CoreErr as exc:
                raise TopOptError(str(exc))
        if optimizer == "eso":
            return self._eso_optimize(
                max_iterations=max_iterations,
                tolerance=tolerance,
                callback=callback,
                evolutionary_rate=evolutionary_rate,
                eso_criterion=eso_criterion,
            )
        x = np.copy(self.x)
        converged = False
        history: List[Dict[str, Any]] = []
        fscale: Optional[float] = None
        if optimizer == "mma":
            self._mma_reset_state(x)
        for it in range(max_iterations):
            compliance, dc = self._compliance_and_sensitivities(x)
            dc_f = self._apply_filter(dc, x)
            if optimizer == "mma":
                if fscale is None:
                    fscale = max(abs(float(compliance)), 1e-12)
                xnew = self._mma_update(x, dc_f, self._volumes, fscale)
            else:
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

        return self._finalize_result(
            x, history, converged, max_iterations, tolerance, optimizer)

    def _finalize_result(
        self,
        x: np.ndarray,
        history: List[Dict[str, Any]],
        converged: bool,
        max_iterations: int,
        tolerance: float,
        optimizer: str,
    ) -> Dict[str, Any]:
        """Análisis final + dict de resultado (compartido OC/MMA/ESO)."""
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
        _vm_pos = np.maximum(nodal_vm, 0.0)
        p_norm_vm = float(
            (np.mean(_vm_pos ** 8) ** (1.0 / 8.0)) if _vm_pos.size else 0.0)

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
            "max_von_mises": float(np.max(nodal_vm)) if nodal_vm.size else 0.0,
            "p_norm_von_mises": p_norm_vm,
            "penalization": float(self.penalization),
            "filter_radius": float(self.filter_radius),
            "num_load_cases": len(cases),
            "load_weights": [float(w) for _, w in cases],
            "per_case_compliance": per_case,
            # VENDORED-CHANGE: etiqueta segun el motor inyectado.
            "engine": getattr(self.fea, "engine_tag", "self-contained-simp-numpy"),
            "optimizer": optimizer,
            "volfrac_mode": self.volfrac_mode,
        }
        self.x = x
        return result

    def _element_von_mises(self, u: np.ndarray) -> np.ndarray:
        """Von Mises por elemento (espejo de core/topopt.py, Fase 6b)."""
        from core.fea import _tet_volume_and_B

        D = self.fea.D
        vm = np.zeros(self.num_elements)
        for e in range(self.num_elements):
            con = self.fea.elements[e]
            _, B = _tet_volume_and_B(self.fea.nodes[con])
            stress = D @ (B @ u[self.dof_map[e]])
            vm[e] = float(np.sqrt(
                stress[0] ** 2 + stress[1] ** 2 + stress[2] ** 2
                - stress[0] * stress[1] - stress[0] * stress[2] - stress[1] * stress[2]
                + 3.0 * (stress[3] ** 2 + stress[4] ** 2 + stress[5] ** 2)
            ))
        return vm

    def _element_von_mises_for_eso(self, x: np.ndarray) -> np.ndarray:
        cases = getattr(self, "_load_cases", None) or []
        us = self._solve_all(x)
        dom = max(range(len(us)), key=lambda i: cases[i][1]) if us else 0
        return self._element_von_mises(us[dom])

    # ------------------------------------------------------------------ #
    # ESO hard-kill (Fase 6a, espejo de core/topopt.py).
    # ------------------------------------------------------------------ #
    def _eso_optimize(
        self,
        max_iterations: int = 50,
        tolerance: float = 0.01,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        evolutionary_rate: float = 0.02,
        eso_criterion: str = "compliance",
    ) -> Dict[str, Any]:
        if not 0.0 < float(evolutionary_rate) < 1.0:
            raise TopOptError(
                f"evolutionary_rate={evolutionary_rate!r} fuera de rango (0, 1)."
            )
        if eso_criterion not in ("compliance", "stress"):
            raise TopOptError(
                f"eso_criterion={eso_criterion!r} no soportado (usar 'compliance' o 'stress')."
            )
        er = float(evolutionary_rate)
        xmin = self.rho_min
        active = self._active
        preserved = self._preserved if self._preserved is not None else \
            np.zeros(self.num_elements, dtype=bool)
        x = np.ones(self.num_elements)
        if self._void is not None:
            x[self._void] = xmin
        x[preserved] = 1.0
        target_vol = float(self._target_active_volume())
        alpha_prev: Optional[np.ndarray] = None
        history: List[Dict[str, Any]] = []
        converged = False
        for it in range(max_iterations):
            compliance, dc = self._compliance_and_sensitivities(x)
            if eso_criterion == "stress":
                alpha = self._apply_filter(self._element_von_mises_for_eso(x), x)
            else:
                alpha = self._apply_filter(-dc, x)
            if alpha_prev is not None:
                alpha = 0.5 * (alpha + alpha_prev)
            alpha_prev = alpha
            vol_now = float(np.dot(x[active], self._volumes[active]))
            solid = active & (~preserved) & (x > 0.5)
            removed_vol = 0.0
            n_removed = 0
            if vol_now > target_vol and np.any(solid):
                order = np.argsort(alpha[solid], kind="stable")
                solid_idx = np.nonzero(solid)[0][order]
                quota = max(int(np.ceil(er * solid_idx.shape[0])), 1)
                xnew = np.copy(x)
                for e in solid_idx[:quota]:
                    if vol_now - removed_vol - self._volumes[e] < target_vol:
                        break
                    xnew[e] = xmin
                    removed_vol += float(self._volumes[e])
                    n_removed += 1
            else:
                xnew = np.copy(x)
            change = float(n_removed / max(int(np.sum(active)), 1))
            vol_frac = float(np.dot(xnew[active], self._volumes[active]) / max(self._vol0_free, 1e-12))
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
            if vol_frac <= float(self.volfrac) + 1e-12 and len(history) >= 10:
                last = np.array([h["compliance"] for h in history[-10:]])
                denom = max(float(np.sum(np.abs(last[5:]))), 1e-12)
                if abs(float(np.sum(last[5:]) - np.sum(last[:5]))) / denom <= tolerance:
                    converged = True
                    break
            if n_removed == 0:
                converged = True
                break
        return self._finalize_result(
            x, history, converged, max_iterations, tolerance, "eso")

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
