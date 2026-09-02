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
from core.conditions import (
    ElasticityCondition,
    LoadCondition,
    LoadOrientation,
    LoadSense,
    ObstructionCondition,
    ProtectedRegion,
    _faces_selection,
    _solids_selection,
)


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
    CONDITION_LOAD = "condition_load"
    CONDITION_ELASTICITY = "condition_elasticity"
    CONDITION_OBSTRUCTION = "condition_obstruction"
    CONDITION_PROTECTED_REGION = "condition_protected_region"
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
                if val is not None:
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
# Transform / Mirror / Pattern Commands
# ====================================================================== #

class TransformType(str, Enum):
    """Kind of transformation applied to a body."""
    TRANSLATE = "translate"
    ROTATE = "rotate"
    SCALE = "scale"


class TransformCommand(Command):
    """Move, rotate or scale a solid body.

    The operation is performed at the geometry layer (CadQuery) by the
    pipeline: ``TransformCommand`` only carries the parameters and the
    selected body (``parameters["target"]``, a ``CadEntityRef`` to a solid).

    Representation
    --------------
    - ``selections[0]`` (or ``parameters["target"]``) is the body to transform.
    - ``parameters["transform_type"]``  translate | rotate | scale
    - ``parameters["translation"]``    [dx, dy, dz] (translate)
    - ``parameters["rotation_axis"]``   [ax, ay, az] unit axis (rotate)
    - ``parameters["rotation_angle"]``  float degrees (rotate)
    - ``parameters["scale_factor"]``    float (scale)
    """

    command_type = CommandType.TRANSFORM
    display_name = "Transform"
    description = "Move, rotate or scale a solid body"

    def __init__(self) -> None:
        super().__init__()
        self._target_ref: Optional[CadEntityRef] = None

    @property
    def parameters_spec(self) -> List[CommandParameter]:
        return [
            CommandParameter(
                name="transform_type", label="Transformación", param_type="enum",
                options=[op.value for op in TransformType],
                default=TransformType.TRANSLATE.value,
                tooltip="Tipo de transformación",
            ),
            CommandParameter(
                name="translation", label="Traslación (x, y, z)", param_type="str",
                default="0, 0, 0", required=False,
                tooltip="Vector de traslación, p. ej. '10, 0, 0'",
            ),
            CommandParameter(
                name="rotation_axis", label="Eje de rotación (x, y, z)", param_type="str",
                default="0, 0, 1", required=False,
                tooltip="Eje de rotación normalizado",
            ),
            CommandParameter(
                name="rotation_angle", label="Ángulo de rotación (°)", param_type="float",
                default=0.0, required=False, tooltip="Ángulo de rotación en grados",
            ),
            CommandParameter(
                name="scale_factor", label="Factor de escala", param_type="float",
                default=1.0, min_value=0.01, max_value=100.0, required=False,
                tooltip="Factor de escala (mayor que 0)",
            ),
            CommandParameter(
                name="target", label="Cuerpo", param_type="selection",
                required=True, tooltip="El cuerpo a transformar",
            ),
        ]

    def set_target(self, ref: Optional[CadEntityRef]) -> None:
        self._target_ref = ref
        self.parameters["target"] = ref.to_dict() if ref is not None else None

    @property
    def target(self) -> Optional[CadEntityRef]:
        return self._target_ref

    def target_body_id(self) -> Optional[str]:
        if self._target_ref is None:
            return None
        return self._target_ref.solid_id or self._target_ref.model_id

    def set_parameter(self, name: str, value: Any) -> None:
        if name == "target":
            if isinstance(value, CadEntityRef):
                self.set_target(value)
            elif isinstance(value, str):
                self.set_target(CadEntityRef.from_solid(value))
            return
        super().set_parameter(name, value)

    def add_selection(self, entity: CadEntityRef) -> None:
        super().add_selection(entity)
        if self._target_ref is None:
            self._target_ref = entity
            self.parameters["target"] = entity.to_dict()

    def validate(self) -> bool:
        super().validate()
        if self._target_ref is None:
            self._add_error("A body must be selected.")
        tt = self.parameters.get("transform_type")
        if tt and tt not in [e.value for e in TransformType]:
            self._add_error(f"Invalid transform type: {tt}")
        if tt == TransformType.SCALE.value:
            sf = self.parameters.get("scale_factor", 1.0)
            if sf is None or float(sf) <= 0:
                self._add_error("Scale factor must be greater than 0.")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        if not self.validate():
            return CommandResult(
                success=False,
                error_message="; ".join(self._validation_errors),
            )
        return CommandResult(
            success=True,
            data={"status": "ready_for_pipeline_execution", "command": self.to_dict()},
        )


