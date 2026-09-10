import * as Babel from '@babel/standalone';
import { CompilationResult } from '../types';

/**
 * Transpiles TSX or JSX into executable JavaScript and wraps it with a runtime mounting harness
 */
export function compileTsxCode(tsxCode: string): CompilationResult {
  const startTime = performance.now();
  try {
    // Resolve babel object whether default or namespace
    const babelObj = (Babel as unknown as { default?: typeof Babel }).default || Babel;

    // Transpile using typescript and react presets
    const transformed = babelObj.transform(tsxCode, {
      presets: [
        ['typescript', { isTSX: true, allExtensions: true }],
        ['react', { runtime: 'classic' }],
      ],
      filename: 'Component.tsx',
    });

    const transpiledJs = transformed.code || '';

    // Create an executable harness that mounts into the iframe DOM
    // We provide a shim for common imports like 'react' or 'lucide-react'
    const harnessedHtml = generateTsxPreviewHtml(transpiledJs);

    return {
      status: 'success',
      compiledCode: harnessedHtml,
      durationMs: Math.round(performance.now() - startTime),
    };
  } catch (err: unknown) {
    const error = err as { message?: string; loc?: { line?: number } };
    const errorMessage = error?.message || 'Error desconocido de compilación';
    const errorLine = error?.loc?.line;

    return {
      status: 'error',
      errorMessage,
      errorLine,
      durationMs: Math.round(performance.now() - startTime),
    };
  }
}

/**
 * Generates the complete, sandboxed HTML document that mounts the compiled TSX component
 */
