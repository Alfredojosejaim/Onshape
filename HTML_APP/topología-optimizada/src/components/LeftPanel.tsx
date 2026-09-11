import React, { useState } from 'react';
import { ActiveTool, BoundaryCondition, CadModelPreset, SolidInfo } from '../types';
// MULTI-VIEW (reversible): clave de cuerpo para ver/ocultar.
import { bodyKey } from '../lib/faces';
// UI-CLEAN-START (reversible: quitar import y devolver bloque inline UI-CLEAN-OPROW de abajo)
import { OperationRow, SolidOpRow } from './OperationRow';
// TOOLPARAMS-START (reversible: quitar import + tarjeta y restaurar Gmsh desde git)
import { ToolParamsPanel } from './ToolParamsPanel';
// TOOLPARAMS-END
// UI-CLEAN-END

interface LeftPanelProps {
  // UI-CLEAN (reversible): null = arbol limpio, sin pieza de referencia.
  currentModel: CadModelPreset | null;
  models: CadModelPreset[];
  onSelectModel: (model: CadModelPreset) => void;
  // MULTI (reversible): arbol acumulativo — un grupo por archivo importado.
  // solidsByFile/meshByFile cachean lo ya importado (clave: filename).
  // Para volver atras: restaurar props solids/hasMesh + bloque single-model.
  solidsByFile: Record<string, SolidInfo[]>;
  meshByFile: Record<string, boolean>;
  // MULTI-VIEW (reversible): ver/ocultar por cuerpo. Para volver atras:
  // quitar props + ojo de las filas.
  hiddenBodies: Record<string, boolean>;
  onToggleBodyVisibility: (key: string) => void;
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
  // TOOLPARAMS (reversible): parametros de la herramienta activa + ciclo de
  // herramienta (Aceptar/Enter). Para volver atras: quitar estas 4 props.
  activeTool: ActiveTool;
  onConfirmTool: () => void;
  onSaveCondition: (condition: BoundaryCondition) => void;
  onActivateTool: (bc: BoundaryCondition) => void;
  // MULTI-COND (reversible): destino + crear otra del mismo tipo.
  targetCondId: string | null;
  onNewCondition: () => void;
  onPushCondition: (condition: BoundaryCondition) => void;
}

export const LeftPanel: React.FC<LeftPanelProps> = ({
  currentModel,
  models,
  onSelectModel,
  // MULTI (reversible)
  solidsByFile,
  meshByFile,
  // MULTI-VIEW (reversible)
  hiddenBodies,
  onToggleBodyVisibility,
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
  // TOOLPARAMS (reversible)
  activeTool,
  onConfirmTool,
  onSaveCondition,
  onActivateTool,
  // MULTI-COND (reversible)
  targetCondId,
  onNewCondition,
  onPushCondition,
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
            <span>Árbol de Operaciones</span>
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
        {/* TREE-SCROLL (reversible): lista con scroll propio estilo Onshape:
            el arbol puede crecer sin empujar el panel de herramienta, que
            queda fijo debajo. Para volver atras: quitar max-h/overflow. */}
        <div className="flex flex-col gap-1 py-1 text-[11px] text-text-secondary max-h-[34vh] overflow-y-auto pr-0.5">
          {/* MULTI-FLAT-START (reversible): solo cuerpos, sin distincion de
              archivo. Todos los solidos y mallas de todos los modelos
              importados en una lista plana; clic en un cuerpo activa su
              modelo. Para volver atras: restaurar grupos por archivo (git). */}
          {models.length === 0 ? (
            <div className="px-2 py-2 rounded border border-dashed border-border-subtle/50 text-[11px] text-text-muted text-center">
              Sin modelo —{' '}
              <button onClick={onOpenImport} className="text-secondary hover:underline font-mono">
                Importa un STEP
              </button>
            </div>
          ) : (
            models.flatMap((m) => {
              const mSolids = solidsByFile[m.filename];
              const mHasMesh = meshByFile[m.filename] ?? false;
              const rows = [];
              if (mSolids !== undefined && mSolids.length > 0) {
                for (const s of mSolids) {
                  const key = bodyKey(m.filename, s.solid_id);
                  rows.push(
                    <div key={key} onClick={() => onSelectModel(m)}>
                      <SolidOpRow
                        solid={s}
                        visible={!hiddenBodies[key]}
                        onToggleVisibility={() => onToggleBodyVisibility(key)}
                        visibilityTitle={`Mostrar / ocultar ${s.name}`}
                      />
                    </div>
                  );
                }
              } else {
                const key = bodyKey(m.filename, 'solid_0');
                rows.push(
                  <div key={key} onClick={() => onSelectModel(m)}>
                    <SolidOpRow
                      solid={{
                        solid_id: 'solid_0',
                        index: 0,
                        name: m.displayName,
                        volume: m.volumeCm3 * 1000,
                        faces_count: m.faces,
                        center: null,
                      }}
                      visible={!hiddenBodies[key]}
                      onToggleVisibility={() => onToggleBodyVisibility(key)}
                      visibilityTitle={`Mostrar / ocultar ${m.displayName}`}
                    />
                  </div>
                );
              }
              if (mHasMesh) {
                const key = bodyKey(m.filename, 'mesh_tet4');
                rows.push(
                  <div key={key} onClick={() => onSelectModel(m)}>
                    <SolidOpRow
                      icon="grid_on"
                      badge="MESH"
                      details={`${m.elementsTet4.toLocaleString()} tets • ${m.nodes.toLocaleString()} nodos`}
                      solid={{
                        solid_id: 'mesh_tet4',
                        index: -1,
                        name: 'Malla Tet4',
                        volume: null,
                        faces_count: m.elementsTet4,
                        center: null,
                      }}
                      visible={!hiddenBodies[key]}
                      onToggleVisibility={() => onToggleBodyVisibility(key)}
                      visibilityTitle="Mostrar / ocultar malla"
                    />
                  </div>
                );
              }
              return rows;
            })
          )}
          {/* MULTI-FLAT-END */}

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
                onActivateTool={onActivateTool}
                onRenameCondition={(c, name) => onSaveCondition({ ...c, name })}
              />
            ))
          )}
          {/* UI-CLEAN-OPROW-END */}
        </div>
      </section>

      {/* TOOLPARAMS-START (reversible): parametros de la herramienta activa
          en el sitio de la tarjeta "Generador de Malla Gmsh" (eliminada: los
          menus de herramienta viven aqui para dejar libre el viewport).
          Para volver atras: borrar este bloque y restaurar la tarjeta Gmsh
          desde git (props meshElementSize/onChangeMeshSize/onRemesh/
          isRemeshing/currentModel se conservan a proposito). */}
      <ToolParamsPanel
        activeTool={activeTool}
        boundaryConditions={boundaryConditions}
        onSaveCondition={onSaveCondition}
        onConfirmTool={onConfirmTool}
        targetCondId={targetCondId}
        onNewCondition={onNewCondition}
        onPushCondition={onPushCondition}
        currentModel={currentModel}
        meshElementSize={meshElementSize}
        onChangeMeshSize={onChangeMeshSize}
        onRemesh={onRemesh}
        isRemeshing={isRemeshing}
      />
      {/* TOOLPARAMS-END */}
    </aside>
  );
};
