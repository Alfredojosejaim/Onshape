import React, { useRef, useState, useEffect } from 'react';
import {
  Copy,
  Check,
  Download,
  AlertTriangle,
  Sparkles,
  Search,
  Code2,
  Maximize2,
  RotateCcw,
} from 'lucide-react';
import { ProjectFile, CompilationResult } from '../types';

interface CodeEditorViewProps {
  file: ProjectFile;
  onChangeContent: (newContent: string) => void;
  compilationResult: CompilationResult;
  onFormatCode?: () => void;
}

export const CodeEditorView: React.FC<CodeEditorViewProps> = ({
  file,
  onChangeContent,
  compilationResult,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);

  // Synchronize line numbers scroll with textarea scroll
  const handleScroll = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  // Support Tab key indentation inside textarea
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const value = textarea.value;

      // Insert 2 spaces
      const newValue = value.substring(0, start) + '  ' + value.substring(end);
      onChangeContent(newValue);

      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2;
      }, 0);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(file.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadFile = () => {
    const blob = new Blob([file.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = file.name;
    a.click();
    URL.revokeObjectURL(url);
  };

  const lineCount = file.content.split('\n').length;
  const linesArray = Array.from({ length: Math.max(lineCount, 1) }, (_, i) => i + 1);

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 border-r border-slate-800 overflow-hidden text-xs">
      {/* Code Editor Header */}
      <div className="h-9 px-3 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between text-slate-300">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-cyan-400" />
          <span className="font-mono font-semibold text-slate-200">{file.name}</span>
          <span className="text-[10px] text-slate-500 font-mono">
            ({lineCount} líneas)
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Status badge */}
          {compilationResult.status === 'compiling' && (
            <span className="px-2 py-0.5 rounded-full bg-amber-950 text-amber-400 border border-amber-800/40 text-[10px] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
              Compilando...
            </span>
          )}
          {compilationResult.status === 'success' && (
            <span className="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/40 text-[10px] flex items-center gap-1 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              {compilationResult.durationMs ? `${compilationResult.durationMs}ms` : 'Montado'}
            </span>
          )}
          {compilationResult.status === 'error' && (
            <span className="px-2 py-0.5 rounded-full bg-rose-950 text-rose-300 border border-rose-800/60 text-[10px] flex items-center gap-1 font-mono">
              <AlertTriangle className="w-3 h-3 text-rose-400" />
              Error {compilationResult.errorLine ? `Línea ${compilationResult.errorLine}` : ''}
            </span>
          )}

          <div className="h-4 w-px bg-slate-800 mx-1" />

          {/* Action buttons */}
          <button
            onClick={() => setShowSearch(!showSearch)}
            className={`p-1.5 rounded hover:bg-slate-800 transition ${
              showSearch ? 'text-cyan-400 bg-slate-800' : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Buscar en código"
          >
            <Search className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleCopy}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Copiar código"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={handleDownloadFile}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Descargar este archivo"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Optional In-Code Search Bar */}
      {showSearch && (
        <div className="px-3 py-1.5 bg-slate-900 border-b border-slate-800 flex items-center gap-2">
          <Search className="w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Buscar texto en el código..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 focus:outline-none text-xs"
          />
          {searchQuery && (
            <span className="text-[10px] text-slate-400">
              {file.content.toLowerCase().split(searchQuery.toLowerCase()).length - 1} coincidencias
            </span>
          )}
        </div>
      )}

      {/* Error notification banner if syntax error */}
      {compilationResult.status === 'error' && compilationResult.errorMessage && (
        <div className="p-2.5 bg-rose-950/80 border-b border-rose-800/80 text-rose-300 text-xs flex items-start gap-2 animate-in slide-in-from-top-1">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="overflow-hidden">
            <p className="font-semibold text-rose-200">
              Error de Transpilación {compilationResult.errorLine ? `(Línea ${compilationResult.errorLine})` : ''}
            </p>
            <p className="text-[11px] font-mono text-rose-300/90 truncate mt-0.5">
              {compilationResult.errorMessage}
            </p>
          </div>
        </div>
      )}

      {/* Editor Main Canvas with Line Numbers */}
      <div className="flex-1 relative flex overflow-hidden font-mono bg-slate-950">
        {/* Line Numbers Column */}
        <div
          ref={lineNumbersRef}
          className="w-12 py-3 bg-slate-950/70 border-r border-slate-900 text-slate-600 select-none text-right pr-3 overflow-hidden text-[12px] leading-5 font-mono"
        >
          {linesArray.map(lineNum => {
            const isErrorLine = compilationResult.errorLine === lineNum;
            return (
              <div
                key={lineNum}
                className={`${
                  isErrorLine
                    ? 'text-rose-400 font-bold bg-rose-950/50 -mr-3 pr-3'
                    : ''
                }`}
              >
                {lineNum}
              </div>
            );
          })}
        </div>

        {/* Textarea Code Input */}
        <textarea
          ref={textareaRef}
          value={file.content}
          onChange={e => onChangeContent(e.target.value)}
          onScroll={handleScroll}
          onKeyDown={handleKeyDown}
          spellCheck={false}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
          className="flex-1 p-3 bg-transparent text-slate-200 text-[12px] leading-5 font-mono resize-none focus:outline-none overflow-auto whitespace-pre tab-4"
          placeholder="Escribe o pega aquí tu código HTML o TSX..."
        />
      </div>

      {/* Status Bar */}
      <div className="h-6 px-3 bg-slate-900/80 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500 select-none font-mono">
        <div className="flex items-center gap-3">
          <span>{file.type.toUpperCase()}</span>
          <span>UTF-8</span>
          <span>Espacios: 2</span>
        </div>
        <div>
          <span>Edición en vivo habilitada</span>
        </div>
      </div>
    </div>
  );
};
