"""Self-contained linear elastic finite element (FEA) solver.

Implements a 3D 4-node tetrahedral (Tet4) linear static solver using only
NumPy and SciPy. It is the standalone FEA engine of the application: it does
NOT depend on Kratos, Onshape, or any external CAD/FEM platform, in accordance
with the project's architecture.

Pipeline
--------
    nodes      (N x 3) node coordinates
    elements   (M x 4) Tet4 connectivity
    young, nu  material constants
    free dofs  (derived from fixed constraints)
    fixed dofs (constraints)
    forces     assembled global load vector
        |
        v
    assemble K  ->  K_ff u_f = F_f  ->  u  ->  element stresses / compliance
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

logger = logging.getLogger(__name__)


class FEAError(Exception):
    """Raised when the FEA solver cannot produce a valid result."""


def _tet_volume_and_B(
    coords: np.ndarray,
) -> Tuple[float, np.ndarray]:
    """Compute the volume and the B matrix of a single 4-node tetrahedron.

    Args:
        coords: (4, 3) array with the four tetrahedron vertices.

    Returns:
        (volume, B) where B is the 6x12 strain-displacement matrix. The volume
        is positive for a correctly oriented (right-handed) tetrahedron.
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
    det = np.linalg.det(X)
    # The physical volume is always positive. A negative determinant simply means
    # the finite-element node ordering is not right-handed; the stiffness must
    # use the absolute volume so energy stays positive for any valid node
    # ordering (some meshers emit inconsistently oriented tetrahedra).
    volume = abs(det) / 6.0
    if volume < 1e-15:
        raise FEAError("Degenerate (zero-volume) tetrahedron encountered")

    # Shape functions N_i(x,y,z) = a_i + b_i x + c_i y + d_i z.
    # The rows of the inverse of X give (a_i, b_i, c_i, d_i) for node i:
    #   [ a1 a2 a3 a4 ]      -1
    #   [ b1 b2 b3 b4 ]  =  X
    #   [ c1 c2 c3 c4 ]
    #   [ d1 d2 d3 d4 ]
    # where b_i = dN_i/dx, c_i = dN_i/dy, d_i = dN_i/dz.
    invX = np.linalg.inv(X)
    b = invX[1, :]  # dN_i/dx, i = 1..4
    c = invX[2, :]  # dN_i/dy
    d = invX[3, :]  # dN_i/dz

    B = np.zeros((6, 12))
    # epsilon_xx
    B[0, 0::3] = b
    # epsilon_yy
    B[1, 1::3] = c
    # epsilon_zz
    B[2, 2::3] = d
    # gamma_xy = du/dy + dv/dx
    B[3, 0::3] = c
    B[3, 1::3] = b
    # gamma_yz = dv/dz + dw/dy
    B[4, 1::3] = d
    B[4, 2::3] = c
    # gamma_xz = du/dz + dw/dx
    B[5, 0::3] = d
    B[5, 2::3] = b

    return volume, B


def _build_constitutive(young: float, poisson: float) -> np.ndarray:
    """Isotropic 3D linear elastic constitutive matrix D (6x6)."""
    E = float(young)
    nu = float(poisson)
    lam = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    mu = E / (2.0 * (1.0 + nu))
    G = mu
    D = np.zeros((6, 6))
    D[0, 0] = D[1, 1] = D[2, 2] = lam + 2.0 * mu
    D[0, 1] = D[0, 2] = D[1, 0] = D[1, 2] = D[2, 0] = D[2, 1] = lam
    D[3, 3] = G
    D[4, 4] = G
    D[5, 5] = G
    return D


