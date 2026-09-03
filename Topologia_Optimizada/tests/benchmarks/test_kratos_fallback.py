"""Tests del fallback de solver lineal iterativo -> directo (Fase 1+, punto d).

Cubre la garantía de producción pedida: si un solver iterativo (amgcl) NO converge
(o falla / no existe), el adaptador debe caer automáticamente a la factorización
directa ``skyline_lu`` con un warning y devolver un resultado correcto, en vez de
`success=True` con un campo de desplazamiento silenciosamente incorrecto.

Uso de `build_adapter` de benchmark_fase0 (ya registra el directorio DLL de Kratos
e importa LinearSolversApplication temprano) sobre la malla pequeña (rápida).
"""

import os
import sys

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from benchmarks.benchmark_fase0 import build_adapter, MATERIAL_YOUNG_MPA, MATERIAL_POISSON
    from benchmarks.compliance import tet4_strain_energy

    _KRATOS = True
except Exception as _e:  # noqa: BLE001
    _KRATOS = False
    _KRATOS_ERR = str(_e)

_MESHES = os.path.join(_ROOT, "benchmarks", "meshes")

AMG_OK = {
    "preconditioner_type": "amg",
    "solver_type": "amgcl",
    "smoother_type": "ilu0",
    "krylov_type": "gmres",
    "coarsening_type": "aggregation",
    "max_iteration": 100,
    "gmres_krylov_space_dimension": 100,
    "tolerance": 1e-6,
}
# Config que NO puede converger a la tolerancia pedida (si el solve respetara
# max_iteration=1) -> la verificación debe detectarla y caer a skyline_lu.
AMG_FORCED_NONCONV = dict(AMG_OK, max_iteration=1, tolerance=1e-30)
BAD_SOLVER = {"solver_type": "solver_que_no_existe_xyz"}
SKY = {"solver_type": "skyline_lu_factorization", "scaling": False, "tolerance": 1e-6}


def _run(mesh, cfg, verify=True):
    adapter, model_part, nodes, elements, _ = build_adapter(
        mesh, _MESHES, load_mode="imposed_disp"
    )
    result = adapter.run_analysis(
        model_part, solver_config={"linear_solver_settings": cfg, "verify_convergence": verify}
    )
    disp = np.asarray(result.get("results", {}).get("displacements", []), dtype=float)
    compliance = tet4_strain_energy(nodes, elements, disp, MATERIAL_YOUNG_MPA, MATERIAL_POISSON)
    return result, compliance, adapter, model_part, nodes, elements


def _ref_compliance(mesh):
    adapter, model_part, nodes, elements, _ = build_adapter(mesh, _MESHES, load_mode="imposed_disp")
    r = adapter.run_analysis(model_part, solver_config={"linear_solver_settings": SKY})
    d = np.asarray(r["results"]["displacements"], dtype=float)
    return tet4_strain_energy(nodes, elements, d, MATERIAL_YOUNG_MPA, MATERIAL_POISSON)


pytestmark = pytest.mark.skipif(not _KRATOS, reason=f"Kratos no disponible: {locals().get('_KRATOS_ERR')}")


def test_amgcl_convergent_no_fallback():
    result, compliance, *_ = _run("small_500", AMG_OK)
    assert result["success"] is True
    assert result.get("fallback_used") is False


def test_amgcl_nonconvergent_falls_back_to_skyline():
    result, compliance, *_ = _run("small_500", AMG_FORCED_NONCONV)
    assert result["success"] is True
    assert result.get("fallback_used") is True
    ref = _ref_compliance("small_500")
    assert abs(compliance - ref) / abs(ref) < 1e-6


def test_invalid_solver_falls_back_to_skyline():
    result, compliance, *_ = _run("small_500", BAD_SOLVER)
    assert result["success"] is True
    assert result.get("fallback_used") is True
    ref = _ref_compliance("small_500")
    assert abs(compliance - ref) / abs(ref) < 1e-6


def test_default_solver_no_config_still_works():
    adapter, model_part, nodes, elements, _ = build_adapter(
        "small_500", _MESHES, load_mode="imposed_disp"
    )
    result = adapter.run_analysis(model_part)
    assert result["success"] is True
    assert result.get("fallback_used") is False
    disp = np.asarray(result["results"]["displacements"], dtype=float)
    compliance = tet4_strain_energy(nodes, elements, disp, MATERIAL_YOUNG_MPA, MATERIAL_POISSON)
    ref = _ref_compliance("small_500")
    assert abs(compliance - ref) / abs(ref) < 1e-6
