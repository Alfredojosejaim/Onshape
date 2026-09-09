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
  getNavProfiles: () =>
    call<{
      profiles: { name: string; display_name: string }[];
      current: string;
    }>('getNavProfiles'),
  setNavProfile: (name: string) => call('setNavProfile', name as never),
};
