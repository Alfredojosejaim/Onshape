import React, { useState } from 'react';
import {
  Monitor,
  Smartphone,
  Tablet,
  Laptop,
  Maximize2,
  Minimize2,
  FolderOpen,
  FileCode,
  Play,
  RotateCcw,
  Sparkles,
  Download,
  Box,
  Layers,
  Search,
  CheckCircle2,
  ExternalLink,
  Split,
  Eye,
  Code2,
} from 'lucide-react';
import { ViewportDevice, ViewLayout, ExecutionMode } from '../types';
import { usePWAInstall } from '../hooks/usePWAInstall';

interface DesktopWindowHeaderProps {
  currentFileName: string;
  viewLayout: ViewLayout;
  setViewLayout: (layout: ViewLayout) => void;
  viewportDevice: ViewportDevice;
  setViewportDevice: (device: ViewportDevice) => void;
  executionMode: ExecutionMode;
  setExecutionMode: (mode: ExecutionMode) => void;
  onRefreshPreview: () => void;
  onImportClick: () => void;
  onNewFileClick: () => void;
  onExportZipClick: () => void;
  onOpenPackagingModal: () => void;
  onToggleConsole: () => void;
  isConsoleOpen: boolean;
  compilationStatus: 'idle' | 'compiling' | 'success' | 'error';
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
}

