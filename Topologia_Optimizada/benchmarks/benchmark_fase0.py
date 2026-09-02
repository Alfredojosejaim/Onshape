"""Fase 0 — Benchmark del pipeline FEA real (GmshTet4Mesher + Kratos).

Mide por separado el tiempo de cada etapa del pipeline real sobre las mallas de
referencia de ``benchmarks/meshes``:

  * carga de malla (.npz)
  * creación de ModelPart / variables
  * importación de malla (nodo + elemento) a Kratos
  * configuración de material + DOFs
  * aplicación de restricciones y cargas (selección geométrica)
  * setup del solver + Solve() + extracción de resultados
  * tiempo total de una corrida FEA completa

También registra el uso de memoria pico por **RSS del proceso** (Fase 3): se muestrea el
Working Set Size en un hilo en segundo plano (``benchmarks/memory.py``), que sí captura la
memoria nativa de Kratos (nodos/elementos, matrices sparse en C++) a diferencia de
``tracemalloc`` (que solo ve allocaciones Python y además ralentiza cada una).

Uso:
    python benchmarks/benchmark_fase0.py            # las 3 mallas, 1 repetición
    python benchmarks/benchmark_fase0.py --mesh medium_5k --repeats 3
    python benchmarks/benchmark_fase0.py --profile   # cProfile sobre la malla mediana

Los tiempos NO miden el mallado (Gmsh) dentro de la corrida FEA: la malla se
genera previamente con ``make_meshes.py`` y se reutiliza. De ese modo el
benchmark aísla el costo del solver real.
"""

import argparse
import importlib.util
import json
import logging
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.disable(logging.CRITICAL)

# Cono: el eje de simetría es Z, base en z≈0, extremo superior en z≈50.3 (mm).
Z_MAX = 50.272

# CONSISTENCIA DE UNIDADES (verificado en Fase 1):
# - La geometría del STEP está en MILÍMETROS (b-box: x∈[-39.5,39.5], z∈[0,50.3] mm).
# - `core/kratos_adapter.py:366` alimenta a Kratos YOUNG_MODULUS SIN conversión,
#   es decir E en PASCALES (68.9e9) sobre coordenadas en mm. El solve es agnóstico
#   a unidades (por eso los tiempos son válidos pase lo que pase), pero el valor
#   absoluto de la compliance queda escalado por esa inconsistencia.
# - Para reportar una compliance FÍSICAMENTE VÁLIDA con u impuesto en mm, E debe
#   estar en N/mm² (MPa): E_MPa = E_Pa/1e6 = 68.9e3.
MATERIAL_YOUNG_PA = 68.9e9          # lo que recibe Kratos (Pa) — igual solve/baseline
MATERIAL_YOUNG_MPA = 68.9e3         # N/mm² (MPa) — para la compliance física (u en mm)
MATERIAL_POISSON = 0.33

# Presets de solver lineal Kratos para la Fase 1 (comparación de rendimiento).
# Valores verificados disponibles en este build (`python_linear_solver_factory`,
# LinearSolversApplication presente):
#   - skyline_lu_factorization -> SkylineLUFactorizationSolver (DEFAULT del adaptador)
#   - sparse_lu                -> SparseLUSolver (Eigen SSparseLU, via LinearSolversApplication)
#   - amgcl                   -> AMGCLSolver (iterativo + AMG). OJO: el coarsening
#                                "ruge_stuben" NO está soportado por el backend de este
#                                build ("coarsening not supported by the backend"); el
#                                valor oficial "aggregation" (con krylov "gmres") SÍ está
#                                verificado resolviendo de verdad. Pardiso/SuperLU no hay.
SOLVER_PRESETS = {
    "skyline_lu": {"solver_type": "skyline_lu_factorization", "scaling": False, "tolerance": 1e-6},
    "sparse_lu": {"solver_type": "sparse_lu"},
    "amgcl": {
        "preconditioner_type": "amg",
        "solver_type": "amgcl",
        "smoother_type": "ilu0",
        "krylov_type": "gmres",
        "coarsening_type": "aggregation",
        "max_iteration": 100,
        "gmres_krylov_space_dimension": 100,
        "tolerance": 1e-6,
        "verbosity": 0,
    },
}