class FEASolver:
    """Solve a 3D Tet4 linear static problem K·u = F."""

    #: Element count above which the local direct solver is expected to
    #: struggle (fill-in) and the optional Kratos backend should be suggested.
    KRATOS_SUGGEST_MIN_ELEMENTS = 50_000
    #: Solve time (s) above which Kratos should be suggested instead.
    KRATOS_SUGGEST_MIN_SECONDS = 30.0

    def __init__(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        young_modulus: float,
        poisson_ratio: float,
        linear_solver: str = "direct",
        cg_tol: float = 1e-8,
        cg_maxiter: Optional[int] = None,
    ):
        if nodes.ndim != 2 or nodes.shape[1] != 3:
            raise FEAError("nodes must be an (N, 3) array")
        if elements.ndim != 2 or elements.shape[1] != 4:
            raise FEAError("elements must be an (M, 4) array")
        if elements.size and elements.min() < 0:
            raise FEAError("elements must use 0-based node indices")
        if not (nodes.shape[0] > 0 and elements.shape[0] > 0):
            raise FEAError("empty mesh")

        if linear_solver not in ("direct", "cg"):
            raise FEAError(f"linear_solver must be 'direct' or 'cg', got {linear_solver!r}")

        self.nodes = np.asarray(nodes, dtype=float)
        self.elements = np.asarray(elements, dtype=int)
        self.num_nodes = self.nodes.shape[0]
        self.num_elements = self.elements.shape[0]
        self.num_dofs = 3 * self.num_nodes
        self.young = float(young_modulus)
        self.poisson = float(poisson_ratio)
        self.D = _build_constitutive(self.young, self.poisson)
        self._K = None
        # Linear solver selection ("direct" default = spsolve; "cg" = conjugate
        # gradients with fallback to direct on non-convergence). Diagnostics of
        # the last solve are exposed via linear_solver_used / cg_iterations /
        # solver_fallback.
        self.linear_solver = linear_solver
        self.cg_tol = float(cg_tol)
        self.cg_maxiter = cg_maxiter
        self.linear_solver_used = "direct"
        self.cg_iterations = 0
        self.solver_fallback = False
        # Cache of per-element base stiffness matrices (ke0 = V * B^T D B).
        # SIMP reassembles K every iteration with new densities; caching ke0
        # avoids recomputing the (expensive) strain-displacement B matrices.
        self._ke0: Optional[np.ndarray] = None

    # ------------------------------------------------------------------ #
    # Element stiffness matrix computation
    # ------------------------------------------------------------------ #
    def element_stiffness(self, element_id: int) -> np.ndarray:
        """Compute the (12x12) stiffness matrix of a single element.

        Returns the FULL 12x12 local matrix (uncondensed, with all 12 dofs) so
        it can be scaled by density (SIMP: ke = rho**p * Ke0).
        """
        con = self.elements[element_id]
        coords = self.nodes[con]
        vol, B = _tet_volume_and_B(coords)
        ke = float(vol) * (B.T @ self.D @ B)
        return ke

    def _base_stiffnesses(self) -> np.ndarray:
        """Return (num_elements, 12, 12) base stiffness matrices, cached."""
        if self._ke0 is None:
            ke0 = np.empty((self.num_elements, 12, 12))
            for e in range(self.num_elements):
                ke0[e] = self.element_stiffness(e)
            self._ke0 = ke0
        return self._ke0

    # ------------------------------------------------------------------ #
    # Global assembly
    # ------------------------------------------------------------------ #
    def assemble_global_stiffness(self, densities: Optional[np.ndarray] = None) -> sp.csc_matrix:
        """Assemble the global sparse stiffness matrix.

        Args:
            densities: Optional per-element density weighting. If provided the
                element stiffness is scaled as ``ke_total = rho**p_unused * ke``
                (this is the SIMP hook; the caller passes already-wanted weights).

        Returns:
            Sparse (num_dofs x num_dofs) K matrix in CSC format.
        """
        n = self.num_dofs
        if densities is None:
            weights = np.ones(self.num_elements)
        else:
            weights = np.asarray(densities, dtype=float).ravel()
            if weights.shape[0] != self.num_elements:
                raise FEAError("densities length must equal the number of elements")

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
        self._dof_map = dof_map

        ii = np.zeros((self.num_elements, 12, 12), dtype=np.int64)
        jj = np.zeros((self.num_elements, 12, 12), dtype=np.int64)
        data = np.zeros((self.num_elements, 12, 12))
        ke0 = self._base_stiffnesses()
        for e in range(self.num_elements):
            data[e] = ke0[e] * weights[e]
            dm = dof_map[e]
            ii[e] = dm[:, None]
            jj[e] = dm[None, :]

        I = ii.ravel()
        J = jj.ravel()
        V = data.ravel()
        K = sp.csc_matrix((V, (I, J)), shape=(n, n))
        # Symmetrize to remove tiny numerical asymmetry
        K = (K + K.T) * 0.5
        K.sort_indices()
        self._K = K
        return K

    def assemble_global_mass(self, density: float) -> sp.csc_matrix:
        """Assemble the global lumped mass matrix for Tet4 elements.

        Lumped (diagonal) mass: each element contributes ``rho * V / 4`` to
        each of its 4 nodes, replicated on the 3 translational DOFs of the
        node. The result is strictly positive diagonal (hence SPD), which
        keeps the generalized eigenproblem ``K*phi = w^2*M*phi`` well posed.

        Args:
            density: Material mass density (kg/m^3). Must be > 0.

        Returns:
            Sparse (num_dofs x num_dofs) diagonal M matrix in CSC format.
        """
        rho = float(density)
        if not rho > 0:
            raise FEAError(f"density must be > 0 for mass assembly, got {density!r}")
        nodal_mass = np.zeros(self.num_nodes)
        for e in range(self.num_elements):
            con = self.elements[e]
            coords = self.nodes[con]
            vol, _ = _tet_volume_and_B(coords)
            nodal_mass[con] += rho * float(vol) / 4.0
        if np.any(nodal_mass <= 0.0):
            raise FEAError("lumped mass assembly produced non-positive nodal masses")
        diag = np.repeat(nodal_mass, 3)
        return sp.csc_matrix(sp.diags(diag, format="csc"))

    def apply_bc_and_solve(
        self,
        force_vector: np.ndarray,
        fixed_dofs: np.ndarray,
        densities: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Solve K·u = F under prescribed fixed DOFs.

        Args:
            force_vector: Global load vector of length num_dofs.
            fixed_dofs: Sorted array of DOF indices set to zero.
            densities: Optional per-element weights (SIMP).

        Returns:
            Displacement vector u of length num_dofs.
        """
        # Always reassemble with the current densities: densities are the SIMP
        # design state and change every iteration, so a cached K would be stale.
        if densities is None and self._K is not None:
            K = self._K
        else:
            K = self.assemble_global_stiffness(densities)

        F = np.asarray(force_vector, dtype=float).ravel()
        if F.shape[0] != self.num_dofs:
            raise FEAError("force_vector length must equal the number of DOFs")

        fixed = np.asarray(fixed_dofs, dtype=np.int64)
        if fixed.size:
            all_dofs = np.arange(self.num_dofs)
            free = np.setdiff1d(all_dofs, fixed)
        else:
            free = np.arange(self.num_dofs)

        if len(free) == 0:
            raise FEAError("no free DOFs remain after applying constraints")

        Kff = K[np.ix_(free, free)]
        Ff = F[free]
        u_free = self._solve_linear(Kff, Ff)

        u = np.zeros(self.num_dofs)
        u[free] = u_free
        return u

    def _solve_linear(self, Kff, Ff) -> np.ndarray:
        """Solve the free-DOF system with the configured linear solver.

        ``"direct"`` (default) uses ``spsolve`` — unchanged legacy behaviour.
        ``"cg"`` uses conjugate gradients; on non-convergence it falls back
        to ``spsolve`` with an explicit warning (never a silent wrong answer).
        """
        import logging
        logger = logging.getLogger(__name__)
        if self.linear_solver == "cg":
            iters = [0]

            def _cb(_):
                iters[0] += 1

            u_free, info = spla.cg(
                Kff, Ff, rtol=self.cg_tol, maxiter=self.cg_maxiter,
                callback=_cb,
            )
            self.cg_iterations = iters[0]
            if info == 0:
                self.linear_solver_used = "cg"
                self.solver_fallback = False
                return np.asarray(u_free)
            logger.warning(
                "CG linear solver did not converge (info=%s, %d iters); "
                "falling back to direct spsolve explicitly.",
                info, iters[0],
            )
            self.solver_fallback = True
        self.linear_solver_used = "direct"
        return spla.spsolve(Kff, Ff)

    # ------------------------------------------------------------------ #
    # Post-processing
    # ------------------------------------------------------------------ #
    def compute_element_results(
        self,
        u: np.ndarray,
        densities: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Compute per-element strain energy, stress and von Mises.

        Args:
            u: Full displacement vector.
            densities: optional per-element weights (not used for stress but
                returned for traceability).

        Returns:
            Dict with element arrays (strain_energy, sigma_vm) and nodal field.
        """
        element_strain_energy = np.zeros(self.num_elements)
        sigma_vm = np.zeros(self.num_elements)
        el_vol = np.zeros(self.num_elements)
        # accumulated nodal von Mises (for scalar field output)
        nodal_vm_accum = np.zeros(self.num_nodes)
        nodal_vm_count = np.zeros(self.num_nodes)
        ke0 = self._base_stiffnesses()

        for e in range(self.num_elements):
            con = self.elements[e]
            coords = self.nodes[con]
            vol, B = _tet_volume_and_B(coords)
            el_vol[e] = vol
            # Element displacement must use the SAME per-node (x,y,z) dof order
            # as the assembly's dof_map, otherwise energy and stress are corrupt.
            ue = u[np.concatenate([[n * 3, n * 3 + 1, n * 3 + 2] for n in con])]
            strain = B @ ue
            stress = self.D @ strain
            energy = 0.5 * ue @ (ke0[e] @ ue)
            element_strain_energy[e] = float(energy)
            sv = np.sqrt(
                stress[0] ** 2 + stress[1] ** 2 + stress[2] ** 2
                - stress[0] * stress[1]
                - stress[0] * stress[2]
                - stress[1] * stress[2]
                + 3.0 * (stress[3] ** 2 + stress[4] ** 2 + stress[5] ** 2)
            )
            sigma_vm[e] = float(sv)
            for k, node in enumerate(con):
                nodal_vm_accum[node] += float(sv)
                nodal_vm_count[node] += 1.0

        nodal_vm = np.divide(
            nodal_vm_accum, nodal_vm_count, out=np.zeros_like(nodal_vm_accum), where=nodal_vm_count > 0
        )

        return {
            "element_strain_energy": element_strain_energy,
            "element_von_mises": sigma_vm,
            "element_volume": el_vol,
            "nodal_von_mises": nodal_vm,
            "total_strain_energy": float(element_strain_energy.sum()),
            "compliance": float(2.0 * element_strain_energy.sum()),
        }


def solve_modal(
    nodes: np.ndarray,
    elements: np.ndarray,
    young_modulus: float,
    poisson_ratio: float,
    density: float,
    fixed_dofs: List[int],
    mode_count: int = 5,
    frequency_min: Optional[float] = None,
    frequency_max: Optional[float] = None,
) -> Dict[str, Any]:
    """Solve the undamped free-vibration eigenproblem K*phi = w^2*M*phi.

    Assembles the Tet4 stiffness ``K`` (via :meth:`FEASolver.element_stiffness`)
    and the lumped mass ``M`` (via :meth:`FEASolver.assemble_global_mass`),
    restricts both to the free DOFs derived from ``fixed_dofs`` (same
    convention as :meth:`FEASolver.apply_bc_and_solve`), and extracts the
    ``mode_count`` lowest modes with ``scipy.sparse.linalg.eigsh``
    (``which='SM'``).

    Args:
        nodes: (N,3) node coordinates.
        elements: (M,4) Tet4 connectivity.
        young_modulus, poisson_ratio: elastic constants.
        density: mass density (kg/m^3), must be > 0.
        fixed_dofs: global DOF indices held at zero. Must be non-empty:
            without constraints the stiffness matrix is singular
            (rigid-body modes) and an :class:`FEAError` is raised explicitly.
        mode_count: number of modes to extract, must be >= 1 and < #free DOFs.
        frequency_min/max: optional window of interest (Hz). Modes outside
            the window are filtered out of ``frequencies``/``mode_shapes``
            and reported explicitly in ``warnings`` (never dropped silently).

    Returns:
        Dict with ``frequencies`` (Hz, ascending), ``mode_shapes`` (full-DOF
        vectors, M-orthonormal, ascending by frequency), ``angular_frequencies``
        (rad/s), ``eigenvalues`` (w^2), ``warnings``, ``num_modes``,
        ``num_free_dofs`` and ``engine``.
    """
    if mode_count is None or int(mode_count) < 1:
        raise FEAError(f"mode_count must be >= 1, got {mode_count!r}")
    mode_count = int(mode_count)
    if frequency_min is not None and frequency_min < 0:
        raise FEAError(f"frequency_min must be >= 0, got {frequency_min!r}")
    if frequency_max is not None and frequency_max < 0:
        raise FEAError(f"frequency_max must be >= 0, got {frequency_max!r}")
    if (frequency_min is not None and frequency_max is not None
            and frequency_min >= frequency_max):
        raise FEAError("frequency_min must be < frequency_max")

    fixed = np.sort(np.unique(np.asarray(list(fixed_dofs), dtype=np.int64)))
    if fixed.size == 0:
        raise FEAError(
            "Modal analysis requires at least one fixed DOF (constraint) to "
            "eliminate rigid-body modes: K is singular without constraints."
        )

    solver = FEASolver(nodes, elements, young_modulus, poisson_ratio)
    if np.any(fixed < 0) or np.any(fixed >= solver.num_dofs):
        raise FEAError("fixed_dofs contains DOF indices out of range")
    K = solver.assemble_global_stiffness()
    M = solver.assemble_global_mass(density)

    all_dofs = np.arange(solver.num_dofs)
    free = np.setdiff1d(all_dofs, fixed)
    if free.size == 0:
        raise FEAError("no free DOFs remain after applying constraints")
    if mode_count >= free.size:
        raise FEAError(
            f"mode_count ({mode_count}) must be < number of free DOFs "
            f"({free.size}): extract fewer modes or release constraints."
        )

    Kff = K[np.ix_(free, free)].tocsc()
    Mff = M[np.ix_(free, free)].tocsc()

    try:
        eigenvals, eigenvecs = spla.eigsh(Kff, k=mode_count, M=Mff, which="SM")
    except Exception as exc:
        raise FEAError(f"eigensolver failed (eigsh, which='SM'): {exc}") from exc

    order = np.argsort(eigenvals)
    eigenvals = np.asarray(eigenvals[order], dtype=float)
    eigenvecs = np.asarray(eigenvecs[:, order])

    warnings: List[str] = []
    nonpositive = eigenvals <= 0.0
    if np.any(nonpositive):
        warnings.append(
            f"{int(np.sum(nonpositive))} modo(s) con autovalor <= 0 "
            "(posible mecanismo o constraint insuficiente); se fijan a 0 Hz."
        )
        eigenvals = np.clip(eigenvals, 0.0, None)

    omegas = np.sqrt(eigenvals)
    freqs = omegas / (2.0 * np.pi)

    # Expand eigenvectors to full-DOF mode shapes (zeros at fixed DOFs) and
    # enforce M-orthonormality explicitly (phi^T M phi = 1).
    Mdiag = np.asarray(M.diagonal(), dtype=float)
    mode_shapes = []
    for i in range(mode_count):
        phi = np.zeros(solver.num_dofs)
        phi[free] = eigenvecs[:, i]
        norm = float(np.sqrt(np.sum(Mdiag * phi * phi)))
        if norm <= 0.0:
            raise FEAError(f"mode shape {i} has zero mass norm")
        phi /= norm
        mode_shapes.append(phi)

    kept = [True] * mode_count
    for i, f in enumerate(freqs):
        if frequency_min is not None and f < frequency_min:
            kept[i] = False
            warnings.append(
                f"Modo {i + 1} ({float(f):.3f} Hz) bajo frequency_min "
                f"({frequency_min} Hz): excluido del resultado."
            )
        elif frequency_max is not None and f > frequency_max:
            kept[i] = False
            warnings.append(
                f"Modo {i + 1} ({float(f):.3f} Hz) sobre frequency_max "
                f"({frequency_max} Hz): excluido del resultado."
            )

    kept_idx = [i for i, k in enumerate(kept) if k]
    return {
        "success": True,
        "status": "completed",
        "frequencies": [float(freqs[i]) for i in kept_idx],
        "angular_frequencies": [float(omegas[i]) for i in kept_idx],
        "eigenvalues": [float(eigenvals[i]) for i in kept_idx],
        "mode_shapes": [mode_shapes[i].tolist() for i in kept_idx],
        "num_modes": len(kept_idx),
        "num_modes_computed": mode_count,
        "num_free_dofs": int(free.size),
        "fixed_dofs": fixed.tolist(),
        "warnings": warnings,
        "engine": "self-contained-numpy-tet4-modal",
    }


def kratos_suggestion(num_elements: int, solve_seconds: Optional[float] = None) -> Optional[str]:
    """Return a Kratos-backend suggestion message, or None if local is fine.

    Numeric migration threshold (no longer subjective "large meshes"): above
    ``KRATOS_SUGGEST_MIN_ELEMENTS`` elements or ``KRATOS_SUGGEST_MIN_SECONDS``
    seconds of local solve, the optional ``backend="kratos"`` should be
    evaluated.
    """
    if num_elements >= FEASolver.KRATOS_SUGGEST_MIN_ELEMENTS:
        return (f"Malla grande ({num_elements} elementos ≥ "
                f"{FEASolver.KRATOS_SUGGEST_MIN_ELEMENTS}): evalúe backend='kratos'.")
    if solve_seconds is not None and solve_seconds >= FEASolver.KRATOS_SUGGEST_MIN_SECONDS:
        return (f"Solve local lento ({solve_seconds:.1f}s ≥ "
                f"{FEASolver.KRATOS_SUGGEST_MIN_SECONDS}s): evalúe backend='kratos'.")
    return None


def solve_fea(
    nodes: np.ndarray,
    elements: np.ndarray,
    young_modulus: float,
    poisson_ratio: float,
    forces_dofs: List[Tuple[int, float]],
    fixed_dofs: List[int],
    element_densities: Optional[np.ndarray] = None,
    linear_solver: str = "direct",
    cg_tol: float = 1e-8,
    cg_maxiter: Optional[int] = None,
) -> Dict[str, Any]:
    """Convenience high-level FEA entry point.

    Args:
        nodes: (N,3) node coordinates.
        elements: (M,4) Tet4 connectivity.
        young_modulus, poisson_ratio: material constants.
        forces_dofs: list of (dof_index, value) global force contributions.
        fixed_dofs: list of global DOF indices to fix (set to zero).
        element_densities: optional per-element SIMP weights.
        linear_solver: "direct" (default, spsolve) or "cg" (conjugate
            gradients with explicit fallback to direct on non-convergence).

    Returns:
        A dict compatible with the application result model.
    """
    import time
    t0 = time.perf_counter()
    solver = FEASolver(nodes, elements, young_modulus, poisson_ratio,
                       linear_solver=linear_solver, cg_tol=cg_tol,
                       cg_maxiter=cg_maxiter)
    K = solver.assemble_global_stiffness(element_densities)
    F = np.zeros(solver.num_dofs)
    for dof, val in forces_dofs:
        F[dof] += val
    fixed = np.sort(np.asarray(fixed_dofs, dtype=np.int64))
    u = solver.apply_bc_and_solve(F, fixed, element_densities)
    results = solver.compute_element_results(u, element_densities)

    # nodal displacements as 3-vector
    displacements = u.reshape(-1, 3).tolist()

    max_disp = float(np.max(np.abs(u))) if u.size else 0.0
    solve_seconds = time.perf_counter() - t0
    return {
        "success": True,
        "status": "completed",
        "displacements": displacements,
        "max_displacement": max_disp,
        "compliance": results["compliance"],
        "total_strain_energy": results["total_strain_energy"],
        "element_strain_energy": results["element_strain_energy"].tolist(),
        "element_von_mises": results["element_von_mises"].tolist(),
        "nodal_von_mises": results["nodal_von_mises"].tolist(),
        "num_nodes": solver.num_nodes,
        "num_elements": solver.num_elements,
        "fixed_dofs": fixed.tolist(),
        "engine": "self-contained-numpy-tet4",
        "linear_solver": solver.linear_solver_used,
        "cg_iterations": solver.cg_iterations,
        "solver_fallback": solver.solver_fallback,
        "solve_seconds": solve_seconds,
        "kratos_suggestion": kratos_suggestion(solver.num_elements, solve_seconds),
    }