class MirrorCommand(Command):
    """Mirror (reflect) a solid body across a plane.

    The mirror plane is defined by a point and a normal.  The operation is
    performed by the geometry layer (CadQuery) via the pipeline.

    Representation
    --------------
    - ``selections[0]`` (or ``parameters["target"]``) is the body to mirror.
    - ``parameters["plane_point"]``    [px, py, pz]
    - ``parameters["plane_normal"]``   [nx, ny, nz]
    - ``parameters["keep_original"]``  whether to keep the original body.
    """

    command_type = CommandType.MIRROR
    display_name = "Mirror"
    description = "Reflect a solid body across a plane"

    def __init__(self) -> None:
        super().__init__()
        self._target_ref: Optional[CadEntityRef] = None

    @property
    def parameters_spec(self) -> List[CommandParameter]:
        return [
            CommandParameter(
                name="plane_point", label="Punto del plano (x, y, z)", param_type="str",
                default="0, 0, 0", tooltip="Un punto del plano de espejo",
            ),
            CommandParameter(
                name="plane_normal", label="Normal del plano (x, y, z)", param_type="str",
                default="0, 1, 0", tooltip="Normal del plano de espejo",
            ),
            CommandParameter(
                name="keep_original", label="Conservar original", param_type="bool",
                default=True, tooltip="Conservar el cuerpo original",
            ),
            CommandParameter(
                name="target", label="Cuerpo", param_type="selection",
                required=True, tooltip="El cuerpo a reflejar",
            ),
        ]

    def set_target(self, ref: Optional[CadEntityRef]) -> None:
        self._target_ref = ref
        self.parameters["target"] = ref.to_dict() if ref is not None else None

    @property
    def target(self) -> Optional[CadEntityRef]:
        return self._target_ref

    def target_body_id(self) -> Optional[str]:
        if self._target_ref is None:
            return None
        return self._target_ref.solid_id or self._target_ref.model_id

    def set_parameter(self, name: str, value: Any) -> None:
        if name == "target":
            if isinstance(value, CadEntityRef):
                self.set_target(value)
            elif isinstance(value, str):
                self.set_target(CadEntityRef.from_solid(value))
            return
        super().set_parameter(name, value)

    def add_selection(self, entity: CadEntityRef) -> None:
        super().add_selection(entity)
        if self._target_ref is None:
            self._target_ref = entity
            self.parameters["target"] = entity.to_dict()

    def validate(self) -> bool:
        super().validate()
        if self._target_ref is None:
            self._add_error("A body must be selected.")
        normal = self.parameters.get("plane_normal")
        try:
            pts = [float(x) for x in str(normal or "0, 1, 0").replace(";", ",").split(",")[:3]]
            import math
            norm = math.sqrt(sum(p * p for p in pts))
            if norm < 1e-9:
                self._add_error("Mirror plane normal cannot be zero.")
        except Exception:
            self._add_error("Invalid mirror plane normal.")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        if not self.validate():
            return CommandResult(
                success=False,
                error_message="; ".join(self._validation_errors),
            )
        return CommandResult(
            success=True,
            data={"status": "ready_for_pipeline_execution", "command": self.to_dict()},
        )


class PatternType(str, Enum):
    LINEAR = "linear"
    RECTANGULAR = "rectangular"
    CIRCULAR = "circular"


