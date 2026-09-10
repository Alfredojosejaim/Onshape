import React, { useState } from 'react';
import { BoundaryCondition, CadModelPreset } from '../types';

interface LeftPanelProps {
  currentModel: CadModelPreset;
  models: CadModelPreset[];
  onSelectModel: (model: CadModelPreset) => void;
  boundaryConditions: BoundaryCondition[];
  onToggleCondition: (id: string) => void;
  onEditCondition: (condition: BoundaryCondition) => void;
  isModelVisible: boolean;
  onToggleModelVisibility: () => void;
  onOpenImport: () => void;
  meshElementSize: number;
  onChangeMeshSize: (size: number) => void;
  onRemesh: () => void;
  isRemeshing: boolean;
}

export const LeftPanel: React.FC<LeftPanelProps> = ({
  currentModel,
  models,
  onSelectModel,
  boundaryConditions,
  onToggleCondition,
  onEditCondition,
  isModelVisible,
  onToggleModelVisibility,
  onOpenImport,
  meshElementSize,
  onChangeMeshSize,
  onRemesh,
  isRemeshing,
}) => {
  const [planesOpen, setPlanesOpen] = useState(true);
  const [showModelPicker, setShowModelPicker] = useState(false);

  return (
    <aside className="w-full xl:w-72 2xl:w-80 flex flex-col gap-space-sm flex-shrink-0 select-none">
      {/* CAD Feature Tree Card */}
      <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-xs border border-border-subtle/40">
        <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated/70 rounded text-[11px] font-semibold text-text-primary">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-secondary text-[15px]">account_tree</span>
            <span>Árbol de Operaciones CAD</span>
          </div>
          <button
            onClick={onOpenImport}
            className="text-[10px] text-secondary hover:underline font-mono"
            title="Importar nueva pieza CAD"
          >
            + AÑADIR
          </button>
        </header>

        {/* Tree Nodes List */}
        <div className="flex flex-col gap-1 py-1 text-[11px] text-text-secondary">
          {/* Origen / Planos Base */}
          <div
            onClick={() => setPlanesOpen(!planesOpen)}
            className="group flex items-center justify-between px-2 py-1 rounded hover:bg-surface-elevated cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-text-muted text-[14px]">
                {planesOpen ? 'expand_more' : 'chevron_right'}
              </span>
              <span className="material-symbols-outlined text-text-muted text-[14px]">grid_4x4</span>
              <span className="text-text-primary font-medium">Sist. Coordenado Global</span>
            </div>
            <span className="text-[9px] font-mono text-text-muted">XYZ</span>
          </div>

          {planesOpen && (
            <div className="pl-6 flex flex-col gap-0.5 border-l border-border-subtle/30 ml-3.5">
              <div className="flex items-center justify-between px-2 py-1 rounded hover:bg-surface-container-high text-text-muted hover:text-text-primary text-[11px] cursor-pointer">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-fea-stress-critical"></span>
                  Plano XY (Base)
                </span>
                <span className="font-mono text-[10px] opacity-60">Z=0</span>
              </div>
              <div className="flex items-center justify-between px-2 py-1 rounded hover:bg-surface-container-high text-text-muted hover:text-text-primary text-[11px] cursor-pointer">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-fea-stress-optimal"></span>
                  Plano XZ (Simetría)
                </span>
                <span className="font-mono text-[10px] opacity-60">Y=0</span>
              </div>
              <div className="flex items-center justify-between px-2 py-1 rounded hover:bg-surface-container-high text-text-muted hover:text-text-primary text-[11px] cursor-pointer">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                  Plano YZ (Transversal)
                </span>
                <span className="font-mono text-[10px] opacity-60">X=0</span>
              </div>
            </div>
          )}

          {/* Sólido Importado STEP */}
          <div className="relative">
            <div className="group flex items-center justify-between px-2 py-1.5 rounded bg-surface-elevated/70 hover:bg-surface-elevated cursor-pointer transition-colors border border-border-subtle/30">
              <div
                className="flex items-center gap-2 min-w-0 flex-1"
                onClick={() => setShowModelPicker(!showModelPicker)}
              >
                <span className="material-symbols-outlined text-primary text-[18px]">deployed_code</span>
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-1">
                    <span className="text-text-primary font-semibold text-[12px] leading-tight truncate">
                      {currentModel.filename}
                    </span>
                    <span className="material-symbols-outlined text-text-muted text-[13px]">arrow_drop_down</span>
                  </div>
                  <span className="text-[10px] font-mono text-text-muted">
                    {currentModel.faces} Caras • {currentModel.edges} Aristas • {currentModel.solids} Sólido
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={onToggleModelVisibility}
                className="p-1 hover:bg-surface-container-high rounded text-secondary transition-colors"
                title={isModelVisible ? 'Ocultar pieza CAD' : 'Mostrar pieza CAD'}
              >
                <span className="material-symbols-outlined text-[16px]">
                  {isModelVisible ? 'visibility' : 'visibility_off'}
                </span>
              </button>
            </div>

            {showModelPicker && (
              <div className="absolute left-0 right-0 top-full mt-1 bg-surface-elevated border border-border-subtle rounded-md shadow-xl p-1 z-30">
                <div className="px-2 py-1 text-[10px] font-mono text-text-muted uppercase">Piezas CAD Disponibles:</div>
                {models.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      onSelectModel(m);
                      setShowModelPicker(false);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded text-[11px] flex items-center justify-between ${
                      m.id === currentModel.id
                        ? 'bg-secondary/15 text-secondary font-medium'
                        : 'hover:bg-surface-container-high text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <span className="font-mono">{m.filename}</span>
                    <span className="text-[9px] text-text-muted">{m.elementsTet4.toLocaleString()} tets</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Feature Conditions List */}
          {boundaryConditions.map((bc) => {
            const isLoad = bc.type === 'carga';
            const isFix = bc.type === 'fijacion';
            const isSafe = bc.type === 'preservada';
            const isKeepout = bc.type === 'keepout';

            let bgClass = 'bg-surface-container-high/40 hover:bg-surface-elevated';
            if (isSafe) bgClass = 'bg-fea-stress-optimal/10 hover:bg-fea-stress-optimal/15';
            if (isKeepout) bgClass = 'bg-fea-stress-critical/10 hover:bg-fea-stress-critical/15';

            return (
              <div
                key={bc.id}
                className={`flex items-center justify-between px-2 py-1.5 rounded cursor-pointer transition-colors border border-border-subtle/20 ${bgClass}`}
                onClick={() => onEditCondition(bc)}
              >
                <div className="flex items-center gap-2">
                  <div
                    className={`w-5 h-5 rounded flex items-center justify-center ${
                      isFix
                        ? 'bg-secondary/10'
                        : isLoad
                        ? 'bg-tertiary/10'
                        : isSafe
                        ? 'bg-fea-stress-optimal/20'
                        : 'bg-fea-stress-critical/20'
                    }`}
                  >
                    <span
                      className={`material-symbols-outlined text-[14px] ${
                        isFix
                          ? 'text-secondary'
                          : isLoad
                          ? 'text-tertiary'
                          : isSafe
                          ? 'text-fea-stress-optimal'
                          : 'text-fea-stress-critical'
                      }`}
                    >
                      {isFix ? 'anchor' : isLoad ? 'arrow_downward' : isSafe ? 'shield' : 'block'}
                    </span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-text-primary font-medium text-[11px]">{bc.name}</span>
                    <span
                      className={`text-[10px] font-mono ${
                        isFix
                          ? 'text-secondary'
                          : isLoad
                          ? 'text-tertiary'
                          : isSafe
                          ? 'text-fea-stress-optimal'
                          : 'text-fea-stress-critical'
                      }`}
                    >
                      {bc.details}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  {isFix && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleCondition(bc.id);
                      }}
                      className="text-fea-stress-optimal"
                      title="Fijación activa"
                    >
                      <span className="material-symbols-outlined text-[15px]">check_circle</span>
                    </button>
                  )}
                  {isLoad && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditCondition(bc);
                      }}
                      className="text-secondary hover:text-text-primary p-0.5"
                      title="Editar vector de carga"
                    >
                      <span className="material-symbols-outlined text-[15px]">edit</span>
                    </button>
                  )}
                  {isSafe && (
                    <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-fea-stress-optimal text-[#0b0e17] font-semibold">
                      SAFE
                    </span>
                  )}
                  {isKeepout && (
                    <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-fea-stress-critical text-[#0b0e17] font-semibold">
                      VOID
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Gmsh Meshing Controls Card */}
      <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-xs border border-border-subtle/40">
        <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated/70 rounded text-[11px] font-semibold text-text-primary">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-secondary text-[15px]">grid_on</span>
            <span>Generador de Malla Gmsh</span>
          </div>
          <span className="px-1 py-0.2 rounded bg-secondary/15 text-secondary font-mono text-[9px]">Tet4</span>
        </header>

        <div className="flex flex-col gap-2 p-1 text-[11px]">
          <div className="flex items-center justify-between">
            <span className="text-text-muted text-[10px] font-mono">Tamaño Elemento (h):</span>
            <span className="font-mono text-text-primary font-bold text-[11px]">{meshElementSize.toFixed(1)} mm</span>
          </div>
          <input
            type="range"
            min="0.8"
            max="3.5"
            step="0.1"
            value={meshElementSize}
            onChange={(e) => onChangeMeshSize(parseFloat(e.target.value))}
            className="w-full h-1 bg-surface-elevated rounded-lg appearance-none cursor-pointer accent-secondary"
          />

          <div className="grid grid-cols-2 gap-1.5 font-mono text-[10px] pt-1">
            <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30">
              <span className="text-text-muted block text-[9px]">Tetraedros:</span>
              <span className="text-secondary font-semibold">
                {Math.round(currentModel.elementsTet4 * (1.8 / meshElementSize)).toLocaleString()}
              </span>
            </div>
            <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30">
              <span className="text-text-muted block text-[9px]">Nodos FEA:</span>
              <span className="text-text-primary font-semibold">
                {Math.round(currentModel.nodes * (1.8 / meshElementSize)).toLocaleString()}
              </span>
            </div>
          </div>

          <button
            id="remesh-btn"
            type="button"
            onClick={onRemesh}
            disabled={isRemeshing}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-surface-elevated hover:bg-surface-container-high border border-border-subtle hover:border-secondary/40 text-text-primary hover:text-secondary text-[11px] font-medium transition-colors active:scale-95 disabled:opacity-50"
          >
            <span className={`material-symbols-outlined text-[15px] ${isRemeshing ? 'animate-spin text-secondary' : ''}`}>
              refresh
            </span>
            <span>{isRemeshing ? 'Generando Malla...' : 'Remallar Dominio CAD'}</span>
          </button>
        </div>
      </section>
    </aside>
  );
};
