import React, { useEffect, useState } from 'react';
import { backend, hasBridge, toSurfaceMesh } from '../lib/backend';
import { useJobPoll } from '../lib/jobs';
import type { ScalarField, SurfaceMeshData } from '../types';

interface Props {
  loadMagnitude: number;
  volumeFraction: number;
  maxIterations: number;
  onMesh: (mesh: SurfaceMeshData, source: 'fea' | 'simp' | 'preview') => void;
  notify: (msg: string) => void;
}

/** Barra de backend real (pywebview + core vendorizado). Estetica dark acorde al Header. */
export function BackendBar({ loadMagnitude, volumeFraction, maxIterations, onMesh, notify }: Props) {
  const [connected, setConnected] = useState(false);
  const [snapshot, setSnapshot] = useState<string>('');
  const [stepPath, setStepPath] = useState('fixtures/cono.step');
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobKind, setJobKind] = useState<'fea' | 'simp' | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshSnapshot = async () => {
    if (!hasBridge()) { setConnected(false); return; }
    const r = await backend.getSnapshot();
    if (r.ok) {
      setConnected(true);
      const s = r.snapshot as { model_name: string | null; has_mesh: boolean; has_result: boolean; material?: string };
      setSnapshot(`${s.model_name ?? '—'} ${s.has_mesh ? '· mallado' : '· sin malla'}${s.has_result ? ' · con resultado' : ''}`);
    } else setConnected(false);
  };

  useEffect(() => { void refreshSnapshot(); }, []);

  const poll = useJobPoll(jobId, async () => {
    // Job terminado: pedir la malla de superficie correspondiente
    if (jobKind === 'fea') {
      const m = await backend.getSurfaceMesh({ field: 'vonmises' });
      if (m.ok) {
        onMesh(toSurfaceMesh(m as never, 'vonmises') as SurfaceMeshData, 'fea');
        notify('FEA real completado (Von Mises)');
      } else notify(`FEA ok pero sin malla: ${(m as { error?: string }).error ?? ''}`);
    } else if (jobKind === 'simp') {
      const m = await backend.getSurfaceMesh({ field: 'density' });
      if (m.ok) {
        onMesh(toSurfaceMesh(m as never, 'density') as SurfaceMeshData, 'simp');
        notify('SIMP real completado (densidad)');
      } else notify(`SIMP ok pero sin malla: ${(m as { error?: string }).error ?? ''}`);
    }
    setJobId(null); setJobKind(null); setBusy(false);
    void refreshSnapshot();
  });

  if (!hasBridge()) {
    return (
      <div className="px-3 py-2 text-[11px] text-slate-400 bg-slate-900/60 border-b border-slate-800">
        Modo preview local (heurístico) — abre con <span className="font-mono text-slate-300">INICIAR_APP_REAL.bat</span> para FEA/SIMP reales.
      </div>
    );
  }

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try { await fn(); } catch (e) { notify(`Error backend: ${String(e)}`); setBusy(false); }
  };

  return (
    <div className="px-3 py-2 flex flex-wrap items-center gap-2 text-[11px] bg-slate-900/80 border-b border-slate-800">
      <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg border ${connected ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-slate-700 text-slate-300'}`}>
        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400' : 'bg-slate-500'}`} />
        {connected ? `Backend real · ${snapshot}` : 'Backend…'}
      </span>
      <input
        value={stepPath}
        onChange={(e) => setStepPath(e.target.value)}
        className="flex-1 min-w-[180px] bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 font-mono text-slate-200"
        title="Ruta local del STEP (la lee Python, no el navegador)"
      />
      <button
        disabled={busy}
        className="px-2 py-1 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold disabled:opacity-50"
        onClick={() => void run(async () => {
          const im = await backend.importStep(stepPath);
          if (!im.ok) { notify(`importStep falló: ${(im as { error?: string }).error}`); setBusy(false); return; }
          const gm = await backend.generateMesh({ target_element_size: 5.0 });
          if (!gm.ok) { notify(`generateMesh falló`); setBusy(false); return; }
          await backend.setBoundaries({ bottom_axis: 2, load_dir: [0, 0, 1], magnitude: loadMagnitude });
          const pv = await backend.getMeshPreview();
          notify(pv.ok ? 'STEP importado + mallado real' : 'Importado (sin preview)');
          setBusy(false); void refreshSnapshot();
        })}
      >Importar + Mallar</button>
      <button
        disabled={busy}
        className="px-2 py-1 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-semibold disabled:opacity-50"
        onClick={() => void run(async () => {
          const r = await backend.runFea({ backend: 'local' });
          if (r.ok && (r as { jobId?: string }).jobId) { setJobId((r as { jobId: string }).jobId); setJobKind('fea'); }
          else { notify('runFea no devolvió jobId'); setBusy(false); }
        })}
      >FEA real</button>
      <button
        disabled={busy}
        className="px-2 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold disabled:opacity-50"
        onClick={() => void run(async () => {
          const r = await backend.runOptimization({ volume_fraction: volumeFraction, max_iterations: maxIterations });
          if (r.ok && (r as { jobId?: string }).jobId) { setJobId((r as { jobId: string }).jobId); setJobKind('simp'); }
          else { notify('runOptimization no devolvió jobId'); setBusy(false); }
        })}
      >SIMP real</button>
      {jobId && <span className="font-mono text-amber-300 animate-pulse">job {jobKind} {poll.state ?? '…'} {(poll.progress ?? 0) * 100 | 0}%</span>}
      {poll.error && <span className="text-red-300">{poll.error}</span>}
      <button
        className="px-2 py-1 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800"
        onClick={() => void refreshSnapshot()}
      >↻</button>
    </div>
  );
}
