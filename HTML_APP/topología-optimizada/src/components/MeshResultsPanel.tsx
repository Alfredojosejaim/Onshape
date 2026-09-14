// MESH-RESULTS (reversible): panel derecho de la pestana Malla — SOLO
// resultados (diagnostico + ultima operacion). Las herramientas viven en
// la barra (Toolbar) y sus parametros en ToolParamsPanel. Sin reporte no
// muestra cifras (regla UI). Para volver atras: borrar este archivo + rama
// 'malla' en RightPanel.tsx.
import React from 'react';
import { MeshOpResult } from '../types';

interface MeshResultsPanelProps {
  isMeshModel: boolean;
  meshFormat: string | null;
  result: MeshOpResult;
}

function num(v: unknown): string {
  if (typeof v === 'number' && Number.isFinite(v)) {
    return v >= 100 ? Math.round(v).toString() : v.toFixed(3);
  }
  return '—';
}

export const MeshResultsPanel: React.FC<MeshResultsPanelProps> = ({
  isMeshModel, meshFormat, result,
}) => {
  const report = result.report;

  const row = (k: string, v: string) => (
    <div key={k} className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
      <span className="text-text-muted text-[11px]">{k}:</span>
      <span className="text-text-primary font-bold">{v}</span>
    </div>
  );

  return (
    <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-sm border border-border-subtle/50">
      <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated rounded border border-border-subtle/40">
        <div className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-secondary text-[16px]">grid_on</span>
          <span className="font-semibold text-[12px] text-text-primary">Resultados de Malla</span>
        </div>
        <span className="px-1.5 py-0.5 rounded bg-secondary/10 border border-secondary/30 text-secondary font-mono text-[10px] font-semibold tracking-wider">
          {isMeshModel ? (meshFormat ?? 'MALLA').toUpperCase() : 'SIN MALLA'}
        </span>
      </header>

      {!isMeshModel ? (
        <div className="text-text-muted font-mono text-[11px] px-1">
          Sin malla importada — importa un .stl / .obj / .ply / .3mf y usa Diagnosticar en la barra.
        </div>
      ) : !report ? (
        <div className="text-text-muted font-mono text-[11px] px-1">
          Sin diagnóstico — pulsa Diagnosticar en la barra de Malla.
        </div>
      ) : (
        <div className="flex flex-col gap-1 font-mono text-[11px]">
          {row('Triángulos', num(report.triangles))}
          {row('Vértices', num(report.vertices))}
          {row('Degenerados', num(report.degenerate_triangles))}
          {row('Non-manifold', num(report.non_manifold_edges))}
          {row('Bordes abiertos', num(report.boundary_loops))}
          {row('Volumen (mm³)', num(report.volume))}
          {row('Área (mm²)', num(report.area))}
          <div className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Estado:</span>
            <span className={`font-bold ${report.open ? 'text-fea-stress-critical' : 'text-fea-stress-optimal'}`}>
              {report.open ? 'ABIERTA / ROTA' : 'CERRADA'}
            </span>
          </div>
          {result.op && result.op !== 'diagnosticar' && (
            <div className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
              <span className="text-text-muted text-[11px]">Última operación:</span>
              <span className="text-secondary font-bold">{result.op}</span>
            </div>
          )}
        </div>
      )}
      {result.error && (
        <div className="text-fea-stress-critical font-mono text-[11px] px-1">{result.error}</div>
      )}
    </section>
  );
};
