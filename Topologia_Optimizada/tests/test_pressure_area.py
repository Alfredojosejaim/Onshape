"""PRESSURE loads: Pa x face area -> total force (Fase 3b, D2).

Pressure (Pa/kPa/MPa) converts to a total normal force using the face surface
triangulation (mesh in mm: mm2 -> m2). Without triangulation the area is
unknown and the load fails explicitly -- never a silent Pa-as-N substitution.
"""

import numpy as np
import pytest


def _grid():
    xs = np.linspace(0.0, 10.0, 3)
    ys = np.linspace(0.0, 10.0, 3)
    nodes = np.array([[x, y, 1.0 if (i + j) % 2 == 0 else 0.0]
                      for j, y in enumerate(ys) for i, x in enumerate(xs)])
    return nodes


def _top_tris(nodes):
    top = np.nonzero(np.isclose(nodes[:, 2], 1.0))[0].tolist()
    # Fan over the 5 top nodes (indices into the full node array).
    return [[top[0], top[k], top[k + 1]] for k in range(1, len(top) - 1)]


def _pressure_condition(unit="MPa", magnitude=2.0):
    from core.conditions import LoadCondition
    from core.cad_entity import CadEntityRef, SelectionSet
    ref = CadEntityRef.from_face(0, model_id="m")
    return LoadCondition(
        name="p", magnitude=magnitude, unit=unit,
        faces=SelectionSet(entities=[ref]),
    )


def _engine(nodes, face_tris):
    from core.generative_engine import GenerativeDesignEngine
    from core.materials import STANDARD_MATERIALS
    from core.conditions import ConditionManager
    return GenerativeDesignEngine(
        model_id="m",
        mesh_nodes=np.asarray(nodes, dtype=float),
        mesh_elements=np.array([[0, 1, 3, 4]]),
        material=STANDARD_MATERIALS["steel"],
        condition_manager=ConditionManager(),
        model_shape=None,
        face_surface_elements={"face_0": face_tris},
        physical_groups=None,
    )


def test_unit_conversion_helpers():
    from core.boundary import (
        is_pressure_unit, pressure_to_total_force_N, surface_area_mm2,
    )
    assert is_pressure_unit("Pa") and is_pressure_unit("kPa") and is_pressure_unit("MPa")
    assert not is_pressure_unit("N") and not is_pressure_unit(None)
    # 1 MPa over 1 mm2 = 1 N.
    assert pressure_to_total_force_N(1.0, "MPa", 1.0) == pytest.approx(1.0)
    # 1 Pa over 1 m2 (1e6 mm2) = 1 N.
    assert pressure_to_total_force_N(1.0, "Pa", 1e6) == pytest.approx(1.0)
    # Unit right triangle (0,0,0)-(2,0,0)-(0,2,0): area = 2 mm2.
    nodes = np.array([[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]])
    assert surface_area_mm2(nodes, [[0, 1, 2]]) == pytest.approx(2.0)
    with pytest.raises(ValueError, match="rea"):
        pressure_to_total_force_N(1.0, "MPa", 0.0)
    with pytest.raises(ValueError, match="desconocida"):
        pressure_to_total_force_N(1.0, "psi", 1.0)


def test_local_pressure_equals_equivalent_distributed_force():
    """Same face, same direction: pressure total == explicit force total."""
    from core.conditions import ConditionType, LoadCondition
    from core.cad_entity import CadEntityRef, SelectionSet
    from core.boundary import surface_area_mm2, pressure_to_total_force_N

    nodes = _grid()
    tris = _top_tris(nodes)
    area = surface_area_mm2(nodes, tris)
    assert area > 0.0
    pressure_MPa = 2.0
    total_N = pressure_to_total_force_N(pressure_MPa, "MPa", area)

    eng = _engine(nodes, tris)
    by_type_p = {ConditionType.LOAD: [_pressure_condition("MPa", pressure_MPa)]}
    ref = CadEntityRef.from_face(0, model_id="m")
    force_N = LoadCondition(
        name="f", magnitude=total_N, unit="N",
        faces=SelectionSet(entities=[ref]),
    )
    by_type_f = {ConditionType.LOAD: [force_N]}

    fp, *_ = eng._map_conditions_to_problem(by_type_p, raise_on_unmapped_face=False)
    ff, *_ = eng._map_conditions_to_problem(by_type_f, raise_on_unmapped_face=False)
    np.testing.assert_allclose(fp, ff, rtol=1e-12)


def test_local_pressure_without_area_is_unsupported():
    from core.conditions import ConditionType, LoadCondition
    nodes = _grid()
    eng = _engine(nodes, [])  # no triangulation -> no area
    eng.face_surface_elements = {}
    # No selected faces: coordinate fallback gives nodes, but pressure has
    # no area to integrate -> honest unsupported (never Pa-as-N).
    load = LoadCondition(name="p", magnitude=2.0, unit="MPa")
    by_type = {ConditionType.LOAD: [load]}
    _, _, _, _, unsupported = eng._map_conditions_to_problem(
        by_type, raise_on_unmapped_face=True)
    assert any("pressure" in u for u in unsupported)


def test_bridge_propagates_pressure_type():
    from core.kratos_bridge import load_condition_to_definition
    from core.study import LoadType
    d = load_condition_to_definition(_pressure_condition("kPa", 50.0))
    assert d.load_type == LoadType.PRESSURE
    assert d.unit == "kPa"
    d2 = load_condition_to_definition(_pressure_condition("N", 10.0))
    assert d2.load_type == LoadType.DISTRIBUTED