class PatternCommand(Command):
    """Create a linear/rectangular/circular pattern of a solid body.

    The duplicated bodies are produced by the geometry layer (CadQuery) via
    the pipeline and cached back as a new model.

    Representation
    --------------
    - ``selections[0]`` (or ``parameters["target"]``) is the body to pattern.
    - ``parameters["pattern_type"]``   linear | rectangular | circular
    - ``parameters["direction"]``      [dx, dy, dz] (linear/rectangular)
    - ``parameters["direction2"]``     [dx, dy, dz] (rectangular)
    - ``parameters["count"]``          int (total instances, >= 2)
    - ``parameters["count2"]``         int (rectangular)
    - ``parameters["spacing"]``        float
    - ``parameters["axis"]``           [ax, ay, az] (circular)
    - ``parameters["center"]``         [cx, cy, cz] (circular)
    - ``parameters["angle"]``          float degrees total (circular)
    """

    command_type = CommandType.PATTERN
    display_name = "Pattern"
    description = "Create a linear, rectangular or circular pattern of a body"

    def __init__(self) -> None:
        super().__init__()
        self._target_ref: Optional[CadEntityRef] = None

    @property
    def parameters_spec(self) -> List[CommandParameter]:
        return [
            CommandParameter(
                name="pattern_type", label="Tipo de patrón", param_type="enum",
                options=[op.value for op in PatternType],
                default=PatternType.LINEAR.value,
                tooltip="Tipo de patrón",
            ),
            CommandParameter(
                name="direction", label="Dirección (x, y, z)", param_type="str",
                default="1, 0, 0", tooltip="Dirección del patrón lineal/rectangular",
            ),
            CommandParameter(
                name="direction2", label="Segunda dirección (x, y, z)", param_type="str",
                default="0, 1, 0", required=False,
                tooltip="Segunda dirección del patrón rectangular",
            ),
            CommandParameter(
                name="count", label="Cantidad de ejemplares", param_type="int",
                default=3, min_value=2, max_value=100,
                tooltip="Número total de instancias del patrón",
            ),
            CommandParameter(
                name="count2", label="Cantidad (dir. 2)", param_type="int",
                default=2, min_value=1, max_value=100, required=False,
                tooltip="Instancias en la segunda dirección (rectangular)",
            ),
            CommandParameter(
                name="spacing", label="Separación", param_type="float",
                default=10.0, min_value=0.0,
                tooltip="Separación entre instancias",
            ),
            CommandParameter(
                name="axis", label="Eje del patrón circular (x, y, z)", param_type="str",
                default="0, 0, 1", required=False,
                tooltip="Eje de rotación del patrón circular",
            ),
            CommandParameter(
                name="center", label="Centro del patrón circular", param_type="str",
                default="0, 0, 0", required=False,
                tooltip="Punto centro del patrón circular",
            ),
            CommandParameter(
                name="angle", label="Ángulo total (°)", param_type="float",
                default=360.0, min_value=1.0, max_value=360.0, required=False,
                tooltip="Ángulo total barrido por el patrón circular",
            ),
            CommandParameter(
                name="target", label="Cuerpo", param_type="selection",
                required=True, tooltip="El cuerpo a duplicar",
            ),
        ]

    def set_target(self, ref: Optional[CadEntityRef]) -> None:
        self._target_ref = ref
        self.parameters["target"] = ref.to_dict() if ref is not None else None

    @property
    def target(self) -> Optional[CadEntityRef]:
        return self._target_ref

    def target_body_id(self) -> Optional[str]:
        if self._target_ref is None:
            return None
        return self._target_ref.solid_id or self._target_ref.model_id

    def set_parameter(self, name: str, value: Any) -> None:
        if name == "target":
            if isinstance(value, CadEntityRef):
                self.set_target(value)
            elif isinstance(value, str):
                self.set_target(CadEntityRef.from_solid(value))
            return
        super().set_parameter(name, value)

    def add_selection(self, entity: CadEntityRef) -> None:
        super().add_selection(entity)
        if self._target_ref is None:
            self._target_ref = entity
            self.parameters["target"] = entity.to_dict()

    def validate(self) -> bool:
        super().validate()
        if self._target_ref is None:
            self._add_error("A body must be selected.")
        pt = self.parameters.get("pattern_type")
        if pt and pt not in [e.value for e in PatternType]:
            self._add_error(f"Invalid pattern type: {pt}")
        try:
            cnt = int(self.parameters.get("count", 3))
            if cnt < 2:
                self._add_error("Pattern count must be at least 2.")
        except Exception:
            self._add_error("Invalid pattern count.")
        if pt == PatternType.RECTANGULAR.value:
            try:
                cnt2 = int(self.parameters.get("count2", 1))
                if cnt2 < 1:
                    self._add_error("Second direction count must be at least 1.")
            except Exception:
                self._add_error("Invalid second-direction count.")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        if not self.validate():
            return CommandResult(
                success=False,
                error_message="; ".join(self._validation_errors),
            )
        return CommandResult(
            success=True,
            data={"status": "ready_for_pipeline_execution", "command": self.to_dict()},
        )


