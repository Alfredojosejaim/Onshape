import React from 'react';
import { DesignDomainPreset } from '../types';
import {
  Anchor,
  ArrowDown,
  Layers,
  Box,
  Eye,
  ShieldCheck,
  Compass,
  FileCode2,
  Upload
} from 'lucide-react';

interface BoundariesPanelProps {
  preset: DesignDomainPreset;
  loadMagnitude: number;
  onLoadMagnitudeChange: (val: number) => void;
  showGlyphs: boolean;
  onToggleGlyphs: () => void;
  showBounds: boolean;
  onToggleBounds: () => void;
  showWireframe: boolean;
  onToggleWireframe: () => void;
  onImportStepFile: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export const BoundariesPanel: React.FC<BoundariesPanelProps> = ({
  preset,
  loadMagnitude,
  onLoadMagnitudeChange,
  showGlyphs,
  onToggleGlyphs,
  showBounds,
  onToggleBounds,
  showWireframe,
  onToggleWireframe,
  onImportStepFile
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 text-xs text-slate-300 shadow-lg">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
          <Anchor className="w-4 h-4 text-emerald-400" />
          Condiciones de Contorno & Cargas
        </h2>
        <span className="text-[10px] text-emerald-400 font-medium bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
          FEA Estático
        </span>
      </div>

      {/* Preset boundary info */}
      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 flex flex-col gap-2">
        <div className="flex items-start gap-2 text-slate-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-slate-200 block">
              {preset === 'cantilever' && 'Empotramiento Completo (X = 0)'}
              {preset === 'mbb_beam' && 'Apoyos Simétricos / Rodillos (Base Inferior)'}
              {preset === 'l_bracket' && 'Sujeción Superior Rígida (Y = Max)'}
              {preset === 'bridge' && 'Apoyos en Pilares Extremos'}
              {preset === 'custom_step' && 'Fijación por Nodos Perimetrales'}
            </span>
            <span className="text-[11px] text-slate-400">
              {preset === 'cantilever' && 'Desplazamientos restringidos en todos los ejes [Ux = Uy = Uz = 0]'}
              {preset === 'mbb_beam' && 'Restricción vertical con simetría en plano central'}
              {preset === 'l_bracket' && 'Superficie superior anclada contra el soporte'}
              {preset === 'bridge' && 'Bases izquierda y derecha ancladas'}
              {preset === 'custom_step' && 'Condiciones mapeadas sobre la geometría importada'}
            </span>
          </div>
        </div>

        {/* Applied Load */}
        <div className="pt-2 border-t border-slate-800/80 flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-200 flex items-center gap-1.5">
              <ArrowDown className="w-3.5 h-3.5 text-red-400" />
              Carga Vertical Aplicada (F):
            </span>
            <span className="font-mono font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
              {(loadMagnitude / 1000).toFixed(1)} kN
            </span>
          </div>
          <input
            type="range"
            min="1000"
            max="50000"
            step="1000"
            value={loadMagnitude}
            onChange={(e) => onLoadMagnitudeChange(parseFloat(e.target.value))}
            className="accent-red-500 cursor-pointer"
          />
        </div>
      </div>

      {/* Simplified Active Layers (Removing useless CAD layers, keeping essential optimization visuals) */}
      <div className="flex flex-col gap-2">
        <label className="text-slate-300 font-semibold flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-sky-400" />
          Capas Visuales Útiles:
        </label>
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={onToggleGlyphs}
            className={`flex items-center justify-center gap-1.5 p-2 rounded-lg border text-[11px] font-medium transition-colors cursor-pointer ${
              showGlyphs
                ? 'bg-emerald-950/40 border-emerald-600/50 text-emerald-300'
                : 'bg-slate-950 border-slate-800 text-slate-500 hover:text-slate-400'
            }`}
          >
            <Eye className="w-3 h-3" />
            Cargas/Apoyos
          </button>
          <button
            onClick={onToggleBounds}
            className={`flex items-center justify-center gap-1.5 p-2 rounded-lg border text-[11px] font-medium transition-colors cursor-pointer ${
              showBounds
                ? 'bg-sky-950/40 border-sky-600/50 text-sky-300'
                : 'bg-slate-950 border-slate-800 text-slate-500 hover:text-slate-400'
            }`}
          >
            <Box className="w-3 h-3" />
            Dominio Inicial
          </button>
          <button
            onClick={onToggleWireframe}
            className={`flex items-center justify-center gap-1.5 p-2 rounded-lg border text-[11px] font-medium transition-colors cursor-pointer ${
              showWireframe
                ? 'bg-indigo-950/40 border-indigo-600/50 text-indigo-300'
                : 'bg-slate-950 border-slate-800 text-slate-500 hover:text-slate-400'
            }`}
          >
            <Layers className="w-3 h-3" />
            Malla/Alambre
          </button>
        </div>
      </div>

      {/* Import custom STEP or mesh file */}
      <div className="pt-2 border-t border-slate-800">
        <label className="text-slate-400 hover:text-slate-200 cursor-pointer flex items-center justify-center gap-2 p-2.5 rounded-lg border border-dashed border-slate-700 hover:border-sky-500 bg-slate-950/40 transition-colors text-center">
          <Upload className="w-4 h-4 text-sky-400" />
          <span>Importar Geometría Base (STEP / STL)</span>
          <input
            type="file"
            accept=".step,.stp,.stl"
            onChange={onImportStepFile}
            className="hidden"
          />
        </label>
      </div>
    </div>
  );
};
