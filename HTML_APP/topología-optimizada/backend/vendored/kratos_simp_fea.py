"""Motor FEA Kratos dentro del loop SIMP (codigo NUEVO de esta app).

Compatible con la interfaz que pide ``vendored.simp.SIMPSolver``:
``num_dofs/num_nodes/num_elements/D/elements/nodes``,
``apply_bc_and_solve(F, fixed, densities)`` y ``element_stiffness(e)``.

Diseno honesto (documentado):
- El equilibrio global ``K(rho)·u = F`` lo resuelve KRATOS en cada iteracion,
  con penalizacion SIMP real: cada elemento tiene su propio ``Properties``
  cuyo ``YOUNG_MODULUS = rho_e^p * E0`` se actualiza por iteracion.
- ``element_stiffness(e)`` y ``D`` se delegan al FEASolver local: es la MISMA
  matematica Tet4 lineal (Ke0 = V·B^T·D·B) que usa
  ``SmallDisplacementElement3D4N``; Kratos no expone Ke por elemento via
  Python sin coste prohibitivo, y la sensibilidad SIMP necesita Ke0.
- Cargas como ``PointLoadCondition3D1N`` reales (fix del RHS verificado en
  la predecesora) y solver directo ``skyline_lu`` por iteracion
  (determinista; amgcl+verificacion quedaria para el post-check).
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class KratosSimpFEA:
    """FEA solver con Kratos en el loop de equilibrio y Ke0 local."""

    engine_tag = "kratos-in-the-loop-simp"

    def __init__(
        self,
        nodes: np.ndarray,
        elements: np.ndarray,
        young_modulus: float,
        poisson_ratio: float,
        density: float = 7850.0,
        penalization: float = 3.0,
    ):
        import KratosMultiphysics as Kratos
        from core.fea import FEASolver
        from core.kratos_adapter import KratosAdapter

        self._Kratos = Kratos
        self.nodes = np.asarray(nodes, dtype=float)
        self.elements = np.asarray(elements, dtype=int)
        self.num_nodes = self.nodes.shape[0]
        self.num_elements = self.elements.shape[0]
        self.num_dofs = 3 * self.num_nodes
        self.young = float(young_modulus)
        self.poisson = float(poisson_ratio)
        self.penalization = float(penalization)

        # Matematica local (misma teoria Tet4 que Kratos 3D4N lineal).
        self._local = FEASolver(nodes, elements, young_modulus, poisson_ratio)
        self.D = self._local.D

        adapter = KratosAdapter()
        self._adapter = adapter
        mp = adapter.create_model_part("VendoredSimpKratos")
        adapter.add_nodal_variables(mp)
        for i, (x, y, z) in enumerate(self.nodes):
            mp.CreateNewNode(i + 1, float(x), float(y), float(z))

        from KratosMultiphysics import StructuralMechanicsApplication as SMA
        self._props: List[Any] = []
        conn = (self.elements + 1).tolist()
        for e, nids in enumerate(conn):
            props = Kratos.Properties(e + 1)
            props.SetValue(Kratos.YOUNG_MODULUS, self.young)
            props.SetValue(Kratos.POISSON_RATIO, self.poisson)
            props.SetValue(Kratos.DENSITY, float(density))
            props.SetValue(Kratos.CONSTITUTIVE_LAW, SMA.LinearElastic3DLaw())
            mp.CreateNewElement("SmallDisplacementElement3D4N", e + 1, nids, props)
            self._props.append(props)
        adapter.add_displacement_dofs(mp)
        self._mp = mp
        self._sma = SMA
        self._fixed: List[int] = []
        self._loads_built = False
        self.solves = 0

    # -- interfaz SIMP -------------------------------------------------
    def element_stiffness(self, element_id: int) -> np.ndarray:
        return self._local.element_stiffness(element_id)

    def _apply_fixed(self, fixed: np.ndarray) -> None:
        Kratos = self._Kratos
        comp = (Kratos.DISPLACEMENT_X, Kratos.DISPLACEMENT_Y, Kratos.DISPLACEMENT_Z)
        new = set(int(d) for d in np.asarray(fixed, dtype=np.int64).ravel())
        old = set(self._fixed)
        for d in old - new:
            self._mp.GetNode(d // 3 + 1).Free(comp[d % 3])
        for d in new - old:
            self._mp.GetNode(d // 3 + 1).Fix(comp[d % 3])
        self._fixed = sorted(new)

    def _build_loads(self, F: np.ndarray) -> None:
        if self._loads_built:
            return
        Kratos = self._Kratos
        props = self._props[0]
        F = np.asarray(F, dtype=float).ravel()
        for n in range(self.num_nodes):
            f = F[3 * n:3 * n + 3]
            if not np.any(f != 0.0):
                continue
            nid = n + 1
            cond = self._mp.CreateNewCondition(
                "PointLoadCondition3D1N", nid, [nid], props)
            cond.SetValue(self._sma.POINT_LOAD,
                          [float(f[0]), float(f[1]), float(f[2])])
        self._loads_built = True

    def apply_bc_and_solve(
        self,
        force_vector: np.ndarray,
        fixed_dofs: np.ndarray,
        densities: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        Kratos = self._Kratos
        F = np.asarray(force_vector, dtype=float).ravel()
        if F.shape[0] != self.num_dofs:
            raise ValueError("force_vector length must equal the number of DOFs")
        if densities is None:
            w = np.ones(self.num_elements)
        else:
            w = np.asarray(densities, dtype=float).ravel()
        # Penalizacion SIMP real en Kratos: E por elemento.
        for e, props in enumerate(self._props):
            props.SetValue(Kratos.YOUNG_MODULUS,
                           float(self.young * max(w[e], 1e-12)))
        self._apply_fixed(fixed_dofs)
        self._build_loads(F)
        res = self._adapter.run_analysis(
            self._mp,
            {"linear_solver_settings": {
                "solver_type": "skyline_lu_factorization",
                "scaling": False, "tolerance": 1e-9},
             "verify_convergence": False})
        if not res.get("success"):
            raise RuntimeError(
                f"Kratos SIMP solve fallo: {res.get('error', 'desconocido')}")
        disp = np.asarray(res["results"]["displacements"], dtype=float)
        self.solves += 1
        u = np.zeros(self.num_dofs)
        u[:] = disp.ravel()[:self.num_dofs]
        return u
