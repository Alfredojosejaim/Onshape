import React from 'react';
import { Material, SimpParameters, OptimizationState, ActiveTab, FeaResults } from '../types';

interface RightPanelProps {
  activeTab: ActiveTab;
  materials: Material[];
  selectedMaterial: Material;
  onSelectMaterial: (m: Material) => void;
  simpParams: SimpParameters;
  onChangeSimpParams: (params: SimpParameters) => void;
  optimizationState: OptimizationState;
  onStartOptimization: () => void;
  onPauseOptimization: () => void;
  onResetOptimization: () => void;
  feaResults: FeaResults;
  deformationScale: number;
  onChangeDeformationScale: (scale: number) => void;
  onExportReport: () => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({
  activeTab,
  materials,
  selectedMaterial,
  onSelectMaterial,
  simpParams,
  onChangeSimpParams,
  optimizationState,
  onStartOptimization,
  onPauseOptimization,
  onResetOptimization,
  feaResults,
  deformationScale,
  onChangeDeformationScale,
  onExportReport,
}) => {
  return (
    <aside className="w-full xl:w-80 2xl:w-88 flex flex-col gap-space-sm flex-shrink-0 select-none">
      {/* Material Library Card */}
      <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-xs border border-border-subtle/40">
        <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated/70 rounded text-[11px] font-semibold text-text-primary">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-secondary text-[15px]">science</span>
            <span>Biblioteca de Materiales CAE</span>
          </div>
          <span className="text-[10px] font-mono text-text-muted">ISO 9001</span>
        </header>

        {/* Alloy Selector Dropdown */}
        <div className="flex flex-col gap-1 pt-1">
          <label className="font-mono text-[10px] text-text-muted">Aleación / Polímero:</label>
          <div className="relative">
            <select
              id="material-select"
              value={selectedMaterial.id}
              onChange={(e) => {
                const found = materials.find((m) => m.id === e.target.value);
                if (found) onSelectMaterial(found);
              }}
              className="w-full bg-surface-elevated border border-border-subtle/60 rounded px-2.5 py-1.5 font-medium text-[12px] text-text-primary appearance-none cursor-pointer focus:ring-1 focus:ring-secondary focus:outline-none pr-8 transition-colors"
            >
              {materials.map((mat) => (
                <option key={mat.id} value={mat.id} className="bg-surface-container-low text-text-primary">
                  {mat.name}
                </option>
              ))}
            </select>
            <span className="material-symbols-outlined text-text-muted text-[16px] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
              expand_more
            </span>
          </div>
        </div>

        {/* Constitutive Law Table */}
        <div className="flex flex-col gap-1 pt-1 font-mono text-[11px]">
          <div className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Módulo Young (E):</span>
            <span className="text-text-primary font-bold">{selectedMaterial.youngModulus.toFixed(1)} GPa</span>
          </div>
          <div className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Coef. Poisson (ν):</span>
            <span className="text-text-primary font-bold">{selectedMaterial.poissonRatio.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Límite Elástico (σ_y):</span>
            <span className="text-fea-stress-yield font-bold">{selectedMaterial.yieldStrength.toFixed(1)} MPa</span>
          </div>
          <div className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Densidad (ρ):</span>
            <span className="text-text-primary font-bold">{selectedMaterial.density.toFixed(2)} g/cm³</span>
          </div>
          <div className="flex items-center justify-between py-1 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Resistencia Tracción:</span>
            <span className="text-text-primary font-bold">
              {selectedMaterial.tensileStrength !== undefined
                ? `${selectedMaterial.tensileStrength.toFixed(1)} MPa`
                : '—'}
            </span>
          </div>
        </div>
      </section>

      {/* Tab Conditional: Optimization Parameters or FEA Results */}
      {activeTab === 'optimizacion' ? (
        /* CAE Study Metrics & SIMP Optimization Parameters */
        <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-sm border border-border-subtle/50">
          <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated rounded border border-border-subtle/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-secondary text-[16px]">tune</span>
              <span className="font-semibold text-[12px] text-text-primary">Parámetros de Optimización</span>
            </div>
            <span className="px-1.5 py-0.5 rounded bg-secondary/10 border border-secondary/30 text-secondary font-mono text-[10px] font-semibold tracking-wider">
              SIMP
            </span>
          </header>

          <div className="flex flex-col gap-2 text-[11px]">
            {/* Volume Fraction Slider */}
            <div className="flex flex-col gap-1 bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="text-text-secondary flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px] text-secondary">pie_chart</span>
                  Fracción de Volumen (Volfrac)
                </span>
                <span className="text-secondary font-bold font-mono">
                  {simpParams.volfrac.toFixed(2)} ({Math.round(simpParams.volfrac * 100)}%)
                </span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.80"
                step="0.05"
                value={simpParams.volfrac}
                disabled={optimizationState.isRunning}
                onChange={(e) =>
                  onChangeSimpParams({ ...simpParams, volfrac: parseFloat(e.target.value) })
                }
                className="w-full h-1.5 bg-surface-container-lowest rounded-full appearance-none cursor-pointer accent-secondary"
              />
              <div className="flex justify-between text-[9px] text-text-muted font-mono">
                <span>0.10 (Extremo)</span>
                <span>Volumen retenido objetivo</span>
                <span>0.80 (Ligero)</span>
              </div>
            </div>

            {/* Grid 2x2 Parameters */}
            <div className="grid grid-cols-2 gap-1.5">
              <div className="flex flex-col gap-0.5 bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <div className="flex items-center justify-between">
                  <span className="text-text-muted font-mono text-[10px]">Penalización (p)</span>
                  <span className="text-tertiary font-bold font-mono text-[11px]">p = {simpParams.penalization.toFixed(1)}</span>
                </div>
                <div className="text-[9px] font-mono text-text-secondary truncate" title="Ke(ρ) = ρ^p · Ke0">
                  K_e(ρ) = ρ³ · K₀
                </div>
              </div>

              <div className="flex flex-col gap-0.5 bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <div className="flex items-center justify-between">
                  <span className="text-text-muted font-mono text-[10px]">Radio Filtro (r_min)</span>
                  <span className="text-text-primary font-bold font-mono text-[11px]">{simpParams.filterRadius.toFixed(2)} mm</span>
                </div>
                <div className="text-[9px] font-mono text-text-secondary truncate" title="Filtro de densidades anti-checkerboard">
                  Anti-checkerboard
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-1.5">
              <div className="flex items-center justify-between px-2 py-1 rounded bg-surface-elevated/40 border border-border-subtle/30 text-[10px] font-mono">
                <span className="text-text-muted">Tol. Conv. (Δρ)</span>
                <span className="text-text-primary font-semibold">1e-03</span>
              </div>
              <div className="flex items-center justify-between px-2 py-1 rounded bg-surface-elevated/40 border border-border-subtle/30 text-[10px] font-mono">
                <span className="text-text-muted">Max Iteraciones</span>
                <span className="text-text-primary font-semibold">{simpParams.maxIterations}</span>
              </div>
            </div>

            {/* Subdomains */}
            <div className="flex flex-col gap-1 bg-surface-elevated/20 p-2 rounded border border-border-subtle/30 font-mono text-[10px]">
              <span className="text-text-muted font-medium flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px] text-fea-stress-optimal">lock</span>
                Subdominios y Restricciones Activas:
              </span>
              <div className="flex items-center justify-between pl-2">
                <span className="text-text-secondary flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-fea-stress-optimal"></span>
                  Región Preservada (Pernos/Bujes)
                </span>
                <span className="text-fea-stress-optimal font-semibold">ρ = 1.0</span>
              </div>
              <div className="flex items-center justify-between pl-2">
                <span className="text-text-secondary flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-fea-stress-critical"></span>
                  Keep-out (Paso Tornillo)
                </span>
                <span className="text-fea-stress-critical font-semibold">ρ = 0.0</span>
              </div>
            </div>

            {/* Live Optimization Progress if Running/Finished */}
            {(optimizationState.currentIteration > 0 || optimizationState.isRunning) && (
              <div className="flex flex-col gap-1.5 bg-surface-elevated/60 p-2.5 rounded border border-secondary/30">
                <div className="flex items-center justify-between font-mono text-[11px]">
                  <span className="text-text-secondary">Iteración SIMP:</span>
                  <span className="text-secondary font-bold">
                    {optimizationState.currentIteration} / {optimizationState.totalIterations}
                  </span>
                </div>
                <div className="w-full bg-surface-container-lowest h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-primary-container to-secondary h-full transition-all duration-150"
                    style={{
                      width: `${(optimizationState.currentIteration / optimizationState.totalIterations) * 100}%`,
                    }}
                  ></div>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[10px] font-mono pt-1 text-text-muted">
                  <div>
                    Masa: <span className="text-text-primary font-semibold">{optimizationState.currentMassKg.toFixed(2)} kg</span>
                    <span className="text-fea-stress-optimal text-[9px] ml-1">
                      (-{Math.round((1 - optimizationState.currentMassKg / optimizationState.initialMassKg) * 100)}%)
                    </span>
                  </div>
                  <div className="text-right">
                    Cumplimiento: <span className="text-secondary font-semibold">{optimizationState.currentCompliance.toFixed(1)} mJ</span>
                  </div>
                </div>
              </div>
            )}

            {/* Main Action Buttons */}
            <div className="flex gap-1.5 pt-1">
              {!optimizationState.isRunning ? (
                <button
                  id="start-simp-btn"
                  type="button"
                  onClick={onStartOptimization}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-primary-container hover:bg-secondary text-on-primary font-semibold text-[12px] transition-all shadow-md active:scale-[0.99]"
                >
                  <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                  <span>
                    {optimizationState.currentIteration > 0 && !optimizationState.isPaused
                      ? 'Reanudar Optimización'
                      : 'Iniciar Optimización SIMP'}
                  </span>
                </button>
              ) : (
                <button
                  id="pause-simp-btn"
                  type="button"
                  onClick={onPauseOptimization}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-fea-stress-yield hover:bg-amber-400 text-[#0b0e17] font-semibold text-[12px] transition-all shadow-md active:scale-[0.99]"
                >
                  <span className="material-symbols-outlined text-[16px]">pause</span>
                  <span>Pausar Iteración</span>
                </button>
              )}

              {optimizationState.currentIteration > 0 && (
                <button
                  id="reset-simp-btn"
                  type="button"
                  onClick={onResetOptimization}
                  className="px-3 py-2 rounded-lg bg-surface-elevated hover:bg-surface-container-high border border-border-subtle text-text-secondary hover:text-text-primary text-[11px] transition-colors"
                  title="Reiniciar a sólido inicial"
                >
                  <span className="material-symbols-outlined text-[16px]">restart_alt</span>
                </button>
              )}
            </div>
          </div>
        </section>
      ) : (
        /* Analysis Mode Panel: Finite Element Analysis (FEA) Metrics */
        <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-sm border border-border-subtle/50">
          <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated rounded border border-border-subtle/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-secondary text-[16px]">analytics</span>
              <span className="font-semibold text-[12px] text-text-primary">Resultados Tensión FEA</span>
            </div>
            <span className="px-1.5 py-0.5 rounded bg-fea-stress-optimal/20 border border-fea-stress-optimal/40 text-fea-stress-optimal font-mono text-[10px] font-semibold">
              VON MISES
            </span>
          </header>

          <div className="flex flex-col gap-2 text-[11px]">
            {/* Stress gauge */}
            <div className="bg-surface-elevated/40 p-2.5 rounded border border-border-subtle/30 flex flex-col gap-1.5">
              <div className="flex items-center justify-between font-mono">
                <span className="text-text-muted text-[10px]">Tensión Máx. Von Mises:</span>
                <span className="text-fea-stress-yield font-bold text-[13px]">
                  {feaResults.maxVonMisesMpa.toFixed(1)} MPa
                </span>
              </div>
              {/* Thermal color bar legend */}
              <div className="w-full h-2 rounded-full overflow-hidden flex">
                <div className="bg-[#38bdf8] flex-1"></div>
                <div className="bg-[#10b981] flex-1"></div>
                <div className="bg-[#f59e0b] flex-1"></div>
                <div className="bg-[#ef4444] flex-1"></div>
              </div>
              <div className="flex justify-between text-[9px] font-mono text-text-muted">
                <span>0 MPa (Mín)</span>
                <span>σ_y = {selectedMaterial.yieldStrength} MPa</span>
                <span className="text-fea-stress-critical font-semibold">Crítico</span>
              </div>
            </div>

            {/* FEA Metrics Grid */}
            <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
              <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <span className="text-text-muted text-[9px] block">Factor de Seguridad:</span>
                <span className="text-fea-stress-optimal font-bold text-[12px]">
                  SF = {feaResults.minSafetyFactor.toFixed(2)}
                </span>
              </div>
              <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <span className="text-text-muted text-[9px] block">Desplazamiento Máx:</span>
                <span className="text-secondary font-bold text-[12px]">
                  {feaResults.maxDisplacementMm.toFixed(3)} mm
                </span>
              </div>
              <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <span className="text-text-muted text-[9px] block">1ª Frec. Propia:</span>
                <span className="text-text-primary font-bold text-[12px]">
                  {feaResults.modalFreqHz !== undefined ? `${feaResults.modalFreqHz} Hz` : '—'}
                </span>
              </div>
              <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <span className="text-text-muted text-[9px] block">Energía Deformación:</span>
                <span className="text-text-primary font-bold text-[12px]">
                  {feaResults.strainEnergyJ.toFixed(2)} J
                </span>
              </div>
            </div>

            {/* Deformation multiplier slider */}
            <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30 flex flex-col gap-1 font-mono text-[10px]">
              <div className="flex justify-between items-center">
                <span className="text-text-muted">Escala de Deformación FEA:</span>
                <span className="text-secondary font-bold">{deformationScale}x</span>
              </div>
              <input
                type="range"
                min="1"
                max="20"
                step="1"
                value={deformationScale}
                onChange={(e) => onChangeDeformationScale(parseInt(e.target.value, 10))}
                className="w-full h-1 bg-surface-container-lowest rounded-full appearance-none cursor-pointer accent-secondary"
              />
            </div>

            {/* Action to Export PDF report */}
            <button
              id="export-fea-report-btn"
              type="button"
              onClick={onExportReport}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-surface-elevated hover:bg-surface-container-high border border-border-subtle hover:border-secondary/40 text-text-primary hover:text-secondary font-semibold text-[12px] transition-all shadow-md active:scale-95"
            >
              <span className="material-symbols-outlined text-[16px] text-secondary">description</span>
              <span>Generar Informe Técnico FEA</span>
            </button>
          </div>
        </section>
      )}
    </aside>
  );
};
