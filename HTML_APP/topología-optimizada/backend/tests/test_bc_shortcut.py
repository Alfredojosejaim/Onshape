"""BC-SHORTCUT: la carga aplicada sobre nodos fijos no hace trabajo.

Regresion del colapso silencioso: con la carga sobre la misma zona que el
apoyo la compliance es ~0, el OC solo minimiza volumen y el diseno colapsa a
vacio (isosuperficie degenerada). Documentado en test_generativa_flujo.py
(carga -Z sobre la base fija). Ahora falla explicito.
"""

import numpy as np
import pytest

from core.conditions import condition_from_dict, ConditionManager
from core.generative_engine import GenerativeDesignEngine, consume_conditions
from tests.test_gcmma import kuhn_bar


def _mesh(nx=2):
    nodes, els, nid = kuhn_bar(nx)
    return np.asarray(nodes, dtype=float), np.asarray(els, dtype=int), nid


def _load(direction):
    return condition_from_dict({
        "type": "load", "name": "Carga",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "orientation": "perpendicular", "reference_plane_normal": [0, 0, 1],
        "angle_deg": None, "sense": "positive", "magnitude": 1000.0,
        "indeterminate": False, "unit": "N", "metadata": {},
        "direction": list(direction),
    })


def _support():
    # Sin caras -> fallback base-Z (nodos min-Z), igual que la app.
    return condition_from_dict({
        "type": "elasticity", "name": "Fijacion",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "flex_range_mm": None, "metadata": {},
    })


def _conditions(load_dir):
    nodes, els, nid = _mesh()
    eng = GenerativeDesignEngine(model_id=None, mesh_nodes=nodes, mesh_elements=els)
    mgr = ConditionManager()
    load = _load(load_dir)
    supp = _support()
    mgr.add(load)
    mgr.add(supp)
    return eng, consume_conditions(mgr, [load.id, supp.id])


def test_carga_sobre_la_base_fija_falla_explicito():
    # -Z cae sobre los nodos min-Z, que es justo el fallback del apoyo base-Z.
    eng, conds = _conditions((0.0, 0.0, -1.0))
    with pytest.raises(ValueError, match="nodos fijos"):
        eng._map_conditions_to_problem(conds)


def test_solape_parcial_no_bloquea():
    # -Y cae sobre y=0; el apoyo base-Z fija z=0 -> se solapan 3 de 6 nodos.
    eng, conds = _conditions((0.0, -1.0, 0.0))
    forces, fixed, _pres, _void, unsupported = eng._map_conditions_to_problem(conds)
    frac = eng._load_on_fixed_fraction(forces, fixed)
    assert 0.0 < frac < 0.9
    assert "load_on_fixed_dofs" not in unsupported


def test_fraccion_uno_cuando_todo_cae_en_fijos():
    f = np.zeros(9)
    f[1] = -50.0
    f[4] = -50.0
    frac = GenerativeDesignEngine._load_on_fixed_fraction(f, [0, 1, 2, 3, 4, 5])
    assert frac == pytest.approx(1.0)
    assert GenerativeDesignEngine._load_on_fixed_fraction(np.zeros(9), [0, 1, 2]) == 0.0