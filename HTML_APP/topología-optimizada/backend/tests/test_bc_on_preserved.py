"""FASE-4: carga aplicada dentro de una región preservada.

Caso distinto de BC-SHORTCUT y SIN error duro a propósito: que la carga caiga
sobre material preservado es el caso normal (el halo auto-preserva alrededor
de cargas/apoyos; un perno preservado con carga es un setup legítimo) y no
hay colapso a vacío (u != 0). Solo se marca como degradada en `unsupported`
para que la UI lo muestre en "Condiciones degradadas".
"""

import numpy as np

from core.conditions import condition_from_dict, ConditionType
from core.generative_engine import GenerativeDesignEngine
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
    return condition_from_dict({
        "type": "elasticity", "name": "Fijacion",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "flex_range_mm": None, "metadata": {},
    })


def _protected(face_index=3):
    return condition_from_dict({
        "type": "protected_region", "name": "Preservada",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": face_index}], "mode": "multi"},
        "geometry_refs": [], "metadata": {},
    })


def test_fraccion_helper_casos_limite():
    els = np.array([[0, 1, 2, 3]])
    f = np.zeros(12)
    f[0:3] = -10.0  # solo nodo 0
    assert GenerativeDesignEngine._load_on_preserved_fraction(
        f, [0], els) == 1.0
    assert GenerativeDesignEngine._load_on_preserved_fraction(
        np.zeros(12), [0], els) == 0.0
    assert GenerativeDesignEngine._load_on_preserved_fraction(
        f, [], els) == 0.0
    assert GenerativeDesignEngine._load_on_preserved_fraction(
        f, [5], els) == 0.0  # índice fuera de rango se ignora
    f[3:6] = -10.0  # nodos 0 y 1, ambos del elemento 0
    assert GenerativeDesignEngine._load_on_preserved_fraction(
        f, [0], els) == 1.0


def test_carga_en_preservada_marca_degradada_sin_error():
    # Carga -X -> nodos x=0; preservada con cara sin mapear -> fallback
    # bbox-end (eje X, extremo lo = x=0). Solape total, sin raise.
    nodes, els, _ = _mesh()
    eng = GenerativeDesignEngine(model_id=None, mesh_nodes=nodes,
                                 mesh_elements=els)
    conds = {ConditionType.LOAD: [_load((-1.0, 0.0, 0.0))],
             ConditionType.ELASTICITY: [_support()],
             ConditionType.PROTECTED_REGION: [_protected()]}
    forces, fixed, preserved, void, unsupported = \
        eng._map_conditions_to_problem(conds, raise_on_unmapped_face=False)
    assert len(preserved) > 0
    frac = eng._load_on_preserved_fraction(forces, preserved, els)
    assert frac >= 0.9
    assert "load_on_preserved_region" in unsupported
    # el guard de fijos no debe haber saltado en este setup
    assert "load_on_fixed_dofs" not in unsupported


def test_sin_preservada_no_hay_flag():
    nodes, els, _ = _mesh()
    eng = GenerativeDesignEngine(model_id=None, mesh_nodes=nodes,
                                 mesh_elements=els)
    conds = {ConditionType.LOAD: [_load((0.0, -1.0, 0.0))],
             ConditionType.ELASTICITY: [_support()],
             ConditionType.PROTECTED_REGION: []}
    _, _, _, _, unsupported = eng._map_conditions_to_problem(
        conds, raise_on_unmapped_face=False)
    assert "load_on_preserved_region" not in unsupported
