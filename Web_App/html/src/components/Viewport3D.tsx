import React, { useState, useRef } from 'react';
import { TabId } from '../types';

interface Viewport3DProps {
  activeTab: TabId;
  forceMagnitude?: number;
  feaDeformedScale?: number;
  feaStressType?: string;
  simpIteration?: number;
  simpDensityCutoff?: number;
  selectedMaterialName?: string;
  onSelectFace?: (faceId: number) => void;
  selectedFace?: number | null;
}

export const Viewport3D: React.FC<Viewport3DProps> = ({
  activeTab,
}) => {
  // 3D Camera & interaction state
  const [rotation, setRotation] = useState({ x: 22, y: -28 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragMode, setDragMode] = useState<'orbit' | 'pan'>('orbit');
  const [lastMouse, setLastMouse] = useState({ x: 0, y: 0 });

  // Viewport toggles
  const [selectionMode, setSelectionMode] = useState<'faces' | 'edges' | 'vertices' | 'volumes'>('faces');
  const [isWireframe, setIsWireframe] = useState(false);
  const [isClipPlane, setIsClipPlane] = useState(false);
  const [clipDistance, setClipDistance] = useState(50);

  const containerRef = useRef<HTMLDivElement>(null);

  // Mouse drag handling for orbit / pan
  const handleMouseDown = (e: React.MouseEvent) => {
    // 0 = LMB, 1 = MMB, 2 = RMB
    if (e.button === 1 || e.shiftKey) {
      setDragMode('pan');
    } else {
      setDragMode('orbit');
    }
    setIsDragging(true);
    setLastMouse({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;

    const deltaX = e.clientX - lastMouse.x;
    const deltaY = e.clientY - lastMouse.y;
    setLastMouse({ x: e.clientX, y: e.clientY });

    if (dragMode === 'orbit') {
      setRotation((prev) => ({
        x: Math.max(-80, Math.min(80, prev.x + deltaY * 0.4)),
        y: prev.y + deltaX * 0.4,
      }));
    } else {
      setPan((prev) => ({
        x: prev.x + deltaX * 0.8,
        y: prev.y + deltaY * 0.8,
      }));
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomDelta = e.deltaY < 0 ? 0.08 : -0.08;
    setZoom((prev) => Math.max(0.6, Math.min(2.5, prev + zoomDelta)));
  };

  const setViewPreset = (preset: 'ISO' | 'TOP' | 'FRONT' | 'RIGHT' | 'FIT') => {
    switch (preset) {
      case 'ISO':
        setRotation({ x: 22, y: -28 });
        break;
      case 'TOP':
        setRotation({ x: 90, y: 0 });
        break;
      case 'FRONT':
        setRotation({ x: 0, y: 0 });
        break;
      case 'RIGHT':
        setRotation({ x: 0, y: -90 });
        break;
      case 'FIT':
        setRotation({ x: 22, y: -28 });
        setZoom(1);
        setPan({ x: 0, y: 0 });
        break;
    }
  };

  // SVG transformations
  const transformStyle = {
    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
    transformOrigin: 'center center',
    transition: isDragging ? 'none' : 'transform 0.15s ease-out',
  };

  return (
    <div
      ref={containerRef}
      className="flex-1 flex flex-col relative rounded-lg bg-[#0b0e17] overflow-hidden shadow-2xl min-h-[560px] select-none cursor-crosshair border border-[#2e3646]/60"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* Perspective background grid */}
      <svg className="absolute inset-0 w-full h-full opacity-20 pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="cadGridLarge" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#2e3646" strokeWidth="0.75" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#cadGridLarge)" />
      </svg>

      {/* Top Floating Viewport Control Ribbon */}
      <div className="absolute top-3 left-3 z-30 flex items-center gap-1.5 bg-[#1f2430]/90 backdrop-blur-md px-2 py-1 rounded-lg border border-[#2e3646] shadow-xl">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setSelectionMode('faces')}
            className={`px-2 py-1 rounded text-xs font-semibold flex items-center gap-1 transition-all ${
              selectionMode === 'faces'
                ? 'bg-[#0ea5e9] text-[#003751] shadow-sm'
                : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#272a33]'
            }`}
            title="Selección de Caras B-Rep"
          >
            <span className="material-symbols-outlined text-[15px]">crop_free</span>
            <span>Caras</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectionMode('edges')}
            className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 transition-all ${
              selectionMode === 'edges'
                ? 'bg-[#0ea5e9] text-[#003751] shadow-sm'
                : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#272a33]'
            }`}
            title="Selección de Aristas"
          >
            <span className="material-symbols-outlined text-[15px]">straighten</span>
            <span>Aristas</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectionMode('vertices')}
            className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 transition-all ${
              selectionMode === 'vertices'
                ? 'bg-[#0ea5e9] text-[#003751] shadow-sm'
                : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#272a33]'
            }`}
            title="Selección de Vértices/Nodos"
          >
            <span className="material-symbols-outlined text-[15px]">grain</span>
            <span>Vértices</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectionMode('volumes')}
            className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 transition-all ${
              selectionMode === 'volumes'
                ? 'bg-[#0ea5e9] text-[#003751] shadow-sm'
                : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#272a33]'
            }`}
            title="Selección de Volúmenes / Espacio de Diseño"
          >
            <span className="material-symbols-outlined text-[15px]">view_in_ar</span>
            <span>Volúmenes</span>
          </button>
        </div>

        <div className="w-px h-4 bg-[#2e3646] mx-1"></div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setIsClipPlane(!isClipPlane)}
            className={`p-1 rounded transition-colors ${
              isClipPlane ? 'bg-[#0ea5e9]/20 text-[#7bd0ff] border border-[#7bd0ff]/40' : 'text-[#94a3b8] hover:text-[#7bd0ff] hover:bg-[#272a33]'
            }`}
            title="Plano de Corte Interactivo (Clip Plane)"
          >
            <span className="material-symbols-outlined text-[16px]">cut</span>
          </button>
          <button
            type="button"
            onClick={() => setIsWireframe(!isWireframe)}
            className={`p-1 rounded transition-colors ${
              isWireframe ? 'bg-[#0ea5e9]/20 text-[#7bd0ff] border border-[#7bd0ff]/40' : 'text-[#94a3b8] hover:text-[#7bd0ff] hover:bg-[#272a33]'
            }`}
            title="Modo Alambre / Malla Oculta (Wireframe)"
          >
            <span className="material-symbols-outlined text-[16px]">grid_4x4</span>
          </button>
          <button
            type="button"
            onClick={() => setViewPreset('FIT')}
            className="p-1 rounded text-[#94a3b8] hover:text-[#7bd0ff] hover:bg-[#272a33] transition-colors"
            title="Centrar y Ajustar Vista (Zoom Fit)"
          >
            <span className="material-symbols-outlined text-[16px]">center_focus_strong</span>
          </button>
        </div>

        {/* Optional Clip Plane Slider when active */}
        {isClipPlane && (
          <div className="flex items-center gap-2 pl-2 border-l border-[#2e3646]">
            <span className="text-[10px] font-mono text-[#94a3b8]">Corte Z:</span>
            <input
              type="range"
              min="0"
              max="100"
              value={clipDistance}
              onChange={(e) => setClipDistance(Number(e.target.value))}
              className="w-16 accent-[#0ea5e9] cursor-pointer"
            />
            <span className="text-[10px] font-mono text-[#7bd0ff]">{clipDistance}%</span>
          </div>
        )}
      </div>

      {/* Floating ViewCube Gizmo (Top Right) */}
      <div className="absolute top-3 right-3 z-30 flex flex-col items-end gap-2">
        <div className="relative w-28 h-28 bg-[#1f2430]/90 backdrop-blur-md rounded-xl p-2 border border-[#2e3646] shadow-2xl flex flex-col items-center justify-center">
          <svg className="w-20 h-20 drop-shadow-md" viewBox="0 0 100 100">
            {/* Orientation Ring */}
            <circle cx="50" cy="50" r="46" fill="none" stroke="#2e3646" strokeDasharray="3 3" strokeWidth="1" />
            {/* TOP FACE */}
            <polygon
              points="50,15 85,32 50,48 15,32"
              className="hover:fill-[#7bd0ff] transition-colors cursor-pointer fill-[#2e3646]"
              onClick={() => setViewPreset('TOP')}
            />
            <text x="50" y="33" fill="#f1f5f9" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold" textAnchor="middle" className="pointer-events-none">
              TOP
            </text>
            {/* FRONT FACE */}
            <polygon
              points="15,32 50,48 50,85 15,67"
              className="hover:fill-[#7bd0ff] transition-colors cursor-pointer fill-[#1f2430]"
              onClick={() => setViewPreset('FRONT')}
            />
            <text x="32" y="60" fill="#94a3b8" fontFamily="JetBrains Mono" fontSize="7" textAnchor="middle" className="pointer-events-none">
              FRONT
            </text>
            {/* RIGHT FACE */}
            <polygon
              points="50,48 85,32 85,67 50,85"
              className="hover:fill-[#7bd0ff] transition-colors cursor-pointer fill-[#181b24]"
              onClick={() => setViewPreset('RIGHT')}
            />
            <text x="68" y="60" fill="#bec8d2" fontFamily="JetBrains Mono" fontSize="7" textAnchor="middle" className="pointer-events-none">
              RIGHT
            </text>
          </svg>
          <div className="flex items-center justify-between w-full mt-1 px-1 text-[9px] font-mono text-[#94a3b8]">
            <button type="button" onClick={() => setViewPreset('ISO')} className="hover:text-[#7bd0ff] cursor-pointer">ISO</button>
            <button type="button" onClick={() => setViewPreset('FRONT')} className="hover:text-[#7bd0ff] cursor-pointer">PERSP</button>
            <button type="button" onClick={() => setViewPreset('FIT')} className="hover:text-[#7bd0ff] cursor-pointer">FIT</button>
          </div>
        </div>

        {/* Camera Quick Buttons */}
        <div className="flex flex-col gap-1 bg-[#1f2430]/90 backdrop-blur-md p-1 rounded-lg border border-[#2e3646] shadow-md">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9]"
            title="Acercar (Zoom +)"
          >
            <span className="material-symbols-outlined text-[15px]">zoom_in</span>
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.6, z - 0.15))}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9]"
            title="Alejar (Zoom -)"
          >
            <span className="material-symbols-outlined text-[15px]">zoom_out</span>
          </button>
          <button
            type="button"
            onClick={() => setViewPreset('ISO')}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-[#272a33] text-[#94a3b8] hover:text-[#f1f5f9]"
            title="Restablecer Rotación 3D"
          >
            <span className="material-symbols-outlined text-[15px]">3d_rotation</span>
          </button>
        </div>
      </div>

      {/* Main 3D Interactive Stage (Clean Empty CAD Workplane with Coordinate Datum) */}
      <div className="w-full flex-1 relative flex items-center justify-center bg-gradient-to-b from-[#0f1117] via-[#141824] to-[#10131c] overflow-hidden">
        <div style={transformStyle} className="relative w-full max-w-2xl h-[470px] flex items-center justify-center">
          <svg className="w-full h-full max-h-[460px] drop-shadow-2xl select-none" viewBox="0 0 600 420">
            <defs>
              <linearGradient id="datumPlaneGrid" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.08" />
                <stop offset="50%" stopColor="#1e2430" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.05" />
              </linearGradient>
            </defs>

            {/* Isometric Ground Reference Plane (XY Datum) */}
            <polygon
              points="300,120 520,240 300,360 80,240"
              fill="url(#datumPlaneGrid)"
              stroke="#2e3646"
              strokeWidth="1.2"
              strokeDasharray="4 2"
            />

            {/* Isometric Grid Lines along X and Y */}
            <g stroke="#2e3646" strokeWidth="0.75" opacity="0.6">
              {/* Lines parallel to X */}
              <line x1="124" y1="216" x2="344" y2="96" />
              <line x1="168" y1="240" x2="388" y2="120" />
              <line x1="212" y1="264" x2="432" y2="144" />
              <line x1="256" y1="288" x2="476" y2="168" />

              <line x1="124" y1="264" x2="344" y2="384" />
              <line x1="168" y1="288" x2="388" y2="408" />
              <line x1="212" y1="216" x2="432" y2="336" />
              <line x1="256" y1="192" x2="476" y2="312" />

              {/* Cross center lines */}
              <line x1="300" y1="120" x2="300" y2="360" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3 3" opacity="0.35" />
              <line x1="80" y1="240" x2="520" y2="240" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3 3" opacity="0.35" />
            </g>

            {/* Negative axes dashed rays from Origin (300, 240) */}
            <line x1="300" y1="240" x2="160" y2="160" stroke="#ef4444" strokeWidth="1" strokeDasharray="4 3" opacity="0.4" />
            <line x1="300" y1="240" x2="440" y2="160" stroke="#10b981" strokeWidth="1" strokeDasharray="4 3" opacity="0.4" />
            <line x1="300" y1="240" x2="300" y2="350" stroke="#38bdf8" strokeWidth="1" strokeDasharray="4 3" opacity="0.4" />

            {/* Principal 3D Coordinate Axis Rays from Origin (300, 240) */}
            {/* +X Axis (Red) */}
            <g>
              <line x1="300" y1="240" x2="470" y2="330" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
              <polygon points="475,333 460,323 466,335" fill="#ef4444" />
              <rect x="480" y="325" width="22" height="16" rx="3" fill="#1f2430" stroke="#ef4444" strokeWidth="1" />
              <text x="491" y="337" fill="#ef4444" fontFamily="JetBrains Mono" fontSize="9" fontWeight="bold" textAnchor="middle">
                +X
              </text>
            </g>

            {/* +Y Axis (Green) */}
            <g>
              <line x1="300" y1="240" x2="130" y2="330" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" />
              <polygon points="125,333 134,335 140,323" fill="#10b981" />
              <rect x="98" y="325" width="22" height="16" rx="3" fill="#1f2430" stroke="#10b981" strokeWidth="1" />
              <text x="109" y="337" fill="#10b981" fontFamily="JetBrains Mono" fontSize="9" fontWeight="bold" textAnchor="middle">
                +Y
              </text>
            </g>

            {/* +Z Axis (Blue) */}
            <g>
              <line x1="300" y1="240" x2="300" y2="60" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" />
              <polygon points="300,50 294,65 306,65" fill="#38bdf8" />
              <rect x="289" y="30" width="22" height="16" rx="3" fill="#1f2430" stroke="#38bdf8" strokeWidth="1" />
              <text x="300" y="42" fill="#38bdf8" fontFamily="JetBrains Mono" fontSize="9" fontWeight="bold" textAnchor="middle">
                +Z
              </text>
            </g>

            {/* Global Origin Point (0, 0, 0) */}
            <circle cx="300" cy="240" r="6" fill="#f1f5f9" stroke="#0ea5e9" strokeWidth="2" />
            <circle cx="300" cy="240" r="2" fill="#003751" />
            <text x="312" y="244" fill="#94a3b8" fontFamily="JetBrains Mono" fontSize="9" fontWeight="600">
              (0, 0, 0)
            </text>

            {/* Center Empty Viewport Informational Card */}
            <g transform="translate(300, 155)">
              <rect
                x="-140"
                y="-32"
                width="280"
                height="64"
                rx="8"
                fill="#181b24"
                fillOpacity="0.88"
                stroke="#2e3646"
                strokeWidth="1"
              />
              <circle cx="-105" cy="0" r="14" fill="#1f2430" stroke="#7bd0ff" strokeWidth="1" />
              <text x="-105" y="4" fill="#7bd0ff" fontFamily="Material Symbols Outlined" fontSize="16" textAnchor="middle">
                view_in_ar
              </text>
              <text x="-80" y="-8" fill="#f1f5f9" fontFamily="JetBrains Mono" fontSize="11" fontWeight="bold">
                Visor 3D Vacío
              </text>
              <text x="-80" y="8" fill="#94a3b8" fontFamily="Inter, sans-serif" fontSize="10">
                Sin modelos geométricos cargados
              </text>
              <text x="-80" y="22" fill="#64748b" fontFamily="JetBrains Mono" fontSize="8">
                Espacio de coordenadas [mm] listo
              </text>
            </g>
          </svg>
        </div>

        {/* Global WCS Triad Gizmo (Bottom Left) */}
        <div className="absolute bottom-3 left-3 z-20 flex items-center gap-2 bg-[#1f2430]/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#2e3646] shadow-md">
          <svg className="w-10 h-10" viewBox="0 0 54 54">
            {/* Center at 20, 36 */}
            {/* X axis (Red) */}
            <line x1="20" y1="36" x2="48" y2="36" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" />
            <polygon points="48,36 43,33 43,39" fill="#ef4444" />
            <text x="50" y="38" fill="#ef4444" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold">X</text>
            {/* Y axis (Green) */}
            <line x1="20" y1="36" x2="20" y2="8" stroke="#10b981" strokeWidth="2" strokeLinecap="round" />
            <polygon points="20,8 17,13 23,13" fill="#10b981" />
            <text x="18" y="6" fill="#10b981" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold">Y</text>
            {/* Z axis (Blue) */}
            <line x1="20" y1="36" x2="6" y2="48" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" />
            <polygon points="6,48 11,46 8,43" fill="#38bdf8" />
            <text x="0" y="52" fill="#38bdf8" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold">Z</text>
            <circle cx="20" cy="36" r="2.5" fill="#f1f5f9" />
          </svg>
          <div className="flex flex-col">
            <span className="text-[#f1f5f9] font-mono text-[11px] font-bold">WCS Global</span>
            <span className="text-[#94a3b8] font-mono text-[10px]">
              Rot: {Math.round(rotation.x)}°, {Math.round(rotation.y)}°
            </span>
          </div>
        </div>

        {/* Viewport Scale & Status (Bottom Right) */}
        <div className="absolute bottom-3 right-3 z-20 flex items-center gap-3 bg-[#1f2430]/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#2e3646] shadow-md font-mono text-[10px]">
          <div className="flex flex-col items-end">
            <div className="w-16 h-1 bg-[#94a3b8] rounded-full" />
            <span className="text-[#94a3b8] text-[9px] mt-0.5">50.0 mm</span>
          </div>
          <div className="w-px h-5 bg-[#2e3646]" />
          <span className="text-[#94a3b8] flex items-center gap-1.5 font-medium">
            <span className="w-2 h-2 rounded-full bg-[#64748b]" />
            Visor vacío (Sin modelos)
          </span>
        </div>
      </div>
    </div>
  );
};
