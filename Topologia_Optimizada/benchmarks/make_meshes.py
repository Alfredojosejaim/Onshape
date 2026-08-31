"""Fase 0 — Generación de mallas de referencia.

Genera 3 mallas Tet4 de tamaño creciente (~500 / ~5.000 / ~50.000 elementos)
usando ``GmshTet4Mesher`` sobre ``cono.step`` (geometría STEP real). Cada malla
se guarda como ``.npz`` con los arrays de nodos (Nx3) y elementos (Mx4) para
evitar la ida y vuelta por listas Python y que el benchmark mida el flujo real
basado en arrays NumPy.

Uso:
    python benchmarks/make_meshes.py [--out benchmarks/meshes]
"""

import argparse
import importlib.util
import logging
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Registro del directorio .libs de Kratos en Windows (requisito del runtime).
_S = importlib.util.find_spec("KratosMultiphysics")
if _S is not None and _S.submodule_search_locations:
    _libs = os.path.join(list(_S.submodule_search_locations)[0], ".libs")
    if os.path.isdir(_libs):
        os.add_dll_directory(_libs)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("make_meshes")

# (nombre, target_element_size): el tamaño de elemento Gmsh se traduce a un
# número de elementos aproximado (validado por barrido sobre cono.step).
REFERENCE_MESHES = [
    ("small_500", 11.5),
    ("medium_5k", 5.2),
    ("large_50k", 2.5),
]


def _mesh_count(step_file: str, element_size: float):
    from core.meshing import GmshTet4Mesher

    m = GmshTet4Mesher()
    t0 = time.perf_counter()
    result = m.generate_mesh_from_step(step_file, target_element_size=element_size)
    elapsed = time.perf_counter() - t0
    return result, elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(_HERE, "meshes"))
    parser.add_argument("--step", default=os.path.join(_ROOT, "cono.step"))
    parser.add_argument("--only", default=None, help="nombre de malla a generar (opcional)")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    if not os.path.exists(args.step):
        logger.error("Archivo STEP no encontrado: %s", args.step)
        return 1

    manifest = []
    for name, element_size in REFERENCE_MESHES:
        if args.only and name != args.only:
            continue
        logger.info("Generando malla %s (element_size=%.2f) ...", name, element_size)
        result, elapsed = _mesh_count(args.step, element_size)

        nodes = np.asarray(result.nodes, dtype=float)
        elements = np.asarray(result.elements, dtype=int)
        out_path = os.path.join(args.out, f"{name}.npz")
        np.savez_compressed(out_path, nodes=nodes, elements=elements)
        manifest.append(
            {
                "name": name,
                "element_size": element_size,
                "num_nodes": int(result.num_nodes),
                "num_elements": int(result.num_elements),
                "mesh_time_s": round(elapsed, 4),
                "npz": out_path,
            }
        )
        logger.info(
            "  -> %d nodos, %d elementos, %.2fs (guardado en %s)",
            result.num_nodes,
            result.num_elements,
            elapsed,
            out_path,
        )

    manifest_path = os.path.join(args.out, "manifest.json")
    import json

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    logger.info("Manifiesto escrito en %s", manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
