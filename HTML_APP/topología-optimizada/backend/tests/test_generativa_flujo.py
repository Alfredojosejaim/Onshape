"""Regresión flujo generativo escenario A (GEN-LEGACY / GEN-NOCOND).

Cubre el no-op silencioso reportado: la generativa, a diferencia de la
estructural, no caía a las BC clásicas ni avisaba cuando no le llegaban
condiciones, así que resolvía con carga cero y "no hacía nada".

Se prueba a nivel core (sin CAD/OCCT): malla sintética + ConditionManager,
y la rama legacy del controller pasando force/fixed_dofs explícitos.
"""

import numpy as np
import pytest

from core.conditions import condition_from_dict, ConditionManager, ConditionType
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


def _faced_load(face_index=3):
    d = {
        "type": "load", "name": "Carga",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": face_index}], "mode": "multi"},
        "orientation": "perpendicular", "reference_plane_normal": [0, 0, 1],
        "angle_deg": None, "sense": "positive", "magnitude": 1000.0,
        "indeterminate": False, "unit": "N", "metadata": {},
        "direction": [0.0, 0.0, 1.0],
    }
    return condition_from_dict(d)


def _elasticity_condition():
    return condition_from_dict({
        "type": "elasticity", "name": "Fijacion",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "flex_range_mm": None, "metadata": {},
    })


def _faced_elasticity(face_index=3):
    d = {
        "type": "elasticity", "name": "Fijacion",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": face_index}], "mode": "multi"},
        "flex_range_mm": None, "metadata": {},
    }
    return condition_from_dict(d)


def _faced_protected(face_index=3):
    return condition_from_dict({
        "type": "protected_region", "name": "Preservada",
        "faces": {"name": "f", "entities": [
            {"entity_type": "face", "face_index": face_index}], "mode": "multi"},
        "geometry_refs": [], "metadata": {},
    })


def test_fallbacks_unmapped_faces_are_flagged_not_silent():
    """Fallbacks bbox/base-Z con caras reales sin mapear: explícitos, no silenciosos.

    Sin CAD shape (model_shape=None) ninguna cara resuelve a nodos: la rama
    permisiva (SIMP, raise_on_unmapped_face=False) debe listar
    elasticity(fallback_base_Z) y protected_region(fallback_bbox) en
    unsupported para que la UI lo muestre; la rama estricta mantiene
    "elasticity".
    """
    nodes, els, _ = _mesh()
    mgr = ConditionManager()
    eng = _engine(nodes, els, mgr)

    conds = {ConditionType.ELASTICITY: [_faced_elasticity()],
             ConditionType.PROTECTED_REGION: [_faced_protected()]}
    _, fixed, _, _, unsupported = eng._map_conditions_to_problem(
        conds, raise_on_unmapped_face=False)
    assert "elasticity(fallback_base_Z)" in unsupported
    assert "protected_region(fallback_bbox)" in unsupported
    assert len(fixed) > 0  # el fallback base-Z igual fija algo (permisivo)

    _, _, _, _, unsupported_strict = eng._map_conditions_to_problem(
        {ConditionType.ELASTICITY: [_faced_elasticity()]},
        raise_on_unmapped_face=True)
    assert "elasticity" in unsupported_strict

    # Sin caras seleccionadas: defaults legítimos, sin flags.
    _, _, _, _, unsupported_noface = eng._map_conditions_to_problem(
        {ConditionType.ELASTICITY: [_elasticity_condition()],
         ConditionType.PROTECTED_REGION: []},
        raise_on_unmapped_face=False)
    assert "elasticity(fallback_base_Z)" not in unsupported_noface
    assert "protected_region(fallback_bbox)" not in unsupported_noface

    # Carga con cara sin mapear: se marca pero el caso se conserva (permisivo).
    cases, _, unsupported_load = eng._map_conditions_to_load_cases(
        {ConditionType.LOAD: [_faced_load()]}, raise_on_unmapped_face=False)
    assert "load(fallback_bbox)" in unsupported_load
    assert len(cases) == 1 and float(np.abs(cases[0]).sum()) > 0.0


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


