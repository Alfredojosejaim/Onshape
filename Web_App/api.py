"""API JS <-> Python para el experimento standalone (pywebview).

Expone el core VENDORIZADO en core_vendor/ (copia de Topologia_Optimizada,
proyecto original intacto). Sin Qt, sin HTTP: pywebview invoca estos metodos
directo desde el HTML via window.pywebview.api.

Todo entra/sale como tipos JSON-serializables. Lo pesado corre en
ThreadPoolExecutor y se sondea con pollJob.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

_HERE = os.path.dirname(os.path.abspath(__file__))
_VENDOR = os.path.join(_HERE, "core_vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logging.getLogger("core.kratos_adapter").setLevel(logging.CRITICAL)

logger = logging.getLogger("webapp.api")

_MAX_MESH_FLOATS = 600_000  # tope de floats por respuesta (protege al webview)


def _clean(obj, _budget=None):
    """Convierte numpy/contenedores a tipos JSON, diezmando arrays grandes."""
    import numpy as np
    if _budget is None:
        _budget = [_MAX_MESH_FLOATS]
    if isinstance(obj, np.ndarray):
        flat = obj.ravel()
        if flat.size > _budget[0]:
            step = (flat.size + _budget[0] - 1) // _budget[0]
            flat = flat[::step]
            truncated = True
        else:
            truncated = False
        _budget[0] -= flat.size
        return {"__ndarray__": True, "shape": list(obj.shape),
                "truncated": truncated, "data": flat.tolist()}
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _clean(v, _budget) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v, _budget) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def _err(exc: Exception) -> dict:
    return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
            "trace": traceback.format_exc(limit=5)}


class Api:
    def __init__(self):
        from desktop.pipeline.controller import PipelineController
        self._ctrl = PipelineController()
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="solver")
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    # -- utilidades -----------------------------------------------------
    def _snapshot(self) -> dict:
        c = self._ctrl
        doc = getattr(c, "document", None)
        hist = getattr(doc, "history", None)
        return {
            "model_name": getattr(c, "model_name", None),
            "model_id": getattr(c, "model_id", None),
            "has_mesh": getattr(c, "mesh", None) is not None,
            "has_result": getattr(c, "result", None) is not None,
            "material": getattr(c, "_material_name", None),
            "features": len(getattr(hist, "features", []) or []),
            "studies": len(getattr(doc, "studies", []) or []),
        }

    def _submit(self, kind: str, fn, *args, **kwargs) -> str:
        jid = f"{kind}_{uuid.uuid4().hex[:8]}"
        fut = self._pool.submit(fn, *args, **kwargs)
        with self._lock:
            self._jobs[jid] = {"state": "running", "progress": 0.0,
                               "future": fut, "result": None, "error": None}

            def _done(f):
                try:
                    res = f.result()
                    with self._lock:
                        self._jobs[jid].update(state="done", progress=1.0,
                                               result=_clean(res))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("job %s fallo: %s", jid, exc)
                    with self._lock:
                        self._jobs[jid].update(state="error", error=_err(exc))
            fut.add_done_callback(_done)
        return jid

    # -- llamadas desde el HTML -----------------------------------------
    def getSnapshot(self) -> dict:
        return {"ok": True, "snapshot": self._snapshot()}

    # -- navegacion (mismo NavigationManager + UserPreferences del core) --
    def _nav(self):
        from core.navigation import NavigationManager
        from core.user_preferences import UserPreferences
        prefs = UserPreferences()
        mgr = NavigationManager(profile_name=prefs.navigation_profile)
        return prefs, mgr

    def getNavProfiles(self) -> dict:
        try:
            from core.navigation import NavigationManager
            prefs, mgr = self._nav()
            return {"ok": True, "profiles": NavigationManager.available_profiles(),
                    "current": mgr.profile_name}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def setNavProfile(self, name: str) -> dict:
        try:
            prefs, mgr = self._nav()
            if not mgr.set_profile(name):
                return {"ok": False, "error": f"perfil desconocido: {name}"}
            prefs.navigation_profile = name
            prefs.save()
            return {"ok": True, "current": name}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def getMaterials(self) -> dict:
        try:
            from core.materials import STANDARD_MATERIALS
            mats = []
            items = (STANDARD_MATERIALS.values()
                     if isinstance(STANDARD_MATERIALS, dict)
                     else STANDARD_MATERIALS)
            for m in items:
                to_dict = getattr(m, "to_dict", None)
                mats.append(_clean(to_dict() if to_dict else m))
            return {"ok": True, "materials": mats,
                    "names": self._ctrl.material_names()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def setMaterial(self, name: str) -> dict:
        try:
            self._ctrl.set_material(name)
            return {"ok": True, "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def validateProblem(self, problem_json: str) -> dict:
        try:
            from core.topo_problem import TopologyOptimizationProblem
            data = json.loads(problem_json or "{}")
            from_dict = getattr(TopologyOptimizationProblem, "from_dict", None)
            problem = from_dict(data) if from_dict else TopologyOptimizationProblem(**data)
            problem.validate()
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def importStep(self, path: str) -> dict:
        try:
            res = self._ctrl.import_model(path)
            return {"ok": True, "result": _clean(res),
                    "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def generateMesh(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            solid = p.get("solid_index")
            size = float(p.get("target_element_size", 0.0) or 0.0)
            if solid is not None:
                res = self._ctrl.generate_mesh_for_solid(int(solid), size)
            else:
                res = self._ctrl.generate_mesh(size)
            return {"ok": True, "result": _clean(res),
                    "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def setBoundaries(self, params_json: str) -> dict:
        try:
            p = json.loads(params_json or "{}")
            self._ctrl.set_simple_boundaries(
                bottom_axis=int(p.get("bottom_axis", 2)),
                load_dir=tuple(p.get("load_dir", (0, 0, 1))),
                magnitude=float(p.get("magnitude", 1000.0)))
            return {"ok": True, "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def runFea(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            backend = p.get("backend", "local")
            jid = self._submit("fea", self._ctrl.run_fea, backend=backend)
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def runOptimization(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            jid = self._submit(
                "simp", self._ctrl.run_optimization,
                volume_fraction=float(p.get("volume_fraction", 0.3)),
                max_iterations=int(p.get("max_iterations", 30)))
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def pollJob(self, job_id: str) -> dict:
        with self._lock:
            j = self._jobs.get(job_id)
            if j is None:
                return {"ok": False, "error": f"job desconocido: {job_id}"}
            return {"ok": True, "state": j["state"], "progress": j["progress"],
                    "result": j["result"], "error": j["error"]}

    def getMeshPreview(self) -> dict:
        """Teselado actual diezmado para three.js (vertices + caras)."""
        try:
            tes = getattr(self._ctrl, "current_tessellation", None)
            if not tes:
                return {"ok": False, "error": "sin teselado (importa un STEP primero)"}
            return {"ok": True, "mesh": _clean(tes),
                    "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def getSurfaceMesh(self, params_json: str = "{}") -> dict:
        """Malla de superficie (una porcion de nodos FEA) + campo escalar.

        params: {field: 'none'|'vonmises'|'displacement'|'density'}.
        Devuelve {positions, indices, values|null, min, max, field, counts}.
        Los indices de face_surface_elements apuntan a mesh.nodes, asi los
        valores nodales (von Mises, desplazamientos) mapean directo; las
        densidades SIMP (por elemento) se promedian a nodos.
        """
        import numpy as np
        try:
            p = json.loads(params_json or "{}")
            field = p.get("field", "none")
            c = self._ctrl
            mesh = getattr(c, "mesh", None)
            if not mesh:
                return {"ok": False, "error": "sin malla (mallar primero)"}
            nodes = np.asarray(mesh["nodes"], dtype=float)
            fse = mesh.get("face_surface_elements") or {}
            tris = [t for lst in fse.values() for t in lst]
            if not tris:
                return {"ok": False, "error": "malla sin superficie"}
            tris = np.asarray(tris, dtype=int)

            uniq, inv = np.unique(tris.ravel(), return_inverse=True)
            positions = nodes[uniq]
            indices = inv.reshape(-1, 3)

            values = None
            vmin = vmax = None
            if field == "vonmises":
                res = getattr(c, "result", None) or {}
                nodal = res.get("nodal_von_mises")
                if nodal is None:
                    return {"ok": False, "error": "sin resultado FEA"}
                values = np.asarray(nodal, dtype=float)[uniq]
            elif field == "displacement":
                res = getattr(c, "result", None) or {}
                disp = res.get("displacements")
                if disp is None:
                    return {"ok": False, "error": "sin resultado FEA"}
                values = np.linalg.norm(np.asarray(disp, dtype=float), axis=1)[uniq]
            elif field == "density":
                dens = getattr(c, "result_densities", None)
                if dens is None:
                    return {"ok": False, "error": "sin resultado SIMP"}
                dens = np.asarray(dens, dtype=float)
                elems = np.asarray(mesh["elements"], dtype=int)
                acc = np.zeros(len(nodes));
                cnt = np.zeros(len(nodes))
                np.add.at(acc, elems.ravel(), np.repeat(dens, 4))
                np.add.at(cnt, elems.ravel(), 1)
                values = (acc / np.maximum(cnt, 1))[uniq]
            if values is not None:
                vmin, vmax = float(values.min()), float(values.max())

            return {"ok": True,
                    "positions": _clean(positions),
                    "indices": _clean(indices),
                    "values": _clean(values) if values is not None else None,
                    "min": vmin, "max": vmax, "field": field,
                    "num_vertices": int(len(uniq)),
                    "num_triangles": int(len(indices))}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def exportStep(self, path: str) -> dict:
        try:
            res = self._ctrl.cad.export_step(self._ctrl.model_id, path)
            return {"ok": True, "result": _clean(res)}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)
