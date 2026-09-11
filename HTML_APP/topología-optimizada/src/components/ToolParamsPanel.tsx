// TOOLPARAMS-START (reversible): panel de parametros de la herramienta
// ACTIVA bajo el arbol de operaciones (ocupa el sitio de la tarjeta
// "Generador de Malla Gmsh", eliminada en este cambio). Razon: editar aqui
// deja libre el viewport para picar caras. Para volver atras: borrar este
// archivo + su uso en LeftPanel.tsx y restaurar la tarjeta Gmsh desde git.
import React, { useEffect, useState } from 'react';
import { ActiveTool, BoundaryCondition, CadModelPreset } from '../types';

interface ToolParamsPanelProps {
  activeTool: ActiveTool;
  boundaryConditions: BoundaryCondition[];
  onSaveCondition: (condition: BoundaryCondition) => void;
  // Aceptar (o Enter/Escape): cierra la herramienta -> 'seleccionar'.
  onConfirmTool: () => void;
  // MULTI-COND (reversible): condicion destino + crear otra del mismo tipo.
  // Cada instancia (Carga 1, Carga 2...) es su propia herramienta: se cambia
  // desde el arbol, aqui solo se edita la destino. Para volver atras: quitar.
  targetCondId: string | null;
  onNewCondition: () => void;
  // Reenvia al backend lo editado en el panel (vector/normal de carga).
  onPushCondition: (condition: BoundaryCondition) => void;
  // REMESH-TOOL (reversible): parametros heredados de la tarjeta Gmsh.
  // Para volver atras: quitar + caso 'malla' de abajo.
  currentModel: CadModelPreset | null;
  meshElementSize: number;
  onChangeMeshSize: (size: number) => void;
  onRemesh: () => void;
  isRemeshing: boolean;
}

const TOOL_META: Record<ActiveTool, { name: string; icon: string; cls: string }> = {
  seleccionar: { name: 'Seleccionar', icon: 'near_me', cls: 'text-secondary' },
  medir: { name: 'Medir', icon: 'straighten', cls: 'text-secondary' },
  carga: { name: 'Carga', icon: 'arrow_downward', cls: 'text-tertiary' },
  fijacion: { name: 'Fijación', icon: 'anchor', cls: 'text-secondary' },
  preservada: { name: 'Preservada', icon: 'shield', cls: 'text-fea-stress-optimal' },
  keepout: { name: 'Keep-out', icon: 'block', cls: 'text-fea-stress-critical' },
  malla: { name: 'Malla', icon: 'grid_on', cls: 'text-secondary' },
  seccion: { name: 'Sección', icon: 'cut', cls: 'text-secondary' },
};

function facesText(cond: BoundaryCondition | null): string {
  const idx = cond?.faceIndices ?? [];
  if (idx.length === 0) return 'sin caras asignadas';
  return [...idx].sort((a, b) => a - b).map((f) => `face_${f}`).join(', ');
}

