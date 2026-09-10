import React, { useState, useEffect } from 'react';
import { Viewport3D } from '../Viewport3D';
import { SimpOptimizationState } from '../../types';

interface OptimizacionSimpScreenProps {
  simpState: SimpOptimizationState;
  onUpdateSimpState: (updater: (prev: SimpOptimizationState) => SimpOptimizationState) => void;
  onProceedToExport: () => void;
  forceMagnitude: number;
}

export const OptimizacionSimpScreen: React.FC<OptimizacionSimpScreenProps> = ({
  simpState,
  onUpdateSimpState,
  onProceedToExport,
  forceMagnitude,
}) => {
  const [isAutoRunning, setIsAutoRunning] = useState(false);

  // Animated runner for SIMP iterations
  useEffect(() => {
    let timer: any;
    if (isAutoRunning && simpState.currentIteration < simpState.maxIterations) {
      timer = setInterval(() => {
        onUpdateSimpState((prev) => {
          const nextIter = Math.min(prev.maxIterations, prev.currentIteration + 1);
          const progress = nextIter / prev.maxIterations;
          const currentCompliance = prev.initialCompliance - progress * (prev.initialCompliance - 107.6);
          const currentVf = 1.0 - progress * (1.0 - prev.targetVolumeFraction);

          if (nextIter >= prev.maxIterations) {
            setIsAutoRunning(false);
          }

          return {
            ...prev,
            currentIteration: nextIter,
            currentCompliance: Math.round(currentCompliance * 10) / 10,
            currentVolumeFraction: Math.round(currentVf * 100) / 100,
            isCompleted: nextIter >= prev.maxIterations,
            history: [
              ...prev.history,
              {
                iteration: nextIter,
                compliance: currentCompliance,
                volumeFraction: currentVf,
                change: Math.max(0.0001, (1 - progress) * 0.05),
              },
            ],
          };
        });
      }, 180);
    }
    return () => clearInterval(timer);
  }, [isAutoRunning, simpState.currentIteration, simpState.maxIterations, onUpdateSimpState]);

  const handleReset = () => {
    setIsAutoRunning(false);
    onUpdateSimpState((prev) => ({
      ...prev,
      currentIteration: 0,
      currentCompliance: prev.initialCompliance,
      currentVolumeFraction: 1.0,
      isCompleted: false,
      history: [{ iteration: 0, compliance: prev.initialCompliance, volumeFraction: 1.0, change: 0 }],
    }));
  };

  const handleStep = () => {
    if (simpState.currentIteration < simpState.maxIterations) {
      onUpdateSimpState((prev) => {
        const nextIter = prev.currentIteration + 1;
        const progress = nextIter / prev.maxIterations;
        const currentCompliance = prev.initialCompliance - progress * (prev.initialCompliance - 107.6);
        const currentVf = 1.0 - progress * (1.0 - prev.targetVolumeFraction);
        return {
          ...prev,
          currentIteration: nextIter,
          currentCompliance: Math.round(currentCompliance * 10) / 10,
          currentVolumeFraction: Math.round(currentVf * 100) / 100,
          isCompleted: nextIter >= prev.maxIterations,
        };
      });
    }
  };

  return (
    <div className="w-full flex flex-col xl:flex-row gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* LEFT PANEL: SIMP Parameters & Run Controls */}
      <aside className="w-full xl:w-72 2xl:w-80 flex flex-col gap-2 flex-shrink-0">
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">model_training</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Parámetros SIMP</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">p = {simpState.penaltyFactor}</span>
          </header>

          <div className="flex flex-col gap-2 text-xs">
            {/* Penalization Factor Slider */}
            <div className="bg-[#1f2430]/50 p-2 rounded flex flex-col gap-1">
              <div className="flex justify-between items-center">
                <span className="text-[#f1f5f9]">Factor Penalización (p):</span>
                <span className="font-mono text-[#7bd0ff] font-bold">{simpState.penaltyFactor}</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="5.0"
                step="0.5"
                value={simpState.penaltyFactor}
                onChange={(e) =>
                  onUpdateSimpState((prev) => ({ ...prev, penaltyFactor: parseFloat(e.target.value) }))
                }
                className="w-full accent-[#0ea5e9] cursor-pointer"
              />
              <span className="text-[9px] font-mono text-[#64748b]">E_e = E_min + ρ^p · (E_0 - E_min)</span>
            </div>

            {/* Filter Radius */}
            <div className="bg-[#1f2430]/50 p-2 rounded flex flex-col gap-1">
              <div className="flex justify-between items-center">
                <span className="text-[#f1f5f9]">Radio de Filtro (r_min):</span>
                <span className="font-mono text-[#7bd0ff] font-bold">{simpState.filterRadius} mm</span>
              </div>
              <input
                type="range"
                min="2.0"
                max="10.0"
                step="0.5"
                value={simpState.filterRadius}
                onChange={(e) =>
                  onUpdateSimpState((prev) => ({ ...prev, filterRadius: parseFloat(e.target.value) }))
                }
                className="w-full accent-[#0ea5e9] cursor-pointer"
              />
              <span className="text-[9px] font-mono text-[#64748b]">Evita formación de tablero de ajedrez</span>
            </div>

            {/* Target Volume Fraction */}
            <div className="bg-[#1f2430]/50 p-2 rounded flex flex-col gap-1">
              <div className="flex justify-between items-center">
                <span className="text-[#f1f5f9]">Fracción de Volumen (VF):</span>
                <span className="font-mono text-[#10b981] font-bold">
                  {(simpState.targetVolumeFraction * 100).toFixed(0)}% (-65%)
                </span>
              </div>
              <input
                type="range"
                min="0.20"
                max="0.80"
                step="0.05"
                value={simpState.targetVolumeFraction}
                onChange={(e) =>
                  onUpdateSimpState((prev) => ({ ...prev, targetVolumeFraction: parseFloat(e.target.value) }))
                }
                className="w-full accent-[#0ea5e9] cursor-pointer"
              />
            </div>

            {/* Execution Controls */}
            <div className="grid grid-cols-2 gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => setIsAutoRunning(!isAutoRunning)}
                className={`py-2 px-2 rounded flex items-center justify-center gap-1 font-semibold transition-all cursor-pointer ${
                  isAutoRunning
                    ? 'bg-[#ef4444] text-[#ffffff]'
                    : 'bg-[#0ea5e9] text-[#003751] hover:bg-[#7bd0ff]'
                }`}
              >
                <span className="material-symbols-outlined text-[16px]">
                  {isAutoRunning ? 'pause' : 'play_arrow'}
                </span>
                <span>{isAutoRunning ? 'Pausar' : 'Optimizar'}</span>
              </button>

              <button
                type="button"
                onClick={handleStep}
                disabled={isAutoRunning || simpState.currentIteration >= simpState.maxIterations}
                className="py-2 px-2 bg-[#1f2430] hover:bg-[#272a33] border border-[#2e3646] text-[#f1f5f9] rounded flex items-center justify-center gap-1 font-semibold transition-colors disabled:opacity-50 cursor-pointer"
              >
                <span className="material-symbols-outlined text-[16px]">skip_next</span>
                <span>Paso +1</span>
              </button>
            </div>

            <button
              type="button"
              onClick={handleReset}
              className="py-1 px-2 text-[11px] text-[#94a3b8] hover:text-[#f1f5f9] flex items-center justify-center gap-1 hover:underline cursor-pointer"
            >
              <span className="material-symbols-outlined text-[14px]">restart_alt</span>
              <span>Reiniciar Iteraciones a #0</span>
            </button>
          </div>
        </section>

        {/* Density threshold slider */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <span className="text-xs font-semibold text-[#f1f5f9]">Corte de Densidad Relativa</span>
            <span className="text-[10px] font-mono text-[#7bd0ff]">ρ &gt; {simpState.densityCutoff}</span>
          </header>

          <div className="flex flex-col gap-1 text-xs">
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={simpState.densityCutoff}
              onChange={(e) =>
                onUpdateSimpState((prev) => ({ ...prev, densityCutoff: parseFloat(e.target.value) }))
              }
              className="w-full accent-[#0ea5e9] cursor-pointer"
            />
            <div className="flex justify-between text-[10px] font-mono text-[#64748b]">
              <span>0.1 (Poroso)</span>
              <span>0.5 (Estándar)</span>
              <span>0.9 (Macizo)</span>
            </div>
          </div>
        </section>
      </aside>

      {/* CENTER: Viewport 3D in SIMP Mode */}
      <Viewport3D
        activeTab="optimizacion-simp"
        forceMagnitude={forceMagnitude}
        simpIteration={simpState.currentIteration}
        simpDensityCutoff={simpState.densityCutoff}
      />

      {/* RIGHT PANEL: Live Convergence Charts & Optimization Diagnostics */}
      <aside className="w-full xl:w-80 2xl:w-88 flex flex-col gap-2 flex-shrink-0">
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">show_chart</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Curva de Convergencia</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">OC Method</span>
          </header>

          {/* SVG Convergence Graph */}
          <div className="bg-[#0b0e17] p-2 rounded border border-[#2e3646]/60 flex flex-col gap-1">
            <div className="flex justify-between text-[10px] font-mono">
              <span className="text-[#0ea5e9]">● Compliance: {simpState.currentCompliance}</span>
              <span className="text-[#10b981]">● Vol. Frac: {simpState.currentVolumeFraction}</span>
            </div>

            <svg className="w-full h-28" viewBox="0 0 240 100">
              {/* Background grid lines */}
              <line x1="0" y1="20" x2="240" y2="20" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="0.5" />
              <line x1="0" y1="50" x2="240" y2="50" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="0.5" />
              <line x1="0" y1="80" x2="240" y2="80" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="0.5" />

              {/* Compliance curve (Cyan, dropping) */}
              <path
                d="M 10,20 Q 50,60 120,70 T 230,78"
                fill="none"
                stroke="#0ea5e9"
                strokeWidth="2"
                strokeLinecap="round"
              />

              {/* Volume fraction curve (Green, converging to 0.35) */}
              <path
                d="M 10,15 Q 60,70 140,85 T 230,85"
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
                strokeLinecap="round"
              />

              {/* Current iteration marker dot */}
              {(() => {
                const xPos = 10 + (simpState.currentIteration / 50) * 220;
                return (
                  <g>
                    <line x1={xPos} y1="0" x2={xPos} y2="100" stroke="#ffffff" strokeWidth="1" strokeDasharray="2 2" />
                    <circle cx={xPos} cy="78" r="3" fill="#0ea5e9" />
                  </g>
                );
              })()}
            </svg>

            <div className="flex justify-between text-[9px] font-mono text-[#64748b]">
              <span>Iteración 0</span>
              <span>Iteración 25</span>
              <span>Iteración 50</span>
            </div>
          </div>

          {/* Metric details */}
          <div className="flex flex-col gap-1 font-mono text-[11px] pt-1">
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Compliance Inicial:</span>
              <span className="text-[#f1f5f9]">{simpState.initialCompliance} J</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Compliance Actual:</span>
              <span className="text-[#7bd0ff] font-bold">{simpState.currentCompliance} J</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Masa Estructural Final:</span>
              <span className="text-[#10b981] font-bold">
                {(3.42 * simpState.currentVolumeFraction).toFixed(2)} kg
              </span>
            </div>
          </div>
        </section>

        {/* Primary CTA */}
        <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md border border-[#2e3646]/60 flex flex-col gap-2 mt-auto">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-mono text-[10px] text-[#94a3b8]">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                Convergencia: {simpState.currentIteration >= 45 ? '100% Óptima' : `${simpState.currentIteration}/50`}
              </span>
              <span className="text-[#10b981] font-bold">-65% Masa</span>
            </div>
            <p className="text-[#64748b] text-[11px] leading-tight">
              Reconstruye la malla de densidad en una superficie suave NURBS B-Rep lista para fabricación aditiva o CNC.
            </p>
          </div>

          <button
            onClick={onProceedToExport}
            className="w-full py-2 px-3 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-semibold text-xs rounded-lg shadow-lg hover:shadow-cyan-500/20 flex items-center justify-center gap-1.5 transition-all transform active:scale-98 cursor-pointer"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">play_arrow</span>
            <span>Generativo & B-Rep Export</span>
          </button>
        </section>
      </aside>
    </div>
  );
};
