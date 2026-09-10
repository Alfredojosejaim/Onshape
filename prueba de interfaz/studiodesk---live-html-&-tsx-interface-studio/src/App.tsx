/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import JSZip from 'jszip';
import {
  ProjectFile,
  ViewportDevice,
  ViewLayout,
  ExecutionMode,
  SelectedElementInfo,
  ConsoleLogMessage,
  CompilationResult,
} from './types';
import { SAMPLE_PROJECTS } from './data/presets';
import { compileTsxCode, prepareHtmlPreview } from './utils/compiler';
import { DesktopWindowHeader } from './components/DesktopWindowHeader';
import { FileExplorerSidebar } from './components/FileExplorerSidebar';
import { CodeEditorView } from './components/CodeEditorView';
import { LivePreviewCanvas } from './components/LivePreviewCanvas';
import { VisualInspectorDrawer } from './components/VisualInspectorDrawer';
import { ConsolePanel } from './components/ConsolePanel';
import { DesktopPackagingModal } from './components/DesktopPackagingModal';

export default function App() {
  // Workspace files initialized with the first sample project (TSX SaaS Dashboard)
  const [files, setFiles] = useState<ProjectFile[]>(() => {
    return SAMPLE_PROJECTS[0].files;
  });

  const [activeFileId, setActiveFileId] = useState<string>(() => {
    return SAMPLE_PROJECTS[0].files[0].id;
  });

  // UI layout and execution states
  const [viewLayout, setViewLayout] = useState<ViewLayout>('split');
  const [viewportDevice, setViewportDevice] = useState<ViewportDevice>('desktop');
  const [executionMode, setExecutionMode] = useState<ExecutionMode>('run');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);
  const [isPackagingModalOpen, setIsPackagingModalOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Inspector element selection
  const [selectedElement, setSelectedElement] = useState<SelectedElementInfo | null>(null);

  // Live compilation results & HTML string
  const [compilationResult, setCompilationResult] = useState<CompilationResult>({
    status: 'idle',
  });
  const [compiledPreviewHtml, setCompiledPreviewHtml] = useState<string>('');

  // Console messages buffer
  const [logs, setLogs] = useState<ConsoleLogMessage[]>([
    {
      id: 'init-1',
      type: 'info',
      content: 'StudioDesk Desktop OS inicializado correctamente en modo autocontenido.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);

  // Active file reference
  const activeFile = useMemo(() => {
    return files.find(f => f.id === activeFileId) || files[0];
  }, [files, activeFileId]);

  // Live compilation trigger (debounced for smooth typing)
  useEffect(() => {
    if (!activeFile) return;

    setCompilationResult(prev => ({ ...prev, status: 'compiling' }));

    const timer = setTimeout(() => {
      if (activeFile.type === 'tsx' || activeFile.type === 'jsx') {
        const result = compileTsxCode(activeFile.content);
        setCompilationResult(result);
        if (result.status === 'success' && result.compiledCode) {
          setCompiledPreviewHtml(result.compiledCode);
        }
      } else if (activeFile.type === 'html') {
        const prepared = prepareHtmlPreview(activeFile.content);
        setCompiledPreviewHtml(prepared);
        setCompilationResult({
          status: 'success',
          durationMs: 12,
        });
      } else {
        // Fallback for CSS or other files: find entry file to preview
        const entry = files.find(f => f.isEntry || f.type === 'tsx' || f.type === 'html');
        if (entry) {
          if (entry.type === 'tsx' || entry.type === 'jsx') {
            const res = compileTsxCode(entry.content);
            setCompilationResult(res);
            if (res.compiledCode) setCompiledPreviewHtml(res.compiledCode);
          } else {
            setCompiledPreviewHtml(prepareHtmlPreview(entry.content));
            setCompilationResult({ status: 'success' });
          }
        }
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [activeFile?.content, activeFile?.type, activeFile?.id, files]);

  // Handler for file content modifications
  const handleContentChange = useCallback((newContent: string) => {
    setFiles(prev =>
      prev.map(f => (f.id === activeFileId ? { ...f, content: newContent, isModified: true } : f))
    );
  }, [activeFileId]);

  // Import files from disk (supports .html, .htm, .tsx, .jsx, .css, etc.)
  const handleImportFiles = useCallback((imported: { name: string; content: string }[]) => {
    const newFilesList: ProjectFile[] = imported.map((item, idx) => {
      const ext = item.name.split('.').pop()?.toLowerCase() || 'tsx';
      const fileType =
        ext === 'html' || ext === 'htm'
          ? 'html'
          : ext === 'css'
          ? 'css'
          : ext === 'jsx'
          ? 'jsx'
          : ext === 'json'
          ? 'json'
          : 'tsx';

      return {
        id: `imported-${Date.now()}-${idx}`,
        name: item.name,
        type: fileType,
        content: item.content,
        isEntry: idx === 0,
      };
    });

    setFiles(prev => [...newFilesList, ...prev]);
    if (newFilesList.length > 0) {
      setActiveFileId(newFilesList[0].id);
    }

    setLogs(prev => [
      {
        id: `import-${Date.now()}`,
        type: 'info',
        content: `Importado(s) ${newFilesList.length} archivo(s): ${newFilesList.map(f => f.name).join(', ')}`,
        timestamp: new Date().toLocaleTimeString(),
      },
      ...prev,
    ]);
  }, []);

  // Add a new file
  const handleAddFile = useCallback((name: string, type: 'html' | 'tsx' | 'css') => {
    const defaultContent =
      type === 'tsx'
        ? `import React, { useState } from 'react';\n\nexport default function App() {\n  const [count, setCount] = useState(0);\n  return (\n    <div className="p-8 text-center bg-slate-950 text-white min-h-screen">\n      <h1 className="text-2xl font-bold">Nueva Interfaz</h1>\n      <button onClick={() => setCount(c => c + 1)} className="mt-4 px-4 py-2 bg-cyan-600 rounded-lg text-xs font-semibold">\n        Clics: {count}\n      </button>\n    </div>\n  );\n}\n`
        : type === 'html'
        ? `<!DOCTYPE html>\n<html lang="es">\n<head>\n  <meta charset="UTF-8">\n  <title>Nueva Interfaz</title>\n  <script src="https://cdn.tailwindcss.com"></script>\n</head>\n<body class="bg-slate-950 text-white p-8">\n  <h1 class="text-2xl font-bold">Interfaz HTML</h1>\n</body>\n</html>\n`
        : `/* Estilos personalizados */\nbody {\n  font-family: system-ui, sans-serif;\n}\n`;

    const newFile: ProjectFile = {
      id: `file-${Date.now()}`,
      name,
      type,
      content: defaultContent,
    };

    setFiles(prev => [...prev, newFile]);
    setActiveFileId(newFile.id);
  }, []);

  // Delete file
  const handleDeleteFile = useCallback((id: string) => {
    setFiles(prev => {
      const remaining = prev.filter(f => f.id !== id);
      if (activeFileId === id && remaining.length > 0) {
        setActiveFileId(remaining[0].id);
      }
      return remaining;
    });
  }, [activeFileId]);

  // Load Preset
  const handleLoadPreset = useCallback((presetId: string) => {
    const preset = SAMPLE_PROJECTS.find(p => p.id === presetId);
    if (!preset) return;

    setFiles(preset.files);
    setActiveFileId(preset.files[0].id);
    setSelectedElement(null);

    setLogs(prev => [
      {
        id: `preset-${Date.now()}`,
        type: 'info',
        content: `Cargada plantilla: "${preset.name}". Montaje en ejecución iniciado.`,
        timestamp: new Date().toLocaleTimeString(),
      },
      ...prev,
    ]);
  }, []);

  // Apply visual changes from inspector directly to code!
  const handleApplyChangesToCode = useCallback(
    (oldText: string, newText: string, oldClasses: string, newClasses: string) => {
      if (!activeFile) return;

      let updatedContent = activeFile.content;

      // Replace text if changed
      if (oldText && newText && oldText !== newText && updatedContent.includes(oldText)) {
        updatedContent = updatedContent.replace(oldText, newText);
      }

      // Replace classes if changed
      if (oldClasses !== newClasses) {
        if (oldClasses && updatedContent.includes(oldClasses)) {
          updatedContent = updatedContent.replace(oldClasses, newClasses);
        } else if (updatedContent.includes('className="') && activeFile.type === 'tsx') {
          // fallback replacement or insertion
          const firstClassMatch = updatedContent.match(/className="([^"]*)"/);
          if (firstClassMatch && firstClassMatch[1] === oldClasses) {
            updatedContent = updatedContent.replace(
              `className="${oldClasses}"`,
              `className="${newClasses}"`
            );
          }
        }
      }

      handleContentChange(updatedContent);

      setLogs(prev => [
        {
          id: `inspect-edit-${Date.now()}`,
          type: 'info',
          content: `Inspector visual: cambios sincronizados con ${activeFile.name}`,
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prev,
      ]);
    },
    [activeFile, handleContentChange]
  );

  // Incoming console logs
  const handleLogReceived = useCallback((log: { type: 'log' | 'warn' | 'error' | 'info'; content: string; timestamp: string }) => {
    setLogs(prev => [{ id: `log-${Date.now()}-${Math.random()}`, ...log }, ...prev.slice(0, 99)]);
  }, []);

  // Download entire workspace as a standalone ZIP package
  const handleDownloadProjectZip = useCallback(async () => {
    const zip = new JSZip();

    // Add all project files
    files.forEach(f => {
      zip.file(f.name, f.content);
    });

    // Add README.md
    const readmeContent = `# StudioDesk - Proyecto Autocontenido

Este proyecto fue creado y editado con StudioDesk Live Interface Studio.

## Archivos incluidos:
${files.map(f => `- ${f.name}`).join('\n')}

## Cómo ejecutar en modo escritorio:
1. **PWA**: Abre la app en Chrome/Edge y selecciona "Instalar aplicación".
2. **Electron**: Ejecuta \`npx electron .\` apuntando a \`index.html\`.
3. **Vite**: Ejecuta \`npm run dev\` para entorno web.
`;
    zip.file('README.md', readmeContent);

    // Add package.json
    const packageJsonContent = JSON.stringify(
      {
        name: 'studiodesk-app',
        version: '1.0.0',
        private: true,
        scripts: {
          start: 'vite',
          build: 'vite build',
        },
        dependencies: {
          react: '^18.3.1',
          'react-dom': '^18.3.1',
        },
      },
      null,
      2
    );
    zip.file('package.json', packageJsonContent);

    const blob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'StudioDesk_Proyecto_Autocontenido.zip';
    a.click();
    URL.revokeObjectURL(url);
  }, [files]);

  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Desktop Window Frame Header & Menu Bar */}
      <DesktopWindowHeader
        currentFileName={activeFile ? activeFile.name : 'Sin Archivo'}
        viewLayout={viewLayout}
        setViewLayout={setViewLayout}
        viewportDevice={viewportDevice}
        setViewportDevice={setViewportDevice}
        executionMode={executionMode}
        setExecutionMode={setExecutionMode}
        onRefreshPreview={() => {
          if (activeFile) {
            handleContentChange(activeFile.content + ' ');
            setTimeout(() => handleContentChange(activeFile.content), 50);
          }
        }}
        onImportClick={() => {
          const input = document.createElement('input');
          input.type = 'file';
          input.multiple = true;
          input.accept = '.html,.htm,.tsx,.jsx,.js,.ts,.css,.json';
          input.onchange = async (e: any) => {
            const fileList = e.target.files;
            if (!fileList) return;
            const readFiles: { name: string; content: string }[] = [];
            for (let i = 0; i < fileList.length; i++) {
              readFiles.push({
                name: fileList[i].name,
                content: await fileList[i].text(),
              });
            }
            handleImportFiles(readFiles);
          };
          input.click();
        }}
        onNewFileClick={() => handleAddFile(`Componente_${Date.now().toString().slice(-4)}.tsx`, 'tsx')}
        onExportZipClick={handleDownloadProjectZip}
        onOpenPackagingModal={() => setIsPackagingModalOpen(true)}
        onToggleConsole={() => setIsConsoleOpen(prev => !prev)}
        isConsoleOpen={isConsoleOpen}
        compilationStatus={compilationResult.status}
        isFullscreen={isFullscreen}
        onToggleFullscreen={toggleFullscreen}
      />

      {/* Main Studio Body */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* File Explorer Sidebar */}
        <FileExplorerSidebar
          files={files}
          activeFileId={activeFileId}
          onSelectFile={setActiveFileId}
          onAddFile={handleAddFile}
          onDeleteFile={handleDeleteFile}
          onImportFiles={handleImportFiles}
          onLoadPreset={handleLoadPreset}
          isOpen={isSidebarOpen}
          onToggleOpen={() => setIsSidebarOpen(prev => !prev)}
        />

        {/* Center Workspace */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 flex overflow-hidden">
            {/* Code Editor Panel */}
            {(viewLayout === 'split' || viewLayout === 'editor-only') && activeFile && (
              <div
                className={`h-full flex flex-col overflow-hidden ${
                  viewLayout === 'split' ? 'w-1/2 min-w-[340px]' : 'w-full'
                }`}
              >
                <CodeEditorView
                  file={activeFile}
                  onChangeContent={handleContentChange}
                  compilationResult={compilationResult}
                />
              </div>
            )}

            {/* Live Mounted Execution Preview Canvas */}
            {(viewLayout === 'split' || viewLayout === 'live-only') && (
              <div
                className={`h-full flex flex-col overflow-hidden ${
                  viewLayout === 'split' ? 'flex-1' : 'w-full'
                }`}
              >
                <LivePreviewCanvas
                  compiledHtml={compiledPreviewHtml}
                  viewportDevice={viewportDevice}
                  executionMode={executionMode}
                  onSelectElement={setSelectedElement}
                  onLogReceived={handleLogReceived}
                  onRefresh={() => {
                    if (activeFile) {
                      handleContentChange(activeFile.content + ' ');
                      setTimeout(() => handleContentChange(activeFile.content), 50);
                    }
                  }}
                />
              </div>
            )}

            {/* Visual Inspector Drawer (Opens when an element is clicked in inspect mode) */}
            {selectedElement && (
              <VisualInspectorDrawer
                selectedElement={selectedElement}
                onClose={() => setSelectedElement(null)}
                onApplyChangesToCode={handleApplyChangesToCode}
              />
            )}
          </div>

          {/* Collapsible Console Logger Panel */}
          <ConsolePanel
            logs={logs}
            onClearLogs={() => setLogs([])}
            isOpen={isConsoleOpen}
            onClose={() => setIsConsoleOpen(false)}
          />
        </div>
      </div>

      {/* Desktop Packaging & Standalone Modal */}
      <DesktopPackagingModal
        isOpen={isPackagingModalOpen}
        onClose={() => setIsPackagingModalOpen(false)}
        files={files}
        onDownloadProjectZip={handleDownloadProjectZip}
      />
    </div>
  );
}
