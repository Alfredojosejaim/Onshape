import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { ActiveTab, ActiveTool, BoundaryCondition, Material, OptimizationState } from '../types';

interface CadViewportProps {
  activeTab: ActiveTab;
  activeTool: ActiveTool;
  selectedMaterial: Material;
  optimizationState: OptimizationState;
  boundaryConditions: BoundaryCondition[];
  showMesh: boolean;
  showSection: boolean;
  isModelVisible: boolean;
  deformationScale: number;
  onUpdateCoords: (coords: { x: number; y: number; z: number }) => void;
  resetViewTrigger: number;
  selectedViewTrigger: { view: 'iso' | 'top' | 'front' | 'right'; count: number };
}

export const CadViewport: React.FC<CadViewportProps> = ({
  activeTab,
  activeTool,
  selectedMaterial,
  optimizationState,
  boundaryConditions,
  showMesh,
  showSection,
  isModelVisible,
  deformationScale,
  onUpdateCoords,
  resetViewTrigger,
  selectedViewTrigger,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const modelGroupRef = useRef<THREE.Group | null>(null);
  const triadRendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const triadSceneRef = useRef<THREE.Scene | null>(null);
  const triadCameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const clipPlaneRef = useRef<THREE.Plane | null>(null);

  const [isOrbiting, setIsOrbiting] = useState(false);
  const [isPanning, setIsPanning] = useState(false);
  const [isOrthographic, setIsOrthographic] = useState(false);
  const [measurePoint, setMeasurePoint] = useState<string | null>(null);

  // Camera spherical coordinates state
  const cameraState = useRef({
    radius: 220,
    theta: Math.PI / 4, // 45 deg azimuth
    phi: Math.PI / 3, // 60 deg elevation
    target: new THREE.Vector3(0, 0, 0),
    isDragging: false,
    dragButton: 0,
    prevMouseX: 0,
    prevMouseY: 0,
  });

  const updateCameraPosition = useCallback(() => {
    if (!cameraRef.current) return;
    const { radius, theta, phi, target } = cameraState.current;
    const x = target.x + radius * Math.sin(phi) * Math.sin(theta);
    const y = target.y + radius * Math.cos(phi);
    const z = target.z + radius * Math.sin(phi) * Math.cos(theta);

    cameraRef.current.position.set(x, y, z);
    cameraRef.current.lookAt(target);
  }, []);

  const setNamedView = useCallback(
    (view: 'iso' | 'top' | 'front' | 'right') => {
      if (view === 'iso') {
        cameraState.current.theta = Math.PI / 4;
        cameraState.current.phi = Math.PI / 3;
        cameraState.current.radius = 220;
      } else if (view === 'top') {
        cameraState.current.theta = 0;
        cameraState.current.phi = 0.001;
        cameraState.current.radius = 220;
      } else if (view === 'front') {
        cameraState.current.theta = 0;
        cameraState.current.phi = Math.PI / 2;
        cameraState.current.radius = 220;
      } else if (view === 'right') {
        cameraState.current.theta = Math.PI / 2;
        cameraState.current.phi = Math.PI / 2;
        cameraState.current.radius = 220;
      }
      cameraState.current.target.set(0, 0, 0);
      updateCameraPosition();
    },
    [updateCameraPosition]
  );

  // React to view presets trigger from header
  useEffect(() => {
    if (selectedViewTrigger.count > 0) {
      setNamedView(selectedViewTrigger.view);
    }
  }, [selectedViewTrigger, setNamedView]);

  // React to reset view trigger
  useEffect(() => {
    if (resetViewTrigger > 0) {
      setNamedView('iso');
    }
  }, [resetViewTrigger, setNamedView]);

  // Setup Three.js Scene and Viewport
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Main Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f1117);
    sceneRef.current = scene;

    // Clipping plane for section view
    const clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 10);
    clipPlaneRef.current = clipPlane;

    // Main Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 2000);
    cameraRef.current = camera;

    // Main Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.localClippingEnabled = true;
    rendererRef.current = renderer;
    container.appendChild(renderer.domElement);

    // Subtle Perspective Ground Grid
    const gridHelper = new THREE.GridHelper(260, 26, 0x2e3646, 0x181b24);
    gridHelper.position.y = -35;
    scene.add(gridHelper);

    // Coordinate Planes visualizers
    const planeXY = new THREE.GridHelper(120, 12, 0xef4444, 0x272a33);
    planeXY.rotation.x = Math.PI / 2;
    planeXY.position.set(0, 0, 0);
    (planeXY.material as THREE.Material).opacity = 0.15;
    (planeXY.material as THREE.Material).transparent = true;
    scene.add(planeXY);

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight1.position.set(120, 180, 150);
    dirLight1.castShadow = true;
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x7bd0ff, 0.6);
    dirLight2.position.set(-150, -60, -100);
    scene.add(dirLight2);

    const pointLight = new THREE.PointLight(0x0ea5e9, 0.8, 300);
    pointLight.position.set(0, 50, 80);
    scene.add(pointLight);

    // Create Group for CAD Geometry
    const modelGroup = new THREE.Group();
    scene.add(modelGroup);
    modelGroupRef.current = modelGroup;

    updateCameraPosition();

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
    };
    animate();

    // Resize Handler with ResizeObserver
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: newWidth, height: newHeight } = entry.contentRect;
        if (newWidth > 0 && newHeight > 0 && cameraRef.current && rendererRef.current) {
          cameraRef.current.aspect = newWidth / newHeight;
          cameraRef.current.updateProjectionMatrix();
          rendererRef.current.setSize(newWidth, newHeight);
        }
      }
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [updateCameraPosition]);

  // UI-CLEAN-START (reversible): viewport limpio, sin modelo de referencia.
  // El bloque de geometria demo (bracket procedural + glifos anclados a el)
  // se elimino; el render real del STEP llegara por getSurfaceMesh.
  // Para volver atras: restaurar el efecto original (ver git).
  useEffect(() => {
    if (!modelGroupRef.current) return;
    const modelGroup = modelGroupRef.current;

    // Clear previous geometries
    while (modelGroup.children.length > 0) {
      const obj = modelGroup.children[0];
      modelGroup.remove(obj);
      if ((obj as THREE.Mesh).geometry) {
        ((obj as THREE.Mesh).geometry as THREE.BufferGeometry).dispose();
      }
    }
    // UI-CLEAN-END: escena vacia (rejilla + luces + overlays intactos).
  }, [
    activeTab,
    selectedMaterial,
    optimizationState,
    boundaryConditions,
    showMesh,
    showSection,
    isModelVisible,
    deformationScale,
  ]);

  // Handle Mouse / Pointer Events for Orbiting, Panning, and Coordinate Inspection
  // (UI-CLEAN: aqui habia ~200 lineas de geometria demo + glifos + el
  // cierre del efecto viejo; eliminadas. Ver git para restaurar.)

  // Handle Mouse / Pointer Events for Orbiting, Panning, and Coordinate Inspection
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    cameraState.current.isDragging = true;
    cameraState.current.dragButton = e.button;
    cameraState.current.prevMouseX = e.clientX;
    cameraState.current.prevMouseY = e.clientY;

    if (e.button === 0 && !e.shiftKey) {
      setIsOrbiting(true);
    } else if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
      setIsPanning(true);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      // Calculate normalized mouse coords in millimeters scale
      const relX = ((e.clientX - rect.left) / rect.width) * 160 - 80;
      const relY = ((rect.bottom - e.clientY) / rect.height) * 120 - 40;
      onUpdateCoords({
        x: parseFloat((relX + 124.5).toFixed(2)),
        y: parseFloat((relY + 45.2).toFixed(2)),
        z: 0.0,
      });
    }

    if (!cameraState.current.isDragging) return;

    const deltaX = e.clientX - cameraState.current.prevMouseX;
    const deltaY = e.clientY - cameraState.current.prevMouseY;
    cameraState.current.prevMouseX = e.clientX;
    cameraState.current.prevMouseY = e.clientY;

    // Pan with Middle Mouse Button (button 1) or Shift + Left Click
    if (cameraState.current.dragButton === 1 || (cameraState.current.dragButton === 0 && e.shiftKey)) {
      const panSpeed = 0.25;
      const right = new THREE.Vector3(1, 0, 0);
      const up = new THREE.Vector3(0, 1, 0);
      if (cameraRef.current) {
        right.crossVectors(cameraRef.current.up, cameraRef.current.getWorldDirection(new THREE.Vector3())).normalize();
        up.copy(cameraRef.current.up);
      }
      cameraState.current.target.addScaledVector(right, deltaX * panSpeed);
      cameraState.current.target.addScaledVector(up, deltaY * panSpeed);
      updateCameraPosition();
      return;
    }

    // Orbit with Left Click
    if (cameraState.current.dragButton === 0) {
      const rotSpeed = 0.008;
      cameraState.current.theta -= deltaX * rotSpeed;
      cameraState.current.phi -= deltaY * rotSpeed;

      // Clamp phi to prevent gimbal lock
      const minPhi = 0.05;
      const maxPhi = Math.PI - 0.05;
      cameraState.current.phi = Math.max(minPhi, Math.min(maxPhi, cameraState.current.phi));

      updateCameraPosition();
    }
  };

  const handleMouseUp = () => {
    cameraState.current.isDragging = false;
    setIsOrbiting(false);
    setIsPanning(false);
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 1.08 : 0.92;
    cameraState.current.radius = Math.max(50, Math.min(800, cameraState.current.radius * zoomFactor));
    updateCameraPosition();
  };

  return (
    <main
      ref={containerRef}
      id="cad-viewport-container"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      className="flex-1 flex flex-col relative rounded-lg bg-surface-container-lowest overflow-hidden shadow-2xl min-h-[580px] cursor-crosshair select-none"
    >
      {/* ViewCube Gizmo (Top Right Floating) */}
      <aside className="absolute top-space-sm right-space-sm z-20 flex flex-col items-end gap-space-xs pointer-events-auto">
        <div className="relative w-28 h-28 bg-surface-elevated/85 backdrop-blur-md rounded-xl p-space-xs shadow-xl flex flex-col items-center justify-center border border-border-subtle/50">
          {/* Cube SVG Isometric Representation */}
          <svg className="w-20 h-20 drop-shadow-md" viewBox="0 0 100 100">
            {/* TOP FACE */}
            <polygon
              onClick={(e) => {
                e.stopPropagation();
                setNamedView('top');
              }}
              className="hover:fill-secondary fill-[#2e3646] transition-colors cursor-pointer"
              points="50,15 85,32 50,48 15,32"
            />
            <text
              fill="#f1f5f9"
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
              onClick={(e) => {
                e.stopPropagation();
                setNamedView('front');
              }}
              className="hover:fill-secondary fill-[#1f2430] transition-colors cursor-pointer"
              points="15,32 50,48 50,85 15,67"
            />
            <text
              fill="#94a3b8"
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
              onClick={(e) => {
                e.stopPropagation();
                setNamedView('right');
              }}
              className="hover:fill-secondary fill-[#181b24] transition-colors cursor-pointer"
              points="50,48 85,32 85,67 50,85"
            />
            <text
              fill="#bec8d2"
              fontFamily="JetBrains Mono"
              fontSize="7"
              textAnchor="middle"
              x="68"
              y="60"
              className="pointer-events-none"
            >
              RIGHT
            </text>

            {/* Orientation Ring Indicators */}
            <circle cx="50" cy="50" fill="none" r="46" stroke="#2e3646" strokeDasharray="3 3" strokeWidth="1" />
          </svg>

          <div className="flex items-center justify-between w-full mt-1 px-1 text-[9px] font-mono text-text-muted">
            <span
              onClick={(e) => {
                e.stopPropagation();
                setNamedView('iso');
              }}
              className="hover:text-secondary cursor-pointer"
            >
              ISO
            </span>
            <span
              onClick={(e) => {
                e.stopPropagation();
                setIsOrthographic(!isOrthographic);
              }}
              className="hover:text-secondary cursor-pointer"
            >
              {isOrthographic ? 'ORTHO' : 'PERSP'}
            </span>
            <span
              onClick={(e) => {
                e.stopPropagation();
                setNamedView('iso');
              }}
              className="hover:text-secondary cursor-pointer"
            >
              FIT
            </span>
          </div>
        </div>

        {/* Camera Tool Floating Stack */}
        <div className="flex flex-col gap-1 bg-surface-elevated/90 backdrop-blur-md p-1 rounded-lg shadow-md border border-border-subtle/50">
          <button
            onClick={() => setNamedView('iso')}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container-high text-text-secondary hover:text-text-primary transition-colors"
            title="Ajustar Zoom (Fit)"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">center_focus_strong</span>
          </button>
          <button
            onClick={() => setNamedView('iso')}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container-high text-text-secondary hover:text-text-primary transition-colors"
            title="Rotar Órbita CAD"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">3d_rotation</span>
          </button>
          <button
            onClick={() => {
              cameraState.current.target.set(0, 0, 0);
              updateCameraPosition();
            }}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container-high text-text-secondary hover:text-text-primary transition-colors"
            title="Centrar Modelo"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">pan_tool</span>
          </button>
          <button
            onClick={() => setIsOrthographic(!isOrthographic)}
            className={`w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container-high transition-colors ${
              isOrthographic ? 'text-secondary' : 'text-text-secondary hover:text-text-primary'
            }`}
            title="Cambiar a Proyección Ortográfica"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">aspect_ratio</span>
          </button>
        </div>
      </aside>

      {/* Triad Gizmo (Bottom-Left Viewport) */}
      <div className="absolute bottom-space-sm left-space-sm z-20 flex items-center gap-space-xs bg-surface-elevated/85 backdrop-blur-md px-space-sm py-1 rounded-lg shadow-md border border-border-subtle/40 pointer-events-none">
        <svg className="w-12 h-12" viewBox="0 0 54 54">
          {/* Triad Lines: X (Red), Y (Green), Z (Blue) */}
          <line stroke="#ef4444" strokeLinecap="round" strokeWidth="2" x1="20" x2="48" y1="36" y2="36" />
          <polygon fill="#ef4444" points="48,36 43,33 43,39" />
          <text fill="#ef4444" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold" x="50" y="38">
            X
          </text>
          <line stroke="#10b981" strokeLinecap="round" strokeWidth="2" x1="20" x2="20" y1="36" y2="8" />
          <polygon fill="#10b981" points="20,8 17,13 23,13" />
          <text fill="#10b981" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold" x="18" y="6">
            Y
          </text>
          <line stroke="#38bdf8" strokeLinecap="round" strokeWidth="2" x1="20" x2="6" y1="36" y2="48" />
          <polygon fill="#38bdf8" points="6,48 11,46 8,43" />
          <text fill="#38bdf8" fontFamily="JetBrains Mono" fontSize="8" fontWeight="bold" x="0" y="52">
            Z
          </text>
          <circle cx="20" cy="36" fill="#f1f5f9" r="2.5" />
        </svg>
        <div className="flex flex-col">
          <span className="text-text-primary font-mono text-[10px] font-semibold">CAD OpenGL</span>
          <span className="text-text-muted font-mono text-[9px]">Vista Isométrica 30°</span>
        </div>
      </div>

      {/* Floating Mode Info Badge */}
      <div className="absolute top-space-sm left-space-sm z-20 flex items-center gap-2 pointer-events-none">
        <div className="bg-surface-elevated/90 backdrop-blur-md px-2.5 py-1 rounded-md border border-border-subtle/50 text-[10px] font-mono text-text-secondary flex items-center gap-2 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
          <span>
            MODO:{' '}
            <strong className="text-text-primary uppercase">
              {activeTab === 'optimizacion' ? 'Optimización Topológica SIMP' : 'Análisis Tensional FEA'}
            </strong>
          </span>
          {showSection && <span className="text-fea-stress-yield">• SECCIÓN CORTE ACTIVA</span>}
          {showMesh && <span className="text-secondary">• MALLA ACTIVADA</span>}
        </div>
      </div>
    </main>
  );
};
