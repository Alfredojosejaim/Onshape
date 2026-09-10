import React, { useState } from 'react';
import { Viewport3D } from '../Viewport3D';
import { GenerativeExportState, MaterialProperties } from '../../types';

interface GenerativoExportScreenProps {
  exportState: GenerativeExportState;
  onUpdateExportState: (updater: (prev: GenerativeExportState) => GenerativeExportState) => void;
  material: MaterialProperties;
  forceMagnitude: number;
  onOpenExportModal: () => void;
}

export const GenerativoExportScreen: React.FC<GenerativoExportScreenProps> = ({
  exportState,
  onUpdateExportState,
  material,
  forceMagnitude,
  onOpenExportModal,
}) => {
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  const handleQuickDownload = (format: string) => {
    setDownloadSuccess(`Descargando archivo ${format} optimizado...`);
    setTimeout(() => {
      setDownloadSuccess(null);
    }, 3500);
  };

  return (
    <div className="w-full flex flex-col xl:flex-row gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* LEFT PANEL: Reconstruction & DFM Checks */}
      <aside className="w-full xl:w-72 2xl:w-80 flex flex-col gap-2 flex-shrink-0">
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">shape_line</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Reconstrucción B-Rep</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">NURBS G2</span>
          </header>

          <div className="flex flex-col gap-2 text-xs">
            {/* Algorithm */}
            <div className="flex flex-col gap-1">
              <label className="font-mono text-[10px] text-[#64748b]">Algoritmo de Superficie:</label>
              <select
                value={exportState.reconstructionMethod}
                onChange={(e) =>
                  onUpdateExportState((prev) => ({
                    ...prev,
                    reconstructionMethod: e.target.value as any,
                  }))
                }
                className="w-full bg-[#1f2430] border border-[#2e3646] rounded p-1.5 text-xs text-[#f1f5f9] font-medium"
              >
                <option value="Marching Cubes + QuadRemesh">Marching Cubes + QuadRemesh</option>
                <option value="Dual Contouring">Dual Contouring Adaptativo</option>
                <option value="NURBS B-Rep">NURBS B-Rep Paramétrico</option>
              </select>
            </div>

            {/* Smoothing Slider */}
            <div className="bg-[#1f2430]/50 p-2 rounded flex flex-col gap-1">
              <div className="flex justify-between items-center">
                <span className="text-[#f1f5f9]">Suavizado Laplaciano:</span>
                <span className="font-mono text-[#7bd0ff] font-bold">{exportState.surfaceSmoothing}%</span>
              </div>
              <input
                type="range"
                min="30"
                max="100"
                step="5"
                value={exportState.surfaceSmoothing}
                onChange={(e) =>
                  onUpdateExportState((prev) => ({
                    ...prev,
                    surfaceSmoothing: parseInt(e.target.value, 10),
                  }))
                }
                className="w-full accent-[#0ea5e9] cursor-pointer"
              />
              <span className="text-[9px] font-mono text-[#64748b]">Preserva interfaces de pernos y roscas</span>
            </div>

            {/* B-Rep Metrics */}
            <div className="bg-[#0b0e17] p-2 rounded border border-[#2e3646]/60 font-mono text-[10px] flex flex-col gap-1">
              <div className="flex justify-between">
                <span className="text-[#64748b]">Caras B-Rep Sólidas:</span>
                <span className="text-[#7bd0ff] font-bold">{exportState.brepFaceCount} parches</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">Hermeticidad (Watertight):</span>
                <span className="text-[#10b981] font-bold">100% Sólido Válido</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">Continuidad de Curvatura:</span>
                <span className="text-[#10b981] font-bold">G2 Tangente</span>
              </div>
            </div>
          </div>
        </section>

        {/* DFM (Design for Additive Manufacturing) */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">precision_manufacturing</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Fabricabilidad (DFM)</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">SLM / DMLS</span>
          </header>

          <div className="flex flex-col gap-1 font-mono text-[11px]">
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Orientación de Fabricación:</span>
              <span className="text-[#7bd0ff] font-bold">Eje {exportState.amBuildDirection} (Vertical)</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Ángulo Crítico Voladizo:</span>
              <span className="text-[#f1f5f9] font-bold">{exportState.overhangMaxAngle}°</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Soportes Requeridos:</span>
              <span className="text-[#10b981] font-bold">Autoportante (0%)</span>
            </div>
          </div>
        </section>
      </aside>

      {/* CENTER: Reconstructed B-Rep 3D Viewport */}
      <Viewport3D activeTab="generativo-export" forceMagnitude={forceMagnitude} />

      {/* RIGHT PANEL: Scorecard & Export Actions */}
      <aside className="w-full xl:w-80 2xl:w-88 flex flex-col gap-2 flex-shrink-0">
        {/* Mass & Stiffness Scorecard */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">speed</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Resumen de Optimización</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">-65.5%</span>
          </header>

          <div className="grid grid-cols-2 gap-1.5 pt-1">
            <div className="p-2 rounded bg-[#1f2430]/50 border border-[#2e3646]/40 flex flex-col">
              <span className="text-[10px] font-mono text-[#64748b]">Masa Inicial:</span>
              <span className="font-mono text-sm font-bold text-[#94a3b8] line-through">
                {exportState.originalMassKg.toFixed(2)} kg
              </span>
            </div>

            <div className="p-2 rounded bg-[#10b981]/15 border border-[#10b981]/30 flex flex-col">
              <span className="text-[10px] font-mono text-[#10b981]">Masa Optimizada:</span>
              <span className="font-mono text-sm font-bold text-[#f1f5f9]">
                {exportState.optimizedMassKg.toFixed(2)} kg
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-1 font-mono text-[11px] pt-1">
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Ahorro de Peso:</span>
              <span className="text-[#10b981] font-bold">2.24 kg (-65.5%)</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Retención de Rigidez:</span>
              <span className="text-[#7bd0ff] font-bold">{exportState.stiffnessRetentionPct}%</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Material Aplicado:</span>
              <span className="text-[#f1f5f9]">{material.name}</span>
            </div>
          </div>
        </section>

        {/* Quick Export Cards */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <span className="text-xs font-semibold text-[#f1f5f9]">Formatos de Fabricación</span>
            <span className="text-[10px] font-mono text-[#64748b]">Descarga Directa</span>
          </header>

          <div className="flex flex-col gap-1">
            {[
              { format: 'STEP AP242 (.step)', desc: 'Geometría Sólida B-Rep con PMI', icon: 'deployed_code' },
              { format: 'STL Binario (.stl)', desc: 'Malla Facetada 480k Polígonos para 3D Print', icon: 'grid_view' },
              { format: 'Certificado CAE (.pdf)', desc: 'Reporte de homologación y tensiones FEA', icon: 'picture_as_pdf' },
            ].map((item) => (
              <button
                key={item.format}
                type="button"
                onClick={() => handleQuickDownload(item.format)}
                className="p-2 rounded bg-[#1f2430]/60 hover:bg-[#272a33] border border-[#2e3646] flex items-center justify-between text-left transition-colors cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px] text-[#7bd0ff] group-hover:scale-110 transition-transform">
                    {item.icon}
                  </span>
                  <div>
                    <span className="text-xs font-semibold text-[#f1f5f9] block">{item.format}</span>
                    <span className="text-[10px] text-[#64748b]">{item.desc}</span>
                  </div>
                </div>
                <span className="material-symbols-outlined text-[16px] text-[#64748b] group-hover:text-[#7bd0ff]">
                  download
                </span>
              </button>
            ))}
          </div>

          {downloadSuccess && (
            <div className="p-2 rounded bg-[#10b981]/20 border border-[#10b981]/40 text-[#10b981] font-mono text-[10px] flex items-center gap-1 animate-fadeIn">
              <span className="material-symbols-outlined text-[14px]">check_circle</span>
              <span>{downloadSuccess}</span>
            </div>
          )}
        </section>

        {/* Primary CTA */}
        <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md border border-[#2e3646]/60 flex flex-col gap-2 mt-auto">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-mono text-[10px] text-[#94a3b8]">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                Modelo Homologado
              </span>
              <span className="text-[#10b981] font-bold">100% Listo</span>
            </div>
            <p className="text-[#64748b] text-[11px] leading-tight">
              Abre el centro de exportación para configurar tolerancias de exportación STEP, metadatos y reporte técnico.
            </p>
          </div>

          <button
            onClick={onOpenExportModal}
            className="w-full py-2 px-3 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-semibold text-xs rounded-lg shadow-lg hover:shadow-cyan-500/20 flex items-center justify-center gap-1.5 transition-all transform active:scale-98 cursor-pointer"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">download_for_offline</span>
            <span>Centro de Exportación Avanzado</span>
          </button>
        </section>
      </aside>
    </div>
  );
};
