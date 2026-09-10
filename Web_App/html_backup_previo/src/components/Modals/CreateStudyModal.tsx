import React, { useState } from 'react';
import { PlusCircle, Layers, Check, X, ShieldAlert } from 'lucide-react';
import { MATERIALS } from '../../data/materials';

interface CreateStudyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateStudy: (config: any) => void;
}

export const CreateStudyModal: React.FC<CreateStudyModalProps> = ({
  isOpen,
  onClose,
  onCreateStudy,
}) => {
  const [studyName, setStudyName] = useState<string>('ESTRUCTURAL_AERO_V2_STATIC');
  const [analysisType, setAnalysisType] = useState<string>('linear_static');
  const [selectedMaterialId, setSelectedMaterialId] = useState<string>('ti6al4v');
  const [loadMagnitudeN, setLoadMagnitudeN] = useState<number>(4500);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreateStudy({
      studyName,
      analysisType,
      selectedMaterialId,
      loadMagnitudeN,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-[#181b24] border border-[#2e3646] rounded-xl shadow-2xl max-w-md w-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 bg-[#10131c] border-b border-[#2e3646] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PlusCircle className="w-4 h-4 text-[#10b981]" />
            <h3 className="font-headline-sm text-[#f1f5f9]">Crear Nuevo Estudio Estructural / SIMP</h3>
          </div>
          <button
            onClick={onClose}
            className="text-[#94a3b8] hover:text-[#f1f5f9] p-1 rounded hover:bg-[#1f2430] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 flex flex-col gap-3.5 text-body-sm">
          <div>
            <label className="block text-[11px] font-label-sm text-[#94a3b8] mb-1">
              Nombre del Estudio:
            </label>
            <input
              type="text"
              value={studyName}
              onChange={(e) => setStudyName(e.target.value)}
              className="w-full bg-[#10131c] border border-[#2e3646] rounded px-3 py-1.5 text-[#f1f5f9] font-mono text-[12px] focus:border-[#7bd0ff] focus:outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-[11px] font-label-sm text-[#94a3b8] mb-1">
              Tipo de Análisis Físico:
            </label>
            <select
              value={analysisType}
              onChange={(e) => setAnalysisType(e.target.value)}
              className="w-full bg-[#10131c] border border-[#2e3646] rounded px-3 py-1.5 text-[#f1f5f9] text-[12px] focus:border-[#7bd0ff] focus:outline-none"
            >
              <option value="linear_static">Elástico Lineal Estático (K·u = F)</option>
              <option value="topopt_simp">Optimización Topológica SIMP (min Compliance)</option>
              <option value="modal_eigen">Análisis Modal de Frecuencias Propias</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-label-sm text-[#94a3b8] mb-1">
              Material Constitutivo Inicial:
            </label>
            <select
              value={selectedMaterialId}
              onChange={(e) => setSelectedMaterialId(e.target.value)}
              className="w-full bg-[#10131c] border border-[#2e3646] rounded px-3 py-1.5 text-[#f1f5f9] text-[12px] focus:border-[#7bd0ff] focus:outline-none"
            >
              {MATERIALS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} (E={m.youngModulusGpa} GPa, σ_y={m.yieldStrengthMpa} MPa)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-label-sm text-[#94a3b8] mb-1">
              Magnitud de Carga Primaria (N):
            </label>
            <input
              type="number"
              value={loadMagnitudeN}
              onChange={(e) => setLoadMagnitudeN(Number(e.target.value))}
              step="100"
              className="w-full bg-[#10131c] border border-[#2e3646] rounded px-3 py-1.5 text-[#f1f5f9] font-mono text-[12px] focus:border-[#7bd0ff] focus:outline-none"
            />
          </div>

          <div className="p-2.5 rounded bg-[#0ea5e9]/10 border border-[#0ea5e9]/25 flex items-start gap-2 text-[11px] text-[#7bd0ff]">
            <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              Las condiciones de encastre y regiones preservadas se heredarán automáticamente del árbol de diseño paramétrico.
            </span>
          </div>

          {/* Footer buttons */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#2e3646]">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded bg-[#1f2430] hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9] text-[12px] transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-headline-sm text-[12px] font-medium transition-colors flex items-center gap-1.5"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Inicializar Estudio</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