function generateTsxPreviewHtml(jsCode: string): string {
  // We sanitize and wrap the user code.
  // Transform imports: strip `import ... from '...'` and replace with global lookups
  const processedCode = jsCode
    .replace(/import\s+[\s\S]*?from\s+['"][^'"]+['"];?/g, '') // remove imports since we provide React & libraries globally
    .replace(/export\s+default\s+function\s+([a-zA-Z0-9_$]+)/g, 'function $1')
    .replace(/export\s+default\s+/g, 'window.__USER_ENTRY_COMPONENT__ = ')
    .replace(/export\s+const\s+/g, 'const ')
    .replace(/export\s+let\s+/g, 'let ')
    .replace(/export\s+function\s+/g, 'function ');

  return `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Live Preview</title>
  <!-- Tailwind CSS Engine -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- React 18 / 19 UMD -->
  <script src="https://unpkg.com/react@18.3.1/umd/react.development.js"></script>
  <script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js"></script>
  <style>
    body {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      -webkit-font-smoothing: antialiased;
    }
    /* Inspector highlight outline */
    .studiodesk-inspect-hover {
      outline: 2px dashed #06b6d4 !important;
      outline-offset: -2px !important;
      cursor: crosshair !important;
    }
    .studiodesk-inspect-selected {
      outline: 2px solid #3b82f6 !important;
      outline-offset: -2px !important;
      background-color: rgba(59, 130, 246, 0.08) !important;
    }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen">
  <div id="root"></div>

  <script>
    // Console proxy to send logs back to parent StudioDesk window
    (function() {
      const origLog = console.log;
      const origWarn = console.warn;
      const origError = console.error;
      const origInfo = console.info;

      function post(type, args) {
        try {
          const content = Array.from(args).map(a => {
            if (typeof a === 'object') {
              try { return JSON.stringify(a); } catch(e) { return String(a); }
            }
            return String(a);
          }).join(' ');

          window.parent.postMessage({
            type: 'STUDIODESK_LOG',
            log: {
              type: type,
              content: content,
              timestamp: new Date().toLocaleTimeString(),
            }
          }, '*');
        } catch(e) {}
      }

      console.log = function() { origLog.apply(console, arguments); post('log', arguments); };
      console.warn = function() { origWarn.apply(console, arguments); post('warn', arguments); };
      console.error = function() { origError.apply(console, arguments); post('error', arguments); };
      console.info = function() { origInfo.apply(console, arguments); post('info', arguments); };

      window.onerror = function(message, source, lineno, colno, error) {
        post('error', ['[Runtime Error: ' + message + ' (Línea ' + lineno + ')]']);
      };
    })();

    // Make React hooks and APIs available in global scope for transpiled code
    window.useState = React.useState;
    window.useEffect = React.useEffect;
    window.useMemo = React.useMemo;
    window.useCallback = React.useCallback;
    window.useRef = React.useRef;
    window.useContext = React.useContext;
    window.useReducer = React.useReducer;

    // Execute user code
    try {
      ${processedCode}

      // Find root component
      let EntryComp = window.__USER_ENTRY_COMPONENT__;
      if (!EntryComp) {
        if (typeof App !== 'undefined') EntryComp = App;
        else if (typeof Component !== 'undefined') EntryComp = Component;
        else if (typeof Main !== 'undefined') EntryComp = Main;
        else if (typeof Dashboard !== 'undefined') EntryComp = Dashboard;
        else if (typeof KanbanBoard !== 'undefined') EntryComp = KanbanBoard;
      }

      const rootElement = document.getElementById('root');
      if (EntryComp && rootElement) {
        const root = ReactDOM.createRoot(rootElement);
        root.render(React.createElement(EntryComp));
        console.log('Componente TSX montado en ejecución exitosamente');
      } else if (!EntryComp) {
        console.warn('No se detectó un export default o función App principal en el archivo TSX');
        rootElement.innerHTML = '<div class="p-8 text-center text-amber-400 font-sans"><p class="font-bold">Aviso de Montaje</p><p class="text-sm mt-1 text-slate-300">Asegúrate de exportar tu componente con: <code>export default function App() { ... }</code></p></div>';
      }
    } catch (err) {
      console.error('Error al ejecutar el componente montado:', err.message);
      document.getElementById('root').innerHTML = '<div style="padding: 24px; font-family: monospace; background: #450a0a; color: #fca5a5; border-radius: 12px; margin: 16px; border: 1px solid #dc2626;"><h3 style="margin: 0 0 8px 0; font-size: 16px;">Error en tiempo de ejecución</h3><pre style="white-space: pre-wrap; font-size: 12px;">' + err.stack + '</pre></div>';
    }

    // Inspector Bridge
    let inspectMode = false;
    let selectedEl = null;
    let hoveredEl = null;

    function getElementSelector(el) {
      if (!el || el === document.body || el === document.documentElement) return '';
      if (el.id) return '#' + el.id;
      let path = el.tagName.toLowerCase();
      if (el.className && typeof el.className === 'string') {
        const firstClass = el.className.trim().split(/\\s+/)[0];
        if (firstClass && !firstClass.includes(':') && !firstClass.includes('/')) {
          path += '.' + firstClass;
        }
      }
      return path;
    }

    window.addEventListener('message', function(e) {
      if (!e.data) return;
      if (e.data.type === 'SET_INSPECT_MODE') {
        inspectMode = !!e.data.enabled;
        if (!inspectMode) {
          if (hoveredEl) hoveredEl.classList.remove('studiodesk-inspect-hover');
          if (selectedEl) selectedEl.classList.remove('studiodesk-inspect-selected');
        }
      } else if (e.data.type === 'UPDATE_SELECTED_TEXT') {
        if (selectedEl) {
          selectedEl.innerText = e.data.text;
        }
      } else if (e.data.type === 'UPDATE_SELECTED_CLASSES') {
        if (selectedEl) {
          selectedEl.className = e.data.className;
        }
      }
    });

    document.addEventListener('mouseover', function(e) {
      if (!inspectMode) return;
      const target = e.target;
      if (target.id === 'root' || target === document.body) return;
      if (hoveredEl && hoveredEl !== target) {
        hoveredEl.classList.remove('studiodesk-inspect-hover');
      }
      hoveredEl = target;
      hoveredEl.classList.add('studiodesk-inspect-hover');
    });

    document.addEventListener('mouseout', function(e) {
      if (!inspectMode) return;
      if (hoveredEl) {
        hoveredEl.classList.remove('studiodesk-inspect-hover');
        hoveredEl = null;
      }
    });

    document.addEventListener('click', function(e) {
      if (!inspectMode) return;
      e.preventDefault();
      e.stopPropagation();

      const target = e.target;
      if (target.id === 'root' || target === document.body) return;

      if (selectedEl) selectedEl.classList.remove('studiodesk-inspect-selected');
      selectedEl = target;
      selectedEl.classList.add('studiodesk-inspect-selected');

      const rect = target.getBoundingClientRect();
      const payload = {
        type: 'ELEMENT_SELECTED',
        element: {
          tagName: target.tagName.toLowerCase(),
          id: target.id || '',
          className: target.className ? target.className.replace('studiodesk-inspect-selected', '').replace('studiodesk-inspect-hover', '').trim() : '',
          text: target.innerText ? target.innerText.slice(0, 100) : '',
          selector: getElementSelector(target),
          boundingRect: {
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height
          }
        }
      };

      window.parent.postMessage(payload, '*');
    }, true);
  </script>
</body>
</html>`;
}

/**
 * Prepares and injects the live inspector & console logger into HTML code
 */
