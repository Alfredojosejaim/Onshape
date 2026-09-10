import React, { useState } from 'react';
import {
  X,
  Box,
  Download,
  CheckCircle2,
  Terminal,
  Layers,
  Copy,
  Check,
  ExternalLink,
  Laptop,
} from 'lucide-react';
import { usePWAInstall } from '../hooks/usePWAInstall';
import { ProjectFile } from '../types';

interface DesktopPackagingModalProps {
  isOpen: boolean;
  onClose: () => void;
  files: ProjectFile[];
  onDownloadProjectZip: () => void;
}

export const DesktopPackagingModal: React.FC<DesktopPackagingModalProps> = ({
  isOpen,
  onClose,
  files,
  onDownloadProjectZip,
}) => {
  const { isInstallable, isInstalled, install } = usePWAInstall();
  const [activeTab, setActiveTab] = useState<'pwa' | 'electron' | 'tauri'>('pwa');
  const [copied, setCopied] = useState<string | null>(null);

  if (!isOpen) return null;

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const electronCode = `// main.js (Electron Desktop Entry)
const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'StudioDesk - Autocontenido',
    backgroundColor: '#0f172a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  // Carga la app localmente o la build de producción
  win.loadFile(path.join(__dirname, 'dist', 'index.html'));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
`;

  const electronPackageJson = `{
  "name": "studiodesk-desktop",
  "version": "1.0.0",
  "main": "main.js",
  "scripts": {
    "desktop": "electron .",
    "dist": "electron-builder --win --mac --linux"
  },
  "devDependencies": {
    "electron": "^33.0.0",
    "electron-builder": "^25.0.0"
  }
}`;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-xs">
        {/* Header */}
        <div className="h-12 px-5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-lg bg-cyan-600 flex items-center justify-center text-white">
              <Box className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight">
                Frameworks Autocontenidos de Escritorio
              </h2>
              <p className="text-[11px] text-slate-400">
                Ejecuta StudioDesk fuera del navegador como una app nativa
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-950/60 px-5 pt-2 gap-2">
          <button
            onClick={() => setActiveTab('pwa')}
            className={`pb-2.5 px-3 font-semibold border-b-2 transition ${
              activeTab === 'pwa'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            1. App Nativa PWA (Recomendada)
          </button>
          <button
            onClick={() => setActiveTab('electron')}
            className={`pb-2.5 px-3 font-semibold border-b-2 transition ${
              activeTab === 'electron'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            2. Wrapper Electron (.exe/.dmg)
          </button>
          <button
            onClick={() => setActiveTab('tauri')}
            className={`pb-2.5 px-3 font-semibold border-b-2 transition ${
              activeTab === 'tauri'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            3. Wrapper Tauri (Rust Ultra-ligero)
          </button>
        </div>

        {/* Tab Contents */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {activeTab === 'pwa' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white text-sm">
                    Instalación Standalone de 1 Clic
                  </span>
                  {isInstalled ? (
                    <span className="px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-500/30 text-[11px] font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      App Ya Instalada
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 text-[10px] font-mono">
                      Cero Dependencias Externas
                    </span>
                  )}
                </div>
                <p className="text-slate-300 leading-relaxed text-xs">
                  StudioDesk incluye el framework <strong>PWA Standalone</strong> preconfigurado con manifiesto nativo y Service Worker. Al instalarla, se ejecuta en una ventana propia de Windows/macOS/Linux, con su propio icono en el dock o barra de tareas, sin barra de URL ni pestañas de navegador.
                </p>

                <div className="pt-2 flex flex-wrap gap-2">
                  {isInstallable && (
                    <button
                      onClick={install}
                      className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold rounded-xl flex items-center gap-2 shadow-lg shadow-cyan-500/20 active:scale-98 transition cursor-pointer"
                    >
                      <Download className="w-4 h-4" />
                      <span>Instalar StudioDesk Ahora en Escritorio</span>
                    </button>
                  )}

                  <button
                    onClick={onDownloadProjectZip}
                    className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl flex items-center gap-2 transition"
                  >
                    <Download className="w-4 h-4" />
                    <span>Descargar Todo el Proyecto (ZIP)</span>
                  </button>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                <span className="font-semibold text-slate-300 text-xs">¿Cómo instalar en Chrome o Edge manualmente?</span>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Haz clic en el icono de instalación en la barra superior (o menú del navegador &gt; &quot;Instalar StudioDesk&quot;) para que se convierta en una aplicación de escritorio independiente.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'electron' && (
            <div className="space-y-3">
              <p className="text-slate-300 text-xs">
                Puedes empaquetar este entorno en un ejecutable nativo (.exe para Windows o .dmg para Mac) usando Electron:
              </p>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-slate-400 text-[11px]">main.js</span>
                  <button
                    onClick={() => copyToClipboard(electronCode, 'main')}
                    className="flex items-center gap-1 text-cyan-400 hover:underline text-[11px]"
                  >
                    {copied === 'main' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copied === 'main' ? 'Copiado' : 'Copiar'}</span>
                  </button>
                </div>
                <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto">
                  {electronCode}
                </pre>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-slate-400 text-[11px]">package.json para Electron</span>
                  <button
                    onClick={() => copyToClipboard(electronPackageJson, 'pkg')}
                    className="flex items-center gap-1 text-cyan-400 hover:underline text-[11px]"
                  >
                    {copied === 'pkg' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copied === 'pkg' ? 'Copiado' : 'Copiar'}</span>
                  </button>
                </div>
                <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto">
                  {electronPackageJson}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'tauri' && (
            <div className="space-y-3 text-xs">
              <p className="text-slate-300">
                Para el menor consumo de memoria RAM (&lt; 30MB) y rendimiento máximo en C++/Rust nativo, puedes usar Tauri:
              </p>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <span className="font-semibold text-white">Comandos para compilar en Tauri:</span>
                <pre className="p-2.5 rounded-lg bg-slate-900 font-mono text-cyan-300 text-[11px]">
                  {`npm install -D @tauri-apps/cli\nnpx tauri init\nnpx tauri build`}
                </pre>
                <p className="text-slate-400 text-[11px]">
                  Generará un binario nativo independiente con soporte total de sistema de archivos.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
