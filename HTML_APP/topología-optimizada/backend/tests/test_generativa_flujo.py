"""Regresión flujo generativo escenario A (GEN-LEGACY / GEN-NOCOND).

Cubre el no-op silencioso reportado: la generativa, a diferencia de la
estructural, no caía a las BC clásicas ni avisaba cuando no le llegaban
condiciones, así que resolvía con carga cero y "no hacía nada".

Se prueba a nivel core (sin CAD/OCCT): malla sintética + ConditionManager,
y la rama legacy del controller pasando force/fixed_dofs explícitos.
"""

import numpy as np
import pytest

from core.conditions import condition_from_dict, ConditionManager
from core.generative import GenerativeDesignStudy
from core.generative_engine import GenerativeDesignEngine, run_generative_design
from core.materials import STANDARD_MATERIALS
from core.optimization_studies import TopOptParameters
from tests.test_gcmma import kuhn_bar

E = 210e3
NU = 0.3


def _mesh():
    nodes, els, nid = kuhn_bar(2)
    return np.asarray(nodes, dtype=float), np.asarray(els, dtype=int), nid


def _load_condition(direction=(0.0, -1.0, 0.0), magnitude=1000.0):
    return condition_from_dict({
        "type": "load", "name": "Carga",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "orientation": "perpendicular", "reference_plane_normal": [0, 0, 1],
        "angle_deg": None, "sense": "positive", "magnitude": magnitude,
        "indeterminate": False, "unit": "N", "metadata": {},
        "direction": list(direction),
    })


def _elasticity_condition():
    return condition_from_dict({
        "type": "elasticity", "name": "Fijacion",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "flex_range_mm": None, "metadata": {},
    })


def _study(condition_ids, max_iterations=3):
    study = GenerativeDesignStudy(name="g")
    study.scenario = "A"
    study.conditions = list(condition_ids)
    op = TopOptParameters()
    op.volume_fraction = 0.4
    op.max_iterations = max_iterations
    op.filter_radius = 0.6
    study.optimization_params = op
    return study


def _engine(nodes, els, manager):
    return GenerativeDesignEngine(
        model_id=None, mesh_nodes=nodes, mesh_elements=els,
        material=STANDARD_MATERIALS["steel"], condition_manager=manager,
    )


def test_scenario_a_runs_with_reusable_conditions():
    nodes, els, _ = _mesh()
    mgr = ConditionManager()
    load = _load_condition()
    supp = _elasticity_condition()
    mgr.add(load)
    mgr.add(supp)
    study = _study([load.id, supp.id])
    result = run_generative_design(study, mgr, _engine(nodes, els, mgr))
    x = np.asarray(result["densities"], dtype=float)
    assert x.shape == (len(els),) and np.all(np.isfinite(x))
    assert result["_consumed_load_conditions"] == 1
    assert result["_consumed_elasticity_conditions"] == 1
    assert np.isfinite(result["final_compliance"])
    assert 0.0 < result["final_volume_fraction"] <= 1.0
    assert "reconstruction" in result


def test_scenario_a_fails_loud_without_any_conditions():
    nodes, els, _ = _mesh()
    mgr = ConditionManager()
    study = _study([])
    with pytest.raises(ValueError, match="sin condiciones"):
        run_generative_design(study, mgr, _engine(nodes, els, mgr))


def test_scenario_a_legacy_bc_fallback_runs():
    """Sin condiciones reutilizables pero con BC clásicas: corre (no no-op)."""
    nodes, els, nid = _mesh()
    mgr = ConditionManager()
    study = _study([])
    fixed = []
    for j in range(2):
        for k in range(2):
            n0 = nid[(0, j, k)]
            fixed += [n0 * 3, n0 * 3 + 1, n0 * 3 + 2]
    force = np.zeros(len(nodes) * 3)
    for j in range(2):
        for k in range(2):
            force[nid[(2, j, k)] * 3 + 1] = -50.0
    result = run_generative_design(
        study, mgr, _engine(nodes, els, mgr),
        legacy_force=force, legacy_fixed_dofs=np.asarray(fixed, dtype=int),
    )
    x = np.asarray(result["densities"], dtype=float)
    assert np.all(np.isfinite(x))
    assert result["_consumed_load_conditions"] == 0
    assert np.isfinite(result["final_compliance"])
