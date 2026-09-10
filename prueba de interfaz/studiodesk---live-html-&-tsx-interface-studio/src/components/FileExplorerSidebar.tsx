import React, { useRef, useState } from 'react';
import {
  Folder,
  FileCode,
  FileText,
  Plus,
  UploadCloud,
  Trash2,
  Layers,
  Sparkles,
  ChevronRight,
  ChevronDown,
  Code,
  FilePlus2,
} from 'lucide-react';
import { ProjectFile } from '../types';
import { SAMPLE_PROJECTS } from '../data/presets';

interface FileExplorerSidebarProps {
  files: ProjectFile[];
  activeFileId: string;
  onSelectFile: (id: string) => void;
  onAddFile: (name: string, type: 'html' | 'tsx' | 'css') => void;
  onDeleteFile: (id: string) => void;
  onImportFiles: (importedFiles: { name: string; content: string }[]) => void;
  onLoadPreset: (presetId: string) => void;
  isOpen: boolean;
  onToggleOpen: () => void;
}

export const FileExplorerSidebar: React.FC<FileExplorerSidebarProps> = ({
  files,
  activeFileId,
  onSelectFile,
  onAddFile,
  onDeleteFile,
  onImportFiles,
  onLoadPreset,
  isOpen,
  onToggleOpen,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileType, setNewFileType] = useState<'tsx' | 'html' | 'css'>('tsx');
  const [showPresets, setShowPresets] = useState(true);

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const readFiles: { name: string; content: string }[] = [];
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const content = await file.text();
      readFiles.push({ name: file.name, content });
    }

    onImportFiles(readFiles);
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const readFiles: { name: string; content: string }[] = [];
      for (let i = 0; i < e.dataTransfer.files.length; i++) {
        const file = e.dataTransfer.files[i];
        const content = await file.text();
        readFiles.push({ name: file.name, content });
      }
      onImportFiles(readFiles);
    }
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFileName.trim()) return;
    let finalName = newFileName.trim();
    if (!finalName.includes('.')) {
      finalName += `.${newFileType}`;
    }
    onAddFile(finalName, newFileType);
    setNewFileName('');
    setIsCreatingFile(false);
  };

  if (!isOpen) {
    return (
      <aside className="w-12 bg-slate-900 border-r border-slate-800 flex flex-col items-center py-3 gap-4 select-none">
        <button
          onClick={onToggleOpen}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          title="Abrir Explorador de Archivos"
        >
          <Folder className="w-5 h-5 text-cyan-400" />
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          title="Importar HTML / TSX"
        >
          <UploadCloud className="w-5 h-5 text-slate-300" />
        </button>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          multiple
          accept=".html,.htm,.tsx,.jsx,.js,.ts,.css,.json"
          className="hidden"
        />
      </aside>
    );
  }

  return (
    <aside className="w-64 sm:w-72 bg-slate-900/95 border-r border-slate-800 flex flex-col select-none h-full overflow-hidden text-xs">
      {/* Header */}
      <div className="h-10 px-3 flex items-center justify-between border-b border-slate-800 text-slate-300">
        <div className="flex items-center gap-2">
          <Folder className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold tracking-wide uppercase text-[11px] text-slate-400">
            Explorador de Interfaces
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsCreatingFile(true)}
            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Nuevo archivo"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-1 rounded hover:bg-slate-800 text-cyan-400 hover:text-cyan-300 transition"
            title="Importar archivo (.html, .tsx)"
          >
            <UploadCloud className="w-4 h-4" />
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            multiple
            accept=".html,.htm,.tsx,.jsx,.js,.ts,.css,.json"
            className="hidden"
          />
        </div>
      </div>

      {/* New File Input Form */}
      {isCreatingFile && (
        <form onSubmit={handleCreateSubmit} className="p-3 bg-slate-950/80 border-b border-slate-800 space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="text"
              autoFocus
              placeholder="NombreArchivo.tsx"
              value={newFileName}
              onChange={e => setNewFileName(e.target.value)}
              className="flex-1 px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white focus:outline-none focus:border-cyan-500"
            />
            <select
              value={newFileType}
              onChange={e => setNewFileType(e.target.value as 'tsx' | 'html' | 'css')}
              className="px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-[11px] text-slate-300 focus:outline-none"
            >
              <option value="tsx">TSX</option>
              <option value="html">HTML</option>
              <option value="css">CSS</option>
            </select>
          </div>
          <div className="flex justify-end gap-1.5">
            <button
              type="button"
              onClick={() => setIsCreatingFile(false)}
              className="px-2 py-1 text-slate-400 hover:text-slate-200 rounded"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-2.5 py-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium"
            >
              Crear
            </button>
          </div>
        </form>
      )}

      {/* File List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-2 py-1 flex items-center justify-between">
          <span>Archivos Activos ({files.length})</span>
        </div>

        {files.map(file => {
          const isActive = file.id === activeFileId;
          const isTsx = file.type === 'tsx' || file.type === 'jsx';
          const isHtml = file.type === 'html';

          return (
            <div
              key={file.id}
              onClick={() => onSelectFile(file.id)}
              className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg cursor-pointer transition ${
                isActive
                  ? 'bg-slate-800 text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                {isTsx && <span className="text-[10px] font-bold px-1 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800/60">TSX</span>}
                {isHtml && <span className="text-[10px] font-bold px-1 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800/60">HTML</span>}
                {!isTsx && !isHtml && <FileText className="w-3.5 h-3.5 text-slate-400" />}

                <span className="truncate text-xs">{file.name}</span>
                {file.isModified && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />}
              </div>

              {files.length > 1 && (
                <button
                  onClick={e => {
                    e.stopPropagation();
                    if (confirm(`¿Eliminar ${file.name}?`)) onDeleteFile(file.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 transition"
                  title="Eliminar archivo"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}

        {/* Drag & Drop Zone */}
        <div
          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`mt-4 p-4 border border-dashed rounded-xl flex flex-col items-center justify-center text-center cursor-pointer transition ${
            isDragging
              ? 'border-cyan-400 bg-cyan-950/30 text-cyan-300'
              : 'border-slate-800 hover:border-slate-700 bg-slate-950/40 text-slate-400 hover:text-slate-300'
          }`}
        >
          <UploadCloud className="w-6 h-6 mb-1 text-cyan-400" />
          <p className="font-medium text-[11px] text-slate-300">Arrastra archivos HTML / TSX</p>
          <p className="text-[10px] text-slate-500 mt-0.5">o haz clic para importar</p>
        </div>

        {/* Sample Templates Library */}
        <div className="pt-4 border-t border-slate-800/80 mt-4">
          <button
            onClick={() => setShowPresets(!showPresets)}
            className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-200"
          >
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Plantillas de Ejemplo
            </span>
            {showPresets ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>

          {showPresets && (
            <div className="mt-2 space-y-1.5 px-1">
              {SAMPLE_PROJECTS.map(preset => (
                <button
                  key={preset.id}
                  onClick={() => onLoadPreset(preset.id)}
                  className="w-full text-left p-2 rounded-lg bg-slate-950/50 hover:bg-slate-800/80 border border-slate-800/60 hover:border-slate-700 transition space-y-0.5 group"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-xs text-slate-200 group-hover:text-cyan-300 transition">
                      {preset.name}
                    </span>
                    <span className="text-[9px] px-1 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                      Cargar
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 line-clamp-1">{preset.description}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-3 bg-slate-950/90 border-t border-slate-800 text-[10px] text-slate-500 flex items-center justify-between">
        <span>Montaje en vivo JS/TSX</span>
        <span className="text-cyan-500 font-mono">Autocontenido</span>
      </div>
    </aside>
  );
};