export const ToolParamsPanel: React.FC<ToolParamsPanelProps> = ({
  activeTool,
  boundaryConditions,
  onSaveCondition,
  onConfirmTool,
  targetCondId,
  onNewCondition,
  onPushCondition,
  currentModel,
  meshElementSize,
  onChangeMeshSize,
  onRemesh,
  isRemeshing,
}) => {
  const meta = TOOL_META[activeTool];
  const isFaceTool =
    activeTool === 'carga' || activeTool === 'fijacion' ||
    activeTool === 'preservada' || activeTool === 'keepout';
  // MULTI-COND: condiciones del mismo tipo + destino (selector del panel).
  const toolConds = isFaceTool
    ? boundaryConditions.filter((c) => c.type === activeTool)
    : [];
  const cond = isFaceTool
    ? (targetCondId ? toolConds.find((c) => c.id === targetCondId) ?? null : null) ??
      toolConds[0] ?? null
    : null;

  return (
    <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-xs border border-border-subtle/40">
      <header className="flex items-center justify-between px-space-xs py-1 bg-surface-elevated/70 rounded text-[11px] font-semibold text-text-primary">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`material-symbols-outlined text-[15px] ${meta.cls}`}>{meta.icon}</span>
          {/* MULTI-COND: nombre de la instancia en edicion (Carga 1...),
              no del tipo. El renombrado vive en el arbol (doble clic). */}
          <span className="truncate">{isFaceTool && cond ? cond.name : meta.name}</span>
        </div>
        {isFaceTool && (
          <span className="px-1 py-0.2 rounded bg-secondary/15 text-secondary font-mono text-[9px]">ACTIVA</span>
        )}
      </header>

      <div className="flex flex-col gap-2 p-1 text-[11px]">
        {activeTool === 'seleccionar' && (
          <p className="text-text-muted text-[11px] leading-relaxed">
            Elige <strong className="text-text-primary">Carga, Fijación, Preservada o Keep-out</strong> en
            la barra y pica caras en el viewport. Acepta con <strong className="text-text-primary">Enter</strong> para
            cerrar la herramienta.
          </p>
        )}

        {activeTool === 'medir' && (
          <p className="text-text-muted text-[11px] leading-relaxed">
            Pica dos puntos del modelo para medir. <strong className="text-text-primary">Enter</strong> o
            Aceptar para cerrar la herramienta.
          </p>
        )}

        {isFaceTool && (
          <div className="flex items-center gap-1.5">
            {/* MULTI-COND: cada instancia es su propia herramienta (se cambia
                desde el arbol). + Nueva crea otra y salta a ella. */}
            <span className="flex-1 min-w-0 truncate text-text-secondary text-[10px] font-mono">
              {toolConds.length > 0
                ? `${toolConds.length} aplicada${toolConds.length > 1 ? 's' : ''} de este tipo`
                : 'sin aplicar aún'}
            </span>
            <button
              type="button"
              onClick={onNewCondition}
              title={`Nueva ${meta.name.toLowerCase()} (otra herramienta del mismo tipo)`}
              className="px-2 py-1 rounded bg-surface-elevated hover:bg-surface-container-high border border-border-subtle hover:border-secondary/40 text-text-primary hover:text-secondary text-[11px] font-medium transition-colors active:scale-95 whitespace-nowrap"
            >
              + Nueva
            </button>
          </div>
        )}

        {isFaceTool && activeTool !== 'carga' && (
          <div className="flex flex-col gap-1.5">
            <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30">
              <span className="text-text-muted block text-[9px] font-mono">Caras asignadas:</span>
              <span className="text-secondary font-mono text-[10px] break-all">{facesText(cond)}</span>
            </div>
            <p className="text-text-muted text-[10px] leading-relaxed">
              Pica caras en el viewport para añadirlas (re-picar quita). Doble clic en su fila del
              árbol reabre esta herramienta.
            </p>
          </div>
        )}

        {activeTool === 'carga' && (
          <CargaEditor
            cond={cond}
            onSaveCondition={onSaveCondition}
            onPushCondition={onPushCondition}
            onConfirmTool={onConfirmTool}
          />
        )}

        {/* REMESH-TOOL-START (reversible): parametros de la antigua tarjeta
            Gmsh, ahora como herramienta (se abre con Remallar en la barra).
            Para volver atras: borrar este bloque + props. */}
        {activeTool === 'malla' && (
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
            <div className="grid grid-cols-2 gap-1.5 font-mono text-[10px]">
              <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30">
                <span className="text-text-muted block text-[9px]">Tetraedros:</span>
                <span className="text-secondary font-semibold">
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
            <button
              type="button"
              onClick={onConfirmTool}
              className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-primary-container hover:bg-secondary text-on-primary text-[11px] font-semibold transition-colors active:scale-95"
            >
              <span className="material-symbols-outlined text-[15px]">check</span>
              <span>Aceptar (Enter)</span>
            </button>
          </div>
        )}
        {/* REMESH-TOOL-END */}

        {activeTool !== 'seleccionar' && activeTool !== 'carga' && activeTool !== 'malla' && (
          <button
            type="button"
            onClick={onConfirmTool}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-primary-container hover:bg-secondary text-on-primary text-[11px] font-semibold transition-colors active:scale-95"
          >
            <span className="material-symbols-outlined text-[15px]">check</span>
            <span>Aceptar (Enter)</span>
          </button>
        )}
      </div>
    </section>
  );
};

// Editor del vector + direccion de carga (antes en el modal de edicion;
// movido aqui para no tapar el viewport). Guarda en vivo sobre la condicion
// destino (la crea si aun no existe: queda inactiva hasta picar caras) y
// reenvia al backend via onPushCondition.
// LOAD-DIR (reversible): direccion = normal de referencia del core
// (LoadCondition perpendicular + reference_plane_normal). Para volver atras:
// quitar el select + loadNormal.
type LoadDir = 'X' | 'Y' | 'Z';
const LOAD_DIRS: Record<LoadDir, [number, number, number]> = {
  X: [1, 0, 0],
  Y: [0, 1, 0],
  Z: [0, 0, 1],
};

function dirFromNormal(n: [number, number, number] | undefined): LoadDir {
  if (n && n[0] === 1 && n[1] === 0 && n[2] === 0) return 'X';
  if (n && n[0] === 0 && n[1] === 1 && n[2] === 0) return 'Y';
  return 'Z';
}

