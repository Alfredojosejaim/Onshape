// BLACKSCREEN-FIX (reversible: quitar archivo + usos en main.tsx/App.tsx).
// Sin error boundary, cualquier excepcion en render/efectos/lazy desmonta
// el root de React y la ventana queda en negro silencioso (fondo #10131c).
// Este boundary lo convierte en un mensaje visible con reintento.
import * as React from 'react';

interface Props {
  label: string;
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error(`[error-boundary:${this.props.label}]`, error, info.componentStack);
  }

  render(): React.ReactNode {
    if (this.state.error) {
      const stack = typeof this.state.error.stack === 'string' ? this.state.error.stack : '';
      // STACK-SHOW: primera linea del stack (suele traer el componente y la
      // posicion minificada) para diagnosticar sin DevTools en pywebview.
      const stackHead = stack.split('\n').slice(0, 4).join('\n');
      return (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 rounded-lg bg-surface-container-lowest min-h-[300px] p-6 text-center">
          <span className="material-symbols-outlined text-[36px] text-fea-stress-critical">error</span>
          <p className="text-[13px] font-semibold text-text-primary">
            Falló {this.props.label}
          </p>
          <p className="text-[11px] font-mono text-text-muted max-w-md break-all">
            {String(this.state.error.message || this.state.error)}
          </p>
          {stackHead && (
            <pre className="text-[10px] font-mono text-text-muted max-w-lg break-all whitespace-pre-wrap text-left bg-surface-container-low rounded p-2 max-h-40 overflow-auto">
              {stackHead}
            </pre>
          )}
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="px-4 py-1.5 rounded-lg bg-primary-container hover:bg-secondary text-on-primary text-[12px] font-semibold"
          >
            Reintentar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
