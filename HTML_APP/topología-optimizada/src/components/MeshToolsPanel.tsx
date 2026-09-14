// MALLA-TOOLS (reversible): pestaña Malla — superficie importada
// (STL/OBJ/PLY/3MF) + volumetrica Gmsh Tet4. Sin modelo MESH, la seccion
// de superficie muestra estado vacio (regla UI). Para volver atras: borrar
// este archivo + rama 'malla' en RightPanel.tsx + tab en SecondaryNav.
import React, { useState } from 'react';
import { backend } from '../lib/bridge';

interface MeshToolsPanelProps {
  isMeshModel: boolean;
  meshFormat: string | null;
  onChanged: () => void;
  // Malla volumetrica (Gmsh Tet4, requiere solido B-Rep / STEP).
  volSize: number;
  onVolSize: (v: number) => void;
  onVolRemesh: () => void;
  isRemeshing: boolean;
  estTets: string;
  estNodes: string;
}

type Report = Record<string, unknown>;

function num(r: Report, k: string): string {
  const v = r[k];
  if (typeof v === 'number' && Number.isFinite(v)) {
    return v >= 100 ? Math.round(v).toString() : v.toFixed(3);
  }
  return '—';
}

const icon = (name: string) => (
  <span className="material-symbols-outlined text-[16px]"> {name} </span>
);

