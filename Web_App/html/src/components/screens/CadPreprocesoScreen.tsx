import React from 'react';
import { Viewport3D } from '../Viewport3D';
import { MaterialProperties, MeshingSettings, CadFeature } from '../../types';

interface CadPreprocesoScreenProps {
  materials: MaterialProperties[];
  selectedMaterial: MaterialProperties;
  onSelectMaterial: (mat: MaterialProperties) => void;
  meshing: MeshingSettings;
  onUpdateMeshing: (newMeshing: Partial<MeshingSettings>) => void;
  onRemesh: () => void;
  isRemeshing: boolean;
  cadFeatures: CadFeature[];
  onToggleFeatureVisibility: (id: string) => void;
  onProceedToNextStep: () => void;
  forceMagnitude: number;
  onUpdateForce: (newVal: number) => void;
  selectedFace: number | null;
  onSelectFace: (id: number) => void;
}

export const CadPreprocesoScreen: React.FC<CadPreprocesoScreenProps> = ({
  materials,
  selectedMaterial,
  onSelectMaterial,
  meshing,
  onUpdateMeshing,
  onRemesh,
  isRemeshing,
  cadFeatures,
  onToggleFeatureVisibility,
  onProceedToNextStep,
  forceMagnitude,
  onUpdateForce,
  selectedFace,
  onSelectFace,
}) => {
  return (
    <div className="w-full flex flex-col xl:flex-row gap-2 p-2 bg-[#0f1117] min-h-[calc(100vh-6.75rem)]">
      {/* LEFT PANEL: Tree, Pre-Process Features & Gmsh Mesher */}
      <aside className="w-full xl:w-72 2xl:w-80 flex flex-col gap-2 flex-shrink-0">
        {/* CAD Feature Tree Card */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">account_tree</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Árbol de Operaciones CAD</span>
            </div>
            <span className="text-[10px] font-mono text-[#64748b]">B-Rep STEP</span>
          </header>

          {/* Tree Nodes List */}
          <div className="flex flex-col gap-1 py-1 text-xs text-[#94a3b8]">
            {/* Global Coordinate System */}
            <div className="group flex items-center justify-between px-2 py-1 rounded hover:bg-[#1f2430] cursor-pointer">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[#64748b] text-[14px]">expand_more</span>
                <span className="material-symbols-outlined text-[#64748b] text-[14px]">grid_4x4</span>
                <span className="text-[#f1f5f9]">Sist. Coordenado Global</span>
              </div>
              <button
                type="button"
                onClick={() => onToggleFeatureVisibility('origin')}
                className="material-symbols-outlined text-[#64748b] hover:text-[#7bd0ff] text-[14px]"
              >
                visibility
              </button>
            </div>

            {/* Planes */}
            <div className="pl-6 flex flex-col gap-0.5">
              <div className="flex items-center justify-between px-2 py-0.5 rounded hover:bg-[#272a33] text-[#64748b] hover:text-[#f1f5f9] text-[11px] cursor-pointer">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#ef4444]"></span>Plano XY (Base)
                </span>
                <span className="font-mono text-[10px] opacity-60">Z=0</span>
              </div>
              <div className="flex items-center justify-between px-2 py-0.5 rounded hover:bg-[#272a33] text-[#64748b] hover:text-[#f1f5f9] text-[11px] cursor-pointer">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>Plano XZ (Simetría)
                </span>
                <span className="font-mono text-[10px] opacity-60">Y=0</span>
              </div>
              <div className="flex items-center justify-between px-2 py-0.5 rounded hover:bg-[#272a33] text-[#64748b] hover:text-[#f1f5f9] text-[11px] cursor-pointer">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#7bd0ff]"></span>Plano YZ (Transversal)
                </span>
                <span className="font-mono text-[10px] opacity-60">X=0</span>
              </div>
            </div>

            {/* Sólido Importado STEP */}
            <div className="group flex items-center justify-between px-2 py-1.5 rounded bg-[#1f2430]/70 hover:bg-[#1f2430] border border-[#2e3646]/50 cursor-pointer">
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[#89ceff] text-[16px]">deployed_code</span>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium text-xs leading-tight">cono_soporte.step</span>
                  <span className="text-[10px] font-mono text-[#64748b]">12 Caras • 18 Aristas • 1 Sólido</span>
                </div>
              </div>
              <span className="material-symbols-outlined text-[#7bd0ff] text-[16px]">visibility</span>
            </div>

            {/* Feature: Fijación Principal */}
            <div className="flex items-center justify-between px-2 py-1 rounded bg-[#272a33]/40 hover:bg-[#1f2430] border border-transparent hover:border-[#2e3646] cursor-pointer">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded bg-[#7bd0ff]/10 flex items-center justify-center">
                  <span className="material-symbols-outlined text-[#7bd0ff] text-[14px]">anchor</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium">Encastre Soporte</span>
                  <span className="text-[10px] font-mono text-[#7bd0ff]">3 Caras | Ux=Uy=Uz=0</span>
                </div>
              </div>
              <span className="material-symbols-outlined text-[#10b981] text-[14px]">check_circle</span>
            </div>

            {/* Feature: Carga Tracción */}
            <div className="flex items-center justify-between px-2 py-1 rounded bg-[#272a33]/40 hover:bg-[#1f2430] border border-transparent hover:border-[#2e3646] cursor-pointer">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded bg-[#ffb95f]/10 flex items-center justify-center">
                  <span className="material-symbols-outlined text-[#ffb95f] text-[14px]">arrow_downward</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium">Tracción Cilíndrica</span>
                  <span className="text-[10px] font-mono text-[#ffb95f]">[0, -{forceMagnitude}, 1200] N</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  const val = prompt('Ingrese magnitud de fuerza F en Newtons:', String(forceMagnitude));
                  if (val && !isNaN(Number(val))) onUpdateForce(Number(val));
                }}
                className="material-symbols-outlined text-[#7bd0ff] text-[14px] hover:text-[#ffffff]"
                title="Editar Magnitud de Carga"
              >
                edit
              </button>
            </div>

            {/* Feature: Non-Design Space Preservada */}
            <div className="flex items-center justify-between px-2 py-1 rounded bg-[#10b981]/10 hover:bg-[#10b981]/15 border border-[#10b981]/20 cursor-pointer">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded bg-[#10b981]/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-[#10b981] text-[14px]">shield</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium">Región Preservada</span>
                  <span className="text-[10px] font-mono text-[#10b981]">Pernos y Bujes (8 mm)</span>
                </div>
              </div>
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#10b981] text-[#0b0e17] font-bold">
                SAFE
              </span>
            </div>

            {/* Feature: Zona Obstáculo / Keep-out */}
            <div className="flex items-center justify-between px-2 py-1 rounded bg-[#ef4444]/10 hover:bg-[#ef4444]/15 border border-[#ef4444]/20 cursor-pointer">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded bg-[#ef4444]/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-[#ef4444] text-[14px]">block</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[#f1f5f9] font-medium">Obstáculo (Keep-Out)</span>
                  <span className="text-[10px] font-mono text-[#ef4444]">Cilindro Paso Tornillo</span>
                </div>
              </div>
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#ef4444] text-[#0b0e17] font-bold">
                VOID
              </span>
            </div>
          </div>
        </section>

        {/* Gmsh Meshing Controls Card */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">grain</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Parámetros Gmsh 3D</span>
            </div>
            <span className="text-[10px] font-mono text-[#10b981]">Delaunay</span>
          </header>

          <div className="flex flex-col gap-1.5 text-xs">
            <div className="flex items-center justify-between bg-[#1f2430]/40 px-2 py-1 rounded">
              <span className="text-[#64748b]">Algoritmo:</span>
              <span className="font-mono text-[11px] text-[#7bd0ff]">{meshing.algorithm}</span>
            </div>

            {/* Element Min / Max Slider Values */}
            <div className="grid grid-cols-2 gap-1.5">
              <div className="bg-[#1f2430]/60 p-1.5 rounded flex flex-col">
                <span className="font-mono text-[10px] text-[#64748b]">h_min (mm)</span>
                <div className="flex items-center justify-between mt-1">
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="5.0"
                    value={meshing.hMin}
                    onChange={(e) => onUpdateMeshing({ hMin: parseFloat(e.target.value) || 1.5 })}
                    className="w-14 bg-transparent font-mono text-xs font-bold text-[#f1f5f9] focus:outline-none"
                  />
                  <span className="material-symbols-outlined text-[#64748b] text-[14px]">tune</span>
                </div>
              </div>

              <div className="bg-[#1f2430]/60 p-1.5 rounded flex flex-col">
                <span className="font-mono text-[10px] text-[#64748b]">h_max (mm)</span>
                <div className="flex items-center justify-between mt-1">
                  <input
                    type="number"
                    step="0.5"
                    min="2.0"
                    max="15.0"
                    value={meshing.hMax}
                    onChange={(e) => onUpdateMeshing({ hMax: parseFloat(e.target.value) || 6.0 })}
                    className="w-14 bg-transparent font-mono text-xs font-bold text-[#f1f5f9] focus:outline-none"
                  />
                  <span className="material-symbols-outlined text-[#64748b] text-[14px]">tune</span>
                </div>
              </div>
            </div>

            {/* Telemetry & Quality Chips */}
            <div className="bg-[#0b0e17] p-2 rounded flex flex-col gap-1 border border-[#2e3646]/50">
              <div className="flex justify-between items-center text-[10px] font-mono">
                <span className="text-[#64748b]">Calidad Jacobiana:</span>
                <span className="text-[#10b981] font-bold">
                  {meshing.jacobianQuality} (Excelente)
                </span>
              </div>
              <div className="w-full bg-[#32343e] rounded h-1.5 overflow-hidden">
                <div className="bg-[#10b981] h-full rounded transition-all duration-300" style={{ width: `${meshing.jacobianQuality * 100}%` }}></div>
              </div>
              <div className="flex justify-between items-center text-[10px] font-mono text-[#64748b] pt-0.5">
                <span>Nodos: <strong className="text-[#f1f5f9]">{meshing.nodesCount.toLocaleString()}</strong></span>
                <span>Elem. Tet4: <strong className="text-[#7bd0ff]">{meshing.elementsCount.toLocaleString()}</strong></span>
              </div>
            </div>

            {/* Remesh Trigger Button */}
            <button
              onClick={onRemesh}
              disabled={isRemeshing}
              className="w-full py-1.5 px-2 bg-[#1f2430] hover:bg-[#272a33] text-[#f1f5f9] hover:text-[#7bd0ff] border border-[#2e3646] rounded flex items-center justify-center gap-1.5 font-semibold text-xs shadow-sm transition-all cursor-pointer disabled:opacity-50"
              type="button"
            >
              <span className={`material-symbols-outlined text-[16px] ${isRemeshing ? 'animate-spin' : ''}`}>
                refresh
              </span>
              <span>{isRemeshing ? 'Generando Nodos y Aristas...' : 'Remallar Geometría Gmsh'}</span>
            </button>
          </div>
        </section>

        {/* Step Inspector Helper */}
        <div className="bg-[#181b24]/60 border border-[#2e3646]/40 rounded-lg p-1.5 flex items-center justify-between font-mono text-[10px] text-[#64748b]">
          <span className="flex items-center gap-1 text-[#f59e0b]">
            <span className="material-symbols-outlined text-[13px]">warning</span>
            Tolerancia Angular: {meshing.angularTolerance}°
          </span>
          <span className="text-[#94a3b8]">Deflexión: {meshing.chordalDeflection} mm</span>
        </div>
      </aside>

      {/* CENTRAL AREA: VTK 3D CAD Viewport */}
      <Viewport3D
        activeTab="cad-preproceso"
        forceMagnitude={forceMagnitude}
        selectedFace={selectedFace}
        onSelectFace={onSelectFace}
      />

      {/* RIGHT PANEL: Material Library & CAE Study Inspector */}
      <aside className="w-full xl:w-80 2xl:w-88 flex flex-col gap-2 flex-shrink-0">
        {/* Material Library Card */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">science</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Biblioteca de Materiales</span>
            </div>
            <span className="text-[10px] font-mono text-[#64748b]">Isótropo Elástico</span>
          </header>

          {/* Alloy Selector Dropdown */}
          <div className="flex flex-col gap-1">
            <label className="font-mono text-[10px] text-[#64748b]">Aleación / Polímero:</label>
            <div className="relative">
              <select
                value={selectedMaterial.id}
                onChange={(e) => {
                  const m = materials.find((mat) => mat.id === e.target.value);
                  if (m) onSelectMaterial(m);
                }}
                className="w-full bg-[#1f2430] border border-[#2e3646] rounded px-2.5 py-1.5 text-xs font-semibold text-[#f1f5f9] appearance-none cursor-pointer focus:ring-1 focus:ring-[#0ea5e9] focus:outline-none pr-8"
              >
                {materials.map((mat) => (
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
          <div className="flex flex-col gap-1 pt-1 font-mono text-[11px]">
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Módulo Young (E):</span>
              <span className="text-[#f1f5f9] font-bold">{selectedMaterial.youngsModulus} GPa</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Coef. Poisson (ν):</span>
              <span className="text-[#f1f5f9] font-bold">{selectedMaterial.poissonRatio}</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Límite Elástico (σ_y):</span>
              <span className="text-[#f59e0b] font-bold">{selectedMaterial.yieldStrength} MPa</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Densidad (ρ):</span>
              <span className="text-[#f1f5f9] font-bold">{selectedMaterial.density} g/cm³</span>
            </div>
            <div className="flex items-center justify-between py-1 px-2 bg-[#1f2430]/50 rounded">
              <span className="text-[#94a3b8] font-sans text-xs">Resistencia Tracción:</span>
              <span className="text-[#f1f5f9] font-bold">{selectedMaterial.tensileStrength} MPa</span>
            </div>
          </div>
        </section>

        {/* CAE Study Metrics & Physical Properties */}
        <section className="bg-[#181b24] rounded-lg p-2 shadow-md border border-[#2e3646]/60 flex flex-col gap-1.5">
          <header className="flex items-center justify-between px-2 py-1 bg-[#1f2430] rounded border border-[#2e3646]/40">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#7bd0ff]">analytics</span>
              <span className="text-xs font-semibold text-[#f1f5f9]">Configuración de Estudio</span>
            </div>
            <span className="text-[10px] font-mono text-[#64748b]">FEA Estático</span>
          </header>

          <div className="flex flex-col gap-1.5 text-xs">
            <div className="flex items-center justify-between bg-[#1f2430]/60 p-2 rounded">
              <div className="flex flex-col">
                <span className="text-[#64748b] text-[11px]">Tipo de Análisis:</span>
                <span className="text-[#f1f5f9] font-semibold">Elástico Lineal Estático</span>
              </div>
              <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">balance</span>
            </div>

            <div className="grid grid-cols-2 gap-1.5">
              <div className="bg-[#1f2430]/40 p-2 rounded flex flex-col">
                <span className="font-mono text-[10px] text-[#64748b]">Masa Inicial:</span>
                <span className="font-mono text-xs text-[#f1f5f9] font-bold mt-0.5">3.42 kg</span>
                <span className="text-[9px] font-mono text-[#64748b] mt-0.5">100% Volumen</span>
              </div>
              <div className="bg-[#1f2430]/40 p-2 rounded flex flex-col">
                <span className="font-mono text-[10px] text-[#64748b]">Volumen Total:</span>
                <span className="font-mono text-xs text-[#f1f5f9] font-bold mt-0.5">1,217 cm³</span>
                <span className="text-[9px] font-mono text-[#10b981] mt-0.5">Sólido Hermético</span>
              </div>
            </div>

            {/* Optimization Objective Brief Preview */}
            <div className="bg-[#272a33]/60 p-2 rounded flex flex-col gap-1 border border-[#2e3646]/50">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#94a3b8] font-medium">Meta de Reducción SIMP:</span>
                <span className="text-[#7bd0ff] font-mono text-[11px] font-bold">VF = 0.35 (-65%)</span>
              </div>
              <div className="flex justify-between items-center text-[10px] font-mono text-[#64748b]">
                <span>Masa proyectada optimizada:</span>
                <span className="text-[#10b981] font-bold">~1.20 kg</span>
              </div>
            </div>
          </div>
        </section>

        {/* Primary High-Impact CTA Button Card */}
        <section className="bg-[#181b24] rounded-lg p-2.5 shadow-md border border-[#2e3646]/60 flex flex-col gap-2 mt-auto">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-mono text-[10px] text-[#94a3b8]">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                BCs Asignadas: 1 Fijación / 1 Carga
              </span>
              <span className="text-[#f1f5f9] font-bold">100% OK</span>
            </div>
            <p className="text-[#64748b] text-[11px] leading-tight">
              El mallador discretizará el espacio no de diseño y generará la matriz de rigidez global K.
            </p>
          </div>

          <button
            onClick={onProceedToNextStep}
            className="w-full py-2 px-3 bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-semibold text-xs rounded-lg shadow-lg hover:shadow-cyan-500/20 flex items-center justify-center gap-1.5 transition-all transform active:scale-98 cursor-pointer"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">play_arrow</span>
            <span>Validar Condiciones & Generar Malla</span>
          </button>
        </section>
      </aside>
    </div>
  );
};
