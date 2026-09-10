"""Codigo vendorizado (copiado) desde la app predecesora, NO modificar el original.

Origen: ``Topologia_Optimizada/core/topopt.py`` (SIMPSolver + run_topology_optimization).
La predecesora queda intacta: este paquete vive en la app actual y es el unico
lugar donde se permite evolucionar el nucleo SIMP (p. ej. inyeccion del solver
FEA para Kratos-in-the-loop).

Diferencias frente al original (documentadas, minimas):
- ``SIMPSolver.__init__`` acepta ``fea_solver``: objeto con la interfaz usada
  por el loop (``num_dofs/num_nodes/num_elements/D/elements/nodes``,
  ``apply_bc_and_solve(F, fixed, densities)``, ``element_stiffness(e)``).
  Si es None se usa el FEASolver local -> comportamiento identico al original.
- ``engine`` del resultado sale del solver (``engine_tag``) cuando existe.
"""