# ====================================================================== #
# Condition Commands (Carga, Elasticidad, Obstrucción, Región protegida)
# ====================================================================== #
# Each condition command is a *configuration* command: it validates the user
# inputs, builds a reusable Condition object, and returns it in the
# CommandResult data.  The pipeline layer then registers the condition and
# records it as a Feature in the history (existing flow).  No geometric
# execution is performed here -- conditions are consumed later by studies.

class LoadConditionCommand(Command):
    """Configure a reusable Carga (load) condition."""
    command_type = CommandType.CONDITION_LOAD
    display_name = "Carga"
    description = "Carga sobre una o varias caras (orientación, sentido y magnitud)"

    def __init__(self) -> None:
        super().__init__()
        self._faces: List[CadEntityRef] = []

    def add_face(self, ref: CadEntityRef) -> None:
        if ref not in self._faces:
            self._faces.append(ref)

    @property
    def faces(self) -> List[CadEntityRef]:
        return list(self._faces)

    @property
    def parameters_spec(self) -> List[CommandParameter]:
        return [
            CommandParameter(
                name="orientation", label="Orientación", param_type="enum",
                options=[o.value for o in LoadOrientation],
                default=LoadOrientation.PERPENDICULAR.value, required=False,
                tooltip="Orientación de la dirección respecto al plano de referencia",
            ),
            CommandParameter(
                name="reference_plane_normal", label="Normal del plano", param_type="vector3",
                default=[0.0, 0.0, 1.0], required=False,
                tooltip="Vector normal al plano de referencia",
            ),
            CommandParameter(
                name="angle_deg", label="Ángulo (º)", param_type="float",
                min_value=0.0, required=False,
                tooltip="Ángulo respecto al plano de referencia (orientación = ángulo)",
            ),
            CommandParameter(
                name="sense", label="Sentido", param_type="enum",
                options=[s.value for s in LoadSense],
                default=LoadSense.INDETERMINATE.value, required=False,
                tooltip="Sentido de la dirección",
            ),
            CommandParameter(
                name="magnitude", label="Magnitud (N)", param_type="float",
                min_value=0.0, required=False,
                tooltip="Magnitud de la carga",
            ),
            CommandParameter(
                name="indeterminate", label="Magnitud indeterminada", param_type="bool",
                default=True, required=False,
                tooltip="Permite dejar la magnitud indeterminada (valor válido del modelo)",
            ),
            CommandParameter(
                name="unit", label="Unidad", param_type="str",
                default="N", required=False,
            ),
        ]

    def build_condition(self) -> LoadCondition:
        orientation = LoadOrientation(self.get_parameter("orientation", LoadOrientation.PERPENDICULAR.value))
        normal = self.get_parameter("reference_plane_normal", [0.0, 0.0, 1.0])
        angle_deg = self.get_parameter("angle_deg")
        magnitude = self.get_parameter("magnitude")
        indeterminate = bool(self.get_parameter("indeterminate", magnitude is None))
        return LoadCondition(
            name=self.get_parameter("name", "Carga"),
            faces=_faces_selection(self._faces, "Caras de carga"),
            orientation=orientation,
            reference_plane_normal=tuple(float(v) for v in normal),
            angle_deg=float(angle_deg) if angle_deg is not None else None,
            sense=LoadSense(self.get_parameter("sense", LoadSense.INDETERMINATE.value)),
            magnitude=float(magnitude) if magnitude is not None else None,
            indeterminate=indeterminate,
            unit=self.get_parameter("unit", "N"),
        )

    def validate(self) -> bool:
        super().validate()
        if not self._faces:
            self._add_error("Seleccione al menos una cara para la carga.")
        magnitude = self.get_parameter("magnitude")
        indeterminate = bool(self.get_parameter("indeterminate", True))
        if not indeterminate and magnitude is None:
            self._add_error("Debe introducir una magnitud (o marcar la carga como indeterminada).")
        if not indeterminate and magnitude is not None and float(magnitude) <= 0:
            self._add_error("La magnitud de la carga debe ser positiva.")
        if self.get_parameter("orientation") == LoadOrientation.ANGLE.value and \
                self.get_parameter("angle_deg") is None:
            self._add_error("La orientación 'ángulo' requiere un ángulo (angle_deg).")
        normal = self.get_parameter("reference_plane_normal", [0.0, 0.0, 1.0])
        if normal is not None and _vec_norm(normal) < 1e-12:
            self._add_error("El vector normal del plano de referencia no puede ser cero.")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        if not self.validate():
            return CommandResult(success=False,
                                 error_message="; ".join(self._validation_errors))
        condition = self.build_condition()
        return CommandResult(
            success=True,
            data={"status": "condition_configured",
                  "condition_id": condition.id,
                  "condition": condition.to_dict()},
        )