export function prepareHtmlPreview(htmlCode: string): string {
  let content = htmlCode;

  // Ensure Tailwind is present for instant modern styling if not already imported
  if (!content.includes('tailwindcss.com') && !content.includes('tailwind')) {
    content = content.replace('</head>', '<script src="https://cdn.tailwindcss.com"></script></head>');
    if (!content.includes('</head>')) {
      content = '<script src="https://cdn.tailwindcss.com"></script>' + content;
    }
  }

  // Inject styles for hover and selection
  const inspectorStyles = `
  <style>
    .studiodesk-inspect-hover {
      outline: 2px dashed #06b6d4 !important;
      outline-offset: -2px !important;
      cursor: crosshair !important;
    }
    .studiodesk-inspect-selected {
      outline: 2px solid #3b82f6 !important;
      outline-offset: -2px !important;
      background-color: rgba(59, 130, 246, 0.08) !important;
    }
  </style>
  `;

  // Inject console logger and inspector bridge script
  const bridgeScript = `
  <script>
    (function() {
      const origLog = console.log;
      const origWarn = console.warn;
      const origError = console.error;

      function post(type, args) {
        try {
          const content = Array.from(args).map(a => {
            if (typeof a === 'object') {
              try { return JSON.stringify(a); } catch(e) { return String(a); }
            }
            return String(a);
          }).join(' ');

          window.parent.postMessage({
            type: 'STUDIODESK_LOG',
            log: {
              type: type,
              content: content,
              timestamp: new Date().toLocaleTimeString(),
            }
          }, '*');
        } catch(e) {}
      }

      console.log = function() { origLog.apply(console, arguments); post('log', arguments); };
      console.warn = function() { origWarn.apply(console, arguments); post('warn', arguments); };
      console.error = function() { origError.apply(console, arguments); post('error', arguments); };

      window.onerror = function(message, source, lineno) {
        post('error', ['[HTML Error: ' + message + ' (Línea ' + lineno + ')]']);
      };
    })();

    let inspectMode = false;
    let selectedEl = null;
    let hoveredEl = null;

    function getElementSelector(el) {
      if (!el || el === document.body || el === document.documentElement) return '';
      if (el.id) return '#' + el.id;
      let path = el.tagName.toLowerCase();
      if (el.className && typeof el.className === 'string') {
        const firstClass = el.className.trim().split(/\\s+/)[0];
        if (firstClass && !firstClass.includes(':') && !firstClass.includes('/')) {
          path += '.' + firstClass;
        }
      }
      return path;
    }

    window.addEventListener('message', function(e) {
      if (!e.data) return;
      if (e.data.type === 'SET_INSPECT_MODE') {
        inspectMode = !!e.data.enabled;
        if (!inspectMode) {
          if (hoveredEl) hoveredEl.classList.remove('studiodesk-inspect-hover');
          if (selectedEl) selectedEl.classList.remove('studiodesk-inspect-selected');
        }
      } else if (e.data.type === 'UPDATE_SELECTED_TEXT') {
        if (selectedEl) {
          selectedEl.innerText = e.data.text;
        }
      } else if (e.data.type === 'UPDATE_SELECTED_CLASSES') {
        if (selectedEl) {
          selectedEl.className = e.data.className;
        }
      }
    });

    document.addEventListener('mouseover', function(e) {
      if (!inspectMode) return;
      const target = e.target;
      if (target === document.body || target === document.documentElement) return;
      if (hoveredEl && hoveredEl !== target) {
        hoveredEl.classList.remove('studiodesk-inspect-hover');
      }
      hoveredEl = target;
      hoveredEl.classList.add('studiodesk-inspect-hover');
    });

    document.addEventListener('mouseout', function(e) {
      if (!inspectMode) return;
      if (hoveredEl) {
        hoveredEl.classList.remove('studiodesk-inspect-hover');
        hoveredEl = null;
      }
    });

    document.addEventListener('click', function(e) {
      if (!inspectMode) return;
      e.preventDefault();
      e.stopPropagation();

      const target = e.target;
      if (target === document.body || target === document.documentElement) return;

      if (selectedEl) selectedEl.classList.remove('studiodesk-inspect-selected');
      selectedEl = target;
      selectedEl.classList.add('studiodesk-inspect-selected');

      const rect = target.getBoundingClientRect();
      window.parent.postMessage({
        type: 'ELEMENT_SELECTED',
        element: {
          tagName: target.tagName.toLowerCase(),
          id: target.id || '',
          className: target.className ? target.className.replace('studiodesk-inspect-selected', '').replace('studiodesk-inspect-hover', '').trim() : '',
          text: target.innerText ? target.innerText.slice(0, 100) : '',
          selector: getElementSelector(target),
          boundingRect: {
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height
          }
        }
      }, '*');
    }, true);
  </script>
  `;

  if (content.includes('</body>')) {
    return content.replace('</head>', inspectorStyles + '</head>').replace('</body>', bridgeScript + '</body>');
  }

  return content + inspectorStyles + bridgeScript;
}
