// TOOLPARAMS-START (reversible): panel de parametros de la herramienta
// ACTIVA bajo el arbol de operaciones (ocupa el sitio de la tarjeta
// "Generador de Malla Gmsh", eliminada en este cambio). Razon: editar aqui
// deja libre el viewport para picar caras. Para volver atras: borrar este
// archivo + su uso en LeftPanel.tsx y restaurar la tarjeta Gmsh desde git.
import React, { useEffect, useState } from 'react';
import { ActiveTool, BoundaryCondition, CadModelPreset, MeshToolAction } from '../types';

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
  // MALLA-TOOLS (reversible): ejecuta herramienta de malla (App llama al
  // backend y publica el resultado en el panel derecho). meshBusy = accion
  // en curso (deshabilita Aplicar). Para volver atras: quitar + ramas malla-*.
  onMeshTool: (action: MeshToolAction, params: Record<string, number>) => void;
  meshBusy: string | null;
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
  'malla-diagnosticar': { name: 'Diagnosticar', icon: 'troubleshoot', cls: 'text-secondary' },
  'malla-reparar': { name: 'Reparar', icon: 'healing', cls: 'text-secondary' },
  'malla-suavizar': { name: 'Suavizar', icon: 'waves', cls: 'text-secondary' },
  'malla-reducir': { name: 'Reducir', icon: 'compress', cls: 'text-secondary' },
  'malla-remallar': { name: 'Remallar', icon: 'autorenew', cls: 'text-secondary' },
  'malla-volumetrica': { name: 'Volumétrica', icon: 'box', cls: 'text-secondary' },
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
  // MULTI-COND: la creación vive en App; la prop se conserva por
  // compatibilidad con el llamador pero este panel ya no la usa.
  onNewCondition: _onNewCondition,
  onPushCondition,
  currentModel,
  meshElementSize,
  onChangeMeshSize,
  onRemesh,
  isRemeshing,
  onMeshTool,
  meshBusy,
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
    // TOOL-FIXED (reversible): menu anclado abajo de la columna (mt-auto) con
    // cuerpo de alto capado + scroll interno: al abrir una herramienta crece
    // HACIA ARRIBA hacia el arbol en vez de esconderse bajo el marco.
    // Para volver atras: quitar mt-auto/flex-shrink-0 y el max-h del cuerpo.
    <section className="bg-surface-container-low rounded-lg p-space-sm shadow-md flex flex-col gap-space-xs border border-border-subtle/40 flex-shrink-0 min-w-0 xl:mt-auto">
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
                desde el arbol). Boton + Nueva eliminado a pedido. */}
            <span className="flex-1 min-w-0 truncate text-text-secondary text-[10px] font-mono">
              {toolConds.length > 0
                ? `${toolConds.length} aplicada${toolConds.length > 1 ? 's' : ''} de este tipo`
                : 'sin aplicar aún'}
            </span>
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
        {(activeTool === 'malla' || activeTool === 'malla-volumetrica') && (      <div className="flex flex-col gap-2 p-1 text-[11px] min-h-0 overflow-y-auto max-h-[42dvh] xl:max-h-[38dvh]">
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
              title="Aceptar (Enter)"
              className="w-full flex items-center justify-center gap-1.5 py-1 rounded bg-primary-container hover:bg-secondary text-on-primary text-[11px] font-semibold transition-colors active:scale-95"
            >
              <span className="material-symbols-outlined text-[15px]">check</span>
            </button>
          </div>
        )}
        {/* REMESH-TOOL-END */}

        {/* MALLA-TOOLS-START (reversible): parametros de superficie (el
            resultado se publica en el panel derecho). Para volver atras:
            borrar hasta MALLA-TOOLS-END + props onMeshTool/meshBusy. */}
        {activeTool === 'malla-diagnosticar' && (
          <div className="flex flex-col gap-2 p-1 text-[11px]">
            <p className="text-text-muted text-[11px] leading-relaxed">
              Detecta degenerados, non-manifold y bordes abiertos. No modifica nada.
            </p>
            <MeshApply label="Diagnosticar malla" busy={meshBusy === 'diagnosticar'}
              onClick={() => onMeshTool('diagnosticar', {})} />
          </div>
        )}

        {activeTool === 'malla-reparar' && (
          <div className="flex flex-col gap-2 p-1 text-[11px]">
            <p className="text-text-muted text-[11px] leading-relaxed">
              Suelda duplicados y quita degenerados/huérfanos. Lo ambiguo solo se reporta.
            </p>
            <MeshApply label="Reparar (soldar + limpiar)" busy={meshBusy === 'reparar'}
              onClick={() => onMeshTool('reparar', {})} />
          </div>
        )}

        {activeTool === 'malla-suavizar' && (
          <MeshSmoothParams busy={meshBusy === 'suavizar'}
            onApply={(p) => onMeshTool('suavizar', p)} />
        )}

        {activeTool === 'malla-reducir' && (
          <MeshDecimateParams busy={meshBusy === 'reducir'}
            onApply={(p) => onMeshTool('reducir', p)} />
        )}

        {activeTool === 'malla-remallar' && (
          <MeshRemeshParams busy={meshBusy === 'remallar'}
            onApply={(p) => onMeshTool('remallar', p)} />
        )}
        {/* MALLA-TOOLS-END */}

        {activeTool !== 'seleccionar' && activeTool !== 'carga' && activeTool !== 'malla' && (
          <button
            type="button"
            onClick={onConfirmTool}
            title="Aceptar (Enter)"
            className="w-full flex items-center justify-center gap-1.5 py-1 rounded bg-primary-container hover:bg-secondary text-on-primary text-[11px] font-semibold transition-colors active:scale-95"
          >
            <span className="material-symbols-outlined text-[15px]">check</span>
          </button>
        )}
      </div>
    </section>
  );
};

