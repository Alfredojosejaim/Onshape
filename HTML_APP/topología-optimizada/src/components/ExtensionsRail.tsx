// EXT-RAIL-START (reversible): barra delgada de extensiones entre el marco
// de la ventana y el arbol de operaciones / menu de herramientas. Estilo
// paleta AutoCAD: tira super angosta y alargada a todo el alto, con flecha
// para abrir/cerrar; abierta mostrara extensiones a otros programas.
// Para volver atras: borrar este archivo y quitar su uso en App.tsx.
import React, { useState } from 'react';

export const ExtensionsRail: React.FC = () => {
  const [open, setOpen] = useState(false);

  return (
    // Tira super delgada (20px) y del mismo alto que la columna de
    // herramientas (hasta el borde inferior de la pantalla).
    <div
      className={`flex flex-row xl:flex-col items-center xl:items-stretch gap-0.5 bg-surface-container-low rounded-md shadow-md border border-border-subtle/40 p-px flex-shrink-0 min-w-0 select-none h-7 xl:h-auto w-full xl:w-5 xl:self-start xl:sticky xl:top-[154px] xl:h-[calc(100dvh-154px-3rem)] xl:overflow-y-auto ${
        open ? 'xl:w-44' : ''
      }`}
    >
      {/* Flecha abrir / cerrar */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        title={open ? 'Cerrar extensiones' : 'Abrir extensiones'}
        className="w-6 h-5 xl:w-[18px] xl:h-6 flex items-center justify-center rounded hover:bg-surface-elevated text-text-secondary hover:text-secondary transition-colors flex-shrink-0 mx-auto"
      >
        <span className="material-symbols-outlined text-[12px]">
          {open ? 'chevron_left' : 'chevron_right'}
        </span>
      </button>

      {/* Contenido cuando esta abierta: aqui iran extensiones a otros programas */}
      {open && (
        <div className="flex flex-row xl:flex-col items-center xl:items-stretch gap-0.5 min-w-0 flex-1">
          <span className="hidden xl:block px-1 text-[9px] font-mono font-semibold text-text-muted text-center">
            EXT
          </span>
          <button
            type="button"
            title="Extensiones (proximamente)"
            className="w-6 h-6 xl:w-auto flex items-center justify-center xl:justify-start gap-1.5 rounded hover:bg-surface-elevated text-text-muted hover:text-text-primary transition-colors px-0 xl:px-2 py-0 xl:py-1 mx-auto xl:mx-0"
          >
            <span className="material-symbols-outlined text-[14px]">extension</span>
            <span className="hidden xl:inline text-[10px] font-mono">Programas</span>
          </button>
        </div>
      )}
    </div>
  );
};