function CargaEditor({
  cond,
  onSaveCondition,
  onPushCondition,
  onConfirmTool,
}: {
  cond: BoundaryCondition | null;
  onSaveCondition: (c: BoundaryCondition) => void;
  onPushCondition: (c: BoundaryCondition) => void;
  onConfirmTool: () => void;
}) {
  const [fx, setFx] = useState('0');
  const [fy, setFy] = useState('-4500');
  const [fz, setFz] = useState('1200');
  const [dir, setDir] = useState<LoadDir>('Z');

  // Carga los valores guardados al abrir/cambiar de condicion.
  useEffect(() => {
    const v = cond?.value;
    if (v && v.length === 3) {
      setFx(String(v[0]));
      setFy(String(v[1]));
      setFz(String(v[2]));
    }
    setDir(dirFromNormal(cond?.loadNormal));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cond?.id]);

  const saveAll = (
    sx: string, sy: string, sz: string, d: LoadDir, live: boolean,
  ): BoundaryCondition | null => {
    const nx = parseFloat(sx);
    const ny = parseFloat(sy);
    const nz = parseFloat(sz);
    if (live && (!Number.isFinite(nx) || !Number.isFinite(ny) || !Number.isFinite(nz))) return null;
    const vx = Number.isFinite(nx) ? nx : 0;
    const vy = Number.isFinite(ny) ? ny : 0;
    const vz = Number.isFinite(nz) ? nz : 0;
    const mag = Math.hypot(vx, vy, vz);
    const details = `[${vx}, ${vy}, ${vz}] N · dir ${d}`;
    const updated: BoundaryCondition = cond
      ? { ...cond, value: [vx, vy, vz], magnitude: mag, details, loadNormal: LOAD_DIRS[d] }
      : {
          id: 'faces_carga',
          name: 'Carga en caras',
          type: 'carga',
          details,
          value: [vx, vy, vz],
          magnitude: mag,
          loadNormal: LOAD_DIRS[d],
          faces: 0,
          faceIndices: [],
          active: false,
        };
    onSaveCondition(updated);
    onPushCondition(updated);
    return updated;
  };

  const confirm = () => {
    saveAll(fx, fy, fz, dir, false);
    onConfirmTool();
  };

  const numCls =
    'flex-1 bg-surface-elevated border border-border-subtle rounded px-2 py-1 text-text-primary font-mono text-[11px] outline-none focus:border-secondary/60';
  return (
    <div className="flex flex-col gap-2 font-mono text-[11px]">
      <span className="text-text-muted">Vector fuerza [N]:</span>
      {(
        [
          ['Fx', fx, setFx, 'text-fea-stress-critical'],
          ['Fy', fy, setFy, 'text-fea-stress-optimal'],
          ['Fz', fz, setFz, 'text-secondary'],
        ] as [string, string, React.Dispatch<React.SetStateAction<string>>, string][]
      ).map(([label, val, setVal, color]) => (
        <div key={label} className="flex items-center gap-2">
          <span className={`${color} font-bold`}>{label}:</span>
          <input
            type="number"
            value={val}
            onChange={(e) => {
              setVal(e.target.value);
              const cur = { Fx: fx, Fy: fy, Fz: fz, [label]: e.target.value };
              saveAll(cur.Fx, cur.Fy, cur.Fz, dir, true);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') confirm();
            }}
            className={numCls}
          />
        </div>
      ))}
      <div className="flex items-center gap-2">
        <span className="text-text-muted">Dirección:</span>
        <select
          aria-label="Dirección de la carga"
          value={dir}
          onChange={(e) => {
            const d = e.target.value as LoadDir;
            setDir(d);
            saveAll(fx, fy, fz, d, false);
          }}
          className="flex-1 bg-surface-elevated border border-border-subtle rounded px-2 py-1 text-text-primary text-[11px] outline-none focus:border-secondary/60"
        >
          <option value="Z">Perpendicular Z (defecto)</option>
          <option value="X">Eje X</option>
          <option value="Y">Eje Y</option>
        </select>
      </div>
      <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30">
        <span className="text-text-muted block text-[9px]">Caras asignadas:</span>
        <span className="text-secondary text-[10px] break-all">{facesText(cond)}</span>
      </div>
      <button
        type="button"
        onClick={confirm}
        className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-primary-container hover:bg-secondary text-on-primary text-[11px] font-semibold transition-colors active:scale-95"
      >
        <span className="material-symbols-outlined text-[15px]">check</span>
        <span>Aceptar (Enter)</span>
      </button>
    </div>
  );
}
