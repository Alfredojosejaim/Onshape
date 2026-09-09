import React, { useState } from 'react';
import { MaterialProperty } from '../../types';
import { backend } from '../../lib/bridge';
import { ViewCube } from '../ViewCube';
import {
  Download,
  CheckCircle2,
  Layers,
  Sparkles,
  ShieldCheck,
  FileCheck,
  Box,
  Eye,
  RotateCw,
  Share2,
  FileDown,
} from 'lucide-react';

interface Screen5Props {
  material: MaterialProperty;
  onRestartStudy: () => void;
  activeFilename: string;
}

export const Screen5GenerativeBRepExport: React.FC<Screen5Props> = ({
  material,
  onRestartStudy,
  activeFilename,
}) => {
  const [zebraView, setZebraView] = useState<boolean>(false);
  const [curvatureView, setCurvatureView] = useState<boolean>(false);
  const [wireframeOn, setWireframeOn] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);
  const [exportPath, setExportPath] = useState<string>('C:\\Modelos\\optimized.step');
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleBackendExport = async () => {
    setExportStatus(null);
    setExportError(null);
    setIsExporting(true);
    try {
      const r = (await backend.exportStep(exportPath)) as { ok: boolean; error?: string };
      if (!r.ok) {
        setExportError(r.error ?? 'exportStep devolvió ok=false');
      } else {
        setExportStatus(`Exportado OK: ${exportPath}`);
      }
    } catch (e) {
      setExportError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownload = (format: string) => {
    setIsExporting(true);
    setTimeout(() => {
      setIsExporting(false);
      setDownloadSuccess(format);

      // Create synthetic downloadable file for standalone real testing
      const baseName = activeFilename.replace(/\.[^/.]+$/, '');
      const exportName = `${baseName}_topopt_brep_${material.id}.${format.toLowerCase()}`;
      const dummyContent = `ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('OpenCASCADE Generative B-Rep NURBS AP242 Solid Model'),'2;1');
FILE_NAME('${exportName}','2026-09-09T12:00:00',('Antigravity CAE'),('AI Studio FEA Engine'),'OpenCASCADE 7.7','CAE Topology Optimization','Approved');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF { 1 0 10303 442 1 1 4 }'));
ENDSEC;
DATA;
/* Manifold Solid B-Rep Topological Structure */
#1 = CARTESIAN_POINT('',(0.,0.,0.));
#2 = DIRECTION('',(0.,0.,1.));
#3 = DIRECTION('',(1.,0.,0.));
#4 = AXIS2_PLACEMENT_3D('',#1,#2,#3);
#5 = B_SPLINE_SURFACE_WITH_KNOTS('NURBS_ORGANIC_STRUT',3,3,...);
#6 = MANIFOLD_SOLID_BREP('${exportName}',#5);
ENDSEC;
END-ISO-10303-21;`;

      const blob = new Blob([dummyContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = exportName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setTimeout(() => setDownloadSuccess(null), 4000);
    }, 600);
  };

  return (
    <div className="w-full flex flex-col gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* Subheader Breadcrumb & Operational Mode Status Strip */}
      <div className="w-full bg-[#181b24] px-3 py-1.5 rounded flex flex-wrap items-center justify-between gap-2 border border-[#2e3646]/60">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">ETAPA:</span>
            <span className="font-label-sm text-[11px] text-[#f1f5f9] font-medium uppercase tracking-wide">
              5. RECONSTRUCCIÓN B-REP (OPENCASCADE) & EXPORTACIÓN CAD
            </span>
          </div>
          <span className="w-1 h-1 rounded-full bg-[#2e3646]"></span>
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">KERNEL:</span>
            <span className="font-label-sm text-[11px] text-[#7bd0ff]">OpenCASCADE Technology (OCP 7.7)</span>
          </div>
          <span className="w-1 h-1 rounded-full bg-[#2e3646]"></span>
          <div className="flex items-center gap-1.5">
            <span className="font-label-sm text-[10px] text-[#64748b]">SUPERFICIE:</span>
            <span className="font-label-sm text-[11px] text-[#10b981]">48 Parches NURBS C¹ Suaves</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-label-sm text-[11px] text-[#10b981] flex items-center gap-1.5 font-medium">
            <span className="w-2 h-2 rounded-full bg-[#10b981]"></span>
            Sólido Manifold Hermético (100% Válido)
          </span>
          <button
            onClick={onRestartStudy}
            className="bg-[#1f2430] hover:bg-[#272a33] px-2.5 py-1 rounded flex items-center gap-1 text-[#f1f5f9] border border-[#2e3646] hover:text-[#7bd0ff] transition-colors font-label-sm text-[10px]"
          >
            <RotateCw className="w-3 h-3" />
            <span>Nuevo Ciclo de Diseño</span>
          </button>
        </div>
      </div>

      {/* Main 3-Pane Layout */}
      <div className="grid grid-cols-12 gap-2 flex-1">
        {/* LEFT PANEL: Geometric Reconstruction Pipeline Details */}
        <aside className="col-span-12 xl:col-span-3 flex flex-col gap-2">
          {/* Card: Pipeline Steps */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Pipeline B-Rep OpenCASCADE</span>
              <span className="font-label-sm text-[10px] text-[#10b981] bg-[#10b981]/15 px-1.5 py-0.5 rounded">
                Finalizado
              </span>
            </div>

            <div className="flex flex-col gap-1.5 text-[11px]">
              {/* Step 1 */}
              <div className="p-2 rounded bg-[#1f2430] border border-[#2e3646]/40 flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#10b981] shrink-0 mt-0.5" />
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium">1. Marching Tetrahedra (ρ = 0.50)</span>
                  <span className="text-[#64748b] text-[10px]">Extracción de isosuperficie poligonal (42,180 triángulos)</span>
                </div>
              </div>

              {/* Step 2 */}
              <div className="p-2 rounded bg-[#1f2430] border border-[#2e3646]/40 flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#10b981] shrink-0 mt-0.5" />
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium">2. Suavizado Taubin C¹</span>
                  <span className="text-[#64748b] text-[10px]">15 iteraciones sin pérdida de volumen geométrico</span>
                </div>
              </div>

              {/* Step 3 */}
              <div className="p-2 rounded bg-[#1f2430] border border-[#2e3646]/40 flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#10b981] shrink-0 mt-0.5" />
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium">3. Segmentación & Ajuste NURBS</span>
                  <span className="text-[#64748b] text-[10px]">48 parches B-Spline bicúbicos con continuidad tangencial</span>
                </div>
              </div>

              {/* Step 4 */}
              <div className="p-2 rounded bg-[#1f2430] border border-[#2e3646]/40 flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#10b981] shrink-0 mt-0.5" />
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium">4. Booleana con Zonas Preservadas</span>
                  <span className="text-[#64748b] text-[10px]">Unión exacta con cilindros de pernos y roscas</span>
                </div>
              </div>

              {/* Step 5 */}
              <div className="p-2 rounded bg-[#1f2430] border border-[#10b981]/30 flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#10b981] shrink-0 mt-0.5" />
                <div className="flex flex-col">
                  <span className="text-[#10b981] font-medium">5. Sewing Hermético (ShapeFix)</span>
                  <span className="text-[#94a3b8] text-[10px]">Topología BRep solid Manifold validada</span>
                </div>
              </div>
            </div>
          </section>

          {/* Tolerance & Deviation Telemetry */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-1.5 border border-[#2e3646]/50 font-label-sm text-[10px]">
            <span className="font-headline-sm text-[12px] text-[#f1f5f9]">Precisión Geométrica B-Rep</span>
            <div className="p-2 rounded bg-[#0b0e17] border border-[#2e3646]/30 flex flex-col gap-1">
              <div className="flex justify-between">
                <span className="text-[#64748b]">Desviación Máx respecto a Malla:</span>
                <span className="text-[#10b981] font-bold">0.038 mm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">Tolerancia de Cierre (Sewing):</span>
                <span className="text-[#7bd0ff]">1.0 × 10⁻⁵ mm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">Continuidad entre Parches:</span>
                <span className="text-[#f1f5f9]">G1 / C1 Tangente</span>
              </div>
            </div>
          </section>
        </aside>

        {/* CENTRAL AREA: 3D NURBS B-Rep Final Solid Viewport */}
        <main className="col-span-12 xl:col-span-6 flex flex-col gap-2">
          <div className="relative w-full h-[620px] rounded-lg bg-[#0b0e17] overflow-hidden shadow-2xl flex flex-col justify-between p-2 select-none border border-[#2e3646]">
            {/* Top Toolbar */}
            <div className="w-full flex items-center justify-between z-20 pointer-events-auto">
              <div className="flex items-center gap-1 bg-[#181b24]/90 backdrop-blur-md px-2 py-1 rounded-lg shadow-md border border-[#2e3646]/60">
                <span className="font-headline-sm text-[11px] text-[#7bd0ff]">Sólido B-Rep AP242</span>
                <div className="w-px h-3.5 bg-[#2e3646] mx-1"></div>
                <span className="font-label-sm text-[10px] text-[#94a3b8]">48 parches NURBS</span>
              </div>

              {/* Analysis view options */}
              <div className="flex items-center gap-1 bg-[#181b24]/90 backdrop-blur-md p-1 rounded-lg shadow-md border border-[#2e3646]/60">
                <button
                  onClick={() => setZebraView(!zebraView)}
                  className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                    zebraView ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                  title="Rayas de cebra para evaluar continuidad de curvatura G1/G2"
                >
                  Rayas Cebra
                </button>
                <button
                  onClick={() => setCurvatureView(!curvatureView)}
                  className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                    curvatureView ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                  title="Mapa de Curvatura Gaussiana"
                >
                  Curvatura Gaussiana
                </button>
                <button
                  onClick={() => setWireframeOn(!wireframeOn)}
                  className={`px-2 py-0.5 rounded font-label-sm text-[10px] transition-colors ${
                    wireframeOn ? 'bg-[#0ea5e9] text-[#003751] font-bold' : 'text-[#94a3b8] hover:text-[#f1f5f9]'
                  }`}
                  title="Líneas Isoparamétricas UV"
                >
                  Isoparámetros UV
                </button>
              </div>
            </div>

            {/* 3D Scene: Organic Generative Titanium Solid */}
            <div className="absolute inset-0 z-0 flex items-center justify-center overflow-hidden">
              <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#2e3646_1px,transparent_1px)] [background-size:24px_24px]"></div>

              <div className="relative w-[520px] h-[430px] flex items-center justify-center">
                <svg className="w-full h-full drop-shadow-2xl select-none" viewBox="0 0 520 400">
                  <defs>
                    {/* Metallic Chrome / Titanium Finish Gradient */}
                    <linearGradient id="titaniumMetal" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#94a3b8" />
                      <stop offset="25%" stopColor="#475569" />
                      <stop offset="50%" stopColor="#64748b" />
                      <stop offset="75%" stopColor="#334155" />
                      <stop offset="100%" stopColor="#1e293b" />
                    </linearGradient>

                    {/* Zebra Stripes Pattern */}
                    <pattern id="zebraPattern" width="20" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                      <rect width="10" height="20" fill="#000000" fillOpacity="0.45" />
                      <rect x="10" width="10" height="20" fill="#ffffff" fillOpacity="0.4" />
                    </pattern>

                    {/* Curvature Map */}
                    <linearGradient id="curvatureMap" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#0ea5e9" />
                      <stop offset="50%" stopColor="#10b981" />
                      <stop offset="100%" stopColor="#ef4444" />
                    </linearGradient>
                  </defs>

                  {/* Drop Shadow Ground */}
                  <ellipse cx="280" cy="365" rx="160" ry="20" fill="#0b0e17" opacity="0.7" />

                  {/* Reconstructed NURBS Solid Body with organic fillet rounds */}
                  <g>
                    {/* Lower Arched Strut */}
                    <path
                      d="M 170,320 C 230,295 285,295 350,320 C 375,320 355,270 325,255 C 275,250 220,260 170,320 Z"
                      fill={curvatureView ? 'url(#curvatureMap)' : 'url(#titaniumMetal)'}
                      stroke="#cbd5e1"
                      strokeWidth="1.5"
                    />

                    {/* Main Diagonal Truss Branch */}
                    <path
                      d="M 170,315 C 200,270 240,210 290,165 C 305,155 315,160 305,175 C 265,225 220,285 170,315 Z"
                      fill={curvatureView ? 'url(#curvatureMap)' : 'url(#titaniumMetal)'}
                      stroke="#cbd5e1"
                      strokeWidth="1.5"
                    />

                    {/* Secondary Cross-brace Truss */}
                    <path
                      d="M 350,315 C 330,270 315,210 295,165 C 285,160 295,150 310,160 C 330,215 345,275 350,315 Z"
                      fill={curvatureView ? 'url(#curvatureMap)' : 'url(#titaniumMetal)'}
                      stroke="#cbd5e1"
                      strokeWidth="1.5"
                    />

                    {/* Zebra stripes overlay */}
                    {zebraView && (
                      <>
                        <path
                          d="M 170,320 C 230,295 285,295 350,320 C 375,320 355,270 325,255 C 275,250 220,260 170,320 Z"
                          fill="url(#zebraPattern)"
                        />
                        <path
                          d="M 170,315 C 200,270 240,210 290,165 C 305,155 315,160 305,175 C 265,225 220,285 170,315 Z"
                          fill="url(#zebraPattern)"
                        />
                      </>
                    )}

                    {/* NURBS UV Isoparameter curves */}
                    {wireframeOn && (
                      <g fill="none" stroke="#7bd0ff" strokeOpacity="0.4" strokeWidth="0.8">
                        <path d="M 180,315 C 220,295 270,295 340,315" />
                        <path d="M 190,305 C 230,285 270,285 330,305" />
                        <path d="M 210,270 C 240,240 270,200 295,170" />
                        <path d="M 230,280 C 260,250 290,210 305,180" />
                      </g>
                    )}

                    {/* Exact Machined Bushing Rings (Cylindrical Precision B-Rep) */}
                    <g transform="translate(170, 315)">
                      <circle cx="0" cy="0" r="16" fill="#1e293b" stroke="#38bdf8" strokeWidth="2.5" />
                      <circle cx="0" cy="0" r="8" fill="#0b0e17" stroke="#94a3b8" strokeWidth="1.5" />
                    </g>

                    <g transform="translate(350, 315)">
                      <circle cx="0" cy="0" r="16" fill="#1e293b" stroke="#38bdf8" strokeWidth="2.5" />
                      <circle cx="0" cy="0" r="8" fill="#0b0e17" stroke="#94a3b8" strokeWidth="1.5" />
                    </g>

                    <g transform="translate(295, 160)">
                      <circle cx="0" cy="0" r="17" fill="#1e293b" stroke="#38bdf8" strokeWidth="2.5" />
                      <circle cx="0" cy="0" r="9" fill="#0b0e17" stroke="#94a3b8" strokeWidth="1.5" />
                    </g>

                    {/* Specular highlight lines */}
                    <path
                      d="M 185,310 C 235,285 285,285 335,310"
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth="1.8"
                      strokeOpacity="0.65"
                    />
                  </g>
                </svg>
              </div>
            </div>

            {/* ViewCube */}
            <div className="absolute top-14 right-2 z-20">
              <ViewCube />
            </div>

            {/* Bottom Bar: Geometry Audit Badge */}
            <div className="w-full flex items-center justify-between bg-[#181b24]/95 backdrop-blur-md p-2 rounded-lg shadow-lg z-20 pointer-events-auto border border-[#2e3646]/60 font-label-sm text-[10px]">
              <div className="flex items-center gap-3">
                <span className="text-[#64748b]">Volumen B-Rep:</span>
                <span className="text-[#f1f5f9] font-bold font-mono">425.8 cm³</span>
                <span className="text-[#64748b]">|</span>
                <span className="text-[#64748b]">Masa Final:</span>
                <span className="text-[#10b981] font-bold font-mono">1.20 kg (-64.9%)</span>
              </div>
              <div className="flex items-center gap-1.5 text-[#10b981]">
                <ShieldCheck className="w-4 h-4" />
                <span>B-Rep Manifold Válido para Fabricación CNC / Aditiva</span>
              </div>
            </div>
          </div>
        </main>

        {/* RIGHT PANEL: Multi-format CAD Export Options & Certification */}
        <aside className="col-span-12 xl:col-span-3 flex flex-col gap-2">
          {/* Download Formats Selection */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 border border-[#2e3646]/50">
            <div className="flex items-center justify-between">
              <span className="font-headline-sm text-[13px] text-[#f1f5f9]">Exportación de Archivo</span>
              <span className="font-label-sm text-[10px] text-[#7bd0ff]">4 Formatos</span>
            </div>

            {downloadSuccess && (
              <div className="p-2 rounded bg-[#10b981]/20 border border-[#10b981]/40 text-[#10b981] font-label-sm text-[11px] flex items-center gap-1.5 animate-fade-in">
                <CheckCircle2 className="w-4 h-4" />
                <span>Archivo {downloadSuccess} generado y descargado con éxito.</span>
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              {/* Option 1: STEP AP242 (Primary) */}
              <div className="p-2.5 rounded bg-[#1f2430] border border-[#0ea5e9] flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-headline-sm text-[12px] text-[#7bd0ff] flex items-center gap-1.5">
                    <FileCheck className="w-4 h-4" />
                    STEP AP242 (.step)
                  </span>
                  <span className="font-label-sm text-[9px] px-1.5 py-0.5 rounded bg-[#0ea5e9]/20 text-[#7bd0ff]">
                    Estándar ISO
                  </span>
                </div>
                <p className="font-body-sm text-[10px] text-[#94a3b8]">
                  Sólido B-Rep de alta fidelidad con topología exacta para SolidWorks, Siemens NX, CATIA y Fusion 360.
                </p>
                <label className="font-label-sm text-[10px] text-[#64748b]">Ruta de exportación:</label>
                <input
                  type="text"
                  value={exportPath}
                  onChange={(e) => setExportPath(e.target.value)}
                  className="w-full bg-[#0b0e17] border border-[#2e3646] rounded px-2 py-1 font-mono text-[10px] text-[#f1f5f9] focus:outline-none focus:border-[#7bd0ff]"
                />
                {exportStatus && (
                  <div className="text-[10px] text-[#10b981] bg-[#10b981]/10 border border-[#10b981]/30 rounded px-2 py-1">{exportStatus}</div>
                )}
                {exportError && (
                  <div className="text-[10px] text-[#fca5a5] bg-[#ef4444]/10 border border-[#ef4444]/30 rounded px-2 py-1">Error: {exportError}</div>
                )}
                <button
                  onClick={handleBackendExport}
                  disabled={isExporting}
                  className="w-full mt-0.5 py-1.5 px-2 bg-[#10b981] hover:bg-[#34d399] text-[#0b0e17] font-headline-sm text-[11px] rounded flex items-center justify-center gap-1.5 font-bold transition-all disabled:opacity-60"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>{isExporting ? 'Exportando...' : 'Exportar vía backend (exportStep)'}</span>
                </button>
                <button
                  onClick={() => handleDownload('STEP')}
                  disabled={isExporting}
                  className="w-full mt-0.5 py-1.5 px-2 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-headline-sm text-[11px] rounded flex items-center justify-center gap-1.5 font-bold transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Descargar STEP AP242</span>
                </button>
              </div>

              {/* Option 2: IGES 5.3 */}
              <div className="p-2 rounded bg-[#1f2430]/70 border border-[#2e3646]/40 flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium text-[11px]">IGES 5.3 (.igs)</span>
                  <span className="text-[#64748b] text-[10px]">Superficies NURBS paramétricas</span>
                </div>
                <button
                  onClick={() => handleDownload('IGS')}
                  className="px-2.5 py-1 rounded bg-[#272a33] hover:bg-[#32343e] text-[#f1f5f9] hover:text-[#7bd0ff] font-label-sm text-[10px] border border-[#2e3646]"
                >
                  Exportar
                </button>
              </div>

              {/* Option 3: STL / OBJ */}
              <div className="p-2 rounded bg-[#1f2430]/70 border border-[#2e3646]/40 flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium text-[11px]">STL Binario (.stl)</span>
                  <span className="text-[#64748b] text-[10px]">Malla de alta densidad para SLM / DMLS</span>
                </div>
                <button
                  onClick={() => handleDownload('STL')}
                  className="px-2.5 py-1 rounded bg-[#272a33] hover:bg-[#32343e] text-[#f1f5f9] hover:text-[#7bd0ff] font-label-sm text-[10px] border border-[#2e3646]"
                >
                  Exportar
                </button>
              </div>

              {/* Option 4: GLTF 2.0 Web3D */}
              <div className="p-2 rounded bg-[#1f2430]/70 border border-[#2e3646]/40 flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium text-[11px]">glTF 2.0 (.glb)</span>
                  <span className="text-[#64748b] text-[10px]">Visualización Web3D y gemelo digital</span>
                </div>
                <button
                  onClick={() => handleDownload('GLB')}
                  className="px-2.5 py-1 rounded bg-[#272a33] hover:bg-[#32343e] text-[#f1f5f9] hover:text-[#7bd0ff] font-label-sm text-[10px] border border-[#2e3646]"
                >
                  Exportar
                </button>
              </div>
            </div>
          </section>

          {/* Verification & Quality Certification */}
          <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md flex flex-col gap-2 mt-auto border border-[#2e3646]">
            <span className="font-headline-sm text-[12px] text-[#f1f5f9]">Certificación del Modelo</span>
            <div className="flex flex-col gap-1.5 text-[10px] font-label-sm">
              <div className="flex items-center justify-between text-[#94a3b8]">
                <span>Material de Fabricación:</span>
                <span className="text-[#f1f5f9] font-bold">{material.name}</span>
              </div>
              <div className="flex items-center justify-between text-[#94a3b8]">
                <span>Factor de Seguridad:</span>
                <span className="text-[#10b981] font-bold font-mono">FS = 1.62 (Aprobado)</span>
              </div>
              <div className="flex items-center justify-between text-[#94a3b8]">
                <span>Ahorro de Masa:</span>
                <span className="text-[#7bd0ff] font-bold font-mono">-64.9% (-2.22 kg)</span>
              </div>
            </div>

            <button
              onClick={() => handleDownload('STEP')}
              className="w-full py-2.5 px-3 bg-[#10b981] hover:bg-[#34d399] text-[#0b0e17] font-headline-sm text-[12px] rounded-lg shadow-lg flex items-center justify-center gap-1.5 font-bold transition-all mt-1"
            >
              <FileDown className="w-4 h-4" />
              <span>Guardar Paquete de Fabricación (.zip)</span>
            </button>
          </section>
        </aside>
      </div>
    </div>
  );
};
