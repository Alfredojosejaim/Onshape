import React, { useState } from 'react';
import {
  Terminal,
  Trash2,
  AlertCircle,
  AlertTriangle,
  Info,
  ChevronDown,
  X,
} from 'lucide-react';
import { ConsoleLogMessage } from '../types';

interface ConsolePanelProps {
  logs: ConsoleLogMessage[];
  onClearLogs: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export const ConsolePanel: React.FC<ConsolePanelProps> = ({
  logs,
  onClearLogs,
  isOpen,
  onClose,
}) => {
  const [filter, setFilter] = useState<'all' | 'log' | 'warn' | 'error'>('all');

  if (!isOpen) return null;

  const filteredLogs = logs.filter(log => {
    if (filter === 'all') return true;
    return log.type === filter;
  });

  const errorCount = logs.filter(l => l.type === 'error').length;
  const warnCount = logs.filter(l => l.type === 'warn').length;

  return (
    <div className="h-48 sm:h-56 bg-slate-950 border-t border-slate-800 flex flex-col z-20 text-xs font-mono select-none">
      {/* Console Header */}
      <div className="h-8 px-3 bg-slate-900 flex items-center justify-between border-b border-slate-800 text-slate-300">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-semibold text-slate-200">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>Consola de Ejecución ({logs.length})</span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setFilter('all')}
              className={`px-2 py-0.5 rounded text-[10px] transition ${
                filter === 'all' ? 'bg-slate-800 text-cyan-400' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Todos
            </button>
            <button
              onClick={() => setFilter('error')}
              className={`px-2 py-0.5 rounded text-[10px] flex items-center gap-1 transition ${
                filter === 'error' ? 'bg-rose-950 text-rose-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertCircle className="w-2.5 h-2.5 text-rose-400" />
              <span>{errorCount}</span>
            </button>
            <button
              onClick={() => setFilter('warn')}
              className={`px-2 py-0.5 rounded text-[10px] flex items-center gap-1 transition ${
                filter === 'warn' ? 'bg-amber-950 text-amber-300' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertTriangle className="w-2.5 h-2.5 text-amber-400" />
              <span>{warnCount}</span>
            </button>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={onClearLogs}
            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Limpiar consola"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Cerrar consola"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Logs List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-[11px]">
        {filteredLogs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600">
            <span>No hay registros en la consola. La interfaz se está ejecutando limpiamente.</span>
          </div>
        ) : (
          filteredLogs.map(log => (
            <div
              key={log.id}
              className={`px-2 py-1 rounded flex items-start gap-2 ${
                log.type === 'error'
                  ? 'bg-rose-950/40 text-rose-300 border-l-2 border-rose-500'
                  : log.type === 'warn'
                  ? 'bg-amber-950/40 text-amber-300 border-l-2 border-amber-500'
                  : 'text-slate-300 hover:bg-slate-900/60'
              }`}
            >
              <span className="text-slate-500 text-[10px] shrink-0">{log.timestamp}</span>
              <span className="break-all whitespace-pre-wrap flex-1">{log.content}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
