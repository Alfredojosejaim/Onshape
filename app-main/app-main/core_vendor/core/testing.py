"""Pruebas - extensible base category for engineering validation tests.

Only the *base category* is defined here (per spec: concrete test types will be
defined later).  The architecture separates:

- ``TestCase``   the unit of work (name + kind + ``run()``)
- ``TestResult`` the outcome of a run
- ``TestSuite``  an ordered collection of cases
- ``TestRegistry`` where future test types register themselves

No concrete test kinds are implemented yet; they plug in via
:meth:`TestRegistry.register`.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

    __test__ = False


class TestKind(str, Enum):
    """Discriminator for concrete test types (extensible)."""
    GENERIC = "generic"

    __test__ = False


@dataclass
class TestResult:
    """Outcome of a single test case run."""
    success: bool
    status: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    __test__ = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }


class TestCase(ABC):
    """Abstract base for a single validation test case."""

    kind: TestKind = TestKind.GENERIC
    display_name: str = "Caso de prueba"
    __test__ = False

    def __init__(self, name: str = "") -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name or self.display_name

    @abstractmethod
    def run(self) -> TestResult:
        """Execute the test case and return a TestResult."""


class TestSuite:
    """Ordered collection of test cases sharing a category (e.g. a CAD/CAE
    validation suite).  Concrete test cases are added later."""

    __test__ = False

    def __init__(self, name: str = "Pruebas", description: str = "") -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.cases: List[TestCase] = []

    def add_case(self, case: TestCase) -> None:
        self.cases.append(case)

    def run_all(self, progress_cb: Optional[Callable[[TestResult], None]] = None) -> List[TestResult]:
        results: List[TestResult] = []
        for case in self.cases:
            try:
                result = case.run()
            except Exception as exc:
                result = TestResult(success=False, status=TestStatus.FAILED.value,
                                    message=case.name, error=str(exc))
            results.append(result)
            if progress_cb is not None:
                progress_cb(result)
        return results

    @property
    def count(self) -> int:
        return len(self.cases)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "count": self.count,
            "cases": [{"id": c.id, "name": c.name, "kind": c.kind.value}
                      for c in self.cases],
        }


class TestRegistry:
    """Registry where future concrete test types register their factories."""

    __test__ = False

    def __init__(self) -> None:
        self._factories: Dict[str, Callable[..., TestCase]] = {}

    def register(self, kind: str, factory: Callable[..., TestCase]) -> None:
        self._factories[kind] = factory

    def create(self, kind: str, **kw: Any) -> Optional[TestCase]:
        factory = self._factories.get(kind)
        return factory(**kw) if factory else None

    def available(self) -> List[str]:
        return sorted(self._factories)


DEFAULT_TEST_REGISTRY = TestRegistry()