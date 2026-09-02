"""Tests of the Thermal/Modal study scaffolding.

Covers the *data model and validation* that are already in place for future
solver integration: material thermal properties, thermal boundary conditions,
modal parameters, validation messages, and the controller's explicit
``not_implemented`` / ``validation_failed`` dispatch. The real thermal/eigen
solvers are intentionally NOT exercised here (they are not integrated yet).
"""

import pytest

from core.cae_studies import (
    StudyStatus,
    StudyNotImplementedError,
    ThermalAnalysis,
    ThermalBoundary,
    ThermalBoundaryType,
    ModalAnalysis,
    ModalParameters,
)
from core.materials import Material, STANDARD_MATERIALS


# ====================================================================== #
# Material thermal properties
# ====================================================================== #

def test_material_backward_compatible_defaults_none():
    m = STANDARD_MATERIALS["steel"]
    assert m.thermal_conductivity is None
    assert m.specific_heat is None
    assert m.thermal_expansion is None
    assert m.has_thermal_properties is False
    d = m.to_dict()
    assert "thermal_conductivity" not in d


def test_with_thermal_properties_promotes_material():
    m = STANDARD_MATERIALS["steel"].with_thermal_properties(
        thermal_conductivity=45.0, specific_heat=490.0, thermal_expansion=1.2e-5,
    )
    assert m.has_thermal_properties is True
    assert m.thermal_conductivity == 45.0
    # original preset unchanged
    assert STANDARD_MATERIALS["steel"].has_thermal_properties is False
    d = m.to_dict()
    assert d["thermal_conductivity"] == 45.0
    assert d["specific_heat"] == 490.0


def test_material_rejects_invalid_thermal_values():
    with pytest.raises(ValueError):
        STANDARD_MATERIALS["steel"].with_thermal_properties(thermal_conductivity=0)
    with pytest.raises(ValueError):
        STANDARD_MATERIALS["steel"].with_thermal_properties(
            thermal_conductivity=45.0, specific_heat=-1.0,
        )


# ====================================================================== #
# Thermal study: config + validation
# ====================================================================== #

def _thermal_study(valid=True):
    s = ThermalAnalysis()
    s.model_id = "m1"
    if valid:
        s.material = STANDARD_MATERIALS["steel"].with_thermal_properties(
            thermal_conductivity=45.0, specific_heat=490.0,
        )
        s.add_thermal_boundary(
            ThermalBoundary(name="Fijada", boundary_type=ThermalBoundaryType.TEMPERATURE,
                            magnitude=100.0)
        )
    return s


def test_thermal_requires_model():
    s = ThermalAnalysis()
    s.material = STANDARD_MATERIALS["steel"].with_thermal_properties(thermal_conductivity=45.0)
    s.add_thermal_boundary(ThermalBoundary())
    assert s.validate() is False
    assert "model" in s.validate_with_message()


def test_thermal_requires_thermal_material():
    s = ThermalAnalysis()
    s.model_id = "m1"  # material has NO thermal conductivity
    s.add_thermal_boundary(ThermalBoundary())
    assert s.validate() is False
    msg = s.validate_with_message()
    assert "conductividad" in msg


def test_thermal_requires_boundary_conditions():
    s = ThermalAnalysis()
    s.model_id = "m1"
    s.material = STANDARD_MATERIALS["steel"].with_thermal_properties(thermal_conductivity=45.0)
    assert s.validate() is False
    assert "condición" in s.validate_with_message()


def test_thermal_valid_config_ok():
    s = _thermal_study(valid=True)
    assert s.validate() is True
    assert s.validate_with_message() is None
    d = s.to_dict()
    assert d["study_type"] == "thermal"
    assert len(d["thermal_boundaries"]) == 1
    assert d["thermal_boundaries"][0]["boundary_type"] == "temperature"


def test_thermal_execute_raises_not_implemented():
    s = _thermal_study(valid=True)
    with pytest.raises(StudyNotImplementedError):
        s.execute()