class ElasticityCommand(Command):
    """Configure a reusable Elasticidad (elasticity) condition."""
    command_type = CommandType.CONDITION_ELASTICITY
    display_name = "Elasticidad"
    description = "Rango/magnitud de flexión en mm sobre una o varias caras"

    def __init__(self) -> None:
        super().__init__()
        self._faces: List[CadEntityRef] = []

    def add_face(self, ref: CadEntityRef) -> None:
        if ref not in self._faces:
            self._faces.append(ref)

    @property
    def faces(self) -> List[CadEntityRef]:
        return list(self._faces)

    @property
    def parameters_spec(self) -> List[CommandParameter]:
        return [
            CommandParameter(
                name="flex_range_mm", label="Rango de flexión (mm)", param_type="float",
                min_value=0.0, required=False,
                tooltip="Rango/magnitud de flexión permitida en milímetros",
            ),
        ]

    def build_condition(self) -> ElasticityCondition:
        return ElasticityCondition(
            name=self.get_parameter("name", "Elasticidad"),
            faces=_faces_selection(self._faces, "Caras de elasticidad"),
            flex_range_mm=float(self.get_parameter("flex_range_mm"))
            if self.get_parameter("flex_range_mm") is not None else None,
        )

    def validate(self) -> bool:
        super().validate()
        if not self._faces:
            self._add_error("Seleccione al menos una cara para la elasticidad.")
        flex = self.get_parameter("flex_range_mm")
        if flex is not None and float(flex) < 0:
            self._add_error("El rango de flexión no puede ser negativo.")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        if not self.validate():
            return CommandResult(success=False,
                                 error_message="; ".join(self._validation_errors))
        condition = self.build_condition()
        return CommandResult(
            success=True,
            data={"status": "condition_configured",
                  "condition_id": condition.id,
                  "condition": condition.to_dict()},
        )