// MALLA-TOOLS (reversible): controles de parametros de superficie.
// Misma estetica que el bloque volumetrico. Para volver atras: borrar.
function MeshApply({ label, busy, onClick }: { label: string; busy: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded bg-primary-container hover:bg-secondary text-on-primary text-[11px] font-semibold transition-colors active:scale-95 disabled:opacity-50"
    >
      <span className="material-symbols-outlined text-[15px]">check</span>
      <span>{busy ? 'Ejecutando…' : label}</span>
    </button>
  );
}

function MeshSmoothParams({ busy, onApply }: { busy: boolean; onApply: (p: Record<string, number>) => void }) {
  const [iters, setIters] = useState(3);
  const [alpha, setAlpha] = useState(0.5);

  return (
    <div className="flex flex-col gap-2 p-1 text-[11px]">
      <div className="flex items-center justify-between font-mono text-[11px]">
        <span className="text-text-muted text-[10px]">Iteraciones:</span>
        <input type="number" min={1} max={100} step={1} value={iters}
          onChange={(e) => setIters(Math.max(1, parseInt(e.target.value || '1', 10)))}
          className="w-20 bg-surface-container-lowest rounded px-2 py-1 text-text-primary font-mono" />
      </div>
      <div className="flex items-center justify-between font-mono text-[11px]">
        <span className="text-text-muted text-[10px]">Alpha (0-1]:</span>
        <input type="number" min={0.05} max={1} step={0.05} value={alpha}
          onChange={(e) => setAlpha(Math.min(1, Math.max(0.05, parseFloat(e.target.value || '0.5'))))}
          className="w-20 bg-surface-container-lowest rounded px-2 py-1 text-text-primary font-mono" />
      </div>
      <MeshApply label="Aplicar suavizado" busy={busy}
        onClick={() => onApply({ iterations: iters, alpha })} />
    </div>
  );
}

function MeshDecimateParams({ busy, onApply }: { busy: boolean; onApply: (p: Record<string, number>) => void }) {
  const [frac, setFrac] = useState(0.5);

  return (
    <div className="flex flex-col gap-2 p-1 text-[11px]">
      <div className="flex items-center justify-between font-mono text-[11px]">
        <span className="text-text-muted text-[10px]">Fracción objetivo:</span>
        <span className="text-secondary font-bold">{Math.round(frac * 100)}%</span>
      </div>
      <input type="range" min={0.05} max={1} step={0.05} value={frac}
        onChange={(e) => setFrac(parseFloat(e.target.value))}
        className="w-full h-1 bg-surface-elevated rounded-lg appearance-none cursor-pointer accent-secondary" />
      <MeshApply label="Aplicar reducción" busy={busy}
        onClick={() => onApply({ target_fraction: frac })} />
    </div>
  );
}

