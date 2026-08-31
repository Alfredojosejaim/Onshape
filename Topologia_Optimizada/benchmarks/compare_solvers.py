"""Fase 1 — Comparación de solvers lineales Kratos (baselines por solver).

Lee los JSON de `benchmarks/results/benchmark_fase0_imposed_disp_{solver}_baseline.json`
(uno por solver: skyline_lu por defecto sin etiqueta, sparse_lu, amgcl) y muestra una
tabla comparativa del tiempo de solve / total y la compliance (N·mm) por malla.

Uso:
    python benchmarks/compare_solvers.py
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_HERE, "results")

# (etiqueta, nombre de archivo) — skyline_lu sin --solver = filename base.
SOLVERS = [
    ("skyline_lu (default)", "benchmark_fase0_imposed_disp_baseline.json"),
    ("sparse_lu", "benchmark_fase0_imposed_disp_sparse_lu_baseline.json"),
    ("amgcl", "benchmark_fase0_imposed_disp_amgcl_baseline.json"),
]
MESHES = ["small_500", "medium_5k", "large_50k"]


def main() -> int:
    data = {}
    for label, fname in SOLVERS:
        path = os.path.join(_RESULTS, fname)
        if not os.path.exists(path):
            print(f"[warn] falta {fname}")
            continue
        with open(path, encoding="utf-8") as fh:
            data[label] = json.load(fh)

    print("Fase 1 - Comparacion de solvers (load-mode imposed_disp, displacement Z=-1 mm)\n")
    hdr = f"{'solver':26s}" + "".join(f"{m:>20s}" for m in MESHES)
    print(hdr)
    print("-" * len(hdr))
    for label in dict.fromkeys([s[0] for s in SOLVERS]):
        if label not in data:
            continue
        row = f"{label:26s}"
        for m in MESHES:
            r = data[label].get(m, {})
            a = r.get("average", {})
            sol = a.get("solve_and_extract_s")
            row += f"{('%.2fs' % sol) if sol is not None else 'n/a':>20s}"
        print(row)
    print()

    # Compliance convergente (debe coincidir entre solvers a 1e-6 relativo)
    print("Compliance 0.5*u^T*K*u (N*mm) por malla - debe coincidir entre solvers:")
    for m in MESHES:
        vals = []
        for label, _ in SOLVERS:
            if label not in data:
                continue
            c = data[label].get(m, {}).get("average", {}).get("compliance")
            if c is not None:
                vals.append((label, c))
        if vals:
            lines = "  ".join(f"{lb}={c:.6g}" for lb, c in vals)
            print(f"  {m:12s} {lines}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