class ObstructionCommand(Command):
    """Configure a reusable Obstrucción (obstruction) condition."""
    command_type = CommandType.CONDITION_OBSTRUCTION
    display_name = "Obstrucción"
    description = "Piezas que obstruyen el espacio de optimización (offset opcional)"

    def __init__(self) -> None:
        super().__init__()
        self._bodies: List[CadEntityRef] = []

    def add_body(self, ref: CadEntityRef) -> None:
        if ref not in self._bodies:
            self._bodies.append(ref)

    @property
    def bodies(self) -> List[CadEntityRef]:
        return list(self._bodies)

    @property
    def parameters_spec(self) -> List[CommandParameter]:
        return [
            CommandParameter(
                name="offset_mm", label="Offset (mm)", param_type="float",
                min_value=0.0, required=False,
                tooltip="Distancia de separación adicional respecto a las piezas",
            ),
        ]

    def build_condition(self) -> ObstructionCondition:
        return ObstructionCondition(
            name=self.get_parameter("name", "Obstrucción"),
            bodies=_solids_selection(self._bodies, "Cuerpos de obstrucción"),
            offset_mm=float(self.get_parameter("offset_mm"))
            if self.get_parameter("offset_mm") is not None else None,
        )

    def validate(self) -> bool:
        super().validate()
        if not self._bodies:
            self._add_error("Seleccione al menos una pieza para la obstrucción.")
        offset = self.get_parameter("offset_mm")
        if offset is not None and float(offset) < 0:
            self._add_error("El offset no puede ser negativo.")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        if not self.validate():
            return CommandResult(success=False,
                                 error_message="; ".join(self._validation_errors))
        condition = self.build_condition()
        return CommandResult(
            success=True,
            data={"status": "condition_configured",
                  "condition_id": condition.id,
                  "condition": condition.to_dict()},
        )


class ProtectedRegionCommand(Command):
    """Configure a reusable Región protegida (protected region) condition."""
    command_type = CommandType.CONDITION_PROTECTED_REGION
    display_name = "Región protegida"
    description = "Geometría (caras) que la optimización no debe modificar"

    def __init__(self) -> None:
        super().__init__()
        self._faces: List[CadEntityRef] = []
        self.parameters["geometry_refs"] = []

    def add_face(self, ref: CadEntityRef) -> None:
        if ref not in self._faces:
            self._faces.append(ref)

    @property
    def faces(self) -> List[CadEntityRef]:
        return list(self._faces)

    @property
    def parameters_spec(self) -> List[CommandParameter]:
        return [
            CommandParameter(
                name="geometry_refs", label="Referencias geométricas",
                param_type="list", default=[], required=False,
                tooltip="Descriptores de regiones geométricas complejas (extensible)",
            ),
        ]

    def add_geometry_ref(self, ref: Dict[str, Any]) -> None:
        # Mutate the tracked list so ``parameters["geometry_refs"]`` stays
        # in sync (the property below returns the same list).
        self.parameters.setdefault("geometry_refs", []).append(ref)

    @property
    def geometry_refs(self) -> List[Dict[str, Any]]:
        return list(self.parameters.get("geometry_refs", []))

    def build_condition(self) -> ProtectedRegion:
        return ProtectedRegion(
            name=self.get_parameter("name", "Región protegida"),
            faces=_faces_selection(self._faces, "Caras protegidas"),
            geometry_refs=list(self.get_parameter("geometry_refs", [])),
        )

    def validate(self) -> bool:
        super().validate()
        if not self._faces and not self.geometry_refs:
            self._add_error("Seleccione al menos una cara (o referencia geométrica) a proteger.")
        return len(self._validation_errors) == 0

    def execute(self) -> CommandResult:
        if not self.validate():
            return CommandResult(success=False,
                                 error_message="; ".join(self._validation_errors))
        condition = self.build_condition()
        return CommandResult(
            success=True,
            data={"status": "condition_configured",
                  "condition_id": condition.id,
                  "condition": condition.to_dict()},
        )


def _vec_norm(v) -> float:
    v = list(v)
    return sum(float(x) ** 2 for x in v) ** 0.5


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
DEFAULT_REGISTRY.register(TransformCommand)
DEFAULT_REGISTRY.register(MirrorCommand)
DEFAULT_REGISTRY.register(PatternCommand)
DEFAULT_REGISTRY.register(LoadConditionCommand)
DEFAULT_REGISTRY.register(ElasticityCommand)
DEFAULT_REGISTRY.register(ObstructionCommand)
DEFAULT_REGISTRY.register(ProtectedRegionCommand)
