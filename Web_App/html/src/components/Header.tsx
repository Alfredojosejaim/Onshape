import React, { useState } from 'react';
import { TabId } from '../types';

interface HeaderProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  onOpenImport: () => void;
  onOpenExport: () => void;
  onOpenHelp: () => void;
  onOpenSettings: () => void;
  projectName?: string;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  onOpenImport,
  onOpenExport,
  onOpenHelp,
  onOpenSettings,
  projectName = 'Brazo_Soporte_Aero_v2.cad',
}) => {
  const [showOptionsDropdown, setShowOptionsDropdown] = useState(false);
  const [showViewDropdown, setShowViewDropdown] = useState(false);

  const tabs: { id: TabId; label: string; num: string }[] = [
    { id: 'cad-preproceso', num: '1.', label: 'Modelo CAD & Pre-proceso' },
    { id: 'mallado-condiciones', num: '2.', label: 'Mallado & Condiciones' },
    { id: 'solver-fea', num: '3.', label: 'Solver FEA & Tensiones' },
    { id: 'optimizacion-simp', num: '4.', label: 'Optimización Topológica (SIMP)' },
    { id: 'generativo-export', num: '5.', label: 'Generativo & B-Rep Export' },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#0b0e17] border-b border-[#2e3646] shadow-md">
      {/* 1. Top Utility Bar (Project info, autosave status, top menus) */}
      <div className="h-7 px-4 flex items-center justify-between border-b border-[#2e3646]/40 bg-[#0b0e17] text-[11px] text-[#94a3b8] select-none font-sans">
        <div className="flex items-center gap-2">
          {/* Options Menu */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setShowOptionsDropdown(!showOptionsDropdown);
                setShowViewDropdown(false);
              }}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-[#1f2430] hover:text-[#f1f5f9] transition-colors"
            >
              <span className="material-symbols-outlined text-[14px] text-[#7bd0ff]">tune</span>
              <span>Opciones</span>
              <span className="material-symbols-outlined text-[12px] text-[#64748b]">expand_more</span>
            </button>

            {showOptionsDropdown && (
              <div
                className="absolute left-0 top-full mt-1 w-48 bg-[#181b24] border border-[#2e3646] rounded-md shadow-2xl py-1 z-50"
                onMouseLeave={() => setShowOptionsDropdown(false)}
              >
                <button
                  type="button"
                  onClick={() => {
                    setShowOptionsDropdown(false);
                    onOpenSettings();
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#272a33] text-[#e0e2ef] flex items-center justify-between"
                >
                  <span>Configuración de Solver</span>
                  <span className="text-[10px] text-[#64748b]">Ctrl+,</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowOptionsDropdown(false);
                    alert('Proyecto guardado en almacenamiento local.');
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#272a33] text-[#e0e2ef] flex items-center justify-between"
                >
                  <span>Guardar Estudio CAE</span>
                  <span className="text-[10px] text-[#64748b]">Ctrl+S</span>
                </button>
                <div className="my-1 border-t border-[#2e3646]"></div>
                <button
                  type="button"
                  onClick={() => {
                    setShowOptionsDropdown(false);
                    onOpenExport();
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#272a33] text-[#7bd0ff]"
                >
                  Exportar Reporte Certificado
                </button>
              </div>
            )}
          </div>

          {/* View Menu */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setShowViewDropdown(!showViewDropdown);
                setShowOptionsDropdown(false);
              }}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-[#1f2430] hover:text-[#f1f5f9] transition-colors"
            >
              <span className="material-symbols-outlined text-[14px] text-[#64748b]">visibility</span>
              <span>Ver</span>
              <span className="material-symbols-outlined text-[12px] text-[#64748b]">expand_more</span>
            </button>

            {showViewDropdown && (
              <div
                className="absolute left-0 top-full mt-1 w-48 bg-[#181b24] border border-[#2e3646] rounded-md shadow-2xl py-1 z-50"
                onMouseLeave={() => setShowViewDropdown(false)}
              >
                <div className="px-3 py-1 text-[10px] font-bold text-[#64748b] uppercase">Visualización</div>
                <button
                  type="button"
                  onClick={() => setShowViewDropdown(false)}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#272a33] text-[#e0e2ef]"
                >
                  Alternar Malla Oculta (W)
                </button>
                <button
                  type="button"
                  onClick={() => setShowViewDropdown(false)}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#272a33] text-[#e0e2ef]"
                >
                  Ver Planos de Referencia WCS
                </button>
                <button
                  type="button"
                  onClick={() => setShowViewDropdown(false)}
                  className="w-full text-left px-3 py-1.5 hover:bg-[#272a33] text-[#e0e2ef]"
                >
                  Vector de Cargas y Restricciones
                </button>
              </div>
            )}
          </div>

          {/* Configuración */}
          <button
            type="button"
            onClick={onOpenSettings}
            className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-[#1f2430] hover:text-[#f1f5f9] transition-colors"
          >
            <span className="material-symbols-outlined text-[14px] text-[#64748b]">settings</span>
            <span>Configuración</span>
          </button>
        </div>

        {/* Center/Right Project status & Autosave */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse"></span>
            <span className="font-mono text-[10px] text-[#94a3b8]">● Proyecto: {projectName}</span>
          </div>
          <span className="font-mono text-[10px] text-[#64748b] border border-[#2e3646]/50 px-1.5 py-0.5 rounded bg-[#1f2430]/40">
            Autoguardado
          </span>
        </div>
      </div>

      {/* 2. Main Branding & Actions Bar */}
      <div className="h-12 px-4 flex items-center justify-between gap-4 border-b border-[#2e3646]/50">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-3 min-w-0 flex-shrink-0">
          <img
            alt="Topología Optimizada Logo"
            className="h-8 w-auto object-contain"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuB_d5POHHoiQhFDbOpHlSbtvQYFsIR11299TryzQhfbD7wXUlXgLA5W18Q9jRa9AKRWpYieZMF5DKGqrzUNl9O2pgUNA5w9Os51AfA7jaS9RmekKZvc9pjLphzf-jYwWSUokh4v2YRpZRt08V7VBLfo7stsGbepjtZT360NUKXxcr_zOrTxR1_IDouI5ZysqDElbN-_h0QioAfXeKQVoSMYwRBKezZXt7StdqspSlba5ItFFJrT_Tcr"
          />
          <div className="flex items-center gap-1">
            <span className="font-bold text-[14px] tracking-wider text-[#f1f5f9] whitespace-nowrap">
              TOPOLOGÍA OPTIMIZADA
            </span>
            <span className="ml-1.5 px-1.5 py-0.5 text-[9px] font-mono font-semibold uppercase bg-[#0ea5e9]/20 text-[#7bd0ff] rounded border border-[#0ea5e9]/30">
              SIMP FEA v2.4
            </span>
          </div>
        </div>

        {/* Action Buttons: Importar, Exportar, Help, User */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="flex items-center gap-1.5 mr-1">
            <button
              onClick={onOpenImport}
              type="button"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#1f2430]/80 hover:bg-[#272a33] border border-[#2e3646] hover:border-[#7bd0ff]/50 text-[#f1f5f9] hover:text-[#7bd0ff] text-[12px] font-semibold transition-all shadow-sm cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-[#7bd0ff]">upload</span>
              <span>Importar</span>
            </button>
            <button
              onClick={onOpenExport}
              type="button"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#1f2430]/80 hover:bg-[#272a33] border border-[#2e3646] hover:border-[#7bd0ff]/50 text-[#f1f5f9] hover:text-[#7bd0ff] text-[12px] font-semibold transition-all shadow-sm cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-[#7bd0ff]">download</span>
              <span>Exportar</span>
            </button>
          </div>

          <button
            onClick={onOpenHelp}
            type="button"
            className="w-8 h-8 rounded-full flex items-center justify-center bg-[#1f2430]/80 hover:bg-[#272a33] border border-[#2e3646] text-[#94a3b8] hover:text-[#f1f5f9] transition-colors cursor-pointer"
            title="Ayuda y Atajos (F1)"
          >
            <span className="material-symbols-outlined text-[18px]">help</span>
          </button>

          <div
            className="w-8 h-8 rounded-full border border-[#2e3646] overflow-hidden flex items-center justify-center cursor-pointer hover:border-[#7bd0ff] transition-colors"
            title="Ing. Estructural - alfredojosejaim03@gmail.com"
          >
            <img
              alt="Usuario"
              className="w-full h-full object-cover"
              src="https://lh3.googleusercontent.com/aida/AEtjO1UXiZU0R2kEsx-SdP1ot9-6do1uPU2K-fDH_CI3UEDOX91_9hDhaPkQRM3uS7lXPMyxIHB28cLeY0C23cfMnQTylfiJrS-v0pMHbMlH1KbsZ2ndwe8VNf1OXIW61hfLbTju4RnlRdavfgp--qkZUYgaTCqyDSfdp2igU44--firpDOXb5ppIIpdNB-sZxrqgBIRA9PLMQGIhnYbyzYt7oLROR4F-Ve38yD6FSZpLKSpN7M84k1HFn57XSE"
            />
          </div>
        </div>
      </div>

      {/* 3. Navigation Bar: 5 Work Area Stages / Tabs */}
      <nav className="h-8 px-4 flex items-center gap-1 bg-[#0b0e17] overflow-x-auto">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={`h-full flex items-center px-3 text-[12px] border-b-2 whitespace-nowrap transition-all cursor-pointer ${
                isActive
                  ? 'bg-[#181b24] text-[#7bd0ff] border-[#0ea5e9] font-semibold shadow-inner'
                  : 'border-transparent text-[#94a3b8] hover:text-[#e0e2ef] hover:bg-[#181b24]/40 font-normal'
              }`}
            >
              <span className="mr-1 opacity-70 font-mono text-[11px]">{tab.num}</span>
              <span>{tab.label.replace(/^[0-9]\.\s*/, '')}</span>
            </button>
          );
        })}
      </nav>
    </header>
  );
};
