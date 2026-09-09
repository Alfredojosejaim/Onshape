import React, { useState, useEffect, useCallback, useRef } from 'react';
import { MaterialProperty } from '../../types';
import { backend } from '../../lib/bridge';
import { ViewCube } from '../ViewCube';
import { MeshViewer, MeshViewerHandle, PreviewMesh, mapCubeFace } from '../MeshViewer';
import { NAV_PROFILE_NAMES, NAV_PROFILES, readStoredNavProfile, type NavProfileName } from '../../lib/navigation';
import {
  Maximize2,
  Minimize2,
  Eye,
  EyeOff,
  Edit2,
  CheckCircle,
  Play,
  RefreshCw,
  Scissors,
  Ruler,
  Grid,
  Filter,
  Layers,
  Shield,
  Ban,
  Anchor,
  ArrowDown,
  AlertTriangle,
} from 'lucide-react';

interface Screen1Props {
  onAdvanceToMesh: () => void;
  selectedMaterial: MaterialProperty;
  onSelectMaterial: (m: MaterialProperty) => void;
  activeFilename: string;
  materials?: MaterialProperty[];
}

export const Screen1CadPreProcess: React.FC<Screen1Props> = ({
  onAdvanceToMesh,
  selectedMaterial,
  onSelectMaterial,
  activeFilename,
  materials,
}) => {
  const [hMin, setHMin] = useState<number>(1.5);
  const [hMax, setHMax] = useState<number>(6.0);
  const [selectionMode, setSelectionMode] = useState<'faces' | 'edges' | 'vertices' | 'volumes'>('faces');
  const [wireframeActive, setWireframeActive] = useState<boolean>(true);
  const [clipActive, setClipActive] = useState<boolean>(false);
  const [isRemeshing, setIsRemeshing] = useState<boolean>(false);
  const [remeshStatus, setRemeshStatus] = useState<string | null>(null);
  const [remeshError, setRemeshError] = useState<string | null>(null);
  const [globalCoordsExpanded, setGlobalCoordsExpanded] = useState<boolean>(true);
  const [previewMesh, setPreviewMesh] = useState<PreviewMesh | null>(null);
  const [meshError, setMeshError] = useState<string | null>(null);
  const [meshLoading, setMeshLoading] = useState<boolean>(false);
  const viewerRef = useRef<MeshViewerHandle>(null);
  const [navProfile, setNavProfile] = useState<NavProfileName>(() => readStoredNavProfile());
  const [selPoint, setSelPoint] = useState<string | null>(null);
  const materialOptions = materials && materials.length > 0 ? materials : [];

  const loadMeshPreview = useCallback(async () => {
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
      } else if (!r.mesh) {
        // mock sin pywebview: estado vacío elegante, no es error fatal
        setPreviewMesh(null);
      } else {
        setPreviewMesh(r.mesh);
      }
    } catch (e) {
      setMeshError(e instanceof Error ? e.message : String(e));
      setPreviewMesh(null);
    } finally {
      setMeshLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMeshPreview();
  }, [loadMeshPreview]);

  // Perfil de navegación: backend -> localStorage -> default autocad.
  useEffect(() => {
    (async () => {
      try {
        const r = (await backend.getNavProfiles()) as {
          ok: boolean;
          current?: string;
        };
        if (r.ok && typeof r.current === 'string') {
          const cur = r.current as NavProfileName;
          if ((NAV_PROFILE_NAMES as string[]).includes(cur)) {
            setNavProfile(cur);
            try { localStorage.setItem('topoopt.nav', cur); } catch { /* noop */ }
            return;
          }
        }
      } catch { /* fallback localStorage */ }
      setNavProfile(readStoredNavProfile());
    })();
  }, []);

  const handleNavProfile = (p: NavProfileName) => {
    setNavProfile(p);
    try { localStorage.setItem('topoopt.nav', p); } catch { /* noop */ }
    void backend.setNavProfile(p).catch(() => undefined);
  };

  const handleRemesh = async () => {
    setIsRemeshing(true);
    setRemeshStatus(null);
    setRemeshError(null);
    try {
      const r = (await backend.generateMesh({ target_element_size: hMax })) as {
        ok: boolean;
        error?: string;
      };
      if (!r.ok) {
        setRemeshError(r.error ?? 'generateMesh devolvió ok=false');
      } else {
        setRemeshStatus('Malla regenerada correctamente.');
        void loadMeshPreview();
      }
    } catch (e) {
      setRemeshError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsRemeshing(false);
    }
  };

  const resetCamera = () => {
    viewerRef.current?.reset();
  };

  const handleViewChange = (face: string) => {
    const dir = mapCubeFace(face);
    if (dir === 'reset') viewerRef.current?.reset();
    else viewerRef.current?.setView(dir);
  };

  return (
    <div className="w-full flex flex-col xl:flex-row gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* LEFT PANEL: Tree, Pre-Process Features & Gmsh Mesher */}
      <aside className="w-full xl:w-72 2xl:w-80 flex flex-col gap-2 flex-shrink-0">
        {/* CAD Feature Tree Card */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md flex flex-col gap-1 border border-[#2e3646]/50">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#7bd0ff] text-[16px]">account_tree</span>
              <span className="font-headline-sm text-[13px] text-[#f1f5f9] tracking-tight">Árbol de Operaciones</span>
            </div>
            <span className="font-label-sm text-[10px] bg-[#32343e] px-1.5 py-0.5 rounded text-[#94a3b8]">
              CAD / Pre
            </span>
          </header>

          {/* Tree Nodes List */}
          <div className="flex flex-col gap-0.5 py-1 text-body-sm text-[#94a3b8]">
            {/* Global Coordinate System */}
            <div
              onClick={() => setGlobalCoordsExpanded(!globalCoordsExpanded)}
              className="group flex items-center justify-between px-1.5 py-1 rounded hover:bg-[#1f2430] cursor-pointer"
            >
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[#64748b] text-[14px]">
                  {globalCoordsExpanded ? 'expand_more' : 'chevron_right'}
                </span>
                <span className="material-symbols-outlined text-[#64748b] text-[14px]">grid_4x4</span>
                <span className="text-[#f1f5f9] text-[11px]">Sist. Coordenado Global</span>
              </div>
              <Eye className="w-3.5 h-3.5 text-[#64748b] group-hover:text-[#7bd0ff]" />
            </div>

            {globalCoordsExpanded && (
              <div className="pl-4 flex flex-col gap-0.5 border-l border-[#2e3646]/40 ml-2">
                <div className="flex items-center justify-between px-1.5 py-0.5 rounded hover:bg-[#272a33] text-[#64748b] hover:text-[#f1f5f9] text-[10px] cursor-pointer">
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#ef4444]"></span>Plano XY (Base)
                  </span>
                  <span className="font-label-sm text-[10px] opacity-60">Z=0</span>
                </div>
                <div className="flex items-center justify-between px-1.5 py-0.5 rounded hover:bg-[#272a33] text-[#64748b] hover:text-[#f1f5f9] text-[10px] cursor-pointer">
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>Plano XZ (Simetría)
                  </span>
                  <span className="font-label-sm text-[10px] opacity-60">Y=0</span>
                </div>
                <div className="flex items-center justify-between px-1.5 py-0.5 rounded hover:bg-[#272a33] text-[#64748b] hover:text-[#f1f5f9] text-[10px] cursor-pointer">
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#7bd0ff]"></span>Plano YZ (Transversal)
                  </span>
                  <span className="font-label-sm text-[10px] opacity-60">X=0</span>
                </div>
              </div>
            )}

            {/* Imported STEP Solid */}
            <div className="group flex items-center justify-between px-1.5 py-1 rounded bg-[#1f2430]/70 hover:bg-[#1f2430] cursor-pointer border border-[#2e3646]/40">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[#89ceff] text-[16px]">deployed_code</span>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-headline-sm text-[11px] leading-tight truncate max-w-[160px]">
                    {activeFilename}
                  </span>
                  <span className="text-[10px] font-label-sm text-[#64748b]">12 Caras • 18 Aristas • 1 Sólido</span>
                </div>
              </div>
              <Eye className="w-3.5 h-3.5 text-[#7bd0ff]" />
            </div>

            {/* Feature: Fixed Encastre Soporte */}
            <div className="flex items-center justify-between px-1.5 py-1 rounded bg-[#272a33]/40 hover:bg-[#1f2430] cursor-pointer">
              <div className="flex items-center gap-1.5">
                <div className="w-5 h-5 rounded bg-[#7bd0ff]/10 flex items-center justify-center">
                  <Anchor className="w-3 h-3 text-[#7bd0ff]" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium text-[11px]">Encastre Soporte</span>
                  <span className="text-[10px] font-label-sm text-[#7bd0ff]">3 Caras | Ux=Uy=Uz=0</span>
                </div>
              </div>
              <CheckCircle className="w-3.5 h-3.5 text-[#10b981]" />
            </div>

            {/* Feature: Tension Load */}
            <div className="flex items-center justify-between px-1.5 py-1 rounded bg-[#272a33]/40 hover:bg-[#1f2430] cursor-pointer">
              <div className="flex items-center gap-1.5">
                <div className="w-5 h-5 rounded bg-[#ffb95f]/10 flex items-center justify-center">
                  <ArrowDown className="w-3 h-3 text-[#ffb95f]" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium text-[11px]">Tracción Cilíndrica</span>
                  <span className="text-[10px] font-label-sm text-[#ffb95f]">[0, -4500, 1200] N</span>
                </div>
              </div>
              <Edit2 className="w-3 h-3 text-[#7bd0ff]" />
            </div>

            {/* Feature: Non-Design Space Preserved */}
            <div className="flex items-center justify-between px-1.5 py-1 rounded bg-[#10b981]/10 hover:bg-[#10b981]/15 cursor-pointer border border-[#10b981]/25">
              <div className="flex items-center gap-1.5">
                <div className="w-5 h-5 rounded bg-[#10b981]/20 flex items-center justify-center">
                  <Shield className="w-3 h-3 text-[#10b981]" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium text-[11px]">Región Preservada</span>
                  <span className="text-[10px] font-label-sm text-[#10b981]">Pernos y Bujes (8 mm)</span>
                </div>
              </div>
              <span className="font-label-sm text-[9px] px-1.5 py-0.5 rounded bg-[#10b981] text-[#0b0e17] font-semibold">
                SAFE
              </span>
            </div>

            {/* Feature: Keep-out Void Obstacle */}
            <div className="flex items-center justify-between px-1.5 py-1 rounded bg-[#ef4444]/10 hover:bg-[#ef4444]/15 cursor-pointer border border-[#ef4444]/25">
              <div className="flex items-center gap-1.5">
                <div className="w-5 h-5 rounded bg-[#ef4444]/20 flex items-center justify-center">
                  <Ban className="w-3 h-3 text-[#ef4444]" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium text-[11px]">Obstáculo (Keep-Out)</span>
                  <span className="text-[10px] font-label-sm text-[#ef4444]">Cilindro Paso Tornillo</span>
                </div>
              </div>
              <span className="font-label-sm text-[9px] px-1.5 py-0.5 rounded bg-[#ef4444] text-[#0b0e17] font-semibold">
                VOID
              </span>
            </div>
          </div>
        </section>

        {/* Gmsh Meshing Controls Card */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md flex flex-col gap-1.5 border border-[#2e3646]/50">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#7bd0ff] text-[16px]">grid_guides</span>
              <span className="font-headline-sm text-[13px] text-[#f1f5f9] tracking-tight">Mallador Gmsh v4</span>
            </div>
            <span className="font-label-sm text-[10px] text-[#10b981] bg-[#32343e] px-1.5 py-0.5 rounded">
              Conforme
            </span>
          </header>

          <div className="flex flex-col gap-2 pt-0.5 text-body-sm">
            <div className="flex items-center justify-between bg-[#1f2430]/40 px-2 py-1 rounded">
              <span className="text-[#94a3b8] text-[11px]">Algoritmo:</span>
              <span className="font-label-sm text-[11px] text-[#7bd0ff]">Frontal 3D (Delaunay)</span>
            </div>

            {/* Min / Max Element Size */}
            <div className="grid grid-cols-2 gap-1.5">
              <div className="bg-[#1f2430]/60 p-1.5 rounded flex flex-col">
                <span className="font-label-sm text-[10px] text-[#94a3b8]">h_min (mm)</span>
                <div className="flex items-center justify-between mt-0.5">
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="5.0"
                    value={hMin}
                    onChange={(e) => setHMin(parseFloat(e.target.value) || 1.5)}
                    className="w-16 bg-transparent font-label-md text-[12px] text-[#f1f5f9] font-bold focus:outline-none"
                  />
                  <span className="material-symbols-outlined text-[#64748b] text-[14px]">tune</span>
                </div>
              </div>

              <div className="bg-[#1f2430]/60 p-1.5 rounded flex flex-col">
                <span className="font-label-sm text-[10px] text-[#94a3b8]">h_max (mm)</span>
                <div className="flex items-center justify-between mt-0.5">
                  <input
                    type="number"
                    step="0.5"
                    min="2.0"
                    max="15.0"
                    value={hMax}
                    onChange={(e) => setHMax(parseFloat(e.target.value) || 6.0)}
                    className="w-16 bg-transparent font-label-md text-[12px] text-[#f1f5f9] font-bold focus:outline-none"
                  />
                  <span className="material-symbols-outlined text-[#64748b] text-[14px]">tune</span>
                </div>
              </div>
            </div>

            {/* Quality Telemetry Bar */}
            <div className="bg-[#0b0e17] p-2 rounded flex flex-col gap-1 border border-[#2e3646]/30">
              <div className="flex justify-between items-center text-[10px] font-label-sm">
                <span className="text-[#94a3b8]">Calidad Jacobiana:</span>
                <span className="text-[#10b981] font-medium">0.84 (Excelente)</span>
              </div>
              <div className="w-full bg-[#32343e] rounded h-1.5 overflow-hidden">
                <div className="bg-[#10b981] h-full rounded transition-all duration-500" style={{ width: '84%' }}></div>
              </div>
              <div className="flex justify-between items-center text-[10px] font-label-sm text-[#94a3b8] pt-1">
                <span>Nodos: <strong className="text-[#f1f5f9] font-label-sm">48,290</strong></span>
                <span>Elem. Tet4: <strong className="text-[#7bd0ff] font-label-sm">215,410</strong></span>
              </div>
            </div>

            {/* Remesh Trigger */}
            <button
              onClick={handleRemesh}
              disabled={isRemeshing}
              className="w-full py-1.5 px-2 bg-[#1f2430] hover:bg-[#272a33] text-[#f1f5f9] hover:text-[#7bd0ff] rounded flex items-center justify-center gap-1.5 font-headline-sm text-[11px] shadow-sm transition-all border border-[#2e3646]"
              type="button"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRemeshing ? 'animate-spin text-[#7bd0ff]' : ''}`} />
              <span>{isRemeshing ? 'Regenerando Malla...' : 'Remallar Geometría Gmsh'}</span>
            </button>
            {remeshStatus && (
              <div className="text-[10px] text-[#10b981] bg-[#10b981]/10 border border-[#10b981]/30 rounded px-2 py-1">{remeshStatus}</div>
            )}
            {remeshError && (
              <div className="text-[10px] text-[#fca5a5] bg-[#ef4444]/10 border border-[#ef4444]/30 rounded px-2 py-1">Error: {remeshError}</div>
            )}
          </div>
        </section>

        {/* Step Inspector Helper */}
        <div className="bg-[#181b24]/60 rounded-lg p-2 flex items-center justify-between text-[10px] font-label-sm text-[#94a3b8] border border-[#2e3646]/30">
          <span className="flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 text-[#f59e0b]" />
            Tolerancia Angular: 12.5°
          </span>
          <span className="text-[#bec8d2]">Deflexión: 0.02 mm</span>
        </div>
      </aside>

      {/* CENTRAL AREA: VTK 3D CAD Viewport */}
      <main className="flex-1 flex flex-col relative rounded-lg bg-[#0b0e17] overflow-hidden shadow-2xl min-h-[560px] border border-[#2e3646]">
        {/* Top Floating Viewport Control Ribbon */}
        <div className="absolute top-2 left-2 z-20 flex items-center gap-1 bg-[#1f2430]/90 backdrop-blur-md px-1.5 py-1 rounded-lg shadow-lg border border-[#2e3646]/60">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setSelectionMode('faces')}
              className={`px-2 py-0.5 rounded font-headline-sm text-[11px] flex items-center gap-1 transition-colors ${
                selectionMode === 'faces'
                  ? 'bg-[#0ea5e9] text-[#003751] font-semibold'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#272a33]'
              }`}
              title="Selección de Caras"
              type="button"
            >
              <span className="material-symbols-outlined text-[14px]">crop_free</span>
              <span>Caras</span>
            </button>

            <button
              onClick={() => setSelectionMode('edges')}
              className={`px-2 py-0.5 rounded font-headline-sm text-[11px] flex items-center gap-1 transition-colors ${
                selectionMode === 'edges'
                  ? 'bg-[#0ea5e9] text-[#003751] font-semibold'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#272a33]'
              }`}
              title="Selección de Aristas"
              type="button"
            >
              <span className="material-symbols-outlined text-[14px]">straighten</span>
              <span>Aristas</span>
            </button>

            <button
              onClick={() => setSelectionMode('vertices')}
              className={`px-2 py-0.5 rounded font-headline-sm text-[11px] flex items-center gap-1 transition-colors ${
                selectionMode === 'vertices'
                  ? 'bg-[#0ea5e9] text-[#003751] font-semibold'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#272a33]'
              }`}
              title="Selección de Nodos/Vértices"
              type="button"
            >
              <span className="material-symbols-outlined text-[14px]">grain</span>
              <span>Vértices</span>
            </button>

            <button
              onClick={() => setSelectionMode('volumes')}
              className={`px-2 py-0.5 rounded font-headline-sm text-[11px] flex items-center gap-1 transition-colors ${
                selectionMode === 'volumes'
                  ? 'bg-[#0ea5e9] text-[#003751] font-semibold'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#272a33]'
              }`}
              title="Selección de Volúmenes"
              type="button"
            >
              <span className="material-symbols-outlined text-[14px]">view_in_ar</span>
              <span>Volúmenes</span>
            </button>
          </div>

          <div className="w-px h-4 bg-[#2e3646] mx-1"></div>

          <div className="flex items-center gap-0.5">
            <button
              onClick={() => setClipActive(!clipActive)}
              className={`p-1 rounded text-[14px] transition-colors ${
                clipActive ? 'bg-[#0ea5e9] text-[#003751]' : 'hover:bg-[#272a33] text-[#94a3b8] hover:text-[#7bd0ff]'
              }`}
              title="Plano de Corte Interactivo (Clip Plane)"
              type="button"
            >
              <Scissors className="w-3.5 h-3.5" />
            </button>

            <button
              className="p-1 rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#7bd0ff]"
              title="Medición de Distancias y Calibre"
              type="button"
            >
              <Ruler className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => setWireframeActive(!wireframeActive)}
              className={`p-1 rounded transition-colors ${
                wireframeActive ? 'text-[#7bd0ff]' : 'text-[#64748b]'
              } hover:bg-[#272a33]`}
              title="Modo Alambre / Wireframe"
              type="button"
            >
              <Grid className="w-3.5 h-3.5" />
            </button>

            <button
              className="p-1 rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#7bd0ff]"
              title="Aislar Selección"
              type="button"
            >
              <Filter className="w-3.5 h-3.5" />
            </button>

            <div className="w-px h-4 bg-[#2e3646] mx-1"></div>

            <select
              value={navProfile}
              onChange={(e) => handleNavProfile(e.target.value as NavProfileName)}
              className="bg-[#0b0e17] border border-[#2e3646] rounded px-1.5 py-0.5 text-[10px] text-[#94a3b8] focus:outline-none focus:border-[#7bd0ff]"
              title={`Navegación (${NAV_PROFILES[navProfile].displayName}): izq=select · medio=${NAV_PROFILES[navProfile].middle} · der=${NAV_PROFILES[navProfile].right}`}
            >
              {NAV_PROFILE_NAMES.map((n) => (
                <option key={n} value={n}>{NAV_PROFILES[n].displayName}</option>
              ))}
            </select>
          </div>
        </div>

        {/* ViewCube & Camera Tool Stack (Top Right) */}
        <aside className="absolute top-2 right-2 z-20 flex flex-col items-end gap-1.5">
          <ViewCube onViewChange={handleViewChange} />
          <div className="flex flex-col gap-0.5 bg-[#1f2430]/90 backdrop-blur-md p-1 rounded-lg shadow-md border border-[#2e3646]/60">
            <button
              onClick={resetCamera}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9]"
              title="Zoom Extensión (Fit)"
              type="button"
            >
              <span className="material-symbols-outlined text-[15px]">center_focus_strong</span>
            </button>
            <button
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9]"
              title="Rotar Órbita CAD"
              type="button"
            >
              <span className="material-symbols-outlined text-[15px]">3d_rotation</span>
            </button>
            <button
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9]"
              title="Desplazamiento Pan"
              type="button"
            >
              <span className="material-symbols-outlined text-[15px]">pan_tool</span>
            </button>
          </div>
        </aside>

        {/* 3D Real Viewport (three.js) */}
        <div className="w-full flex-1 relative flex flex-col bg-gradient-to-b from-[#0f1117] via-[#181b24] to-[#10131c] overflow-hidden select-none">
          {(meshError || meshLoading) && (
            <div className="px-3 pt-2 z-10">
              {meshLoading && (
                <div className="text-[10px] text-[#7bd0ff] bg-[#0ea5e9]/10 border border-[#0ea5e9]/30 rounded px-2 py-1">
                  Cargando previsualización de malla…
                </div>
              )}
              {meshError && (
                <div className="text-[10px] text-[#fca5a5] bg-[#ef4444]/10 border border-[#ef4444]/30 rounded px-2 py-1">
                  Error: {meshError}{' '}
                  <button onClick={() => void loadMeshPreview()} className="underline hover:text-white" type="button">
                    Reintentar (Cargar malla)
                  </button>
                </div>
              )}
            </div>
          )}
          <div className="flex-1 relative min-h-[380px]">
            <MeshViewer ref={viewerRef} mesh={previewMesh} wireframe={wireframeActive} color="#8fa3b8" height={460} clip={clipActive} profile={navProfile} onSelect={(s) => setSelPoint(s ? `[${s.point.map((v) => v.toFixed(1)).join(', ')}]` : null)} />
          </div>
          <div className="px-3 pb-1 z-10 flex justify-end">
            <button
              onClick={() => void loadMeshPreview()}
              className="px-2 py-1 rounded bg-[#1f2430] hover:bg-[#272a33] text-[#94a3b8] hover:text-[#7bd0ff] font-label-sm text-[10px] border border-[#2e3646]/50 flex items-center gap-1"
              type="button"
            >
              <RefreshCw className={`w-3 h-3 ${meshLoading ? 'animate-spin' : ''}`} />
              <span>{meshLoading ? 'Cargando malla…' : 'Cargar malla'}</span>
            </button>
          </div>


          {/* Triad Gizmo (Bottom-Left Viewport) */}
          <div className="absolute bottom-2 left-2 z-20 flex items-center gap-1.5 bg-[#1f2430]/85 backdrop-blur-md px-2.5 py-1.5 rounded-lg shadow-md border border-[#2e3646]/60">
            <svg className="w-10 h-10" viewBox="0 0 54 54">
              <line x1="20" y1="36" x2="48" y2="36" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" />
              <polygon points="48,36 43,33 43,39" fill="#ef4444" />
              <text x="50" y="38" fill="#ef4444" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold">X</text>
              <line x1="20" y1="36" x2="20" y2="8" stroke="#10b981" strokeWidth="2" strokeLinecap="round" />
              <polygon points="20,8 17,13 23,13" fill="#10b981" />
              <text x="18" y="6" fill="#10b981" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold">Y</text>
              <line x1="20" y1="36" x2="6" y2="48" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" />
              <polygon points="6,48 11,46 8,43" fill="#38bdf8" />
              <text x="0" y="52" fill="#38bdf8" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold">Z</text>
              <circle cx="20" cy="36" r="2.5" fill="#f1f5f9" />
            </svg>
            <div className="flex flex-col">
              <span className="text-[#f1f5f9] font-label-sm text-[10px] font-bold">WCS Global</span>
              <span className="text-[#64748b] font-label-sm text-[9px]">Vista Isométrica 30°</span>
            </div>
          </div>

          {/* Viewport Scale Legend (Bottom Right) */}
          <div className="absolute bottom-2 right-2 z-20 flex items-center gap-2 bg-[#1f2430]/85 backdrop-blur-md px-2.5 py-1.5 rounded-lg shadow-md font-label-sm text-[10px] border border-[#2e3646]/60">
            <div className="flex flex-col items-end">
              <div className="w-14 h-1 bg-[#94a3b8] rounded-full"></div>
              <span className="text-[#64748b] text-[9px] mt-0.5">50.0 mm</span>
            </div>
            <div className="w-px h-4 bg-[#2e3646]"></div>
            <span className="text-[#10b981] flex items-center gap-1 text-[10px]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
              Malla Activa (Tet4)
            </span>
            {selPoint && (
              <span className="text-[#fbbf24] font-mono text-[10px]">sel {selPoint}</span>
            )}
          </div>
        </div>
      </main>

      {/* RIGHT PANEL: Material Library & CAE Study Inspector */}
      <aside className="w-full xl:w-80 2xl:w-88 flex flex-col gap-2 flex-shrink-0">
        {/* Material Library Card */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md flex flex-col gap-1.5 border border-[#2e3646]/50">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#7bd0ff] text-[16px]">science</span>
              <span className="font-headline-sm text-[13px] text-[#f1f5f9] tracking-tight">Biblioteca de Material</span>
            </div>
            <span className="font-label-sm text-[10px] text-[#7bd0ff] bg-[#32343e] px-1.5 py-0.5 rounded">
              Isótropo
            </span>
          </header>

          {/* Alloy Selector Dropdown */}
          <div className="flex flex-col gap-1 pt-0.5">
            <label className="font-label-sm text-[10px] text-[#64748b]">Aleación / Polímero:</label>
            <div className="relative">
              <select
                value={selectedMaterial.id}
                onChange={(e) => {
                  const mat = materialOptions.find((m) => m.id === e.target.value);
                  if (mat) onSelectMaterial(mat);
                }}
                className="w-full bg-[#1f2430] border border-[#2e3646] rounded px-2.5 py-1.5 font-headline-sm text-[11px] text-[#f1f5f9] appearance-none cursor-pointer focus:border-[#7bd0ff] focus:outline-none pr-7"
              >
                {materialOptions.map((mat) => (
                  <option key={mat.id} value={mat.id}>
                    {mat.name}
                  </option>
                ))}
              </select>
              <span className="material-symbols-outlined text-[#64748b] text-[16px] absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none">
                expand_more
              </span>
            </div>
          </div>

          {/* Constitutive Law Table */}
          <div className="flex flex-col gap-1 pt-1 font-label-md text-[11px]">
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-body-sm text-[11px]">Módulo Young (E):</span>
              <span className="text-[#f1f5f9] font-bold">{selectedMaterial.youngModulusGpa} GPa</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-body-sm text-[11px]">Coef. Poisson (ν):</span>
              <span className="text-[#f1f5f9] font-bold">{selectedMaterial.poissonRatio}</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-body-sm text-[11px]">Límite Elástico (σ_y):</span>
              <span className="text-[#f59e0b] font-bold">{selectedMaterial.yieldStrengthMpa} MPa</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-body-sm text-[11px]">Densidad (ρ):</span>
              <span className="text-[#f1f5f9] font-bold">{selectedMaterial.densityGcm3} g/cm³</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-body-sm text-[11px]">Resistencia Tracción:</span>
              <span className="text-[#f1f5f9] font-bold">{selectedMaterial.tensileStrengthMpa} MPa</span>
            </div>
          </div>
        </section>

        {/* CAE Study Metrics & Physical Properties */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md flex flex-col gap-1.5 border border-[#2e3646]/50">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#7bd0ff] text-[16px]">tune</span>
              <span className="font-headline-sm text-[13px] text-[#f1f5f9] tracking-tight">Estudio CAE & Físicas</span>
            </div>
            <span className="font-label-sm text-[10px] text-[#10b981] bg-[#32343e] px-1.5 py-0.5 rounded">
              Listo FEA
            </span>
          </header>

          <div className="flex flex-col gap-1.5 pt-0.5">
            <div className="flex items-center justify-between bg-[#1f2430]/60 p-1.5 rounded">
              <div className="flex flex-col">
                <span className="text-[#64748b] font-body-sm text-[10px]">Tipo de Análisis:</span>
                <span className="text-[#f1f5f9] font-headline-sm text-[11px]">Elástico Lineal Estático</span>
              </div>
              <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">balance</span>
            </div>

            <div className="grid grid-cols-2 gap-1.5">
              <div className="bg-[#1f2430]/40 p-1.5 rounded flex flex-col">
                <span className="font-label-sm text-[10px] text-[#64748b]">Masa Inicial:</span>
                <span className="font-label-lg text-[13px] text-[#f1f5f9] font-bold mt-0.5">3.42 kg</span>
                <span className="text-[9px] font-label-sm text-[#64748b] mt-0.5">100% Volumen</span>
              </div>

              <div className="bg-[#1f2430]/40 p-1.5 rounded flex flex-col">
                <span className="font-label-sm text-[10px] text-[#64748b]">Volumen Total:</span>
                <span className="font-label-lg text-[13px] text-[#f1f5f9] font-bold mt-0.5">1,217 cm³</span>
                <span className="text-[9px] font-label-sm text-[#10b981] mt-0.5">Sólido Hermético</span>
              </div>
            </div>

            {/* Optimization Objective Brief Preview */}
            <div className="bg-[#32343e]/40 p-2 rounded flex flex-col gap-1 border border-[#2e3646]/30">
              <div className="flex items-center justify-between text-body-sm text-[11px]">
                <span className="text-[#bec8d2] font-medium">Meta de Reducción SIMP:</span>
                <span className="text-[#7bd0ff] font-label-sm text-[11px] font-bold">VF = 0.35 (-65%)</span>
              </div>
              <div className="flex justify-between items-center text-[10px] font-label-sm text-[#64748b]">
                <span>Masa proyectada optimizada:</span>
                <span className="text-[#10b981] font-bold">~1.20 kg</span>
              </div>
            </div>
          </div>
        </section>

        {/* Primary High-Impact CTA Button Card */}
        <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 mt-auto border border-[#2e3646]">
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center justify-between font-label-sm text-[10px] text-[#94a3b8]">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                BCs Asignadas: 1 Fijación / 1 Carga
              </span>
              <span className="text-[#f1f5f9] font-bold">100% OK</span>
            </div>
            <p className="text-[#64748b] font-body-sm text-[11px] leading-tight">
              El mallador discretizará el espacio no de diseño y generará la matriz de rigidez global K.
            </p>
          </div>

          <button
            onClick={onAdvanceToMesh}
            className="w-full py-2 px-3 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-headline-sm text-[13px] rounded-lg shadow-lg hover:shadow-cyan-500/20 flex items-center justify-center gap-2 transition-all font-semibold transform active:scale-98"
            type="button"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>Validar Condiciones & Generar Malla</span>
          </button>
        </section>
      </aside>
    </div>
  );
};
