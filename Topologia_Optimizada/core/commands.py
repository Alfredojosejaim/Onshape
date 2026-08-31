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

from core.cad_entity import CadEntityRef, EntityType


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

    A boolean command distinguishes between a **target** body (the piece to be
    modified) and one or more **tool** bodies (the pieces used to perform the
    operation).  The UI builds a ``BooleanCommand`` by selecting the target and
    the tools from the viewport (reusing the existing ``SelectionManager``).

    The actual CadQuery execution is delegated to the pipeline layer via
    ``CommandResult`` returned by ``execute()``.

    Representation
    --------------
    - ``selection[0]`` (or the ``target`` parameter) is the target body.
    - the remaining selections (or the ``tools`` parameter) are the tool bodies.
    - ``parameters["operation"]``  union | difference | intersection
    - ``parameters["keep_tools"]`` whether the tool bodies stay after the op.
    """

    command_type = CommandType.BOOLEAN
    display_name = "Boolean"
    description = "Union, difference, or intersection of solid bodies"

    def __init__(self) -> None:
        super().__init__()
        self._target_ref: Optional[CadEntityRef] = None
        self._tool_refs: List[CadEntityRef] = []

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
            CommandParameter(
                name="target", label="Target body", param_type="selection",
                required=True, tooltip="The body to be modified",
            ),
            CommandParameter(
                name="tools", label="Tool bodies", param_type="selection",
                required=True, tooltip="The bodies used to perform the operation",
            ),
        ]

    # ------------------------------------------------------------------ #
    # Target / tool configuration
    # ------------------------------------------------------------------ #
    def set_target(self, ref: Optional[CadEntityRef]) -> None:
        """Set the target body reference (the piece to be modified)."""
        self._target_ref = ref
        # Keep parameters in sync so the base validate() passes the required
        # 'target' check.
        self.parameters["target"] = ref.to_dict() if ref is not None else None

    def add_tool(self, ref: CadEntityRef) -> None:
        """Add a tool body reference (the piece used for the operation)."""
        if ref not in self._tool_refs:
            self._tool_refs.append(ref)
        self.parameters["tools"] = [t.to_dict() for t in self._tool_refs]

    def clear_tools(self) -> None:
        self._tool_refs.clear()
        self.parameters["tools"] = []

    @property
    def target(self) -> Optional[CadEntityRef]:
        return self._target_ref

    @property
    def tools(self) -> List[CadEntityRef]:
        return list(self._tool_refs)

    def target_body_id(self) -> Optional[str]:
        """Return the target body's solid id (``solid_<n>``) or its model id."""
        if self._target_ref is None:
            return None
        return self._target_ref.solid_id or self._target_ref.model_id

    def tool_body_ids(self) -> List[str]:
        """Return the tool body solid ids (falls back to model ids)."""
        ids = []
        for ref in self._tool_refs:
            sid = ref.solid_id if ref.entity_type == EntityType.SOLID else None
            ids.append(sid or ref.model_id)
        return ids

    def set_parameter(self, name: str, value: Any) -> None:
        """Extend the base setter to also handle target / tools shorthand."""
        if name == "target":
            if isinstance(value, CadEntityRef):
                self.set_target(value)
            elif isinstance(value, str):
                self.set_target(CadEntityRef.from_solid(value))
            return
        if name == "tools":
            if isinstance(value, (list, tuple)):
                for v in value:
                    if isinstance(v, CadEntityRef):
                        self.add_tool(v)
                    elif isinstance(v, str):
                        self.add_tool(CadEntityRef.from_solid(v))
            elif isinstance(value, CadEntityRef):
                self.add_tool(value)
            return
        if name == "operation":
            if isinstance(value, BooleanOperation):
                value = value.value
        super().set_parameter(name, value)

    def add_selection(self, entity: CadEntityRef) -> None:
        """Keep selections in sync with the explicit target/tool model.

        The first added selection is treated as the target; any subsequent
        ones as tools.  This keeps the existing ``selections`` list coherent
        with the dedicated target/tools fields.
        """
        super().add_selection(entity)
        if self._target_ref is None:
            self._target_ref = entity
        else:
            self.add_tool(entity)

    def validate(self) -> bool:
        super().validate()
        if self._target_ref is None:
            self._add_error("A target body must be selected.")
        if not self._tool_refs:
            self._add_error("At least one tool body must be selected.")
        op = self.parameters.get("operation")
        if op and op not in [e.value for e in BooleanOperation]:
            self._add_error(f"Invalid boolean operation: {op}")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        """The pipeline layer performs the CadQuery boolean operation.

        ``execute_command`` in the pipeline controller interprets the target /
        tools and produces the result.  If the command is not valid, a failing
        ``CommandResult`` is returned so the UI never mutates the model.
        """
        if not self.validate():
            return CommandResult(
                success=False,
                error_message="; ".join(self._validation_errors),
            )
        return CommandResult(
            success=True,
            data={"status": "ready_for_pipeline_execution", "command": self.to_dict()},
        )

    # Do NOT override to_dict: the base implementation already serialises
    # parameters + selections; target/tools are derivable from them.


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
