import React, { useState } from 'react';
import { BoundaryCondition, CadModelPreset, SolidInfo } from '../types';
// UI-CLEAN-START (reversible: quitar import y devolver bloque inline UI-CLEAN-OPROW de abajo)
import { OperationRow, SolidOpRow } from './OperationRow';
// UI-CLEAN-END

interface LeftPanelProps {
  // UI-CLEAN (reversible): null = arbol limpio, sin pieza de referencia.
  currentModel: CadModelPreset | null;
  models: CadModelPreset[];
  onSelectModel: (model: CadModelPreset) => void;
  // SOLIDS (reversible): cuerpos del STEP, una operacion por objeto.
  solids: SolidInfo[];
  // UI-CLEAN2 (reversible): malla volumetrica real presente.
  hasMesh: boolean;
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
  // SOLIDS (reversible)
  solids,
  // UI-CLEAN2 (reversible)
  hasMesh,
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
  // UI-CLEAN2 (reversible): sin nodo archivo no hay picker local.
  // models/onSelectModel/isModelVisible/onToggleModelVisibility se conservan
  // en props para seleccion futura y compatibilidad con App.
  // SOLIDS (reversible): planesOpen se fue con las coordenadas.

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
          {/* SOLIDS-START (reversible): coordenadas fuera del arbol.
              El bloque "Sist. Coordenado Global" + planos se elimino;
              para volver atras restaurarlo desde git. */}

          {/* UI-CLEAN2-START (reversible): solo objetos, sin nodo archivo.
              El bloque del archivo importado (nombre + picker + visibilidad)
              se elimino: el arbol lista unicamente solidos y malla.
              Para volver atras: restaurar desde git. */}
          {currentModel === null ? (
            <div className="px-2 py-2 rounded border border-dashed border-border-subtle/50 text-[11px] text-text-muted text-center">
              Sin modelo —{' '}
              <button onClick={onOpenImport} className="text-secondary hover:underline font-mono">
                Importa un STEP
              </button>
            </div>
          ) : (
            <>
          {/* UI-CLEAN2-END (el cierre del fragmento esta mas abajo) */}

          {/* SOLIDS-START (reversible): una operacion por cuerpo del STEP,
              con la estetica aprobada (SolidOpRow). Sin cuerpos reales y con
              modelo local: una fila generica. Para volver atras: borrar. */}
          {currentModel !== null &&
            (solids.length > 0 ? (
              solids.map((s) => <SolidOpRow key={s.solid_id} solid={s} />)
            ) : (
              <SolidOpRow
                solid={{
                  solid_id: 'solid_0',
                  index: 0,
                  name: currentModel.displayName,
                  volume: currentModel.volumeCm3 * 1000,
                  faces_count: currentModel.faces,
                  center: null,
                }}
              />
            ))}
          {/* SOLIDS-END */}
          {/* UI-CLEAN2-START (reversible): fila Malla cuando hay malla
              volumetrica real (snapshot has_mesh). Para volver: borrar. */}
          {currentModel !== null && hasMesh && (
            <SolidOpRow
              icon="grid_on"
              badge="MESH"
              details={`${currentModel.elementsTet4.toLocaleString()} tets • ${currentModel.nodes.toLocaleString()} nodos`}
              solid={{
                solid_id: 'mesh_tet4',
                index: -1,
                name: 'Malla Tet4',
                volume: null,
                faces_count: currentModel.elementsTet4,
                center: null,
              }}
            />
          )}
          {/* UI-CLEAN2-END */}
            </>
          )}
          {/* UI-CLEAN2-END (cierre: solo objetos, sin nodo archivo) */}

          {/* Feature Conditions List */}
          {/* UI-CLEAN-OPROW-START (reversible): lista extraida a OperationRow
              (estetica identica). El bloque inline original se movio a
              src/components/OperationRow.tsx. Para volver atras, pegar de
              vuelta el bloque y quitar el import + este map. */}
          {boundaryConditions.length === 0 ? (
            <div className="px-2 py-1.5 rounded border border-dashed border-border-subtle/50 text-[11px] text-text-muted text-center">
              Sin operaciones
            </div>
          ) : (
            boundaryConditions.map((bc) => (
              <OperationRow
                key={bc.id}
                bc={bc}
                onToggleCondition={onToggleCondition}
                onEditCondition={onEditCondition}
              />
            ))
          )}
          {/* UI-CLEAN-OPROW-END */}
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
                {/* UI-CLEAN (reversible): 0 sin modelo real */}
                {currentModel
                  ? Math.round(currentModel.elementsTet4 * (1.8 / meshElementSize)).toLocaleString()
                  : '—'}
              </span>
            </div>
            <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30">
              <span className="text-text-muted block text-[9px]">Nodos FEA:</span>
              <span className="text-text-primary font-semibold">
                {currentModel
                  ? Math.round(currentModel.nodes * (1.8 / meshElementSize)).toLocaleString()
                  : '—'}
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
