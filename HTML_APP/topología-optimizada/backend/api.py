"""API JS <-> Python para la nueva app (pywebview).

Funcionamiento: core vendorado en backend/ (autocontenido); fallback a
Topologia_Optimizada externa solo en desarrollo. Sin Qt, sin HTTP.
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
# SELF-CONTAINED (reversible): el core va vendorado en backend/core (+desktop,
# adapters, services). backend/ ya esta en sys.path, asi que `import core...`
# resuelve local sin tocar nada. Solo si falta (desarrollo), se usa la carpeta
# hermana externa como antes. Ver backend/CORE_VENDORADO.txt.
if not os.path.isdir(os.path.join(_HERE, "core")):
    _CORE = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "Topologia_Optimizada"))
    if _CORE not in sys.path:
        sys.path.insert(0, _CORE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

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
        # DECIM-ALIGN (reversible): diezmar por FILAS (vertice/triangulo
        # completos), nunca en plano. El flat[::step] anterior rompia las
        # tripletas xyz y a-b-c del teselado y el viewport quedaba en negro
        # con archivos grandes. Para volver atras: restaurar flat[::step].
        if obj.size > _budget[0]:
            step = (obj.size + _budget[0] - 1) // _budget[0]
            if obj.ndim == 1 and obj.size % 3 == 0:
                flat = obj.reshape(-1, 3)[::step].ravel()
            elif obj.ndim == 2:
                flat = obj[::step].ravel()
            else:
                flat = obj.ravel()[::step]
            truncated = True
        else:
            flat = obj.ravel()
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
        # MULTI (reversible): libreria de archivos importados en la sesion.
        # El core mantiene UN modelo activo; aqui se acumula el registro
        # {key: {filename, displayName, path}} y switch re-importa del disco
        # (el controller limpia downstream solo, como la app de escritorio).
        self._library: dict[str, dict] = {}
        self._active_key: str | None = None

    # -- utilidades -----------------------------------------------------
    def _model_stats(self) -> dict:
        """Stats reales del modelo actual: caras/triangulos/bbox de la
        teselacion y volumen en cm3 (superficie cerrada; si hay malla
        volumetrica se recalcula con los tetraedros, mas exacto)."""
        stats = {"num_faces": 0, "num_triangles": 0, "num_vertices": 0,
                 "bbox": None, "volume_cm3": 0.0,
                 "num_nodes": 0, "num_elements": 0}
        try:
            import numpy as np
            tes = getattr(self._ctrl, "current_tessellation", None) or {}
            faces = tes.get("faces") or []
            stats["num_faces"] = len(faces) if hasattr(faces, "__len__") else int(tes.get("num_faces", 0) or 0)
            stats["num_triangles"] = int(tes.get("num_triangles", 0) or 0)
            stats["num_vertices"] = int(tes.get("num_vertices", 0) or 0)
            stats["bbox"] = tes.get("bbox")
            verts = tes.get("vertices")
            idx = tes.get("indices")
            if verts is not None and idx is not None:
                v = np.asarray(verts, dtype=float).reshape(-1, 3)  # lista plana xyz
                t = np.asarray(idx, dtype=np.int64).reshape(-1, 3)
                if len(v) and len(t):
                    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
                    signed = float(np.einsum("ij,ij->i", p0, np.cross(p1, p2)).sum() / 6.0)
                    vol_mm3 = abs(signed)
                    stats["volume_cm3"] = round(vol_mm3 / 1000.0, 3)
            mesh = getattr(self._ctrl, "mesh", None) or {}
            nodes = mesh.get("nodes")
            elems = mesh.get("elements")
            if nodes is not None and elems is not None:
                nd = np.asarray(nodes, dtype=float).reshape(-1, 3)
                el = np.asarray(elems, dtype=np.int64).reshape(-1, 4)  # Tet4
                stats["num_nodes"] = int(len(nd))
                stats["num_elements"] = int(len(el))
                if len(nd) and len(el):
                    p = nd[el[:, :4]]
                    mat = np.stack([p[:, 1] - p[:, 0], p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]], axis=-1)
                    vol_mm3 = abs(float(np.linalg.det(mat).sum() / 6.0))
                    stats["volume_cm3"] = round(vol_mm3 / 1000.0, 3)
        except Exception:  # noqa: BLE001 - stats opcionales, nunca rompen el snapshot
            pass
        return stats

    def _snapshot(self) -> dict:
        c = self._ctrl
        doc = getattr(c, "document", None)
        hist = getattr(doc, "history", None)
        snap = {
            "model_name": getattr(c, "model_name", None),
            "model_id": getattr(c, "model_id", None),
            "has_mesh": getattr(c, "mesh", None) is not None,
            "has_result": getattr(c, "result", None) is not None,
            "material": getattr(c, "_material_name", None),
            "features": len(getattr(hist, "features", []) or []),
            "studies": len(getattr(doc, "studies", []) or []),
        }
        snap.update(self._model_stats())
        # SOLIDS (reversible): conteo real de cuerpos del STEP.
        try:
            solids = self.getSolids()
            snap["num_solids"] = len(solids.get("solids", [])) if solids.get("ok") else 0
        except Exception:  # noqa: BLE001
            snap["num_solids"] = 0
        return snap

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

    def _resolve_step_path(self, path: str) -> str:
        """Resuelve un nombre de fixture (p.ej. 'cono.step') a ruta real.
        Orden: ruta tal cual, backend/fixtures, raiz de Topologia_Optimizada,
        Web_App/fixtures. Solo lectura, no copia nada."""
        if path and os.path.exists(path):
            return path
        base = os.path.basename(path or "")
        candidates = [
            os.path.join(_HERE, "fixtures", base),
            os.path.abspath(os.path.join(_HERE, "..", "..", "..", "Topologia_Optimizada", base)),
            os.path.abspath(os.path.join(_HERE, "..", "..", "..", "Web_App", "fixtures", base)),
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return path

    def listFixtures(self) -> dict:
        """STEP reales disponibles para importar (sin inventar modelos)."""
        try:
            seen: dict[str, str] = {}
            dirs = [
                os.path.join(_HERE, "fixtures"),
                os.path.abspath(os.path.join(_HERE, "..", "..", "..", "Topologia_Optimizada")),
                os.path.abspath(os.path.join(_HERE, "..", "..", "..", "Web_App", "fixtures")),
            ]
            for d in dirs:
                if not os.path.isdir(d):
                    continue
                for f in sorted(os.listdir(d)):
                    if f.lower().endswith((".step", ".stp")) and f not in seen:
                        seen[f] = os.path.join(d, f)
            return {"ok": True, "fixtures": [
                {"filename": f, "path": p} for f, p in seen.items()]}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # SOLIDS (reversible): cuerpos del STEP, uno por objeto (list_solids del core).
    def getSolids(self) -> dict:
        try:
            c = self._ctrl
            if not getattr(c, "model_id", None):
                return {"ok": True, "solids": []}
            solids = c.cad.list_solids(c.model_id) or []
            return {"ok": True, "solids": _clean(solids)}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def importStep(self, path: str) -> dict:
        try:
            real = self._resolve_step_path(path)
            res = self._ctrl.import_model(real)
            key = self._register_library(os.path.basename(real), real)
            return {"ok": True, "result": _clean(res),
                    "snapshot": self._snapshot(), "key": key,
                    "library": self._library_view()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # MULTI (reversible): registro y cambio de modelo activo.
    def _register_library(self, filename: str, path: str) -> str:
        key = f"{os.path.basename(filename)}_{uuid.uuid4().hex[:6]}"
        self._library[key] = {"key": key, "filename": os.path.basename(filename),
                              "displayName": filename.replace(".step", "").replace(".stp", "")
                              .replace("_", " ").replace("-", " ").upper() or key,
                              "path": path}
        self._active_key = key
        return key

    def _library_view(self) -> list:
        return [{"key": k, "filename": v["filename"],
                 "displayName": v["displayName"],
                 "active": (k == self._active_key)}
                for k, v in self._library.items()]

    def listLibrary(self) -> dict:
        try:
            return {"ok": True, "library": self._library_view(),
                    "activeKey": self._active_key}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def switchModel(self, key: str) -> dict:
        """Activa otro archivo de la libreria (re-importa del disco;
        aguas abajo —malla/estudios— se limpian como en el desktop)."""
        try:
            entry = self._library.get(str(key))
            if entry is None or not os.path.exists(entry["path"]):
                return {"ok": False, "error": f"modelo desconocido o ausente: {key}"}
            res = self._ctrl.import_model(entry["path"])
            self._active_key = str(key)
            return {"ok": True, "result": _clean(res),
                    "snapshot": self._snapshot(), "key": str(key),
                    "library": self._library_view()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def removeModel(self, key: str) -> dict:
        try:
            key = str(key)
            if key not in self._library:
                return {"ok": False, "error": f"modelo desconocido: {key}"}
            was_active = (key == self._active_key)
            del self._library[key]
            if was_active:
                try:
                    self._ctrl.close_model()
                except Exception:  # noqa: BLE001
                    pass
                self._active_key = None
            return {"ok": True, "library": self._library_view(),
                    "activeKey": self._active_key,
                    "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # UPLOAD-STEP (reversible): importar un archivo local real enviado desde
    # el frontend (drag&drop). Se guarda en backend/uploads y se importa como
    # cualquier STEP: teselado + solidos + viewport reales.
    def importStepBytes(self, params_json: str = "{}") -> dict:
        import base64
        try:
            p = json.loads(params_json or "{}")
            filename = os.path.basename(str(p.get("filename", "upload.step")))
            if not filename.lower().endswith((".step", ".stp")):
                filename += ".step"
            raw = base64.b64decode(str(p.get("base64", "")))
            if len(raw) > 50 * 1024 * 1024:
                return {"ok": False, "error": "archivo mayor a 50 MB"}
            updir = os.path.join(_HERE, "uploads")
            os.makedirs(updir, exist_ok=True)
            dest = os.path.join(updir, filename)
            with open(dest, "wb") as fh:
                fh.write(raw)
            res = self._ctrl.import_model(dest)
            key = self._register_library(filename, dest)
            return {"ok": True, "result": _clean(res),
                    "snapshot": self._snapshot(), "key": key,
                    "library": self._library_view()}
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
            conds = self._resolve_conditions(p.get("condition_ids"))
            if conds is not None:
                jid = self._submit("fea", self._ctrl.run_fea,
                                   conditions=conds, backend=backend)
            else:
                jid = self._submit("fea", self._ctrl.run_fea, backend=backend)
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def runOptimization(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            conds = self._resolve_conditions(p.get("condition_ids"))
            kwargs = dict(
                volume_fraction=float(p.get("volume_fraction", 0.3)),
                max_iterations=int(p.get("max_iterations", 30)),
                penalization=float(p.get("penalization", 3.0)),
                filter_radius=float(p.get("filter_radius", 1.5)),
                tolerance=float(p.get("tolerance", 1e-3)))
            if conds is not None:
                kwargs["conditions"] = conds
            halo = p.get("halo_radius")
            if halo is not None:
                kwargs["halo_radius"] = float(halo)
            jid = self._submit("simp", self._ctrl.run_optimization, **kwargs)
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- condiciones reutilizables (core/conditions.py, por id, sin duplicar)
    def _resolve_conditions(self, ids):
        """ids -> objetos Condition compartidos, o None si no se piden."""
        if not ids:
            return None
        mgr = getattr(self._ctrl, "conditions", None)
        if mgr is None:
            raise RuntimeError("controller sin ConditionManager")
        return mgr.resolve([str(i) for i in ids])

    def createCondition(self, condition_json: str) -> dict:
        """Crea una condicion reutilizable (load/elasticity/obstruction/
        protected_region) y la registra en el ConditionManager."""
        try:
            from core.conditions import condition_from_dict
            cond = condition_from_dict(json.loads(condition_json or "{}"))
            cid = self._ctrl.conditions.add(cond)
            return {"ok": True, "id": cid,
                    "condition": _clean(cond.to_dict())}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def listConditions(self) -> dict:
        try:
            mgr = getattr(self._ctrl, "conditions", None)
            items = [c.to_dict() for c in (mgr.all if mgr else [])]
            return {"ok": True, "conditions": _clean(items)}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def clearConditions(self) -> dict:
        try:
            mgr = getattr(self._ctrl, "conditions", None)
            if mgr is not None:
                mgr.clear()
            return {"ok": True, "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- diseno generativo (core/generative_engine.py, escenario A/B real)
    def runGenerativeDesign(self, params_json: str = "{}") -> dict:
        try:
            from core.generative import GenerativeDesignStudy
            from core.generative_engine import (
                GenerativeDesignEngine, run_generative_design)
            from core.optimization_studies import TopOptParameters
            p = json.loads(params_json or "{}")
            if self._ctrl.mesh is None:
                raise RuntimeError("Sin malla. Malla primero.")
            study = GenerativeDesignStudy(name=p.get("name", "Generative Design"))
            study.scenario = str(p.get("scenario", "A")).upper()
            study.conditions = [str(i) for i in (p.get("condition_ids") or [])]
            op = TopOptParameters()
            for k in ("volume_fraction", "max_iterations", "penalization",
                      "filter_radius", "convergence_tolerance"):
                if p.get(k) is not None:
                    setattr(op, k, p[k])
            study.optimization_params = op
            if p.get("resolution") is not None:
                study.design_space.resolution = float(p["resolution"])
            c = self._ctrl
            engine = GenerativeDesignEngine(
                model_id=c.model_id,
                mesh_nodes=c.mesh_nodes,
                mesh_elements=c.mesh_elements,
                material=c.material(),
                condition_manager=c.conditions,
                model_shape=c.cad.get_model_shape(c.model_id) if c.model_id else None,
                face_surface_elements=(c.mesh.get("face_surface_elements") or None),
                physical_groups=(c.mesh.get("physical_groups") or None),
            )
            step_path = p.get("step_path")
            jid = self._submit("generative", run_generative_design,
                               study, c.conditions, engine,
                               step_path=step_path)
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def registerReconstruction(self, job_id: str) -> dict:
        """Registra el solido B-Rep de un job generativo como CADModel activo
        (Document/historial/viewport). Best-effort: nunca rompe el estudio."""
        try:
            with self._lock:
                j = self._jobs.get(job_id)
                res = dict(j["result"]) if j and j["result"] else None
            if not res:
                return {"ok": False, "error": "job sin resultado"}
            recon = res.get("reconstruction") or {}
            # El solido crudo no viaja en _clean (serializado a str); se
            # re-ejecuta la reconstruccion solo si hay densidades.
            info = self._ctrl._register_reconstruction_model(recon)
            return {"ok": True, "registered": _clean(info),
                    "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- operaciones CAD (boolean/transform/mirror/pattern, geometria real)
    def cadOperation(self, params_json: str = "{}") -> dict:
        try:
            from core.commands import (BooleanCommand, MirrorCommand,
                                       PatternCommand, TransformCommand)
            p = json.loads(params_json or "{}")
            kind = str(p.get("op", "")).lower()
            cls = {"boolean": BooleanCommand, "transform": TransformCommand,
                   "mirror": MirrorCommand, "pattern": PatternCommand}.get(kind)
            if cls is None:
                return {"ok": False,
                        "error": f"op desconocida: {kind} "
                                 "(boolean|transform|mirror|pattern)"}
            cmd = cls()
            for k, v in p.items():
                if k != "op":
                    cmd.set_parameter(k, v)
            res = self._ctrl.execute_command(cmd)
            ok = bool(getattr(res, "success", False))
            if not ok:
                return {"ok": False,
                        "error": getattr(res, "error_message", "operacion fallo")}
            return {"ok": True,
                    "result": _clean(getattr(res, "data", {}) or {}),
                    "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def generateAdaptiveMesh(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            res = self._ctrl.generate_adaptive_mesh(
                base_size=float(p.get("base_size", 5.0)),
                min_size=float(p.get("min_size", 0.5)),
                use_density=bool(p.get("use_density", True)))
            return {"ok": True, "result": _clean(res),
                    "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def validateState(self) -> dict:
        """Estado real del pipeline (modelo, malla, BCs, estudios, resultado),
        equivalente al dialogo Validar del desktop."""
        try:
            c = self._ctrl
            mgr = getattr(c, "conditions", None)
            doc = getattr(c, "document", None)
            studies = getattr(doc, "studies", []) or []
            report = {
                "has_model": bool(getattr(c, "model_id", None)),
                "model_name": getattr(c, "model_name", None),
                "has_mesh": getattr(c, "mesh", None) is not None,
                "num_nodes": int(len(c.mesh_nodes)) if getattr(c, "mesh", None) is not None else 0,
                "has_legacy_forces": bool(getattr(c, "forces", None)),
                "has_legacy_constraints": bool(getattr(c, "constraints", None)),
                "conditions": len(mgr.all) if mgr is not None else 0,
                "studies": len(studies),
                "has_result": getattr(c, "result", None) is not None,
                "has_densities": getattr(c, "result_densities", None) is not None,
            }
            missing = [k for k, v in
                       (("modelo STEP", report["has_model"]),
                        ("malla", report["has_mesh"]),
                        ("condiciones o BCs",
                         report["conditions"] > 0 or report["has_legacy_forces"]),
                        ("resultado", report["has_result"] or report["has_densities"]))
                       if not v]
            report["valid"] = not missing
            report["missing"] = missing
            return {"ok": True, "report": report, "snapshot": self._snapshot()}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- solver lineal local (directo spsolve vs CG iterativo, core/fea.py) --
    def _run_fea_with_linear_solver(self, linear_solver: str) -> dict:
        c = self._ctrl
        nodes, elements, force, fixed = c.build_problem()
        mat = c.material()
        from core.fea import solve_fea
        result = solve_fea(
            nodes=nodes, elements=elements,
            young_modulus=mat.young_modulus,
            poisson_ratio=mat.poisson_ratio,
            forces_dofs=[(int(i), float(v)) for i, v in enumerate(force) if v != 0.0],
            fixed_dofs=fixed.tolist(),
            linear_solver=linear_solver)
        c.result = result
        return result

    def runFeaIterative(self, params_json: str = "{}") -> dict:
        """FEA local con solver lineal configurable ('direct'|'cg').
        Aprovecha el escalon iterativo documentado antes de saltar a Kratos."""
        try:
            p = json.loads(params_json or "{}")
            ls = str(p.get("linear_solver", "cg")).lower()
            if ls not in ("direct", "cg"):
                return {"ok": False,
                        "error": f"linear_solver desconocido: {ls} (direct|cg)"}
            jid = self._submit("fea_iter", self._run_fea_with_linear_solver, ls)
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- licenciamiento (core/license.py: estados + gracia offline) ----------
    def getLicense(self) -> dict:
        try:
            from core.license import LicenseManager
            if not hasattr(self, "_license"):
                self._license = LicenseManager()
            mgr = self._license
            state = mgr.validate()
            return {"ok": True, "state": state.value,
                    "is_licensed": mgr.is_licensed,
                    "metadata": _clean(mgr.metadata)}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- termico estacionario real (core/thermal.py via ThermalAnalysis) -----
    def _run_thermal(self, t_cold: float, t_hot: float,
                     conductivity: float) -> dict:
        import numpy as np
        from core.cae_studies import (ThermalAnalysis, ThermalBoundary,
                                      ThermalBoundaryType)
        c = self._ctrl
        if c.mesh is None:
            raise RuntimeError("Sin malla. Malla primero.")
        nodes = np.asarray(c.mesh_nodes, dtype=float)
        zmin, zmax = float(nodes[:, 2].min()), float(nodes[:, 2].max())
        span = max(zmax - zmin, 1e-9)
        tol = 1e-3 * span
        bottom = [i for i, z in enumerate(nodes[:, 2]) if abs(z - zmin) <= tol]
        top = [i for i, z in enumerate(nodes[:, 2]) if abs(z - zmax) <= tol]
        if not bottom or not top:
            raise RuntimeError("No se pudieron resolver caras fria/caliente.")
        study = ThermalAnalysis(name="Thermal V2")
        study.model_id = c.model_id
        mat = c.material()
        study.material = mat if mat.has_thermal_properties else \
            mat.with_thermal_properties(float(conductivity))
        study.add_thermal_boundary(ThermalBoundary(
            name="Cara fria", boundary_type=ThermalBoundaryType.TEMPERATURE,
            magnitude=float(t_cold), metadata={"nodes": bottom}))
        study.add_thermal_boundary(ThermalBoundary(
            name="Cara caliente", boundary_type=ThermalBoundaryType.TEMPERATURE,
            magnitude=float(t_hot), metadata={"nodes": top}))
        res = study.execute_on_mesh(nodes, np.asarray(c.mesh_elements, dtype=int))
        out = res.to_dict()
        out["t_cold_nodes"] = len(bottom)
        out["t_hot_nodes"] = len(top)
        return out

    def runThermal(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            jid = self._submit(
                "thermal", self._run_thermal,
                float(p.get("t_cold", 300.0)), float(p.get("t_hot", 400.0)),
                float(p.get("conductivity", 45.0)))
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- modal real (core/fea.solve_modal via ModalAnalysis) -----------------
    def _run_modal(self, mode_count: int) -> dict:
        import numpy as np
        from core.cae_studies import ConstraintCase, ModalAnalysis
        c = self._ctrl
        if c.mesh is None:
            raise RuntimeError("Sin malla. Malla primero.")
        nodes = np.asarray(c.mesh_nodes, dtype=float)
        fixed = np.asarray(c._apply_constraints(nodes)).tolist()
        study = ModalAnalysis(name="Modal V2", mode_count=int(mode_count))
        study.model_id = c.model_id
        study.material = c.material()
        study.constraints = [ConstraintCase(name="Soporte",
                                            constraint_type="fixed")]
        return study.execute_on_mesh(
            nodes, np.asarray(c.mesh_elements, dtype=int),
            fixed_dofs=fixed).to_dict()

    def runModal(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            jid = self._submit("modal", self._run_modal,
                               int(p.get("mode_count", 5)))
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- Kratos dentro del flujo: verificacion cruzada + SIMP verificado ----
    # NOTA honesta: el nucleo SIMP (core/topopt.SIMPSolver) esta acoplado a su
    # FEASolver interno y el callable de Kratos devuelve un dict, no esa
    # interfaz; por decision documentada de la predecesora no se refactoriza.
    # Kratos se aprovecha como oraculo mutuo: mismo caso fisico en ambos
    # motores + comparacion automatizada (dual-motor de PROJECT_STATUS.md).
    def _cross_check(self, condition_ids) -> dict:
        import numpy as np
        c = self._ctrl
        conds = self._resolve_conditions(condition_ids)
        local = dict(c.run_fea(conditions=conds, backend="local"))
        try:
            krat = dict(c.run_fea(conditions=conds, backend="kratos"))
        except Exception as exc:  # noqa: BLE001 - Kratos opcional
            local["kratos_error"] = f"{type(exc).__name__}: {exc}"
            local["cross_check"] = "kratos_no_disponible"
            return local
        cl = float(local.get("compliance", 0.0) or 0.0)
        ck = float(krat.get("compliance", 0.0) or 0.0)
        rel = abs(cl - ck) / max(abs(cl), 1e-12)
        ul = np.asarray(local.get("displacements", []), dtype=float).ravel()
        uk = np.asarray(krat.get("displacements", []), dtype=float).ravel()
        urel = (float(np.linalg.norm(ul - uk) / max(np.linalg.norm(ul), 1e-12))
                if ul.size and ul.size == uk.size else None)
        return {"local_compliance": cl, "kratos_compliance": ck,
                "rel_compliance_diff": rel,
                "rel_displacement_diff": urel,
                "agreement_1e6": rel <= 1e-6,
                "local_engine": local.get("engine"),
                "kratos_success": krat.get("success")}

    def runCrossCheck(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            jid = self._submit("xcheck", self._cross_check,
                               p.get("condition_ids"))
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    def _simp_kratos_verified(self, simp_kwargs: dict,
                              condition_ids) -> dict:
        c = self._ctrl
        conds = self._resolve_conditions(condition_ids)
        simp = dict(c.run_optimization(conditions=conds, **simp_kwargs)
                    if conds is not None
                    else c.run_optimization(**simp_kwargs))
        check = self._cross_check(condition_ids)
        simp["kratos_verification"] = check
        return simp

    def runSimpKratosVerified(self, params_json: str = "{}") -> dict:
        """SIMP local + verificacion cruzada Kratos del mismo caso fisico."""
        try:
            p = json.loads(params_json or "{}")
            kwargs = dict(
                volume_fraction=float(p.get("volume_fraction", 0.3)),
                max_iterations=int(p.get("max_iterations", 30)),
                penalization=float(p.get("penalization", 3.0)),
                filter_radius=float(p.get("filter_radius", 1.5)),
                tolerance=float(p.get("tolerance", 1e-3)))
            jid = self._submit("simp_verify", self._simp_kratos_verified,
                               kwargs, p.get("condition_ids"))
            return {"ok": True, "jobId": jid}
        except Exception as exc:  # noqa: BLE001
            return _err(exc)

    # -- SIMP vendorizado con motor inyectable (local | kratos-in-loop) ----
    # Copia del nucleo en backend/vendored (la predecesora no se toca):
    # con engine="kratos" el equilibrio K(rho)*u=F de CADA iteracion lo
    # resuelve Kratos con E penalizado por elemento.
    def _simp_loop(self, simp_kwargs: dict, engine: str,
                   halo_radius) -> dict:
        import numpy as np
        from vendored.simp import SIMPSolver as VendoredSIMP
        c = self._ctrl
        if c.mesh is None:
            raise RuntimeError("Sin malla. Malla primero.")
        nodes, elements, force, fixed = c.build_problem()
        mat = c.material()
        fea_solver = None
        if engine == "kratos":
            from vendored.kratos_simp_fea import KratosSimpFEA
            fea_solver = KratosSimpFEA(
                np.asarray(nodes, dtype=float),
                np.asarray(elements, dtype=int),
                mat.young_modulus, mat.poisson_ratio, mat.density,
                penalization=float(simp_kwargs.get("penalization", 3.0)))
        solver = VendoredSIMP(
            nodes=nodes, elements=elements,
            young_modulus=mat.young_modulus,
            poisson_ratio=mat.poisson_ratio,
            volfrac=float(simp_kwargs.get("volume_fraction", 0.3)),
            penalization=float(simp_kwargs.get("penalization", 3.0)),
            filter_radius=float(simp_kwargs.get("filter_radius", 1.5)),
            fea_solver=fea_solver)
        # MULTICARGA: casos separados (Kratos reconstruye su RHS por caso).
        cases, weights = c._load_case_vectors(
            np.asarray(nodes), int(np.asarray(nodes).shape[0] * 3))
        if len(cases) > 1:
            solver.set_loads(cases, weights)
        else:
            solver.set_load(force)
        solver.set_fixed_dofs(fixed)
        if halo_radius is not None and (c._load_nodes or c._bot_nodes):
            solver.protect_elements_near_nodes(
                list(set(c._load_nodes + c._bot_nodes)),
                radius=float(halo_radius) if halo_radius > 0 else None)
        try:
            result = solver.optimize(
                max_iterations=int(simp_kwargs.get("max_iterations", 30)),
                tolerance=float(simp_kwargs.get("tolerance", 1e-3)))
        except Exception as exc:
            from desktop.pipeline.controller import PipelineError
            raise PipelineError(f"Optimizacion ({engine}) fallo: {exc}")
        c.result = result
        c.result_densities = np.asarray(result["densities"], dtype=float)
        return result

    def runSimpLoop(self, params_json: str = "{}") -> dict:
        try:
            p = json.loads(params_json or "{}")
            engine = str(p.get("engine", "local")).lower()
            if engine not in ("local", "kratos"):
                return {"ok": False,
                        "error": f"engine desconocido: {engine} (local|kratos)"}
            kwargs = {k: p.get(k) for k in (
                "volume_fraction", "max_iterations", "penalization",
                "filter_radius", "tolerance") if p.get(k) is not None}
            jid = self._submit("simp_loop", self._simp_loop,
                               kwargs, engine, p.get("halo_radius"))
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
