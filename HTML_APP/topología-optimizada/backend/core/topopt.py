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


def _tet_shape_gradients(coords: np.ndarray) -> np.ndarray:
    """3x4 gradientes de las funciones de forma de un tet lineal.

    Misma matriz X que :func:`core.fea._tet_volume_and_B`: las filas 1..3
    de ``inv(X)`` son (dN_i/dx, dN_i/dy, dN_i/dz) por nodo-columna.
    """
    X = np.array(
        [
            [1, coords[0, 0], coords[0, 1], coords[0, 2]],
            [1, coords[1, 0], coords[1, 1], coords[1, 2]],
            [1, coords[2, 0], coords[2, 1], coords[2, 2]],
            [1, coords[3, 0], coords[3, 1], coords[3, 2]],
        ],
        dtype=float,
    )
    try:
        invX = np.linalg.inv(X)
    except np.linalg.LinAlgError:
        raise TopOptError("Tetraedro degenerado al calcular gradientes de forma.")
    return invX[1:4, :]


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
        self._load_cases: Optional[List[Tuple[np.ndarray, float]]] = None
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
        self._load_cases = [(f, 1.0)]

    def set_loads(
        self,
        forces: List[np.ndarray],
        weights: Optional[List[float]] = None,
    ) -> None:
        """MULTICARGA: c(rho) = sum_i w_i·u_i^T·K·u_i (pesos normalizados)."""
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
        self._forces = sum(fv * wi for fv, wi in self._load_cases)

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

    # ------------------------------------------------------------------ #
    # Manufacturing constraint: planos de simetría (Fase 6c)
    # ------------------------------------------------------------------ #
    def set_symmetry_planes(self, planes) -> None:
        """Fuerza simetría del diseño respecto a planos coordenados.

        Args:
            planes: iterable de ``(eje, valor)`` donde eje es 0/1/2 o
                'x'/'y'/'z' y valor la coordenada del plano. ``None`` o
                vacío desactiva la simetría.

        Cada elemento se aparea con el más cercano a su reflejado; sin
        contraparte (malla asimétrica) conserva su valor (explícito en
        ``symmetry_pairs``). OC/MMA promedian pares por iteración; ESO
        promedia sensibilidades y propaga remociones al espejo.
        """
        if not planes:
            self._sym_pairs = None
            return
        parsed = []
        for p in planes:
            try:
                ax, val = p
            except (TypeError, ValueError):
                raise TopOptError(
                    f"plano de simetría inválido {p!r}: usar (eje, valor).")
            if isinstance(ax, str):
                ax = {"x": 0, "y": 1, "z": 2}.get(ax.lower(), -1)
            if ax not in (0, 1, 2) or not np.isfinite(float(val)):
                raise TopOptError(
                    f"plano de simetría inválido {p!r}: eje 0/1/2 o x/y/z y valor finito.")
            parsed.append((int(ax), float(val)))
        from scipy.spatial import cKDTree

        centers = np.asarray(self.element_centers, dtype=float)
        mirrored = centers.copy()
        for ax, val in parsed:
            mirrored[:, ax] = 2.0 * val - mirrored[:, ax]
        tree = cKDTree(centers)
        dist, idx = tree.query(mirrored, k=1)
        h = float(np.mean(self._volumes) ** (1.0 / 3.0)) if self.num_elements else 1.0
        pairs = np.arange(self.num_elements)
        n_paired = 0
        for i in range(self.num_elements):
            if dist[i] <= 0.25 * h:
                pairs[i] = int(idx[i])
                n_paired += 1
        self._sym_pairs = pairs
        self._sym_paired_count = int(n_paired)

    def _mirror_average(self, v: np.ndarray) -> np.ndarray:
        """Promedia cada elemento con su espejo (OC/MMA continuo)."""
        if getattr(self, "_sym_pairs", None) is None:
            return v
        return 0.5 * (np.asarray(v, dtype=float) + np.asarray(v, dtype=float)[self._sym_pairs])

    def _mirror_min(self, x: np.ndarray, xmin: float) -> np.ndarray:
        """Propaga remociones al espejo (ESO binario: la remoción gana).

        Preservados y vacíos se re-pinean después (nunca los toca)."""
        if getattr(self, "_sym_pairs", None) is None:
            return x
        out = np.asarray(x, dtype=float).copy()
        mirror = out[self._sym_pairs]
        out[(out <= 0.5 * (1.0 + xmin)) | (mirror <= 0.5 * (1.0 + xmin))] = xmin
        if self._preserved is not None:
            out[self._preserved] = 1.0
        if self._void is not None:
            out[self._void] = xmin
        return out

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
            raise TopOptError("load vector not set; call set_load()/set_loads() first")
        cases = getattr(self, "_load_cases", None)
        F = cases[0][0] if cases else self._forces
        fixed = self._fixed_dofs if self._fixed_dofs is not None else np.array([], dtype=np.int64)
        weights = np.power(x, self.penalization)
        u = self.fea.apply_bc_and_solve(F, fixed, densities=weights)
        return u

    def _solve_all(self, x: np.ndarray) -> List[np.ndarray]:
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
        # compliance = sum_i w_i * sum_e rho_e^p * u_i,e^T Ke0 u_i,e
        for (F, w), u in zip(cases, us):
            for e in range(self.num_elements):
                dm = self.dof_map[e]
                ue = u[dm]
                ke = self.fea.element_stiffness(e)
                ukeu = ue @ ke @ ue
                compliance += float(w * ukeu) * (x[e] ** self.penalization)
                dc[e] += float(w * -self.penalization * (x[e] ** (self.penalization - 1)) * ukeu)
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
    # MMA update (Fase 4 plan.md) — Method of Moving Asymptotes, Svanberg.
    # Implementación propia en numpy (Kratos 10.4 no expone optimizador
    # standalone: solo OptResponses + framework completo). Opt-in vía
    # optimize(optimizer="mma"); el default sigue siendo OC ("oc").
    # Subproblema separable con 1 restricción (volumen):
    #   min Σ p0j/(Uj-xj)+q0j/(xj-Lj)  s.t. Σ p1j/(Uj-xj)+q1j/(xj-Lj) ≤ 0,
    # resuelto en el dual (lam ≥ 0, Newton + bisección acotada).
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
        """Un paso MMA sobre el subdominio activo.

        Args:
            x: densidades actuales (n,).
            df0: gradiente del objetivo (compliance, filtrado) (n,).
            dv: gradiente de la restricción de volumen (volúmenes) (n,).
            fscale: escala del objetivo (compliance inicial) para
                condicionar el dual; > 0.
        """
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

        # --- Asíntotas móviles (adaptación por oscilación) ---
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

        # --- Bounds alfa/beta (asíntotas + move limit implícito) ---
        alfa = np.maximum(low + self._MMA_ALBEFA * (xa - low), xa_min)
        beta = np.minimum(upp - self._MMA_ALBEFA * (upp - xa), xa_max)

        # --- Coeficientes del subproblema (objetivo normalizado) ---
        ux = upp - xa
        lx = xa - low
        p0 = ux * ux * np.maximum(df0a, 0.0) + 1e-9
        q0 = lx * lx * np.maximum(-df0a, 0.0) + 1e-9
        # Restricción g(x) = V(x)/Vt - 1 ≤ 0, gradiente constante dva/Vt.
        vt = max(float(self.volfrac * self._vol0_free), 1e-12)
        dg = dva / vt
        p1 = ux * ux * np.maximum(dg, 0.0)
        q1 = lx * lx * np.maximum(-dg, 0.0)
        # Volumen actual normalizado (constante del subproblema).
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

        # --- Dual: lam ≥ 0 con holgura complementaria ---
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

        # --- Avanza el estado de asíntotas ---
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

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
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
            optimizer: "oc" (Optimality Criteria, default histórico),
                "mma" (Moving Asymptotes propio, Fase 4), "eso"
                (Evolutionary hard-kill, Fase 6a) o "level_set"
                (frontera implícita HJ, Fase 6f). Cualquier otro valor
                lanza TopOptError explícito (sin fallback silencioso a OC).
            evolutionary_rate: fracción de elementos sólidos a remover
                por iteración ESO (solo aplica a "eso").
            eso_criterion: "compliance" (energía de deformación, default) o
                "stress" (von Mises por elemento, Xie & Steven original).
                Solo aplica a "eso".
            ls_cfl: CFL del paso HJ explícito en (0, 1] (solo "level_set").
            ls_hole_period: cada cuántas iteraciones redistanciar +
                nuclear (solo "level_set").
        """
        if optimizer not in ("oc", "mma", "eso", "level_set"):
            raise TopOptError(
                f"optimizer={optimizer!r} no soportado (usar 'oc', 'mma', 'eso' o 'level_set')."
            )
        if optimizer == "eso":
            return self._eso_optimize(
                max_iterations=max_iterations,
                tolerance=tolerance,
                callback=callback,
                evolutionary_rate=evolutionary_rate,
                eso_criterion=eso_criterion,
            )
        if optimizer == "level_set":
            return self._level_set_optimize(
                max_iterations=max_iterations,
                tolerance=tolerance,
                callback=callback,
                ls_cfl=ls_cfl,
                ls_hole_period=ls_hole_period,
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
            xnew = self._mirror_average(xnew)

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

        # Final analysis with converged density field (multicarga ponderada)
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
                cc += float(ue @ ke @ ue) * weight[e]
            per_case.append({"weight": float(w), "compliance": float(cc)})
            compliance_final += float(w) * float(cc)
        dom = max(range(len(final_us)), key=lambda i: cases[i][1]) if final_us else 0
        final_u = final_us[dom]
        for e in range(self.num_elements):
            dm = self.dof_map[e]
            ue = final_u[dm]
            ke = self.fea.element_stiffness(e)
            ke_term[e] = float(ue @ ke @ ue)

        nodal_vm = self._nodal_vm(final_u)
        max_disp = float(np.max(np.abs(final_u))) if final_u.size else 0.0
        # Restricción de tensión máxima (Fase 6b): medida agregada p-norm
        # (estándar para constraint global) + máximo nodal explícito.
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
            "engine": "self-contained-simp-numpy",
            "optimizer": optimizer,
        }
        self.x = x
        return result

    # ------------------------------------------------------------------ #
    # ESO hard-kill (Fase 6a): remoción evolutiva por ranking de
    # sensibilidad (Xie & Steven). Diseño 0/1 puro: cada iteración remueve
    # una fracción ER de los elementos sólidos menos sensibles hasta
    # alcanzar volfrac; luego verifica convergencia por estabilidad del
    # compliance (criterio clásico sobre las últimas 10 iteraciones).
    # Preservados nunca se remueven; vacíos quedan en rho_min.
    # ------------------------------------------------------------------ #
    def _element_von_mises(self, u: np.ndarray) -> np.ndarray:
        """Von Mises por elemento (tetraedro = deformación constante)."""
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
        """VM por elemento del caso de carga dominante (mismo criterio que
        ``ke_term`` del finalizador: mayor peso; desempate: primero)."""
        cases = getattr(self, "_load_cases", None) or []
        us = self._solve_all(x)
        dom = max(range(len(us)), key=lambda i: cases[i][1]) if us else 0
        return self._element_von_mises(us[dom])

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
        # ESO parte del dominio lleno (solo vacíos pre-vaciados).
        x = np.ones(self.num_elements)
        if self._void is not None:
            x[self._void] = xmin
        x[preserved] = 1.0
        target_vol = float(self.volfrac * self._vol0_free)
        alpha_prev: Optional[np.ndarray] = None
        history: List[Dict[str, Any]] = []
        converged = False
        for it in range(max_iterations):
            compliance, dc = self._compliance_and_sensitivities(x)
            if eso_criterion == "stress":
                # Criterio tensional (Xie & Steven original): ranking por
                # von Mises por elemento del caso de carga dominante.
                alpha = self._apply_filter(self._element_von_mises_for_eso(x), x)
            else:
                # Sensibilidad = energía de deformación por elemento (positiva).
                alpha = self._apply_filter(-dc, x)
            if alpha_prev is not None:
                alpha = 0.5 * (alpha + alpha_prev)
            alpha_prev = alpha
            alpha = self._mirror_average(alpha)
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
            xnew = self._mirror_min(xnew, xmin)
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
            # Convergencia ESO clásica: en volumen objetivo y compliance
            # estable en las últimas 10 iteraciones. Si no se pudo remover
            # nada (objetivo alcanzado o ninguna remoción cabe sin pasarse
            # del objetivo discreto), el diseño ya no puede progresar.
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

    # ------------------------------------------------------------------ #
    # Level-Set explícito (Fase 6f): frontera implícita φ=0 advectada por
    # Hamilton-Jacobi con velocidad = sensibilidad − λ (volumen), más
    # redistancing de Sussman y nucleación topológica periódica.
    # Material: Heaviside suavizado nodal (ancho h) promediado por elemento.
    # Preservados/vacíos se re-pinean tras el mapeo (igual que OC/ESO).
    # ------------------------------------------------------------------ #
    def _level_set_optimize(
        self,
        max_iterations: int = 50,
        tolerance: float = 0.01,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        ls_cfl: float = 0.2,
        ls_hole_period: int = 5,
    ) -> Dict[str, Any]:
        if not 0.0 < float(ls_cfl) <= 1.0:
            raise TopOptError(f"ls_cfl={ls_cfl!r} fuera de rango (0, 1].")
        if int(ls_hole_period) < 1:
            raise TopOptError(f"ls_hole_period={ls_hole_period!r} debe ser >= 1.")
        from scipy.spatial import cKDTree

        vols = np.asarray(self._volumes, dtype=float)
        active = np.asarray(self._active, dtype=bool)
        if not np.any(active):
            raise TopOptError("Level-Set sin subdominio diseñable (todo preservado/vacío).")
        preserved = self._preserved if self._preserved is not None else \
            np.zeros(self.num_elements, dtype=bool)
        nodes = np.asarray(self.nodes, dtype=float)
        elements = np.asarray(self.elements, dtype=int)
        ne = self.num_elements
        nn = nodes.shape[0]
        h = float(np.mean(vols[active]) ** (1.0 / 3.0))
        h = max(h, 1e-12)
        target_vol = float(self.volfrac * self._vol0_free)
        xmin = self.rho_min

        # Operadores de gradiente por elemento + incidencia nodo->elementos.
        grads = np.zeros((ne, 3, 4))
        for e in range(ne):
            grads[e] = _tet_shape_gradients(nodes[elements[e]])
        incidence: List[List[int]] = [[] for _ in range(nn)]
        for e in range(ne):
            for a in elements[e]:
                incidence[int(a)].append(e)
        node_tree = cKDTree(nodes)
        # Espaciado nodal (la nucleación debe cubrir al menos el anillo
        # vecino: el radio en h de elemento puede quedar bajo el espaciado).
        _nn_dist, _ = node_tree.query(nodes, k=2)
        nodal_h = max(float(np.mean(_nn_dist[:, 1])), 1e-12)

        def _nodal_average(elem_vals: np.ndarray) -> np.ndarray:
            out = np.zeros(nn)
            wsum = np.zeros(nn)
            for e in range(ne):
                v = float(elem_vals[e]) * vols[e]
                for a in elements[e]:
                    out[int(a)] += v
                    wsum[int(a)] += vols[e]
            return np.divide(out, np.maximum(wsum, 1e-18))

        def _nodal_grad_norm(phi: np.ndarray) -> np.ndarray:
            g = np.zeros((nn, 3))
            wsum = np.zeros(nn)
            for e in range(ne):
                ge = grads[e] @ phi[elements[e]]
                for a in elements[e]:
                    g[int(a)] += ge * vols[e]
                    wsum[int(a)] += vols[e]
            g /= np.maximum(wsum, 1e-18)[:, None]
            return np.linalg.norm(g, axis=1)

        def _heaviside(phi: np.ndarray) -> np.ndarray:
            # Banda estrecha (0.5h): nítida como 0/1 pero derivable para HJ.
            w = 0.5 * h
            x = np.zeros(ne)
            for e in range(ne):
                pv = phi[elements[e]] / w
                hv = np.where(pv <= -1.0, 0.0,
                              np.where(pv >= 1.0, 1.0,
                                       0.5 + 0.5 * (pv + np.sin(np.pi * pv) / np.pi)))
                x[e] = float(np.mean(hv))
            x = np.maximum(x, xmin)
            x[preserved] = 1.0
            if self._void is not None:
                x[self._void] = xmin
            return x

        def _nucleate(phi: np.ndarray, se: np.ndarray, frac: float) -> int:
            xe = _heaviside(phi)
            solid = active & (~preserved) & (xe > 0.5)
            if not np.any(solid):
                return 0
            order = np.argsort(se[solid], kind="stable")
            cand = np.nonzero(solid)[0][order]
            k = max(int(np.ceil(frac * cand.shape[0])), 1)
            centers = np.asarray(self.element_centers, dtype=float)
            n = 0
            for e in cand[:k]:
                idx = node_tree.query_ball_point(centers[e], 1.5 * nodal_h)
                phi[idx] = -1.0
                n += 1
            return n

        def _redistance(phi: np.ndarray, iters: int = 3) -> np.ndarray:
            d = phi.copy()
            s = np.sign(phi)
            for _ in range(max(int(iters), 0)):
                g = _nodal_grad_norm(d)
                d = d - 0.3 * h * s * (g - 1.0)
            return d

        # Init: dominio lleno + nucleación inicial por derivada topológica.
        phi = np.full(nn, 1.0)
        x0 = _heaviside(phi)
        _, dc0 = self._compliance_and_sensitivities(x0)
        _nucleate(phi, self._apply_filter(-dc0, x0), 0.05)

        history: List[Dict[str, Any]] = []
        converged = False
        for it in range(max_iterations):
            x = _heaviside(phi)
            compliance, dc = self._compliance_and_sensitivities(x)
            se = self._apply_filter(-dc, x)
            vol = float(np.dot(x[active], vols[active]))
            # Multiplicador de volumen (control proporcional con ganancia
            # K=3: compensa el paso CFL pequeño del HJ explícito).
            # Convención dφ/dt = −V|∇φ| con φ>0 sólido: remover exige V>0
            # en baja sensibilidad → V = λ−se, con media(V) = +K·(vol−target)
            # /ΣV (sobre-volumen → φ decrece → se remueve).
            se_a = se[active]
            lam = (float(np.dot(se_a, vols[active])) + 3.0 * (vol - target_vol)) / max(float(vols[active].sum()), 1e-18)
            v_elem = np.zeros(ne)
            v_elem[active] = lam - se[active]
            v_nod = _nodal_average(v_elem)
            gnorm = _nodal_grad_norm(phi)
            vmax = float(np.max(np.abs(v_nod)))
            if vmax <= 1e-18:
                x = _heaviside(phi)
                vol_frac = float(np.dot(x[active], vols[active]) / max(self._vol0_free, 1e-12))
                history.append({"iteration": it + 1, "compliance": float(compliance),
                                "volume_fraction": vol_frac, "max_change": 0.0})
                converged = True
                break
            dt = float(ls_cfl) * h / vmax
            phi = phi - dt * v_nod * gnorm
            if (it + 1) % int(ls_hole_period) == 0:
                phi = _redistance(phi)
                if vol > target_vol:
                    _nucleate(phi, se, 0.04)
            xnew = _heaviside(phi)
            change = float(np.max(np.abs(xnew - x)))
            vol_frac = float(np.dot(xnew[active], vols[active]) / max(self._vol0_free, 1e-12))
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
            if vol_frac <= float(self.volfrac) + 1e-12 and len(history) >= 10:
                last = np.array([h["compliance"] for h in history[-10:]])
                denom = max(float(np.sum(np.abs(last[5:]))), 1e-12)
                if abs(float(np.sum(last[5:]) - np.sum(last[:5]))) / denom <= tolerance:
                    converged = True
                    break
        return self._finalize_result(
            _heaviside(phi), history, converged, max_iterations, tolerance, "level_set")

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
