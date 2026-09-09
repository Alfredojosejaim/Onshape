import React from 'react';
import { OptimizationMode, SimpConfig, DomainDimensions } from '../../types';
import {
  Play,
  Square,
  RotateCcw,
  Sparkles,
  Layers,
  Sliders,
  Zap,
  CheckCircle2,
  Gauge
} from 'lucide-react';

interface OptimizarPanelProps {
  mode: OptimizationMode;
  onModeChange: (mode: OptimizationMode) => void;
  config: SimpConfig;
  onConfigChange: (c: Partial<SimpConfig>) => void;
  dimensions: DomainDimensions;
  isOptimizing: boolean;
  currentIteration: number;
  maxIterations: number;
  onStartOptimization: () => void;
  onStopOptimization: () => void;
  onReset: () => void;
}

export const OptimizarPanel: React.FC<OptimizarPanelProps> = ({
  mode,
  onModeChange,
  config,
  onConfigChange,
  dimensions,
  isOptimizing,
  currentIteration,
  maxIterations,
  onStartOptimization,
  onStopOptimization,
  onReset
}) => {
  const targetMassReduction = ((1 - config.volumeFraction) * 100).toFixed(0);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 text-xs text-slate-300 shadow-lg">
      {/* Selector de las dos modalidades de optimización: Generativa o Estructural */}
      <div className="flex flex-col gap-2">
        <label className="text-slate-300 font-semibold flex items-center justify-between">
          <span>Modalidad de Optimización:</span>
          <span className="text-[10px] text-sky-400 font-mono font-bold">
            {mode === 'generativa' ? 'Algoritmo Biónico / Aditivo' : 'Algoritmo SIMP / Mecanizado'}
          </span>
        </label>

        <div className="grid grid-cols-2 gap-2.5">
          {/* Opción 1: Generativa */}
          <button
            onClick={() => onModeChange('generativa')}
            disabled={isOptimizing}
            className={`p-3 rounded-xl border text-left flex flex-col gap-1.5 transition-all cursor-pointer ${
              mode === 'generativa'
                ? 'bg-sky-500/15 border-sky-500/80 text-sky-100 shadow-md shadow-sky-500/10'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold flex items-center gap-1.5 text-xs">
                <Sparkles className={`w-3.5 h-3.5 ${mode === 'generativa' ? 'text-sky-400' : 'text-slate-500'}`} />
                Generativa
              </span>
              {mode === 'generativa' && (
                <span className="w-2 h-2 rounded-full bg-sky-400 shadow-[0_0_8px_#38bdf8]" />
              )}
            </div>
            <p className="text-[11px] text-slate-400 leading-snug">
              Estructuras orgánicas bio-inspiradas (hueso trabecular). Ramificación celular continua ideal para <strong className="text-slate-300">impresión 3D aditiva</strong>.
            </p>
          </button>

          {/* Opción 2: Estructural */}
          <button
            onClick={() => onModeChange('estructural')}
            disabled={isOptimizing}
            className={`p-3 rounded-xl border text-left flex flex-col gap-1.5 transition-all cursor-pointer ${
              mode === 'estructural'
                ? 'bg-indigo-500/15 border-indigo-500/80 text-indigo-100 shadow-md shadow-indigo-500/10'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold flex items-center gap-1.5 text-xs">
                <Layers className={`w-3.5 h-3.5 ${mode === 'estructural' ? 'text-indigo-400' : 'text-slate-500'}`} />
                Estructural
              </span>
              {mode === 'estructural' && (
                <span className="w-2 h-2 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8]" />
              )}
            </div>
            <p className="text-[11px] text-slate-400 leading-snug">
              Máxima rigidez estática directa (celosía Michell). Miembros axiales nítidos y nervaduras para <strong className="text-slate-300">mecanizado CNC y fundición</strong>.
            </p>
          </button>
        </div>
      </div>

      {/* Fracción de Volumen Objetivo */}
      <div className="flex flex-col gap-1.5 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
        <div className="flex items-center justify-between">
          <label className="text-slate-300 font-semibold flex items-center gap-1.5">
            <Gauge className="w-3.5 h-3.5 text-sky-400" />
            Volumen Objetivo Retenido (V / V₀):
          </label>
          <span className="text-sky-400 font-mono font-bold text-xs">
            {(config.volumeFraction * 100).toFixed(0)}%
          </span>
        </div>

        <input
          type="range"
          min="0.15"
          max="0.65"
          step="0.05"
          value={config.volumeFraction}
          onChange={(e) => onConfigChange({ volumeFraction: parseFloat(e.target.value) })}
          disabled={isOptimizing}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
        />

        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-0.5">
          <span>Aligeramiento de Peso: <strong className="text-emerald-400">-{targetMassReduction}%</strong></span>
          <span className="text-slate-500 font-mono">Retenido: {(config.volumeFraction * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Parámetros Numéricos SIMP */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80 flex flex-col gap-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-300">Iteraciones Máximas:</span>
            <span className="text-slate-200 font-mono font-bold">{config.maxIterations}</span>
          </div>
          <input
            type="range"
            min="15"
            max="60"
            step="5"
            value={config.maxIterations}
            onChange={(e) => onConfigChange({ maxIterations: parseInt(e.target.value, 10) })}
            disabled={isOptimizing}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
        </div>

        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80 flex flex-col gap-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-300">Radio de Filtro:</span>
            <span className="text-slate-200 font-mono font-bold">{config.filterRadius} el.</span>
          </div>
          <input
            type="range"
            min="1.2"
            max="4.0"
            step="0.2"
            value={config.filterRadius}
            onChange={(e) => onConfigChange({ filterRadius: parseFloat(e.target.value) })}
            disabled={isOptimizing}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
        </div>
      </div>

      {/* Barra de progreso si está optimizando */}
      {isOptimizing && (
        <div className="flex flex-col gap-1 bg-slate-950 p-2.5 rounded-lg border border-sky-500/30 animate-pulse">
          <div className="flex items-center justify-between text-[11px] text-sky-300 font-semibold">
            <span>Resolviendo FEA & Criterio de Optimalidad...</span>
            <span className="font-mono">{Math.round((currentIteration / maxIterations) * 100)}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-sky-500 to-indigo-500 h-full transition-all duration-150"
              style={{ width: `${(currentIteration / maxIterations) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Botones de Control Principal */}
      <div className="flex items-center gap-2 pt-1">
        {!isOptimizing ? (
          <button
            onClick={onStartOptimization}
            className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold py-2.5 px-4 rounded-xl shadow-lg shadow-sky-500/25 transition-all cursor-pointer text-xs"
          >
            <Play className="w-4 h-4 fill-white" />
            Iniciar Optimización {mode === 'generativa' ? 'Generativa' : 'Estructural'}
          </button>
        ) : (
          <button
            onClick={onStopOptimization}
            className="flex-1 flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-bold py-2.5 px-4 rounded-xl shadow-lg shadow-rose-600/25 transition-all cursor-pointer text-xs"
          >
            <Square className="w-4 h-4 fill-white" />
            Detener Cálculo
          </button>
        )}

        <button
          onClick={onReset}
          disabled={isOptimizing}
          className="flex items-center justify-center gap-1.5 p-2.5 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-all cursor-pointer disabled:opacity-40"
          title="Reiniciar a volumen homogéneo inicial"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