def test_register_rejects_bad_solids_before_store():
    """VALIDATE-BEFORE-STORE: invertido reparable se corrige, degenerado no.

    Regresión del "cuerpo de 0,0 cm³": el sewing puede producir un sólido
    válido pero invertido (Volume() negativo, caso real -231 con IsValid
    True) o un sliver degenerado. Lo primero se repara con Reverse()
    explícito (flag orientation_fixed); lo segundo se rechaza con
    registration_error y sin llamar a store_computed_shape (nunca se guarda).
    """
    import types

    import cadquery as cq

    from desktop.pipeline.controller import PipelineController

    nodes, els, _ = _mesh()  # kuhn_bar(2): volumen de malla = 2 mm3
    c = PipelineController.__new__(PipelineController)
    c.mesh_nodes = np.asarray(nodes, dtype=float)
    c.mesh_elements = np.asarray(els, dtype=int)
    c.cad = types.SimpleNamespace(
        store_computed_shape=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("no debe guardar un sólido rechazado")))

    box = cq.Solid.makeBox(1.0, 1.0, 1.0)  # 1 mm3 >> 1% de 2 mm3: apto
    _, reason_ok, flipped_ok = c._validate_reconstruction_solid(box)
    assert reason_ok is None and flipped_ok is False

    inverted = cq.Shape(box.wrapped.Reversed())  # volumen negativo
    shape_fixed, reason_inv, flipped_inv = c._validate_reconstruction_solid(inverted)
    assert reason_inv is None and flipped_inv is True
    assert float(shape_fixed.Volume()) > 0.0

    tiny = cq.Solid.makeBox(0.01, 0.01, 0.01)  # 1e-6 mm3 << 1%: degenerado
    _, reason_tiny, _ = c._validate_reconstruction_solid(tiny)
    assert reason_tiny is not None and "degenerado" in reason_tiny

    recon = {"data": tiny, "status": "repro"}
    assert c._register_reconstruction_model(recon) == {}
    assert "registration_error" in recon and "data" not in recon
    assert c.last_reconstruction_warning == recon["registration_error"]


def test_reconstruct_exposes_brep_error_on_collapse():
    """Colapso a xmin: sin sólido pero CON motivo (nunca "sin detalle").

    Con densidades bajo el threshold no hay isosuperficie: la etapa BREP
    falla y el dict final debe traer brep_error + la fuente única
    reconstruction_failure_reason debe devolverlo.
    """
    from types import SimpleNamespace

    from core.generative_engine import _reconstruct
    from desktop.pipeline.controller import reconstruction_failure_reason

    nodes, els, _ = _mesh()
    eng = SimpleNamespace(mesh_nodes=np.asarray(nodes, dtype=float),
                          mesh_elements=np.asarray(els, dtype=int))
    out = _reconstruct({"densities": np.full(len(els), 0.001)}, eng)
    assert out.get("stage") != "brep_solid"
    assert out.get("brep_error"), out
    assert reconstruction_failure_reason(out) == out["brep_error"]
    assert reconstruction_failure_reason(
        {"registration_error": "x"}) == "x"
    assert "surface_mesh" in reconstruction_failure_reason(
        {"stage": "surface_mesh", "status": "completed"})
    assert reconstruction_failure_reason({}) == "sin información de reconstrucción"


def test_registration_exposes_reconstructed_tessellation():
    """GEN-TESS: tras registrar la reconstrucción, el teselado activo debe ser
    el de la pieza generada (no quedar None y mostrar la pieza vieja).

    Regresión del bug: `_register_reconstruction_model` comprobaba
    `tess.get("success")`, clave que el dict de ÉXITO de tessellate_model no
    trae, así que descartaba la teselación y el viewport no cambiaba.

    Escenario físicamente válido: carga +Z (nodos max-Z) opuesta al soporte
    (base min-Z). Con la carga en -Z caía sobre los nodos fijos → compliance
    0 → OC colapsaba a xmin → reconstrucción degenerada (la dirección -Z
    quedó descartada a propósito, no por casualidad).
    """
    import json
    import time

    from api import Api

    api = Api()
    assert api.importStep("cono.step")["ok"]
    assert api.generateMesh(json.dumps({"target_element_size": 8.0}))["ok"]
    load = api.createCondition(json.dumps({
        "type": "load", "name": "L",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
        "orientation": "perpendicular", "reference_plane_normal": [0, 0, 1],
        "angle_deg": None, "sense": "positive", "magnitude": 1000.0,
        "indeterminate": False, "unit": "N", "metadata": {},
        "direction": [0, 0, 1],
    }))
    supp = api.createCondition(json.dumps({
        "type": "elasticity", "name": "S",
        "faces": {"name": "f", "entities": [], "mode": "multi"},
    }))
    run = api.runGenerativeDesign(json.dumps({
        "scenario": "A", "condition_ids": [load["id"], supp["id"]],
        "volume_fraction": 0.4, "max_iterations": 3,
        "penalization": 3.0, "filter_radius": 2.0,
        "convergence_tolerance": 1e-3,
    }))
    assert run["ok"], run
    jid = run["jobId"]
    for _ in range(600):
        poll = api.pollJob(jid)
        if poll.get("state") in ("done", "error", "failed"):
            break
        time.sleep(0.2)
    assert poll.get("state") == "done", poll
    reg = api.registerReconstruction(jid)
    assert reg["ok"] and reg.get("registered"), reg
    preview = api.getMeshPreview()
    assert preview["ok"], preview
    assert int(preview["mesh"].get("num_triangles") or 0) > 0
    assert preview["mesh"].get("vertices") and preview["mesh"].get("indices")

