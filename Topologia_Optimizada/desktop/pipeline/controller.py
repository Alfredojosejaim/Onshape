"""PipelineController - orchestrates CAD import, meshing, FEA and topology
optimization, reusing the existing project services (services.cad_service and
the self-contained core solvers) while keeping heavy work off the UI thread.

The GUI talks only to this controller; all the reusable engineering logic lives
in the pre-existing services/core layers.

Architecture integration (Phase 1):
    The controller now owns a ``Document`` that tracks the feature history,
    model states, and studies.  This is additive -- all existing public
    methods continue to work exactly as before.  The Document can be queried
    by the UI panels (design tree, timeline) to display the feature history
    and study list.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, Qt, Signal

import numpy as np

from services.cad_service import CADService
from core.materials import STANDARD_MATERIALS
from core.document import Document
from core.features import Feature, FeatureHistory, FeatureStatus, FeatureType
from core.cad_entity import EntityType

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    pass


class PipelineController:
    def __init__(self) -> None:
        self.cad = CADService()
        self.model_id: Optional[str] = None
        self.model_name: Optional[str] = None
        self.mesh: Optional[Dict[str, Any]] = None
        self._material_name = "steel"
        self.current_tessellation: Optional[Dict[str, Any]] = None

        self.forces: list[Dict[str, Any]] = []
        self.constraints: list[Dict[str, Any]] = []
        self.result: Optional[Dict[str, Any]] = None
        self.result_densities: Optional[np.ndarray] = None
        self.mesh_nodes: Optional[np.ndarray] = None
        self.mesh_elements: Optional[np.ndarray] = None

        self._bot_nodes = []
        self._load_nodes = []

        # --- Architecture layer (additive, does not change existing behaviour) ---
        self.document = Document()
        self.feature_history = FeatureHistory()
        self._studies: Dict[str, Any] = {}  # study_id -> Study

        # --- Reusable conditions (shared, never duplicated by studies) ---
        from core.conditions import ConditionManager
        self.conditions = ConditionManager()

        # --- Licensing (single, encapsulated object; no scattered internet
        #     checks anywhere else in the app) ---
        from core.license import LicenseManager
        self.license = LicenseManager()

    # ------------------------------------------------------------------ #
    # Material helpers
    # ------------------------------------------------------------------ #
    def material_names(self):
        return list(STANDARD_MATERIALS.keys())

    def material_name(self) -> str:
        return self._material_name

    def set_material(self, name: str) -> None:
        if name in STANDARD_MATERIALS:
            self._material_name = name

    def material(self):
        return STANDARD_MATERIALS.get(self._material_name, STANDARD_MATERIALS["steel"])

    # ------------------------------------------------------------------ #
    # Import / tessellation (runs on caller thread; STEP parse can be heavy)
    # ------------------------------------------------------------------ #
    def import_model(self, path: str) -> Dict[str, Any]:
        if not path or not os.path.exists(path):
            raise PipelineError(f"Archivo no encontrado: {path}")
        model = self.cad.import_step_from_file(path)
        self.model_id = model.id
        self.model_name = model.name
        # tessellate for the shaded surface; per-face ranges enable entity
        # (face) selection in the viewport and CAD-anchored BC regions.
        tess = self.cad.tessellate_model(model.id, face_mapping=True)
        mismatch = (not tess or tess.get("success") is False
                    or "vertices" not in tess or not tess.get("vertices")
                    or "indices" not in tess or not tess.get("indices"))
        if mismatch:
            raise PipelineError(tess.get("error", "Tesselación falló (sin triángulos)"))
        self.current_tessellation = tess
        # reset downstream state
        self.mesh = None
        self.mesh_nodes = self.mesh_elements = None
        self.result = None
        self.forces = []
        self.constraints = []

        # --- Architecture layer: record import feature in history + document ---
        import_feature = Feature.import_step(
            filename=os.path.basename(path),
            model_id=model.id,
        )
        self.feature_history.append(import_feature)
        self.document.set_model(model)
        self.document.add_feature(import_feature)

        return {"name": model.name, "model": model, "tessellation": tess}

    # ------------------------------------------------------------------ #
    # Mesh generation
    # ------------------------------------------------------------------ #
    def generate_mesh(self, target_element_size: float = 0.0) -> Dict[str, Any]:
        if not self.model_id:
            raise PipelineError("No hay modelo importado. Importa un archivo STEP primero.")
        if target_element_size and target_element_size > 0:
            mesh = self.cad.generate_mesh(self.model_id, target_element_size=target_element_size)
        else:
            mesh = self.cad.generate_mesh(self.model_id)
        if not mesh.get("success"):
            raise PipelineError(mesh.get("error", "Error al generar la malla"))
        self.mesh = mesh
        self.mesh_nodes = np.asarray(mesh["nodes"], dtype=float)
        self.mesh_elements = np.asarray(mesh["elements"], dtype=int)
        self.result = None
        return mesh

    def generate_mesh_for_solid(self, solid_index: int, target_element_size: float = 0.0) -> Dict[str, Any]:
        """Generate the FE mesh for a single selected solid body of the model.

        Used by structural-topology studies so the analysis domain is exactly
        the solid referenced by ``study.parts`` (deterministic), rather than
        implicitly using the first solid or the whole compound.
        """
        if not self.model_id:
            raise PipelineError("No hay modelo importado. Importa un archivo STEP primero.")
        if solid_index is None:
            raise PipelineError("No se pudo resolver el sólido seleccionado del estudio.")
        if target_element_size and target_element_size > 0:
            mesh = self.cad.generate_mesh_for_solid(
                self.model_id, solid_index, target_element_size=target_element_size)
        else:
            mesh = self.cad.generate_mesh_for_solid(self.model_id, solid_index)
        if not mesh.get("success"):
            raise PipelineError(mesh.get("error", "Error al generar la malla del sólido seleccionado"))
        self.mesh = mesh
        self.mesh_nodes = np.asarray(mesh["nodes"], dtype=float)
        self.mesh_elements = np.asarray(mesh["elements"], dtype=int)
        self.result = None
        return mesh

    # ------------------------------------------------------------------ #
    # Adaptive mesh generation (density-driven, Fase 2)
    # ------------------------------------------------------------------ #
    def generate_adaptive_mesh(
        self,
        base_size: float = 5.0,
        min_size: float = 0.5,
        use_density: bool = True,
    ) -> Dict[str, Any]:
        """Generate a locally-refined mesh, optionally using the optimization
        density field to refine solid/dense regions.
        """
        if not self.model_id:
            raise PipelineError("No hay modelo importado. Importa un archivo STEP primero.")
        densities = self.result_densities if use_density else None
        mesh = self.cad.generate_adaptive_mesh(
            self.model_id,
            densities=densities,
            elements=self.mesh_elements,
            nodes=self.mesh_nodes,
            base_size=base_size,
            min_size=min_size,
        )
        if not mesh.get("success"):
            # Fall back to uniform mesh through the standard path.
            return self.generate_mesh(target_element_size=base_size)
        self.mesh = mesh
        self.mesh_nodes = np.asarray(mesh["nodes"], dtype=float)
        self.mesh_elements = np.asarray(mesh["elements"], dtype=int)
        self.result = None
        return mesh

    # ------------------------------------------------------------------ #
    # Boundary conditions (simplified: fixed base + tip distributed load)
    # ------------------------------------------------------------------ #
    def _apply_constraints(self, nodes: np.ndarray) -> np.ndarray:
        """Default: fix the nodes at the minimum coordinate along the longest axis."""
        from core.boundary import BoundaryConditionMapper, resolve_face_index
        from core.selection import NodeSelectionEngine

        fixed_dofs = []
        node_indices = []
        shape = self.cad.get_model_shape(self.model_id) if self.model_id else None
        for c in self.constraints:
            dof = c.get("degrees_of_freedom") or {"ux": True, "uy": True, "uz": True}
            fix_xyz = [bool(dof.get("ux", True)), bool(dof.get("uy", True)), bool(dof.get("uz", True))]

            cond_nodes = []
            selection = c.get("selection")
            if selection:
                tol = c.get("tolerance")
                cond_nodes = NodeSelectionEngine.select_nodes(
                    nodes, selection, cad_shape=shape,
                    default_tolerance=float(tol) if tol is not None else None,
                )
            else:
                location = c.get("location", "")
                face_index = resolve_face_index(str(location)) if location else None
                if shape is not None and face_index is not None:
                    sample = nodes[:: max(1, len(nodes) // 500)]
                    bbox = sample.max(axis=0) - sample.min(axis=0)
                    char_length = max(float(np.linalg.norm(bbox) / max(1.0, len(nodes) ** (1.0 / 3.0))), 1e-9)
                    mapped = BoundaryConditionMapper.map_faces_to_nodes(
                        shape, nodes.tolist(), face_indices=[face_index], tolerance=1.5 * char_length
                    )
                    if mapped and mapped[0].node_indices:
                        cond_nodes = mapped[0].node_indices

            node_indices.extend(cond_nodes)
            for ni in cond_nodes:
                for ax in range(3):
                    if fix_xyz[ax]:
                        fixed_dofs.append(ni * 3 + ax)
        self._bot_nodes = list(dict.fromkeys(node_indices))
        if not fixed_dofs:
            axis = 2
            coord = float(nodes[:, axis].min())
            node_indices = [
                i for i in range(nodes.shape[0])
                if abs(float(nodes[i, axis]) - coord) <= 1e-6 * max(1.0, np.ptp(nodes[:, axis]))
            ]
            self._bot_nodes = node_indices
            for ni in node_indices:
                fixed_dofs.extend([ni * 3, ni * 3 + 1, ni * 3 + 2])
        return np.sort(np.unique(np.asarray(fixed_dofs, dtype=int)))

    def _apply_loads(self, nodes: np.ndarray, num_dofs: int) -> np.ndarray:
        from core.boundary import BoundaryConditionMapper, resolve_face_index
        from core.selection import NodeSelectionEngine

        force_vector = np.zeros(num_dofs)
        node_indices = []
        shape = self.cad.get_model_shape(self.model_id) if self.model_id else None
        for ld in self.forces:
            mag = float(ld.get("magnitude", 0))
            direction = [float(ld.get("direction_x", 0)), float(ld.get("direction_y", 0)), float(ld.get("direction_z", 0))]
            norm = np.linalg.norm(direction)
            if norm == 0 or mag == 0:
                continue
            direction = np.array(direction) / norm
            fvec = direction * mag
            mapped_nodes = []
            selection = ld.get("selection")
            if selection:
                tol = ld.get("tolerance")
                mapped_nodes = NodeSelectionEngine.select_nodes(
                    nodes, selection, cad_shape=shape,
                    default_tolerance=float(tol) if tol is not None else None,
                )
            else:
                face_id = ld.get("application_face_id")
                face_index = resolve_face_index(str(face_id)) if face_id else None
                if shape is not None and face_index is not None:
                    sample = nodes[:: max(1, len(nodes) // 500)]
                    bbox = sample.max(axis=0) - sample.min(axis=0)
                    char_length = max(float(np.linalg.norm(bbox) / max(1.0, len(nodes) ** (1.0 / 3.0))), 1e-9)
                    mapped = BoundaryConditionMapper.map_faces_to_nodes(
                        shape, nodes.tolist(), face_indices=[face_index], tolerance=1.5 * char_length
                    )
                    if mapped and mapped[0].node_indices:
                        mapped_nodes = mapped[0].node_indices
            if mapped_nodes:
                node_indices.extend(mapped_nodes)
            elif not selection:
                axis = int(np.argmax(np.abs(direction)))
                coord = float(nodes[:, axis].max())
                node_indices.extend(
                    i for i in range(nodes.shape[0])
                    if abs(float(nodes[i, axis]) - coord) <= 1e-6 * max(1.0, np.ptp(nodes[:, axis]))
                )
            uniq = list(dict.fromkeys(node_indices))
            for ni in uniq:
                force_vector[ni * 3: ni * 3 + 3] += np.array(fvec) / max(len(uniq), 1)
        self._load_nodes = list(dict.fromkeys(node_indices))
        return force_vector

    def set_simple_boundaries(self, bottom_axis: int = 2, load_dir=(0, 0, 1), magnitude: float = 1000.0):
        """Convenience for a one-load / one-constraint study."""
        self.constraints = [{"constraint_type": "fixed", "location": "", "fixed_axis": bottom_axis}]
        self.forces = [{"magnitude": magnitude, "direction_x": load_dir[0],
                        "direction_y": load_dir[1], "direction_z": load_dir[2]}]

    # ------------------------------------------------------------------ #
    # Solvers (heavy; call via run_in_background)
    # ------------------------------------------------------------------ #
    def build_problem(self):
        if self.mesh is None:
            raise PipelineError("No hay malla. Genera la malla primero.")
        nodes = self.mesh_nodes
        num_dofs = int(nodes.shape[0] * 3)
        if not self.constraints:
            self.set_simple_boundaries()
        fixed = self._apply_constraints(nodes)
        force = self._apply_loads(nodes, num_dofs)
        return nodes, self.mesh_elements, force, fixed

    def run_fea(self, conditions=None, backend: str = "local") -> Dict[str, Any]:
        """Run the quasi-static FE solver.

        ``backend`` selects the solver:

        * ``"local"`` (default): the self-contained NumPy/SciPy FE solver in
          :mod:`core.fea`.  Kept as default so nothing regresses.
        * ``"kratos"``: the optional Kratos FEA solver created via
          ``core.solver_interface.create_kratos_fea_solver``.  It consumes the
          *same* reusable conditions and the mesh's ``physical_groups`` are
          rebuilt as named Kratos submodelparts so boundary conditions select the
          exact CAD-face nodes.  Requires Kratos to be installed, otherwise a
          ``PipelineError`` is raised.

        When ``conditions`` is provided (an iterable of reusable Condition
        objects), the load/elasticity conditions are translated to the mesh
        (local: through ``GenerativeDesignEngine``; kratos: through
        ``core.kratos_bridge``) so the FEA step consumes the real conditions
        instead of the bare ``self.forces`` / ``self.constraints`` arrays.  A
        selected CAD face that cannot be mapped to mesh nodes is reported as an
        error rather than being silently relocated.
        """
        if backend == "kratos":
            return self._run_fea_kratos(conditions)

        if conditions:
            from core.generative_engine import GenerativeDesignEngine, consume_conditions
            engine = GenerativeDesignEngine(
                model_id=self.model_id,
                mesh_nodes=self.mesh_nodes,
                mesh_elements=self.mesh_elements,
                material=self.material(),
                condition_manager=self.conditions,
                model_shape=self.cad.get_model_shape(self.model_id) if self.model_id else None,
            )
            by_type = consume_conditions(self.conditions, [c.id for c in conditions])
            force, fixed = engine.build_fea_problem(by_type)
            nodes, elements = self.mesh_nodes, self.mesh_elements
        else:
            nodes, elements, force, fixed = self.build_problem()
        mat = self.material()
        from core.fea import solve_fea
        result = solve_fea(
            nodes=nodes,
            elements=elements,
            young_modulus=mat.young_modulus,
            poisson_ratio=mat.poisson_ratio,
            forces_dofs=[(int(i), float(v)) for i, v in enumerate(force) if v != 0.0],
            fixed_dofs=fixed.tolist(),
        )
        self.result = result
        return result

    def _run_fea_kratos(self, conditions) -> Dict[str, Any]:
        """Run the optional Kratos FEA backend on the current mesh/conditions.

        Translates reusable conditions into ``LoadDefinition`` /
        ``ConstraintDefinition`` (via :mod:`core.kratos_bridge`), builds the
        Kratos FE solver with ``create_kratos_fea_solver`` (forwarding the mesh's
        ``physical_groups`` so named boundary groups become Kratos submodelparts)
        and runs a single linear-static solve on a uniform density field.

        Uses the same strict contract as the local conditions path: a selected
        CAD face that cannot be mapped is reported rather than silently relocated.
        """
        if self.mesh is None:
            raise PipelineError("No hay malla. Genera la malla primero.")
        if conditions:
            from core.generative_engine import consume_conditions
            from core.kratos_bridge import conditions_to_kratos_definitions
            by_type = consume_conditions(self.conditions, [c.id for c in conditions])
            resolved = []
            for group in by_type.values():
                resolved.extend(group)
            loads, constraints, _skipped = conditions_to_kratos_definitions(resolved)
        else:
            from core.kratos_bridge import conditions_to_kratos_definitions
            loads, constraints, _skipped = conditions_to_kratos_definitions(
                self.conditions.all
            )

        mat = self.material()
        nodes = self.mesh_nodes
        elements = self.mesh_elements
        physical_groups = self.mesh.get("physical_groups") or None
        model_shape = self.cad.get_model_shape(self.model_id) if self.model_id else None

        try:
            from core.solver_interface import create_kratos_fea_solver
            solver = create_kratos_fea_solver(
                nodes=nodes,
                elements=elements,
                material=mat,
                constraints=constraints,
                loads=loads,
                cad_shape=model_shape,
                physical_groups=physical_groups,
            )
        except RuntimeError as exc:  # Kratos not available
            raise PipelineError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - unexpected construction error
            logger.exception("Fallo al crear el solver FEA de Kratos")
            raise PipelineError(f"Fallo al crear el solver FEA de Kratos: {exc}") from exc

        densities = np.ones(elements.shape[0], dtype=float)
        result = solver(densities=densities)
        if not result.get("success"):
            raise PipelineError(
                f"FEA (Kratos) fallo: {result.get('error', 'error desconocido')}"
            )
        self.result = result
        return result

    def run_optimization(
        self,
        volume_fraction: float = 0.3,
        max_iterations: int = 30,
        penalization: float = 3.0,
        filter_radius: float = 1.5,
        tolerance: float = 1e-3,
        progress_cb: Optional[Callable[[dict], None]] = None,
        conditions=None,
    ) -> Dict[str, Any]:
        """Run the self-contained SIMP topology optimisation.

        When ``conditions`` is provided (an iterable of reusable Condition
        objects), the load/elasticity/protected/obstruction conditions are
        translated into the SIMP forces / fixed DOFs / preserved elements /
        void elements, so the solve *consumes* the pre-created conditions
        instead of the bare ``self.forces`` / ``self.constraints`` arrays.
        """
        if self.mesh is None:
            raise PipelineError("No hay malla. Genera la malla primero.")
        nodes, elements = self.mesh_nodes, self.mesh_elements
        mat = self.material()
        from core.topopt import SIMPSolver

        if conditions:
            from core.generative_engine import GenerativeDesignEngine, consume_conditions
            engine = GenerativeDesignEngine(
                model_id=self.model_id,
                mesh_nodes=nodes,
                mesh_elements=elements,
                material=mat,
                condition_manager=self.conditions,
                model_shape=self.cad.get_model_shape(self.model_id) if self.model_id else None,
            )
            by_type = consume_conditions(self.conditions, [c.id for c in conditions])
            g = engine.solve_simp(
                by_type,
                volume_fraction=volume_fraction,
                max_iterations=max_iterations,
                penalization=penalization,
                filter_radius=filter_radius,
                tolerance=tolerance,
                progress_cb=progress_cb,
            )
            self.result = g
            self.result_densities = np.asarray(g["densities"], dtype=float)
            return g

        if not self.constraints:
            self.set_simple_boundaries()
        force = self._apply_loads(nodes, int(nodes.shape[0] * 3))
        fixed = self._apply_constraints(nodes)

        solver = SIMPSolver(
            nodes=nodes,
            elements=elements,
            young_modulus=mat.young_modulus,
            poisson_ratio=mat.poisson_ratio,
            volfrac=volume_fraction,
            penalization=penalization,
            filter_radius=filter_radius,
        )
        solver.set_load(force)
        solver.set_fixed_dofs(fixed)
        try:
            result = solver.optimize(max_iterations=max_iterations, tolerance=tolerance, callback=progress_cb)
        except Exception as exc:
            logger.exception("Optimization failed")
            raise PipelineError(f"Optimización falló: {exc}")
        self.result = result
        self.result_densities = np.asarray(result["densities"], dtype=float)
        return result

    # ------------------------------------------------------------------ #
    # Architecture layer: command execution coordinator
    # ------------------------------------------------------------------ #
    def execute_command(self, command) -> "CommandResult":
        """Validate and execute a CAD command through the pipeline.

        The command's ``validate()`` is called first.  If valid, the command
        is executed and a Feature is recorded in the history.

        For boolean operations the actual CadQuery execution is delegated
        to the pipeline; the command carries the parameters.
        """
        from core.commands import CommandResult, BooleanCommand, CommandType

        if not command.validate():
            return CommandResult(
                success=False,
                error_message="; ".join(command.validation_errors),
            )

        if command.command_type == CommandType.BOOLEAN:
            return self._execute_boolean(command)

        if command.command_type == CommandType.TRANSFORM:
            return self._execute_transform(command)

        if command.command_type == CommandType.MIRROR:
            return self._execute_mirror(command)

        if command.command_type == CommandType.PATTERN:
            return self._execute_pattern(command)

        if command.command_type in (
            CommandType.CONDITION_LOAD,
            CommandType.CONDITION_ELASTICITY,
            CommandType.CONDITION_OBSTRUCTION,
            CommandType.CONDITION_PROTECTED_REGION,
        ):
            return self._execute_condition(command)

        # Default: record as a feature and return pending
        feature = Feature(
            name=command.display_name,
            feature_type=FeatureType(command.command_type.value),
            parameters=command.parameters,
        )
        feature.status = "executed"
        self.feature_history.append(feature)
        self.document.add_feature(feature)
        return CommandResult(
            success=True,
            feature_id=feature.id,
            data={"status": "recorded_in_history"},
        )

    def _execute_boolean(self, command) -> "CommandResult":
        """Execute a boolean command using the existing CadQuery backend (Fase 2).

        The boolean operates at the **body level** on the current model: the
        target body and the tool bodies are resolved from the command and the
        ``boolean_bodies`` CAD service routine modifies the current model in
        place (re-stored as a new model).  ``keep_tools`` controls whether the
        tool bodies are consumed by the operation or remain available.

        On failure the previous model is left untouched and a failing
        ``CommandResult`` is returned so no invalid Feature is recorded.
        """
        from core.commands import CommandResult, BooleanOperation

        operation = command.get_parameter("operation", "union")
        keep_tools = command.get_parameter("keep_tools", False)

        # Resolve target + tools from the command.  Prefer the explicit
        # target/tools fields; fall back to the selections list.
        target_id = None
        if hasattr(command, "target") and command.target is not None:
            target_id = self._body_index(command.target)
        tool_ids = []
        if hasattr(command, "tools") and command.tools:
            tool_ids = [self._body_index(t) for t in command.tools]
        else:
            for sel in command.selections:
                bid = self._body_index(sel)
                if bid is None:
                    continue
                if target_id is None:
                    target_id = bid
                else:
                    tool_ids.append(bid)

        if target_id is None:
            return CommandResult(success=False, error_message="No se definió un cuerpo objetivo.")
        tool_ids = [i for i in tool_ids if i is not None]
        if not tool_ids:
            return CommandResult(success=False,
                                 error_message="No se encontraron cuerpos herramienta (seleccione al menos uno).")

        if not self.model_id:
            return CommandResult(success=False, error_message="No hay modelo importado.")

        result = self.cad.boolean_bodies(
            self.model_id,
            operation=operation,
            target_index=target_id,
            tool_indices=tool_ids,
            keep_tools=keep_tools,
        )
        if not result.get("success"):
            return CommandResult(success=False, error_message=result.get("error", "Operación booleana fallida."))

        # Commit through the single finalize mechanism: activates the new model
        # in PipelineController + Document, updates model_name, invalidates
        # mesh/results/tessellation and re-tessellates (avoiding the previous
        # duplicated invalidation which also missed the Document sync).
        res = self._finalize_cad_result(result)
        if not res.success:
            return res
        new_model_id = res.result_model_id

        # Record as feature (uses the existing Feature.boolean_op).
        feature = Feature.boolean_op(
            operation=operation,
            target_body_id=str(target_id),
            tool_body_ids=[str(i) for i in tool_ids],
            keep_tools=keep_tools,
        )
        feature.name = f"Boolean {operation}"
        feature.status = "executed"
        feature.result_model_id = new_model_id
        self.feature_history.append(feature)
        self.document.add_feature(feature)
        res.feature_id = feature.id

        return CommandResult(
            success=True,
            feature_id=feature.id,
            result_model_id=new_model_id,
            data={"operation": operation, "status": "executed",
                  "target_body_id": str(target_id),
                  "tool_body_ids": [str(i) for i in tool_ids],
                  "keep_tools": keep_tools,
                  "result_model_id": new_model_id},
        )

    # ------------------------------------------------------------------ #
    # Transform / Mirror / Pattern execution
    # ------------------------------------------------------------------ #
    def _finalize_cad_result(self, cad_result: Dict[str, Any]) -> "CommandResult":
        """Commit a CADService geometry result as the new active model.

        On success it invalidates the FEM mesh, downstream results and the old
        tessellation, re-tessellates the new model for the viewport, and returns
        a success ``CommandResult``.  On failure the previous model is left
        untouched.
        """
        from core.commands import CommandResult

        if not cad_result.get("success"):
            return CommandResult(
                success=False,
                error_message=cad_result.get("error", "Operación CAD fallida."),
            )

        new_model_id = cad_result["model_id"]
        self.model_id = new_model_id
        # Keep the architecture layers in sync: PipelineController, CADService
        # (already), Viewport (below) and Document must all point at the same
        # active model / name, otherwise the DesignTree / properties / UI would
        # describe a stale model.
        cad_model = self.cad.get_model(new_model_id)
        if cad_model is not None:
            self.model_name = cad_model.name
            self.document.set_model(cad_model)
        # Invalidate geometry-dependent state: the previous FE mesh, results and
        # tessellation no longer correspond to the new geometry.
        self.result = None
        self.result_densities = None
        self.mesh = None
        self.mesh_nodes = self.mesh_elements = None
        self._study_solid_index = None
        self.current_tessellation = None

        # Re-tessellate so the viewport can display the CAD result.
        tess = self.cad.tessellate_model(new_model_id, face_mapping=True)
        self.current_tessellation = tess

        return CommandResult(
            success=True,
            result_model_id=new_model_id,
            data={"status": "executed", "result_model_id": new_model_id,
                  "model_name": self.model_name},
        )

    def _register_reconstruction_model(self, reconstruction: Dict[str, Any]) -> Dict[str, Any]:
        """Best-effort: register a reconstructed OCP solid back as the active CADModel.

        The reconstruction dict produced by ``core.generative_engine._reconstruct``
        carries the B-Rep solid under ``data`` (only when the BREP stage completed).
        When available we wrap it as a CadQuery Shape, store it as a new model in
        the CAD service, make it the active model (controller + Document), record a
        reconstruction Feature and re-tessellate for the viewport.

        Returns a description dict with ``model_id``/``model_name``, or ``{}`` if
        the reconstruction produced no usable solid or the CAD layer cannot store
        it (e.g. in tests using a minimal fake CAD service).  Never raises: the
        reconstruction result is a bonus on top of the SIMP/density result.
        """
        solid = reconstruction.get("data")
        if solid is None:
            return {}
        store = getattr(self.cad, "store_computed_shape", None)
        if store is None:
            return {}
        try:
            import cadquery as cq
            # Accept either a raw OCP TopoDS shape or an already-wrapped
            # CadQuery Shape; cq.Shape only re-wraps a raw TopoDS object.
            wrapped = getattr(solid, "wrapped", solid)
            shape = cq.Shape(wrapped)
            model_name = reconstruction.get("metadata", {}).get("step_path") \
                or "Reconstrucción Topológica"
            model_id = store(shape, model_name=model_name)

            # Activate the new model across layers.
            self.model_id = model_id
            self.model_name = model_name
            if hasattr(self.document, "set_model"):
                cad_model = self.cad.get_model(model_id) \
                    if hasattr(self.cad, "get_model") else None
                if cad_model is not None:
                    self.document.set_model(cad_model)

            # Re-tessellate the reconstructed model for the viewport/export.
            # (The density field stays available so the study result remains
            # visualisable as before; the new model is registered and active.)
            self.current_tessellation = None
            if hasattr(self.cad, "tessellate_model"):
                tess = self.cad.tessellate_model(model_id, face_mapping=True)
                if tess and tess.get("success"):
                    self.current_tessellation = tess

            # Record a reconstruction feature in history + Document so the
            # result appears in the Design Tree.
            feature = Feature(
                name="Reconstrucción Topológica",
                feature_type=FeatureType.CUSTOM,
                parameters={"kind": "reconstruction",
                            "result_model_id": model_id},
                status=FeatureStatus.EXECUTED,
                result_model_id=model_id,
            )
            self.feature_history.append(feature)
            if hasattr(self.document, "add_feature"):
                self.document.add_feature(feature)
            # Drop the raw OCP object from the returned dict before it reaches
            # consumers (kept only as a serialisable description).
            reconstruction.pop("data", None)
            reconstruction["model_id"] = model_id
            reconstruction["model_name"] = model_name
            return {"model_id": model_id, "model_name": model_name}
        except Exception as exc:
            logger.warning("No se pudo registrar la reconstrucción como CADModel: %s", exc)
            return {}

    def _execute_transform(self, command) -> "CommandResult":
        """Execute a transform (translate/rotate/scale) of a solid body.

        The body selected on the command is transformed through the geometry
        layer (``CADService.transform_bodies``), committed as the new active
        model, and recorded as a ``Transform`` Feature.
        """
        from core.commands import CommandResult

        target_id = self._body_index(command.target) if hasattr(command, "target") else None
        if target_id is None:
            return CommandResult(success=False,
                                 error_message="No se encontró el cuerpo objetivo.")

        if not self.model_id:
            return CommandResult(success=False, error_message="No hay modelo importado.")

        transform_type = command.get_parameter("transform_type", "translate")
        cad_result = self.cad.transform_bodies(
            self.model_id,
            target_index=target_id,
            transform_type=transform_type,
            translation=command.get_parameter("translation"),
            rotation_axis=command.get_parameter("rotation_axis"),
            rotation_angle=command.get_parameter("rotation_angle", 0.0),
            scale_factor=command.get_parameter("scale_factor", 1.0),
            keep_original=bool(command.get_parameter("keep_original", False)),
        )
        res = self._finalize_cad_result(cad_result)
        if not res.success:
            return res

        feature = Feature.transform(
            matrix=self.cad._parse_vector(command.get_parameter("translation"), [0, 0, 0]),
            target_body_id=str(target_id),
            transform_type=transform_type,
            rotation_axis=self.cad._parse_vector(command.get_parameter("rotation_axis"), [0, 0, 1]),
            rotation_angle=command.get_parameter("rotation_angle", 0.0),
            scale_factor=command.get_parameter("scale_factor", 1.0),
        )
        feature.name = f"Transform {transform_type}"
        feature.status = "executed"
        feature.result_model_id = res.result_model_id
        self.feature_history.append(feature)
        self.document.add_feature(feature)
        res.feature_id = feature.id
        res.data.update({"target_body_id": str(target_id),
                         "transform_type": transform_type})
        return res

    def _execute_mirror(self, command) -> "CommandResult":
        """Execute a mirror of a solid body across a plane.

        The mirrored solid is produced by ``CADService.mirror_bodies`` and
        committed as the new active model.
        """
        from core.commands import CommandResult

        target_id = self._body_index(command.target) if hasattr(command, "target") else None
        if target_id is None:
            return CommandResult(success=False,
                                 error_message="No se encontró el cuerpo objetivo.")

        if not self.model_id:
            return CommandResult(success=False, error_message="No hay modelo importado.")

        plane_point = command.get_parameter("plane_point", "0, 0, 0")
        plane_normal = command.get_parameter("plane_normal", "0, 1, 0")
        keep_original = bool(command.get_parameter("keep_original", True))

        cad_result = self.cad.mirror_bodies(
            self.model_id,
            target_index=target_id,
            plane_point=plane_point,
            plane_normal=plane_normal,
            keep_original=keep_original,
        )
        res = self._finalize_cad_result(cad_result)
        if not res.success:
            return res

        feature = Feature.mirror(
            plane_point=list(self.cad._parse_vector(plane_point, [0, 0, 0])),
            plane_normal=list(self.cad._parse_vector(plane_normal, [0, 1, 0])),
            target_body_id=str(target_id),
            keep_original=keep_original,
        )
        feature.status = "executed"
        feature.result_model_id = res.result_model_id
        self.feature_history.append(feature)
        self.document.add_feature(feature)
        res.feature_id = feature.id
        res.data.update({"target_body_id": str(target_id),
                         "keep_original": keep_original})
        return res

    def _execute_pattern(self, command) -> "CommandResult":
        """Execute a linear/rectangular/circular pattern of a solid body.

        The duplicated bodies are produced by ``CADService.pattern_bodies`` and
        committed as the new active model.
        """
        from core.commands import CommandResult

        target_id = self._body_index(command.target) if hasattr(command, "target") else None
        if target_id is None:
            return CommandResult(success=False,
                                 error_message="No se encontró el cuerpo objetivo.")

        if not self.model_id:
            return CommandResult(success=False, error_message="No hay modelo importado.")

        pattern_type = command.get_parameter("pattern_type", "linear")
        cad_result = self.cad.pattern_bodies(
            self.model_id,
            target_index=target_id,
            pattern_type=pattern_type,
            direction=command.get_parameter("direction"),
            direction2=command.get_parameter("direction2"),
            count=int(command.get_parameter("count", 3)),
            count2=int(command.get_parameter("count2", 2)),
            spacing=float(command.get_parameter("spacing", 10.0)),
            axis=command.get_parameter("axis"),
            center=command.get_parameter("center"),
            angle=float(command.get_parameter("angle", 360.0)),
        )
        res = self._finalize_cad_result(cad_result)
        if not res.success:
            return res

        feature = Feature.pattern(
            pattern_type=pattern_type,
            target_body_id=str(target_id),
            count=int(command.get_parameter("count", 3)),
            spacing=float(command.get_parameter("spacing", 10.0)),
            center=command.get_parameter("center"),
            angle=float(command.get_parameter("angle", 360.0)),
        )
        feature.status = "executed"
        feature.result_model_id = res.result_model_id
        self.feature_history.append(feature)
        self.document.add_feature(feature)
        res.feature_id = feature.id
        res.data.update({"target_body_id": str(target_id),
                         "pattern_type": pattern_type})
        return res

    # ------------------------------------------------------------------ #
    # Architecture layer: condition command coordinator
    # ------------------------------------------------------------------ #
    def _execute_condition(self, command) -> "CommandResult":
        """Register a reusable Condition and record it as a Feature.

        Conditions are stored in the shared :class:`ConditionManager` (owned by
        this controller) so optimization / generative studies can later consume
        them *by id* without duplicating them.  Executing the command does not
        mutate the CAD geometry -- conditions are reusable configuration.
        """
        from core.commands import CommandResult
        from core.features import Feature

        # Build the condition once; register the exact same object so the id
        # reported to the caller always matches the registered condition.
        if not hasattr(command, "build_condition"):
            return CommandResult(success=False,
                                 error_message="El comando no produce una condición.")

        # Validation is performed exactly once by ``execute_command`` (the
        # public entry point); this private coordinator only executes.
        condition = command.build_condition()

        # Register in the shared manager + document, then record a Feature.
        self.conditions.add(condition)
        if hasattr(self.document, "add_condition"):
            self.document.add_condition(condition)

        feature = Feature.condition(
            condition_type=command.command_type.value,
            name=condition.name,
            condition=condition.to_dict(),
        )
        self.feature_history.append(feature)
        self.document.add_feature(feature)

        return CommandResult(
            success=True,
            feature_id=feature.id,
            result_model_id=self.model_id,
            data={
                "status": "condition_registered",
                "condition_id": condition.id,
                "condition_type": command.command_type.value,
                "feature_id": feature.id,
            },
        )

    def list_conditions(self) -> list:
        """Return all registered reusable conditions (for the design tree)."""
        return self.conditions.all

    @staticmethod
    def _body_index(ref) -> Optional[int]:
        """Extract a solid body index from a CadEntityRef/selection.

        Returns ``None`` when the reference cannot be reduced to an index.
        Falls back to parsing ``solid_<n>`` ids and the model-level index.
        """
        import re
        if ref is None:
            return None
        solid_id = getattr(ref, "solid_id", None)
        if solid_id:
            m = re.match(r"solid_(\d+)", str(solid_id))
            if m:
                return int(m.group(1))
        index = getattr(ref, "index", None)
        if index is not None:
            return int(index)
        solid = getattr(ref, "solid", None)
        if solid is not None:
            sid = getattr(solid, "solid_id", None)
            if sid:
                m = re.match(r"solid_(\d+)", str(sid))
                if m:
                    return int(m.group(1))
        idx = getattr(ref, "solid_index", None)
        if idx is not None:
            return int(idx)
        return None

    # ------------------------------------------------------------------ #
    # Architecture layer: study execution coordinator
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_study_solid_index(study, model_id: Optional[str]) -> Optional[int]:
        """Resolve the body index of the solid selected on ``study.parts``.

        Returns ``None`` when the study has no resolvable SOLID part for the
        given model (zero parts, non-SOLID, incompatible model_id, or a solid
        id that cannot be mapped to a body index).  This is the deterministic
        domain selector: the first part is used only if it is the user's
        explicit selection (never an implicit fallback).
        """
        parts = getattr(study, "parts", None) or []
        if not parts:
            return None
        for ref in parts:
            if getattr(ref, "entity_type", None) != EntityType.SOLID:
                return None
            ref_model = getattr(ref, "model_id", None)
            if ref_model and model_id and ref_model != model_id:
                return None
            index = PipelineController._body_index(ref)
            if index is not None:
                return index
        return None

    def register_study(self, study) -> str:
        """Register a Study in the controller and document.  Returns study id."""
        sid = study.id
        self._studies[sid] = study
        self.document.add_study(study)
        return sid

    def execute_study(self, study, progress_cb: Optional[Callable] = None) -> "StudyResult":
        """Execute an engineering study through the pipeline.

        For TopologyOptimizationStudy the existing SIMP engine is used.
        For StructuralAnalysis the existing FEA engine is used.
        Other study types are marked as ready_for_pipeline.

        The study's ``parts`` list determines which solid(s) are the domain
        of analysis.  If no mesh exists yet, one is generated automatically
        from the model referenced by the study.
        """
        from core.cae_studies import StudyResult, StudyStatus, StudyNotImplementedError
        from core.optimization_studies import TopologyOptimizationStudy

        if not study.validate():
            study.status = StudyStatus.FAILED
            specific = getattr(study, "validate_with_message", lambda: None)()
            return StudyResult(
                success=False,
                status="validation_failed",
                error_message=specific or "Study validation failed.",
            )

        study.status = StudyStatus.RUNNING

        # Ensure the controller's active model matches the study's model.
        effective_model_id = getattr(study, "model_id", None) or self.model_id
        if effective_model_id and effective_model_id != self.model_id:
            self.model_id = effective_model_id

        if isinstance(study, TopologyOptimizationStudy):
            try:
                # The selected solid on ``study.parts`` is the deterministic
                # domain of analysis.  Resolve its body index and validate that
                # it is actually resolvable against the current model (never
                # silently use an implicit "first solid").
                solid_index = self._resolve_study_solid_index(study, effective_model_id)
                if solid_index is None:
                    study.status = StudyStatus.FAILED
                    return StudyResult(
                        success=False,
                        status="invalid_part",
                        error_message=(
                            "El estudio no tiene una pieza (sólido) seleccionada válida para "
                            "el modelo actual. Seleccione un sólido real en el viewport e "
                            "intente de nuevo."
                        ),
                    )

                # Validate that the selected solid is actually resolvable in the
                # current model (in-range body index) -- refuse an unresolvable
                # part instead of silently producing a wrong result.
                if effective_model_id:
                    solids = self.cad.list_solids(effective_model_id)
                    if not solids:
                        study.status = StudyStatus.FAILED
                        return StudyResult(
                            success=False,
                            status="no_solids",
                            error_message="El modelo no contiene sólidos resolubles para el estudio.",
                        )
                    if not (0 <= solid_index < len(solids)):
                        study.status = StudyStatus.FAILED
                        return StudyResult(
                            success=False,
                            status="unresolvable_part",
                            error_message=(
                                f"El sólido seleccionado (índice {solid_index}) no existe en el "
                                "modelo actual. Seleccione un sólido válido en el viewport."
                            ),
                        )

                # Auto-generate / refresh the mesh for the *selected solid* only,
                # so the analysis domain matches study.parts (not the whole model).
                if self.mesh is None or getattr(self, "_study_solid_index", None) != solid_index:
                    self.generate_mesh_for_solid(solid_index)
                    self._study_solid_index = solid_index

                p = study.optimization_params
                conditions = study.consume_conditions(self.conditions) \
                    if study.conditions else None
                result = self.run_optimization(
                    volume_fraction=p.volume_fraction,
                    max_iterations=p.max_iterations,
                    penalization=p.penalization,
                    filter_radius=p.filter_radius,
                    tolerance=p.convergence_tolerance,
                    progress_cb=progress_cb,
                    conditions=conditions,
                )
                study.status = StudyStatus.COMPLETED
                sr = StudyResult(success=True, status="completed", data=result)
                study.result = sr
                self.document.add_result(study.id, result)
                return sr
            except Exception as exc:
                study.status = StudyStatus.FAILED
                return StudyResult(success=False, status="failed", error_message=str(exc))

        if study.study_type.value == "generative_design":
            try:
                from core.generative_engine import GenerativeDesignEngine, run_generative_design
                engine = GenerativeDesignEngine(
                    model_id=effective_model_id,
                    mesh_nodes=self.mesh_nodes,
                    mesh_elements=self.mesh_elements,
                    material=self.material(),
                    condition_manager=self.conditions,
                    model_shape=self.cad.get_model_shape(effective_model_id) if effective_model_id else None,
                )
                result = run_generative_design(study, self.conditions, engine,
                                               progress_cb=progress_cb)
                # Surface the SIMP/density output so the UI can visualise it.
                self.result = result
                densities = result.get("densities")
                if densities is not None and len(densities):
                    self.result_densities = np.asarray(densities, dtype=float)
                # Register the reconstructed B-Rep back as the active CADModel
                # (Document / viewport / history / Design Tree).  Best-effort:
                # never fails the study if no solid was produced.
                reconstruction = result.get("reconstruction") or {}
                self._register_reconstruction_model(reconstruction)
                study.status = StudyStatus.COMPLETED
                sr = StudyResult(success=True, status="completed", data=result)
                study.result = sr
                self.document.add_result(study.id, result)
                return sr
            except Exception as exc:
                study.status = StudyStatus.FAILED
                return StudyResult(success=False, status="failed", error_message=str(exc))

        # Thermal / Modal are scaffolded (data model + validation complete) but
        # their real solvers are not integrated yet. Report a clear
        # ``not_implemented`` result instead of a confusing generic failure.
        if study.study_type.value in ("thermal", "modal"):
            try:
                study.validate()
                validation_msg = getattr(study, "validate_with_message", lambda: None)()
                if validation_msg:
                    study.status = StudyStatus.FAILED
                    return StudyResult(
                        success=False, status="validation_failed", error_message=validation_msg,
                    )
                study.execute()
                study.status = StudyStatus.COMPLETED
                sr = study.result or StudyResult(success=True, status="completed")
                if study.result and sr.data:
                    self.document.add_result(study.id, sr.data)
                return sr
            except StudyNotImplementedError as exc:
                study.status = StudyStatus.FAILED
                return StudyResult(
                    success=False, status="not_implemented", error_message=str(exc),
                )
            except Exception as exc:
                study.status = StudyStatus.FAILED
                return StudyResult(success=False, status="failed", error_message=str(exc))

        # Default: mark as ready for pipeline
        study.status = StudyStatus.READY
        return StudyResult(
            success=True,
            status="ready_for_pipeline",
            data={"study_id": study.id, "type": study.study_type.value},
        )

    # ------------------------------------------------------------------ #
    # Background execution helper
    # ------------------------------------------------------------------ #
    def run_in_background(self, fn: Callable[[], Any], on_done: Callable[[Any], None],
                          on_error: Optional[Callable[[Exception], None]] = None) -> None:
        def worker():
            try:
                out = fn()
            except Exception as exc:
                logger.exception("Background task failed")
                if on_error:
                    launch_qt(lambda: on_error(exc))
                return
            launch_qt(lambda: on_done(out))

        threading.Thread(target=worker, daemon=True).start()


def launch_qt(cb: Callable[[], None]) -> None:
    """Run ``cb`` on the Qt main thread from any thread.

    ``QTimer.singleShot`` is NOT safe to call from a plain Python thread; the
    timer is never delivered. We instead emit a queued signal on a dispatcher
    QObject that lives on the GUI thread, which always gets delivered.
    """
    dispatcher = _GUI_DISPATCHER
    if dispatcher is None:
        cb()
        return
    try:
        dispatcher.invoke.emit(cb)
    except RuntimeError:
        cb()


class _GuiDispatcher(QObject):
    invoke = Signal(object)


def _make_dispatcher() -> Optional[_GuiDispatcher]:
    try:
        disp = _GuiDispatcher()
        disp.invoke.connect(lambda fn: fn(), Qt.QueuedConnection)
        return disp
    except Exception:
        return None


# Created at import time so its thread affinity is the main (GUI) thread; the
# controller module is imported by the GUI during application startup.
_GUI_DISPATCHER = _make_dispatcher()

