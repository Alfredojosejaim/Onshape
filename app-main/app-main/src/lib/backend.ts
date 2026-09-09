// Puente HTML -> backend Python (pywebview) con fallback mock.
// Copiado del patron Web_App/html/src/lib/bridge.ts: misma firma que api.py.
// Si no hay pywebview (npm run dev en navegador), responde mocks y la app
// sigue funcionando con el motor local simpEngine (preview heuristico).
declare global {
  interface Window { pywebview?: { api: Record<string, (...a: never[]) => Promise<unknown>> } }
}

type Ok<T = unknown> = { ok: boolean } & T;

export function hasBridge(): boolean {
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
  console.warn(`[backend] sin pywebview — mock para ${method}`);
  const base: Record<string, unknown> = {
    getSnapshot: { snapshot: { model_name: null, has_mesh: false, has_result: false } },
    getMaterials: { materials: [], names: ['steel', 'aluminum', 'titanium'] },
    pollJob: { state: 'done', progress: 1, result: null, error: null },
    getNavProfiles: { profiles: [], current: 'onshape' },
    getSurfaceMesh: { ok: false, error: 'sin backend (usa motor local)' },
    getMeshPreview: { ok: false, error: 'sin backend (usa motor local)' },
  };
  return { ok: true, ...((base[method] as Record<string, unknown> | undefined) ?? {}) } as unknown as Ok<T>;
}

export interface NdArrayMsg { __ndarray__?: boolean; data?: number[]; shape?: number[]; truncated?: boolean }

export function unwrapArray(m: unknown): number[] {
  if (Array.isArray(m)) return m as number[];
  const o = m as NdArrayMsg | null;
  if (o && o.__ndarray__ && Array.isArray(o.data)) return o.data;
  return [];
}

/** Convierte la respuesta getSurfaceMesh del backend a SurfaceMeshData del Viewport. */
export function toSurfaceMesh(
  r: { positions: unknown; indices: unknown; values: unknown; min: number | null; max: number | null; field: string },
  field: 'density' | 'vonmises' | 'displacement' | 'none' = 'density',
) {
  const pos = unwrapArray(r.positions);
  const idx = unwrapArray(r.indices);
  const val = r.values == null ? new Float32Array(0) : Float32Array.from(unwrapArray(r.values));
  return {
    positions: Float32Array.from(pos),
    indices: Uint32Array.from(idx),
    values: val,
    minVal: r.min ?? 0,
    maxVal: r.max ?? 1,
    field,
  };
}

export const backend = {
  hasBridge,
  getSnapshot: () => call<{ snapshot: { model_name: string | null; has_mesh: boolean; has_result: boolean; material?: string } }>('getSnapshot'),
  getMaterials: () => call<{ materials: unknown[]; names: string[] }>('getMaterials'),
  setMaterial: (name: string) => call('setMaterial', name as never),
  validateProblem: (problemJson: string) => call('validateProblem', problemJson as never),
  importStep: (path: string) => call('importStep', path as never),
  generateMesh: (params: object = {}) =>
    call('generateMesh', JSON.stringify(params) as never),
  setBoundaries: (params: object) =>
    call('setBoundaries', JSON.stringify(params) as never),
  runFea: (params: object = {}) => call<{ jobId: string }>('runFea', JSON.stringify(params) as never),
  runOptimization: (params: object = {}) =>
    call<{ jobId: string }>('runOptimization', JSON.stringify(params) as never),
  pollJob: (jobId: string) => call<{ state: string; progress: number; result: unknown; error: unknown }>('pollJob', jobId as never),
  getMeshPreview: () => call<{ mesh: unknown }>('getMeshPreview'),
  getSurfaceMesh: (params: object = {}) =>
    call<{
      positions: unknown; indices: unknown; values: unknown;
      min: number | null; max: number | null; field: string;
      num_vertices: number; num_triangles: number;
    }>('getSurfaceMesh', JSON.stringify(params) as never),
  exportStep: (path: string) => call('exportStep', path as never),
};
