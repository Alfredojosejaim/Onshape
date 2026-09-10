import React, { useState } from 'react';
import { Viewport3D } from '../Viewport3D';
import { FeaResults, MaterialProperties } from '../../types';

interface SolverFeaScreenProps {
  fea: FeaResults;
  material: MaterialProperties;
  onUpdateDeformedScale: (scale: number) => void;
  onSolveFea: () => void;
  onProceedToSimp: () => void;
  forceMagnitude: number;
}

export const SolverFeaScreen: React.FC<SolverFeaScreenProps> = ({
  fea,
  material,
  onUpdateDeformedScale,
  onSolveFea,
  onProceedToSimp,
  forceMagnitude,
}) => {
  const [activeStressType, setActiveStressType] = useState<'vonMises' | 'tresca' | 'principal1' | 'displacement'>('vonMises');
  const [solverType, setSolverType] = useState<'Cholesky' | 'PCG'>('Cholesky');

  return (
    <div className="w-full flex flex-col xl:flex-row gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* LEFT PANEL: Solver Settings & Diagnostics */}
      <aside className="w-full xl:w-72 2xl:w-80 flex flex-col gap-2 flex-shrink-0">
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">memory</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Motor de Resolución FEA</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">Pardiso MKL</span>
          </header>

          <div className="flex flex-col gap-2 text-xs">
            {/* Solver type */}
            <div>
              <label className="font-mono text-[10px] text-[#64748b]">Algoritmo Matricial:</label>
              <div className="grid grid-cols-2 gap-1 mt-1">
                <button
                  type="button"
                  onClick={() => setSolverType('Cholesky')}
                  className={`py-1 text-center font-mono text-[11px] rounded border transition-colors cursor-pointer ${
                    solverType === 'Cholesky'
                      ? 'bg-[#0ea5e9]/20 border-[#0ea5e9] text-[#7bd0ff] font-bold'
                      : 'bg-[#1f2430] border-[#2e3646] text-[#94a3b8]'
                  }`}
                >
                  Directo Cholesky
                </button>
                <button
                  type="button"
                  onClick={() => setSolverType('PCG')}
                  className={`py-1 text-center font-mono text-[11px] rounded border transition-colors cursor-pointer ${
                    solverType === 'PCG'
                      ? 'bg-[#0ea5e9]/20 border-[#0ea5e9] text-[#7bd0ff] font-bold'
                      : 'bg-[#1f2430] border-[#2e3646] text-[#94a3b8]'
                  }`}
                >
                  Iterativo PCG
                </button>
              </div>
            </div>

            {/* Run Solver button */}
            <button
              onClick={onSolveFea}
              disabled={fea.isSolving}
              className="w-full py-1.5 px-3 bg-[#1f2430] hover:bg-[#272a33] text-[#f1f5f9] hover:text-[#7bd0ff] border border-[#2e3646] rounded flex items-center justify-center gap-1.5 font-semibold text-xs transition-all cursor-pointer disabled:opacity-50"
              type="button"
            >
              <span className={`material-symbols-outlined text-[16px] ${fea.isSolving ? 'animate-spin' : ''}`}>
                {fea.isSolving ? 'sync' : 'play_circle'}
              </span>
              <span>{fea.isSolving ? 'Resolviendo Ku = F...' : 'Re-ejecutar Solver'}</span>
            </button>

            {/* Solver logs */}
            <div className="bg-[#0b0e17] p-2 rounded border border-[#2e3646]/60 font-mono text-[10px] text-[#94a3b8] flex flex-col gap-1">
              <span className="text-[#10b981] flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px]">check_circle</span>
                Convergencia de Residuos: 1.2e-8
              </span>
              <div className="flex justify-between">
                <span>Tiempo de Cálculo:</span>
                <span className="text-[#f1f5f9]">{fea.solveTimeSeconds} s</span>
              </div>
              <div className="flex justify-between">
                <span>Número de Hilos:</span>
                <span className="text-[#7bd0ff]">16 OpenMP</span>
              </div>
            </div>
          </div>
        </section>

        {/* Stress Field Selector */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <span className="text-xs font-semibold text-[#f1f5f9]">Campo de Tensiones</span>
            <span className="text-[10px] font-mono text-[#7bd0ff]">Isosurperficies</span>
          </header>

          <div className="flex flex-col gap-1 text-xs">
            {[
              { id: 'vonMises', label: 'Tensión Equivalente Von Mises (σ_v)', peak: `${fea.maxVonMises} MPa` },
              { id: 'tresca', label: 'Criterio de Tresca (2 · τ_max)', peak: '512.1 MPa' },
              { id: 'principal1', label: 'Tensión Principal Mayor (σ_1)', peak: '468.9 MPa' },
              { id: 'displacement', label: 'Desplazamiento Total (|U|)', peak: `${fea.maxDisplacement} mm` },
            ].map((item) => (
              <div
                key={item.id}
                onClick={() => setActiveStressType(item.id as any)}
                className={`p-1.5 rounded cursor-pointer transition-colors flex items-center justify-between ${
                  activeStressType === item.id
                    ? 'bg-[#0ea5e9]/20 text-[#7bd0ff] font-medium border border-[#0ea5e9]/40'
                    : 'bg-[#1f2430]/40 hover:bg-[#272a33] text-[#94a3b8]'
                }`}
              >
                <span>{item.label}</span>
                <span className="font-mono text-[10px] text-[#f1f5f9]">{item.peak}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Deformed shape amplification */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <span className="text-xs font-semibold text-[#f1f5f9]">Escala de Deformación</span>
            <span className="text-[10px] font-mono text-[#10b981]">{fea.deformedScale}x</span>
          </header>

          <div className="grid grid-cols-4 gap-1">
            {[1, 5, 20, 50].map((scale) => (
              <button
                key={scale}
                type="button"
                onClick={() => onUpdateDeformedScale(scale)}
                className={`py-1 text-center font-mono text-xs rounded border transition-colors cursor-pointer ${
                  fea.deformedScale === scale
                    ? 'bg-[#0ea5e9] text-[#003751] font-bold border-[#0ea5e9]'
                    : 'bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9] border-[#2e3646]'
                }`}
              >
                {scale}x
              </button>
            ))}
          </div>
        </section>
      </aside>

      {/* CENTER: 3D FEA Thermal Stress Viewer */}
      <Viewport3D
        activeTab="solver-fea"
        forceMagnitude={forceMagnitude}
        feaDeformedScale={fea.deformedScale}
        feaStressType={activeStressType}
      />

      {/* RIGHT PANEL: Results Inspector & Safety Margins */}
      <aside className="w-full xl:w-80 2xl:w-88 flex flex-col gap-2 flex-shrink-0">
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">verified</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Márgenes de Seguridad</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">ASTM E8</span>
          </header>

          <div className="flex flex-col gap-1.5">
            {/* Safety Factor hero block */}
            <div className="p-2.5 rounded bg-[#1f2430] border border-[#2e3646] flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono text-[#64748b] block">Factor de Seguridad (SF):</span>
                <span className="font-mono text-lg font-bold text-[#10b981]">
                  {fea.safetyFactor.toFixed(2)}
                </span>
                <span className="text-[9px] text-[#94a3b8] block">σ_y (503) / σ_max (482.4)</span>
              </div>
              <div className="px-2 py-1 rounded bg-[#10b981]/20 border border-[#10b981]/40 text-[#10b981] font-mono text-[10px] font-bold">
                ESTRUCTURA SEGURA
              </div>
            </div>

            {/* Numerical breakdown */}
            <div className="flex flex-col gap-1 font-mono text-[11px]">
              <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
                <span className="text-[#94a3b8] font-sans text-xs">Tensión Máxima:</span>
                <span className="text-[#ef4444] font-bold">{fea.maxVonMises} MPa</span>
              </div>
              <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
                <span className="text-[#94a3b8] font-sans text-xs">Límite Elástico Material:</span>
                <span className="text-[#f59e0b] font-bold">{material.yieldStrength} MPa</span>
              </div>
              <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
                <span className="text-[#94a3b8] font-sans text-xs">Desplazamiento Máx (|U|):</span>
                <span className="text-[#7bd0ff] font-bold">{fea.maxDisplacement} mm</span>
              </div>
              <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
                <span className="text-[#94a3b8] font-sans text-xs">Energía Deformación (U_e):</span>
                <span className="text-[#f1f5f9]">{fea.strainEnergy} mJ</span>
              </div>
            </div>
          </div>
        </section>

        {/* Diagnosis for Topology Optimization */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <span className="text-xs font-semibold text-[#f1f5f9]">Diagnóstico SIMP</span>
            <span className="text-[10px] font-mono text-[#7bd0ff]">65% Ineficiente</span>
          </header>

          <p className="text-[#94a3b8] text-xs leading-relaxed">
            El 65% del volumen sólido registra tensiones inferiores a <strong className="text-[#7bd0ff]">40 MPa</strong>.
            Esta masa pasiva no contribuye a la rigidez del soporte y puede removerse matemáticamente mediante el método SIMP.
          </p>
        </section>

        {/* Primary CTA */}
        <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md border border-[#2e3646]/60 flex flex-col gap-2 mt-auto">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-mono text-[10px] text-[#94a3b8]">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                FEA Completado
              </span>
              <span className="text-[#7bd0ff] font-bold">4.82 s</span>
            </div>
            <p className="text-[#64748b] text-[11px] leading-tight">
              Avanza a la formulación de optimización topológica para maximizar la rigidez con fracción de volumen objetivo de 0.35.
            </p>
          </div>

          <button
            onClick={onProceedToSimp}
            className="w-full py-2 px-3 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-semibold text-xs rounded-lg shadow-lg hover:shadow-cyan-500/20 flex items-center justify-center gap-1.5 transition-all transform active:scale-98 cursor-pointer"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">play_arrow</span>
            <span>Optimización Topológica (SIMP)</span>
          </button>
        </section>
      </aside>
    </div>
  );
};
