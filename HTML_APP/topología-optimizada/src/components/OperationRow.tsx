// UI-CLEAN (reversible): fila de operacion del arbol, con la ESTETICA
// aprobada de la lista de condiciones. Las operaciones reales futuras
// (boolean/transform/mirror/pattern/generativo/estudios) deben reutilizar
// este componente para verse igual. Extraido sin ningun cambio visual:
// mismas clases, mismos iconos, mismos badges.
// Para volver atras: borrar este archivo y devolver el bloque inline
// marcado UI-CLEAN-OPROW en LeftPanel.tsx.
import React from 'react';
import { BoundaryCondition, SolidInfo } from '../types';

interface OperationRowProps {
  bc: BoundaryCondition;
  onToggleCondition: (id: string) => void;
  onEditCondition: (condition: BoundaryCondition) => void;
}

export const OperationRow: React.FC<OperationRowProps> = ({
  bc,
  onToggleCondition,
  onEditCondition,
}) => {
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
};

// SOLIDS-START (reversible): fila por cuerpo del STEP con la MISMA estetica
// aprobada (mismas clases, iconos, badges). Para volver atras: borrar este
// componente + su uso en LeftPanel.tsx.
export interface SolidOpRowProps {
  solid: SolidInfo;
}

export const SolidOpRow: React.FC<SolidOpRowProps> = ({ solid }) => {
  const volCm3 =
    typeof solid.volume === 'number' && Number.isFinite(solid.volume)
      ? (solid.volume / 1000).toFixed(1)
      : '—';
  return (
    <div className="flex items-center justify-between px-2 py-1.5 rounded cursor-pointer transition-colors border border-border-subtle/20 bg-surface-container-high/40 hover:bg-surface-elevated">
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 rounded flex items-center justify-center bg-secondary/10">
          <span className="material-symbols-outlined text-[14px] text-secondary">
            deployed_code
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-text-primary font-medium text-[11px]">{solid.name}</span>
          <span className="text-[10px] font-mono text-secondary">
            {solid.faces_count} Caras • {volCm3} cm³
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-secondary/15 text-secondary font-semibold">
          SOLID
        </span>
      </div>
    </div>
  );
};
// SOLIDS-END
