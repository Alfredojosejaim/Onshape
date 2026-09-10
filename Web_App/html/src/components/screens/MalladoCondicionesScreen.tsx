import React, { useState } from 'react';
import { Viewport3D } from '../Viewport3D';
import { MeshingSettings, BoundaryCondition } from '../../types';

interface MalladoCondicionesScreenProps {
  meshing: MeshingSettings;
  onUpdateMeshing: (newVal: Partial<MeshingSettings>) => void;
  boundaryConditions: BoundaryCondition[];
  onToggleBc: (id: string) => void;
  onProceedToFea: () => void;
  forceMagnitude: number;
}

export const MalladoCondicionesScreen: React.FC<MalladoCondicionesScreenProps> = ({
  meshing,
  onUpdateMeshing,
  boundaryConditions,
  onToggleBc,
  onProceedToFea,
  forceMagnitude,
}) => {
  const [selectedElementType, setSelectedElementType] = useState<'Tet4' | 'Tet10' | 'Hex8'>('Tet4');
  const [activeRefinementZone, setActiveRefinementZone] = useState<string>('Bujes Base');
  const [showAddBc, setShowAddBc] = useState(false);

  // Quality metrics distribution
  const qualityBins = [
    { label: '< 0.5', pct: 0, color: '#ef4444' },
    { label: '0.5-0.7', pct: 4, color: '#f59e0b' },
    { label: '0.7-0.9', pct: 42, color: '#0ea5e9' },
    { label: '> 0.9', pct: 54, color: '#10b981' },
  ];

  return (
    <div className="w-full flex flex-col xl:flex-row gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* LEFT PANEL: Detailed Mesher & Quality Diagnostics */}
      <aside className="w-full xl:w-72 2xl:w-80 flex flex-col gap-2 flex-shrink-0">
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">view_in_ar</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Discretización de Dominio</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">Gmsh 4.12</span>
          </header>

          <div className="flex flex-col gap-2 text-xs">
            {/* Element formulation toggle */}
            <div>
              <label className="font-mono text-[10px] text-[#64748b]">Tipo de Elemento Finito:</label>
              <div className="grid grid-cols-3 gap-1 mt-1">
                {(['Tet4', 'Tet10', 'Hex8'] as const).map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setSelectedElementType(type)}
                    className={`py-1 text-center font-mono text-[11px] rounded border transition-colors cursor-pointer ${
                      selectedElementType === type
                        ? 'bg-[#0ea5e9]/20 border-[#0ea5e9] text-[#7bd0ff] font-bold'
                        : 'bg-[#1f2430] border-[#2e3646] text-[#94a3b8] hover:text-[#f1f5f9]'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {/* Element Growth Rate */}
            <div className="bg-[#1f2430]/50 p-2 rounded flex items-center justify-between">
              <div>
                <span className="text-[#f1f5f9] font-medium block">Tasa de Crecimiento:</span>
                <span className="text-[10px] text-[#64748b]">Gradiente h_max / h_min</span>
              </div>
              <span className="font-mono text-xs text-[#7bd0ff] font-bold">1.25x</span>
            </div>

            {/* Quality Distribution Histogram */}
            <div className="bg-[#0b0e17] p-2 rounded border border-[#2e3646]/60 flex flex-col gap-1.5">
              <span className="font-mono text-[10px] text-[#94a3b8] uppercase">
                Histograma Calidad Jacobiana (Det J / J_ideal)
              </span>
              <div className="flex items-end gap-1.5 h-16 pt-2">
                {qualityBins.map((bin) => (
                  <div key={bin.label} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                    <span className="text-[9px] font-mono text-[#94a3b8]">{bin.pct}%</span>
                    <div
                      className="w-full rounded-t transition-all duration-300"
                      style={{ height: `${Math.max(4, bin.pct * 1.1)}px`, backgroundColor: bin.color }}
                    />
                    <span className="text-[8px] font-mono text-[#64748b]">{bin.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Metric Details */}
            <div className="flex flex-col gap-1 font-mono text-[10px]">
              <div className="flex justify-between py-0.5 px-1.5 bg-[#1f2430]/40 rounded">
                <span className="text-[#64748b]">Ángulo Mínimo Diedro:</span>
                <span className="text-[#10b981] font-bold">28.4° (&gt; 20° Requerido)</span>
              </div>
              <div className="flex justify-between py-0.5 px-1.5 bg-[#1f2430]/40 rounded">
                <span className="text-[#64748b]">Relación de Aspecto Máx:</span>
                <span className="text-[#f1f5f9]">3.12 (Excelente)</span>
              </div>
              <div className="flex justify-between py-0.5 px-1.5 bg-[#1f2430]/40 rounded">
                <span className="text-[#64748b]">Elementos Degenerados:</span>
                <span className="text-[#10b981] font-bold">0 (0.00%)</span>
              </div>
            </div>
          </div>
        </section>

        {/* Refinement zones card */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <span className="text-xs font-semibold text-[#f1f5f9]">Refinamiento Adaptativo</span>
            <span className="text-[10px] font-mono text-[#7bd0ff]">Octree</span>
          </header>
          <div className="flex flex-col gap-1 text-xs text-[#94a3b8]">
            {['Bujes Base (h=1.0mm)', 'Ojo Superior de Carga (h=0.8mm)', 'Entalla de Transición (h=1.2mm)'].map((zone) => (
              <div
                key={zone}
                onClick={() => setActiveRefinementZone(zone)}
                className={`flex items-center justify-between px-2 py-1 rounded cursor-pointer transition-colors ${
                  activeRefinementZone === zone
                    ? 'bg-[#0ea5e9]/20 text-[#7bd0ff] font-medium border border-[#0ea5e9]/40'
                    : 'bg-[#1f2430]/40 hover:bg-[#272a33]'
                }`}
              >
                <span>{zone}</span>
                <span className="material-symbols-outlined text-[14px]">
                  {activeRefinementZone === zone ? 'radio_button_checked' : 'radio_button_unchecked'}
                </span>
              </div>
            ))}
          </div>
        </section>
      </aside>

      {/* CENTER: Viewport 3D in Mesh Mode */}
      <Viewport3D activeTab="mallado-condiciones" forceMagnitude={forceMagnitude} />

      {/* RIGHT PANEL: Boundary Conditions & Matrix Preparation */}
      <aside className="w-full xl:w-80 2xl:w-88 flex flex-col gap-2 flex-shrink-0">
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">anchor</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Condiciones de Borde (BCs)</span>
            </div>
            <button
              type="button"
              onClick={() => setShowAddBc(!showAddBc)}
              className="text-[10px] font-mono text-[#7bd0ff] hover:underline cursor-pointer flex items-center gap-0.5"
            >
              <span className="material-symbols-outlined text-[12px]">add</span> Nueva BC
            </button>
          </header>

          <div className="flex flex-col gap-1.5">
            {boundaryConditions.map((bc) => (
              <div
                key={bc.id}
                className={`p-2 rounded border transition-all ${
                  bc.active
                    ? 'bg-[#1f2430]/70 border-[#2e3646]'
                    : 'bg-[#10131c]/50 border-dashed border-[#2e3646]/40 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`material-symbols-outlined text-[16px] ${
                        bc.type === 'fixed' ? 'text-[#7bd0ff]' : 'text-[#ffb95f]'
                      }`}
                    >
                      {bc.type === 'fixed' ? 'anchor' : 'arrow_downward'}
                    </span>
                    <span className="text-xs font-medium text-[#f1f5f9]">{bc.name}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onToggleBc(bc.id)}
                    className={`material-symbols-outlined text-[16px] cursor-pointer ${
                      bc.active ? 'text-[#10b981]' : 'text-[#64748b]'
                    }`}
                  >
                    {bc.active ? 'toggle_on' : 'toggle_off'}
                  </button>
                </div>
                <div className="mt-1 flex items-center justify-between text-[10px] font-mono text-[#94a3b8]">
                  <span>{bc.location}</span>
                  <span className="text-[#7bd0ff]">
                    {bc.type === 'force' ? `F = ${forceMagnitude} N` : 'Ux=Uy=Uz=0'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Global Stiffness Matrix Info */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <span className="text-xs font-semibold text-[#f1f5f9]">Ensamblaje de Matriz [K]</span>
            <span className="text-[10px] font-mono text-[#64748b]">Sparse CSR</span>
          </header>

          <div className="flex flex-col gap-1 font-mono text-[11px]">
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Grados de Libertad (DOFs):</span>
              <span className="text-[#7bd0ff] font-bold">289,740</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Valores No Cero (NNZ):</span>
              <span className="text-[#f1f5f9] font-bold">14,280,450</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Memoria Requerida:</span>
              <span className="text-[#f1f5f9] font-bold">342.8 MB</span>
            </div>
            <div className="flex justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Simetría de Matriz:</span>
              <span className="text-[#10b981] font-bold">Simétrica Positiva Definida</span>
            </div>
          </div>
        </section>

        {/* Primary Action Button */}
        <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md border border-[#2e3646]/60 flex flex-col gap-2 mt-auto">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-mono text-[10px] text-[#94a3b8]">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                Malla Validada: 215,410 Tets
              </span>
              <span className="text-[#10b981] font-bold">Listo para Solver</span>
            </div>
            <p className="text-[#64748b] text-[11px] leading-tight">
              Se resolverá el sistema Ku = F mediante el solver Cholesky directo paralelizado con OpenMP.
            </p>
          </div>

          <button
            onClick={onProceedToFea}
            className="w-full py-2 px-3 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-semibold text-xs rounded-lg shadow-lg hover:shadow-cyan-500/20 flex items-center justify-center gap-1.5 transition-all transform active:scale-98 cursor-pointer"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">play_arrow</span>
            <span>Resolver FEA & Tensiones</span>
          </button>
        </section>
      </aside>
    </div>
  );
};
