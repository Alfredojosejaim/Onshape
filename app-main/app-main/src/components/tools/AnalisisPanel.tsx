import React from 'react';
import {
  ScalarField,
  OptimizationMetrics,
  IterationData,
  Material
} from '../../types';
import {
  BarChart3,
  Download,
  Box,
  FileCode2,
  TrendingDown,
  Shield,
  Activity,
  Layers,
  Scissors
} from 'lucide-react';

interface AnalisisPanelProps {
  field: ScalarField;
  onFieldChange: (f: ScalarField) => void;
  densityThreshold: number;
  onThresholdChange: (val: number) => void;
  clipPlaneRatio: number;
  onClipPlaneChange: (val: number) => void;
  metrics: OptimizationMetrics | null;
  history: IterationData[];
  material: Material;
  onExportStep: () => void;
  onExportStl: () => void;
  onExportReport: () => void;
}

export const AnalisisPanel: React.FC<AnalisisPanelProps> = ({
  field,
  onFieldChange,
  densityThreshold,
  onThresholdChange,
  clipPlaneRatio,
  onClipPlaneChange,
  metrics,
  history,
  material,
  onExportStep,
  onExportStl,
  onExportReport
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 text-xs text-slate-300 shadow-lg">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Herramienta de Análisis FEA & CAD</h2>
            <p className="text-[11px] text-slate-400">Mapas de tensión, convergencia y síntesis de archivos CAD</p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 font-bold">
          {field === 'vonmises' ? 'Von Mises' : field === 'displacement' ? 'Desplazamiento' : 'Densidad'}
        </span>
      </div>

      {/* Selector de Campo Escalar */}
      <div className="flex flex-col gap-2">
        <label className="text-slate-300 font-semibold flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-violet-400" />
          Campo de Esfuerzos / Deformación:
        </label>
        <div className="grid grid-cols-3 gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => onFieldChange('density')}
            className={`py-1.5 px-2 rounded-lg font-medium transition-all text-center cursor-pointer ${
              field === 'density'
                ? 'bg-violet-600 text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            Densidad (ρ)
          </button>
          <button
            onClick={() => onFieldChange('vonmises')}
            className={`py-1.5 px-2 rounded-lg font-medium transition-all text-center cursor-pointer ${
              field === 'vonmises'
                ? 'bg-violet-600 text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            Von Mises (MPa)
          </button>
          <button
            onClick={() => onFieldChange('displacement')}
            className={`py-1.5 px-2 rounded-lg font-medium transition-all text-center cursor-pointer ${
              field === 'displacement'
                ? 'bg-violet-600 text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            Desplazamiento
          </button>
        </div>
      </div>

      {/* Controles de Inspección 3D (Isosuperficie y Plano de Corte) */}
      <div className="grid grid-cols-2 gap-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-300 flex items-center gap-1">
              <Layers className="w-3 h-3 text-violet-400" /> Umbral Isosuperficie:
            </span>
            <span className="text-violet-400 font-mono font-bold">{densityThreshold.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0.1"
            max="0.8"
            step="0.02"
            value={densityThreshold}
            onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-violet-500"
          />
        </div>

        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-300 flex items-center gap-1">
              <Scissors className="w-3 h-3 text-violet-400" /> Corte Longitudinal:
            </span>
            <span className="text-violet-400 font-mono font-bold">{(clipPlaneRatio * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.2"
            max="1.0"
            step="0.05"
            value={clipPlaneRatio}
            onChange={(e) => onClipPlaneChange(parseFloat(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-violet-500"
          />
        </div>
      </div>

      {/* Métricas de Rendimiento FEA */}
      {metrics ? (
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-slate-950 p-2 rounded-lg border border-slate-800/80 flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Reducción Masa</span>
            <span className="text-base font-bold text-emerald-400 font-mono">
              -{metrics.massReductionPercent.toFixed(1)}%
            </span>
            <span className="text-[10px] text-slate-400">
              {metrics.optimizedMassKg.toFixed(2)} / {metrics.initialMassKg.toFixed(2)} kg
            </span>
          </div>

          <div className="bg-slate-950 p-2 rounded-lg border border-slate-800/80 flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Tensión Máx.</span>
            <span className="text-base font-bold text-amber-400 font-mono">
              {metrics.maxVonMisesMpa.toFixed(1)} <span className="text-[10px]">MPa</span>
            </span>
            <span className="text-[10px] text-slate-400">
              Límite: {material.yieldStrength} MPa
            </span>
          </div>

          <div className="bg-slate-950 p-2 rounded-lg border border-slate-800/80 flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Factor Seguridad</span>
            <span className={`text-base font-bold font-mono ${metrics.safetyFactor >= 1.5 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {metrics.safetyFactor.toFixed(2)}×
            </span>
            <span className="text-[10px] text-slate-400">
              {metrics.safetyFactor >= 1.5 ? 'Estructural OK' : 'Ajustar carga'}
            </span>
          </div>
        </div>
      ) : (
        <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/60 text-slate-400 text-center">
          Inicia la optimización para calcular métricas FEA de tensión y masa.
        </div>
      )}

      {/* Exportación CAD Directa */}
      <div className="flex flex-col gap-2 pt-1 border-t border-slate-800">
        <label className="text-slate-300 font-semibold">Generación y Exportación de CAD:</label>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={onExportStep}
            className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md shadow-indigo-600/20 transition-all cursor-pointer"
            title="Exportar archivo STEP B-Rep para SolidWorks, Fusion 360, Inventor, Siemens NX"
          >
            <Download className="w-4 h-4" />
            Exportar STEP (CAD)
          </button>
          <button
            onClick={onExportStl}
            className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-bold text-xs transition-all cursor-pointer"
            title="Exportar archivo STL para impresión 3D / Fabricación aditiva"
          >
            <Box className="w-4 h-4" />
            Exportar STL (3D)
          </button>
        </div>

        <button
          onClick={onExportReport}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 text-[11px] transition-all cursor-pointer"
        >
          <FileCode2 className="w-3.5 h-3.5 text-violet-400" />
          Descargar Informe Técnico de Cálculo (JSON)
        </button>
      </div>
    </div>
  );
};
