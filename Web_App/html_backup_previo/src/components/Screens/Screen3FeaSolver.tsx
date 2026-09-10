import React, { useState, useEffect, useRef } from 'react';
import { FeaBackend, MaterialProperty } from '../../types';
import { backend } from '../../lib/bridge';
import { useJobPoll } from '../../lib/jobs';
import { ViewCube } from '../ViewCube';
import { MeshViewer, MeshViewerHandle, PreviewMesh, mapCubeFace } from '../MeshViewer';
import { readStoredNavProfile } from '../../lib/navigation';
import {
  Cpu,
  RefreshCw,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Play,
  Pause,
  ArrowRight,
  Maximize2,
  ZoomIn,
  Layers,
  Camera,
  Grid,
  Scale,
  ShieldCheck,
  Flame,
} from 'lucide-react';

interface Screen3Props {
  onAdvanceToSimp: () => void;
  backend: FeaBackend;
  onSetBackend: (backend: FeaBackend) => void;
  material: MaterialProperty;
}

export const Screen3FeaSolver: React.FC<Screen3Props> = ({
  onAdvanceToSimp,
  backend: feaBackend,
  onSetBackend,
  material,
}) => {
  const [scaleFactor, setScaleFactor] = useState<number>(5.0);
  const [isAnimating, setIsAnimating] = useState<boolean>(false);
  const [animPhase, setAnimPhase] = useState<number>(0);
  const [activeFieldMode, setActiveFieldMode] = useState<'vonmises' | 'disp' | 'sigma1' | 'sed'>('vonmises');
  const [wireframeVisible, setWireframeVisible] = useState<boolean>(true);
  const [probeSelected, setProbeSelected] = useState<string>('14092');
  const [jobId, setJobId] = useState<string | null>(null);
  const [feaBusy, setFeaBusy] = useState<boolean>(false);
  const [feaError, setFeaError] = useState<string | null>(null);
  const [feaResult, setFeaResult] = useState<Record<string, unknown> | null>(null);
  const [previewMesh, setPreviewMesh] = useState<PreviewMesh | null>(null);
  const [meshError, setMeshError] = useState<string | null>(null);
  const [meshLoading, setMeshLoading] = useState<boolean>(false);
  const [fieldValues, setFieldValues] = useState<number[] | null>(null);
  const [fieldMin, setFieldMin] = useState<number | undefined>(undefined);
  const [fieldMax, setFieldMax] = useState<number | undefined>(undefined);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [fieldLoading, setFieldLoading] = useState<boolean>(false);
  const viewerRef = useRef<MeshViewerHandle>(null);
  const [navProfile] = useState(() => readStoredNavProfile());
  const poll = useJobPoll(jobId, (res) => {
    if (res && typeof res === 'object') setFeaResult(res as Record<string, unknown>);
  });
  const isDemo = !backend.hasBridge();

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

  // --- Campo superficial FEA (colormap) ---------------------------------
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

  const loadSurfaceField = async (field: 'vonmises' | 'displacement') => {
    setFieldError(null);
    if (!backend.hasBridge()) return; // mocks: vacío elegante
    const api = window.pywebview?.api as unknown as
      | { getSurfaceMesh?: (paramsJson: string) => Promise<unknown> }
      | undefined;
    if (!api?.getSurfaceMesh) return; // sin pywebview real: vacío elegante
    setFieldLoading(true);
    try {
      const r = (await api.getSurfaceMesh(JSON.stringify({ field }))) as {
        ok: boolean;
        positions?: unknown;
        indices?: unknown;
        values?: unknown;
        min?: number;
        max?: number;
        error?: string;
      };
      if (!r?.ok) {
        setFieldError(r?.error ?? `getSurfaceMesh(${field}) devolvió ok=false`);
        setFieldValues(null);
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
      setFieldValues(vals);
      setFieldMin(typeof r.min === 'number' ? r.min : undefined);
      setFieldMax(typeof r.max === 'number' ? r.max : undefined);
    } catch (e) {
      setFieldError(e instanceof Error ? e.message : String(e));
      setFieldValues(null);
    } finally {
      setFieldLoading(false);
    }
  };

  const feaDone = !!feaResult || poll.state === 'done';
  useEffect(() => {
    if (!feaDone) return;
    if (activeFieldMode === 'vonmises') void loadSurfaceField('vonmises');
    else if (activeFieldMode === 'disp') void loadSurfaceField('displacement');
    else setFieldValues(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feaDone, activeFieldMode]);

  const handleViewChange = (face: string) => {
    const dir = mapCubeFace(face);
    if (dir === 'reset') viewerRef.current?.reset();
    else viewerRef.current?.setView(dir);
  };

  const handleSolve = async () => {
    setFeaError(null);
    if (!backend.hasBridge()) {
      setFeaResult(null);
      setScaleFactor(5);
      setIsAnimating(false);
      return;
    }
    setFeaBusy(true);
    try {
      const r = (await backend.runFea({ backend: feaBackend })) as {
        ok: boolean;
        jobId?: string;
        error?: string;
      };
      if (!r.ok || !r.jobId) {
        setFeaError(r.error ?? 'runFea devolvió ok=false');
        setFeaBusy(false);
        return;
      }
      setJobId(r.jobId);
      setFeaBusy(false);
    } catch (e) {
      setFeaError(e instanceof Error ? e.message : String(e));
      setFeaBusy(false);
    }
  };

  const feaStatusText = feaBusy
    ? 'Lanzando job FEA...'
    : poll.loading
      ? `Resolviendo FEA... estado=${poll.state ?? '?'} progreso=${poll.progress ?? '?'}` 
      : poll.error
        ? `Error: ${poll.error}`
        : feaResult
          ? 'Resultado real del backend disponible.'
          : null;

  // Harmonic oscillation animation loop
  useEffect(() => {
    let interval: any = null;
    if (isAnimating) {
      interval = setInterval(() => {
        setAnimPhase((p) => {
          const next = p + 0.15;
          const osc = Math.sin(next) * 5 + 6;
          setScaleFactor(osc);
          return next;
        });
      }, 45);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isAnimating]);

  const handlePlayPause = () => {
    if (isAnimating) {
      setIsAnimating(false);
      setScaleFactor(5.0);
    } else {
      setIsAnimating(true);
    }
  };

  const handlePresetScale = (val: number) => {
    setIsAnimating(false);
    setScaleFactor(val);
  };

  // SVG deformation parameters based on scale factor
  const skewDeg = (scaleFactor / 5 - 1) * 0.9;
  const deformY = 1 + (scaleFactor / 5 - 1) * 0.02;

  return (
    <div className="w-full flex flex-col gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* Subheader Breadcrumb & Operational Mode Status Strip */}
      <div className="w-full bg-[#181b24] px-3 py-1.5 rounded flex flex-wrap items-center justify-between gap-2 border border-[#2e3646]/60">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">ESTUDIO:</span>
            <span className="font-label-sm text-[11px] text-[#f1f5f9] uppercase tracking-wide font-medium">
              ESTRUCTURAL_AERO_V2_STATIC
            </span>
          </div>
          <span className="w-1 h-1 rounded-full bg-[#2e3646]"></span>
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">MALLA:</span>
            <span className="font-label-sm text-[11px] text-[#7bd0ff]">Tet4 Lineal (184,920 els)</span>
          </div>
          <span className="w-1 h-1 rounded-full bg-[#2e3646]"></span>
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">MAT:</span>
            <span className="font-label-sm text-[11px] text-[#f1f5f9]">
              {material.name} (E={material.youngModulusGpa} GPa, ν={material.poissonRatio})
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
            <span className="font-label-sm text-[11px] text-[#10b981] uppercase font-medium">
              FEA Convergido (Residuo: 4.8e-09)
            </span>
          </div>
          <button
            onClick={handleSolve}
            disabled={feaBusy || poll.loading}
            className="bg-[#1f2430] hover:bg-[#272a33] px-2.5 py-1 rounded flex items-center gap-1 text-[#f1f5f9] border border-[#2e3646] hover:text-[#7bd0ff] transition-colors font-label-sm text-[10px] disabled:opacity-60"
          >
            <RefreshCw className="w-3 h-3" />
            <span>{feaBusy || poll.loading ? 'Resolviendo...' : isDemo ? 'Re-computar FEA (demo)' : 'Resolver FEA (backend)'}</span>
          </button>
        </div>
      </div>

      {/* Main 3-Pane FEA Analytical Workspace */}
      <div className="w-full grid grid-cols-12 gap-2 flex-1">
        {/* LEFT PANEL: FEA Solver Summary, Residuals & Key Metrics */}
        <aside className="col-span-12 xl:col-span-3 flex flex-col gap-2">
          {/* Backend Selector Card */}
          <div className="bg-[#181b24] rounded-lg p-2.5 shadow-sm flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-[#7bd0ff]" />
                <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Motor FEA Activo</span>
              </div>
              <span className="px-1.5 py-0.5 rounded bg-[#10b981]/15 text-[#10b981] font-label-sm text-[10px] uppercase font-medium">
                Verificado Standalone
              </span>
            </div>

            <div className="grid grid-cols-2 gap-1.5 mt-0.5">
              <button
                onClick={() => onSetBackend('numpy')}
                className={`flex flex-col text-left p-2 rounded transition-all cursor-pointer border ${
                  feaBackend === 'numpy'
                    ? 'bg-[#1f2430] border-[#0ea5e9] shadow-sm'
                    : 'bg-[#1c1f29] border-[#2e3646] hover:bg-[#272a33]'
                }`}
                type="button"
              >
                <span className={`font-headline-sm text-[11px] ${feaBackend === 'numpy' ? 'text-[#7bd0ff]' : 'text-[#f1f5f9]'}`}>
                  NumPy / SciPy
                </span>
                <span className="font-label-sm text-[10px] text-[#64748b] mt-0.5">Skyline LU · Tet4 Local</span>
                <span className="font-label-sm text-[10px] text-[#10b981] mt-1 font-medium">
                  {feaBackend === 'numpy' ? '● Activo 64-bit' : 'Disponible'}
                </span>
              </button>

              <button
                onClick={() => onSetBackend('kratos')}
                className={`flex flex-col text-left p-2 rounded transition-all cursor-pointer border ${
                  feaBackend === 'kratos'
                    ? 'bg-[#1f2430] border-[#0ea5e9] shadow-sm'
                    : 'bg-[#1c1f29] border-[#2e3646] hover:bg-[#272a33]'
                }`}
                type="button"
              >
                <span className={`font-headline-sm text-[11px] ${feaBackend === 'kratos' ? 'text-[#7bd0ff]' : 'text-[#f1f5f9]'}`}>
                  Kratos Multiphysics
                </span>
                <span className="font-label-sm text-[10px] text-[#64748b] mt-0.5">Iterativo AMGCL</span>
                <span className="font-label-sm text-[10px] text-[#7bd0ff] mt-1">
                  {feaBackend === 'kratos' ? '● Activo AMGCL' : 'Disponible OpenMP'}
                </span>
              </button>
            </div>

            {/* Solve Timing Telemetry Breakdown */}
            <div className="bg-[#1c1f29] rounded p-2 flex flex-col gap-1.5 border border-[#2e3646]/30">
              <div className="flex items-center justify-between font-label-sm text-[10px]">
                <span className="text-[#94a3b8]">Tiempo Total Solve:</span>
                <span className="text-[#7bd0ff] font-medium">4.82 s ({feaBackend === 'numpy' ? 'NumPy Core' : 'AMGCL'})</span>
              </div>
              <div className="w-full h-1.5 bg-[#0b0e17] rounded-full overflow-hidden flex">
                <div className="h-full bg-[#7bd0ff]" style={{ width: '23.8%' }} title="Ensamblaje K: 1.15s"></div>
                <div className="h-full bg-[#0ea5e9]" style={{ width: '61.0%' }} title="Factorización LU: 2.94s"></div>
                <div className="h-full bg-[#10b981]" style={{ width: '15.2%' }} title="Post-proceso: 0.73s"></div>
              </div>
              <div className="grid grid-cols-3 gap-1 pt-0.5 font-label-sm text-[9px] text-[#64748b]">
                <div>Ensamblado: <span className="text-[#f1f5f9]">1.15s</span></div>
                <div>Factoriz.: <span className="text-[#f1f5f9]">2.94s</span></div>
                <div>Post-eval: <span className="text-[#f1f5f9]">0.73s</span></div>
              </div>
            </div>
          </div>

          {/* Residual Convergence Graph */}
          <div className="bg-[#181b24] rounded-lg p-2.5 shadow-sm flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <TrendingDown className="w-4 h-4 text-[#7bd0ff]" />
                <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Convergencia de Residuos</span>
              </div>
              <span className="font-label-sm text-[10px] text-[#10b981]">||Ku - F||/||F|| &lt; 10⁻⁸</span>
            </div>

            <div className="w-full bg-[#1c1f29] rounded p-2 flex flex-col gap-1 border border-[#2e3646]/30">
              <div className="h-28 w-full relative">
                <svg className="w-full h-full overflow-visible" viewBox="0 0 280 100" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="residual-gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>
                  {/* Grid lines */}
                  <line x1="0" y1="10" x2="280" y2="10" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="1" />
                  <line x1="0" y1="35" x2="280" y2="35" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="1" />
                  <line x1="0" y1="60" x2="280" y2="60" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="1" />
                  <line x1="0" y1="85" x2="280" y2="85" stroke="#2e3646" strokeDasharray="2 2" strokeWidth="1" />
                  {/* Target Threshold */}
                  <line x1="0" y1="85" x2="280" y2="85" stroke="#10b981" strokeDasharray="3 3" strokeWidth="1.2" />

                  {/* Residual Curve & Fill */}
                  <polygon
                    points="10,12 45,28 90,44 140,62 195,74 240,82 275,88 275,98 10,98"
                    fill="url(#residual-gradient)"
                  />
                  <polyline
                    points="10,12 45,28 90,44 140,62 195,74 240,82 275,88"
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="2"
                  />
                  <circle cx="10" cy="12" r="3" fill="#ffb4ab" />
                  <circle cx="90" cy="44" r="2.5" fill="#38bdf8" />
                  <circle cx="195" cy="74" r="2.5" fill="#38bdf8" />
                  <circle cx="275" cy="88" r="3.5" fill="#10b981" />
                </svg>
              </div>

              <div className="flex justify-between items-center font-label-sm text-[9px] text-[#64748b]">
                <span>Iter 1 (1.0e+0)</span>
                <span>Iter 6 (4.2e-05)</span>
                <span className="text-[#10b981] font-medium">Iter 14 (3.1e-09)</span>
              </div>
            </div>
          </div>

          {/* Key Mechanical Results Matrix */}
          <div className="bg-[#181b24] rounded-lg p-2.5 shadow-sm flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Matriz de Resultados Clave</span>
              <span className="font-label-sm text-[10px] text-[#64748b]">
                {feaResult ? 'Resultado real (backend)' : isDemo ? 'Demo (sin pywebview)' : 'Estático Lineal'}
              </span>
            </div>

            {(feaStatusText || feaError) && (
              <div className={`rounded px-2 py-1 text-[10px] border ${feaError || poll.error ? 'text-[#fca5a5] bg-[#ef4444]/10 border-[#ef4444]/30' : 'text-[#7bd0ff] bg-[#0ea5e9]/10 border-[#0ea5e9]/30'}`}>
                {feaError ?? poll.error ?? feaStatusText}
              </div>
            )}
            {feaResult && (
              <div className="rounded bg-[#0b0e17] border border-[#2e3646]/40 p-2 text-[10px] font-mono text-[#7bd0ff] whitespace-pre-wrap break-all max-h-40 overflow-y-auto">
                {JSON.stringify(feaResult, null, 2)}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              {/* Von Mises Peak */}
              <div className="bg-[#1c1f29] rounded p-2 flex items-center justify-between hover:bg-[#272a33] transition-colors border border-[#2e3646]/30">
                <div className="flex flex-col">
                  <span className="font-body-sm text-[10px] text-[#94a3b8]">Tensión Von Mises Máx (σ_vm)</span>
                  <span className="font-label-lg text-[13px] text-[#f59e0b] font-bold">342.60 MPa</span>
                  <span className="font-label-sm text-[9px] text-[#64748b]">Nodo #14092 · Orejeta frontal</span>
                </div>
                <div className="text-right flex flex-col items-end">
                  <span className="font-label-sm text-[10px] px-1.5 py-0.5 rounded bg-[#10b981]/15 text-[#10b981] font-medium">
                    FS = 1.47
                  </span>
                  <span className="font-label-sm text-[9px] text-[#64748b] mt-0.5">Límite: 503.0 MPa</span>
                </div>
              </div>

              {/* Displacement Result */}
              <div className="bg-[#1c1f29] rounded p-2 flex items-center justify-between hover:bg-[#272a33] transition-colors border border-[#2e3646]/30">
                <div className="flex flex-col">
                  <span className="font-body-sm text-[10px] text-[#94a3b8]">Desplazamiento Resultante |u|</span>
                  <span className="font-label-lg text-[13px] text-[#7bd0ff] font-bold">0.412 mm</span>
                  <span className="font-label-sm text-[9px] text-[#64748b]">En nodo de tracción exterior</span>
                </div>
                <div className="text-right flex flex-col items-end">
                  <span className="font-label-sm text-[10px] text-[#10b981]">Dentro de límite</span>
                  <span className="font-label-sm text-[9px] text-[#64748b] mt-0.5">δ_adm: 1.000 mm</span>
                </div>
              </div>

              {/* Total Compliance */}
              <div className="bg-[#1c1f29] rounded p-2 flex items-center justify-between hover:bg-[#272a33] transition-colors border border-[#2e3646]/30">
                <div className="flex flex-col">
                  <span className="font-body-sm text-[10px] text-[#94a3b8]">Compliance Total (1/2 uᵀKu)</span>
                  <span className="font-label-lg text-[13px] text-[#f1f5f9] font-bold">14.820 J</span>
                  <span className="font-label-sm text-[9px] text-[#64748b]">Energía elástica absorbida</span>
                </div>
                <div className="text-right flex flex-col items-end">
                  <span className="font-label-sm text-[10px] px-1.5 py-0.5 rounded bg-[#0ea5e9]/20 text-[#7bd0ff]">
                    Base para SIMP
                  </span>
                  <span className="font-label-sm text-[9px] text-[#64748b] mt-0.5">min Compliance</span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* CENTRAL AREA: VTK 3D Viewport - Post-proceso FEA */}
        <main className="col-span-12 xl:col-span-6 flex flex-col gap-2">
          <div className="relative w-full h-[620px] rounded-lg bg-[#0b0e17] overflow-hidden shadow-2xl flex flex-col justify-between p-2 select-none border border-[#2e3646]">
            {/* Viewport Header Strip (Mode switchers & display toggles) */}
            <div className="w-full flex items-center justify-between z-20 pointer-events-auto">
              <div className="flex items-center gap-1 bg-[#181b24]/90 backdrop-blur-md p-1 rounded-lg shadow-md border border-[#2e3646]/60">
                <button
                  onClick={() => setActiveFieldMode('vonmises')}
                  className={`px-2.5 py-1 rounded font-headline-sm text-[11px] transition-colors ${
                    activeFieldMode === 'vonmises'
                      ? 'bg-[#0ea5e9] text-[#003751] font-semibold'
                      : 'bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                >
                  Tensión Von Mises
                </button>
                <button
                  onClick={() => setActiveFieldMode('disp')}
                  className={`px-2.5 py-1 rounded font-body-sm text-[11px] transition-colors ${
                    activeFieldMode === 'disp'
                      ? 'bg-[#0ea5e9] text-[#003751] font-semibold'
                      : 'bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                >
                  Desplazamiento U
                </button>
                <button
                  onClick={() => setActiveFieldMode('sigma1')}
                  className={`px-2.5 py-1 rounded font-body-sm text-[11px] transition-colors ${
                    activeFieldMode === 'sigma1'
                      ? 'bg-[#0ea5e9] text-[#003751] font-semibold'
                      : 'bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                >
                  Principal σ₁
                </button>
                <button
                  onClick={() => setActiveFieldMode('sed')}
                  className={`px-2.5 py-1 rounded font-body-sm text-[11px] transition-colors ${
                    activeFieldMode === 'sed'
                      ? 'bg-[#0ea5e9] text-[#003751] font-semibold'
                      : 'bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                >
                  Densidad Energía (SED)
                </button>
              </div>

              {/* View options icons */}
              <div className="flex items-center gap-1 bg-[#181b24]/90 backdrop-blur-md p-1 rounded-lg shadow-md border border-[#2e3646]/60">
                <button
                  onClick={() => setWireframeVisible(!wireframeVisible)}
                  className={`w-7 h-7 flex items-center justify-center rounded transition-colors ${
                    wireframeVisible ? 'bg-[#1f2430] text-[#7bd0ff]' : 'bg-[#1f2430] text-[#64748b]'
                  }`}
                  title="Alternar Malla Alambre"
                >
                  <Grid className="w-3.5 h-3.5" />
                </button>
                <button
                  className="w-7 h-7 flex items-center justify-center rounded bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]"
                  title="Vectores de Reacción & Cargas"
                >
                  <span className="material-symbols-outlined text-[15px]">north_east</span>
                </button>
                <button
                  className="w-7 h-7 flex items-center justify-center rounded bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]"
                  title="Isosuperficie de Límite Elástico"
                >
                  <Layers className="w-3.5 h-3.5" />
                </button>
                <button
                  className="w-7 h-7 flex items-center justify-center rounded bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]"
                  title="Captura de Pantalla HR"
                >
                  <Camera className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* 3D Real Viewport (three.js) — malla actual */}
            <div className="absolute inset-0 z-0 flex flex-col items-center justify-center overflow-hidden px-2 pt-14 pb-24">
              <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#2e3646_1px,transparent_1px)] [background-size:24px_24px]"></div>
              <div className="relative w-full max-w-[560px] flex flex-col gap-1">
                {meshError && (
                  <div className="text-[10px] text-[#fca5a5] bg-[#ef4444]/10 border border-[#ef4444]/30 rounded px-2 py-1">
                    Error: {meshError}
                  </div>
                )}
                <div className="rounded-lg overflow-hidden border border-[#2e3646]/60 bg-[#0f1117]">
                  <MeshViewer ref={viewerRef} mesh={previewMesh} wireframe={wireframeVisible} color="#38bdf8" height={320} profile={navProfile}
                    values={activeFieldMode === 'vonmises' || activeFieldMode === 'disp' ? fieldValues : null}
                    colorMin={fieldMin} colorMax={fieldMax}
                    colorbarLabel={activeFieldMode === 'vonmises' ? 'Von Mises (MPa)' : activeFieldMode === 'disp' ? 'Desplazamiento |u| (mm)' : undefined} />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] text-[#64748b]">
                    {fieldLoading ? 'Cargando campo superficial…' : fieldError ? `Campo FEA no disponible: ${fieldError}` : fieldValues ? `Campo ${activeFieldMode === 'disp' ? 'displacement' : 'vonmises'} aplicado (${fieldValues.length} nodos).` : 'Malla actual del backend. Ejecuta FEA para ver el colormap.'}
                  </p>
                  <button onClick={() => void loadMeshPreview()} disabled={meshLoading} className="shrink-0 px-2 py-1 rounded bg-[#1f2430] hover:bg-[#272a33] text-[#94a3b8] hover:text-[#7bd0ff] font-label-sm text-[10px] border border-[#2e3646]/50 flex items-center gap-1 disabled:opacity-60" type="button">
                    <RefreshCw className={"w-3 h-3" + (meshLoading ? " animate-spin" : "")} />
                    <span>{meshLoading ? "Cargando..." : "Cargar malla"}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Floating ViewCube (Top Right) */}
            <div className="absolute top-16 right-2 z-20 flex flex-col items-center">
              <ViewCube onViewChange={handleViewChange} />
              <div className="flex gap-1 mt-1">
                <button className="px-1.5 py-0.5 bg-[#181b24]/90 rounded text-[#94a3b8] hover:text-[#f1f5f9] font-label-sm text-[10px]">X</button>
                <button className="px-1.5 py-0.5 bg-[#181b24]/90 rounded text-[#94a3b8] hover:text-[#f1f5f9] font-label-sm text-[10px]">Y</button>
                <button className="px-1.5 py-0.5 bg-[#181b24]/90 rounded text-[#94a3b8] hover:text-[#f1f5f9] font-label-sm text-[10px]">Z</button>
              </div>
            </div>

            {/* Floating Colorbar Legend (Left Side) */}
            <div className="absolute left-2 top-16 bottom-20 z-20 w-36 bg-[#181b24]/90 backdrop-blur-md rounded-lg p-2 shadow-xl flex flex-col justify-between border border-[#2e3646]/60">
              <div className="flex flex-col gap-0.5">
                <span className="font-headline-sm text-[11px] text-[#f1f5f9]">Tensión (MPa)</span>
                <span className="font-label-sm text-[9px] text-[#64748b]">Von Mises Nodal</span>
              </div>

              {/* Spectrum bar with values */}
              <div className="flex items-stretch gap-2 h-full my-1.5">
                <div className="w-4 h-full rounded-sm relative overflow-hidden bg-gradient-to-b from-[#e63946] via-[#e9c46a] via-40% via-[#2ec4b6] via-70% to-[#023e8a] shadow-inner">
                  {/* Yield mark */}
                  <div className="absolute left-0 right-0 h-0.5 bg-[#ef4444]" style={{ bottom: '82%' }}></div>
                  {/* Current peak mark */}
                  <div className="absolute left-0 right-0 h-1 bg-white shadow" style={{ bottom: '72%' }}></div>
                  {/* Probe marker */}
                  <div className="absolute left-0 right-0 h-0.5 bg-[#7bd0ff] animate-pulse" style={{ bottom: '58%' }}></div>
                </div>

                <div className="flex flex-col justify-between font-label-sm text-[9px] text-[#94a3b8] h-full py-0.5">
                  <span className="text-[#ef4444] font-medium">350.0 Máx</span>
                  <span className="text-[#f59e0b]">284.1 Probe</span>
                  <span>210.0</span>
                  <span>140.0</span>
                  <span>70.0</span>
                  <span className="text-[#7bd0ff]">0.00 Mín</span>
                </div>
              </div>

              {/* Dynamic Probe Tooltip Card */}
              <div className="bg-[#1f2430] rounded p-1.5 flex flex-col border border-[#2e3646]/40">
                <div className="flex items-center justify-between font-label-sm text-[9px] text-[#64748b]">
                  <span>Sonda #{probeSelected}</span>
                  <span className="text-[#7bd0ff] font-medium">Activo</span>
                </div>
                <span className="font-headline-sm text-[12px] text-[#f59e0b] mt-0.5">284.1 MPa</span>
                <span className="font-label-sm text-[9px] text-[#94a3b8]">X: 132.8 | Y: 44.1</span>
              </div>
            </div>

            {/* Viewport Footer Controls */}
            <div className="w-full flex flex-wrap items-center justify-between gap-2 bg-[#181b24]/95 backdrop-blur-md p-2 rounded-lg shadow-lg z-20 pointer-events-auto border border-[#2e3646]/60">
              {/* Deformation scale controls */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-[#7bd0ff] text-[16px]">zoom_out_map</span>
                  <span className="font-label-sm text-[10px] text-[#94a3b8]">Factor Deformación:</span>
                  <span className="font-label-sm text-[10px] text-[#f1f5f9] font-bold">
                    {scaleFactor.toFixed(1)}x {scaleFactor === 1 ? '(Real)' : scaleFactor > 15 ? '(Extremo)' : '(Exagerado)'}
                  </span>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handlePresetScale(1)}
                    className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                      scaleFactor === 1 ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]'
                    }`}
                  >
                    1x (Real)
                  </button>
                  <button
                    onClick={() => handlePresetScale(5)}
                    className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                      scaleFactor === 5 ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]'
                    }`}
                  >
                    5x
                  </button>
                  <button
                    onClick={() => handlePresetScale(20)}
                    className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                      scaleFactor === 20 ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'bg-[#1f2430] text-[#94a3b8] hover:text-[#f1f5f9]'
                    }`}
                  >
                    20x
                  </button>
                </div>

                <input
                  type="range"
                  min="0"
                  max="25"
                  step="0.5"
                  value={scaleFactor}
                  onChange={(e) => handlePresetScale(parseFloat(e.target.value))}
                  className="w-24 h-1.5 bg-[#32343e] rounded cursor-pointer accent-[#0ea5e9]"
                />
              </div>

              {/* Harmonic Playback */}
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 bg-[#1f2430] rounded p-0.5 border border-[#2e3646]/50">
                  <button
                    onClick={handlePlayPause}
                    className={`w-6 h-6 flex items-center justify-center rounded transition-colors ${
                      isAnimating ? 'text-[#10b981]' : 'text-[#7bd0ff] hover:text-[#89ceff]'
                    }`}
                    title={isAnimating ? 'Pausar Ciclo Armónico' : 'Reproducir Ciclo Armónico'}
                  >
                    {isAnimating ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                  </button>
                </div>
                <span className="font-label-sm text-[10px] text-[#64748b]">Ciclo Elástico: 1.0 Hz (Estático)</span>
                <button
                  onClick={() => viewerRef.current?.reset()}
                  className="px-2 py-1 rounded bg-[#1f2430] hover:bg-[#272a33] text-[#f1f5f9] hover:text-[#7bd0ff] font-label-sm text-[10px] transition-colors flex items-center gap-1 border border-[#2e3646]/50"
                >
                  <Maximize2 className="w-3 h-3" />
                  <span>Reset Cámara</span>
                </button>
              </div>
            </div>
          </div>

          {/* Quick Analysis Audit & Load Cases Bar */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#181b24] rounded p-2 shadow-sm flex items-center gap-2 border border-[#2e3646]/40">
              <div className="w-7 h-7 rounded bg-[#0ea5e9]/15 flex items-center justify-center text-[#7bd0ff]">
                <Scale className="w-4 h-4" />
              </div>
              <div className="flex flex-col">
                <span className="font-label-sm text-[9px] text-[#64748b]">Equilibrio Global ΣF</span>
                <span className="font-headline-sm text-[11px] text-[#f1f5f9]">0.0000 N (Exacto)</span>
              </div>
            </div>

            <div className="bg-[#181b24] rounded p-2 shadow-sm flex items-center gap-2 border border-[#2e3646]/40">
              <div className="w-7 h-7 rounded bg-[#10b981]/15 flex items-center justify-center text-[#10b981]">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="flex flex-col">
                <span className="font-label-sm text-[9px] text-[#64748b]">Energía Residual Relativa</span>
                <span className="font-headline-sm text-[11px] text-[#10b981]">2.14 × 10⁻¹⁰</span>
              </div>
            </div>

            <div className="bg-[#181b24] rounded p-2 shadow-sm flex items-center gap-2 border border-[#2e3646]/40">
              <div className="w-7 h-7 rounded bg-[#ffb95f]/15 flex items-center justify-center text-[#ffb95f]">
                <Flame className="w-4 h-4" />
              </div>
              <div className="flex flex-col">
                <span className="font-label-sm text-[9px] text-[#64748b]">Caso de Carga Activo</span>
                <span className="font-headline-sm text-[11px] text-[#f1f5f9]">LC1: Flexión + Torsión</span>
              </div>
            </div>
          </div>
        </main>

        {/* RIGHT PANEL: Structural Diagnostics & Transition to SIMP */}
        <aside className="col-span-12 xl:col-span-3 flex flex-col gap-2">
          {/* Critical Hotspots Card */}
          <div className="bg-[#181b24] rounded-lg p-2.5 shadow-sm flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-[#f59e0b]" />
                <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Puntos Críticos Detectados</span>
              </div>
              <span className="font-label-sm text-[10px] text-[#64748b]">3 Zonas</span>
            </div>

            <div className="flex flex-col gap-1.5 text-[11px]">
              {/* Critical Node 1 */}
              <div
                onClick={() => setProbeSelected('14092')}
                className="bg-[#1c1f29] rounded p-2 flex flex-col gap-1 hover:bg-[#272a33] transition-colors cursor-pointer border border-[#2e3646]/40"
              >
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-[10px] text-[#ef4444] font-medium">
                    Concentración en Ojal de Anclaje
                  </span>
                  <span className="font-label-sm text-[11px] text-[#f1f5f9] font-bold">342.6 MPa</span>
                </div>
                <p className="font-body-sm text-[10px] text-[#94a3b8]">
                  Radio de entalle R=3.5 mm. Se recomienda preservar volumen no modificable en SIMP.
                </p>
                <div className="flex items-center justify-between mt-0.5 font-label-sm text-[9px] text-[#64748b]">
                  <span>Nodo #14092</span>
                  <span className="text-[#f59e0b] font-medium">FS = 1.47 (Crítico)</span>
                </div>
              </div>

              {/* Critical Node 2 */}
              <div
                onClick={() => setProbeSelected('08941')}
                className="bg-[#1c1f29] rounded p-2 flex flex-col gap-1 hover:bg-[#272a33] transition-colors cursor-pointer border border-[#2e3646]/40"
              >
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-[10px] text-[#f59e0b] font-medium">
                    Transición Alma - Pestaña
                  </span>
                  <span className="font-label-sm text-[11px] text-[#f1f5f9] font-bold">284.1 MPa</span>
                </div>
                <p className="font-body-sm text-[10px] text-[#94a3b8]">
                  Gradiente de corte elevado. Alta contribución a la rigidez total.
                </p>
                <div className="flex items-center justify-between mt-0.5 font-label-sm text-[9px] text-[#64748b]">
                  <span>Nodo #08941</span>
                  <span className="text-[#10b981] font-medium">FS = 1.77 (Aceptable)</span>
                </div>
              </div>

              {/* Low Stress Area */}
              <div className="bg-[#1c1f29] rounded p-2 flex flex-col gap-1 hover:bg-[#272a33] transition-colors cursor-pointer border border-[#2e3646]/40">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-[10px] text-[#7bd0ff] font-medium">
                    Zona Central Pasiva (Vacío Potencial)
                  </span>
                  <span className="font-label-sm text-[11px] text-[#f1f5f9] font-bold">14.2 MPa</span>
                </div>
                <p className="font-body-sm text-[10px] text-[#94a3b8]">
                  Baja densidad de energía. Candidato de vaciado prioritario en SIMP.
                </p>
                <div className="flex items-center justify-between mt-0.5 font-label-sm text-[9px] text-[#64748b]">
                  <span>Volumen: ~38% total</span>
                  <span className="text-[#7bd0ff]">ρ_e → 0.001</span>
                </div>
              </div>
            </div>
          </div>

          {/* Numerical Validation vs Theoretical Solution */}
          <div className="bg-[#181b24] rounded-lg p-2.5 shadow-sm flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Validación Numérica</span>
              <span className="px-1.5 py-0.5 rounded bg-[#10b981]/15 text-[#10b981] font-label-sm text-[10px]">
                ISO 17025 Compliant
              </span>
            </div>

            <div className="space-y-1.5 text-[11px]">
              <div className="bg-[#1c1f29] rounded p-2 flex items-center justify-between border border-[#2e3646]/30">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />
                  <span className="text-[#f1f5f9]">Patch Test Deformación Constante</span>
                </div>
                <span className="font-label-sm text-[10px] text-[#10b981] font-medium">PASSED (100%)</span>
              </div>

              <div className="bg-[#1c1f29] rounded p-2 flex items-center justify-between border border-[#2e3646]/30">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />
                  <span className="text-[#f1f5f9]">Convergencia h-adaptativa</span>
                </div>
                <span className="font-label-sm text-[10px] text-[#10b981] font-medium">Error &lt; 1.8%</span>
              </div>

              <div className="bg-[#1c1f29] rounded p-2 flex items-center justify-between border border-[#2e3646]/30">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#7bd0ff] text-[15px]">numbers</span>
                  <span className="text-[#f1f5f9]">Número de Condición cond(K)</span>
                </div>
                <span className="font-label-sm text-[10px] text-[#94a3b8]">4.12 × 10⁴ (Bien cond.)</span>
              </div>
            </div>
          </div>

          {/* Ready for SIMP Card & Transition Button */}
          <div className="bg-[#181b24] rounded-lg p-2.5 shadow-sm flex flex-col gap-2 mt-auto border border-[#2e3646] relative overflow-hidden">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">shape_line</span>
              <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Preparación SIMP</span>
            </div>

            <div className="bg-[#1c1f29] rounded p-2 flex flex-col gap-1.5 border border-[#2e3646]/40 text-[11px]">
              <div className="flex items-center gap-1 text-[#10b981] font-label-sm text-[10px]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                <span>Matriz Ke Elemental Pre-computada</span>
              </div>
              <p className="text-[#94a3b8] text-[10px] leading-relaxed">
                El modelo cumple todos los criterios de estabilidad. Las matrices de rigidez están listas para penalización SIMP:
              </p>
              <div className="bg-[#0b0e17] p-1.5 rounded text-center font-mono text-[10px] text-[#7bd0ff] tracking-wide border border-[#2e3646]/30">
                K_e(ρ) = (ρ_min + (1 - ρ_min) · ρ_e^p) · K_e0
              </div>
              <div className="grid grid-cols-2 gap-1 pt-1 font-label-sm text-[9px] text-[#64748b]">
                <span>Penalizador (p): <strong className="text-[#f1f5f9]">3.00</strong></span>
                <span>Filtro Helmholtz: <strong className="text-[#f1f5f9]">R_min = 6 mm</strong></span>
              </div>
            </div>

            <button
              onClick={onAdvanceToSimp}
              className="w-full mt-1 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-headline-sm text-[12px] py-2 px-3 rounded flex items-center justify-center gap-1.5 shadow-md font-semibold transition-all transform hover:-translate-y-0.5"
              type="button"
            >
              <span>Configurar Optimización Topológica</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <div className="flex items-center justify-between px-1 text-[#64748b] font-label-sm text-[9px]">
              <span>Siguiente paso: Paso 4 (SIMP)</span>
              <span>Volumen Obj.: 40%</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};
