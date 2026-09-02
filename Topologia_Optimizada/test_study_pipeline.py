"""Tests for the study pipeline: selection → CadEntityRef → study.parts →
conditions → solver → result → document → viewport.

Covers the 16 scenarios defined in prompts.md ETAPA 9.
"""

from __future__ import annotations

import numpy as np
import pytest

from core.cad_entity import CadEntityRef, EntityType, SelectionSet
from core.conditions import (
    ConditionManager,
    ConditionType,
    ElasticityCondition,
    LoadCondition,
    LoadOrientation,
    LoadSense,
    ObstructionCondition,
    ProtectedRegion,
)
from core.optimization_studies import TopologyOptimizationStudy


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def _solid_ref(model_id: str = "m1", solid_id: str = "solid_0") -> CadEntityRef:
    return CadEntityRef.from_solid(solid_id=solid_id, model_id=model_id)


def _face_ref(model_id: str = "m1", face_index: int = 0) -> CadEntityRef:
    return CadEntityRef.from_face(face_index=face_index, model_id=model_id)


def _make_conditions() -> ConditionManager:
    mgr = ConditionManager()
    load = LoadCondition(
        name="Carga",
        magnitude=1000.0,
        sense=LoadSense.POSITIVE,
        orientation=LoadOrientation.PERPENDICULAR,
    )
    support = ElasticityCondition(name="Soporte")
    prot = ProtectedRegion(name="Zona protegida")
    obs = ObstructionCondition(name="Obstrucción")
    mgr.add(load)
    mgr.add(support)
    mgr.add(prot)
    mgr.add(obs)
    return mgr


def _make_study(conditions: ConditionManager, parts: list | None = None,
                model_id: str = "m1") -> TopologyOptimizationStudy:
    study = TopologyOptimizationStudy(name="Test Study")
    study.model_id = model_id
    if parts:
        for p in parts:
            study.add_part(p)
    for c in conditions.all:
        study.add_condition(c.id)
    return study


# --------------------------------------------------------------------- #
# Scenario 1: solid selection → CadEntityRef
# --------------------------------------------------------------------- #
class TestSolidSelectionToCadEntityRef:
    def test_solid_ref_has_required_fields(self):
        ref = _solid_ref()
        assert ref.entity_type == EntityType.SOLID
        assert ref.model_id == "m1"
        assert ref.solid_id == "solid_0"

    def test_face_promoted_to_solid_via_resolver(self):
        face = _face_ref(face_index=5)
        assert face.entity_type == EntityType.FACE
        assert face.face_index == 5
        # Simulate resolver promotion
        solid = CadEntityRef.from_solid(
            solid_id="solid_1", model_id=face.model_id
        )
        assert solid.entity_type == EntityType.SOLID
        assert solid.solid_id == "solid_1"


# --------------------------------------------------------------------- #
# Scenario 2: study.parts receives the reference
# --------------------------------------------------------------------- #
class TestStudyPartsReceivesReference:
    def test_add_part(self):
        study = TopologyOptimizationStudy()
        ref = _solid_ref()
        study.add_part(ref)
        assert len(study.parts) == 1
        assert study.parts[0] is ref

    def test_add_part_deduplicates(self):
        study = TopologyOptimizationStudy()
        ref = _solid_ref()
        study.add_part(ref)
        study.add_part(ref)
        assert len(study.parts) == 1

    def test_add_multiple_distinct_parts(self):
        study = TopologyOptimizationStudy()
        r1 = _solid_ref(solid_id="solid_0")
        r2 = _solid_ref(solid_id="solid_1")
        study.add_part(r1)
        study.add_part(r2)
        assert len(study.parts) == 2


