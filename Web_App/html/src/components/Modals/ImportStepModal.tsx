import React, { useState } from 'react';
import { FolderOpen, Upload, FileText, CheckCircle2, X } from 'lucide-react';
import { backend } from '../../lib/bridge';

interface ImportStepModalProps {
  isOpen: boolean;
  onClose: () => void;
  onModelSelected: (filename: string, details?: any) => void;
}

export const ImportStepModal: React.FC<ImportStepModalProps> = ({
  isOpen,
  onClose,
  onModelSelected,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<string>('cono_soporte_aero.step');
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [importedCustomName, setImportedCustomName] = useState<string | null>(null);
  const [stepPath, setStepPath] = useState<string>('fixtures\\cono.step');
  const [isImporting, setIsImporting] = useState<boolean>(false);
  const [status, setStatus] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  if (!isOpen) return null;

  const presets = [
    {
      id: 'cono_soporte_aero.step',
      name: 'cono_soporte_aero.step',
      description: 'Soporte cónico aeronáutico (Al 7075-T6, 12 caras, 1 buje preservado)',
      size: '3.42 kg · 1,217 cm³',
      elements: '184,920 Tet4',
    },
    {
      id: 'viga_voladizo_bracket.step',
      name: 'viga_voladizo_bracket.step',
      description: 'Ménsula estructural de voladizo con doble anclaje y orejeta de carga',
      size: '4.15 kg · 1,480 cm³',
      elements: '210,400 Tet4',
    },
    {
      id: 'suspension_upright_formula.step',
      name: 'suspension_upright_formula.step',
      description: 'Mangueta de suspensión delantera con puntos de fijación de rótula',
      size: '2.80 kg · 980 cm³',
      elements: '162,150 Tet4',
    },
    {
      id: 'brida_turbina_generativa.step',
      name: 'brida_turbina_generativa.step',
      description: 'Brida concéntrica con 6 taladros perimetrales y núcleo de empuje',
      size: '5.20 kg · 1,850 cm³',
      elements: '245,800 Tet4',
    },
  ];

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setImportedCustomName(file.name);
      setSelectedPreset(file.name);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setImportedCustomName(file.name);
      setSelectedPreset(file.name);
    }
  };

  const handleConfirm = async () => {
    setIsImporting(true);
    setStatus(null);
    setStatusError(null);
    try {
      const path = importedCustomName ?? stepPath.trim() !== '' ? (importedCustomName ?? stepPath.trim()) : selectedPreset;
      // Si el usuario eligió preset sin ruta completa, usar la ruta del input o el preset
      const effectivePath = importedCustomName ?? (stepPath.trim() !== '' ? stepPath.trim() : selectedPreset);
      void path;
      const r = (await backend.importStep(effectivePath)) as { ok: boolean; error?: string };
      if (!r.ok) {
        setStatusError(r.error ?? 'importStep devolvió ok=false');
        return;
      }
      const base = effectivePath.split(/[/\\]/).pop() || effectivePath;
      setStatus(`Importado OK: ${base}`);
      onModelSelected(base);
      onClose();
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-[#181b24] border border-[#2e3646] rounded-xl shadow-2xl max-w-lg w-full overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-4 py-3 bg-[#10131c] border-b border-[#2e3646] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-[#0ea5e9]/20 flex items-center justify-center text-[#7bd0ff]">
              <FolderOpen className="w-3.5 h-3.5" />
            </div>
            <h3 className="font-headline-sm text-[#f1f5f9]">Importar Geometría STEP (.step / .stp)</h3>
          </div>
          <button
            onClick={onClose}
            className="text-[#94a3b8] hover:text-[#f1f5f9] p-1 rounded hover:bg-[#1f2430] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 flex flex-col gap-4">
          {/* Drag & Drop Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleFileDrop}
            className={`border-2 border-dashed rounded-lg p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
              dragActive
                ? 'border-[#7bd0ff] bg-[#0ea5e9]/10'
                : 'border-[#2e3646] hover:border-[#7bd0ff]/50 bg-[#10131c]/50'
            }`}
          >
            <Upload className="w-8 h-8 text-[#7bd0ff] mb-2 animate-bounce" />
            <span className="font-body-md text-[#f1f5f9] font-medium">
              Arrastra y suelta tu archivo STEP local aquí
            </span>
            <span className="font-label-sm text-[#64748b] text-[11px] mt-1">
              Compatible con AP203, AP214 y AP242 (B-Rep Sólido Manifold)
            </span>
            <label className="mt-3 px-3 py-1.5 rounded bg-[#1f2430] hover:bg-[#272a33] text-[#7bd0ff] border border-[#2e3646] font-label-sm text-[11px] cursor-pointer transition-colors">
              Explorar Archivo en Disco
              <input
                type="file"
                accept=".step,.stp"
                onChange={handleFileInput}
                className="hidden"
              />
            </label>
          </div>

          {importedCustomName && (
            <div className="p-2.5 rounded bg-[#10b981]/15 border border-[#10b981]/30 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#10b981]" />
              <span className="font-label-sm text-[#10b981] text-[11px]">
                Archivo cargado con éxito: <strong>{importedCustomName}</strong>
              </span>
            </div>
          )}

          {/* Ruta local STEP */}
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-[11px] text-[#94a3b8] uppercase tracking-wider">
              Ruta local del archivo STEP:
            </label>
            <input
              type="text"
              value={stepPath}
              onChange={(e) => setStepPath(e.target.value)}
              className="w-full bg-[#10131c] border border-[#2e3646] rounded px-2.5 py-1.5 font-mono text-[11px] text-[#f1f5f9] focus:outline-none focus:border-[#7bd0ff]"
            />
          </div>

          {status && (
            <div className="p-2.5 rounded bg-[#10b981]/15 border border-[#10b981]/30 text-[#10b981] text-[11px]">
              {status}
            </div>
          )}
          {statusError && (
            <div className="p-2.5 rounded bg-[#ef4444]/15 border border-[#ef4444]/30 text-[#fca5a5] text-[11px]">
              Error: {statusError}
            </div>
          )}

          {/* Modelos Preestablecidos de Validación Standalone */}
          <div className="flex flex-col gap-1.5">
            <label className="font-label-sm text-[11px] text-[#94a3b8] uppercase tracking-wider">
              O selecciona un modelo preestablecido del banco de pruebas:
            </label>
            <div className="grid grid-cols-1 gap-1.5 max-h-48 overflow-y-auto pr-1">
              {presets.map((preset) => {
                const isSelected = selectedPreset === preset.id;
                return (
                  <div
                    key={preset.id}
                    onClick={() => {
                      setSelectedPreset(preset.id);
                      setImportedCustomName(null);
                    }}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-[#1f2430] border-[#0ea5e9] text-[#f1f5f9]'
                        : 'bg-[#10131c]/60 border-[#2e3646] hover:bg-[#1f2430]/60 text-[#94a3b8]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className={`w-4 h-4 shrink-0 ${isSelected ? 'text-[#7bd0ff]' : 'text-[#64748b]'}`} />
                      <div className="flex flex-col min-w-0">
                        <span className="font-headline-sm text-[12px] text-[#f1f5f9] truncate">
                          {preset.name}
                        </span>
                        <span className="font-body-sm text-[10px] text-[#64748b] truncate">
                          {preset.description}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end shrink-0 pl-2">
                      <span className="font-label-sm text-[10px] text-[#7bd0ff]">{preset.size}</span>
                      <span className="font-label-sm text-[9px] text-[#64748b]">{preset.elements}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-4 py-3 bg-[#10131c] border-t border-[#2e3646] flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-[#1f2430] hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9] font-body-sm text-[12px] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={isImporting}
            className="px-4 py-1.5 rounded bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-headline-sm text-[12px] transition-colors font-medium flex items-center gap-1.5 disabled:opacity-60"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{isImporting ? 'Importando...' : 'Cargar Modelo STEP'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