function MeshRemeshParams({ busy, onApply }: { busy: boolean; onApply: (p: Record<string, number>) => void }) {
  const [len, setLen] = useState(1.0);

  return (
    <div className="flex flex-col gap-2 p-1 text-[11px]">
      <div className="flex items-center justify-between font-mono text-[11px]">
        <span className="text-text-muted text-[10px]">Longitud objetivo (mm):</span>
        <input type="number" min={0.01} step={0.1} value={len}
          onChange={(e) => setLen(Math.max(0.01, parseFloat(e.target.value || '1')))}
          className="w-24 bg-surface-container-lowest rounded px-2 py-1 text-text-primary font-mono" />
      </div>
      <MeshApply label="Aplicar remallado" busy={busy}
        onClick={() => onApply({ target_length: len, iterations: 3 })} />
    </div>
  );
}

// Editor del vector + direccion de carga (antes en el modal de edicion;
// movido aqui para no tapar el viewport). Guarda en vivo sobre la condicion
// destino (la crea si aun no existe: queda inactiva hasta picar caras) y
// reenvia al backend via onPushCondition.
// LOAD-DIR2 (reversible): direccion parametrica = modo (perpendicular o
// paralelo al plano) + plano (xy/xz/yz) + angulo en el plano (°) + sentido
// (+/-). La flecha muestra la proyeccion en el plano y al pincharla invierte
// el sentido. Para volver atras: restaurar el select Direccion (git).
type LoadMode = 'perpendicular' | 'paralelo';

type LoadPlane = 'xy' | 'xz' | 'yz';

const LOAD_MODES: LoadMode[] = ['perpendicular', 'paralelo'];

const LOAD_PLANES: LoadPlane[] = ['xy', 'xz', 'yz'];

const PLANE_NORMAL: Record<LoadPlane, [number, number, number]> = {
  xy: [0, 0, 1],
  xz: [0, 1, 0],
  yz: [1, 0, 0],
};

const PLANE_AXES: Record<LoadPlane, [[number, number, number], [number, number, number]]> = {
  xy: [[1, 0, 0], [0, 1, 0]],
  xz: [[1, 0, 0], [0, 0, 1]],
  yz: [[0, 1, 0], [0, 0, 1]],
};

// Vector unitario: paralelo = giro en el plano desde el 1er eje;
// perpendicular = normal inclinada hacia el 1er eje por el angulo.
function loadDirVector(mode: LoadMode, plane: LoadPlane, angleDeg: number, sense: 1 | -1): [number, number, number] {
  const r = (Number.isFinite(angleDeg) ? angleDeg : 0) * Math.PI / 180;
  const c = Math.cos(r) * sense;
  const s = Math.sin(r) * sense;
  const n = PLANE_NORMAL[plane];
  const [a1, a2] = PLANE_AXES[plane];
  const base = mode === 'paralelo' ? [a1, a2] : [n, a1];

  const v: [number, number, number] = [
    c * base[0][0] + s * base[1][0],
    c * base[0][1] + s * base[1][1],
    c * base[0][2] + s * base[1][2],
  ];

  const m = Math.hypot(v[0], v[1], v[2]) || 1;

  return [v[0] / m, v[1] / m, v[2] / m];
}

