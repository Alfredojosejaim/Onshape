import React from 'react';
import { ObstacleZone } from '../../types';
import { Ban, Plus, Trash2, Eye, EyeOff, Check, AlertCircle } from 'lucide-react';

interface ObstruccionesPanelProps {
  obstacles: ObstacleZone[];
  onToggleObstacle: (id: string) => void;
  onAddObstacle: (obstacle: ObstacleZone) => void;
  onRemoveObstacle: (id: string) => void;
  isOptimizing: boolean;
}

export const ObstruccionesPanel: React.FC<ObstruccionesPanelProps> = ({
  obstacles,
  onToggleObstacle,
  onAddObstacle,
  onRemoveObstacle,
  isOptimizing
}) => {
  const handleAddNewBore = () => {
    const newId = `obs_${Date.now()}`;
    const newObs: ObstacleZone = {
      id: newId,
      name: `Taladro de Paso #${obstacles.length + 1}`,
      description: 'Zona cilíndrica de despeje mecánico para eje pasante',
      shape: 'cylinder',
      enabled: true,
      color: '#f59e0b',
      bounds: [0.35, 0.35, 0.0, 0.65, 0.65, 1.0]
    };
    onAddObstacle(newObs);
  };

  const handleAddNewChannel = () => {
    const newId = `obs_${Date.now()}`;
    const newObs: ObstacleZone = {
      id: newId,
      name: `Canal de Paso #${obstacles.length + 1}`,
      description: 'Paso libre para cableado, tubería o tornillería',
      shape: 'box',
      enabled: true,
      color: '#ef4444',
      bounds: [0.1, 0.45, 0.3, 0.9, 0.55, 0.7]
    };
    onAddObstacle(newObs);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 text-xs text-slate-300 shadow-lg">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Ban className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Herramienta de Obstrucciones</h2>
            <p className="text-[11px] text-slate-400">Zonas de exclusión donde NO se permite generar material (Keep-Out)</p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
          {obstacles.filter((o) => o.enabled).length} Activas
        </span>
      </div>

      {/* Explicación de ingeniería */}
      <div className="bg-amber-500/10 border border-amber-500/25 p-3 rounded-lg text-amber-200/90 text-[11px] flex items-start gap-2">
        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <span>
          Las obstrucciones garantizan que componentes móviles, pernos, ejes o conductos no sean invadidos por el material optimizado durante el proceso generativo.
        </span>
      </div>

      {/* Lista de Zonas de Obstrucción */}
      <div className="flex flex-col gap-2">
        <label className="text-slate-300 font-semibold flex items-center justify-between">
          <span>Zonas de Exclusión Configuradas:</span>
          <span className="text-[10px] text-slate-500 font-mono">ρ = 0.000 (Vacío absoluto)</span>
        </label>

        {obstacles.map((obs) => (
          <div
            key={obs.id}
            className={`p-3 rounded-lg border transition-all flex items-start justify-between gap-3 ${
              obs.enabled
                ? 'bg-slate-950/80 border-amber-500/40 text-slate-200'
                : 'bg-slate-950/30 border-slate-800/60 text-slate-500 opacity-60'
            }`}
          >
            <div className="flex items-start gap-2.5">
              <button
                onClick={() => onToggleObstacle(obs.id)}
                disabled={isOptimizing}
                className={`w-5 h-5 rounded-md flex items-center justify-center text-xs transition-colors cursor-pointer shrink-0 mt-0.5 ${
                  obs.enabled
                    ? 'bg-amber-500 text-slate-950 font-bold shadow-sm'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}
                title={obs.enabled ? 'Desactivar obstrucción' : 'Activar obstrucción'}
              >
                {obs.enabled ? <Check className="w-3.5 h-3.5" /> : null}
              </button>
              <div>
                <span className="font-semibold block text-slate-200">{obs.name}</span>
                <span className="text-[11px] text-slate-400 block">{obs.description}</span>
                <span className="text-[10px] font-mono text-amber-400 mt-0.5 block">
                  Geometría: {obs.shape === 'cylinder' ? 'Cilindro pasante' : 'Caja rectangular'}
                </span>
              </div>
            </div>

            {obstacles.length > 1 && (
              <button
                onClick={() => onRemoveObstacle(obs.id)}
                disabled={isOptimizing}
                className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                title="Eliminar zona de obstrucción"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Botones para añadir nuevas obstrucciones */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={handleAddNewBore}
          disabled={isOptimizing}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-medium transition-all cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 text-amber-400" />
          + Taladro Pasante
        </button>
        <button
          onClick={handleAddNewChannel}
          disabled={isOptimizing}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-medium transition-all cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 text-amber-400" />
          + Canal de Paso
        </button>
      </div>
    </div>
  );
};
