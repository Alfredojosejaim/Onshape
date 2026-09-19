// Puente HTML -> backend Python (pywebview) con fallback mock.
//
// Uso desde cualquier pantalla:
//   import { backend } from '../lib/bridge';
//   const r = await backend.getMaterials();   // {ok, materials, names}
//   const s = await backend.getSnapshot();
//
// En vite dev sin pywebview responde mocks para no romper la UI.
import type { JsonRecord, JsonValue } from '../types';
import type { ApiSnapshot, LoadBoundaries } from './realdata';
import { isBridgeFunction } from './guards';

declare global {
  interface Window { pywebview?: { api: Record<string, (...a: string[]) => Promise<JsonValue>> } }
}

/** Envelope del bridge: éxito con payload T, o error/mock sin payload.
 *  La UI siempre lee r.ok primero; r.error/r.mock solo existen en esos
 *  caminos, por eso son opcionales. */
type Ok<T = unknown> = { ok: boolean; error?: string; mock?: boolean } & T;

/** Parámetros de setBoundaries: dirección+magnitud + eje inferior fijo. */
export interface SetBoundariesParams extends LoadBoundaries {
  bottom_axis: number;
}

/** Respuesta de pollJob del backend (campos JSON opcionales). */
export interface PollJobPayload {
  state?: string;
  progress?: number;
  result?: JsonValue;
  error?: string | null;
  mock?: boolean;
  stale?: boolean;
  stale_sec?: number;
}

/** Entrada de librería de la pieza generada registrada. */
export interface ReconstructionEntry {
  key?: string;
  filename?: string;
  displayName?: string;
}

/** Registro de la reconstrucción generativa como modelo activo. */
export interface RegisterReconstructionResult {
  registered?: { model_id?: string; model_name?: string };
  key?: string | null;
  entry?: ReconstructionEntry | null;
  snapshot?: ApiSnapshot;
  error?: string;
  reason?: JsonValue;
}

/** Respuesta de generateMesh (snapshot + posible fallback del mesher). */
export interface GenerateMeshResult {
  snapshot?: ApiSnapshot;
  result?: { fallback?: boolean; mesher?: string; fallback_reason?: string };
  error?: string;
}

/** Resultado de importar/subir un modelo (snapshot + clave de librería). */
export interface ImportResult {
  snapshot?: ApiSnapshot;
  key?: string;
}

/** Resultado de eliminar un modelo (librería restante + activo). */
export interface RemoveModelResult extends ImportResult {
  library?: { key: string; filename: string; displayName: string; active: boolean }[];
  activeKey?: string | null;
}

/** Resultado de una operación de malla (stats solo lectura para la UI). */
export interface MeshToolResult {
  stats?: JsonRecord;
}

function hasBridge(): boolean {
  return typeof window !== 'undefined' && !!window.pywebview?.api;
}

async function call<T>(method: string, ...args: string[]): Promise<Ok<T>> {
  if (!hasBridge()) return mock<T>(method);
  const fn = window.pywebview!.api[method];

  // BRIDGE-GUARD (reversible): si el metodo no esta expuesto por el host
  // (whitelist desactualizada / bundle viejo), devolver error explicito en vez
  // de un TypeError opaco que la UI mostraba como fallo de conexion.
  if (!isBridgeFunction(fn)) {
    // SAFETY: el envelope {ok:false, error} es el contrato que toda la UI
    // consume (primero r.ok, luego los campos de éxito); sin bridge no hay
    // campos de éxito que preservar.
    return { ok: false, error: `método no expuesto por el backend: ${method}` } as Ok<T>;
  }

  try {
    // SAFETY: pywebview serializa la respuesta a JSON y el backend siempre
    // responde el envelope {ok, ...}; los campos de éxito se validan por uso
    // (r.ok) y por los mapeos de realdata.ts que devuelven null si faltan.
    return (await fn(...args)) as Ok<T>;
  } catch (e) {
    // SAFETY: camino de excepción del transporte; mismo contrato de error.
    return { ok: false, error: String(e) } as Ok<T>;
  }
}

