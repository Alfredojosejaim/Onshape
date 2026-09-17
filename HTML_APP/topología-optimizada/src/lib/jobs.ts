import { useEffect, useState } from 'react';
import { backend } from './bridge';

export interface JobPollData {
  state: string | null;
  progress: number | null;
  result: unknown;
  error: string | null;
  loading: boolean;
  /** true si el backend lleva demasiado sin contestar al sondeo. No es un
   * fallo del job: el proceso sigue vivo y puede estar dentro de una llamada
   * nativa larga (OCP retiene el GIL durante la reconstrucción). */
  stalled: boolean;
  /** Segundos que el backend lleva sin reportar avance (0 = al día). */
  stalledSec: number;
}

/** Sondea un job del backend cada 2s. Limpia el intervalo al desmontar o cambiar de job. */
export function useJobPoll(jobId: string | null, onDone?: (result: unknown) => void): JobPollData {
  const [state, setState] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [stalled, setStalled] = useState<boolean>(false);
  const [stalledSec, setStalledSec] = useState<number>(0);

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
    setStalled(false);
    setStalledSec(0);
    // POLL-STALL (reversible): el servidor es monohilo y el job corre en un
    // hilo del MISMO proceso. Durante la reconstruccion B-Rep/bspline, OCP
    // (pybind11) retiene el GIL en llamadas nativas largas: el hilo HTTP NO
    // puede atender pollJob aunque el proceso siga vivo y el calculo avance
    // (medido: un unico Sewing.Perform() congela el hilo principal ~1.1 s).
    // Antes el sondeo contaba FALLOS (150) sin reiniciar nunca el contador
    // tras un poll correcto, con ticks solapados (setInterval + async): unos
    // segundos de backend ocupado sumaban cientos de "fallos" y la UI decia
    // "La optimizacion termino con error" con el job sano (que de hecho
    // termino bien minutos despues). Ahora:
    //   - los ticks NO se solapan (1 peticion en vuelo como maximo),
    //   - el contador se reinicia en cada respuesta correcta,
    //   - el presupuesto es TIEMPO sin respuesta (no numero de fallos),
    //   - mientras el proceso viva se sigue sondeando y solo se avisa
    //     ("stalled"), sin declarar error. Para volver atras: restaurar el
    //     contador de 150 fallos.
    const STALL_WARN_MS = 45_000;       // aviso "backend ocupado"
    const STALL_FAIL_MS = 60 * 60_000;  // silencio total -> error terminal
    let lastOkAt = Date.now();
    // JOB-STATUS (reversible): edad (s) del último avance publicado por el
    // backend. El sondeo normal lo responde el host leyendo ese snapshot, así
    // que un poll "correcto" NO prueba que el cálculo avance: hay que mirar
    // esta edad. 0 = el backend publicó avance hace nada.
    let staleSec = 0;
    let inFlight = false;
    const TRANSPORT_RETRY = /(backend ocupado|backend no responde|timed out|timeout|URLError|10061|refused|abort|fetch failed|networkerror|failed to fetch)/i;
    const SERVER_DEAD = /el proceso backend terminó/i;
    /** Comprueba el silencio acumulado. false = hay que detener el sondeo. */
    const checkStall = (): boolean => {
      const silenceMs = Math.max(Date.now() - lastOkAt, staleSec * 1000);
      if (silenceMs > STALL_FAIL_MS) {
        setError(`sin respuesta del backend durante ${Math.round(silenceMs / 60000)} min `
          + '(no se pudo confirmar el resultado; el proceso puede seguir ocupado en una '
          + 'llamada nativa larga —revisa backend/server_stdout.log— o haberse colgado).');
        setLoading(false);
        stop();
        return false;
      }
      if (silenceMs > STALL_WARN_MS) setStalled(true);
      return true;
    };
    const tick = async () => {
      // POLL-SERIAL: si la peticion anterior sigue en vuelo (backend ocupado),
      // no se lanza otra: evita llenar la cola TCP del servidor monohilo y que
      // los fallos se cuenten en ráfaga.
      if (inFlight) {
        if (!cancelled) checkStall();
        return;
      }
      inFlight = true;
      try {
        let r: {
          ok: boolean;
          mock?: unknown;
          state?: string;
          progress?: number;
          result?: unknown;
          error?: string | null;
          stale?: boolean;
          stale_sec?: number;
        };
        try {
          r = (await backend.pollJob(jobId)) as {
            ok: boolean;
            mock?: unknown;
            state?: string;
            progress?: number;
            result?: unknown;
            error?: string | null;
            stale?: boolean;
            stale_sec?: number;
          };
        } catch (e) {
          if (!cancelled && checkStall()) {
            // Sigue sondeando; no se pisa un error previo real.
          } else if (!cancelled) {
            setError(e instanceof Error ? e.message : String(e));
            setLoading(false);
            stop();
          }
          return;
        }
        if (cancelled) return;
        if (!r.ok) {
          const detail = typeof r.error === 'string' && r.error ? r.error : '';
          if (SERVER_DEAD.test(detail)) {
            setError(`pollJob falló en el backend: ${detail}`);
            setLoading(false);
            stop();
            return;
          }
          if (TRANSPORT_RETRY.test(detail)) {
            checkStall();
            return;
          }
          // POLL-ERR-STR (reversible): el backend SÍ trae el detalle en
          // `error` ("job desconocido: ...", "método no expuesto: ...",
          // excepción del puente). Antes se descartaba y la UI mostraba
          // solo el genérico, perdiendo la causa real. Para volver atrás:
          // mensaje fijo sin sufijo.
          const suffix = detail ? `: ${detail}` : '';
          setError(`pollJob falló en el backend${suffix}`);
          setLoading(false);
          stop();
          return;
        }
        // Respuesta válida: el transporte está sano (lastOkAt).
        lastOkAt = Date.now();
        // JOB-STATUS: el avance real lo dice la edad publicada por el backend
        // (el host contesta el poll leyendo su snapshot), no el éxito del poll.
        staleSec = typeof r.stale_sec === 'number' ? r.stale_sec : 0;
        setStalled(Boolean(r.stale) || staleSec * 1000 > STALL_WARN_MS);
        setStalledSec(r.stale ? Math.round(staleSec) : 0);
        // Job vivo pero el backend lleva demasiado sin publicar avance: aviso
        // (stalled) y, pasado el presupuesto, error terminal.
        if (r.state === 'running' && !checkStall()) return;
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
      } finally {
        inFlight = false;
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

  return { state, progress, result, error, loading, stalled, stalledSec };
}
