import React from 'react';
import { ScreenId, FeaBackend } from '../types';
import {
  FileCode,
  FolderOpen,
  PlusCircle,
  Grid,
  Calculator,
  Binary,
  Layers,
  Download,
  HelpCircle,
  Cpu,
  RefreshCw,
} from 'lucide-react';

interface HeaderProps {
  currentScreen: ScreenId;
  onSelectScreen: (screen: ScreenId) => void;
  activeFilename: string;
  backend: FeaBackend;
  onToggleBackend: () => void;
  onOpenImportModal: () => void;
  onOpenHelpModal: () => void;
  onOpenCreateStudyModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentScreen,
  onSelectScreen,
  activeFilename,
  backend,
  onToggleBackend,
  onOpenImportModal,
  onOpenHelpModal,
  onOpenCreateStudyModal,
}) => {
  const screens: { id: ScreenId; label: string }[] = [
    { id: 'modelo-cad-y-pre-proceso', label: '1. Modelo CAD & Pre-proceso' },
    { id: 'mallado-y-condiciones', label: '2. Mallado & Condiciones' },
    { id: 'solver-fea-y-tensiones', label: '3. Solver FEA & Tensiones' },
    { id: 'optimizacion-topologica-simp', label: '4. Optimización Topológica (SIMP)' },
    { id: 'generativo-y-b-rep-export', label: '5. Generativo & B-Rep Export' },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#0b0e17] border-b border-[#2e3646]">
      {/* Top Main Bar */}
      <div className="h-12 px-3 flex items-center justify-between gap-3 border-b border-[#2e3646]/50">
        {/* Brand & File Chip */}
        <div className="flex items-center gap-3 min-w-0 flex-shrink-0">
          {/* Logo icon */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-[#181b24] border border-[#2e3646] flex items-center justify-center text-[#7bd0ff] shadow-inner">
              <span className="material-symbols-outlined text-[20px] text-[#89ceff]">
                deployed_code
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-headline-md tracking-tight text-[#f1f5f9] whitespace-nowrap">
                TOPOLOGÍA OPTIMIZADA
              </span>
              <span className="px-1.5 py-0.5 rounded bg-[#32343e] text-[#7bd0ff] font-label-sm text-[10px] border border-[#2e3646]">
                v2.4 Standalone
              </span>
            </div>
          </div>

          <div className="hidden xl:flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#181b24] border border-[#2e3646]">
            <FileCode className="w-3.5 h-3.5 text-[#7bd0ff]" />
            <span className="font-label-sm text-[11px] text-[#94a3b8] truncate max-w-[280px]">
              {activeFilename} ({backend === 'numpy' ? 'Modo Local / NumPy FEA' : 'Kratos Multiphysics'})
            </span>
          </div>
        </div>

        {/* Global Toolbar Action Buttons */}
        <div className="flex items-center gap-1 overflow-x-auto py-0.5">
          <button
            onClick={onOpenImportModal}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#1f2430] hover:bg-[#272a33] border border-[#2e3646] text-[#f1f5f9] hover:text-[#7bd0ff] hover:border-[#7bd0ff]/40 font-body-sm text-[11px] transition-colors"
            type="button"
            title="Importar archivo STEP local"
          >
            <FolderOpen className="w-3.5 h-3.5 text-[#7bd0ff]" />
            <span>Importar STEP</span>
          </button>

          <button
            onClick={onOpenCreateStudyModal}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#1f2430] hover:bg-[#272a33] border border-[#2e3646] text-[#f1f5f9] hover:text-[#7bd0ff] hover:border-[#7bd0ff]/40 font-body-sm text-[11px] transition-colors"
            type="button"
            title="Crear nuevo estudio estático o topológico"
          >
            <PlusCircle className="w-3.5 h-3.5 text-[#10b981]" />
            <span>Crear Estudio</span>
          </button>

          <button
            onClick={() => onSelectScreen('mallado-y-condiciones')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded border font-body-sm text-[11px] transition-colors ${
              currentScreen === 'mallado-y-condiciones'
                ? 'bg-[#0ea5e9]/20 border-[#0ea5e9] text-[#7bd0ff]'
                : 'bg-[#1f2430] hover:bg-[#272a33] border-[#2e3646] text-[#f1f5f9] hover:text-[#7bd0ff]'
            }`}
            type="button"
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Malla Gmsh</span>
          </button>

          <button
            onClick={() => onSelectScreen('solver-fea-y-tensiones')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded border font-body-sm text-[11px] transition-colors ${
              currentScreen === 'solver-fea-y-tensiones'
                ? 'bg-[#0ea5e9]/20 border-[#0ea5e9] text-[#7bd0ff]'
                : 'bg-[#1f2430] hover:bg-[#272a33] border-[#2e3646] text-[#f1f5f9] hover:text-[#7bd0ff]'
            }`}
            type="button"
          >
            <Calculator className="w-3.5 h-3.5 text-[#ffb95f]" />
            <span>Resolver FEA (K·u=F)</span>
          </button>

          <button
            onClick={() => onSelectScreen('optimizacion-topologica-simp')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded border font-body-sm text-[11px] transition-colors ${
              currentScreen === 'optimizacion-topologica-simp'
                ? 'bg-[#0ea5e9] text-[#003751] font-semibold border-[#7bd0ff]'
                : 'bg-[#0ea5e9]/25 hover:bg-[#0ea5e9] hover:text-[#003751] border-[#0ea5e9] text-[#7bd0ff]'
            }`}
            type="button"
          >
            <Binary className="w-3.5 h-3.5" />
            <span>Optimización SIMP</span>
          </button>

          <button
            onClick={() => onSelectScreen('generativo-y-b-rep-export')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded border font-body-sm text-[11px] transition-colors ${
              currentScreen === 'generativo-y-b-rep-export'
                ? 'bg-[#0ea5e9]/20 border-[#0ea5e9] text-[#7bd0ff]'
                : 'bg-[#1f2430] hover:bg-[#272a33] border-[#2e3646] text-[#f1f5f9] hover:text-[#7bd0ff]'
            }`}
            type="button"
          >
            <Layers className="w-3.5 h-3.5 text-[#89ceff]" />
            <span>Reconstrucción B-Rep</span>
          </button>

          <button
            onClick={() => onSelectScreen('generativo-y-b-rep-export')}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#1f2430] hover:bg-[#272a33] border border-[#2e3646] text-[#f1f5f9] hover:text-[#7bd0ff] hover:border-[#7bd0ff]/40 font-body-sm text-[11px] transition-colors"
            type="button"
          >
            <Download className="w-3.5 h-3.5 text-[#10b981]" />
            <span>Exportar STEP</span>
          </button>
        </div>

        {/* Engine Status & Help */}
        <div className="flex items-center gap-2.5 flex-shrink-0">
          {/* Motor toggle chip */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#181b24] border border-[#2e3646]">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
            <span className="font-label-sm text-[10px] text-[#94a3b8]">Motor:</span>
            <span className="font-label-sm text-[11px] text-[#f1f5f9] font-medium">
              {backend === 'numpy' ? 'Local (Tet4 NumPy)' : 'Kratos Multiphysics'}
            </span>
            <button
              onClick={onToggleBackend}
              className="text-[#7bd0ff] hover:text-[#89ceff] transition-colors text-[14px] ml-1 p-0.5 rounded hover:bg-[#272a33]"
              title={`Alternar a ${backend === 'numpy' ? 'Kratos Multiphysics' : 'NumPy Local'}`}
              type="button"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>

          <div className="hidden 2xl:flex items-center gap-1.5 px-2 py-1 rounded bg-[#181b24] border border-[#2e3646]">
            <Cpu className="w-3.5 h-3.5 text-[#64748b]" />
            <span className="font-label-sm text-[11px] text-[#f1f5f9]">1.4 GB / amgcl</span>
          </div>

          <button
            onClick={onOpenHelpModal}
            className="w-7 h-7 flex items-center justify-center rounded bg-[#1f2430] hover:bg-[#272a33] border border-[#2e3646] text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
            title="Ayuda y Atajos de Teclado (F1)"
            type="button"
          >
            <HelpCircle className="w-4 h-4" />
          </button>

          <div
            className="w-7 h-7 rounded-full bg-[#1f2430] border border-[#2e3646] flex items-center justify-center text-[#89ceff] font-label-sm text-[11px] font-bold"
            title="Ingeniero Estructural / Operador Standalone"
          >
            FEA
          </div>
        </div>
      </div>

      {/* Sub-navigation Tabs Strip */}
      <nav className="h-8 px-3 flex items-center gap-1 bg-[#0b0e17] overflow-x-auto">
        {screens.map((screen) => {
          const isActive = currentScreen === screen.id;
          return (
            <button
              key={screen.id}
              onClick={() => onSelectScreen(screen.id)}
              className={`h-full flex items-center px-3 border-b-2 font-body-sm text-[12px] transition-colors whitespace-nowrap ${
                isActive
                  ? 'bg-[#181b24] text-[#7bd0ff] border-[#0ea5e9] font-medium'
                  : 'border-transparent text-[#94a3b8] hover:text-[#e0e2ef] hover:bg-[#181b24]/40'
              }`}
            >
              {screen.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
};
