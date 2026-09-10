import React from 'react';

interface FooterProps {
  coords: { x: number; y: number; z: number };
  elementsCount: number;
  nodesCount: number;
}

export const Footer: React.FC<FooterProps> = ({ coords, elementsCount, nodesCount }) => {
  return (
    <footer className="fixed bottom-0 left-0 right-0 h-7 bg-surface-container-lowest border-t border-border-subtle z-40 px-space-md flex items-center justify-between font-mono text-[10px] text-text-secondary select-none">
      {/* Left Specs */}
      <div className="flex items-center gap-space-lg">
        <div className="flex items-center gap-1">
          <span className="text-text-muted">XYZ:</span>
          <span className="text-text-primary font-medium">
            X: {coords.x.toFixed(2)} mm, Y: {coords.y.toFixed(2)} mm, Z: {coords.z.toFixed(2)} mm
          </span>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-text-muted">Unidades:</span>
          <span className="text-text-primary font-medium">mm [kg·mm·s]</span>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-text-muted">Elementos Tet4:</span>
          <span className="text-secondary font-medium">{elementsCount.toLocaleString()}</span>
        </div>

        <div className="flex items-center gap-1">
          <span className="text-text-muted">Nodos:</span>
          <span className="text-text-primary font-medium">{nodesCount.toLocaleString()}</span>
        </div>
      </div>

      {/* Right Specs */}
      <div className="flex items-center gap-space-lg">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-fea-stress-optimal"></span>
          <span className="text-text-primary">VTK OpenGL2: 60 FPS (Hardware Accel)</span>
        </div>

        <div className="hidden lg:flex items-center gap-1 text-text-muted">
          <span>Atajos: [Shift+RMB] Rotar | [MMB] Pan | [R] Reset Vista</span>
        </div>
      </div>
    </footer>
  );
};