export const MeshToolsPanel: React.FC<MeshToolsPanelProps> = ({
  isMeshModel, meshFormat, onChanged,
  volSize, onVolSize, onVolRemesh, isRemeshing, estTets, estNodes,
}) => {
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [smoothIters, setSmoothIters] = useState(3);
  const [smoothAlpha, setSmoothAlpha] = useState(0.5);
  const [decimateFrac, setDecimateFrac] = useState(0.5);
  const [remeshLen, setRemeshLen] = useState(1.0);

  const run = async (label: string, fn: () => Promise<unknown>, refresh: boolean) => {
    setBusy(label);
    setError(null);
    try {
      const r = (await fn()) as { ok: boolean; error?: unknown; report?: Report };
      if (!r.ok) {
        setError(String(r.error ?? 'falló'));
        return;
      }
      if (r.report) setReport(r.report);
      if (refresh) {
        const q = (await backend.meshQualityReport({})) as { ok: boolean; report?: Report };
        if (q.ok && q.report) setReport(q.report);
        onChanged();
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const row = (k: string, v: string) => (
    <div key={k} className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
      <span className="text-text-muted text-[11px]">{k}:</span>
      <span className="text-text-primary font-bold">{v}</span>
    </div>
  );

  const btn =
    'w-full flex items-center justify-center gap-2 py-2 rounded-lg font-semibold text-[12px] transition-all disabled:opacity-50 active:scale-95';
  const btnGhost =
    `${btn} bg-surface-elevated hover:bg-surface-container-high border border-border-subtle text-text-primary`;
  const btnPrimary =
    `${btn} bg-primary-container hover:bg-secondary text-on-primary shadow-md`;

  return (
    <>
      {/* Superficie importada: solo con modelo MESH */}
      {isMeshModel ? (
        <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-sm border border-border-subtle/50">
          <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated rounded border border-border-subtle/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-secondary text-[16px]">grid_on</span>
              <span className="font-semibold text-[12px] text-text-primary">Malla de Superficie</span>
            </div>
            <span className="px-1.5 py-0.5 rounded bg-secondary/10 border border-secondary/30 text-secondary font-mono text-[10px] font-semibold tracking-wider">
              {(meshFormat ?? 'MALLA').toUpperCase()}
            </span>
          </header>

          <div className="flex flex-col gap-1 font-mono text-[11px]">
            {report ? (
              <>
                {row('Triángulos', num(report, 'triangles'))}
                {row('Vértices', num(report, 'vertices'))}
                {row('Degenerados', num(report, 'degenerate_triangles'))}
                {row('Non-manifold', num(report, 'non_manifold_edges'))}
                {row('Bordes abiertos', num(report, 'boundary_loops'))}
                {row('Volumen (mm³)', num(report, 'volume'))}
                {row('Área (mm²)', num(report, 'area'))}
                <div className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
                  <span className="text-text-muted text-[11px]">Estado:</span>
                  <span className={`font-bold ${report.open ? 'text-fea-stress-critical' : 'text-fea-stress-optimal'}`}>
                    {report.open ? 'ABIERTA / ROTA' : 'CERRADA'}
                  </span>
                </div>
              </>
            ) : (
              <div className="text-text-muted text-[11px] px-1">Sin diagnóstico — pulsa Diagnosticar.</div>
            )}
            {error && <div className="text-fea-stress-critical text-[11px] px-1">{error}</div>}
          </div>

          <button type="button" disabled={busy !== null}
            onClick={() => void run('diag', () => backend.meshQualityReport({}), false)}
            className={btnGhost}>
            {icon('troubleshoot')}
            <span>{busy === 'diag' ? 'Diagnosticando…' : 'Diagnosticar malla'}</span>
          </button>

          <button type="button" disabled={busy !== null}
            onClick={() => void run('rep', () => backend.repairMesh({}), true)}
            className={btnPrimary}>
            {icon('healing')}
            <span>{busy === 'rep' ? 'Reparando…' : 'Reparar (soldar + limpiar)'}</span>
          </button>

          <div className="flex flex-col gap-1 bg-surface-elevated/40 p-2 rounded border border-border-subtle/30 font-mono text-[10px]">
            <div className="flex justify-between items-center">
              <span className="text-text-muted flex items-center gap-1">
                {icon('waves')}
                <span>Suavizar (laplaciano):</span>
              </span>
              <span className="text-secondary font-bold">it {smoothIters} · α {smoothAlpha}</span>
            </div>
            <div className="flex gap-1.5">
              <input type="number" min={1} max={100} step={1} value={smoothIters}
                onChange={(e) => setSmoothIters(Math.max(1, parseInt(e.target.value || '1', 10)))}
                className="w-1/2 bg-surface-container-lowest rounded px-2 py-1 text-text-primary" />
              <input type="number" min={0.05} max={1} step={0.05} value={smoothAlpha}
                onChange={(e) => setSmoothAlpha(Math.min(1, Math.max(0.05, parseFloat(e.target.value || '0.5'))))}
                className="w-1/2 bg-surface-container-lowest rounded px-2 py-1 text-text-primary" />
            </div>
            <button type="button" disabled={busy !== null}
              onClick={() => void run('smo', () => backend.smoothMesh({ iterations: smoothIters, alpha: smoothAlpha }), true)}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-surface-elevated hover:bg-surface-container-high border border-border-subtle text-text-primary font-semibold text-[11px] disabled:opacity-50">
              {icon('waves')}
              <span>{busy === 'smo' ? 'Suavizando…' : 'Aplicar suavizado'}</span>
            </button>
          </div>

          <div className="flex flex-col gap-1 bg-surface-elevated/40 p-2 rounded border border-border-subtle/30 font-mono text-[10px]">
            <div className="flex justify-between items-center">
              <span className="text-text-muted flex items-center gap-1">
                {icon('compress')}
                <span>Reducir triángulos:</span>
              </span>
              <span className="text-secondary font-bold">{Math.round(decimateFrac * 100)}%</span>
            </div>
            <input type="range" min={0.05} max={1} step={0.05} value={decimateFrac}
              onChange={(e) => setDecimateFrac(parseFloat(e.target.value))}
              className="w-full h-1 bg-surface-container-lowest rounded-full appearance-none cursor-pointer accent-secondary" />
            <button type="button" disabled={busy !== null}
              onClick={() => void run('dec', () => backend.decimateMesh({ target_fraction: decimateFrac }), true)}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-surface-elevated hover:bg-surface-container-high border border-border-subtle text-text-primary font-semibold text-[11px] disabled:opacity-50">
              {icon('compress')}
              <span>{busy === 'dec' ? 'Reduciendo…' : 'Aplicar reducción'}</span>
            </button>
          </div>

          <div className="flex flex-col gap-1 bg-surface-elevated/40 p-2 rounded border border-border-subtle/30 font-mono text-[10px]">
            <div className="flex justify-between items-center">
              <span className="text-text-muted flex items-center gap-1">
                {icon('autorenew')}
                <span>Remallar (longitud objetivo mm):</span>
              </span>
            </div>
            <input type="number" min={0.01} step={0.1} value={remeshLen}
              onChange={(e) => setRemeshLen(Math.max(0.01, parseFloat(e.target.value || '1')))}
              className="w-full bg-surface-container-lowest rounded px-2 py-1 text-text-primary" />
            <button type="button" disabled={busy !== null}
              onClick={() => void run('rem', () => backend.remeshMesh({ target_length: remeshLen, iterations: 3 }), true)}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-surface-elevated hover:bg-surface-container-high border border-border-subtle text-text-primary font-semibold text-[11px] disabled:opacity-50">
              {icon('autorenew')}
              <span>{busy === 'rem' ? 'Remallando…' : 'Aplicar remallado'}</span>
            </button>
          </div>
        </section>
      ) : (
        <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-xs border border-border-subtle/50">
          <header className="flex items-center gap-1.5 px-space-xs py-1 bg-surface-elevated rounded border border-border-subtle/40">
            <span className="material-symbols-outlined text-secondary text-[16px]">grid_on</span>
            <span className="font-semibold text-[12px] text-text-primary">Malla de Superficie</span>
          </header>
          <div className="text-text-muted font-mono text-[11px] px-1">
            Sin malla importada — importa un .stl / .obj / .ply / .3mf para diagnosticar y reparar.
          </div>
        </section>
      )}

      {/* Volumetrica Gmsh Tet4 (misma estetica que ToolParamsPanel) */}
      <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-sm border border-border-subtle/50">
        <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated rounded border border-border-subtle/40">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-secondary text-[16px]">box</span>
            <span className="font-semibold text-[12px] text-text-primary">Malla Volumétrica</span>
          </div>
          <span className="px-1.5 py-0.5 rounded bg-secondary/10 border border-secondary/30 text-secondary font-mono text-[10px] font-semibold tracking-wider">
            GMSH TET4
          </span>
        </header>
        {isMeshModel ? (
          <div className="text-text-muted font-mono text-[11px] px-1">
            Requiere sólido B-Rep (STEP) — la malla importada no tiene sólido para mallar.
          </div>
        ) : (
          <div className="flex flex-col gap-2 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-text-muted text-[10px] font-mono">Tamaño Elemento (h):</span>
              <span className="font-mono text-text-primary font-bold text-[11px]">{volSize.toFixed(1)} mm</span>
            </div>
            <input
              type="range"
              min="0.8"
              max="3.5"
              step="0.1"
              value={volSize}
              onChange={(e) => onVolSize(parseFloat(e.target.value))}
              className="w-full h-1 bg-surface-elevated rounded-lg appearance-none cursor-pointer accent-secondary"
            />
            <div className="grid grid-cols-2 gap-1.5 font-mono text-[10px]">
              <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30">
                <span className="text-text-muted block text-[9px]">Tetraedros:</span>
                <span className="text-secondary font-semibold">{estTets}</span>
              </div>
              <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30">
                <span className="text-text-muted block text-[9px]">Nodos FEA:</span>
                <span className="text-text-primary font-semibold">{estNodes}</span>
              </div>
            </div>
            <button
              type="button"
              onClick={onVolRemesh}
              disabled={isRemeshing}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-surface-elevated hover:bg-surface-container-high border border-border-subtle hover:border-secondary/40 text-text-primary hover:text-secondary text-[11px] font-medium transition-colors active:scale-95 disabled:opacity-50"
            >
              <span className={`material-symbols-outlined text-[15px] ${isRemeshing ? 'animate-spin text-secondary' : ''}`}>
                refresh
              </span>
              <span>{isRemeshing ? 'Generando Malla...' : 'Remallar Dominio CAD'}</span>
            </button>
          </div>
        )}
      </section>
    </>
  );
};