export const DesktopWindowHeader: React.FC<DesktopWindowHeaderProps> = ({
  currentFileName,
  viewLayout,
  setViewLayout,
  viewportDevice,
  setViewportDevice,
  executionMode,
  setExecutionMode,
  onRefreshPreview,
  onImportClick,
  onNewFileClick,
  onExportZipClick,
  onOpenPackagingModal,
  onToggleConsole,
  isConsoleOpen,
  compilationStatus,
  isFullscreen,
  onToggleFullscreen,
}) => {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [activeMenu, setActiveMenu] = useState<string | null>(null);

  const toggleMenu = (name: string) => {
    setActiveMenu(prev => (prev === name ? null : name));
  };

  const closeMenu = () => setActiveMenu(null);

  return (
    <header className="bg-slate-900/95 border-b border-slate-800 backdrop-blur-md select-none sticky top-0 z-30 flex flex-col">
      {/* Top Title Bar with Native Window Controls */}
      <div className="h-10 px-3 flex items-center justify-between border-b border-slate-800/80">
        {/* Left: Window Traffic Lights & App Title */}
        <div className="flex items-center gap-3">
          {/* Traffic Lights simulation */}
          <div className="flex items-center gap-1.5 pr-2">
            <button
              onClick={() => alert('Para cerrar StudioDesk en modo autocontenido, usa el atajo de tu sistema (Alt+F4 o Cmd+W).')}
              title="Cerrar ventana"
              className="w-3 h-3 rounded-full bg-red-500/80 hover:bg-red-600 transition-colors flex items-center justify-center text-[8px] text-red-950 font-bold opacity-80 hover:opacity-100"
            />
            <button
              onClick={() => alert('Minimizar ventana autocontenida')}
              title="Minimizar"
              className="w-3 h-3 rounded-full bg-amber-500/80 hover:bg-amber-600 transition-colors opacity-80 hover:opacity-100"
            />
            <button
              onClick={onToggleFullscreen}
              title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa / Maximizar'}
              className="w-3 h-3 rounded-full bg-emerald-500/80 hover:bg-emerald-600 transition-colors opacity-80 hover:opacity-100"
            />
          </div>

          {/* App Brand */}
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-md bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-sm font-bold text-[10px]">
              SD
            </div>
            <span className="text-xs font-semibold tracking-tight text-slate-200">
              StudioDesk
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 font-mono border border-slate-700">
              Autocontenido
            </span>
          </div>

          {/* Current File indicator */}
          <div className="hidden sm:flex items-center gap-1.5 pl-3 border-l border-slate-800 text-xs text-slate-400">
            <FileCode className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-200 font-medium">{currentFileName}</span>
            {compilationStatus === 'compiling' && (
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            )}
            {compilationStatus === 'success' && (
              <span className="text-[10px] text-emerald-400 font-mono">● En Ejecución</span>
            )}
            {compilationStatus === 'error' && (
              <span className="text-[10px] text-rose-400 font-mono">● Error de Sintaxis</span>
            )}
          </div>
        </div>

        {/* Right: Install Desktop App / Standalone Indicator */}
        <div className="flex items-center gap-2">
          {isInstalled ? (
            <div className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 text-[11px] font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>App Nativa Activa</span>
            </div>
          ) : isInstallable ? (
            <button
              onClick={install}
              className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-cyan-600 hover:bg-cyan-500 text-white text-[11px] font-semibold transition shadow-sm hover:shadow cursor-pointer"
              title="Instalar StudioDesk como aplicación nativa de escritorio independiente"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Instalar en Escritorio</span>
            </button>
          ) : (
            <button
              onClick={onOpenPackagingModal}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-cyan-300 text-[11px] font-medium border border-slate-700 transition"
              title="Ver opciones para empaquetar en Electron, Tauri o PWA"
            >
              <Box className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Framework Autocontenido</span>
            </button>
          )}

          <button
            onClick={onToggleFullscreen}
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Main Desktop Menu & Action Toolbar */}
      <div className="h-11 px-3 flex items-center justify-between gap-2 overflow-x-auto text-xs">
        {/* Left: Desktop Menu Bar */}
        <div className="flex items-center gap-1">
          {/* Archivo Menu */}
          <div className="relative">
            <button
              onClick={() => toggleMenu('file')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                activeMenu === 'file' ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/60'
              }`}
            >
              Archivo
            </button>
            {activeMenu === 'file' && (
              <div
                className="absolute left-0 mt-1 w-56 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl py-1.5 z-50 text-xs animate-in fade-in zoom-in-95"
                onMouseLeave={closeMenu}
              >
                <button
                  onClick={() => { onNewFileClick(); closeMenu(); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-slate-800 text-slate-200 flex items-center justify-between"
                >
                  <span>Nuevo Archivo (TSX/HTML)</span>
                  <span className="text-[10px] text-slate-500 font-mono">+N</span>
                </button>
                <button
                  onClick={() => { onImportClick(); closeMenu(); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-slate-800 text-cyan-400 flex items-center justify-between font-medium"
                >
                  <span>Importar Archivo Local...</span>
                  <span className="text-[10px] text-slate-500 font-mono">.html .tsx</span>
                </button>
                <div className="my-1 border-t border-slate-800" />
                <button
                  onClick={() => { onExportZipClick(); closeMenu(); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-slate-800 text-slate-200 flex items-center justify-between"
                >
                  <span>Exportar Proyecto (ZIP)</span>
                  <Download className="w-3.5 h-3.5 text-slate-400" />
                </button>
                <button
                  onClick={() => { onOpenPackagingModal(); closeMenu(); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-slate-800 text-slate-200 flex items-center justify-between"
                >
                  <span>Empaquetar Desktop (Electron/Tauri)</span>
                  <Box className="w-3.5 h-3.5 text-cyan-400" />
                </button>
              </div>
            )}
          </div>

          {/* Vista Menu */}
          <div className="relative">
            <button
              onClick={() => toggleMenu('view')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                activeMenu === 'view' ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/60'
              }`}
            >
              Vista
            </button>
            {activeMenu === 'view' && (
              <div
                className="absolute left-0 mt-1 w-52 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl py-1.5 z-50 text-xs"
                onMouseLeave={closeMenu}
              >
                <button
                  onClick={() => { setViewLayout('split'); closeMenu(); }}
                  className={`w-full text-left px-3 py-1.5 hover:bg-slate-800 flex items-center justify-between ${
                    viewLayout === 'split' ? 'text-cyan-400 font-bold' : 'text-slate-200'
                  }`}
                >
                  <span>Vista Dividida</span>
                  <Split className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => { setViewLayout('live-only'); closeMenu(); }}
                  className={`w-full text-left px-3 py-1.5 hover:bg-slate-800 flex items-center justify-between ${
                    viewLayout === 'live-only' ? 'text-cyan-400 font-bold' : 'text-slate-200'
                  }`}
                >
                  <span>Solo En Vivo (App Full)</span>
                  <Eye className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => { setViewLayout('editor-only'); closeMenu(); }}
                  className={`w-full text-left px-3 py-1.5 hover:bg-slate-800 flex items-center justify-between ${
                    viewLayout === 'editor-only' ? 'text-cyan-400 font-bold' : 'text-slate-200'
                  }`}
                >
                  <span>Solo Editor de Código</span>
                  <Code2 className="w-3.5 h-3.5" />
                </button>
                <div className="my-1 border-t border-slate-800" />
                <button
                  onClick={() => { onToggleConsole(); closeMenu(); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-slate-800 text-slate-200 flex items-center justify-between"
                >
                  <span>{isConsoleOpen ? 'Ocultar Consola' : 'Mostrar Consola Runtime'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Layout Quick Toggles */}
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800 ml-2">
            <button
              onClick={() => setViewLayout('split')}
              className={`px-2 py-1 rounded text-xs flex items-center gap-1 font-medium transition ${
                viewLayout === 'split' ? 'bg-slate-800 text-cyan-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Vista Dividida (Código + App en Vivo)"
            >
              <Split className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Dividido</span>
            </button>
            <button
              onClick={() => setViewLayout('live-only')}
              className={`px-2 py-1 rounded text-xs flex items-center gap-1 font-medium transition ${
                viewLayout === 'live-only' ? 'bg-slate-800 text-cyan-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Solo Frontend en Ejecución"
            >
              <Eye className="w-3.5 h-3.5" />
              <span className="hidden md:inline">En Vivo</span>
            </button>
            <button
              onClick={() => setViewLayout('editor-only')}
              className={`px-2 py-1 rounded text-xs flex items-center gap-1 font-medium transition ${
                viewLayout === 'editor-only' ? 'bg-slate-800 text-cyan-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Solo Editor de Código"
            >
              <Code2 className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Editor</span>
            </button>
          </div>
        </div>

        {/* Center: Interactive Mode Switcher (Run vs Inspect) */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800">
            <button
              onClick={() => setExecutionMode('run')}
              className={`px-3 py-1 rounded text-xs flex items-center gap-1.5 font-medium transition ${
                executionMode === 'run'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-600/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Modo Interactivo: Usa la app como si estuviera en ejecución real (botones, estados, formularios)"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Ejecución</span>
            </button>
            <button
              onClick={() => setExecutionMode('inspect')}
              className={`px-3 py-1 rounded text-xs flex items-center gap-1.5 font-medium transition ${
                executionMode === 'inspect'
                  ? 'bg-blue-950 text-blue-400 border border-blue-600/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Modo Inspección: Haz clic sobre cualquier elemento visual para editar su texto y clases Tailwind"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Inspeccionar</span>
            </button>
          </div>

          <button
            onClick={onRefreshPreview}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition"
            title="Recargar montaje del frontend"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Right: Device Viewport selector */}
        <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800">
          <button
            onClick={() => setViewportDevice('desktop')}
            className={`p-1.5 rounded text-xs transition ${
              viewportDevice === 'desktop' ? 'bg-slate-800 text-cyan-400' : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Desktop (1920x1080)"
          >
            <Monitor className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewportDevice('laptop')}
            className={`p-1.5 rounded text-xs transition ${
              viewportDevice === 'laptop' ? 'bg-slate-800 text-cyan-400' : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Laptop (1366x768)"
          >
            <Laptop className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewportDevice('tablet')}
            className={`p-1.5 rounded text-xs transition ${
              viewportDevice === 'tablet' ? 'bg-slate-800 text-cyan-400' : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Tablet (768x1024)"
          >
            <Tablet className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewportDevice('mobile')}
            className={`p-1.5 rounded text-xs transition ${
              viewportDevice === 'mobile' ? 'bg-slate-800 text-cyan-400' : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Móvil (390x844)"
          >
            <Smartphone className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
};
