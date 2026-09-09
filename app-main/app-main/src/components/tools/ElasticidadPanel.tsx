import React from 'react';
import { Material } from '../../types';
import { STANDARD_MATERIALS } from '../../lib/materials';
import { Atom, Scale, Shield, Sparkles, Activity } from 'lucide-react';

interface ElasticidadPanelProps {
  material: Material;
  materialsList?: Material[];
  onMaterialChange: (m: Material) => void;
  onOpenMaterialsWindow?: () => void;
  isOptimizing: boolean;
}

export const ElasticidadPanel: React.FC<ElasticidadPanelProps> = ({
  material,
  materialsList = STANDARD_MATERIALS,
  onMaterialChange,
  onOpenMaterialsWindow,
  isOptimizing
}) => {
  // Specific stiffness (E / rho ratio)
  const specificStiffness = ((material.youngModulus * 1e9) / material.density / 1e6).toFixed(1);

  const handleCustomPropertyChange = (prop: keyof Material, value: number) => {
    onMaterialChange({
      ...material,
      id: material.isCustom ? material.id : `${material.id}_mod`,
      [prop]: value
    });
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 text-xs text-slate-300 shadow-lg">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Atom className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Herramienta de Elasticidad</h2>
            <p className="text-[11px] text-slate-400">Propiedades mecánicas y tensores de rigidez elástica</p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold">
          E = {material.youngModulus} GPa
        </span>
      </div>

      {/* Selector de Material y acceso a Biblioteca */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <label className="text-slate-300 font-semibold">Material Seleccionado:</label>
          {onOpenMaterialsWindow && (
            <button
              onClick={onOpenMaterialsWindow}
              className="text-[11px] text-sky-400 hover:text-sky-300 hover:underline flex items-center gap-1 cursor-pointer font-medium"
            >
              <Sparkles className="w-3 h-3" /> Biblioteca de Materiales
            </button>
          )}
        </div>
        <select
          value={material.id}
          onChange={(e) => {
            const found = materialsList.find((m) => m.id === e.target.value);
            if (found) onMaterialChange(found);
          }}
          disabled={isOptimizing}
          className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 cursor-pointer"
        >
          {materialsList.map((mat) => (
            <option key={mat.id} value={mat.id}>
              {mat.name} {mat.isCustom ? '(Personalizado)' : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Propiedades Elásticas Directas */}
      <div className="flex flex-col gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
        <span className="font-semibold text-indigo-300 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5" /> Parámetros Elásticos Constitutivos:
        </span>

        {/* Módulo de Young */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-300">Módulo de Young (E):</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min="1"
                max="1000"
                step="1"
                value={material.youngModulus}
                onChange={(e) => handleCustomPropertyChange('youngModulus', Math.max(1, Number(e.target.value)))}
                disabled={isOptimizing}
                className="w-16 bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-right text-indigo-300 font-mono text-[11px]"
              />
              <span className="text-slate-400 font-mono">GPa</span>
            </div>
          </div>
          <input
            type="range"
            min="5"
            max="400"
            step="1"
            value={material.youngModulus}
            onChange={(e) => handleCustomPropertyChange('youngModulus', Number(e.target.value))}
            disabled={isOptimizing}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
          />
        </div>

        {/* Coeficiente de Poisson */}
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-300">Coeficiente de Poisson (ν):</span>
          <div className="flex items-center gap-1">
            <input
              type="number"
              min="0.1"
              max="0.49"
              step="0.01"
              value={material.poissonRatio}
              onChange={(e) => handleCustomPropertyChange('poissonRatio', Number(e.target.value))}
              disabled={isOptimizing}
              className="w-16 bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-right text-indigo-300 font-mono text-[11px]"
            />
            <span className="text-slate-400 font-mono">-</span>
          </div>
        </div>

        {/* Límite Elástico */}
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-300">Límite Elástico (σy):</span>
          <div className="flex items-center gap-1">
            <input
              type="number"
              min="10"
              max="3000"
              step="10"
              value={material.yieldStrength}
              onChange={(e) => handleCustomPropertyChange('yieldStrength', Number(e.target.value))}
              disabled={isOptimizing}
              className="w-16 bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-right text-indigo-300 font-mono text-[11px]"
            />
            <span className="text-slate-400 font-mono">MPa</span>
          </div>
        </div>

        {/* Densidad */}
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-300">Densidad (ρ):</span>
          <div className="flex items-center gap-1">
            <input
              type="number"
              min="500"
              max="20000"
              step="50"
              value={material.density}
              onChange={(e) => handleCustomPropertyChange('density', Number(e.target.value))}
              disabled={isOptimizing}
              className="w-16 bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-right text-indigo-300 font-mono text-[11px]"
            />
            <span className="text-slate-400 font-mono">kg/m³</span>
          </div>
        </div>
      </div>

      {/* Ratios e Índices de Rendimiento */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-bold">
            Rigidez Específica (E/ρ)
          </span>
          <span className="text-sm font-mono font-bold text-indigo-400">
            {specificStiffness} <span className="text-[10px] text-slate-400">kN·m/g</span>
          </span>
        </div>
        <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-bold">
            Matriz de Elasticidad
          </span>
          <span className="text-sm font-mono font-bold text-slate-200">
            Isótropa 3D
          </span>
        </div>
      </div>

      <p className="text-[11px] text-slate-400">
        El módulo de Young y el coeficiente de Poisson determinan la matriz constitutiva elástica C en cada elemento finito y guían el gradiente de sensibilidad en el aligeramiento.
      </p>
    </div>
  );
};
