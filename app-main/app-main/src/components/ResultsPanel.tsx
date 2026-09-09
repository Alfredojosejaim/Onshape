import React from 'react';
import { OptimizationMetrics, IterationData, Material } from '../types';
import {
  TrendingDown,
  Scale,
  Activity,
  Shield,
  Clock,
  Download,
  CheckCircle2,
  FileSpreadsheet,
  Box
} from 'lucide-react';

interface ResultsPanelProps {
  metrics: OptimizationMetrics | null;
  history: IterationData[];
  material: Material;
  onExportStep: () => void;
  onExportStl: () => void;
  onExportReport: () => void;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  metrics,
  history,
  material,
  onExportStep,
  onExportStl,
  onExportReport
}) => {
  if (!metrics || history.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col items-center justify-center text-center gap-2 text-xs text-slate-400 min-h-[160px] shadow-lg">
        <Activity className="w-6 h-6 text-slate-600 animate-pulse" />
        <span className="font-semibold text-slate-300">Aún no se ha ejecutado la optimización</span>
        <p className="text-[11px] text-slate-500 max-w-xs">
          Configura la fracción de volumen objetivo y pulsa "Ejecutar Optimización Topológica" para iniciar el algoritmo SIMP.
        </p>
      </div>
    );
  }

  // Generate SVG points for the convergence curve
  const svgWidth = 320;
  const svgHeight = 70;
  const padding = 10;

  const compliances = history.map((h) => h.compliance);
  const minC = Math.min(...compliances);
  const maxC = Math.max(...compliances, minC + 1);

  const points = history.map((h, i) => {
    const x = padding + (i / Math.max(1, history.length - 1)) * (svgWidth - 2 * padding);
    const y = svgHeight - padding - ((h.compliance - minC) / (maxC - minC)) * (svgHeight - 2 * padding);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-3 text-xs text-slate-300 shadow-lg">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400" />
          Resultados & Síntesis Generativa
        </h2>
        <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
          <CheckCircle2 className="w-3.5 h-3.5" />
          {metrics.converged ? 'Convergencia alcanzada' : `Iteración ${metrics.iterationsCompleted}`}
        </span>
      </div>

      {/* Structural Scorecard Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {/* Mass Saved */}
        <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] uppercase font-semibold">Reducción Masa</span>
            <Scale className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <span className="text-base font-extrabold text-sky-400">
            -{metrics.massReductionPercent.toFixed(1)}%
          </span>
          <span className="block text-[10px] text-slate-500">
            {metrics.initialMassKg.toFixed(2)}kg → {metrics.optimizedMassKg.toFixed(2)}kg
          </span>
        </div>

        {/* Max Von Mises Stress */}
        <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] uppercase font-semibold">Tensión Máx.</span>
            <TrendingDown className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <span className="text-base font-extrabold text-amber-400">
            {metrics.maxVonMisesMpa.toFixed(1)} MPa
          </span>
          <span className="block text-[10px] text-slate-500">
            Límite: {material.yieldStrength} MPa
          </span>
        </div>

        {/* Safety Factor */}
        <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] uppercase font-semibold">Factor Seguridad</span>
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <span className="text-base font-extrabold text-emerald-400">
            n = {metrics.safetyFactor.toFixed(2)}
          </span>
          <span className="block text-[10px] text-slate-500">
            {metrics.safetyFactor >= 1.5 ? 'Estructuralmente Óptimo' : 'Dentro de Rango'}
          </span>
        </div>

        {/* Elapsed Computation Time */}
        <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[10px] uppercase font-semibold">Tiempo Cálculo</span>
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <span className="text-base font-extrabold text-indigo-400">
            {metrics.computationTimeSec.toFixed(2)}s
          </span>
          <span className="block text-[10px] text-slate-500">
            {metrics.iterationsCompleted} iteraciones
          </span>
        </div>
      </div>

      {/* Real-time Convergence Curve (Compliance vs Iteration) */}
      <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80">
        <div className="flex items-center justify-between text-[11px] mb-1.5">
          <span className="font-semibold text-slate-300">Convergencia de Rigidez (Compliance C)</span>
          <span className="font-mono text-slate-400">
            C = {metrics.finalCompliance.toFixed(1)} J
          </span>
        </div>
        <div className="relative w-full h-18 bg-slate-900/60 rounded border border-slate-800/80 overflow-hidden">
          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            className="w-full h-full"
            preserveAspectRatio="none"
          >
            {/* Grid lines */}
            <line x1="0" y1="20" x2={svgWidth} y2="20" stroke="#1e293b" strokeDasharray="3,3" />
            <line x1="0" y1="45" x2={svgWidth} y2="45" stroke="#1e293b" strokeDasharray="3,3" />
            {/* Trend line */}
            <polyline
              fill="none"
              stroke="#38bdf8"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={points}
            />
          </svg>
        </div>
        <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
          <span>Iteración 1</span>
          <span>Iteración {metrics.iterationsCompleted}</span>
        </div>
      </div>

      {/* CAD Generation & Export Row */}
      <div className="pt-1 flex flex-wrap items-center justify-between gap-2">
        <div className="text-[11px] text-slate-400">
          Reconstrucción de sólido CAD generada mediante filtrado de densidad e isosuperficie.
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onExportStep}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors cursor-pointer shadow"
          >
            <Download className="w-3.5 h-3.5" />
            Descargar .STEP (CAD)
          </button>
          <button
            onClick={onExportStl}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-slate-700 transition-colors cursor-pointer"
          >
            <Box className="w-3.5 h-3.5" />
            Descargar .STL
          </button>
          <button
            onClick={onExportReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700 transition-colors cursor-pointer"
            title="Descargar reporte técnico con especificaciones del cálculo"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            Reporte
          </button>
        </div>
      </div>
    </div>
  );
};
