"""Validation tests for the extensible "Pruebas" base category.

Per spec, only the extensible base category is implemented (no concrete test
types yet).  These tests verify:

1.  The base ``TestCase`` / ``TestSuite`` / ``TestRegistry`` framework works.
2.  A future concrete test type can be registered and created dynamically.
3.  Running a suite produces per-case results without interfering with the
    CAD/history systems (Pruebas is a separate category, not a Feature).
"""

import pytest

from core.testing import (
    DEFAULT_TEST_REGISTRY,
    TestCase,
    TestKind,
    TestRegistry,
    TestResult,
    TestStatus,
    TestSuite,
)


class _DummyCase(TestCase):
    kind = TestKind.GENERIC
    display_name = "Caso dummy"

    def __init__(self, name: str = "dummy", should_pass: bool = True) -> None:
        super().__init__(name=name)
        self.should_pass = should_pass

    def run(self) -> TestResult:
        if self.should_pass:
            return TestResult(success=True, status=TestStatus.PASSED.value, message=self.name)
        return TestResult(success=False, status=TestStatus.FAILED.value,
                          message=self.name, error="forced failure")


def test_base_case_run():
    case = _DummyCase("caso-ok")
    res = case.run()
    assert res.success
    assert res.status == TestStatus.PASSED.value


def test_base_case_failure():
    case = _DummyCase("caso-fail", should_pass=False)
    res = case.run()
    assert not res.success
    assert res.status == TestStatus.FAILED.value


def test_suite_runs_all_and_reports():
    suite = TestSuite(name="Pruebas de geometría")
    suite.add_case(_DummyCase("a"))
    suite.add_case(_DummyCase("b", should_pass=False))
    results = suite.run_all()
    assert len(results) == 2
    assert results[0].success
    assert not results[1].success
    assert suite.count == 2


def test_suite_captures_exceptions():
    class _Boom(TestCase):
        kind = TestKind.GENERIC
        display_name = "boom"

        def run(self) -> TestResult:
            raise RuntimeError("exploded")

    suite = TestSuite()
    suite.add_case(_Boom())
    results = suite.run_all()
    assert len(results) == 1
    assert not results[0].success
    assert "exploded" in (results[0].error or "")


def test_registry_register_and_create():
    reg = TestRegistry()
    reg.register("dummy", lambda **kw: _DummyCase(**kw))
    case = reg.create("dummy", name="from-registry")
    assert case is not None
    assert case.name == "from-registry"
    assert reg.create("missing") is None
    assert "dummy" in reg.available()


def test_default_registry_exists_and_extensible():
    assert isinstance(DEFAULT_TEST_REGISTRY, TestRegistry)


def test_pruebas_do_not_create_parallel_systems():
    """Creating a suite must not touch the feature history / document / selection."""
    from desktop.pipeline.controller import PipelineController
    from core.document import Document

    ctrl = PipelineController()
    assert len(ctrl.feature_history.features) == 0
    assert isinstance(ctrl.document, Document)

    suite = TestSuite(name="Pruebas")
    suite.run_all()
    # The CAD/history systems stay untouched by the Pruebas category.
    assert len(ctrl.feature_history.features) == 0