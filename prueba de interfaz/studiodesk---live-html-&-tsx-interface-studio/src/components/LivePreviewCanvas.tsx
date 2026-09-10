import React, { useRef, useEffect, useState } from 'react';
import {
  RotateCcw,
  ZoomIn,
  ZoomOut,
  Maximize,
  Sparkles,
  Search,
  Play,
  Monitor,
  Smartphone,
  Tablet,
  Laptop,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { ViewportDevice, ExecutionMode, SelectedElementInfo } from '../types';

interface LivePreviewCanvasProps {
  compiledHtml: string;
  viewportDevice: ViewportDevice;
  executionMode: ExecutionMode;
  onSelectElement: (element: SelectedElementInfo) => void;
  onLogReceived: (log: { type: 'log' | 'warn' | 'error' | 'info'; content: string; timestamp: string }) => void;
  onRefresh: () => void;
}

export const LivePreviewCanvas: React.FC<LivePreviewCanvasProps> = ({
  compiledHtml,
  viewportDevice,
  executionMode,
  onSelectElement,
  onLogReceived,
  onRefresh,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [isLoaded, setIsLoaded] = useState(false);

  // Send execution mode change to iframe
  useEffect(() => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        {
          type: 'SET_INSPECT_MODE',
          enabled: executionMode === 'inspect',
        },
        '*'
      );
    }
  }, [executionMode]);

  // Listen to messages from the preview iframe
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (!e.data) return;

      if (e.data.type === 'ELEMENT_SELECTED') {
        onSelectElement(e.data.element);
      } else if (e.data.type === 'STUDIODESK_LOG') {
        onLogReceived(e.data.log);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onSelectElement, onLogReceived]);

  // When compiledHtml changes, write into iframe
  useEffect(() => {
    if (!iframeRef.current) return;
    const iframe = iframeRef.current;

    // Use srcdoc for clean isolated sandboxed rendering
    iframe.srcdoc = compiledHtml;
    setIsLoaded(true);

    const handleLoad = () => {
      // Re-send current inspection mode after reload
      if (iframe.contentWindow) {
        iframe.contentWindow.postMessage(
          {
            type: 'SET_INSPECT_MODE',
            enabled: executionMode === 'inspect',
          },
          '*'
        );
      }
    };

    iframe.addEventListener('load', handleLoad);
    return () => iframe.removeEventListener('load', handleLoad);
  }, [compiledHtml]);

  // Determine viewport width & height
  const getDeviceDimensions = () => {
    switch (viewportDevice) {
      case 'mobile':
        return { width: '390px', height: '844px', label: 'iPhone 15 (390 x 844)' };
      case 'tablet':
        return { width: '768px', height: '1024px', label: 'iPad Pro (768 x 1024)' };
      case 'laptop':
        return { width: '1280px', height: '800px', label: 'MacBook (1280 x 800)' };
      case 'desktop':
      default:
        return { width: '100%', height: '100%', label: 'Desktop (100% Fluido)' };
    }
  };

  const device = getDeviceDimensions();
  const isConstrained = viewportDevice !== 'desktop';

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-hidden relative select-none">
      {/* Canvas Top Bar */}
      <div className="h-9 px-3 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between text-xs text-slate-300">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
            {device.label}
          </div>

          {executionMode === 'run' ? (
            <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
              <Play className="w-3 h-3 fill-current" />
              Modo Ejecución Activo
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] text-cyan-400 font-medium animate-pulse">
              <Search className="w-3 h-3" />
              Haz clic en cualquier elemento para editarlo
            </span>
          )}
        </div>

        {/* Zoom and Preview Controls */}
        <div className="flex items-center gap-1.5">
          <div className="flex items-center bg-slate-950 rounded border border-slate-800 px-1">
            <button
              onClick={() => setZoomLevel(prev => Math.max(0.4, prev - 0.1))}
              className="p-1 text-slate-400 hover:text-slate-200 transition"
              title="Alejar"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-1.5 font-mono text-[10px] text-slate-400">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              onClick={() => setZoomLevel(prev => Math.min(1.5, prev + 0.1))}
              className="p-1 text-slate-400 hover:text-slate-200 transition"
              title="Acercar"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            {zoomLevel !== 1 && (
              <button
                onClick={() => setZoomLevel(1)}
                className="text-[9px] px-1 text-cyan-400 hover:underline"
              >
                100%
              </button>
            )}
          </div>

          <button
            onClick={onRefresh}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
            title="Recargar montaje"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 overflow-auto bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] bg-slate-950/80 p-4 flex items-center justify-center relative">
        <div
          style={{
            width: isConstrained ? device.width : '100%',
            height: isConstrained ? device.height : '100%',
            transform: `scale(${zoomLevel})`,
            transformOrigin: 'center center',
            transition: 'width 0.2s ease, height 0.2s ease',
          }}
          className={`relative bg-slate-950 shadow-2xl transition-all ${
            isConstrained
              ? 'rounded-2xl border-4 border-slate-800 overflow-hidden ring-1 ring-slate-700/50'
              : 'w-full h-full rounded-none border-none'
          }`}
        >
          {/* Constrained Device Notch simulation */}
          {viewportDevice === 'mobile' && (
            <div className="absolute top-2 left-1/2 -translate-x-1/2 w-24 h-4 bg-slate-900 rounded-full z-20 pointer-events-none border border-slate-800" />
          )}

          {/* Sandboxed Live Execution Frame */}
          <iframe
            ref={iframeRef}
            title="Frontend en Ejecución"
            sandbox="allow-scripts allow-forms allow-same-origin allow-modals allow-popups"
            className="w-full h-full border-0 bg-slate-950"
          />
        </div>
      </div>

      {/* Bottom Status Info */}
      <div className="h-6 px-3 bg-slate-900/80 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>IFrame Sandbox Seguro</span>
        </div>
        <div>
          <span>Babel Standalone + React 18/19 + Tailwind CDN</span>
        </div>
      </div>
    </div>
  );
};
