import React, { useState } from 'react';

interface ViewCubeProps {
  onViewChange?: (view: string) => void;
  className?: string;
}

export const ViewCube: React.FC<ViewCubeProps> = ({ onViewChange, className = '' }) => {
  const [activeFace, setActiveFace] = useState<string>('ISO');

  const handleFaceClick = (face: string) => {
    setActiveFace(face);
    if (onViewChange) {
      onViewChange(face);
    }
  };

  return (
    <aside className={`flex flex-col items-end gap-1.5 ${className}`}>
      <div className="relative w-28 h-28 bg-[#1f2430]/90 backdrop-blur-md rounded-xl p-1.5 shadow-xl flex flex-col items-center justify-center border border-[#2e3646]/60 select-none">
        {/* Cube SVG Isometric Representation */}
        <svg className="w-20 h-20 drop-shadow-md cursor-pointer" viewBox="0 0 100 100">
          {/* Orientation Ring Indicators */}
          <circle
            cx="50"
            cy="50"
            r="46"
            fill="none"
            stroke="#2e3646"
            strokeDasharray="3 3"
            strokeWidth="1"
          />

          {/* TOP FACE */}
          <polygon
            onClick={() => handleFaceClick('TOP')}
            className="hover:fill-[#7bd0ff] transition-colors cursor-pointer"
            fill={activeFace === 'TOP' ? '#7bd0ff' : '#2e3646'}
            points="50,15 85,32 50,48 15,32"
          />
          <text
            fill={activeFace === 'TOP' ? '#00354a' : '#f1f5f9'}
            fontFamily="JetBrains Mono"
            fontSize="8"
            fontWeight="bold"
            textAnchor="middle"
            x="50"
            y="33"
            className="pointer-events-none"
          >
            TOP
          </text>

          {/* FRONT FACE */}
          <polygon
            onClick={() => handleFaceClick('FRONT')}
            className="hover:fill-[#7bd0ff] transition-colors cursor-pointer"
            fill={activeFace === 'FRONT' ? '#7bd0ff' : '#1f2430'}
            points="15,32 50,48 50,85 15,67"
          />
          <text
            fill={activeFace === 'FRONT' ? '#00354a' : '#94a3b8'}
            fontFamily="JetBrains Mono"
            fontSize="7"
            textAnchor="middle"
            x="32"
            y="60"
            className="pointer-events-none"
          >
            FRONT
          </text>

          {/* RIGHT FACE */}
          <polygon
            onClick={() => handleFaceClick('RIGHT')}
            className="hover:fill-[#7bd0ff] transition-colors cursor-pointer"
            fill={activeFace === 'RIGHT' ? '#7bd0ff' : '#181b24'}
            points="50,48 85,32 85,67 50,85"
          />
          <text
            fill={activeFace === 'RIGHT' ? '#00354a' : '#bec8d2'}
            fontFamily="JetBrains Mono"
            fontSize="7"
            textAnchor="middle"
            x="68"
            y="60"
            className="pointer-events-none"
          >
            RIGHT
          </text>
        </svg>

        <div className="flex items-center justify-between w-full mt-0.5 px-1 text-[9px] font-label-sm text-[#64748b]">
          <span
            onClick={() => handleFaceClick('ISO')}
            className={`cursor-pointer hover:text-[#7bd0ff] ${activeFace === 'ISO' ? 'text-[#7bd0ff] font-bold' : ''}`}
          >
            ISO
          </span>
          <span
            onClick={() => handleFaceClick('PERSP')}
            className={`cursor-pointer hover:text-[#7bd0ff] ${activeFace === 'PERSP' ? 'text-[#7bd0ff] font-bold' : ''}`}
          >
            PERSP
          </span>
          <span
            onClick={() => handleFaceClick('FIT')}
            className={`cursor-pointer hover:text-[#7bd0ff] ${activeFace === 'FIT' ? 'text-[#7bd0ff] font-bold' : ''}`}
          >
            FIT
          </span>
        </div>
      </div>
    </aside>
  );
};