function mock<T>(method: string): Ok<T> {
  console.warn(`[bridge] sin pywebview — mock para ${method}`);

  const base = {
    getSnapshot: { snapshot: { model_name: 'demo.step', has_mesh: false, has_result: false } },
    getMaterials: { materials: [], names: ['steel', 'aluminum', 'titanium'] },
    pollJob: { state: 'done', progress: 1, result: null, error: null },
    getNavProfiles: {
      profiles: [
        { name: 'autocad', display_name: 'AutoCAD' },
        { name: 'onshape', display_name: 'Onshape' },
        { name: 'fusion360', display_name: 'Fusion 360' },
        { name: 'blender', display_name: 'Blender' },
      ],
      current: 'autocad',
    },
    setNavProfile: { ok: true },
  };

  // P-A (reversible): toda respuesta mock va marcada con mock:true para que
  // la UI pueda etiquetarla MOCK-FALLBACK (AGENTS.md) en vez de confundirla
  // con un éxito real. Para volver atrás: quitar la bandera + su chequeo
  // en jobs.ts.
  // SAFETY: el mock solo se invoca con nombres de método que el backend
  // expone; la entrada existe en la tabla para esos nombres.
  const key = method as keyof typeof base;

  // SAFETY: el mock replica el envelope {ok:true, mock:true, ...payload} del
  // backend; los mapeos de realdata.ts devuelven null si un campo falta.
  return { ok: true, mock: true, ...base[key] } as Ok<T>;
}

