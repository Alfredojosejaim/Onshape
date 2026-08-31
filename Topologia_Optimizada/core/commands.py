"""Command pattern for CAD operations.

A Command encapsulates a complete CAD operation: parameters, selection,
validation, execution, and result.  The UI builds a Command, the pipeline
validates and executes it, and the result is recorded as a Feature in the
history.

Conceptual structure:

    Command
    ├── parameters
    ├── selections
    ├── validate() -> bool
    └── execute() -> FeatureResult

This separation ensures:
- The UI does NOT contain geometric logic.
- Commands are testable in isolation.
- Commands can be serialised for undo/redo or recorded in the feature history.
- Future CAD operations (boolean, fillet, chamfer, shell, etc.) follow the
  same pattern.

The module also provides a CommandRegistry that maps command type strings
to their Command classes, enabling the UI to discover available operations
dynamically.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from core.cad_entity import CadEntityRef


class CommandType(str, Enum):
    BOOLEAN = "boolean"
    TRANSFORM = "transform"
    MIRROR = "mirror"
    PATTERN = "pattern"
    FILLET = "fillet"
    CHAMFER = "chamfer"
    SHELL = "shell"
    IMPORT_STEP = "import_step"
    MEASUREMENT = "measurement"
    CUSTOM = "custom"


@dataclass
class CommandParameter:
    """Describes a single parameter of a command (for UI generation)."""
    name: str
    label: str
    param_type: str = "float"  # float | int | str | bool | enum | selection
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[str]] = None
    required: bool = True
    tooltip: str = ""


@dataclass
class CommandResult:
    """Outcome of a command execution."""
    success: bool
    feature_id: Optional[str] = None
    result_model_id: Optional[str] = None
    error_message: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class Command(ABC):
    """Abstract base class for all CAD commands.

    Subclasses must implement:
    - ``command_type``       class-level CommandType
    - ``display_name``       human-readable name
    - ``parameters_spec``    list of CommandParameter descriptors
    - ``validate()``         check preconditions
    - ``execute()``          perform the operation, return CommandResult
    """

    command_type: CommandType = CommandType.CUSTOM
    display_name: str = "Custom Command"
    description: str = ""

    def __init__(self) -> None:
        self.id: str = str(uuid.uuid4())
        self.parameters: Dict[str, Any] = {}
        self.selections: List[CadEntityRef] = []
        self._validation_errors: List[str] = []

    @property
    @abstractmethod
    def parameters_spec(self) -> List[CommandParameter]:
        """Return the list of parameter descriptors for this command."""

    def set_parameter(self, name: str, value: Any) -> None:
        self.parameters[name] = value

    def get_parameter(self, name: str, default: Any = None) -> Any:
        return self.parameters.get(name, default)

    def add_selection(self, entity: CadEntityRef) -> None:
        self.selections.append(entity)

    def clear_selections(self) -> None:
        self.selections.clear()

    def validate(self) -> bool:
        """Validate command parameters and selections.

        Returns True if the command is ready to execute.
        Subclasses should override to add specific checks and call
        ``self._add_error()`` for each problem found.
        """
        self._validation_errors.clear()
        spec = {p.name: p for p in self.parameters_spec}
        for name, param in spec.items():
            if param.required and name not in self.parameters:
                self._add_error(f"Required parameter '{param.label}' is missing.")
            if name in self.parameters:
                val = self.parameters[name]
                if param.min_value is not None and val < param.min_value:
                    self._add_error(f"{param.label} must be >= {param.min_value}")
                if param.max_value is not None and val > param.max_value:
                    self._add_error(f"{param.label} must be <= {param.max_value}")
        return len(self._validation_errors) == 0

    @abstractmethod
    def execute(self) -> CommandResult:
        """Execute the command.  Must be called only after validate() returns True."""

    @property
    def validation_errors(self) -> List[str]:
        return list(self._validation_errors)

    def _add_error(self, msg: str) -> None:
        self._validation_errors.append(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "command_type": self.command_type.value,
            "display_name": self.display_name,
            "parameters": dict(self.parameters),
            "selections": [s.to_dict() for s in self.selections],
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, type={self.command_type.value!r})"


# ====================================================================== #
# Boolean Command (prepared, not fully executed in this phase)
# ====================================================================== #

class BooleanOperation(str, Enum):
    UNION = "union"
    DIFFERENCE = "difference"
    INTERSECTION = "intersection"


class BooleanCommand(Command):
    """Boolean operation between solid bodies.

    Architecture-ready: validates parameters and selections but the actual
    CadQuery boolean execution is delegated to the pipeline layer.
    """

    command_type = CommandType.BOOLEAN
    display_name = "Boolean"
    description = "Union, difference, or intersection of solid bodies"

    @property
    def parameters_spec(self) -> List[CommandParameter]:
        return [
            CommandParameter(
                name="operation", label="Operation", param_type="enum",
                options=[op.value for op in BooleanOperation],
                default=BooleanOperation.UNION.value,
                tooltip="Boolean operation type",
            ),
            CommandParameter(
                name="keep_tools", label="Keep tool bodies", param_type="bool",
                default=False,
                tooltip="Whether to keep the tool bodies after the operation",
            ),
        ]

    def validate(self) -> bool:
        super().validate()
        if not self.selections:
            self._add_error("At least one tool body must be selected.")
        op = self.parameters.get("operation")
        if op and op not in [e.value for e in BooleanOperation]:
            self._add_error(f"Invalid boolean operation: {op}")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        """Placeholder: actual execution requires pipeline integration."""
        if not self.validate():
            return CommandResult(
                success=False,
                error_message="; ".join(self._validation_errors),
            )
        # The pipeline layer will perform:
        #   cadquery boolean operation using the target and tool shapes
        # For now, return a pending result that the controller can interpret.
        return CommandResult(
            success=True,
            data={"status": "pending_pipeline_execution", "command": self.to_dict()},
        )


# ====================================================================== #
# Command Registry
# ====================================================================== #

class CommandRegistry:
    """Maps command type strings to their Command classes.

    The UI can query the registry to discover which commands are available
    and generate parameter forms dynamically.
    """

    def __init__(self) -> None:
        self._commands: Dict[str, Type[Command]] = {}

    def register(self, cmd_class: Type[Command]) -> None:
        key = cmd_class.command_type.value
        self._commands[key] = cmd_class

    def get(self, command_type: str) -> Optional[Type[Command]]:
        return self._commands.get(command_type)

    def available(self) -> List[Dict[str, str]]:
        return [
            {"type": k, "name": cls.display_name, "description": cls.description}
            for k, cls in self._commands.items()
        ]

    def create(self, command_type: str) -> Optional[Command]:
        cls = self._commands.get(command_type)
        return cls() if cls else None


# Default registry instance (populated at module level)
DEFAULT_REGISTRY = CommandRegistry()
DEFAULT_REGISTRY.register(BooleanCommand)
