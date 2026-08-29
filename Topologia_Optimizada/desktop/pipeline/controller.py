"""PipelineController - orchestrates CAD import, meshing, FEA and topology
optimization, reusing the existing project services (services.cad_service and
the self-contained core solvers) while keeping heavy work off the UI thread.

The GUI talks only to this controller; all the reusable engineering logic lives
in the pre-existing services/core layers.
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
        # tessellate for the shaded surface
        tess = self.cad.tessellate_model(model.id)
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

    # ------------------------------------------------------------------ #
    # Boundary conditions (simplified: fixed base + tip distributed load)
    # ------------------------------------------------------------------ #
    def _apply_constraints(self, nodes: np.ndarray) -> np.ndarray:
        """Default: fix the nodes at the minimum coordinate along the longest axis."""
        from core.boundary import BoundaryConditionMapper, resolve_face_index

        fixed_dofs = []
        node_indices = []
        for c in self.constraints:
            ctype = c.get("constraint_type", "fixed")
            location = c.get("location", "")
            if location:
                model = self.cad.get_model(self.model_id) if self.model_id else None
                shape = self.cad.get_model_shape(self.model_id) if self.model_id else None
                face_index = resolve_face_index(str(location)) if location else None
                mapped_nodes = []
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
            if not node_indices and not self.constraints:
                axis = int(c.get("fixed_axis", 2))
                coord = c.get("fixed_coordinate")
                if coord is None:
                    coord = float(nodes[:, axis].min())
                node_indices = [
                    i for i in range(nodes.shape[0])
                    if abs(float(nodes[i, axis]) - coord) <= 1e-6 * max(1.0, np.ptp(nodes[:, axis]))
                ]
            dof = c.get("degrees_of_freedom") or {"ux": True, "uy": True, "uz": True}
            fix_xyz = [bool(dof.get("ux", True)), bool(dof.get("uy", True)), bool(dof.get("uz", True))]
            for ni in node_indices:
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

        force_vector = np.zeros(num_dofs)
        node_indices = []
        for ld in self.forces:
            mag = float(ld.get("magnitude", 0))
            direction = [float(ld.get("direction_x", 0)), float(ld.get("direction_y", 0)), float(ld.get("direction_z", 0))]
            norm = np.linalg.norm(direction)
            if norm == 0 or mag == 0:
                continue
            direction = np.array(direction) / norm
            fvec = direction * mag
            face_id = ld.get("application_face_id")
            shape = self.cad.get_model_shape(self.model_id) if self.model_id else None
            mapped_nodes = []
            if shape is not None and face_id:
                face_index = resolve_face_index(str(face_id)) if face_id else None
                if face_index is not None:
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
            else:
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

    def run_fea(self) -> Dict[str, Any]:
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

    def run_optimization(
        self,
        volume_fraction: float = 0.3,
        max_iterations: int = 30,
        penalization: float = 3.0,
        filter_radius: float = 1.5,
        tolerance: float = 1e-3,
        progress_cb: Optional[Callable[[dict], None]] = None,
    ) -> Dict[str, Any]:
        nodes, elements, force, fixed = self.build_problem()
        mat = self.material()
        from core.topopt import SIMPSolver

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