export const backend = {
  hasBridge,
  getSnapshot: () => call<{ snapshot: unknown }>('getSnapshot'),
  getMaterials: () => call<{ materials: unknown[]; names: string[] }>('getMaterials'),
  setMaterial: (name: string) => call('setMaterial', name),
  validateProblem: (problemJson: string) => call('validateProblem', problemJson),
  importStep: (path: string) => call<ImportResult>('importStep', path),
  // UPLOAD-STEP (reversible): importar un archivo local real al backend.
  importStepBytes: (params: { filename: string; base64: string }) =>
    call<ImportResult>('importStepBytes', JSON.stringify(params)),
  // SOLIDS (reversible): cuerpos del STEP, uno por objeto.
  getSolids: () => call<{ solids: unknown[] }>('getSolids'),
  // MULTI (reversible): libreria acumulativa de modelos importados.
  listLibrary: () =>
    call<{ library: { key: string; filename: string; displayName: string; active: boolean }[]; activeKey: string | null }>('listLibrary'),
  switchModel: (key: string) => call<ImportResult>('switchModel', key),
  removeModel: (key: string) => call<RemoveModelResult>('removeModel', key),
  listFixtures: () =>
    call<{ fixtures: { filename: string; path: string }[] }>('listFixtures'),
  generateMesh: (params = {}) =>
    call<GenerateMeshResult>('generateMesh', JSON.stringify(params)),
  setBoundaries: (params: SetBoundariesParams) =>
    call('setBoundaries', JSON.stringify(params)),
  runFea: (params = {}) => call<{ jobId: string }>('runFea', JSON.stringify(params)),
  runOptimization: (params = {}) =>
    call<{ jobId: string }>('runOptimization', JSON.stringify(params)),
  pollJob: (jobId: string) => call<PollJobPayload>('pollJob', jobId),
  getMeshPreview: () => call<{ mesh: unknown }>('getMeshPreview'),
  getSurfaceMesh: (params = {}) =>
    call<{
      positions: JsonValue;
      indices: JsonValue;
      values: JsonValue;
      min: number | null;
      max: number | null;
      field: string;
      num_vertices: number;
      num_triangles: number;
    }>('getSurfaceMesh', JSON.stringify(params)),
  exportStep: (path: string) => call('exportStep', path),
  // Enfoque real del core (sin UI): condiciones, generativo, CAD, validación.
  createCondition: (conditionJson: string) =>
    call<{ id: string }>('createCondition', conditionJson),
  listConditions: () => call<{ conditions: unknown[] }>('listConditions'),
  clearConditions: () => call('clearConditions'),
  deleteCondition: (id: string) =>
    call<{ id: string; conditions: unknown[] }>('deleteCondition', id),
  // UNDO-REDO (reversible): deshacer/rehacer última operación destructiva
  // (modelo/condición). Responde librería + snapshot + condiciones para
  // refrescar la UI. Para volver atrás: quitar + endpoints + uso en App.
  undo: () => call<{
    label?: string; library: { key: string; filename: string; displayName: string; active: boolean }[];
    activeKey: string | null; snapshot: ApiSnapshot; conditions: { id: string; name: string; type: string }[];
    canUndo: string | null; canRedo: string | null;
  }>('undo'),
  redo: () => call<{
    label?: string; library: { key: string; filename: string; displayName: string; active: boolean }[];
    activeKey: string | null; snapshot: ApiSnapshot; conditions: { id: string; name: string; type: string }[];
    canUndo: string | null; canRedo: string | null;
  }>('redo'),
  runGenerativeDesign: (params = {}) =>
    call<{ jobId: string }>('runGenerativeDesign', JSON.stringify(params)),
  registerReconstruction: (jobId: string) =>
    call<RegisterReconstructionResult>('registerReconstruction', jobId),
  cadOperation: (params: JsonRecord) =>
    call('cadOperation', JSON.stringify(params)),
  generateAdaptiveMesh: (params = {}) =>
    call('generateAdaptiveMesh', JSON.stringify(params)),
  validateState: () => call<{ report: unknown }>('validateState'),
  // V2-NEW-START (reversible: borrar hasta V2-NEW-END + src/components/v2/)
  runFeaIterative: (params = {}) =>
    call<{ jobId: string }>('runFeaIterative', JSON.stringify(params)),
  getLicense: () =>
    call<{ state: string; is_licensed: boolean; metadata: unknown }>('getLicense'),
  runThermal: (params = {}) =>
    call<{ jobId: string }>('runThermal', JSON.stringify(params)),
  runModal: (params = {}) =>
    call<{ jobId: string }>('runModal', JSON.stringify(params)),
  runCrossCheck: (params = {}) =>
    call<{ jobId: string }>('runCrossCheck', JSON.stringify(params)),
  runSimpKratosVerified: (params = {}) =>
    call<{ jobId: string }>('runSimpKratosVerified', JSON.stringify(params)),
  runSimpLoop: (params = {}) =>
    call<{ jobId: string }>('runSimpLoop', JSON.stringify(params)),
  // V2-NEW-END
  // FASE3-START (reversible): postproceso (FoS + comparativa). Para volver
  // atrás: borrar hasta FASE3-END + src/components/CompareTable.tsx +
  // SafetyCard.tsx y su uso en RightPanel.tsx.
  getSafetySummary: (params = {}) =>
    call<{ summary: { min_fos: number | null; mean_fos: number | null; count: number; below_threshold: number; threshold: number } }>(
      'getSafetySummary', JSON.stringify(params)),
  compareStudies: () =>
    call<{ rows: JsonRecord[]; count: number }>('compareStudies'),
  // FASE3-END
  // MALLA-TOOLS-START (reversible): diagnostico + reparacion de mallas
  // importadas (STL/OBJ/PLY/3MF). Para volver atras: borrar hasta
  // MALLA-TOOLS-END + metodos Api + whitelist.
  meshQualityReport: (params = {}) =>
    call<{ report: JsonRecord }>('meshQualityReport', JSON.stringify(params)),
  repairMesh: (params = {}) =>
    call<MeshToolResult>('repairMesh', JSON.stringify(params)),
  smoothMesh: (params = {}) =>
    call<MeshToolResult>('smoothMesh', JSON.stringify(params)),
  decimateMesh: (params = {}) =>
    call<MeshToolResult>('decimateMesh', JSON.stringify(params)),
  remeshMesh: (params = {}) =>
    call<MeshToolResult>('remeshMesh', JSON.stringify(params)),
  // MALLA-TOOLS-END
  // UPLOAD-CHUNKED-START (reversible): archivos grandes por partes.
  beginUpload: (filename: string) =>
    call<{ upload_id: string }>('beginUpload', JSON.stringify({ filename })),
  uploadChunk: (params: { upload_id: string; base64: string; last: boolean }) =>
    call<ImportResult & { received?: number }>('uploadChunk', JSON.stringify(params)),
  // UPLOAD-CHUNKED-END
  getNavProfiles: () =>
    call<{
      profiles: { name: string; display_name: string }[];
      current: string;
    }>('getNavProfiles'),
  setNavProfile: (name: string) => call('setNavProfile', name),
};
