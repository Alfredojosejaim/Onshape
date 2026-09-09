import React from 'react';
import {
  ArrowDownCircle,
  ArrowDown,
  ArrowRight,
  RotateCw,
  Compass,
  Sliders,
  Check
} from 'lucide-react';

interface CargaPanelProps {
  loadMagnitude: number;
  onLoadMagnitudeChange: (val: number) => void;
  loadDirection: [number, number, number];
  onLoadDirectionChange: (dir: [number, number, number]) => void;
  loadPosition: string;
  onLoadPositionChange: (pos: string) => void;
  onStartOptimization: () => void;
  isOptimizing: boolean;
}

export const CargaPanel: React.FC<CargaPanelProps> = ({
  loadMagnitude,
  onLoadMagnitudeChange,
  loadDirection,
  onLoadDirectionChange,
  loadPosition,
  onLoadPositionChange,
  onStartOptimization,
  isOptimizing
}) => {
  const presets = [
    { label: 'Vertical Descendente (-Y)', dir: [0, -1, 0] as [number, number, number], icon: ArrowDown },
    { label: 'Inclinada 45° (-X, -Y)', dir: [-0.707, -0.707, 0] as [number, number, number], icon: ArrowRight },
    { label: 'Carga Lateral Cortante (+X)', dir: [1, 0, 0] as [number, number, number], icon: ArrowRight },
    { label: 'Tracción Frontal (+Z)', dir: [0, 0, 1] as [number, number, number], icon: RotateCw }
  ];

  const positions = [
    { id: 'right_bottom', name: 'Extremo Inferior Derecho', desc: 'Típico en voladizo / ménsula cantilever' },
    { id: 'center_top', name: 'Centro Superior', desc: 'Típico en viga MBB o puente' },
    { id: 'center_bottom', name: 'Centro Inferior', desc: 'Carga colgante central' },
    { id: 'custom', name: 'Superficie Completa Frontal', desc: 'Distribución perimetral de carga' }
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 text-xs text-slate-300 shadow-lg">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <ArrowDownCircle className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Herramienta de Carga</h2>
            <p className="text-[11px] text-slate-400">Define vectores de fuerza externa y puntos de contacto</p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold">
          {(loadMagnitude / 1000).toFixed(1)} kN
        </span>
      </div>

      {/* Magnitud de Carga */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <label className="text-slate-300 font-semibold flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-rose-400" />
            Magnitud de Fuerza:
          </label>
          <div className="flex items-center gap-1">
            <input
              type="number"
              min="100"
              max="150000"
              step="500"
              value={loadMagnitude}
              onChange={(e) => onLoadMagnitudeChange(Math.max(100, Number(e.target.value)))}
              disabled={isOptimizing}
              className="w-24 bg-slate-950 border border-slate-700 text-slate-200 text-right px-2 py-1 rounded text-xs font-mono focus:outline-none focus:border-rose-500"
            />
            <span className="text-slate-400 font-mono text-[11px]">N</span>
          </div>
        </div>

        <input
          type="range"
          min="500"
          max="50000"
          step="500"
          value={loadMagnitude}
          onChange={(e) => onLoadMagnitudeChange(Number(e.target.value))}
          disabled={isOptimizing}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-rose-500"
        />

        {/* Quick presets for magnitude */}
        <div className="flex items-center gap-1.5 pt-1">
          <span className="text-[11px] text-slate-500">Preajustes:</span>
          {[2000, 5000, 10000, 20000, 50000].map((val) => (
            <button
              key={val}
              onClick={() => onLoadMagnitudeChange(val)}
              disabled={isOptimizing}
              className={`px-2 py-0.5 rounded text-[10px] font-mono cursor-pointer transition-colors ${
                loadMagnitude === val
                  ? 'bg-rose-500 text-white font-bold'
                  : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {val / 1000} kN
            </button>
          ))}
        </div>
      </div>

      {/* Dirección Vectorial */}
      <div className="flex flex-col gap-2">
        <label className="text-slate-300 font-semibold flex items-center gap-1.5">
          <Compass className="w-3.5 h-3.5 text-rose-400" />
          Dirección Vectorial [Fx, Fy, Fz]:
        </label>
        <div className="grid grid-cols-2 gap-2">
          {presets.map((preset, idx) => {
            const isSelected =
              Math.abs(loadDirection[0] - preset.dir[0]) < 0.05 &&
              Math.abs(loadDirection[1] - preset.dir[1]) < 0.05 &&
              Math.abs(loadDirection[2] - preset.dir[2]) < 0.05;
            return (
              <button
                key={idx}
                onClick={() => onLoadDirectionChange(preset.dir)}
                disabled={isOptimizing}
                className={`flex items-center gap-2 p-2 rounded-lg border text-left cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-rose-500/15 border-rose-500/60 text-rose-200 shadow-sm'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <preset.icon className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-rose-400' : 'text-slate-500'}`} />
                <span className="text-[11px] font-medium truncate">{preset.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Punto de Aplicación de la Carga */}
      <div className="flex flex-col gap-2">
        <label className="text-slate-300 font-semibold">Punto de Aplicación en el Sólido:</label>
        <div className="flex flex-col gap-1.5">
          {positions.map((pos) => (
            <button
              key={pos.id}
              onClick={() => onLoadPositionChange(pos.id)}
              disabled={isOptimizing}
              className={`flex items-start justify-between p-2.5 rounded-lg border text-left cursor-pointer transition-all ${
                loadPosition === pos.id
                  ? 'bg-rose-500/10 border-rose-500/50 text-slate-200'
                  : 'bg-slate-950/50 border-slate-800/80 text-slate-400 hover:text-slate-200'
              }`}
            >
              <div>
                <span className="font-semibold block text-slate-200">{pos.name}</span>
                <span className="text-[11px] text-slate-400">{pos.desc}</span>
              </div>
              {loadPosition === pos.id && <Check className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />}
            </button>
          ))}
        </div>
      </div>

      {/* Nota técnica de FEA */}
      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 text-[11px] text-slate-400 flex flex-col gap-1">
        <span className="text-rose-400 font-semibold">Efecto en la Topología:</span>
        <span>
          El algoritmo trazará puntales axiales y tirantes directos orientados a canalizar la carga hacia los apoyos fijos con mínima deformación elástica.
        </span>
      </div>
    </div>
  );
};
