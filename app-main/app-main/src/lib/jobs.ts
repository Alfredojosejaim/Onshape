import { useEffect, useState } from 'react';
import { backend } from './backend';

export interface JobPollData {
  state: string | null;
  progress: number | null;
  result: unknown;
  error: string | null;
  loading: boolean;
}

/** Sondea un job del backend cada 2s. Limpia el intervalo al desmontar o cambiar de job. */
export function useJobPoll(jobId: string | null, onDone?: (result: unknown) => void): JobPollData {
  const [state, setState] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const tick = async () => {
      try {
        const r = (await backend.pollJob(jobId)) as {
          ok: boolean; state?: string; progress?: number; result?: unknown; error?: string | null;
        };
        if (cancelled) return;
        if (!r.ok) { setError('pollJob falló en el backend'); setLoading(false); return; }
        setState(r.state ?? null);
        setProgress(typeof r.progress === 'number' ? r.progress : null);
        if (r.state === 'done') {
          setResult(r.result ?? null);
          setLoading(false);
          if (onDone) onDone(r.result ?? null);
        } else if (r.state === 'error' || r.state === 'failed') {
          setError(typeof r.error === 'string' && r.error ? r.error : 'El job terminó con error');
          setLoading(false);
        }
      } catch (e) {
        if (!cancelled) { setError(e instanceof Error ? e.message : String(e)); setLoading(false); }
      }
    };
    void tick();
    const id = setInterval(() => { void tick(); }, 2000);
    return () => { cancelled = true; clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return { state, progress, result, error, loading };
}