def test_thermal_validation_failure_returns_result_not_raise():
    s = ThermalAnalysis()
    res = s.execute()  # invalid -> returns failure result, does not raise
    assert res.success is False
    assert res.status == "validation_failed"
    assert s.status == StudyStatus.FAILED


def test_thermal_convection_rejects_negative_h():
    with pytest.raises(ValueError):
        ThermalBoundary(boundary_type=ThermalBoundaryType.CONVECTION, h=-1.0, T_inf=20.0)


# ====================================================================== #
# Modal study: config + validation
# ====================================================================== #

def test_modal_parameters_validation():
    m = ModalParameters(mode_count=5)
    assert m.mode_count == 5
    with pytest.raises(ValueError):
        ModalParameters(mode_count=0)
    with pytest.raises(ValueError):
        ModalParameters(mode_count=3, frequency_min=10.0, frequency_max=5.0)


def test_modal_requires_model():
    s = ModalAnalysis()
    s.modal = ModalParameters(mode_count=5)
    assert s.validate() is False
    assert "model" in s.validate_with_message()


def test_modal_requires_constraint():
    s = ModalAnalysis()
    s.model_id = "m1"
    s.modal = ModalParameters(mode_count=5)
    assert s.validate() is False
    assert "soporte" in s.validate_with_message()


def test_modal_default_mode_count():
    s = ModalAnalysis()
    assert s.modal.mode_count == 5
    assert s.to_dict()["modal"]["mode_count"] == 5


def test_modal_valid_config_ok():
    from core.cae_studies import ConstraintCase
    s = ModalAnalysis(mode_count=8)
    s.model_id = "m1"
    s.add_constraint(ConstraintCase(name="Soporte", constraint_type="fixed"))
    assert s.validate() is True
    assert s.validate_with_message() is None


def test_modal_execute_raises_not_implemented():
    from core.cae_studies import ConstraintCase
    s = ModalAnalysis(mode_count=8)
    s.model_id = "m1"
    s.add_constraint(ConstraintCase(name="Soporte", constraint_type="fixed"))
    with pytest.raises(StudyNotImplementedError):
        s.execute()


# ====================================================================== #
# Controller dispatch (thermal / modal)
# ====================================================================== #

def _bare_controller():
    from desktop.pipeline.controller import PipelineController
    c = PipelineController.__new__(PipelineController)
    c.constraints = []
    c.forces = []
    c.model_id = None
    c.mesh = None
    c.mesh_nodes = None
    c.mesh_elements = None
    c._studies = {}

    class FakeDoc:
        def add_study(self, s):
            pass

        def add_result(self, id_, r):
            pass

    c.document = FakeDoc()
    return c


def test_controller_thermal_valid_reports_not_implemented():
    c = _bare_controller()
    from core.cae_studies import ConstraintCase  # noqa: F401
    s = _thermal_study(valid=True)
    res = c.execute_study(s)
    assert res.success is False
    assert res.status == "not_implemented"
    assert "thermal" in res.error_message.lower()


def test_controller_thermal_invalid_reports_validation_failed():
    c = _bare_controller()
    s = ThermalAnalysis()
    s.model_id = "m1"  # no thermal material, no boundaries
    res = c.execute_study(s)
    assert res.success is False
    assert res.status == "validation_failed"
    assert "conductividad" in res.error_message


def test_controller_modal_valid_reports_not_implemented():
    from core.cae_studies import ConstraintCase
    c = _bare_controller()
    s = ModalAnalysis(mode_count=8)
    s.model_id = "m1"
    s.add_constraint(ConstraintCase(name="Soporte", constraint_type="fixed"))
    res = c.execute_study(s)
    assert res.success is False
    assert res.status == "not_implemented"
    assert "modal" in res.error_message.lower()


def test_controller_modal_missing_constraint_reports_validation_failed():
    c = _bare_controller()
    s = ModalAnalysis(mode_count=8)
    s.model_id = "m1"
    res = c.execute_study(s)
    assert res.success is False
    assert res.status == "validation_failed"
    assert "soporte" in res.error_message
