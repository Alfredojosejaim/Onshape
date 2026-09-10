import React, { useState, useEffect } from 'react';
import {
  X,
  Type,
  Palette,
  Sparkles,
  Check,
  Code,
  Layers,
  Sliders,
  CornerDownLeft,
} from 'lucide-react';
import { SelectedElementInfo } from '../types';

interface VisualInspectorDrawerProps {
  selectedElement: SelectedElementInfo | null;
  onClose: () => void;
  onApplyChangesToCode: (oldText: string, newText: string, oldClasses: string, newClasses: string) => void;
}

const QUICK_TAILWIND_CLASSES = [
  'bg-blue-600',
  'bg-emerald-600',
  'bg-slate-900',
  'text-white',
  'text-cyan-400',
  'text-emerald-400',
  'rounded-xl',
  'rounded-full',
  'p-4',
  'px-4 py-2',
  'font-bold',
  'shadow-lg',
  'border border-slate-800',
];

export const VisualInspectorDrawer: React.FC<VisualInspectorDrawerProps> = ({
  selectedElement,
  onClose,
  onApplyChangesToCode,
}) => {
  const [editText, setEditText] = useState('');
  const [editClasses, setEditClasses] = useState('');
  const [applied, setApplied] = useState(false);

  useEffect(() => {
    if (selectedElement) {
      setEditText(selectedElement.text || '');
      setEditClasses(selectedElement.className || '');
      setApplied(false);
    }
  }, [selectedElement]);

  if (!selectedElement) return null;

  const handleApply = () => {
    onApplyChangesToCode(
      selectedElement.text,
      editText,
      selectedElement.className,
      editClasses
    );
    setApplied(true);
    setTimeout(() => setApplied(false), 2000);
  };

  const handleToggleClass = (cls: string) => {
    const currentList = editClasses.split(/\s+/).filter(Boolean);
    if (currentList.includes(cls)) {
      setEditClasses(currentList.filter(c => c !== cls).join(' '));
    } else {
      setEditClasses([...currentList, cls].join(' '));
    }
  };

  return (
    <div className="w-80 sm:w-88 bg-slate-900/98 border-l border-slate-800 flex flex-col h-full z-20 shadow-2xl text-xs select-none">
      {/* Header */}
      <div className="h-10 px-3 flex items-center justify-between border-b border-slate-800 text-slate-300">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-slate-200">Inspector Visual</span>
          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/40">
            &lt;{selectedElement.tagName}&gt;
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition"
          title="Cerrar inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Selector & Dimensions */}
        <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider block">
            Selector DOM
          </span>
          <p className="font-mono text-xs text-cyan-400 truncate">
            {selectedElement.selector || selectedElement.tagName}
          </p>
          {selectedElement.boundingRect && (
            <p className="text-[10px] text-slate-500 font-mono">
              Dimensiones: {Math.round(selectedElement.boundingRect.width)} × {Math.round(selectedElement.boundingRect.height)} px
            </p>
          )}
        </div>

        {/* Text Content Editor */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 font-medium text-slate-300 text-xs">
            <Type className="w-3.5 h-3.5 text-cyan-400" />
            <span>Texto del Elemento</span>
          </label>
          <textarea
            value={editText}
            onChange={e => setEditText(e.target.value)}
            rows={2}
            className="w-full p-2.5 bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl text-slate-200 text-xs focus:outline-none resize-none"
            placeholder="Texto del elemento..."
          />
        </div>

        {/* Class List & Tailwind Editor */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 font-medium text-slate-300 text-xs">
            <Palette className="w-3.5 h-3.5 text-cyan-400" />
            <span>Clases Tailwind CSS</span>
          </label>
          <textarea
            value={editClasses}
            onChange={e => setEditClasses(e.target.value)}
            rows={3}
            className="w-full p-2.5 bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl text-slate-200 font-mono text-[11px] focus:outline-none resize-none leading-relaxed"
            placeholder="px-4 py-2 bg-blue-600 rounded text-white..."
          />

          {/* Quick Utility Class Pills */}
          <div className="space-y-1 pt-1">
            <span className="text-[10px] text-slate-500 block">Atajos de Estilo:</span>
            <div className="flex flex-wrap gap-1">
              {QUICK_TAILWIND_CLASSES.map(cls => {
                const isPresent = editClasses.includes(cls);
                return (
                  <button
                    key={cls}
                    type="button"
                    onClick={() => handleToggleClass(cls)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono transition ${
                      isPresent
                        ? 'bg-cyan-600 text-white font-semibold'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    }`}
                  >
                    {cls}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Action */}
      <div className="p-3 bg-slate-950 border-t border-slate-800 space-y-2">
        <button
          onClick={handleApply}
          className="w-full py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold rounded-xl text-xs flex items-center justify-center gap-2 transition shadow-md shadow-cyan-600/20 active:scale-98"
        >
          {applied ? <Check className="w-4 h-4 text-white" /> : <Sparkles className="w-4 h-4" />}
          <span>{applied ? '¡Cambios Sincronizados!' : 'Aplicar al Código Fuente'}</span>
        </button>
        <p className="text-[10px] text-slate-500 text-center">
          Actualiza el texto y clases en el archivo activo
        </p>
      </div>
    </div>
  );
};
