import React from 'react';
import { ProtectedFace } from '../../types';
import { ShieldCheck, Plus, Trash2, Check, Lock, Shield } from 'lucide-react';

interface ProtegidaPanelProps {
  protectedFaces: ProtectedFace[];
  onToggleProtectedFace: (id: string) => void;
  onAddProtectedFace: (face: ProtectedFace) => void;
  onRemoveProtectedFace: (id: string) => void;
  isOptimizing: boolean;
}

export const ProtegidaPanel: React.FC<ProtegidaPanelProps> = ({
  protectedFaces,
  onToggleProtectedFace,
  onAddProtectedFace,
  onRemoveProtectedFace,
  isOptimizing
}) => {
  const handleAddAnchorFace = () => {
    const newId = `prot_${Date.now()}`;
    const newFace: ProtectedFace = {
      id: newId,
      name: `Cara de Fijación Posterior #${protectedFaces.length + 1}`,
      description: 'Superficie de contacto con la estructura portante (X = 0)',
      type: 'support_anchor',
      enabled: true,
      color: '#10b981',
      bounds: [0.0, 0.0, 0.0, 0.08, 1.0, 1.0]
    };
    onAddProtectedFace(newFace);
  };

  const handleAddLoadPadFace = () => {
    const newId = `prot_${Date.now()}`;
    const newFace: ProtectedFace = {
      id: newId,
      name: `Almohadilla de Carga #${protectedFaces.length + 1}`,
      description: 'Zona de aplicación y distribución de fuerza mecánica',
      type: 'load_bearing',
      enabled: true,
      color: '#38bdf8',
      bounds: [0.88, 0.0, 0.3, 1.0, 0.15, 0.7]
    };
    onAddProtectedFace(newFace);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 text-xs text-slate-300 shadow-lg">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Herramienta Caras Protegidas</h2>
            <p className="text-[11px] text-slate-400">Caras que NO se modificarán en la optimización (100% sólidas)</p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
          {protectedFaces.filter((f) => f.enabled).length} Bloqueadas
        </span>
      </div>

      {/* Explicación de preservación */}
      <div className="bg-emerald-500/10 border border-emerald-500/25 p-3 rounded-lg text-emerald-200/90 text-[11px] flex items-start gap-2">
        <Lock className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
        <span>
          Las caras protegidas constituyen el dominio no modificable (Non-Design Domain). El algoritmo retiene el 100% de la densidad en estas zonas sin perforar ni aligerar las interfaces mecánicas.
        </span>
      </div>

      {/* Lista de Caras Protegidas */}
      <div className="flex flex-col gap-2">
        <label className="text-slate-300 font-semibold flex items-center justify-between">
          <span>Superficies Preservadas:</span>
          <span className="text-[10px] text-slate-500 font-mono">ρ = 1.000 (Sólido permanente)</span>
        </label>

        {protectedFaces.map((face) => (
          <div
            key={face.id}
            className={`p-3 rounded-lg border transition-all flex items-start justify-between gap-3 ${
              face.enabled
                ? 'bg-slate-950/80 border-emerald-500/40 text-slate-200'
                : 'bg-slate-950/30 border-slate-800/60 text-slate-500 opacity-60'
            }`}
          >
            <div className="flex items-start gap-2.5">
              <button
                onClick={() => onToggleProtectedFace(face.id)}
                disabled={isOptimizing}
                className={`w-5 h-5 rounded-md flex items-center justify-center text-xs transition-colors cursor-pointer shrink-0 mt-0.5 ${
                  face.enabled
                    ? 'bg-emerald-500 text-slate-950 font-bold shadow-sm'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}
                title={face.enabled ? 'Desproteger cara' : 'Proteger cara (retener sólida)'}
              >
                {face.enabled ? <Check className="w-3.5 h-3.5" /> : null}
              </button>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-slate-200">{face.name}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                    Protegida
                  </span>
                </div>
                <span className="text-[11px] text-slate-400 block mt-0.5">{face.description}</span>
                <span className="text-[10px] font-mono text-emerald-400/80 mt-1 block">
                  Estado: Material inalterable (Sin penalización SIMP)
                </span>
              </div>
            </div>

            {protectedFaces.length > 1 && (
              <button
                onClick={() => onRemoveProtectedFace(face.id)}
                disabled={isOptimizing}
                className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                title="Eliminar cara protegida"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Acciones para añadir más caras protegidas */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={handleAddAnchorFace}
          disabled={isOptimizing}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-medium transition-all cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 text-emerald-400" />
          + Cara de Anclaje
        </button>
        <button
          onClick={handleAddLoadPadFace}
          disabled={isOptimizing}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-medium transition-all cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 text-emerald-400" />
          + Almohadilla de Carga
        </button>
      </div>
    </div>
  );
};
