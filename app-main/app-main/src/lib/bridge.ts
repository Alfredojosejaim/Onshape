// Compat: la API real vive en ./backend (misma firma que api.py).
// Este modulo se mantiene para no romper imports antiguos.
export { backend, hasBridge, unwrapArray, toSurfaceMesh } from './backend';
export { backend as default } from './backend';

export function isNativePywebview(): boolean {
  return typeof window !== 'undefined' && Boolean(window.pywebview?.api);
}

export async function checkBackendConnection(): Promise<{
  connected: boolean;
  modelName?: string;
  material?: string;
}> {
  const { backend } = await import('./backend');
  if (!isNativePywebview()) return { connected: false };
  try {
    const res = (await backend.getSnapshot()) as {
      ok: boolean; snapshot?: { model_name?: string; material?: string };
    };
    if (res?.ok) {
      return { connected: true, modelName: res.snapshot?.model_name, material: res.snapshot?.material };
    }
  } catch (err) {
    console.warn('Native pywebview ping failed:', err);
  }
  return { connected: false };
}