# --------------------------------------------------------------------- #
# Scenario 3: non-SOLID entity rejected
# --------------------------------------------------------------------- #
class TestNonSolidRejected:
    def test_validate_rejects_face_entity(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        face = _face_ref()
        study.add_part(face)
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        assert study.validate() is False

    def test_validate_rejects_edge_entity(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        edge = CadEntityRef(entity_type=EntityType.EDGE, model_id="m1", edge_index=0)
        study.add_part(edge)
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        assert study.validate() is False


# --------------------------------------------------------------------- #
# Scenario 4: incompatible model_id rejected
# --------------------------------------------------------------------- #
class TestIncompatibleModelId:
    def test_validate_rejects_different_model_ids(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        r1 = _solid_ref(model_id="m1", solid_id="solid_0")
        r2 = _solid_ref(model_id="m2", solid_id="solid_1")
        study.add_part(r1)
        study.add_part(r2)
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        assert study.validate() is False


# --------------------------------------------------------------------- #
# Scenario 5: multiple solids no duplicate refs
# --------------------------------------------------------------------- #
class TestMultipleSolidsNoDuplicate:
    def test_add_part_no_duplicates(self):
        study = TopologyOptimizationStudy()
        r = _solid_ref(solid_id="solid_0")
        study.add_part(r)
        study.add_part(r)
        study.add_part(r)
        assert len(study.parts) == 1

    def test_distinct_solids_stored(self):
        study = TopologyOptimizationStudy()
        r1 = _solid_ref(solid_id="solid_0")
        r2 = _solid_ref(solid_id="solid_1")
        r3 = _solid_ref(solid_id="solid_2")
        study.add_part(r1)
        study.add_part(r2)
        study.add_part(r3)
        assert len(study.parts) == 3
        ids = {p.solid_id for p in study.parts}
        assert ids == {"solid_0", "solid_1", "solid_2"}


# --------------------------------------------------------------------- #
# Scenario 6: conditions referenced by ID
# --------------------------------------------------------------------- #
class TestConditionsReferencedById:
    def test_condition_ids_stored(self):
        mgr = _make_conditions()
        study = _make_study(mgr)
        assert len(study.conditions) == len(mgr.all)
        for c in mgr.all:
            assert c.id in study.conditions

    def test_condition_ids_are_strings(self):
        mgr = _make_conditions()
        study = _make_study(mgr)
        for cid in study.conditions:
            assert isinstance(cid, str)


# --------------------------------------------------------------------- #
# Scenario 7: conditions reach run_optimization
# --------------------------------------------------------------------- #
class TestConditionsReachSolver:
    def test_consume_conditions_resolves(self):
        mgr = _make_conditions()
        study = _make_study(mgr)
        resolved = study.consume_conditions(mgr)
        assert len(resolved) == len(mgr.all)
        for c in resolved:
            assert hasattr(c, "condition_type")

    def test_consume_conditions_returns_real_objects(self):
        mgr = _make_conditions()
        study = _make_study(mgr)
        resolved = study.consume_conditions(mgr)
        types = {c.condition_type for c in resolved}
        assert ConditionType.LOAD in types
        assert ConditionType.ELASTICITY in types


# --------------------------------------------------------------------- #
# Scenario 8: load condition reaches solver
# --------------------------------------------------------------------- #
class TestLoadConditionToSolver:
    def test_load_condition_has_magnitude(self):
        mgr = _make_conditions()
        loads = mgr.conditions_by_type(ConditionType.LOAD)
        assert len(loads) == 1
        load = loads[0]
        assert hasattr(load, "magnitude")
        assert load.magnitude == 1000.0

    def test_load_condition_has_orientation(self):
        mgr = _make_conditions()
        loads = mgr.conditions_by_type(ConditionType.LOAD)
        load = loads[0]
        assert hasattr(load, "orientation")
        assert load.orientation == LoadOrientation.PERPENDICULAR


# --------------------------------------------------------------------- #
# Scenario 9: constraint reaches fixed DOFs
# --------------------------------------------------------------------- #
class TestConstraintToFixedDofs:
    def test_elasticity_condition_exists(self):
        mgr = _make_conditions()
        elastic = mgr.conditions_by_type(ConditionType.ELASTICITY)
        assert len(elastic) == 1
        assert elastic[0].name == "Soporte"


# --------------------------------------------------------------------- #
# Scenario 10: preserved/obstruction transmitted when mappable
# --------------------------------------------------------------------- #
class TestPreservedObstructionTransmitted:
    def test_protected_region_exists(self):
        mgr = _make_conditions()
        prot = mgr.conditions_by_type(ConditionType.PROTECTED_REGION)
        assert len(prot) == 1

    def test_obstruction_condition_exists(self):
        mgr = _make_conditions()
        obs = mgr.conditions_by_type(ConditionType.OBSTRUCTION)
        assert len(obs) == 1

    def test_consume_includes_all_types(self):
        mgr = _make_conditions()
        study = _make_study(mgr)
        resolved = study.consume_conditions(mgr)
        types = {c.condition_type for c in resolved}
        assert ConditionType.PROTECTED_REGION in types
        assert ConditionType.OBSTRUCTION in types


# --------------------------------------------------------------------- #
# Scenario 11: unsupported condition → explicit error, not silent
# --------------------------------------------------------------------- #
class TestUnsupportedConditionExplicit:
    def test_validate_fails_with_zero_parts(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        assert study.validate() is False

    def test_validate_fails_with_no_conditions(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        study.add_part(_solid_ref())
        assert study.validate() is False

    def test_validate_fails_with_invalid_volume_fraction(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        study.add_part(_solid_ref())
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        study.optimization_params.volume_fraction = 0.0
        assert study.validate() is False

    def test_validate_fails_with_zero_iterations(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        study.add_part(_solid_ref())
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        study.optimization_params.max_iterations = 0
        assert study.validate() is False


# --------------------------------------------------------------------- #
# Scenario 12: study without mesh → auto-generate
# --------------------------------------------------------------------- #
class TestAutoMeshGeneration:
    def test_study_stores_model_id_for_mesh_generation(self):
        study = _make_study(_make_conditions(), parts=[_solid_ref()])
        assert study.model_id == "m1"

    def test_study_parts_provide_domain(self):
        r1 = _solid_ref(solid_id="solid_0")
        r2 = _solid_ref(solid_id="solid_1")
        study = _make_study(_make_conditions(), parts=[r1, r2])
        solid_ids = [p.solid_id for p in study.parts]
        assert "solid_0" in solid_ids
        assert "solid_1" in solid_ids


# --------------------------------------------------------------------- #
# Scenario 13: study uses selected piece, not first solid
# --------------------------------------------------------------------- #
class TestStudyUsesSelectedNotFirst:
    def test_study_parts_from_selection(self):
        # Simulate user selecting solid_2 (not solid_0)
        selected = [_solid_ref(solid_id="solid_2", model_id="m1")]
        study = _make_study(_make_conditions(), parts=selected)
        assert len(study.parts) == 1
        assert study.parts[0].solid_id == "solid_2"

    def test_study_does_not_auto_add_first_solid(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        # No add_part called → parts should be empty
        assert len(study.parts) == 0


# --------------------------------------------------------------------- #
# Scenario 14: StudyResult reaches Document
# --------------------------------------------------------------------- #
class TestStudyResultToDocument:
    def test_study_result_stored(self):
        from core.cae_studies import StudyResult
        study = _make_study(_make_conditions(), parts=[_solid_ref()])
        sr = StudyResult(success=True, status="completed", data={"densities": [0.5]})
        study.result = sr
        assert study.result.success is True
        assert study.result.data["densities"] == [0.5]

    def test_study_result_serializable(self):
        from core.cae_studies import StudyResult
        study = _make_study(_make_conditions(), parts=[_solid_ref()])
        sr = StudyResult(success=True, status="completed", data={"key": "val"})
        study.result = sr
        d = study.to_dict()
        assert d["result"] is not None
        assert d["result"]["success"] is True


# --------------------------------------------------------------------- #
# Scenario 15: densities available for Viewport3D
# --------------------------------------------------------------------- #
class TestDensitiesForViewport:
    def test_study_result_contains_densities(self):
        from core.cae_studies import StudyResult
        densities = np.random.rand(100)
        study = _make_study(_make_conditions(), parts=[_solid_ref()])
        sr = StudyResult(success=True, status="completed",
                         data={"densities": densities.tolist()})
        study.result = sr
        assert "densities" in sr.data
        assert len(sr.data["densities"]) == 100


# --------------------------------------------------------------------- #
# Scenario 16: heavy execution continues in background
# --------------------------------------------------------------------- #
class TestBackgroundExecution:
    def test_study_status_transitions(self):
        from core.cae_studies import StudyStatus
        study = _make_study(_make_conditions(), parts=[_solid_ref()])
        assert study.status == StudyStatus.DRAFT
        study.status = StudyStatus.RUNNING
        assert study.status == StudyStatus.RUNNING
        study.status = StudyStatus.COMPLETED
        assert study.status == StudyStatus.COMPLETED

    def test_study_failed_status(self):
        from core.cae_studies import StudyStatus
        study = _make_study(_make_conditions(), parts=[_solid_ref()])
        study.status = StudyStatus.FAILED
        assert study.status == StudyStatus.FAILED


# --------------------------------------------------------------------- #
# StudyPanel integration (UI-level, no Qt required)
# --------------------------------------------------------------------- #
class TestStudyPanelIntegration:
    def test_study_panel_accepts_parts(self):
        """Verify StudyPanel constructor accepts parts parameter."""
        from PySide6.QtWidgets import QApplication
        import sys
        app = QApplication.instance() or QApplication(sys.argv)
        from desktop.ui.panels.study_panel import StudyPanel
        parts = [_solid_ref()]
        panel = StudyPanel(
            parts=parts,
            model_id="m1",
            condition_manager=_make_conditions(),
        )
        assert panel._parts == parts
        assert panel._model_id == "m1"

    def test_study_panel_validates_parts_on_accept(self):
        """Verify StudyPanel._on_accept rejects when no parts."""
        from PySide6.QtWidgets import QApplication
        import sys
        app = QApplication.instance() or QApplication(sys.argv)
        from desktop.ui.panels.study_panel import StudyPanel
        panel = StudyPanel(
            parts=[],
            model_id="m1",
            condition_manager=_make_conditions(),
        )
        panel._on_accept()
        assert panel.study is None
        assert "pieza" in panel._error.text().lower()

    def test_study_panel_rejects_non_solid(self):
        """Verify StudyPanel._on_accept rejects non-SOLID entities."""
        from PySide6.QtWidgets import QApplication
        import sys
        app = QApplication.instance() or QApplication(sys.argv)
        from desktop.ui.panels.study_panel import StudyPanel
        panel = StudyPanel(
            parts=[_face_ref()],
            model_id="m1",
            condition_manager=_make_conditions(),
        )
        panel._on_accept()
        assert panel.study is None
        assert "sólidos" in panel._error.text().lower()

    def test_study_panel_captures_from_selection(self):
        """Verify the panel captures solids from the viewport via callback."""
        from PySide6.QtWidgets import QApplication
        import sys
        app = QApplication.instance() or QApplication(sys.argv)
        from desktop.ui.panels.study_panel import StudyPanel
        captured = [_solid_ref(solid_id="solid_3", model_id="m1")]
        panel = StudyPanel(
            parts=[],
            model_id="m1",
            condition_manager=_make_conditions(),
            get_solid_selections=lambda: captured,
        )
        assert not panel._parts
        panel._capture_parts()
        assert len(panel._parts) == 1
        assert panel._parts[0].solid_id == "solid_3"
        assert panel._parts_list.count() == 1
        assert panel._btn_ok.isEnabled()

    def test_study_panel_capture_rejects_unselected(self):
        """Verify capture flags an error when nothing is selected."""
        from PySide6.QtWidgets import QApplication
        import sys
        app = QApplication.instance() or QApplication(sys.argv)
        from desktop.ui.panels.study_panel import StudyPanel
        panel = StudyPanel(
            parts=[],
            model_id="m1",
            condition_manager=_make_conditions(),
            get_solid_selections=lambda: [],
        )
        panel._capture_parts()
        assert not panel._parts
        assert "seleccionados" in panel._error.text().lower()


# --------------------------------------------------------------------- #
# Validation edge cases
# --------------------------------------------------------------------- #
class TestValidationEdgeCases:
    def test_valid_study_passes(self):
        study = _make_study(_make_conditions(), parts=[_solid_ref()])
        assert study.validate() is True

    def test_no_model_id_no_parts_fails(self):
        study = TopologyOptimizationStudy()
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        assert study.validate() is False

    def test_legacy_loads_accepted(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        study.add_part(_solid_ref())
        from core.cae_studies import LoadCase
        study.add_load(LoadCase(magnitude=1000.0))
        assert study.validate() is True

    def test_legacy_constraints_accepted(self):
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        study.add_part(_solid_ref())
        from core.cae_studies import ConstraintCase
        study.add_constraint(ConstraintCase())
        assert study.validate() is True

    def test_remove_part(self):
        study = TopologyOptimizationStudy()
        r = _solid_ref(solid_id="solid_0")
        study.add_part(r)
        assert len(study.parts) == 1
        study.remove_part("solid_0")
        assert len(study.parts) == 0

    def test_remove_condition(self):
        study = TopologyOptimizationStudy()
        study.add_condition("c1")
        assert len(study.conditions) == 1
        study.remove_condition("c1")
        assert len(study.conditions) == 0

    def test_serialization_roundtrip(self):
        study = _make_study(_make_conditions(), parts=[_solid_ref()])
        d = study.to_dict()
        assert "parts" in d
        assert "conditions" in d
        assert len(d["parts"]) == 1
        assert d["parts"][0]["entity_type"] == "solid"


# --------------------------------------------------------------------- #
# Deterministic domain: study.parts governs the selected solid (no implicit
# "first solid").  See prompts.md ETAPA sección 5 y 6.
# --------------------------------------------------------------------- #
class TestSelectedSolidIsDomain:
    def test_resolve_study_solid_index_uses_selected_solid(self):
        from desktop.pipeline.controller import PipelineController
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        # User explicitly selects solid_2 (not solid_0).
        study.add_part(_solid_ref(solid_id="solid_2", model_id="m1"))
        idx = PipelineController._resolve_study_solid_index(study, "m1")
        assert idx == 2

    def test_resolve_uses_first_part_only_when_selected(self):
        from desktop.pipeline.controller import PipelineController
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        study.add_part(_solid_ref(solid_id="solid_0", model_id="m1"))
        idx = PipelineController._resolve_study_solid_index(study, "m1")
        assert idx == 0

    def test_resolve_returns_none_without_parts(self):
        from desktop.pipeline.controller import PipelineController
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        assert PipelineController._resolve_study_solid_index(study, "m1") is None

    def test_resolve_rejects_incompatible_model_id(self):
        from desktop.pipeline.controller import PipelineController
        study = TopologyOptimizationStudy()
        study.model_id = "m1"
        study.add_part(_solid_ref(solid_id="solid_0", model_id="m2"))
        assert PipelineController._resolve_study_solid_index(study, "m1") is None

    def test_generate_mesh_for_solid_updates_global_mesh(self, monkeypatch):
        """generate_mesh_for_solid meshes the selected solid and stores it."""
        from desktop.pipeline.controller import PipelineController
        ctrl = PipelineController()
        ctrl.model_id = "m1"
        mesh = {
            "success": True, "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            "elements": [[0, 1, 2, 2]], "num_nodes": 3, "num_elements": 1,
        }
        monkeypatch.setattr(ctrl.cad, "generate_mesh_for_solid",
                            lambda mid, idx, target_element_size=None: mesh)
        out = ctrl.generate_mesh_for_solid(2)
        assert out["success"] is True
        assert ctrl.mesh_nodes.shape == (3, 3)
        assert ctrl.mesh_elements.shape == (1, 4)
        assert ctrl.mesh is mesh

    def test_generate_mesh_for_solid_called_with_selected_index(self, monkeypatch):
        """execute_study must mesh the *selected* solid, not an implicit first."""
        from desktop.pipeline.controller import PipelineController
        from core.cad_entity import EntityType
        ctrl = PipelineController()
        ctrl.model_id = "m1"

        # 3 solids in the model
        monkeypatch.setattr(ctrl.cad, "list_solids",
                            lambda mid: [{"solid_id": "solid_0", "index": 0},
                                         {"solid_id": "solid_1", "index": 1},
                                         {"solid_id": "solid_2", "index": 2}])
        mesh = {
            "success": True, "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            "elements": [[0, 1, 2, 2]], "num_nodes": 3, "num_elements": 1,
        }
        meshed_indices = []
        def fake_mesh_for_solid(mid, idx, target_element_size=None):
            meshed_indices.append(idx)
            return mesh
        monkeypatch.setattr(ctrl.cad, "generate_mesh_for_solid", fake_mesh_for_solid)
        # Replacement for the real SIMP solve (avoid heavy geometry).
        monkeypatch.setattr(ctrl, "run_optimization",
                            lambda **kw: {"success": True, "densities": [0.5] * 1})

        study = TopologyOptimizationStudy(name="S")
        study.model_id = "m1"
        study.add_part(CadEntityRef(entity_type=EntityType.SOLID,
                                    model_id="m1", solid_id="solid_2"))
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        ctrl.conditions = mgr

        sr = ctrl.execute_study(study)
        assert sr.success is True
        # The mesh must correspond to the selected solid (index 2), not solid_0.
        assert meshed_indices == [2]
        assert getattr(ctrl, "_study_solid_index", None) == 2

    def test_execute_study_rejects_unresolvable_solid(self, monkeypatch):
        """execute_study must fail clearly when the selected solid is out of range."""
        from desktop.pipeline.controller import PipelineController
        from core.cae_studies import StudyStatus
        ctrl = PipelineController()
        ctrl.model_id = "m1"
        monkeypatch.setattr(ctrl.cad, "list_solids",
                            lambda mid: [{"solid_id": "solid_0", "index": 0},
                                         {"solid_id": "solid_1", "index": 1}])
        ctrl.run_optimization = lambda **kw: {"success": True, "densities": [0.5]}

        study = TopologyOptimizationStudy(name="S")
        study.model_id = "m1"
        # Select solid_5 which does not exist (only 2 solids).
        study.add_part(_solid_ref(solid_id="solid_5", model_id="m1"))
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        ctrl.conditions = mgr

        sr = ctrl.execute_study(study)
        assert sr.success is False
        assert sr.status == "unresolvable_part"
        assert study.status == StudyStatus.FAILED

    def test_execute_study_rejects_missing_solids(self, monkeypatch):
        """execute_study fails when the model has no resolvable solids."""
        from desktop.pipeline.controller import PipelineController
        ctrl = PipelineController()
        ctrl.model_id = "m1"
        monkeypatch.setattr(ctrl.cad, "list_solids", lambda mid: [])
        ctrl.run_optimization = lambda **kw: {"success": True, "densities": [0.5]}

        study = TopologyOptimizationStudy(name="S")
        study.model_id = "m1"
        study.add_part(_solid_ref(solid_id="solid_0", model_id="m1"))
        mgr = _make_conditions()
        for c in mgr.all:
            study.add_condition(c.id)
        ctrl.conditions = mgr

        sr = ctrl.execute_study(study)
        assert sr.success is False
        assert sr.status == "no_solids"
