import React, { useState, useEffect, useRef } from 'react';
import { SimpConfig } from '../../types';
import { backend } from '../../lib/bridge';
import { useJobPoll } from '../../lib/jobs';
import { ViewCube } from '../ViewCube';
import { MeshViewer, MeshViewerHandle, PreviewMesh, mapCubeFace } from '../MeshViewer';
import { readStoredNavProfile } from '../../lib/navigation';
import {
  Sliders,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  SkipBack,
  TrendingDown,
  Layers,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  Shield,
  Zap,
  Info,
} from 'lucide-react';

interface Screen4Props {
  onAdvanceToBRep: () => void;
  simpConfig: SimpConfig;
  onUpdateSimpConfig: (cfg: Partial<SimpConfig>) => void;
}

export const Screen4TopologyOptimization: React.FC<Screen4Props> = ({
  onAdvanceToBRep,
  simpConfig,
  onUpdateSimpConfig,
}) => {
  const [currentIter, setCurrentIter] = useState<number>(42);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isoThreshold, setIsoThreshold] = useState<number>(0.5);
  const [viewMode, setViewMode] = useState<'density' | 'iso' | 'stress'>('density');
  const [jobId, setJobId] = useState<string | null>(null);
  const [optBusy, setOptBusy] = useState<boolean>(false);
  const [optError, setOptError] = useState<string | null>(null);
  const [optResult, setOptResult] = useState<Record<string, unknown> | null>(null);
  const [previewMesh, setPreviewMesh] = useState<PreviewMesh | null>(null);
  const [meshError, setMeshError] = useState<string | null>(null);
  const [meshLoading, setMeshLoading] = useState<boolean>(false);
  const [densityValues, setDensityValues] = useState<number[] | null>(null);
  const [densityMin, setDensityMin] = useState<number | undefined>(undefined);
  const [densityMax, setDensityMax] = useState<number | undefined>(undefined);
  const [densityError, setDensityError] = useState<string | null>(null);
  const [densityLoading, setDensityLoading] = useState<boolean>(false);
  const viewerRef = useRef<MeshViewerHandle>(null);
  const [navProfile] = useState(() => readStoredNavProfile());
  const poll = useJobPoll(jobId, (res) => {
    if (res && typeof res === 'object') setOptResult(res as Record<string, unknown>);
  });

  const loadMeshPreview = async () => {
    setMeshLoading(true);
    setMeshError(null);
    try {
      const r = (await backend.getMeshPreview()) as {
        ok: boolean;
        mesh?: PreviewMesh;
        error?: string;
      };
      if (!r.ok) {
        setMeshError(r.error ?? 'getMeshPreview devolvió ok=false (¿sin STEP importado?)');
        setPreviewMesh(null);
      } else {
        setPreviewMesh(r.mesh ?? null);
      }
    } catch (e) {
      setMeshError(e instanceof Error ? e.message : String(e));
      setPreviewMesh(null);
    } finally {
      setMeshLoading(false);
    }
  };

  useEffect(() => {
    void loadMeshPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function unwrap(arr: unknown): number[] | null {
    if (arr == null) return null;
    if (Array.isArray(arr)) return arr as number[];
    if (typeof arr === 'object') {
      const o = arr as { __ndarray__?: boolean; data?: unknown };
      if (o.__ndarray__ && Array.isArray(o.data)) return o.data as number[];
      if (Array.isArray(o.data)) return o.data as number[];
    }
    return null;
  }

  const loadDensityField = async () => {
    setDensityError(null);
    if (!backend.hasBridge()) return; // mocks: vacío elegante
    const api = window.pywebview?.api as unknown as
      | { getSurfaceMesh?: (paramsJson: string) => Promise<unknown> }
      | undefined;
    if (!api?.getSurfaceMesh) return;
    setDensityLoading(true);
    try {
      const r = (await api.getSurfaceMesh(JSON.stringify({ field: 'density' }))) as {
        ok: boolean;
        positions?: unknown;
        indices?: unknown;
        values?: unknown;
        min?: number;
        max?: number;
        error?: string;
      };
      if (!r?.ok) {
        setDensityError(r?.error ?? 'getSurfaceMesh(density) devolvió ok=false');
        setDensityValues(null);
        return;
      }
      const pos = unwrap(r.positions);
      const idx = unwrap(r.indices);
      const vals = unwrap(r.values);
      if (pos && idx && pos.length > 0 && idx.length > 0) {
        setPreviewMesh((prev) => ({
          vertices: pos,
          indices: idx.map((v) => Math.round(v)),
          normals: null,
          bbox: prev?.bbox ?? null,
          num_vertices: Math.floor(pos.length / 3),
          num_triangles: Math.floor(idx.length / 3),
        }));
      }
      setDensityValues(vals);
      setDensityMin(typeof r.min === 'number' ? r.min : undefined);
      setDensityMax(typeof r.max === 'number' ? r.max : undefined);
    } catch (e) {
      setDensityError(e instanceof Error ? e.message : String(e));
      setDensityValues(null);
    } finally {
      setDensityLoading(false);
    }
  };

  const simpDone = !!optResult || poll.state === 'done';
  useEffect(() => {
    if (simpDone) void loadDensityField();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [simpDone]);

  const handleViewChange = (face: string) => {
    const dir = mapCubeFace(face);
    if (dir === 'reset') viewerRef.current?.reset();
    else viewerRef.current?.setView(dir);
  };

  const handleRunOptimization = async () => {
    setOptError(null);
    if (!backend.hasBridge()) return; // conserva simulación demo
    setOptBusy(true);
    try {
      const r = (await backend.runOptimization({
        volume_fraction: simpConfig.targetVolumeFraction,
        max_iterations: simpConfig.maxIterations,
      })) as { ok: boolean; jobId?: string; error?: string };
      if (!r.ok || !r.jobId) {
        setOptError(r.error ?? 'runOptimization devolvió ok=false');
        setOptBusy(false);
        return;
      }
      setJobId(r.jobId);
    } catch (e) {
      setOptError(e instanceof Error ? e.message : String(e));
    } finally {
      setOptBusy(false);
    }
  };

  const numOf = (v: unknown): number | null => (typeof v === 'number' ? v : null);
  const realCompliance = optResult ? numOf(optResult.compliance ?? optResult.currentCompliance) : null;
  const realMass = optResult ? numOf(optResult.finalMassKg ?? optResult.mass_kg ?? optResult.mass) : null;

  // Simulation play loop
  useEffect(() => {
    let timer: any = null;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentIter((prev) => {
          if (prev >= simpConfig.maxIterations) {
            setIsPlaying(false);
            return simpConfig.maxIterations;
          }
          return prev + 1;
        });
      }, 120);
    } else {
      clearInterval(timer);
    }
    return () => clearInterval(timer);
  }, [isPlaying, simpConfig.maxIterations]);

  // Compute interpolated compliance and volume based on iteration
  const progressRatio = Math.min(1, currentIter / simpConfig.maxIterations);
  const currentVolumeFraction = 1.0 - (1.0 - simpConfig.targetVolumeFraction) * Math.min(1, currentIter / 25);
  const currentCompliance = 48.2 - 32.6 * Math.min(1, Math.sqrt(progressRatio));
  const currentMassKg = (3.42 * currentVolumeFraction).toFixed(2);
  const massReductionPct = ((1 - currentVolumeFraction) * 100).toFixed(1);

  return (
    <div className="w-full flex flex-col gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* Subheader Breadcrumb & Operational Mode Status Strip */}
      <div className="w-full bg-[#181b24] px-3 py-1.5 rounded flex flex-wrap items-center justify-between gap-2 border border-[#2e3646]/60">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">ETAPA:</span>
            <span className="font-label-sm text-[11px] text-[#f1f5f9] font-medium uppercase tracking-wide">
              4. OPTIMIZACIÓN TOPOLÓGICA SIMP
            </span>
          </div>
          <span className="w-1 h-1 rounded-full bg-[#2e3646]"></span>
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">PENALIZACIÓN:</span>
            <span className="font-label-sm text-[11px] text-[#ffb95f]">p = {simpConfig.penaltyExponent.toFixed(1)} (SIMP)</span>
          </div>
          <span className="w-1 h-1 rounded-full bg-[#2e3646]"></span>
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">FILTRO PDE:</span>
            <span className="font-label-sm text-[11px] text-[#7bd0ff]">Helmholtz (r = {simpConfig.filterRadiusMm.toFixed(1)} mm)</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-label-sm text-[11px] text-[#10b981] flex items-center gap-1.5 font-medium">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
            Iteración {currentIter}/{simpConfig.maxIterations} · ΔC: 0.0004
          </span>
          <button
            onClick={handleRunOptimization}
            disabled={optBusy || poll.loading}
            className="bg-[#0ea5e9] hover:bg-[#7bd0ff] px-2.5 py-1 rounded flex items-center gap-1 text-[#003751] font-label-sm text-[10px] font-bold disabled:opacity-60"
          >
            <span>{optBusy || poll.loading ? 'Optimizando...' : 'Lanzar optimización (backend)'}</span>
          </button>
          <button
            onClick={() => {
              setCurrentIter(1);
              setIsPlaying(true);
            }}
            className="bg-[#1f2430] hover:bg-[#272a33] px-2.5 py-1 rounded flex items-center gap-1 text-[#f1f5f9] border border-[#2e3646] hover:text-[#7bd0ff] transition-colors font-label-sm text-[10px]"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reiniciar SIMP</span>
          </button>
        </div>
      </div>

      {/* Main 3-Pane Layout */}
      <div className="grid grid-cols-12 gap-2 flex-1">
        {/* LEFT PANEL: SIMP Hyperparameters & Boundary Filters */}
        <aside className="col-span-12 xl:col-span-3 flex flex-col gap-2">
          {/* Card: Parameters */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2.5 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-[#ffb95f]" />
                <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Parámetros SIMP</span>
              </div>
              <span className="px-1.5 py-0.5 rounded bg-[#ffb95f]/15 text-[#ffb95f] font-label-sm text-[10px]">
                Active Solver
              </span>
            </div>

            {/* Slider 1: Exponente de Penalización (p) */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between font-label-sm text-[10px]">
                <span className="text-[#94a3b8]">Exponente Penalización (p):</span>
                <span className="text-[#ffb95f] font-bold font-mono">{simpConfig.penaltyExponent.toFixed(1)}</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="5.0"
                step="0.1"
                value={simpConfig.penaltyExponent}
                onChange={(e) => onUpdateSimpConfig({ penaltyExponent: parseFloat(e.target.value) })}
                className="w-full h-1.5 bg-[#32343e] rounded cursor-pointer accent-[#ffb95f]"
              />
              <span className="text-[9px] font-label-sm text-[#64748b]">
                p = 3.0 penaliza densidades intermedias hacia 0 (hueco) o 1 (sólido).
              </span>
            </div>

            {/* Slider 2: Fracción de Volumen Objetivo (V_f) */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between font-label-sm text-[10px]">
                <span className="text-[#94a3b8]">Fracción de Volumen (V_f):</span>
                <span className="text-[#7bd0ff] font-bold font-mono">
                  {(simpConfig.targetVolumeFraction * 100).toFixed(0)}%
                </span>
              </div>
              <input
                type="range"
                min="0.15"
                max="0.70"
                step="0.05"
                value={simpConfig.targetVolumeFraction}
                onChange={(e) => onUpdateSimpConfig({ targetVolumeFraction: parseFloat(e.target.value) })}
                className="w-full h-1.5 bg-[#32343e] rounded cursor-pointer accent-[#0ea5e9]"
              />
              <span className="text-[9px] font-label-sm text-[#64748b]">
                Volumen final deseado respecto al espacio de diseño original.
              </span>
            </div>

            {/* Slider 3: Radio de Filtro Helmholtz (r_min) */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between font-label-sm text-[10px]">
                <span className="text-[#94a3b8]">Radio de Filtro (r_min):</span>
                <span className="text-[#10b981] font-bold font-mono">{simpConfig.filterRadiusMm.toFixed(1)} mm</span>
              </div>
              <input
                type="range"
                min="2.0"
                max="12.0"
                step="0.5"
                value={simpConfig.filterRadiusMm}
                onChange={(e) => onUpdateSimpConfig({ filterRadiusMm: parseFloat(e.target.value) })}
                className="w-full h-1.5 bg-[#32343e] rounded cursor-pointer accent-[#10b981]"
              />
              <span className="text-[9px] font-label-sm text-[#64748b]">
                Evita efecto ajedrez y garantiza espesor mínimo de miembros estructurales.
              </span>
            </div>

            {/* Optimizer algorithm dropdown */}
            <div className="flex flex-col gap-1 pt-1 border-t border-[#2e3646]/50">
              <label className="font-label-sm text-[10px] text-[#64748b]">Algoritmo de Actualización:</label>
              <select
                value={simpConfig.algorithm}
                onChange={(e) => onUpdateSimpConfig({ algorithm: e.target.value as any })}
                className="w-full bg-[#1f2430] border border-[#2e3646] rounded px-2 py-1 text-[11px] text-[#f1f5f9] focus:outline-none"
              >
                <option value="OC">Criterios de Optimalidad (OC - Rápido)</option>
                <option value="MMA">Method of Moving Asymptotes (MMA - Restricciones Múltiples)</option>
              </select>
            </div>
          </section>

          {/* Non-design preserved spaces */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 border border-[#2e3646]/50">
            <span className="font-headline-sm text-[12px] text-[#f1f5f9]">Regiones No de Diseño (Frozen)</span>
            <div className="flex flex-col gap-1.5 text-[10px] font-label-sm">
              <div className="p-2 rounded bg-[#1f2430] border border-[#10b981]/30 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-[#10b981]" />
                  <span className="text-[#f1f5f9]">Bujes de Anclaje (3 Perforaciones)</span>
                </div>
                <span className="text-[#10b981] font-bold">ρ = 1.0 (Fijo)</span>
              </div>
              <div className="p-2 rounded bg-[#1f2430] border border-[#10b981]/30 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-[#10b981]" />
                  <span className="text-[#f1f5f9]">Zona de Aplicación de Carga</span>
                </div>
                <span className="text-[#10b981] font-bold">ρ = 1.0 (Fijo)</span>
              </div>
            </div>
          </section>

          {/* Additive Manufacturing Overhang Constraint */}
          <div className="bg-[#181b24]/80 rounded-lg p-2 flex items-center justify-between text-[10px] font-label-sm text-[#94a3b8] border border-[#2e3646]/40">
            <span className="flex items-center gap-1 text-[#bec8d2]">
              <Zap className="w-3.5 h-3.5 text-[#ffb95f]" />
              Ángulo Sobrevuelo Máx:
            </span>
            <span className="text-[#10b981] font-bold font-mono">45.0° (Imprimible SLM)</span>
          </div>
        </aside>

        {/* CENTRAL AREA: 3D Topology Density & Isosurface Viewport */}
        <main className="col-span-12 xl:col-span-6 flex flex-col gap-2">
          <div className="relative w-full h-[620px] rounded-lg bg-[#0b0e17] overflow-hidden shadow-2xl flex flex-col justify-between p-2 select-none border border-[#2e3646]">
            {/* Top Toolbar: Iteration Scrubber & Density Threshold */}
            <div className="w-full flex items-center justify-between z-20 pointer-events-auto">
              {/* Playback Controls */}
              <div className="flex items-center gap-1.5 bg-[#181b24]/90 backdrop-blur-md px-2 py-1 rounded-lg shadow-md border border-[#2e3646]/60">
                <button
                  onClick={() => setCurrentIter((prev) => Math.max(1, prev - 1))}
                  className="p-1 rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9]"
                  title="Iteración Anterior"
                >
                  <SkipBack className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className={`p-1.5 rounded transition-colors ${
                    isPlaying ? 'bg-[#10b981] text-[#0b0e17]' : 'bg-[#0ea5e9] text-[#003751]'
                  }`}
                  title={isPlaying ? 'Pausar Optimización' : 'Ejecutar Iteraciones'}
                >
                  {isPlaying ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                </button>
                <button
                  onClick={() => setCurrentIter((prev) => Math.min(simpConfig.maxIterations, prev + 1))}
                  className="p-1 rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9]"
                  title="Siguiente Iteración"
                >
                  <SkipForward className="w-3.5 h-3.5" />
                </button>

                <div className="w-px h-3.5 bg-[#2e3646] mx-1"></div>

                <span className="font-label-sm text-[11px] text-[#f1f5f9] font-mono min-w-[70px]">
                  Iter: <strong>{currentIter}</strong>/{simpConfig.maxIterations}
                </span>

                <input
                  type="range"
                  min="1"
                  max={simpConfig.maxIterations}
                  value={currentIter}
                  onChange={(e) => {
                    setIsPlaying(false);
                    setCurrentIter(parseInt(e.target.value));
                  }}
                  className="w-24 h-1.5 bg-[#32343e] rounded cursor-pointer accent-[#0ea5e9]"
                />
              </div>

              {/* View Modes */}
              <div className="flex items-center gap-1 bg-[#181b24]/90 backdrop-blur-md p-1 rounded-lg shadow-md border border-[#2e3646]/60">
                <button
                  onClick={() => setViewMode('density')}
                  className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                    viewMode === 'density' ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                >
                  Densidad Continua
                </button>
                <button
                  onClick={() => setViewMode('iso')}
                  className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                    viewMode === 'iso' ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                >
                  Isosuperficie (ρ &gt; {isoThreshold.toFixed(2)})
                </button>
              </div>
            </div>

            {/* 3D Real Viewport (three.js) — malla actual */}
            <div className="absolute inset-0 z-0 flex flex-col items-center justify-center overflow-hidden px-2 pt-14 pb-16">
              <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#2e3646_1px,transparent_1px)] [background-size:24px_24px]"></div>
              <div className="relative w-full max-w-[560px] flex flex-col gap-1">
                {meshError && (
                  <div className="text-[10px] text-[#fca5a5] bg-[#ef4444]/10 border border-[#ef4444]/30 rounded px-2 py-1">
                    Error: {meshError}
                  </div>
                )}
                <div className="rounded-lg overflow-hidden border border-[#2e3646]/60 bg-[#0f1117]">
                  <MeshViewer ref={viewerRef} mesh={previewMesh} wireframe={viewMode === "iso"} color="#3b82f6" height={320} profile={navProfile}
                    values={viewMode === 'density' ? densityValues : null}
                    colorMin={densityMin} colorMax={densityMax}
                    colorbarLabel="Densidad SIMP ρ (0=vacío, 1=sólido)" />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] text-[#64748b]">
                    {densityLoading ? 'Cargando densidades SIMP…' : densityError ? `Densidades no disponibles: ${densityError}` : densityValues ? `Densidad ρ en rango [${densityMin?.toFixed(2) ?? '…'}, ${densityMax?.toFixed(2) ?? '…'}] — 0=vacío, 1=sólido.` : 'Malla actual del backend. Ejecuta SIMP para ver densidades.'}
                  </p>
                  <button onClick={() => void loadMeshPreview()} disabled={meshLoading} className="shrink-0 px-2 py-1 rounded bg-[#1f2430] hover:bg-[#272a33] text-[#94a3b8] hover:text-[#7bd0ff] font-label-sm text-[10px] border border-[#2e3646]/50 disabled:opacity-60" type="button">
                    {meshLoading ? "Cargando..." : "Cargar malla"}
                  </button>
                </div>
              </div>
            </div>

            {/* ViewCube Top Right */}
            <div className="absolute top-14 right-2 z-20">
              <ViewCube onViewChange={handleViewChange} />
            </div>

            {/* Floating Colorbar Legend: Relative Density */}
            <div className="absolute left-2 top-14 bottom-14 z-20 w-32 bg-[#181b24]/90 backdrop-blur-md rounded-lg p-2 shadow-xl flex flex-col justify-between border border-[#2e3646]/60">
              <div className="flex flex-col gap-0.5">
                <span className="font-headline-sm text-[11px] text-[#f1f5f9]">Densidad ρ_e</span>
                <span className="font-label-sm text-[9px] text-[#64748b]">Filtro SIMP Penalizado</span>
              </div>

              <div className="flex items-stretch gap-2 h-full my-1.5">
                <div className="w-3.5 h-full rounded-sm relative overflow-hidden bg-gradient-to-b from-[#0f172a] via-[#3b82f6] to-[#0ea5e9] shadow-inner">
                  {/* Threshold mark */}
                  <div
                    className="absolute left-0 right-0 h-0.5 bg-[#f59e0b]"
                    style={{ bottom: `${isoThreshold * 100}%` }}
                  ></div>
                </div>

                <div className="flex flex-col justify-between font-label-sm text-[9px] text-[#94a3b8] h-full py-0.5">
                  <span className="text-[#f1f5f9] font-bold">1.0 Sólido</span>
                  <span>0.75</span>
                  <span className="text-[#f59e0b]">Iso: {isoThreshold.toFixed(2)}</span>
                  <span>0.25</span>
                  <span className="text-[#64748b]">0.0 Vacío</span>
                </div>
              </div>

              <div className="flex flex-col gap-0.5">
                <span className="font-label-sm text-[9px] text-[#64748b]">Corte Isosuperficie:</span>
                <input
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                  value={isoThreshold}
                  onChange={(e) => setIsoThreshold(parseFloat(e.target.value))}
                  className="w-full h-1 bg-[#32343e] rounded cursor-pointer accent-[#f59e0b]"
                />
              </div>
            </div>

            {/* Bottom Viewport Telemetry Bar */}
            <div className="w-full flex items-center justify-between bg-[#181b24]/95 backdrop-blur-md p-2 rounded-lg shadow-lg z-20 pointer-events-auto border border-[#2e3646]/60 font-label-sm text-[10px]">
              <div className="flex items-center gap-3">
                <span className="text-[#64748b]">Volumen Actual:</span>
                <span className="text-[#7bd0ff] font-bold font-mono">
                  {(currentVolumeFraction * 100).toFixed(1)}% ({currentMassKg} kg)
                </span>
                <span className="text-[#64748b]">|</span>
                <span className="text-[#64748b]">Compliance:</span>
                <span className="text-[#f1f5f9] font-bold font-mono">{realCompliance !== null ? `${realCompliance.toFixed(2)} J (real)` : `${currentCompliance.toFixed(2)} J`}</span>
              </div>
              {(optError || poll.error || poll.loading || optResult) && (
                <div className={`w-full rounded px-2 py-1 text-[10px] border ${optError || poll.error ? 'text-[#fca5a5] bg-[#ef4444]/10 border-[#ef4444]/30' : 'text-[#7bd0ff] bg-[#0ea5e9]/10 border-[#0ea5e9]/30'}`}>
                  {optError ?? poll.error ?? (poll.loading ? `Optimizando... estado=${poll.state ?? '?'} progreso=${poll.progress ?? '?'}` : `Resultado real: ${JSON.stringify(optResult)}${realMass !== null ? ` · masa=${realMass.toFixed(2)} kg` : ''}`)}
                </div>
              )}
              <div className="flex items-center gap-1 text-[#10b981]">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Convergencia Estable (ΔC &lt; 10⁻⁴)</span>
              </div>
            </div>
          </div>
        </main>

        {/* RIGHT PANEL: Convergence History Curves & B-Rep Advance */}
        <aside className="col-span-12 xl:col-span-3 flex flex-col gap-2">
          {/* Convergence History Dual Curve */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <TrendingDown className="w-4 h-4 text-[#7bd0ff]" />
                <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Historial de Convergencia</span>
              </div>
              <span className="font-label-sm text-[10px] text-[#64748b]">50 Iters</span>
            </div>

            {/* SVG Convergence Dual Chart */}
            <div className="w-full bg-[#0b0e17] rounded p-2 flex flex-col gap-1 border border-[#2e3646]/40">
              <div className="h-32 w-full relative">
                <svg className="w-full h-full overflow-visible" viewBox="0 0 280 120" preserveAspectRatio="none">
                  {/* Grid */}
                  <line x1="0" y1="20" x2="280" y2="20" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="1" />
                  <line x1="0" y1="60" x2="280" y2="60" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="1" />
                  <line x1="0" y1="100" x2="280" y2="100" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="1" />

                  {/* Volume Fraction Curve (Dashed Blue) */}
                  <path
                    d="M 10,20 L 70,60 L 140,85 L 210,85 L 270,85"
                    fill="none"
                    stroke="#0ea5e9"
                    strokeWidth="1.8"
                    strokeDasharray="3 2"
                  />

                  {/* Compliance Objective Curve (Solid Orange) */}
                  <path
                    d="M 10,15 L 70,35 L 140,65 L 210,80 L 270,90"
                    fill="none"
                    stroke="#ffb95f"
                    strokeWidth="2.2"
                  />

                  {/* Current point */}
                  <circle cx="235" cy="87" r="3.5" fill="#10b981" />
                </svg>
              </div>

              <div className="flex items-center justify-between font-label-sm text-[9px] pt-1">
                <span className="flex items-center gap-1 text-[#ffb95f]">
                  <span className="w-2 h-0.5 bg-[#ffb95f]"></span>
                  Compliance C(ρ)
                </span>
                <span className="flex items-center gap-1 text-[#0ea5e9]">
                  <span className="w-2 h-0.5 bg-[#0ea5e9] border-b border-dashed"></span>
                  Volumen V(ρ)/V₀
                </span>
              </div>
            </div>
          </section>

          {/* Mass & Structural Efficiency */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 border border-[#2e3646]/50">
            <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Eficiencia Estructural</span>
            <div className="grid grid-cols-2 gap-1.5 font-label-sm text-[10px]">
              <div className="bg-[#1f2430] p-2 rounded flex flex-col">
                <span className="text-[#64748b]">Ahorro de Peso:</span>
                <span className="font-label-lg text-[14px] text-[#10b981] font-bold mt-0.5">-{massReductionPct}%</span>
                <span className="text-[9px] text-[#64748b] mt-0.5">3.42 kg → {currentMassKg} kg</span>
              </div>

              <div className="bg-[#1f2430] p-2 rounded flex flex-col">
                <span className="text-[#64748b]">Rigidez Específica:</span>
                <span className="font-label-lg text-[14px] text-[#7bd0ff] font-bold mt-0.5">+152%</span>
                <span className="text-[9px] text-[#64748b] mt-0.5">E/ρ optimizado</span>
              </div>
            </div>
          </section>

          {/* Call To Action: Advance to B-Rep CAD Reconstruction */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 mt-auto border border-[#2e3646]">
            <div className="flex items-center gap-1.5 text-[#10b981] font-label-sm text-[10px]">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Convergencia SIMP Alcanzada</span>
            </div>
            <p className="text-[#94a3b8] font-body-sm text-[10px] leading-tight">
              Los campos de densidad celular están listos para Marching Tetrahedra, ajuste NURBS y costura hermética B-Rep.
            </p>

            <button
              onClick={onAdvanceToBRep}
              className="w-full py-2.5 px-3 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-headline-sm text-[12px] rounded-lg shadow-lg flex items-center justify-center gap-2 transition-all font-semibold transform hover:-translate-y-0.5"
              type="button"
            >
              <Sparkles className="w-4 h-4" />
              <span>Reconstruir B-Rep NURBS & Exportar</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </section>
        </aside>
      </div>
    </div>
  );
};
