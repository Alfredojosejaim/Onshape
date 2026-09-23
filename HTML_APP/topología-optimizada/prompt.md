vendored/simp.py no conoce volfrac_mode (solo ruta estructural).
Conversión de densidad mm solo aplicada a cae_studies.solve_modal; falta revisar otros consumidores.
topo_problem.py sigue rechazando VolfracMode.TOTAL_VOLUME.
Guard BC no cubre "carga dentro de región preservada".