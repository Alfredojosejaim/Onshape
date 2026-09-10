import React, { useState } from 'react';

interface HeaderProps {
  onOpenImport: () => void;
  onOpenExport: () => void;
  onOpenHelp: () => void;
  onResetView: () => void;
  onToggleMesh: () => void;
  showMesh: boolean;
  onSelectView: (view: 'iso' | 'top' | 'front' | 'right') => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenImport,
  onOpenExport,
  onOpenHelp,
  onResetView,
  onToggleMesh,
  showMesh,
  onSelectView,
}) => {
  const [openMenu, setOpenMenu] = useState<'opciones' | 'ver' | 'config' | null>(null);

  const toggleMenu = (menu: 'opciones' | 'ver' | 'config') => {
    setOpenMenu(openMenu === menu ? null : menu);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-surface-container-lowest border-b border-border-subtle select-none">
      {/* Top micro-bar */}
      <div className="h-7 px-space-md flex items-center justify-between border-b border-border-subtle/40 bg-surface-container-lowest text-[11px] text-text-secondary">
        <div className="flex items-center gap-space-xs relative">
          {/* Menu Opciones */}
          <div className="relative">
            <button
              id="menu-opciones-btn"
              type="button"
              onClick={() => toggleMenu('opciones')}
              className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-surface-elevated hover:text-text-primary text-[11px] text-text-secondary transition-colors"
            >
              <span className="material-symbols-outlined text-[14px] text-secondary">tune</span>
              <span>Opciones</span>
              <span className="material-symbols-outlined text-[12px] text-text-muted">expand_more</span>
            </button>
            {openMenu === 'opciones' && (
              <div
                className="absolute left-0 top-full mt-1 w-52 bg-surface-elevated border border-border-subtle rounded-md shadow-xl py-1 z-50 text-[12px]"
                onMouseLeave={() => setOpenMenu(null)}
              >
                <button
                  onClick={() => {
                    onOpenImport();
                    setOpenMenu(null);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-surface-container-high text-text-primary flex items-center gap-2"
                >
                  <span className="material-symbols-outlined text-[15px] text-secondary">file_open</span>
                  Nuevo Estudio desde STEP/CAD
                </button>
                <button
                  onClick={() => {
                    onOpenExport();
                    setOpenMenu(null);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-surface-container-high text-text-primary flex items-center gap-2"
                >
                  <span className="material-symbols-outlined text-[15px] text-secondary">save</span>
                  Guardar Configuración JSON
                </button>
                <div className="border-t border-border-subtle my-1"></div>
                <div className="px-3 py-1 text-[10px] text-text-muted font-mono">
                  SOLVER: SIMP 3D FEM Engine v4.2
                </div>
              </div>
            )}
          </div>

          {/* Menu Ver */}
          <div className="relative">
            <button
              id="menu-ver-btn"
              type="button"
              onClick={() => toggleMenu('ver')}
              className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-surface-elevated hover:text-text-primary text-[11px] text-text-secondary transition-colors"
            >
              <span className="material-symbols-outlined text-[14px] text-text-muted">visibility</span>
              <span>Ver</span>
              <span className="material-symbols-outlined text-[12px] text-text-muted">expand_more</span>
            </button>
            {openMenu === 'ver' && (
              <div
                className="absolute left-0 top-full mt-1 w-48 bg-surface-elevated border border-border-subtle rounded-md shadow-xl py-1 z-50 text-[12px]"
                onMouseLeave={() => setOpenMenu(null)}
              >
                <button
                  onClick={() => {
                    onSelectView('iso');
                    setOpenMenu(null);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-surface-container-high text-text-primary flex items-center justify-between"
                >
                  <span>Vista Isométrica</span>
                  <span className="text-text-muted text-[10px] font-mono">Num 0</span>
                </button>
                <button
                  onClick={() => {
                    onSelectView('top');
                    setOpenMenu(null);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-surface-container-high text-text-primary flex items-center justify-between"
                >
                  <span>Vista Superior (Top)</span>
                  <span className="text-text-muted text-[10px] font-mono">Num 7</span>
                </button>
                <button
                  onClick={() => {
                    onSelectView('front');
                    setOpenMenu(null);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-surface-container-high text-text-primary flex items-center justify-between"
                >
                  <span>Vista Frontal (Front)</span>
                  <span className="text-text-muted text-[10px] font-mono">Num 1</span>
                </button>
                <button
                  onClick={() => {
                    onSelectView('right');
                    setOpenMenu(null);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-surface-container-high text-text-primary flex items-center justify-between"
                >
                  <span>Vista Lateral (Right)</span>
                  <span className="text-text-muted text-[10px] font-mono">Num 3</span>
                </button>
                <div className="border-t border-border-subtle my-1"></div>
                <button
                  onClick={() => {
                    onToggleMesh();
                    setOpenMenu(null);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-surface-container-high text-text-primary flex items-center justify-between"
                >
                  <span>{showMesh ? 'Ocultar Malla Gmsh' : 'Mostrar Malla Gmsh'}</span>
                  <span className="text-text-muted text-[10px] font-mono">M</span>
                </button>
                <button
                  onClick={() => {
                    onResetView();
                    setOpenMenu(null);
                  }}
                  className="w-full text-left px-3 py-1.5 hover:bg-surface-container-high text-text-primary flex items-center justify-between"
                >
                  <span>Ajustar Zoom (Fit)</span>
                  <span className="text-text-muted text-[10px] font-mono">F</span>
                </button>
              </div>
            )}
          </div>

          {/* Menu Configuración */}
          <div className="relative">
            <button
              id="menu-config-btn"
              type="button"
              onClick={() => toggleMenu('config')}
              className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-surface-elevated hover:text-text-primary text-[11px] text-text-secondary transition-colors"
            >
              <span className="material-symbols-outlined text-[14px] text-text-muted">settings</span>
              <span>Configuración</span>
            </button>
            {openMenu === 'config' && (
              <div
                className="absolute left-0 top-full mt-1 w-56 bg-surface-elevated border border-border-subtle rounded-md shadow-xl p-3 z-50 text-[11px]"
                onMouseLeave={() => setOpenMenu(null)}
              >
                <div className="font-semibold text-text-primary mb-2">Entorno de Cómputo CAE</div>
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/40">
                  <span className="text-text-muted">Aceleración:</span>
                  <span className="text-fea-stress-optimal font-mono font-medium">WebGL 2.0 / GPU</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-border-subtle/40">
                  <span className="text-text-muted">Unidades base:</span>
                  <span className="text-text-primary font-mono">SI (mm, N, MPa)</span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-text-muted">Algoritmo SIMP:</span>
                  <span className="text-secondary font-mono">OC (Optimality Crit.)</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-fea-stress-optimal animate-pulse"></span>
            <span className="text-[10px] font-mono text-text-secondary">ESTADO: LISTO</span>
          </div>
        </div>
      </div>

      {/* Main Brand & Action Row */}
      <div className="h-12 px-space-md flex items-center justify-between gap-space-md border-b border-border-subtle/50">
        <div className="flex items-center gap-space-md min-w-0 flex-shrink-0">
          <div className="relative h-8 w-8 rounded bg-surface-container-lowest border border-secondary/30 flex items-center justify-center overflow-hidden shadow-sm">
            <img
              alt="Isotipo Topología Optimizada"
              className="h-full w-full object-contain"
              src="https://lh3.googleusercontent.com/aida/AEtjO1VJ8LqcXt8gfogoOHQrbB29AG0yRLPEKm8yKE0aXB2EzRn1eNb63XD6QkfBEFz4wrabdCPMeYE7saiolhRQe4-sDO6IrqY1eOtyXaeO_CjcFzTaZ6Gplc4pDb5vTBdRd12E9oeAVs1DXC_yOTkPPPV0AQne2pvUN7mgEwpSD3hQZYhdYTLqijVbHnwh6hCh03hj7EZ4IFLY0se8W1a5km373ZX8WFP7Dju74btpnaHMOn6Z694T8Q5jLb4"
              onError={(e) => {
                (e.currentTarget as HTMLElement).style.display = 'none';
              }}
            />
            {/* Hexagonal Topology Cellular SVG Fallback Icon */}
            <svg
              className="absolute inset-0 w-full h-full p-1 text-secondary pointer-events-none"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2l8.5 5v10L12 22l-8.5-5V7L12 2z" stroke="#00a6e0" />
              <path d="M12 22V12" stroke="#7bd0ff" />
              <path d="M12 12L3.5 7" stroke="#7bd0ff" />
              <path d="M12 12l8.5-5" stroke="#7bd0ff" />
              <circle cx="12" cy="12" r="2.5" fill="#7bd0ff" />
            </svg>
          </div>
          <div className="flex items-center gap-space-xs">
            <span
              className="font-semibold text-[15px] text-text-primary whitespace-nowrap tracking-tight"
              style={{ fontFamily: 'Inter, system-ui, -apple-system, sans-serif' }}
            >
              Topología Optimizada
            </span>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-secondary/15 text-secondary border border-secondary/30 ml-1">
              v4.2 PRO
            </span>
          </div>
        </div>

        {/* Global CTAs & User */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="flex items-center gap-1.5 mr-1">
            <button
              id="import-btn"
              onClick={onOpenImport}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-elevated/80 hover:bg-surface-container-high border border-border-subtle hover:border-secondary/50 text-text-primary hover:text-secondary text-[12px] font-medium transition-all shadow-sm active:scale-95"
              type="button"
            >
              <span className="material-symbols-outlined text-[16px] text-secondary">upload</span>
              <span>Importar</span>
            </button>
            <button
              id="export-btn"
              onClick={onOpenExport}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-elevated/80 hover:bg-surface-container-high border border-border-subtle hover:border-secondary/50 text-text-primary hover:text-secondary text-[12px] font-medium transition-all shadow-sm active:scale-95"
              type="button"
            >
              <span className="material-symbols-outlined text-[16px] text-secondary">download</span>
              <span>Exportar</span>
            </button>
          </div>

          <button
            id="help-btn"
            onClick={onOpenHelp}
            className="w-8 h-8 rounded-full flex items-center justify-center bg-surface-elevated/80 hover:bg-surface-container-high border border-border-subtle text-text-secondary hover:text-text-primary transition-colors"
            title="Ayuda y Atajos (F1)"
            type="button"
          >
            <span className="material-symbols-outlined text-[18px]">help</span>
          </button>

          <div
            className="w-8 h-8 rounded-full border border-border-subtle overflow-hidden flex items-center justify-center bg-[#1f2430] cursor-pointer hover:border-secondary transition-colors relative"
            title="Ingeniero Estructural - Alfredo Jaime"
          >
            <span className="material-symbols-outlined text-[18px] text-[#94a3b8]">person</span>
            <img
              alt="Usuario"
              className="w-full h-full object-cover absolute inset-0"
              src="https://lh3.googleusercontent.com/aida/AEtjO1UXiZU0R2kEsx-SdP1ot9-6do1uPU2K-fDH_CI3UEDOX91_9hDhaPkQRM3uS7lXPMyxIHB28cLeY0C23cfMnQTylfiJrS-v0pMHbMlH1KbsZ2ndwe8VNf1OXIW61hfLbTju4RnlRdavfgp--qkZUYgaTCqyDSfdp2igU44--firpDOXb5ppIIpdNB-sZxrqgBIRA9PLMQGIhnYbyzYt7oLROR4F-Ve38yD6FSZpLKSpN7M84k1HFn57XSE"
              onError={(e) => {
                (e.currentTarget as HTMLElement).style.display = 'none';
              }}
            />
          </div>
        </div>
      </div>
    </header>
  );
};
