// V2-NEW (reversible): panel de estudios avanzados del core real.
// Contenido: licencia, solver lineal (direct/cg), termico, modal,
// verificacion cruzada local<->Kratos y SIMP verificado.
// Para revertir: borrar esta carpeta src/components/v2/ + el bloque
// marcado V2-NEW en App.tsx y src/lib/bridge.ts.
import React, { useEffect, useState } from 'react';
import { backend } from '../../lib/bridge';
import { useJobPoll } from '../../lib/jobs';

type Log = { label: string; text: string };

function useRunner() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [log, setLog] = useState<Log[]>([]);
  const poll = useJobPoll(jobId, (result) => {
    setLog((p) => [...p, { label: 'resultado', text: JSON.stringify(result)?.slice(0, 2000) ?? '' }]);
    setJobId(null);
  });
  useEffect(() => {
    if (poll.error && jobId) {
      setLog((p) => [...p, { label: 'error', text: poll.error ?? '' }]);
      setJobId(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [poll.error]);
  return { jobId, setJobId, log, setLog, busy: poll.loading };
}

export const V2Panel: React.FC = () => {
  const [license, setLicense] = useState<string>('—');
  const [tCold, setTCold] = useState(300);
  const [tHot, setTHot] = useState(400);
  const [modes, setModes] = useState(5);
  const r = useRunner();

  useEffect(() => {
    if (!backend.hasBridge()) return;
    void backend.getLicense().then((x) => {
      if (x.ok) setLicense(`${(x as { state: string }).state}`);
    }).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const run = async (label: string, fn: () => Promise<{ ok: boolean; jobId?: string; error?: unknown }>) => {
    if (!backend.hasBridge()) {
      r.setLog((p) => [...p, { label, text: 'sin bridge: solo funciona con el backend real' }]);
      return;
    }
    try {
      const res = await fn();
      if (res.ok && res.jobId) {
        r.setJobId(res.jobId);
        r.setLog((p) => [...p, { label, text: `job ${res.jobId} en curso…` }]);
      } else {
        r.setLog((p) => [...p, { label, text: `fallo al lanzar: ${JSON.stringify(res).slice(0, 500)}` }]);
      }
    } catch (e) {
      r.setLog((p) => [...p, { label, text: String(e) }]);
    }
  };

  const box = 'rounded border border-border-subtle/40 bg-surface-panel/40 p-2 flex flex-col gap-2';
  const btn = 'px-2 py-1 rounded bg-secondary text-on-secondary text-body-sm disabled:opacity-50';
  const inp = 'w-20 px-1 rounded border border-border-subtle/40 bg-surface text-body-sm';

  return (
    <section className="flex flex-col gap-2 p-2 border-t border-border-subtle/40" aria-label="Estudios avanzados V2">
      <div className="flex items-center gap-2">
        <h2 className="text-body-sm font-semibold">Estudios avanzados <span className="opacity-60">(V2 · reversible)</span></h2>
        <span className="text-body-sm px-2 py-0.5 rounded bg-surface-container-lowest" title="Estado de licencia del core">
          Licencia: {license}
        </span>
      </div>

      <div className={box}>
        <strong className="text-body-sm">Solver FEA</strong>
        <div className="flex gap-2">
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('FEA directo', () => backend.runFeaIterative({ linear_solver: 'direct' }))}>Directo</button>
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('FEA CG', () => backend.runFeaIterative({ linear_solver: 'cg' }))}>Iterativo CG</button>
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('FEA Kratos', () => backend.runFea({ backend: 'kratos' }))}>Kratos</button>
        </div>
      </div>

      <div className={box}>
        <strong className="text-body-sm">Térmico estacionario (Tet4 real)</strong>
        <div className="flex items-center gap-2 text-body-sm">
          <label>T fría <input className={inp} type="number" value={tCold} onChange={(e) => setTCold(Number(e.target.value))} /></label>
          <label>T caliente <input className={inp} type="number" value={tHot} onChange={(e) => setTHot(Number(e.target.value))} /></label>
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('Térmico', () => backend.runThermal({ t_cold: tCold, t_hot: tHot }))}>Ejecutar</button>
        </div>
      </div>

      <div className={box}>
        <strong className="text-body-sm">Modal (frecuencias propias reales)</strong>
        <div className="flex items-center gap-2 text-body-sm">
          <label>Modos <input className={inp} type="number" value={modes} onChange={(e) => setModes(Number(e.target.value))} /></label>
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('Modal', () => backend.runModal({ mode_count: modes }))}>Ejecutar</button>
        </div>
      </div>

      <div className={box}>
        <strong className="text-body-sm">Kratos en el flujo (oráculo mutuo)</strong>
        <div className="flex gap-2">
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('Cross-check', () => backend.runCrossCheck({}))}>Verificación local↔Kratos</button>
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('SIMP verificado', () => backend.runSimpKratosVerified({}))}>SIMP + verificación Kratos</button>
        </div>
      </div>

      <div className={box}>
        <strong className="text-body-sm">SIMP vendorizado con motor inyectable (copia local, Kratos en el loop)</strong>
        <div className="flex gap-2">
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('SIMP-loop local', () => backend.runSimpLoop({ engine: 'local', max_iterations: 30 }))}>Loop local</button>
          <button className={btn} disabled={!!r.jobId} onClick={() => void run('SIMP-loop Kratos', () => backend.runSimpLoop({ engine: 'kratos', max_iterations: 30 }))}>Loop Kratos real</button>
        </div>
      </div>

      <div className="flex flex-col gap-1 max-h-40 overflow-auto text-body-sm">
        {r.log.slice(-8).map((l, i) => (
          <div key={i}><strong>{l.label}:</strong> <span className="break-all">{l.text}</span></div>
        ))}
      </div>
    </section>
  );
};