_S = importlib.util.find_spec("KratosMultiphysics")
if _S is not None and _S.submodule_search_locations:
    _libs = os.path.join(list(_S.submodule_search_locations)[0], ".libs")
    if os.path.isdir(_libs):
        os.add_dll_directory(_libs)

# Fase 1: importar explícitamente LinearSolversApplication de forma temprana.
# Sin ello, `solver_type: "sparse_lu"` (Eigen SSparseLU, vive en esa app) falla de
# forma intermitente por un race de lazy-load cuado se construye tras otra app;
# importándola primero se vuelve confiable. Guardado con try/except para no romper
# el flujo por defecto (skyline_lu / RHS-force) en builds sin esa aplicación.
try:
    import KratosMultiphysics.LinearSolversApplication as _LSA  # noqa: F401
except Exception:
    _LSA = None


def _load_mesh(mesh_name: str, meshes_dir: str):
    path = os.path.join(meshes_dir, f"{mesh_name}.npz")
    data = np.load(path)
    return data["nodes"].astype(float), data["elements"].astype(int)


IMPOSED_DISP_Z = -1.0


def _apply_imposed_displacement(model_part, nodes, axis=2, value=-1.0, tolerance=0.01):
    """Aplica una condición de *desplazamiento impuesto* en la cara superior.

    Es el único mecanismo de carga que este build de Kratos soporta a prueba
    (la ruta de fuerza/RHS está bloqueada: ver Fase 0.5). Fija el DOF de
    desplazamiento de los nodos de la cara ``z == z_max`` a ``value`` (y fija los
    otros dos DOFs de esos nodos a 0), generando una deformación real no trivial.
    """
    import KratosMultiphysics as Kratos

    top_z = nodes[:, 2].max()
    top = np.where(np.abs(nodes[:, 2] - top_z) < tolerance)[0]
    for ni in top:
        node = model_part.Nodes[int(ni) + 1]
        for a in range(3):
            node.Fix(getattr(Kratos, f"DISPLACEMENT_{'XYZ'[a]}"))
            if a == axis:
                node.SetSolutionStepValue(
                    getattr(Kratos, f"DISPLACEMENT_{'XYZ'[a]}"), 0, value
                )
    return len(top)


