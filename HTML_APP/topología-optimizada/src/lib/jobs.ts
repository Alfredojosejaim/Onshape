import { useEffect, useState } from 'react';
import { backend } from './bridge';

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
    // REOPT-FIX (reversible): antes el intervalo seguía sondeando cada 2s
    // tras done/error y re-disparaba onDone sin fin (efectos repetidos y
    // puerto ocupado). Ahora se detiene en estado terminal. Para volver
    // atrás: quitar los clearInterval.
    let id: ReturnType<typeof setInterval> | null = null;
    const stop = () => {
      if (id !== null) {
        clearInterval(id);
        id = null;
      }
    };
    setLoading(true);
    setError(null);
    const tick = async () => {
      try {
        const r = (await backend.pollJob(jobId)) as {
          ok: boolean;
          mock?: unknown;
          state?: string;
          progress?: number;
          result?: unknown;
          error?: string | null;
        };
        if (cancelled) return;
        if (!r.ok) {
          // POLL-ERR-STR (reversible): el backend SÍ trae el detalle en
          // `error` ("job desconocido: ...", "método no expuesto: ...",
          // excepción del puente). Antes se descartaba y la UI mostraba
          // solo el genérico, perdiendo la causa real. Para volver atrás:
          // mensaje fijo sin sufijo.
          const detail = typeof r.error === 'string' && r.error ? `: ${r.error}` : '';
          setError(`pollJob falló en el backend${detail}`);
          setLoading(false);
          stop();
          return;
        }
        // P-A (reversible): el mock del bridge responde done/result:null con
        // ok:true. Sin este chequeo, un jobId seteado sin bridge se daría por
        // terminado con éxito y dispararía onDone(null). Para volver atrás:
        // quitar este bloque + la bandera mock:true de bridge.ts.
        if (r.mock) {
          setError('sin bridge: el sondeo mock no es un resultado real');
          setLoading(false);
          stop();
          return;
        }
        setState(r.state ?? null);
        setProgress(typeof r.progress === 'number' ? r.progress : null);
        if (r.state === 'done') {
          setResult(r.result ?? null);
          setLoading(false);
          stop();
          if (onDone) onDone(r.result ?? null);
        } else if (r.state === 'error' || r.state === 'failed') {
          setError(typeof r.error === 'string' && r.error ? r.error : 'El job terminó con error');
          setLoading(false);
          stop();
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setLoading(false);
          stop();
        }
      }
    };
    void tick();
    // POLL-1S (reversible): 2s hacía que una corrida corta terminara antes de
    // mostrar la primera iteración ("no itera"). 1s muestra el avance. Para
    // volver atrás: 2000.
    id = setInterval(() => {
      void tick();
    }, 1000);
    return () => {
      cancelled = true;
      stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return { state, progress, result, error, loading };
}
