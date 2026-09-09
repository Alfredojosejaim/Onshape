"""Bridge Qt <-> HTML para el experimento html-ui-poc.

SOLO capa de presentacion: expone el core maduro (topo_problem, solvers,
PipelineController, pipeline VTK) a la UI HTML via QWebChannel.

NO copia ni reescribe el core: todo se importa por sys.path desde
../Topologia_Optimizada. No toca desktop.ui (ribbon, design_tree) — los
reemplaza la UI HTML en Web_App/html.
"""
from __future__ import annotations

import json
import logging
import traceback

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)


class CoreBridge(QObject):
    """QObject publicado como 'pyBridge' en QWebChannel."""

    # HTML -> Python ya usa Slots; Python -> HTML usa estas signals.
    statusChanged = Signal(str)
    studyUpdated = Signal(str)  # JSON con snapshot del Document/controller

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller

    def _snapshot(self) -> str:
        ctrl = self._controller
        if ctrl is None:
            return json.dumps({"ok": False, "error": "sin controller"})
        try:
            doc = getattr(ctrl, "document", None)
            payload = {
                "ok": True,
                "model_name": getattr(ctrl, "model_name", None),
                "model_id": getattr(ctrl, "model_id", None),
                "has_mesh": getattr(ctrl, "mesh", None) is not None,
                "has_result": getattr(ctrl, "result", None) is not None,
                "features": len(getattr(getattr(doc, "history", None), "features", []) or []),
                "studies": len(getattr(doc, "studies", []) or []),
            }
            return json.dumps(payload)
        except Exception as exc:  # noqa: BLE001 - el error viaja al HTML
            return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    def _emit(self):
        snap = self._snapshot()
        self.studyUpdated.emit(snap)

    @Slot(str, result=str)
    def validateProblem(self, problemJson: str) -> str:
        """Valida un TopologyOptimizationProblem serializado desde el HTML."""
        try:
            from core.topo_problem import TopologyOptimizationProblem

            data = json.loads(problemJson or "{}")
            # Reconstruccion minima: el HTML manda dict compatible con el
            # schema; aqui solo se valida lo que el core ya soporta.
            problem = TopologyOptimizationProblem.from_dict(data) \
                if hasattr(TopologyOptimizationProblem, "from_dict") \
                else TopologyOptimizationProblem(**data)
            problem.validate()
            self.statusChanged.emit("problema valido")
            return json.dumps({"ok": True})
        except Exception as exc:  # noqa: BLE001
            logger.warning("validateProblem fallo: %s", exc)
            return json.dumps({
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc(limit=3),
            })

    @Slot(str, result=str)
    def importStep(self, path: str) -> str:
        try:
            res = self._controller.import_cad(path) if self._controller else None
            self.statusChanged.emit(f"CAD importado: {path}")
            self._emit()
            return json.dumps({"ok": True, "result": str(res)[:2000]})
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    @Slot(str, result=str)
    def runSolver(self, configJson: str) -> str:
        """Dispara FEA/SIMP via PipelineController existente (mismo VTK)."""
        try:
            cfg = json.loads(configJson or "{}")
            method = cfg.pop("method", "run_topology_optimization")
            fn = getattr(self._controller, method, None)
            if fn is None:
                return json.dumps({"ok": False, "error": f"metodo desconocido: {method}"})
            res = fn(**cfg) if isinstance(cfg, dict) else fn()
            self.statusChanged.emit(f"solver OK: {method}")
            self._emit()
            return json.dumps({"ok": True, "result": str(res)[:4000]})
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    @Slot(result=str)
    def getSnapshot(self) -> str:
        return self._snapshot()
