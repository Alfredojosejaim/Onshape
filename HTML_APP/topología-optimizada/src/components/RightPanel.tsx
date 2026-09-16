import React from 'react';
import { Material, SimpParameters, OptimizationState, OptimizationType, ActiveTab, FeaResults, MeshOpResult } from '../types';
// FASE3-START (reversible): FoS + comparativa. Para volver atrás: quitar
// imports + usos <SafetyCard/> y <CompareTable/>.
import { SafetyCard } from './SafetyCard';
import { CompareTable } from './CompareTable';
// FASE3-END
// MALLA-TOOLS-START (reversible): resultados de malla (solo lectura;
// las herramientas viven en la barra). Para volver atras: quitar import +
// rama 'malla' + props.
import { MeshResultsPanel } from './MeshResultsPanel';
// MALLA-TOOLS-END
// ADV-OPT-START (reversible): motores y restricciones avanzadas. Para volver
// atrás: quitar import + render <AdvancedOptPanel/>.
import { AdvancedOptPanel } from './AdvancedOptPanel';
// ADV-OPT-END

interface RightPanelProps {
  activeTab: ActiveTab;
  materials: Material[];
  selectedMaterial: Material;
  onSelectMaterial: (m: Material) => void;
  simpParams: SimpParameters;
  onChangeSimpParams: (params: SimpParameters) => void;
  // OPT-TYPE (reversible): estructural (SIMP) vs generativa (escenario A).
  optType: OptimizationType;
  onChangeOptType: (t: OptimizationType) => void;
  optimizationState: OptimizationState;
  onStartOptimization: () => void;
  onPauseOptimization: () => void;
  onResetOptimization: () => void;
  feaResults: FeaResults;
  deformationScale: number;
  onChangeDeformationScale: (scale: number) => void;
  onExportReport: () => void;
  // MALLA-TOOLS (reversible): resultado publicado (solo lectura).
  isMeshModel?: boolean;
  meshFormat?: string | null;
  meshResult?: MeshOpResult | null;
  // DENSITY-VIEW (reversible): toggle + leyenda del overlay SIMP.
  densityAvailable?: boolean;
  densityMin?: number | null;
  densityMax?: number | null;
  showDensity?: boolean;
  onToggleDensity?: () => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({
  activeTab,
  materials,
  selectedMaterial,
  onSelectMaterial,
  simpParams,
  onChangeSimpParams,
  optType,
  onChangeOptType,
  optimizationState,
  onStartOptimization,
  onPauseOptimization,
  onResetOptimization,
  feaResults,
  deformationScale,
  onChangeDeformationScale,
  onExportReport,
  isMeshModel,
  meshFormat,
  meshResult,
  densityAvailable,
  densityMin,
  densityMax,
  showDensity,
  onToggleDensity,
}) => {
  return (
    <aside className="w-full xl:w-80 2xl:w-88 flex flex-col gap-2 flex-shrink-0 min-w-0 select-none xl:sticky xl:top-[154px] xl:max-h-[calc(100dvh-154px-3rem)] xl:overflow-y-auto xl:[&>*]:shrink-0">
      {/* RIGHT-ADAPTIVE (reversible): mismo anclaje que LeftPanel (sticky +
          alto capado a 100dvh con margen inferior 3rem = misma distancia al
          borde que el rail de herramientas) + scroll interno en pantallas
          cortas; hijos sin shrink para que desplace en vez de comprimir.
          Para volver atras: aside "w-full xl:w-80 2xl:w-88 flex flex-col gap-space-sm flex-shrink-0 select-none". */}
      {/* Material Library Card (compacta: p-2/gap-1.5/filas py-0.5) */}
      <section className="bg-surface-container-low rounded-lg p-2 shadow-md flex flex-col gap-1.5 border border-border-subtle/40">
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
          <div className="flex items-center justify-between py-0.5 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Módulo Young (E):</span>
            <span className="text-text-primary font-bold">{selectedMaterial.youngModulus.toFixed(1)} GPa</span>
          </div>
          <div className="flex items-center justify-between py-0.5 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Coef. Poisson (ν):</span>
            <span className="text-text-primary font-bold">{selectedMaterial.poissonRatio.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between py-0.5 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Límite Elástico (σ_y):</span>
            <span className="text-fea-stress-yield font-bold">{selectedMaterial.yieldStrength.toFixed(1)} MPa</span>
          </div>
          <div className="flex items-center justify-between py-0.5 px-2 bg-surface-elevated/50 rounded">
            <span className="text-text-muted text-[11px]">Densidad (ρ):</span>
            <span className="text-text-primary font-bold">{selectedMaterial.density.toFixed(2)} g/cm³</span>
          </div>
          <div className="flex items-center justify-between py-0.5 px-2 bg-surface-elevated/50 rounded">
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
        /* CAE Study Metrics & SIMP Optimization Parameters (compacto p-2) */
        <section className="bg-surface-container-low rounded-lg p-2 shadow-md flex flex-col gap-2 border border-border-subtle/50">
          <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated rounded border border-border-subtle/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-secondary text-[16px]">tune</span>
              <span className="font-semibold text-[12px] text-text-primary">Parámetros de Optimización</span>
            </div>
            <span className="px-1.5 py-0.5 rounded bg-secondary/10 border border-secondary/30 text-secondary font-mono text-[10px] font-semibold tracking-wider">
              {optType === 'estructural' ? 'SIMP' : 'GEN-A'}
            </span>
          </header>

          <div className="flex flex-col gap-2 text-[11px]">
            {/* OPT-TYPE (reversible): estructural vs generativa. */}
            <div className="flex items-center gap-1 min-w-0" role="group" aria-label="Tipo de optimización">
              {(['estructural', 'generativa'] as OptimizationType[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  title={t === 'estructural' ? 'Optimización estructural SIMP' : 'Optimización generativa (escenario A: pieza existente)'}
                  onClick={() => onChangeOptType(t)}
                  disabled={optimizationState.isRunning}
                  className={`flex-1 min-w-0 truncate px-1.5 py-1 rounded text-[10px] font-semibold transition-colors disabled:opacity-50 ${
                    optType === t
                      ? 'bg-secondary/15 text-secondary ring-1 ring-secondary/30'
                      : 'text-text-secondary hover:bg-surface-elevated hover:text-text-primary'
                  }`}
                >
                  {t === 'estructural' ? 'Estructural' : 'Generativa'}
                </button>
              ))}
              <span className="shrink-0 px-1.5 py-0.5 rounded bg-secondary/10 border border-secondary/30 text-secondary font-mono text-[10px] font-semibold tracking-wider">
                {optType === 'estructural' ? 'SIMP' : 'GEN-A'}
              </span>
            </div>
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

            {/* Geometría limpia: Heaviside + extrusión 2D + B-spline STEP */}
            <div className="flex flex-col gap-1 bg-surface-elevated/20 p-2 rounded border border-border-subtle/30 font-mono text-[10px]">
              <span className="text-text-muted font-medium flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px] text-secondary">shape_line</span>
                Geometría limpia (bordes nítidos)
              </span>
              <label className="flex items-center justify-between pl-2">
                <span className="text-text-secondary" title="Generativa: optimizar la pieza (solo vacía) o una caja de diseño (crece estructura orgánica)">Design space</span>
                <select
                  value={simpParams.designSpace}
                  disabled={optimizationState.isRunning}
                  onChange={(e) => onChangeSimpParams({ ...simpParams, designSpace: e.target.value as SimpParameters['designSpace'] })}
                  className="bg-surface-container-lowest border border-border-subtle/40 rounded px-1 py-0.5 text-text-primary"
                >
                  <option value="part">Pieza</option>
                  <option value="envelope">Envelope</option>
                </select>
              </label>
              <label className="flex items-center justify-between pl-2 cursor-pointer">
                <span className="text-text-secondary">Proyección Heaviside</span>
                <input
                  type="checkbox"
                  checked={simpParams.heaviside}
                  disabled={optimizationState.isRunning}
                  onChange={(e) => onChangeSimpParams({ ...simpParams, heaviside: e.target.checked })}
                  className="accent-secondary"
                />
              </label>
              <label className="flex items-center justify-between pl-2">
                <span className="text-text-secondary">Beta (agudeza)</span>
                <input
                  type="number"
                  min={1}
                  max={128}
                  step={1}
                  value={simpParams.heavisideBeta}
                  disabled={optimizationState.isRunning || !simpParams.heaviside}
                  onChange={(e) => onChangeSimpParams({ ...simpParams, heavisideBeta: parseFloat(e.target.value) || 1 })}
                  className="w-16 bg-surface-container-lowest border border-border-subtle/40 rounded px-1 py-0.5 text-text-primary text-right"
                />
              </label>
              <label className="flex items-center justify-between pl-2">
                <span className="text-text-secondary" title="Densidad constante a lo largo del eje (pieza 2.5D)">Extrusión 2D</span>
                <select
                  value={simpParams.extrusionAxis}
                  disabled={optimizationState.isRunning}
                  onChange={(e) => onChangeSimpParams({ ...simpParams, extrusionAxis: e.target.value as SimpParameters['extrusionAxis'] })}
                  className="bg-surface-container-lowest border border-border-subtle/40 rounded px-1 py-0.5 text-text-primary"
                >
                  <option value="off">Off</option>
                  <option value="x">X</option>
                  <option value="y">Y</option>
                  <option value="z">Z</option>
                </select>
              </label>
              <label className="flex items-center justify-between pl-2">
                <span className="text-text-secondary" title="STEP facetado (malla) vs B-spline (caras suaves)">Reconstrucción STEP</span>
                <select
                  value={simpParams.brepStyle}
                  disabled={optimizationState.isRunning}
                  onChange={(e) => onChangeSimpParams({ ...simpParams, brepStyle: e.target.value as SimpParameters['brepStyle'] })}
                  className="bg-surface-container-lowest border border-border-subtle/40 rounded px-1 py-0.5 text-text-primary"
                >
                  <option value="faceted">Facetada</option>
                  <option value="bspline">B-spline</option>
                </select>
              </label>
            </div>

            {/* ADV-OPT (reversible): motores/restricciones del core. Para
                volver atrás: quitar bloque + import + tipos + spread. */}
            <AdvancedOptPanel
              simpParams={simpParams}
              onChangeSimpParams={onChangeSimpParams}
              disabled={optimizationState.isRunning}
            />

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

            {/* DENSITY-VIEW (reversible): overlay de densidades SIMP sobre
                la malla (solo visual, no modifica la pieza). Para volver
                atrás: borrar bloque + props. */}
            {densityAvailable && (
              <div className="flex flex-col gap-1.5 bg-surface-elevated/60 p-2.5 rounded border border-secondary/30">
                <button
                  type="button"
                  onClick={onToggleDensity}
                  className="flex items-center justify-between font-mono text-[11px] text-text-secondary hover:text-text-primary transition-colors"
                  title="Mostrar u ocultar el campo de densidades sobre la malla"
                >
                  <span>Campo de densidades ρ</span>
                  <span className={`material-symbols-outlined text-[16px] ${showDensity ? 'text-secondary' : 'text-text-muted'}`}>
                    {showDensity ? 'visibility' : 'visibility_off'}
                  </span>
                </button>
                <div
                  className="h-2 rounded-full"
                  style={{ background: 'linear-gradient(90deg, #1e3a8a, #f97316)' }}
                />
                <div className="flex items-center justify-between font-mono text-[10px] text-text-muted">
                  <span>vacío ρ = {densityMin?.toFixed(2) ?? '—'}</span>
                  <span>sólido ρ = {densityMax?.toFixed(2) ?? '—'}</span>
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
                      : optType === 'estructural' ? 'Iniciar Optimización SIMP' : 'Iniciar Diseño Generativo'}
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
      ) : activeTab === 'malla' ? (
        /* MALLA-TOOLS (reversible): pestana Malla — SOLO resultados. */
        <MeshResultsPanel
          isMeshModel={!!isMeshModel}
          meshFormat={meshFormat ?? null}
          result={meshResult ?? { report: null, op: null, stats: null, error: null }}
        />
      ) : (
        /* Analysis Mode Panel: Finite Element Analysis (FEA) Metrics (compacto p-2) */
        <section className="bg-surface-container-low rounded-lg p-2 shadow-md flex flex-col gap-2 border border-border-subtle/50">
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
                  {feaResults.maxVonMisesMpa !== null && feaResults.maxVonMisesMpa !== undefined ? `${feaResults.maxVonMisesMpa.toFixed(1)} MPa` : '—'}
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
                  {feaResults.minSafetyFactor !== null && feaResults.minSafetyFactor !== undefined ? `SF = ${feaResults.minSafetyFactor.toFixed(2)}` : 'SF = —'}
                </span>
              </div>
              <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <span className="text-text-muted text-[9px] block">Desplazamiento Máx:</span>
                <span className="text-secondary font-bold text-[12px]">
                  {feaResults.maxDisplacementMm !== null && feaResults.maxDisplacementMm !== undefined ? `${feaResults.maxDisplacementMm.toFixed(3)} mm` : '—'}
                </span>
              </div>
              <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <span className="text-text-muted text-[9px] block">1ª Frec. Propia:</span>
                <span className="text-text-primary font-bold text-[12px]">
                  {feaResults.modalFreqHz !== undefined && feaResults.modalFreqHz !== null ? `${feaResults.modalFreqHz} Hz` : '—'}
                </span>
              </div>
              <div className="bg-surface-elevated/40 p-2 rounded border border-border-subtle/30">
                <span className="text-text-muted text-[9px] block">Energía Deformación:</span>
                <span className="text-text-primary font-bold text-[12px]">
                  {feaResults.strainEnergyJ !== null && feaResults.strainEnergyJ !== undefined ? `${feaResults.strainEnergyJ.toFixed(2)} J` : '—'}
                </span>
              </div>
            </div>

            {/* FASE3 (reversible): FoS por elemento + zonas bajo umbral. */}
            <SafetyCard />

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
      {/* FASE3 (reversible): tabla comparativa A vs B (ambas pestañas). */}
      <CompareTable />
    </aside>
  );
};
