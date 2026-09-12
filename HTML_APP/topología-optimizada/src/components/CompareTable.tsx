// FASE3-START (reversible, plan.md Fase 3.2): tabla comparativa A vs B (vs C…).
// Usa backend compareStudies (snapshots con solo claves reales, sin ceros
// inventados). Para volver atrás: borrar este archivo + su uso en RightPanel.
import React, { useState } from 'react';
import { backend } from '../lib/bridge';

type Row = Record<string, unknown>;

const META_KEYS = new Set(['study_id', 'name', 'study_type', 'status']);

function fmt(v: unknown): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) return '—';
    const a = Math.abs(v);
    if (a !== 0 && (a >= 1e6 || a < 1e-3)) return v.toExponential(2);
    return String(Math.round(v * 1000) / 1000);
  }
  const s = String(v);
  return s.length > 24 ? `${s.slice(0, 24)}…` : s;
}

export const CompareTable: React.FC = () => {
  const [rows, setRows] = useState<Row[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const refresh = async () => {
    if (!backend.hasBridge()) {
      setNotice('sin bridge: solo funciona con el backend real');
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      const r = await backend.compareStudies();
      if (r.ok) {
        setRows(((r as { rows?: Row[] }).rows ?? []) as Row[]);
        setLoaded(true);
        if (!((r as { rows?: Row[] }).rows ?? []).length) {
          setNotice('sin estudios con resultado todavía');
        }
      } else {
        setNotice(`fallo: ${JSON.stringify(r).slice(0, 160)}`);
      }
    } catch (e) {
      setNotice(String(e));
    } finally {
      setBusy(false);
    }
  };

  const metricKeys: string[] = [];
  for (const row of rows) {
    for (const k of Object.keys(row)) {
      if (!META_KEYS.has(k) && !metricKeys.includes(k)) metricKeys.push(k);
    }
  }

  return (
    <section
      className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-xs border border-border-subtle/40"
      aria-label="Comparación de estudios"
    >
      <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated/70 rounded text-[11px] font-semibold text-text-primary">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="material-symbols-outlined text-[15px] text-secondary">balance</span>
          <span className="truncate">Comparar estudios (A vs B)</span>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={busy}
          className="px-2 py-0.5 rounded bg-surface-container-high hover:bg-secondary hover:text-on-primary border border-border-subtle text-[10px] font-mono transition-colors disabled:opacity-50"
        >
          {busy ? '…' : 'Actualizar'}
        </button>
      </header>
      {!loaded ? (
        <p className="text-text-muted text-[11px] px-1">
          Pulsa Actualizar para ver masa, compliance, FoS y demás por estudio.
        </p>
      ) : rows.length === 0 ? (
        <p className="text-text-muted text-[11px] px-1">Sin estudios con resultado todavía.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[10px] font-mono">
            <thead>
              <tr className="text-text-muted text-left">
                <th className="px-1.5 py-1 font-medium">Métrica</th>
                {rows.map((row, i) => (
                  <th key={i} className="px-1.5 py-1 font-semibold text-text-primary">
                    {fmt(row.name ?? row.study_id ?? `Estudio ${i + 1}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metricKeys.map((k) => (
                <tr key={k} className="border-t border-border-subtle/30">
                  <td className="px-1.5 py-1 text-text-muted">{k}</td>
                  {rows.map((row, i) => (
                    <td key={i} className="px-1.5 py-1 text-text-primary">{fmt(row[k])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {notice && <div className="text-fea-stress-critical font-mono text-[10px] px-1 break-all">{notice}</div>}
    </section>
  );
};
