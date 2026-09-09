import React, { useState } from 'react';
import { Material } from '../../types';
import {
  Layers,
  Plus,
  Trash2,
  Check,
  Sparkles,
  Info,
  Scale,
  Shield,
  Activity,
  Box,
  Palette,
  CheckCircle2,
  X
} from 'lucide-react';

interface MaterialesPanelProps {
  currentMaterial: Material;
  materialsList: Material[];
  onSelectMaterial: (m: Material) => void;
  onAddCustomMaterial: (m: Material) => void;
  onRemoveCustomMaterial: (id: string) => void;
  isOptimizing: boolean;
}

export const MaterialesPanel: React.FC<MaterialesPanelProps> = ({
  currentMaterial,
  materialsList,
  onSelectMaterial,
  onAddCustomMaterial,
  onRemoveCustomMaterial,
  isOptimizing
}) => {
  const [isCreating, setIsCreating] = useState(false);

  // Form state for custom material
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [youngModulus, setYoungModulus] = useState(100);
  const [poissonRatio, setPoissonRatio] = useState(0.33);
  const [density, setDensity] = useState(4000);
  const [yieldStrength, setYieldStrength] = useState(500);
  const [color, setColor] = useState('#0ea5e9');
  const [formError, setFormError] = useState<string | null>(null);

  // Predefined quick color options
  const colorOptions = [
    '#38bdf8', // sky
    '#818cf8', // indigo
    '#a78bfa', // purple
    '#ec4899', // pink
    '#f59e0b', // amber
    '#10b981', // emerald
    '#14b8a6', // teal
    '#94a3b8'  // slate
  ];

  const handleSaveCustom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setFormError('Introduce un nombre para el material');
      return;
    }
    if (youngModulus <= 0) {
      setFormError('El módulo de Young debe ser mayor a 0 GPa');
      return;
    }
    if (poissonRatio <= 0 || poissonRatio >= 0.5) {
      setFormError('El coeficiente de Poisson debe estar entre 0.01 y 0.49');
      return;
    }
    if (density <= 0) {
      setFormError('La densidad debe ser positiva');
      return;
    }
    if (yieldStrength <= 0) {
      setFormError('El límite elástico debe ser positivo');
      return;
    }

    const newMat: Material = {
      id: `custom_${Date.now()}`,
      name: name.trim(),
      description: description.trim() || 'Material personalizado definido por el usuario',
      youngModulus,
      poissonRatio,
      density,
      yieldStrength,
      color,
      isCustom: true
    };

    onAddCustomMaterial(newMat);
    onSelectMaterial(newMat);
    setIsCreating(false);
    setName('');
    setDescription('');
    setFormError(null);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-4 text-xs text-slate-300 shadow-lg">
      {/* Encabezado de la Ventana de Materiales */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">Biblioteca de Materiales</h2>
            <p className="text-[11px] text-slate-400">Selección de aleaciones y materiales personalizados</p>
          </div>
        </div>
        <button
          onClick={() => setIsCreating(!isCreating)}
          disabled={isOptimizing}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all ${
            isCreating
              ? 'bg-slate-800 text-slate-300 border border-slate-700'
              : 'bg-sky-600 hover:bg-sky-500 text-white shadow-sm shadow-sky-600/20'
          }`}
        >
          {isCreating ? (
            <>
              <X className="w-3.5 h-3.5" />
              Cancelar
            </>
          ) : (
            <>
              <Plus className="w-3.5 h-3.5" />
              Nuevo Material
            </>
          )}
        </button>
      </div>

      {/* Formulario de Creación de Material Personalizado */}
      {isCreating && (
        <form
          onSubmit={handleSaveCustom}
          className="bg-slate-950 p-3.5 rounded-xl border border-sky-500/40 flex flex-col gap-3 shadow-inner"
        >
          <div className="flex items-center justify-between">
            <span className="font-bold text-sky-300 flex items-center gap-1.5 text-xs">
              <Sparkles className="w-3.5 h-3.5" /> Definir Material Personalizado
            </span>
            <span className="text-[10px] text-slate-400 font-mono">FEA Constitutivo</span>
          </div>

          {formError && (
            <div className="p-2 rounded bg-rose-500/15 border border-rose-500/30 text-rose-300 text-[11px]">
              {formError}
            </div>
          )}

          {/* Nombre y descripción */}
          <div className="flex flex-col gap-1">
            <label className="text-slate-300 font-medium text-[11px]">Nombre del Material:</label>
            <input
              type="text"
              placeholder="Ej: Aleación Magnesio AZ31B, PLA Reforzado..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500"
              autoFocus
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-slate-400 font-medium text-[10px]">Descripción / Notas (Opcional):</label>
            <input
              type="text"
              placeholder="Ej: Para componentes aligerados aeroespaciales"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-sky-500"
            />
          </div>

          {/* Propiedades Físicas */}
          <div className="grid grid-cols-2 gap-2 pt-1">
            {/* Módulo de Young */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px] text-slate-300">
                <span>Módulo Young (E):</span>
                <span className="font-mono text-sky-400 font-bold">{youngModulus} GPa</span>
              </div>
              <input
                type="number"
                min="0.1"
                max="1200"
                step="0.5"
                value={youngModulus}
                onChange={(e) => setYoungModulus(Math.max(0.1, Number(e.target.value)))}
                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-right font-mono text-slate-200"
              />
            </div>

            {/* Poisson */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px] text-slate-300">
                <span>Poisson (ν):</span>
                <span className="font-mono text-sky-400 font-bold">{poissonRatio}</span>
              </div>
              <input
                type="number"
                min="0.05"
                max="0.49"
                step="0.01"
                value={poissonRatio}
                onChange={(e) => setPoissonRatio(Number(e.target.value))}
                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-right font-mono text-slate-200"
              />
            </div>

            {/* Límite Elástico */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px] text-slate-300">
                <span>Límite Elástico (σy):</span>
                <span className="font-mono text-sky-400 font-bold">{yieldStrength} MPa</span>
              </div>
              <input
                type="number"
                min="5"
                max="4000"
                step="10"
                value={yieldStrength}
                onChange={(e) => setYieldStrength(Math.max(1, Number(e.target.value)))}
                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-right font-mono text-slate-200"
              />
            </div>

            {/* Densidad */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px] text-slate-300">
                <span>Densidad (ρ):</span>
                <span className="font-mono text-sky-400 font-bold">{density} kg/m³</span>
              </div>
              <input
                type="number"
                min="100"
                max="25000"
                step="50"
                value={density}
                onChange={(e) => setDensity(Math.max(50, Number(e.target.value)))}
                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-right font-mono text-slate-200"
              />
            </div>
          </div>

          {/* Color del material */}
          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-slate-400">Color Representativo:</span>
            <div className="flex items-center gap-1.5">
              {colorOptions.map((c) => (
                <button
                  type="button"
                  key={c}
                  onClick={() => setColor(c)}
                  className={`w-5 h-5 rounded-full border transition-transform cursor-pointer ${
                    color === c ? 'scale-125 border-white shadow-sm' : 'border-slate-700 hover:scale-110'
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          {/* Guardar */}
          <button
            type="submit"
            className="w-full mt-1 py-2 rounded-lg bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold text-xs shadow-md shadow-sky-500/20 transition-all cursor-pointer flex items-center justify-center gap-1.5"
          >
            <CheckCircle2 className="w-4 h-4" />
            Guardar y Aplicar Material Personalizado
          </button>
        </form>
      )}

      {/* Lista de Materiales Disponibles */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-slate-300 font-semibold">
          <span>Materiales Disponibles:</span>
          <span className="text-[10px] text-slate-500 font-mono">{materialsList.length} en biblioteca</span>
        </div>

        <div className="flex flex-col gap-2 max-h-[380px] overflow-y-auto pr-1">
          {materialsList.map((mat) => {
            const isSelected = mat.id === currentMaterial.id;
            const specificStiffness = ((mat.youngModulus * 1e9) / mat.density / 1e6).toFixed(1);
            const specificStrength = ((mat.yieldStrength * 1e6) / mat.density / 1e3).toFixed(1);

            return (
              <div
                key={mat.id}
                onClick={() => !isOptimizing && onSelectMaterial(mat)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col gap-2 ${
                  isSelected
                    ? 'bg-sky-500/10 border-sky-500/70 shadow-md shadow-sky-500/5'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-400'
                }`}
              >
                {/* Header del card de material */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-3.5 h-3.5 rounded-full shrink-0 border border-slate-700"
                      style={{ backgroundColor: mat.color }}
                    />
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className={`font-bold text-xs ${isSelected ? 'text-slate-100' : 'text-slate-300'}`}>
                          {mat.name}
                        </span>
                        {mat.isCustom && (
                          <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-400 border border-amber-500/25">
                            Personalizado
                          </span>
                        )}
                      </div>
                      {mat.description && (
                        <p className="text-[10px] text-slate-500 leading-tight mt-0.5">{mat.description}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {isSelected && (
                      <span className="flex items-center gap-1 text-[10px] font-mono font-bold text-sky-400 bg-sky-500/15 px-2 py-0.5 rounded border border-sky-500/30">
                        <Check className="w-3 h-3" /> Activo
                      </span>
                    )}

                    {mat.isCustom && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemoveCustomMaterial(mat.id);
                        }}
                        disabled={isOptimizing}
                        className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                        title="Eliminar material personalizado"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Grid de Propiedades Clave */}
                <div className="grid grid-cols-4 gap-1.5 bg-slate-950/80 p-2 rounded-lg border border-slate-800/80 text-[10px] font-mono">
                  <div className="flex flex-col">
                    <span className="text-slate-500 text-[9px]">E</span>
                    <span className="text-sky-300 font-bold">{mat.youngModulus} GPa</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-slate-500 text-[9px]">ν</span>
                    <span className="text-slate-300">{mat.poissonRatio}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-slate-500 text-[9px]">σy</span>
                    <span className="text-amber-300 font-bold">{mat.yieldStrength} MPa</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-slate-500 text-[9px]">ρ</span>
                    <span className="text-slate-300">{mat.density} kg/m³</span>
                  </div>
                </div>

                {/* Ratios mecánicos */}
                <div className="flex items-center justify-between text-[10px] text-slate-400 px-0.5">
                  <span>Rigidez Específica: <strong className="text-slate-200 font-mono">{specificStiffness} kN·m/g</strong></span>
                  <span>Resistencia/Peso: <strong className="text-slate-200 font-mono">{specificStrength} kN·m/kg</strong></span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
