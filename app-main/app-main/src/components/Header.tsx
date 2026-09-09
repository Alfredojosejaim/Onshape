import React from 'react';
import { ActiveTool, OptimizationMode } from '../types';
import {
  ArrowDownCircle,
  Atom,
  Ban,
  ShieldCheck,
  Play,
  BarChart3,
  Sparkles,
  Layers,
  Cpu,
  Square
} from 'lucide-react';

interface HeaderProps {
  activeTool: ActiveTool;
  onSelectTool: (tool: ActiveTool) => void;
  mode: OptimizationMode;
  onModeChange: (mode: OptimizationMode) => void;
  isOptimizing: boolean;
  loadMagnitude: number;
  protectedCount: number;
  obstacleCount: number;
  currentMaterialName?: string;
  onStartOptimization: () => void;
  onStopOptimization: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTool,
  onSelectTool,
  mode,
  onModeChange,
  isOptimizing,
  loadMagnitude,
  protectedCount,
  obstacleCount,
  currentMaterialName,
  onStartOptimization,
  onStopOptimization
}) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between gap-4 select-none shadow-md z-20">
      {/* Brand: Solo el nombre "Topologia Optimizada" */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-md shadow-sky-500/20 text-white font-bold">
          <Cpu className="w-5 h-5" />
        </div>
        <div className="flex flex-col">
          <h1 className="text-base font-bold text-slate-100 tracking-tight leading-tight">
            Topologia Optimizada
          </h1>
          <span className="text-[10px] text-slate-400 font-medium leading-none">
            {mode === 'generativa' ? 'Modo Generativo Orgánico' : 'Modo Estructural SIMP'}
          </span>
        </div>
      </div>

      {/* Barra de botones superior: Solo las herramientas solicitadas */}
      <nav aria-label="Herramientas principales" className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 shadow-inner">
        {/* 1. Carga */}
        <button
          onClick={() => onSelectTool('carga')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTool === 'carga'
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
          title="Herramienta de Carga: Magnitud, dirección vectorial y puntos de aplicación de fuerzas"
        >
          <ArrowDownCircle className={`w-4 h-4 ${activeTool === 'carga' ? 'text-rose-400' : 'text-slate-400'}`} />
          <span>Carga</span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900/80 text-rose-400 border border-rose-500/20">
            {(loadMagnitude / 1000).toFixed(0)} kN
          </span>
        </button>

        {/* 2. Materiales */}
        <button
          onClick={() => onSelectTool('materiales')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTool === 'materiales'
              ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
          title="Ventana de Materiales: Biblioteca y creación de materiales personalizados"
        >
          <Layers className={`w-4 h-4 ${activeTool === 'materiales' ? 'text-sky-400' : 'text-slate-400'}`} />
          <span>Materiales</span>
          {currentMaterialName && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900/80 text-sky-400 border border-sky-500/20 max-w-[80px] truncate">
              {currentMaterialName.split(' ')[0]}
            </span>
          )}
        </button>

        {/* 3. Elasticidad */}
        <button
          onClick={() => onSelectTool('elasticidad')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTool === 'elasticidad'
              ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
          title="Herramienta de Elasticidad: Módulo de Young (E), Poisson, límite elástico y materiales"
        >
          <Atom className={`w-4 h-4 ${activeTool === 'elasticidad' ? 'text-indigo-400' : 'text-slate-400'}`} />
          <span>Elasticidad</span>
        </button>

        {/* 3. Obstrucciones */}
        <button
          onClick={() => onSelectTool('obstrucciones')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTool === 'obstrucciones'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
          title="Herramienta de Obstrucciones: Zonas de exclusión de material (taladros, canales de paso)"
        >
          <Ban className={`w-4 h-4 ${activeTool === 'obstrucciones' ? 'text-amber-400' : 'text-slate-400'}`} />
          <span>Obstrucciones</span>
          {obstacleCount > 0 && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900/80 text-amber-400 border border-amber-500/20">
              {obstacleCount}
            </span>
          )}
        </button>

        {/* 4. Protegida */}
        <button
          onClick={() => onSelectTool('protegida')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTool === 'protegida'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
          title="Herramienta Protegida: Caras y zonas que NO se modificarán en la optimización (100% sólidas)"
        >
          <ShieldCheck className={`w-4 h-4 ${activeTool === 'protegida' ? 'text-emerald-400' : 'text-slate-400'}`} />
          <span>Protegida</span>
          {protectedCount > 0 && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900/80 text-emerald-400 border border-emerald-500/20">
              {protectedCount}
            </span>
          )}
        </button>

        {/* 5. Optimizar */}
        <button
          onClick={() => onSelectTool('optimizar')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            activeTool === 'optimizar'
              ? 'bg-sky-500 text-white shadow-md shadow-sky-500/25'
              : isOptimizing
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
              : 'text-sky-300 hover:text-white hover:bg-sky-600/30'
          }`}
          title="Herramienta de Optimización: Selección de modo (Generativa o Estructural) y cálculo de malla"
        >
          {isOptimizing ? (
            <span className="w-3.5 h-3.5 border-2 border-amber-300 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          <span>Optimizar</span>
        </button>

        {/* 6. Análisis */}
        <button
          onClick={() => onSelectTool('analisis')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            activeTool === 'analisis'
              ? 'bg-violet-500/20 text-violet-300 border border-violet-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
          title="Herramienta de Análisis: Tensiones Von Mises, desplazamientos elásticos y exportación CAD (STEP / STL)"
        >
          <BarChart3 className={`w-4 h-4 ${activeTool === 'analisis' ? 'text-violet-400' : 'text-slate-400'}`} />
          <span>Análisis</span>
        </button>
      </nav>

      {/* Selector de Modo: Generativa vs Estructural */}
      <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs shrink-0">
        <span className="text-[11px] text-slate-500 font-medium px-2 hidden xl:inline">Modo:</span>
        <button
          onClick={() => onModeChange('generativa')}
          disabled={isOptimizing}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            mode === 'generativa'
              ? 'bg-sky-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
          title="Optimización Generativa: Estructuras bio-inspiradas, ramificación celular continua y aligeramiento para impresión 3D"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Generativa
        </button>
        <button
          onClick={() => onModeChange('estructural')}
          disabled={isOptimizing}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
            mode === 'estructural'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
          title="Optimización Estructural: Rigidez estática pura, celosía Michell directa y perfiles nítidos para mecanizado CNC"
        >
          <Layers className="w-3.5 h-3.5" />
          Estructural
        </button>
      </div>
    </header>
  );
};
