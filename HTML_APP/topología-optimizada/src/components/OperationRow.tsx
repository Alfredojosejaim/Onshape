// UI-CLEAN (reversible): fila de operacion del arbol, con la ESTETICA
// aprobada de la lista de condiciones. Las operaciones reales futuras
// (boolean/transform/mirror/pattern/generativo/estudios) deben reutilizar
// este componente para verse igual. Extraido sin ningun cambio visual:
// mismas clases, mismos iconos, mismos badges.
// Para volver atras: borrar este archivo y devolver el bloque inline
// marcado UI-CLEAN-OPROW en LeftPanel.tsx.
import React, { useState } from 'react';
import { BoundaryCondition, SolidInfo } from '../types';

interface OperationRowProps {
  bc: BoundaryCondition;
  onToggleCondition: (id: string) => void;
  onEditCondition: (condition: BoundaryCondition) => void;
  // TOOL-OPEN (reversible): clic o doble clic en la fila reabre su
  // herramienta (panel de parametros). El lapiz abre el modal de edicion.
  // Para volver atras: quitar prop + handlers y devolver onClick al modal.
  onActivateTool?: (bc: BoundaryCondition) => void;
  // TREE-RENAME-INLINE (reversible): doble clic en el nombre edita in situ
  // estilo Onshape (Enter/blur confirma, Escape cancela). El modal con lapiz
  // tambien tiene el campo. Para volver atras: quitar prop + bloque.
  onRenameCondition?: (bc: BoundaryCondition, name: string) => void;
}

export const OperationRow: React.FC<OperationRowProps> = ({
  bc,
  onToggleCondition,
  onEditCondition,
  onActivateTool,
  onRenameCondition,
}) => {
  const isLoad = bc.type === 'carga';
  const isFix = bc.type === 'fijacion';
  const isSafe = bc.type === 'preservada';
  const isKeepout = bc.type === 'keepout';

  let bgClass = 'bg-surface-container-high/40 hover:bg-surface-elevated';
  if (isSafe) bgClass = 'bg-fea-stress-optimal/10 hover:bg-fea-stress-optimal/15';
  if (isKeepout) bgClass = 'bg-fea-stress-critical/10 hover:bg-fea-stress-critical/15';

  // TREE-RENAME-INLINE: edicion in situ del nombre.
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState('');
  const commitRename = () => {
    if (renaming && onRenameCondition) {
      const name = draft.trim() || bc.name;
      if (name !== bc.name) onRenameCondition(bc, name);
    }
    setRenaming(false);
  };

  return (
    <div
      key={bc.id}
      className={`flex items-center justify-between px-2 py-1.5 rounded cursor-pointer transition-colors border border-border-subtle/20 ${bgClass}`}
      // TOOL-OPEN: clic abre la herramienta en el panel (no el modal, para
      // no tapar el viewport); el lapiz sigue abriendo el modal de edicion.
      onClick={() => {
        if (onActivateTool) onActivateTool(bc);
        else onEditCondition(bc);
      }}
      onDoubleClick={() => {
        if (onActivateTool) onActivateTool(bc);
      }}
      title="Clic: abrir herramienta • Lápiz: editar en ventana"
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
        <div className="flex flex-col min-w-0">
          {renaming ? (
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={commitRename}
              onKeyDown={(e) => {
                // Enter confirma sin cerrar la herramienta (no burbujea al
                // atajo global); Escape cancela.
                e.stopPropagation();
                if (e.key === 'Enter') commitRename();
                else if (e.key === 'Escape') setRenaming(false);
              }}
              onClick={(e) => e.stopPropagation()}
              onDoubleClick={(e) => e.stopPropagation()}
              aria-label="Renombrar herramienta"
              className="bg-surface-elevated border border-secondary/60 rounded px-1.5 py-0.5 text-text-primary text-[11px] outline-none w-full"
            />
          ) : (
            <span
              className="text-text-primary font-medium text-[11px] truncate"
              onDoubleClick={(e) => {
                e.stopPropagation();
                if (onRenameCondition) {
                  setDraft(bc.name);
                  setRenaming(true);
                }
              }}
              title="Doble clic para renombrar"
            >
              {bc.name}
            </span>
          )}
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
        {/* TREE-CLEAN (reversible): quitados el tilde de fijacion, el badge
            SAFE de preservada y el badge VOID de keep-out; solo queda el
            lapiz de edicion. Para volver atras: restaurar desde git. */}
        {/* TOOL-OPEN: lapiz en TODAS las herramientas (antes solo carga).
            Abre el modal de edicion sin activar la herramienta. */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onEditCondition(bc);
          }}
          className="text-secondary hover:text-text-primary p-0.5"
          title="Editar en ventana"
        >
          <span className="material-symbols-outlined text-[15px]">edit</span>
        </button>
      </div>
    </div>
  );
};

// SOLIDS-START (reversible): fila por cuerpo del STEP con la MISMA estetica
// aprobada (mismas clases, iconos, badges). Para volver atras: borrar este
// componente + su uso en LeftPanel.tsx.
export interface SolidOpRowProps {
  solid: SolidInfo;
  // UI-CLEAN2 (reversible): permite la fila Malla con la misma estetica.
  icon?: string;
  badge?: string;
  details?: string;
  // MULTI-VIEW (reversible): ojo ver/ocultar por cuerpo. Para volver atras:
  // quitar props + boton.
  visible?: boolean;
  onToggleVisibility?: () => void;
  visibilityTitle?: string;
}

export const SolidOpRow: React.FC<SolidOpRowProps> = ({
  solid,
  icon = 'deployed_code',
  badge = 'SOLID',
  details,
  visible = true,
  onToggleVisibility,
  visibilityTitle = 'Mostrar / ocultar cuerpo',
}) => {
  const volCm3 =
    typeof solid.volume === 'number' && Number.isFinite(solid.volume)
      ? (solid.volume / 1000).toFixed(1)
      : '—';
  return (
    <div className={`flex items-center justify-between px-2 py-1.5 rounded cursor-pointer transition-colors border border-border-subtle/20 bg-surface-container-high/40 hover:bg-surface-elevated ${visible ? '' : 'opacity-50'}`}>
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 rounded flex items-center justify-center bg-secondary/10">
          <span className="material-symbols-outlined text-[14px] text-secondary">
            {icon}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-text-primary font-medium text-[11px]">{solid.name}</span>
          <span className="text-[10px] font-mono text-secondary">
            {details ?? `${solid.faces_count} Caras • ${volCm3} cm³`}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        {/* MULTI-VIEW (reversible): ver/ocultar cuerpo en el viewport unico. */}
        {onToggleVisibility && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleVisibility();
            }}
            className={`p-0.5 transition-colors ${visible ? 'text-text-secondary hover:text-text-primary' : 'text-text-muted hover:text-text-secondary'}`}
            title={visibilityTitle}
          >
            <span className="material-symbols-outlined text-[15px]">
              {visible ? 'visibility' : 'visibility_off'}
            </span>
          </button>
        )}
        <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-secondary/15 text-secondary font-semibold">
          {badge}
        </span>
      </div>
    </div>
  );
};
// SOLIDS-END
