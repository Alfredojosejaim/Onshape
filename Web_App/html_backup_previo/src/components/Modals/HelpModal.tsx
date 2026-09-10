import React from 'react';
import { HelpCircle, Keyboard, Cpu, Compass, X, Check } from 'lucide-react';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-[#181b24] border border-[#2e3646] rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="px-5 py-3.5 bg-[#10131c] border-b border-[#2e3646] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-[#7bd0ff]" />
            <h3 className="font-headline-md text-[#f1f5f9]">Guía del Sistema & Atajos de Teclado</h3>
          </div>
          <button
            onClick={onClose}
            className="text-[#94a3b8] hover:text-[#f1f5f9] p-1 rounded hover:bg-[#1f2430] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 flex flex-col gap-5 text-body-sm text-[#bec8d2]">
          {/* Section 1: Navigation shortcuts */}
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-[#7bd0ff] font-headline-sm">
              <Keyboard className="w-4 h-4" />
              <h4>Controles de Viewport 3D (VTK OpenGL2)</h4>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2.5 rounded bg-[#10131c] border border-[#2e3646] flex items-center justify-between">
                <span className="text-[#94a3b8]">Rotación de Órbita:</span>
                <kbd className="px-2 py-0.5 rounded bg-[#1f2430] text-[#7bd0ff] font-mono border border-[#2e3646]">
                  Shift + Clic Izquierdo / Arrastrar
                </kbd>
              </div>
              <div className="p-2.5 rounded bg-[#10131c] border border-[#2e3646] flex items-center justify-between">
                <span className="text-[#94a3b8]">Desplazamiento (Pan):</span>
                <kbd className="px-2 py-0.5 rounded bg-[#1f2430] text-[#7bd0ff] font-mono border border-[#2e3646]">
                  Botón Central (MMB) / Arrastrar
                </kbd>
              </div>
              <div className="p-2.5 rounded bg-[#10131c] border border-[#2e3646] flex items-center justify-between">
                <span className="text-[#94a3b8]">Zoom de Cámara:</span>
                <kbd className="px-2 py-0.5 rounded bg-[#1f2430] text-[#7bd0ff] font-mono border border-[#2e3646]">
                  Rueda del Ratón (Scroll)
                </kbd>
              </div>
              <div className="p-2.5 rounded bg-[#10131c] border border-[#2e3646] flex items-center justify-between">
                <span className="text-[#94a3b8]">Ajustar / Resetear Vista:</span>
                <kbd className="px-2 py-0.5 rounded bg-[#1f2430] text-[#7bd0ff] font-mono border border-[#2e3646]">
                  Tecla R / Botón FIT
                </kbd>
              </div>
            </div>
          </section>

          {/* Section 2: Mathematical SIMP Model */}
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-[#ffb95f] font-headline-sm">
              <Compass className="w-4 h-4" />
              <h4>Formulación Matemática SIMP (Solid Isotropic Material with Penalisation)</h4>
            </div>
            <div className="p-3 rounded bg-[#10131c] border border-[#2e3646] flex flex-col gap-2 text-[11px] font-mono">
              <div className="text-[#7bd0ff]">
                K_e(ρ) = [ρ_min + (1 - ρ_min) · ρ_e^p] · K_e0
              </div>
              <p className="text-[#94a3b8] font-sans">
                Donde <strong>p = 3.0</strong> penaliza los elementos intermedios hacia 0 (vacío) o 1 (sólido denso).
                El filtro de densidad PDE Helmholtz previene el problema del tablero de ajedrez (checkerboard) y garantiza un espesor mínimo de puntal.
              </p>
              <div className="text-[#10b981]">
                min Compliance C(ρ) = Uᵀ · K(ρ) · U  sujeto a: V(ρ) / V₀ ≤ 0.35
              </div>
            </div>
          </section>

          {/* Section 3: Engine Architecture */}
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-[#10b981] font-headline-sm">
              <Cpu className="w-4 h-4" />
              <h4>Arquitectura Standalone First & Motores de Cálculo</h4>
            </div>
            <ul className="space-y-1.5 text-[11px] text-[#94a3b8]">
              <li className="flex items-start gap-2">
                <Check className="w-3.5 h-3.5 text-[#10b981] mt-0.5 shrink-0" />
                <span><strong>Motor Local (NumPy/SciPy):</strong> Skyline LU directo y gradiente conjugado (CG) de 64 bits para ejecución ultrarrápida sin dependencias externas.</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-3.5 h-3.5 text-[#10b981] mt-0.5 shrink-0" />
                <span><strong>Kratos Multiphysics:</strong> Solucionador iterativo AMGCL con fallback automático a skyline_lu para mallas de gran escala.</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-3.5 h-3.5 text-[#10b981] mt-0.5 shrink-0" />
                <span><strong>Reconstrucción B-Rep (OpenCASCADE):</strong> Marching Tetrahedra → Suavizado Laplaciano C¹ → Sewing hermético → Booleana con sólidos exactos → Exportación STEP AP242.</span>
              </li>
            </ul>
          </section>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 bg-[#10131c] border-t border-[#2e3646] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-headline-sm text-[12px] font-medium transition-colors"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
