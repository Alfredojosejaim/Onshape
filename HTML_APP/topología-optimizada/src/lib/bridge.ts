// Puente HTML -> backend Python (pywebview) con fallback mock.
//
// Uso desde cualquier pantalla:
//   import { backend } from '../lib/bridge';
//   const r = await backend.getMaterials();   // {ok, materials, names}
//   const s = await backend.getSnapshot();
//
// En vite dev sin pywebview responde mocks para no romper la UI.
declare global {
  interface Window { pywebview?: { api: Record<string, (...a: never[]) => Promise<unknown>> } }
}

type Ok<T = unknown> = { ok: boolean } & T;

function hasBridge(): boolean {
  return typeof window !== 'undefined' && !!window.pywebview?.api;
}

async function call<T>(method: string, ...args: never[]): Promise<Ok<T>> {
  if (!hasBridge()) return mock<T>(method);
  try {
    return (await window.pywebview!.api[method](...args)) as Ok<T>;
  } catch (e) {
    return { ok: false, error: String(e) } as unknown as Ok<T>;
  }
}

function mock<T>(method: string): Ok<T> {
  console.warn(`[bridge] sin pywebview — mock para ${method}`);
  const base: Record<string, unknown> = {
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
  return { ok: true, ...((base[method] as Record<string, unknown> | undefined) ?? {}) } as unknown as Ok<T>;
}

export const backend = {
  hasBridge,
  getSnapshot: () => call<{ snapshot: unknown }>('getSnapshot'),
  getMaterials: () => call<{ materials: unknown[]; names: string[] }>('getMaterials'),
  setMaterial: (name: string) => call('setMaterial', name as never),
  validateProblem: (problemJson: string) => call('validateProblem', problemJson as never),
  importStep: (path: string) => call('importStep', path as never),
  // UPLOAD-STEP (reversible): importar un archivo local real al backend.
  importStepBytes: (params: { filename: string; base64: string }) =>
    call('importStepBytes', JSON.stringify(params) as never),
  // SOLIDS (reversible): cuerpos del STEP, uno por objeto.
  getSolids: () => call<{ solids: unknown[] }>('getSolids'),
  // MULTI (reversible): libreria acumulativa de modelos importados.
  listLibrary: () =>
    call<{ library: { key: string; filename: string; displayName: string; active: boolean }[]; activeKey: string | null }>('listLibrary'),
  switchModel: (key: string) => call('switchModel', key as never),
  removeModel: (key: string) => call('removeModel', key as never),
  listFixtures: () =>
    call<{ fixtures: { filename: string; path: string }[] }>('listFixtures'),
  generateMesh: (params = {}) =>
    call('generateMesh', JSON.stringify(params) as never),
  setBoundaries: (params: object) =>
    call('setBoundaries', JSON.stringify(params) as never),
  runFea: (params = {}) => call<{ jobId: string }>('runFea', JSON.stringify(params) as never),
  runOptimization: (params = {}) =>
    call<{ jobId: string }>('runOptimization', JSON.stringify(params) as never),
  pollJob: (jobId: string) => call('pollJob', jobId as never),
  getMeshPreview: () => call<{ mesh: unknown }>('getMeshPreview'),
  getSurfaceMesh: (params = {}) =>
    call<{
      positions: unknown;
      indices: unknown;
      values: unknown;
      min: number | null;
      max: number | null;
      field: string;
      num_vertices: number;
      num_triangles: number;
    }>('getSurfaceMesh', JSON.stringify(params) as never),
  exportStep: (path: string) => call('exportStep', path as never),
  // Enfoque real del core (sin UI): condiciones, generativo, CAD, validación.
  createCondition: (conditionJson: string) =>
    call<{ id: string }>('createCondition', conditionJson as never),
  listConditions: () => call<{ conditions: unknown[] }>('listConditions'),
  clearConditions: () => call('clearConditions'),
  runGenerativeDesign: (params = {}) =>
    call<{ jobId: string }>('runGenerativeDesign', JSON.stringify(params) as never),
  registerReconstruction: (jobId: string) =>
    call('registerReconstruction', jobId as never),
  cadOperation: (params: object) =>
    call('cadOperation', JSON.stringify(params) as never),
  generateAdaptiveMesh: (params = {}) =>
    call('generateAdaptiveMesh', JSON.stringify(params) as never),
  validateState: () => call<{ report: unknown }>('validateState'),
  // V2-NEW-START (reversible: borrar hasta V2-NEW-END + src/components/v2/)
  runFeaIterative: (params = {}) =>
    call<{ jobId: string }>('runFeaIterative', JSON.stringify(params) as never),
  getLicense: () =>
    call<{ state: string; is_licensed: boolean; metadata: unknown }>('getLicense'),
  runThermal: (params = {}) =>
    call<{ jobId: string }>('runThermal', JSON.stringify(params) as never),
  runModal: (params = {}) =>
    call<{ jobId: string }>('runModal', JSON.stringify(params) as never),
  runCrossCheck: (params = {}) =>
    call<{ jobId: string }>('runCrossCheck', JSON.stringify(params) as never),
  runSimpKratosVerified: (params = {}) =>
    call<{ jobId: string }>('runSimpKratosVerified', JSON.stringify(params) as never),
  runSimpLoop: (params = {}) =>
    call<{ jobId: string }>('runSimpLoop', JSON.stringify(params) as never),
  // V2-NEW-END
  // FASE3-START (reversible): postproceso (FoS + comparativa). Para volver
  // atrás: borrar hasta FASE3-END + src/components/CompareTable.tsx +
  // SafetyCard.tsx y su uso en RightPanel.tsx.
  getSafetySummary: (params = {}) =>
    call<{ summary: { min_fos: number | null; mean_fos: number | null; count: number; below_threshold: number; threshold: number } }>(
      'getSafetySummary', JSON.stringify(params) as never),
  compareStudies: () =>
    call<{ rows: Record<string, unknown>[]; count: number }>('compareStudies'),
  // FASE3-END
  getNavProfiles: () =>
    call<{
      profiles: { name: string; display_name: string }[];
      current: string;
    }>('getNavProfiles'),
  setNavProfile: (name: string) => call('setNavProfile', name as never),
};