def build_adapter(mesh_name: str, meshes_dir: str, load_mode: str = "force"):
    """Construye un KratosAdapter con la malla, material, restricciones y cargas.

    Devuelve el (adapter, model_part) ya configurado y la malla, para poder
    separar el tiempo de cada etapa en el caller.

    load_mode:
      * ``"force"``       — carga de fuerza distribuida en la cara superior (la ruta
                            original del RHS; en este build de Kratos queda en 0 y es
                            la medida "antes de"). 
      * ``"imposed_disp"``— desplazamiento impuesto en la cara superior (baseline real
                            físico; verifica rendimiento con deformación no trivial).
    """
    from core.kratos_adapter import KratosAdapter
    from core.materials import STANDARD_MATERIALS
    from core.study import ConstraintDefinition, LoadDefinition, ConstraintType, LoadType
    from core.solver_interface import _apply_constraint_geometrically, _apply_load_geometrically

    nodes, elements = _load_mesh(mesh_name, meshes_dir)

    t_setup = time.perf_counter()
    adapter = KratosAdapter()
    model_part = adapter.create_model_part(f"BM_{mesh_name}")
    adapter.add_nodal_variables(model_part)
    t_after_mp = time.perf_counter()

    adapter.import_mesh_from_core_format(
        model_part, nodes, elements, element_type="tet4"
    )
    t_after_import = time.perf_counter()

    adapter.configure_material_from_core(model_part, STANDARD_MATERIALS["aluminum"])
    adapter.add_displacement_dofs(model_part)
    t_after_mat = time.perf_counter()

    constraints = [
        ConstraintDefinition(
            id="c1", constraint_type=ConstraintType.FIXED, location_face_id="base",
            fixed_axis=2, fixed_coordinate=0.0, tolerance=0.01,
        )
    ]
    nodes_list = nodes.tolist()
    for c in constraints:
        _apply_constraint_geometrically(adapter, model_part, c, nodes_list)
    if load_mode == "imposed_disp":
        _apply_imposed_displacement(model_part, nodes)
    else:
        loads = [
            LoadDefinition(
                id="l1", magnitude=1000.0, direction=(0.0, 0.0, -1.0),
                load_type=LoadType.DISTRIBUTED, load_axis=2, load_coordinate=Z_MAX,
                tolerance=0.01,
            )
        ]
        for l in loads:
            _apply_load_geometrically(adapter, model_part, l, nodes_list)
    t_after_bc = time.perf_counter()

    timings = {
        "modelpart_and_vars_s": round(t_after_mp - t_setup, 4),
        "mesh_import_s": round(t_after_import - t_after_mp, 4),
        "material_and_dofs_s": round(t_after_mat - t_after_import, 4),
        "bc_apply_s": round(t_after_bc - t_after_mat, 4),
    }
    return adapter, model_part, nodes, elements, timings


