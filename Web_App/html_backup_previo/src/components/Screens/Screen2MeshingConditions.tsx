import React, { useState } from 'react';
import { ViewCube } from '../ViewCube';
import { backend } from '../../lib/bridge';
import {
  Grid,
  Layers,
  Scissors,
  Eye,
  CheckCircle2,
  Calculator,
  RefreshCw,
  Sliders,
  ZoomIn,
  Move,
  RotateCw,
} from 'lucide-react';

interface Screen2Props {
  onAdvanceToFea: () => void;
  activeFilename: string;
}

export const Screen2MeshingConditions: React.FC<Screen2Props> = ({
  onAdvanceToFea,
  activeFilename,
}) => {
  const [elementShrink, setElementShrink] = useState<number>(0);
  const [showNodeCloud, setShowNodeCloud] = useState<boolean>(true);
  const [meshAlgorithm, setMeshAlgorithm] = useState<string>('delaunay');
  const [isMeshing, setIsMeshing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'mesh' | 'bcs'>('mesh');
  const [loadMagnitude, setLoadMagnitude] = useState<number>(4500);
  const [meshStatus, setMeshStatus] = useState<string | null>(null);
  const [meshError, setMeshError] = useState<string | null>(null);
  void activeTab;
  void setActiveTab;

  const handleGenerateMesh = async () => {
    setIsMeshing(true);
    setMeshStatus(null);
    setMeshError(null);
    try {
      const r = (await backend.generateMesh({ target_element_size: 6.0 })) as {
        ok: boolean;
        error?: string;
      };
      if (!r.ok) {
        setMeshError(r.error ?? 'generateMesh devolvió ok=false');
        return;
      }
      const b = (await backend.setBoundaries({
        bottom_axis: 2,
        load_dir: [0, 0, 1],
        magnitude: loadMagnitude,
      })) as { ok: boolean; error?: string };
      if (!b.ok) {
        setMeshError(b.error ?? 'setBoundaries devolvió ok=false');
        return;
      }
      setMeshStatus('Malla generada y condiciones de borde aplicadas.');
    } catch (e) {
      setMeshError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsMeshing(false);
    }
  };

  return (
    <div className="w-full flex flex-col gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* Subheader Breadcrumb & Operational Mode Status Strip */}
      <div className="w-full bg-[#181b24] px-3 py-1.5 rounded flex flex-wrap items-center justify-between gap-2 border border-[#2e3646]/60">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">ETAPA:</span>
            <span className="font-label-sm text-[11px] text-[#f1f5f9] font-medium uppercase tracking-wide">
              2. MALLADO CONFORME & ASIGNACIÓN DE GRUPOS FÍSICOS
            </span>
          </div>
          <span className="w-1 h-1 rounded-full bg-[#2e3646]"></span>
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">MOTOR:</span>
            <span className="font-label-sm text-[11px] text-[#7bd0ff]">Gmsh v4.12 (OpenCASCADE Engine)</span>
          </div>
          <span className="w-1 h-1 rounded-full bg-[#2e3646]"></span>
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">DISCRETIZACIÓN:</span>
            <span className="font-label-sm text-[11px] text-[#10b981]">215,410 Tetraedros Tet4</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-label-sm text-[10px] text-[#10b981] flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
            Jacobiano Óptimo (0.84)
          </span>
          <button
            onClick={handleGenerateMesh}
            className="bg-[#1f2430] hover:bg-[#272a33] border border-[#2e3646] px-2.5 py-1 rounded flex items-center gap-1 text-[#f1f5f9] hover:text-[#7bd0ff] font-label-sm text-[11px] transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${isMeshing ? 'animate-spin text-[#7bd0ff]' : ''}`} />
            <span>Remallar</span>
          </button>
        </div>
      </div>

      {/* Main 3-Pane Area */}
      <div className="grid grid-cols-12 gap-2 flex-1">
        {/* LEFT PANEL: Mesher Properties & Quality Metric */}
        <aside className="col-span-12 xl:col-span-3 flex flex-col gap-2">
          {/* Card: Gmsh Discretization Engine */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Grid className="w-4 h-4 text-[#7bd0ff]" />
                <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Configuración Gmsh</span>
              </div>
              <span className="font-label-sm text-[10px] text-[#7bd0ff] bg-[#32343e] px-1.5 py-0.5 rounded">
                Tet4
              </span>
            </div>

            <div className="flex flex-col gap-2 text-body-sm">
              <div className="flex flex-col gap-1">
                <label className="font-label-sm text-[10px] text-[#64748b]">Algoritmo Volumétrico 3D:</label>
                <select
                  value={meshAlgorithm}
                  onChange={(e) => setMeshAlgorithm(e.target.value)}
                  className="w-full bg-[#1f2430] border border-[#2e3646] rounded px-2 py-1 text-[11px] text-[#f1f5f9] focus:outline-none"
                >
                  <option value="delaunay">Frontal-Delaunay 3D (Recomendado)</option>
                  <option value="hxt">HXT Paralelo Multi-núcleo</option>
                  <option value="mmg3d">MMG3D Optimización de Calidad</option>
                </select>
              </div>

              {/* Quality Distribution Histogram */}
              <div className="p-2 rounded bg-[#0b0e17] border border-[#2e3646]/40 flex flex-col gap-1.5">
                <div className="flex items-center justify-between font-label-sm text-[10px]">
                  <span className="text-[#94a3b8]">Distribución Jacobiana:</span>
                  <span className="text-[#10b981] font-bold">&gt; 0.70 (94.2% els)</span>
                </div>

                {/* Histogram Bars */}
                <div className="h-14 w-full flex items-end gap-1 pt-2 px-1">
                  <div className="flex-1 bg-[#ef4444]/60 h-2 rounded-t" title="< 0.3: 0.1%"></div>
                  <div className="flex-1 bg-[#f59e0b]/70 h-4 rounded-t" title="0.3-0.5: 1.2%"></div>
                  <div className="flex-1 bg-[#7bd0ff]/70 h-8 rounded-t" title="0.5-0.7: 4.5%"></div>
                  <div className="flex-1 bg-[#10b981] h-12 rounded-t" title="0.7-0.9: 68.2%"></div>
                  <div className="flex-1 bg-[#10b981] h-14 rounded-t" title="0.9-1.0: 26.0%"></div>
                </div>

                <div className="flex justify-between font-label-sm text-[9px] text-[#64748b]">
                  <span>0.0 (Pobre)</span>
                  <span>0.5</span>
                  <span>1.0 (Ideal)</span>
                </div>
              </div>

              {/* Geometric Fidelity Badges */}
              <div className="grid grid-cols-2 gap-1.5 text-[10px] font-label-sm">
                <div className="bg-[#1f2430] p-1.5 rounded flex flex-col">
                  <span className="text-[#64748b]">Nodos de Borde:</span>
                  <span className="text-[#f1f5f9] font-bold mt-0.5">14,820</span>
                </div>
                <div className="bg-[#1f2430] p-1.5 rounded flex flex-col">
                  <span className="text-[#64748b]">Tet4 Interiores:</span>
                  <span className="text-[#7bd0ff] font-bold mt-0.5">200,590</span>
                </div>
              </div>
            </div>
          </section>

          {/* Card: Element Shrinkage & Slicing */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 border border-[#2e3646]/50">
            <span className="font-headline-sm text-[12px] text-[#f1f5f9]">Inspección Interna de Tetraedros</span>
            <div className="flex flex-col gap-1">
              <div className="flex justify-between font-label-sm text-[10px]">
                <span className="text-[#94a3b8]">Contracción Elemental (Shrink):</span>
                <span className="text-[#7bd0ff] font-bold">{(elementShrink * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="0.5"
                step="0.05"
                value={elementShrink}
                onChange={(e) => setElementShrink(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-[#32343e] rounded cursor-pointer accent-[#0ea5e9]"
              />
              <span className="text-[9px] font-label-sm text-[#64748b]">
                Separa visualmente las caras de cada elemento para inspeccionar porosidad y calidad.
              </span>
            </div>

            <div className="flex items-center justify-between pt-1 border-t border-[#2e3646]/50">
              <span className="font-body-sm text-[11px] text-[#94a3b8]">Nube de Nodos FEA:</span>
              <button
                onClick={() => setShowNodeCloud(!showNodeCloud)}
                className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                  showNodeCloud ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'bg-[#1f2430] text-[#64748b]'
                }`}
              >
                {showNodeCloud ? 'Visible' : 'Oculto'}
              </button>
            </div>
          </section>
        </aside>

        {/* CENTRAL AREA: 3D Volumetric Mesh Viewport */}
        <main className="col-span-12 xl:col-span-6 flex flex-col relative rounded-lg bg-[#0b0e17] overflow-hidden shadow-2xl border border-[#2e3646] min-h-[540px]">
          {/* Top Mesh Control Ribbon */}
          <div className="absolute top-2 left-2 z-20 flex items-center gap-1 bg-[#1f2430]/90 backdrop-blur-md px-2 py-1 rounded-lg shadow-md border border-[#2e3646]/60">
            <span className="font-label-sm text-[11px] text-[#7bd0ff] font-medium">Malla 3D Tet4 Conforme</span>
            <div className="w-px h-3.5 bg-[#2e3646] mx-1"></div>
            <span className="font-label-sm text-[10px] text-[#94a3b8]">215,410 elementos</span>
          </div>

          <aside className="absolute top-2 right-2 z-20">
            <ViewCube />
          </aside>

          {/* Interactive 3D Mesh Stage SVG Graphic */}
          <div className="w-full flex-1 flex items-center justify-center relative bg-gradient-to-b from-[#0f1117] via-[#141721] to-[#10131c] overflow-hidden">
            {/* Perspective grid */}
            <svg className="absolute inset-0 w-full h-full opacity-20 pointer-events-none">
              <defs>
                <pattern id="meshGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#2e3646" strokeWidth="0.75" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#meshGrid)" />
            </svg>

            <div className="relative w-full max-w-xl h-[440px] flex items-center justify-center">
              <svg className="w-full h-full drop-shadow-2xl" viewBox="0 0 520 400">
                <defs>
                  <linearGradient id="meshSolid" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#1e293b" />
                    <stop offset="100%" stopColor="#0f172a" />
                  </linearGradient>
                </defs>

                {/* Base Geometry */}
                <polygon
                  points="140,240 220,160 360,160 420,240 370,320 190,320"
                  fill="url(#meshSolid)"
                  stroke="#38bdf8"
                  strokeWidth="1.2"
                />

                {/* Dense Tetrahedral Mesh Facets Wireframe */}
                <g fill="none" stroke="#7bd0ff" strokeWidth="0.8" strokeOpacity="0.45">
                  {/* Outer shell triangles */}
                  <path d="M 140,240 L 190,200 L 220,160 Z" />
                  <path d="M 190,200 L 260,160 L 220,160 Z" />
                  <path d="M 260,160 L 310,160 L 280,210 Z" />
                  <path d="M 310,160 L 360,160 L 340,210 Z" />
                  <path d="M 360,160 L 420,240 L 370,240 Z" />
                  <path d="M 420,240 L 370,320 L 340,260 Z" />
                  <path d="M 370,320 L 300,320 L 310,250 Z" />
                  <path d="M 300,320 L 240,320 L 250,260 Z" />
                  <path d="M 240,320 L 190,320 L 190,260 Z" />
                  <path d="M 190,320 L 140,240 L 170,260 Z" />

                  {/* Internal cross tetrahedra diagonals */}
                  <path d="M 190,200 L 250,210 L 190,260 Z" />
                  <path d="M 250,210 L 280,210 L 250,260 Z" />
                  <path d="M 280,210 L 340,210 L 310,250 Z" />
                  <path d="M 340,210 L 370,240 L 340,260 Z" />
                  <path d="M 250,210 L 310,250 L 250,260 Z" />
                  <path d="M 190,200 L 280,210 L 220,160 Z" />
                  <path d="M 280,210 L 370,240 L 310,250 Z" />
                  <path d="M 170,260 L 250,260 L 190,320 Z" />
                  <path d="M 250,260 L 310,250 L 300,320 Z" />
                </g>

                {/* Node Points Cloud */}
                {showNodeCloud && (
                  <g fill="#7bd0ff" opacity="0.8">
                    <circle cx="140" cy="240" r="2.5" />
                    <circle cx="190" cy="200" r="2" />
                    <circle cx="220" cy="160" r="2.5" />
                    <circle cx="260" cy="160" r="2" />
                    <circle cx="310" cy="160" r="2" />
                    <circle cx="360" cy="160" r="2.5" />
                    <circle cx="420" cy="240" r="2.5" />
                    <circle cx="370" cy="320" r="2.5" />
                    <circle cx="300" cy="320" r="2" />
                    <circle cx="240" cy="320" r="2" />
                    <circle cx="190" cy="320" r="2.5" />
                    <circle cx="250" cy="210" r="2" />
                    <circle cx="280" cy="210" r="2" />
                    <circle cx="340" cy="210" r="2" />
                    <circle cx="310" cy="250" r="2" />
                    <circle cx="250" cy="260" r="2" />
                    <circle cx="190" cy="260" r="2" />
                  </g>
                )}

                {/* Boundary Anchors (Encastre Base) */}
                <g transform="translate(170, 310)">
                  <polygon points="0,0 -8,12 8,12" fill="#0ea5e9" />
                  <line x1="-10" y1="13" x2="10" y2="13" stroke="#7bd0ff" strokeWidth="2" />
                  <text x="0" y="24" textAnchor="middle" fill="#7bd0ff" fontSize="8" fontFamily="JetBrains Mono">
                    Ux=Uy=Uz=0
                  </text>
                </g>
                <g transform="translate(330, 310)">
                  <polygon points="0,0 -8,12 8,12" fill="#0ea5e9" />
                  <line x1="-10" y1="13" x2="10" y2="13" stroke="#7bd0ff" strokeWidth="2" />
                </g>

                {/* Traction Load Vector */}
                <g transform="translate(290, 160)">
                  <line x1="0" y1="0" x2="0" y2="-55" stroke="#ffb95f" strokeWidth="3" strokeLinecap="round" />
                  <polygon points="0,-65 -6,-50 6,-50" fill="#ffb95f" />
                  <rect x="-60" y="-85" width="120" height="16" rx="3" fill="#181b24" stroke="#ffb95f" strokeWidth="1" />
                  <text x="0" y="-74" textAnchor="middle" fill="#ffb95f" fontSize="8" fontFamily="JetBrains Mono" fontWeight="bold">
                    F = 4,500 N
                  </text>
                </g>

                {/* Preserved Zone Overlay */}
                <rect x="250" y="145" width="80" height="35" rx="4" fill="#10b981" fillOpacity="0.2" stroke="#10b981" strokeDasharray="3 3" />
                <text x="290" y="140" textAnchor="middle" fill="#10b981" fontSize="8" fontFamily="JetBrains Mono">
                  Grupo Físico: SAFE
                </text>
              </svg>
            </div>

            {/* Bottom Left WCS Triad */}
            <div className="absolute bottom-2 left-2 z-20 flex items-center gap-1.5 bg-[#1f2430]/85 backdrop-blur-md px-2.5 py-1.5 rounded-lg shadow-md border border-[#2e3646]/60">
              <span className="font-label-sm text-[10px] text-[#f1f5f9] font-bold">WCS Global</span>
              <span className="text-[#64748b] text-[10px]">|</span>
              <span className="font-label-sm text-[10px] text-[#10b981]">Conforme 100%</span>
            </div>
          </div>
        </main>

        {/* RIGHT PANEL: Physical Groups & Boundary Conditions Table */}
        <aside className="col-span-12 xl:col-span-3 flex flex-col gap-2">
          {/* Physical Groups & Boundary Conditions Card */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Grupos Físicos & BCs</span>
              <span className="px-1.5 py-0.5 rounded bg-[#10b981]/15 text-[#10b981] font-label-sm text-[10px]">
                3 Asignadas
              </span>
            </div>

            <div className="flex flex-col gap-1.5 text-[11px]">
              {/* Group 1 */}
              <div className="p-2 rounded bg-[#1f2430] border border-[#2e3646]/60 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="text-[#7bd0ff] font-medium flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#0ea5e9]"></span>
                    Fijación Base (Encastre)
                  </span>
                  <span className="font-label-sm text-[10px] text-[#94a3b8]">2,410 nodos</span>
                </div>
                <span className="text-[#64748b] font-label-sm text-[10px]">Ux = Uy = Uz = 0.0 mm</span>
              </div>

              {/* Group 2 */}
              <div className="p-2 rounded bg-[#1f2430] border border-[#2e3646]/60 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="text-[#ffb95f] font-medium flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#ffb95f]"></span>
                    Carga Tracción Nodal
                  </span>
                  <span className="font-label-sm text-[10px] text-[#94a3b8]">840 nodos</span>
                </div>
                <span className="text-[#64748b] font-label-sm text-[10px]">Fz = -4,500 N, Fy = 1,200 N</span>
                <label className="font-label-sm text-[10px] text-[#64748b] flex items-center gap-1 mt-1">
                  Magnitud (N):
                  <input
                    type="number"
                    value={loadMagnitude}
                    onChange={(e) => setLoadMagnitude(parseFloat(e.target.value) || 0)}
                    className="w-24 bg-[#0b0e17] border border-[#2e3646] rounded px-1.5 py-0.5 text-[#f1f5f9] text-[10px]"
                  />
                </label>
              </div>

              {/* Group 3 */}
              <div className="p-2 rounded bg-[#1f2430] border border-[#10b981]/30 flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="text-[#10b981] font-medium flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#10b981]"></span>
                    Subdominio Preservado
                  </span>
                  <span className="font-label-sm text-[10px] text-[#10b981]">ρ = 1.0 (Fijo)</span>
                </div>
                <span className="text-[#64748b] font-label-sm text-[10px]">14,200 elementos no de diseño</span>
              </div>
            </div>
          </section>

          {/* Pre-computation of Element Stiffness Matrices Ke0 */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-1.5 border border-[#2e3646]/50">
            <span className="font-headline-sm text-[12px] text-[#f1f5f9]">Matrices Ke0 Precomputadas</span>
            <div className="p-2 rounded bg-[#0b0e17] border border-[#2e3646]/30 flex flex-col gap-1 font-label-sm text-[10px]">
              <div className="flex justify-between">
                <span className="text-[#64748b]">Integración Gauss:</span>
                <span className="text-[#f1f5f9]">1 Punto (Exacta Tet4)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">Tamaño Ke:</span>
                <span className="text-[#7bd0ff]">12 x 12 (3 GDL/nodo)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">Memoria Matriz K:</span>
                <span className="text-[#10b981]">148.5 MB (Sparse CSR)</span>
              </div>
            </div>
          </section>

          {/* Action Button: Go to FEA */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 mt-auto border border-[#2e3646]">
            <div className="flex items-center justify-between font-label-sm text-[10px] text-[#94a3b8]">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />
                Malla Conforme Lista para Solver
              </span>
            </div>
            {meshStatus && (
              <div className="text-[10px] text-[#10b981] bg-[#10b981]/10 border border-[#10b981]/30 rounded px-2 py-1">{meshStatus}</div>
            )}
            {meshError && (
              <div className="text-[10px] text-[#fca5a5] bg-[#ef4444]/10 border border-[#ef4444]/30 rounded px-2 py-1">Error: {meshError}</div>
            )}
            {isMeshing && (
              <div className="text-[10px] text-[#7bd0ff]">Generando malla y aplicando BCs...</div>
            )}
            <button
              onClick={onAdvanceToFea}
              className="w-full py-2 px-3 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-headline-sm text-[13px] rounded-lg shadow-lg flex items-center justify-center gap-2 transition-all font-semibold"
              type="button"
            >
              <Calculator className="w-4 h-4" />
              <span>Resolver FEA (K·u = F)</span>
            </button>
          </section>
        </aside>
      </div>
    </div>
  );
};
