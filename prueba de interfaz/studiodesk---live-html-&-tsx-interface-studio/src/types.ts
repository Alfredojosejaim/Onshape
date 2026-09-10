export type FileType = 'html' | 'tsx' | 'jsx' | 'css' | 'js' | 'json';

export interface ProjectFile {
  id: string;
  name: string;
  type: FileType;
  content: string;
  isEntry?: boolean;
  isModified?: boolean;
}

export type ViewportDevice = 'desktop' | 'laptop' | 'tablet' | 'mobile' | 'responsive';

export interface ViewportConfig {
  device: ViewportDevice;
  name: string;
  width: number | string;
  height: number | string;
  iconName: string;
}

export type ViewLayout = 'split' | 'live-only' | 'editor-only';
export type ExecutionMode = 'run' | 'inspect';

export interface SelectedElementInfo {
  tagName: string;
  id?: string;
  className: string;
  text: string;
  selector: string;
  boundingRect?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface ConsoleLogMessage {
  id: string;
  type: 'log' | 'warn' | 'error' | 'info';
  content: string;
  timestamp: string;
  count?: number;
}

export interface CompilationResult {
  status: 'idle' | 'compiling' | 'success' | 'error';
  errorMessage?: string;
  errorLine?: number;
  compiledCode?: string;
  durationMs?: number;
}
