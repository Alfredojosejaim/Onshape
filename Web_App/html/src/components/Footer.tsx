import React from 'react';

interface FooterProps {
  elementsCount?: number;
  nodesCount?: number;
  cursorCoordinates?: { x: number; y: number; z: number };
}

export const Footer: React.FC<FooterProps> = ({
  elementsCount = 184920,
  nodesCount = 38412,
  cursorCoordinates = { x: 124.5, y: 45.2, z: 0.0 },
}) => {
  return (
    <footer className="fixed bottom-0 left-0 right-0 h-7 bg-[#0b0e17] border-t border-[#2e3646] z-40 px-3 flex items-center justify-between font-label-sm text-[10px] text-[#94a3b8]">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1">
          <span className="text-[#64748b]">XYZ:</span>
          <span className="text-[#f1f5f9] font-mono">
            X: {cursorCoordinates.x.toFixed(2)} mm, Y: {cursorCoordinates.y.toFixed(2)} mm, Z: {cursorCoordinates.z.toFixed(2)} mm
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[#64748b]">Unidades:</span>
          <span className="text-[#f1f5f9]">mm [kg·mm·s]</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[#64748b]">Elementos Tet4:</span>
          <span className="text-[#7bd0ff]">{elementsCount.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[#64748b]">Nodos:</span>
          <span className="text-[#f1f5f9]">{nodesCount.toLocaleString()}</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
          <span className="text-[#f1f5f9]">VTK OpenGL2: 60 FPS (Hardware Accel)</span>
        </div>
        <div className="hidden lg:flex items-center gap-1 text-[#64748b]">
          <span>Atajos: [Shift+RMB] Rotar | [MMB] Pan | [R] Reset Vista</span>
        </div>
      </div>
    </footer>
  );
};
