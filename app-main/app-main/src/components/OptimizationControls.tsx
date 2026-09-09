import React from 'react';
import { Material, SimpConfig, DomainDimensions } from '../types';
import { STANDARD_MATERIALS } from '../lib/materials';
import {
  Play,
  Square,
  RotateCcw,
  Sliders,
  Scale,
  Sparkles,
  Zap,
  Gauge,
  Atom
} from 'lucide-react';

interface OptimizationControlsProps {
  material: Material;
  onMaterialChange: (m: Material) => void;
  config: SimpConfig;
  onConfigChange: (config: Partial<SimpConfig>) => void;
  dimensions: DomainDimensions;
  isOptimizing: boolean;
  currentIteration: number;
  maxIterations: number;
  onStartOptimization: () => void;
  onStopOptimization: () => void;
  onReset: () => void;
}

export const OptimizationControls: React.FC<OptimizationControlsProps> = ({
  material,
  onMaterialChange,
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
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
          <Sliders className="w-4 h-4 text-sky-400" />
          Parámetros SIMP & Material
        </h2>
        <span className="text-[10px] text-slate-400 font-mono">
          {dimensions.resolutionX}×{dimensions.resolutionY}×{dimensions.resolutionZ} elementos
        </span>
      </div>

      {/* Material Selector */}
      <div className="flex flex-col gap-1.5">
        <label className="text-slate-300 font-semibold flex items-center gap-1.5">
          <Atom className="w-3.5 h-3.5 text-indigo-400" />
          Material Estructural:
        </label>
        <select
          value={material.id}
          onChange={(e) => {
            const found = STANDARD_MATERIALS.find((m) => m.id === e.target.value);
            if (found) onMaterialChange(found);
          }}
          disabled={isOptimizing}
          className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-sky-500 cursor-pointer"
        >
          {STANDARD_MATERIALS.map((mat) => (
            <option key={mat.id} value={mat.id}>
              {mat.name}
            </option>
          ))}
        </select>
        {/* Material properties quick view */}
        <div className="grid grid-cols-3 gap-2 bg-slate-950/60 p-2 rounded-lg border border-slate-800/80 text-[11px] text-slate-400 font-mono">
          <div>
            <span className="text-slate-500 block text-[9px] uppercase">Mód. Young (E)</span>
            <span className="text-slate-200 font-bold">{material.youngModulus} GPa</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[9px] uppercase">Límite Elástico</span>
            <span className="text-emerald-400 font-bold">{material.yieldStrength} MPa</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[9px] uppercase">Densidad (ρ)</span>
            <span className="text-slate-200 font-bold">{material.density} kg/m³</span>
          </div>
        </div>
      </div>

      {/* Target Volume Fraction Slider (V*) */}
      <div className="flex flex-col gap-1.5 bg-slate-950/40 p-3 rounded-lg border border-slate-800/60">
        <div className="flex items-center justify-between">
          <label className="font-semibold text-slate-200 flex items-center gap-1.5">
            <Scale className="w-3.5 h-3.5 text-sky-400" />
            Fracción de Volumen Objetivo (V* / V₀):
          </label>
          <span className="font-mono font-bold text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
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
          className="w-full accent-sky-500 cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-slate-500">
          <span>15% (Ultra-ligero)</span>
          <span className="text-sky-300 font-medium">Reducción de peso esperada: ~{targetMassReduction}%</span>
          <span>65% (Alta rigidez)</span>
        </div>
      </div>

      {/* Numerical SIMP Solver settings */}
      <div className="grid grid-cols-2 gap-3">
        {/* Penalization Factor p */}
        <div className="flex flex-col gap-1">
          <label className="text-slate-400 text-[11px] font-medium flex items-center justify-between">
            <span>Factor de Penalización (p):</span>
            <span className="text-slate-200 font-mono font-bold">{config.penaltyExponent.toFixed(1)}</span>
          </label>
          <input
            type="range"
            min="2.0"
            max="4.0"
            step="0.2"
            value={config.penaltyExponent}
            onChange={(e) => onConfigChange({ penaltyExponent: parseFloat(e.target.value) })}
            disabled={isOptimizing}
            className="accent-slate-400 cursor-pointer"
          />
        </div>

        {/* Filter Radius */}
        <div className="flex flex-col gap-1">
          <label className="text-slate-400 text-[11px] font-medium flex items-center justify-between">
            <span>Radio Filtro (r_min):</span>
            <span className="text-slate-200 font-mono font-bold">{config.filterRadius.toFixed(1)} el</span>
          </label>
          <input
            type="range"
            min="1.2"
            max="3.5"
            step="0.1"
            value={config.filterRadius}
            onChange={(e) => onConfigChange({ filterRadius: parseFloat(e.target.value) })}
            disabled={isOptimizing}
            className="accent-slate-400 cursor-pointer"
          />
        </div>
      </div>

      {/* Maximum Iterations */}
      <div className="flex items-center justify-between bg-slate-950/40 px-3 py-2 rounded-lg border border-slate-800/60">
        <span className="text-slate-300 text-[11px] font-medium flex items-center gap-1.5">
          <Gauge className="w-3.5 h-3.5 text-amber-400" />
          Iteraciones Máximas:
        </span>
        <select
          value={config.maxIterations}
          onChange={(e) => onConfigChange({ maxIterations: parseInt(e.target.value) })}
          disabled={isOptimizing}
          className="bg-slate-900 border border-slate-700 text-slate-200 rounded px-2 py-1 text-xs focus:outline-none cursor-pointer"
        >
          <option value={20}>20 (Rápida)</option>
          <option value={35}>35 (Recomendada)</option>
          <option value={50}>50 (Alta precisión)</option>
        </select>
      </div>

      {/* Primary Execution Actions */}
      <div className="flex flex-col gap-2 pt-2">
        {!isOptimizing ? (
          <button
            onClick={onStartOptimization}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold text-xs shadow-lg shadow-sky-500/25 transition-all cursor-pointer active:scale-[0.98]"
          >
            <Play className="w-4 h-4 fill-current" />
            Ejecutar Optimización Topológica
          </button>
        ) : (
          <button
            onClick={onStopOptimization}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-lg shadow-amber-600/20 transition-all cursor-pointer"
          >
            <Square className="w-4 h-4 fill-current" />
            Detener Cálculo (Iteración {currentIteration}/{maxIterations})
          </button>
        )}

        <button
          onClick={onReset}
          disabled={isOptimizing}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Restablecer Dominio Inicial
        </button>
      </div>
    </div>
  );
};
