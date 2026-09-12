// FASE3-START (reversible, plan.md Fase 3.1): tarjeta de factor de seguridad.
// Muestra FoS mín/medio + zonas bajo umbral del resultado FEA activo
// (backend getSafetySummary, mismo pipeline de color que tensión).
// Para volver atrás: borrar este archivo + su uso en RightPanel.tsx.
import React, { useState } from 'react';
import { backend } from '../lib/bridge';

interface Summary {
  min_fos: number | null;
  mean_fos: number | null;
  count: number;
  below_threshold: number;
  threshold: number;
}

export const SafetyCard: React.FC = () => {
  const [threshold, setThreshold] = useState('1.5');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    if (!backend.hasBridge()) {
      setNotice('sin bridge: solo funciona con el backend real');
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      const r = await backend.getSafetySummary({ threshold: parseFloat(threshold) || 1.5 });
      if (r.ok && (r as { summary?: Summary }).summary) {
        setSummary((r as { summary: Summary }).summary);
      } else {
        setNotice(`sin dato: ${JSON.stringify(r).slice(0, 160)}`);
      }
    } catch (e) {
      setNotice(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30 flex flex-col gap-1.5 font-mono text-[10px]">
      <div className="flex items-center justify-between">
        <span className="text-text-muted">Seguridad FoS (σ_y/σ_vM):</span>
        <span className="text-fea-stress-optimal font-bold text-[12px]">
          {summary?.min_fos !== undefined && summary?.min_fos !== null
            ? `mín ${summary.min_fos.toFixed(2)}`
            : '—'}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-text-muted">Umbral:</span>
        <input
          type="number"
          aria-label="Umbral de FoS"
          min="0.5"
          step="0.1"
          value={threshold}
          onChange={(e) => setThreshold(e.target.value)}
          className="w-16 bg-surface-container-lowest border border-border-subtle rounded px-1.5 py-0.5 text-text-primary outline-none focus:border-secondary/60"
        />
        <span className="text-text-secondary">
          {summary ? `${summary.below_threshold}/${summary.count} bajo umbral` : 'sin cálculo'}
        </span>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={busy}
          className="ml-auto px-2 py-0.5 rounded bg-surface-container-high hover:bg-secondary hover:text-on-primary border border-border-subtle text-text-primary transition-colors disabled:opacity-50"
        >
          {busy ? '…' : 'Calcular'}
        </button>
      </div>
      {summary?.mean_fos !== undefined && summary?.mean_fos !== null && (
        <div className="text-text-muted">FoS medio: {summary.mean_fos.toFixed(2)}</div>
      )}
      {notice && <div className="text-fea-stress-critical break-all">{notice}</div>}
    </div>
  );
};
