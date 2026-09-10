import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { ActiveTab, ActiveTool, BoundaryCondition, Material, OptimizationState } from '../types';
// NAV-VIEW-START (reversible: quitar imports + prop surface + efectos/camara marcados)
import { dollyCamera, fitCamera, orbitCamera, panCamera, viewCamera } from '../lib/camera3d';
import {
  NAV_PROFILES,
  isNavProfileName,
  readStoredNavProfile,
  type NavAction,
  type NavProfileName,
} from '../lib/navigation';
import { backend } from '../lib/bridge';
import type { RealSurface } from '../lib/realdata';
// NAV-VIEW-END

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
  // NAV-VIEW (reversible): superficie real del STEP (null = escena vacia).
  surface: RealSurface | null;
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
  // NAV-VIEW (reversible)
  surface,
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

  // NAV-VIEW-START (reversible): camara libre estilo CameraController de la
  // predecesora (posicion + target + up; orbita trackball sin bloqueo a ejes,
  // pan en espacio de camara, dolly en direccion de vista). Para volver atras:
  // restaurar cameraState esferico + updateCameraPosition/setNamedView viejos.
  const targetRef = useRef(new THREE.Vector3(0, 0, 0));
  const dragActionRef = useRef<NavAction>('none');

  const [navProfile, setNavProfile] = useState<NavProfileName>(() => readStoredNavProfile());

  // Perfil del backend (persiste en preferences.json) o localStorage.
  useEffect(() => {
    if (!backend.hasBridge()) return;
    void backend
      .getNavProfiles()
      .then((r) => {
        const cur = (r as { current?: unknown }).current;
        if (r.ok && isNavProfileName(cur)) {
          setNavProfile(cur);
          try {
            localStorage.setItem('topoopt.nav', cur);
          } catch {
            /* sin localStorage */
          }
        }
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const changeNavProfile = (name: NavProfileName) => {
    setNavProfile(name);
    try {
      localStorage.setItem('topoopt.nav', name);
    } catch {
      /* sin localStorage */
    }
    if (backend.hasBridge()) void backend.setNavProfile(name).catch(() => undefined);
  };

  const fitToSurface = useCallback(() => {
    if (!cameraRef.current) return;
    if (surface && surface.positions.length >= 9) {
      const box = new THREE.Box3();
      const v = new THREE.Vector3();
      for (let i = 0; i + 2 < surface.positions.length; i += 3) {
        // ORIENT (reversible): misma rotacion Z-up->Y-up que el render.
        v.set(surface.positions[i], surface.positions[i + 2], -surface.positions[i + 1]);
        box.expandByPoint(v);
      }
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      fitCamera(cameraRef.current, targetRef.current, sphere.center, Math.max(sphere.radius, 1e-6));
    } else {
      targetRef.current.set(0, 0, 0);
      cameraRef.current.position.set(160, 160, 160);
      cameraRef.current.up.set(0, 1, 0);
      cameraRef.current.lookAt(targetRef.current);
    }
  }, [surface]);

  const applyNamedView = useCallback(
    (view: 'iso' | 'top' | 'front' | 'right') => {
      if (!cameraRef.current) return;
      viewCamera(cameraRef.current, targetRef.current, view);
    },
    []
  );

  // React to view presets trigger from header
  useEffect(() => {
    if (selectedViewTrigger.count > 0) {
      applyNamedView(selectedViewTrigger.view);
    }
  }, [selectedViewTrigger, applyNamedView]);

  // React to reset view trigger
  useEffect(() => {
    if (resetViewTrigger > 0) {
      if (surface) fitToSurface();
      else applyNamedView('iso');
    }
  }, [resetViewTrigger, applyNamedView, fitToSurface, surface]);
  // NAV-VIEW-END

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

    // NAV-VIEW (reversible): vista inicial razonable hasta que llegue superficie.
    camera.position.set(160, 160, 160);
    camera.up.set(0, 1, 0);
    camera.lookAt(0, 0, 0);

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
  }, []);

  // NAV-VIEW-START (reversible): render real del STEP importado.
  // Teselacion del core (vertices xyz + indices) -> BufferGeometry three.js.
  // Sin surface: escena vacia. Para volver atras: devolver el stub vacio.
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

    if (!isModelVisible || !surface) return;

    const positions = new Float32Array(surface.positions);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setIndex(surface.indices);
    // ORIENT (reversible): el core CAD es Z-up (como la antecesora, viewUp Z);
    // three.js es Y-up: rotar -90° en X para ver la pieza en su orientacion.
    // Para volver atras: quitar esta linea + el mapeo en fitToSurface.
    geo.rotateX(-Math.PI / 2);
    geo.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(selectedMaterial.color),
      metalness: 0.55,
      roughness: 0.4,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geo, mat);
    modelGroup.add(mesh);

    if (showMesh) {
      const wireGeo = new THREE.WireframeGeometry(geo);
      const wireMat = new THREE.LineBasicMaterial({
        color: 0x7bd0ff,
        transparent: true,
        opacity: 0.35,
      });
      modelGroup.add(new THREE.LineSegments(wireGeo, wireMat));
    }

    if (showSection && clipPlaneRef.current) {
      mat.clippingPlanes = [clipPlaneRef.current];
    }

    fitToSurface();
  }, [surface, isModelVisible, selectedMaterial, showMesh, showSection, fitToSurface]);
  // NAV-VIEW-END

  // Handle Mouse / Pointer Events for Orbiting, Panning, and Coordinate Inspection
  // (UI-CLEAN: aqui habia ~200 lineas de geometria demo + glifos + el
  // cierre del efecto viejo; eliminadas. Ver git para restaurar.)

  // NAV-VIEW-START (reversible): input por perfiles como NavigationManager.
  // left/middle/right (+shift) -> orbit/pan segun perfil; wheel = dolly
  // (arriba acerca); doble-clic y f/n/. = fit. Para volver atras: restaurar
  // handlers viejos (ver git).
  const dragState = useRef({ dragging: false, lastX: 0, lastY: 0 });

  const resolveDragAction = (button: number, shift: boolean): NavAction => {
    const p = NAV_PROFILES[navProfile];
    if (button === 0) return 'none'; // select en los 4 perfiles: sin arrastre
    if (button === 1) return shift ? p.shiftMiddle : p.middle; // orbit|pan
    if (button === 2) {
      if (p.right === 'orbit' || p.right === 'pan') return p.right;
      return 'none'; // menu: sin arrastre 3D
    }
    return 'none';
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragState.current = { dragging: true, lastX: e.clientX, lastY: e.clientY };
    dragActionRef.current = resolveDragAction(e.button, e.shiftKey);
    setIsOrbiting(dragActionRef.current === 'orbit');
    setIsPanning(dragActionRef.current === 'pan');
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

    if (!dragState.current.dragging || !cameraRef.current) return;
    const dx = e.clientX - dragState.current.lastX;
    const dy = e.clientY - dragState.current.lastY;
    dragState.current.lastX = e.clientX;
    dragState.current.lastY = e.clientY;
    if (dx === 0 && dy === 0) return;

    if (dragActionRef.current === 'orbit') {
      orbitCamera(cameraRef.current, targetRef.current, dx, dy);
    } else if (dragActionRef.current === 'pan') {
      panCamera(cameraRef.current, targetRef.current, dx, dy);
    }
  };

  const handleMouseUp = () => {
    dragState.current.dragging = false;
    dragActionRef.current = 'none';
    setIsOrbiting(false);
    setIsPanning(false);
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (!cameraRef.current) return;
    // Rueda arriba (deltaY<0) = steps>0 = acercar (dolly de la predecesora).
    const steps = -e.deltaY / 100;
    dollyCamera(cameraRef.current, targetRef.current, steps);
  };

  const handleDoubleClick = () => {
    fitToSurface();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const k = e.key.toLowerCase();
    if (NAV_PROFILES[navProfile].fitKeys.includes(k)) fitToSurface();
  };
  // NAV-VIEW-END

  return (
    <main
      ref={containerRef}
      id="cad-viewport-container"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      onDoubleClick={handleDoubleClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      // NAV-VIEW (reversible): el clic derecho puede orbitar segun perfil.
      onContextMenu={(e) => e.preventDefault()}
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
                applyNamedView('top');
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
                applyNamedView('front');
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
                applyNamedView('right');
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
                applyNamedView('iso');
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
                fitToSurface();
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
            onClick={() => fitToSurface()}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container-high text-text-secondary hover:text-text-primary transition-colors"
            title="Ajustar Zoom (Fit)"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">center_focus_strong</span>
          </button>
          <button
            onClick={() => applyNamedView('iso')}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container-high text-text-secondary hover:text-text-primary transition-colors"
            title="Rotar Órbita CAD"
            type="button"
          >
            <span className="material-symbols-outlined text-[16px]">3d_rotation</span>
          </button>
          <button
            onClick={() => {
              // NAV-VIEW (reversible): centrar = fit a la pieza real.
              fitToSurface();
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
          {/* NAV-VIEW-START (reversible): selector de perfil de navegacion de
              la predecesora (persiste en backend + localStorage). Para volver
              atras: borrar este select. */}
          <select
            aria-label="Perfil de navegación"
            value={navProfile}
            onChange={(e) => {
              const v = e.target.value;
              if (isNavProfileName(v)) changeNavProfile(v);
            }}
            onMouseDown={(e) => e.stopPropagation()}
            className="pointer-events-auto bg-surface-elevated border border-border-subtle/50 rounded px-1 py-0.5 text-[10px] font-mono text-text-primary outline-none"
          >
            {(Object.keys(NAV_PROFILES) as NavProfileName[]).map((n) => (
              <option key={n} value={n}>
                {NAV_PROFILES[n].displayName}
              </option>
            ))}
          </select>
          {/* NAV-VIEW-END */}
        </div>
      </div>
    </main>
  );
};
