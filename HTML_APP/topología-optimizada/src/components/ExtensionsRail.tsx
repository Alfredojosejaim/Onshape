// EXT-RAIL-START (reversible): barra delgada de extensiones entre el marco
// de la ventana y el arbol de operaciones / menu de herramientas. Estilo
// paleta AutoCAD: tira super angosta y alargada a todo el alto, con flecha
// para abrir/cerrar; abierta mostrara extensiones a otros programas.
// Para volver atras: borrar este archivo y quitar su uso en App.tsx.
import React, { useState } from 'react';

export const ExtensionsRail: React.FC = () => {
  const [open, setOpen] = useState(false);
  const toggle = () => setOpen((o) => !o);

  return (
    <>
      {/* Movil: una sola barra en flujo que se agranda en linea */}
      <div className="flex xl:hidden flex-row items-center gap-0.5 bg-surface-container-low rounded shadow-md border border-border-subtle/40 p-0 flex-shrink-0 min-w-0 select-none h-7 w-full">
        <button
          type="button"
          onClick={toggle}
          title={open ? 'Cerrar extensiones' : 'Abrir extensiones'}
          className="w-6 h-5 flex items-center justify-center rounded hover:bg-surface-elevated text-text-secondary hover:text-secondary transition-colors flex-shrink-0 mx-auto"
        >
          <span className="material-symbols-outlined text-[12px]">
            {open ? 'chevron_left' : 'chevron_right'}
          </span>
        </button>
        {open && (
          <div className="flex flex-row items-center gap-0.5 min-w-0 flex-1">
            <span className="px-1 text-[9px] font-mono font-semibold text-text-muted text-center">
              EXT
            </span>
            <button
              type="button"
              title="Extensiones (proximamente)"
              className="w-6 h-6 flex items-center justify-center gap-1.5 rounded hover:bg-surface-elevated text-text-muted hover:text-text-primary transition-colors px-0 py-0 mx-auto"
            >
              <span className="material-symbols-outlined text-[14px]">extension</span>
            </button>
          </div>
        )}
      </div>

      {/* Desktop: espaciador en flujo (12px + gap estándar). La drawer es
          fixed y no ocupa lugar, asi nada se desplaza al abrir/cerrar. */}
      <div
        aria-hidden="true"
        className="hidden xl:block xl:w-3 xl:-ml-1 xl:-mr-1 flex-shrink-0"
      />

      {/* Desktop: UNA sola barra drawer superpuesta sobre el arbol y el
          menu. Cerrada 12px, abierta 176px (se agranda, no abre otra).
          fixed + z-[60]: header y modales usan z-50, queda por encima.
          Largo igual al arbol: top-158px = header fijo (146px) + padding
          de la columna (12px); h-202px deja el mismo margen inferior. */}
      <div
        className={`hidden xl:flex flex-col items-stretch gap-0.5 fixed left-2 top-[158px] h-[calc(100dvh-202px)] z-[60] bg-surface-container-low rounded-md shadow-xl border border-border-subtle/40 p-0.5 overflow-hidden transition-[width] duration-200 ${
          open ? 'w-44' : 'w-3'
        }`}
      >
        {open ? (
          <>
            <div className="flex items-center justify-between px-1">
              <span className="text-[9px] font-mono font-semibold text-text-muted text-center">
                EXT
              </span>
              <button
                type="button"
                onClick={toggle}
                title="Cerrar extensiones"
                className="w-5 h-5 flex items-center justify-center rounded hover:bg-surface-elevated text-text-secondary hover:text-secondary transition-colors flex-shrink-0"
              >
                <span className="material-symbols-outlined text-[10px]">
                  chevron_left
                </span>
              </button>
            </div>
            <button
              type="button"
              title="Extensiones (proximamente)"
              className="w-auto flex items-center justify-start gap-1.5 rounded hover:bg-surface-elevated text-text-muted hover:text-text-primary transition-colors px-2 py-1"
            >
              <span className="material-symbols-outlined text-[14px]">extension</span>
              <span className="text-[10px] font-mono">Programas</span>
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={toggle}
            title="Abrir extensiones"
            className="w-full h-6 flex items-center justify-center rounded hover:bg-surface-elevated text-text-secondary hover:text-secondary transition-colors flex-shrink-0"
          >
            <span className="material-symbols-outlined text-[10px]">
              chevron_right
            </span>
          </button>
        )}
      </div>
    </>
  );
};