// Angulo CSS de la flecha (proyeccion del vector en los ejes del plano).
function loadArrowDeg(mode: LoadMode, plane: LoadPlane, angleDeg: number, sense: 1 | -1): number {
  const d = loadDirVector(mode, plane, angleDeg, sense);
  const [a1, a2] = PLANE_AXES[plane];
  const sx = d[0] * a1[0] + d[1] * a1[1] + d[2] * a1[2];
  const syUp = d[0] * a2[0] + d[1] * a2[1] + d[2] * a2[2];

  return (Math.atan2(-syUp, sx) * 180) / Math.PI;
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
  const [mag, setMag] = useState('4500');
  const [unit, setUnit] = useState<'N' | 'kN'>('N');
  const [mode, setMode] = useState<LoadMode>('perpendicular');
  const [plane, setPlane] = useState<LoadPlane>('xy');
  const [angle, setAngle] = useState('0');
  const [sense, setSense] = useState<1 | -1>(1);
  // LOAD-CASE (reversible, Fase 1.3 plan.md): caso de carga + peso.
  const [caseId, setCaseId] = useState('');
  const [weight, setWeight] = useState('1');

  // Carga los valores guardados al abrir/cambiar de condicion.
  useEffect(() => {
    if (cond?.magnitude && Number.isFinite(cond.magnitude) && cond.magnitude > 0) {
      setMag(String(Math.round(cond.magnitude)));
    }

    if (cond?.loadMode) setMode(cond.loadMode);

    if (cond?.loadPlane) setPlane(cond.loadPlane);

    if (cond?.loadAngleDeg !== undefined) setAngle(String(cond.loadAngleDeg));

    if (cond?.loadSense) setSense(cond.loadSense);
    setCaseId(cond?.loadCaseId ?? '');
    setWeight(String(cond?.loadWeight ?? 1));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cond?.id]);

  const saveAll = (
    magStr: string, u: 'N' | 'kN', m: LoadMode, pl: LoadPlane,
    angStr: string, se: 1 | -1, live: boolean,
    caseOverride?: string, weightOverride?: string,
  ): BoundaryCondition | null => {
    const magRaw = parseFloat(magStr);

    if (live && (!Number.isFinite(magRaw) || magRaw <= 0)) return null;
    const magN = (Number.isFinite(magRaw) && magRaw > 0 ? magRaw : 0) * (u === 'kN' ? 1000 : 1);
    const angRaw = parseFloat(angStr);
    const ang = Number.isFinite(angRaw) ? Math.max(-180, Math.min(180, angRaw)) : 0;
    const d = loadDirVector(m, pl, ang, se);
    const vx = magN * d[0];
    const vy = magN * d[1];
    const vz = magN * d[2];
    const gid = (caseOverride ?? caseId).trim();
    const wRaw = parseFloat(weightOverride ?? weight);
    const w = Number.isFinite(wRaw) && wRaw > 0 ? wRaw : 1;
    const sym = m === 'perpendicular' ? '⊥' : '∥';
    const details = `[${vx.toFixed(0)}, ${vy.toFixed(0)}, ${vz.toFixed(0)}] N · ${sym}${pl.toUpperCase()} ${ang}° · ${se === 1 ? '+' : '−'}${gid ? ` · caso ${gid} ×${w}` : ''}`;

    const updated: BoundaryCondition = cond
      ? { ...cond, value: [vx, vy, vz], magnitude: magN, details, loadNormal: PLANE_NORMAL[pl], loadMode: m, loadPlane: pl, loadAngleDeg: ang, loadSense: se, loadCaseId: gid || undefined, loadWeight: w }
      : {
          id: 'faces_carga',
          name: 'Carga en caras',
          type: 'carga',
          details,
          value: [vx, vy, vz],
          magnitude: magN,
          loadNormal: PLANE_NORMAL[pl],
          loadMode: m,
          loadPlane: pl,
          loadAngleDeg: ang,
          loadSense: se,
          loadCaseId: gid || undefined,
          loadWeight: w,
          faces: 0,
          faceIndices: [],
          active: false,
        };

    onSaveCondition(updated);
    onPushCondition(updated);

    return updated;
  };

  const confirm = () => {
    saveAll(mag, unit, mode, plane, angle, sense, false);
    onConfirmTool();
  };

  const numCls =
    'min-w-0 flex-1 bg-surface-elevated border border-border-subtle rounded px-2 py-1 text-text-primary font-mono text-[11px] outline-none focus:border-secondary/60';

  const segOn =
    'flex-1 min-w-0 truncate px-1.5 py-1 rounded text-[10px] font-semibold bg-secondary/15 text-secondary ring-1 ring-secondary/30 transition-colors';

  const segOff =
    'flex-1 min-w-0 truncate px-1.5 py-1 rounded text-[10px] text-text-secondary hover:bg-surface-elevated hover:text-text-primary transition-colors';

  const arrowDeg = loadArrowDeg(mode, plane, parseFloat(angle) || 0, sense);

  return (
    <div className="flex flex-col gap-2 font-mono text-[11px] min-w-0">
      {/* Valor + unidades */}
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="text-text-muted shrink-0">Valor:</span>
        <input
          type="number"
          aria-label="Valor de la carga"
          min="0"
          step="100"
          value={mag}
          onChange={(e) => {
            setMag(e.target.value);
            saveAll(e.target.value, unit, mode, plane, angle, sense, true);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') confirm();
          }}
          className={numCls}
        />
        <select
          aria-label="Unidades de la carga"
          value={unit}
          onChange={(e) => {
            const u = e.target.value === 'kN' ? 'kN' : 'N';
            setUnit(u);
            saveAll(mag, u, mode, plane, angle, sense, false);
          }}
          className="shrink-0 w-[60px] bg-surface-elevated border border-border-subtle rounded px-1 py-1 text-text-primary text-[11px] outline-none focus:border-secondary/60"
        >
          <option value="N">N</option>
          <option value="kN">kN</option>
        </select>
      </div>
      {/* Modo: perpendicular / paralelo */}
      <div className="flex items-center gap-1 min-w-0" role="group" aria-label="Modo de dirección">
        {LOAD_MODES.map((m) => (
          <button
            key={m}
            type="button"
            title={m === 'perpendicular' ? 'Perpendicular al plano' : 'Paralelo al plano'}
            onClick={() => {
              setMode(m);
              saveAll(mag, unit, m, plane, angle, sense, false);
            }}
            className={m === mode ? segOn : segOff}
          >
            {m === 'perpendicular' ? '⊥ Perpend.' : '∥ Paralelo'}
          </button>
        ))}
      </div>
      {/* Plano + angulo + flecha de sentido */}
      <div className="flex items-center gap-1 min-w-0">
        <div className="flex items-center gap-1 flex-1 min-w-0" role="group" aria-label="Plano">
          {LOAD_PLANES.map((pl) => (
            <button
              key={pl}
              type="button"
              title={`Plano ${pl.toUpperCase()}`}
              onClick={() => {
                setPlane(pl);
                saveAll(mag, unit, mode, pl, angle, sense, false);
              }}
              className={pl === plane ? segOn : segOff}
            >
              {pl.toUpperCase()}
            </button>
          ))}
        </div>
        <input
          type="number"
          aria-label="Ángulo en el plano (grados)"
          title="Ángulo en el plano (°)"
          min="-180"
          max="180"
          step="5"
          value={angle}
          onChange={(e) => {
            setAngle(e.target.value);
            saveAll(mag, unit, mode, plane, e.target.value, sense, true);
          }}
          className="shrink-0 w-14 bg-surface-elevated border border-border-subtle rounded px-1.5 py-1 text-text-primary font-mono text-[11px] outline-none focus:border-secondary/60"
        />
        <span className="text-text-muted shrink-0">°</span>
        <button
          type="button"
          onClick={() => {
            const ns = sense === 1 ? -1 : 1;
            setSense(ns);
            saveAll(mag, unit, mode, plane, angle, ns, false);
          }}
          title={`Sentido ${sense === 1 ? '+' : '−'} — pinchar invierte la carga`}
          aria-label="Invertir sentido de la carga"
          className="shrink-0 w-9 h-7 flex items-center justify-center rounded bg-surface-elevated border border-border-subtle hover:border-secondary/60 text-secondary transition-colors active:scale-95"
        >
          <svg viewBox="0 0 24 24" className="w-5 h-5" style={{ transform: `rotate(${arrowDeg}deg)` }}>
            <line x1="4" y1="12" x2="16.5" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <polyline points="12.5,7.5 17,12 12.5,16.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
      <div className="flex items-center gap-1.5 min-w-0 text-[10px]">
        <span className="text-text-muted shrink-0">Vector:</span>
        <span className="truncate text-secondary" title={cond?.details ?? ''}>{cond?.details ?? '—'}</span>
      </div>
      <div className="bg-surface-elevated/40 p-1.5 rounded border border-border-subtle/30 min-w-0">
        <span className="text-text-muted block text-[9px]">Caras asignadas:</span>
        <span className="text-secondary text-[10px] break-all">{facesText(cond)}</span>
      </div>
      {/* LOAD-CASE (reversible, Fase 1.3): caso + peso multicarga.
          Vacío = caso único (comportamiento anterior). */}
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="text-text-muted shrink-0">Caso:</span>
        <input
          type="text"
          aria-label="Caso de carga"
          placeholder="único"
          value={caseId}
          onChange={(e) => {
            setCaseId(e.target.value);
            saveAll(mag, unit, mode, plane, angle, sense, false, e.target.value, weight);
          }}
          className={numCls}
        />
        <span className="text-text-muted shrink-0">×</span>
        <input
          type="number"
          aria-label="Peso del caso de carga"
          min="0.01"
          step="0.1"
          value={weight}
          onChange={(e) => {
            setWeight(e.target.value);
            saveAll(mag, unit, mode, plane, angle, sense, true, caseId, e.target.value);
          }}
          className="shrink-0 w-14 bg-surface-elevated border border-border-subtle rounded px-1.5 py-1 text-text-primary font-mono text-[11px] outline-none focus:border-secondary/60"
        />
      </div>
      <button
        type="button"
        onClick={confirm}
        title="Aceptar (Enter)"
        className="w-full flex items-center justify-center gap-1.5 py-1 rounded bg-primary-container hover:bg-secondary text-on-primary text-[11px] font-semibold transition-colors active:scale-95"
      >
        <span className="material-symbols-outlined text-[15px]">check</span>
      </button>
    </div>
  );
}