def run_fea(
    mesh_name: str,
    meshes_dir: str,
    track_memory: bool = True,
    load_mode: str = "force",
    solver_config: dict = None,
):
    """Ejecuta una corrida FEA completa y devuelve el dict de tiempos + resultado.

    En modo ``imposed_disp`` la compliance se calcula por energía interna
    0.5·uᵀ·K·u (post-proceso NumPy sobre la solución de Kratos), porque en ese
    modo no hay vector de fuerza explícito y el build de Kratos no expone ni K
    ni reacciones ni STRAIN_ENERGY por Python.

    ``solver_config`` (opcional): dict con ``{"linear_solver_settings": {...}}``
    que se reenvía a ``adapter.run_analysis`` → ``setup_solver_and_strategy``.
    Permite comparar solvers de Kratos en la Fase 1 sin tocar el código y sin
    cambiar el default al no pasarlo (None).
    """
    from benchmarks.compliance import tet4_strain_energy

    mem_monitor = None
    if track_memory:
        from benchmarks.memory import PeakRSS

        mem_monitor = PeakRSS().start()

    adapter, model_part, nodes, elements, timings = build_adapter(
        mesh_name, meshes_dir, load_mode=load_mode
    )

    t_solve0 = time.perf_counter()
    result = adapter.run_analysis(model_part, solver_config=solver_config)
    timings["solve_and_extract_s"] = round(time.perf_counter() - t_solve0, 4)

    success = bool(result.get("success"))
    results = result.get("results", {})
    timings["success"] = success
    if success:
        timings["num_nodes_with_displacement"] = results.get(
            "num_nodes_with_displacement", 0
        )
        if load_mode == "imposed_disp":
            disp = np.asarray(results.get("displacements", []), dtype=float)
            timings["max_abs_disp"] = float(np.abs(disp).max()) if disp.size else 0.0
            timings["compliance"] = tet4_strain_energy(
                nodes, elements, disp, MATERIAL_YOUNG_MPA, MATERIAL_POISSON
            )
        else:
            timings["compliance"] = results.get("compliance", 0.0)

    peak_kb = None
    if mem_monitor is not None:
        peak_kb = mem_monitor.stop() / 1024.0

    timings["total_s"] = round(
        sum(v for k, v in timings.items() if isinstance(v, (int, float)) and k.endswith("_s")),
        4,
    )
    timings["peak_memory_kb"] = round(peak_kb, 1) if peak_kb is not None else None
    timings["num_nodes"] = nodes.shape[0]
    timings["num_elements"] = elements.shape[0]
    return timings, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--meshes", default=os.path.join(_HERE, "meshes"))
    parser.add_argument("--out", default=os.path.join(_HERE, "results"))
    parser.add_argument("--mesh", default=None, help="solo una malla: small_500|medium_5k|large_50k")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--no-memory", action="store_true", help="no medir pico de RSS (memoria)")
    parser.add_argument("--profile", action="store_true", help="correr cProfile sobre la malla mediana")
    parser.add_argument(
        "--load-mode", default="force", choices=["force", "imposed_disp"],
        help="fuerza distribuida en cara superior (RHS bloqueado -> u=0) o "
             "desplazamiento impuesto (baseline real fisico, u != 0). Default: force.",
    )
    parser.add_argument(
        "--solver", default=None, choices=list(SOLVER_PRESETS.keys()),
        help="preset de solver lineal Kratos para comparar (Fase 1): "
             "skyline_lu (default del adaptador) | sparse_lu | amgcl. "
             "Default None = comportamiento original (skyline_lu).",
    )
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # Config de solver reenviada al run_analysis (solo si se eligió uno).
    solver_config = None
    if args.solver:
        solver_config = {"linear_solver_settings": dict(SOLVER_PRESETS[args.solver])}

    with open(os.path.join(args.meshes, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)

    meshes = [m["name"] for m in manifest]
    if args.mesh:
        if args.mesh not in meshes:
            print(f"ERROR: malla '{args.mesh}' no está en el manifiesto. Disponibles: {meshes}")
            return 1
        meshes = [args.mesh]

    results_out = {}

    profiler = None
    if args.profile:
        import cProfile
        import pstats
        import io
        profiler = cProfile.Profile()

    target_profile = "medium_5k"
    for mesh in meshes:
        row = {"runs": []}
        for rep in range(max(1, args.repeats)):
            if profiler is not None and mesh == target_profile:
                profiler.enable()
            timings, result = run_fea(
                mesh, args.meshes,
                track_memory=not args.no_memory,
                load_mode=args.load_mode,
                solver_config=solver_config,
            )
            if profiler is not None and mesh == target_profile:
                profiler.disable()
            row["runs"].append(timings)
            print(f"[{mesh}] rep {rep + 1}: {timings}")
        # Reporte resumido (promedio de repeticiones)
        avg = {}
        keys = [k for k in row["runs"][0] if isinstance(row["runs"][0][k], (int, float))]
        for k in keys:
            vals = [r[k] for r in row["runs"] if isinstance(r.get(k), (int, float))]
            avg[k] = round(sum(vals) / len(vals), 4) if vals else None
        avg["success"] = all(r.get("success") for r in row["runs"])
        row["average"] = avg
        results_out[mesh] = row
        print(f"[{mesh}] AVERAGE: {avg}")

    # Sin --solver: se conserva el nombre original del baseline (para no romper
    # referencias/documentación previas). Con --solver: se etiqueta el archivo,
    # ya que es una comparación de solvers de la Fase 1.
    if args.solver:
        results_path = os.path.join(
            args.out,
            f"benchmark_fase0_{args.load_mode}_{args.solver}_baseline.json",
        )
    else:
        results_path = os.path.join(
            args.out, f"benchmark_fase0_{args.load_mode}_baseline.json"
        )
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump(results_out, fh, indent=2, default=str)
    print(f"\nBaseline JSON escrito en {results_path}")

    if profiler is not None:
        import pstats
        prof_path = os.path.join(args.out, "benchmark_fase0_medium_5k.prof")
        profiler.dump_stats(prof_path)
        # Volcado legible como texto
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
        stats.print_stats(40)
        txt_path = os.path.join(args.out, "benchmark_fase0_medium_5k.txt")
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(stream.getvalue())
        print(f"cProfile guardado en {prof_path} y {txt_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
