import React from 'react';
import { ActiveTool } from '../types';

interface ToolbarProps {
  activeTool: ActiveTool;
  onSelectTool: (tool: ActiveTool) => void;
  showMesh: boolean;
  onToggleMesh: () => void;
  showSection: boolean;
  onToggleSection: () => void;
  onUndo: () => void;
  onRedo: () => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  activeTool,
  onSelectTool,
  showMesh,
  onToggleMesh,
  showSection,
  onToggleSection,
  onUndo,
  onRedo,
}) => {
  return (
    <div className="h-9 px-space-md bg-surface-container-low border-b border-border-subtle flex items-center justify-between overflow-x-auto select-none">
      <div className="flex items-center gap-1">
        {/* Seleccionar */}
        <button
          id="tool-select"
          type="button"
          onClick={() => onSelectTool('seleccionar')}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors shadow-sm ${
            activeTool === 'seleccionar'
              ? 'bg-surface-elevated text-secondary font-medium ring-1 ring-secondary/30'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Seleccionar entidad geométrica"
        >
          <span className="material-symbols-outlined text-[15px]">near_me</span>
          <span>Seleccionar</span>
        </button>

        {/* Medir */}
        <button
          id="tool-measure"
          type="button"
          onClick={() => onSelectTool('medir')}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
            activeTool === 'medir'
              ? 'bg-surface-elevated text-secondary font-medium ring-1 ring-secondary/30'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Medir cotas y distancias geométricas"
        >
          <span className="material-symbols-outlined text-[15px]">straighten</span>
          <span>Medir</span>
        </button>

        <div className="w-px h-4 bg-border-subtle mx-1"></div>

        {/* Carga */}
        <button
          id="tool-load"
          type="button"
          onClick={() => onSelectTool('carga')}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
            activeTool === 'carga'
              ? 'bg-surface-elevated text-tertiary font-medium ring-1 ring-tertiary/30'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Definir cargas mecánicas (Fuerzas y presiones)"
        >
          <span className="material-symbols-outlined text-[15px] text-tertiary">arrow_downward</span>
          <span>Carga</span>
        </button>

        {/* Fijación */}
        <button
          id="tool-fixation"
          type="button"
          onClick={() => onSelectTool('fijacion')}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
            activeTool === 'fijacion'
              ? 'bg-surface-elevated text-secondary font-medium ring-1 ring-secondary/30'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Definir condiciones de apoyo y empotramientos"
        >
          <span className="material-symbols-outlined text-[15px] text-secondary">anchor</span>
          <span>Fijación</span>
        </button>

        {/* Preservada */}
        <button
          id="tool-preserved"
          type="button"
          onClick={() => onSelectTool('preservada')}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
            activeTool === 'preservada'
              ? 'bg-surface-elevated text-fea-stress-optimal font-medium ring-1 ring-fea-stress-optimal/30'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Región no diseñable preservada (ρ = 1.0)"
        >
          <span className="material-symbols-outlined text-[15px] text-fea-stress-optimal">shield</span>
          <span>Preservada</span>
        </button>

        {/* Keep-out */}
        <button
          id="tool-keepout"
          type="button"
          onClick={() => onSelectTool('keepout')}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
            activeTool === 'keepout'
              ? 'bg-surface-elevated text-fea-stress-critical font-medium ring-1 ring-fea-stress-critical/30'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Zona de obstáculo prohibida (ρ = 0.0)"
        >
          <span className="material-symbols-outlined text-[15px] text-fea-stress-critical">block</span>
          <span>Keep-out</span>
        </button>

        <div className="w-px h-4 bg-border-subtle mx-1"></div>

        {/* Malla Gmsh */}
        <button
          id="tool-mesh"
          type="button"
          onClick={onToggleMesh}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
            showMesh
              ? 'bg-secondary/15 text-secondary border border-secondary/30 font-medium'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Visualizar malla de tetraedros (Gmsh)"
        >
          <span className="material-symbols-outlined text-[15px]">grid_on</span>
          <span>Malla Gmsh</span>
        </button>

        {/* Sección */}
        <button
          id="tool-section"
          type="button"
          onClick={onToggleSection}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
            showSection
              ? 'bg-secondary/15 text-secondary border border-secondary/30 font-medium'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Plano de corte interactivo de sección"
        >
          <span className="material-symbols-outlined text-[15px]">cut</span>
          <span>Sección</span>
        </button>

        <div className="w-px h-4 bg-border-subtle mx-1"></div>

        {/* REMESH-TOOL-START (reversible): remallado como herramienta (abre
            sus parametros en el panel bajo el arbol). Para volver atras:
            borrar este bloque. */}
        <button
          id="tool-remesh"
          type="button"
          onClick={() => onSelectTool('malla')}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] transition-colors ${
            activeTool === 'malla'
              ? 'bg-surface-elevated text-secondary font-medium ring-1 ring-secondary/30'
              : 'hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
          }`}
          title="Remallar dominio CAD (Gmsh Tet4)"
        >
          <span className="material-symbols-outlined text-[15px]">refresh</span>
          <span>Remallar</span>
        </button>
        {/* REMESH-TOOL-END */}
      </div>

      {/* Undo / Redo */}
      <div className="flex items-center gap-1">
        <button
          id="undo-btn"
          type="button"
          onClick={onUndo}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-elevated text-text-muted hover:text-text-primary transition-colors"
          title="Deshacer (Ctrl+Z)"
        >
          <span className="material-symbols-outlined text-[16px]">undo</span>
        </button>
        <button
          id="redo-btn"
          type="button"
          onClick={onRedo}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-elevated text-text-muted hover:text-text-primary transition-colors"
          title="Rehacer (Ctrl+Y)"
        >
          <span className="material-symbols-outlined text-[16px]">redo</span>
        </button>
      </div>
    </div>
  );
};
