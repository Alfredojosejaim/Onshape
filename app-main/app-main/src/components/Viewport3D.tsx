import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import {
  SurfaceMeshData,
  ScalarField,
  DomainDimensions,
  LoadCondition,
  BoundaryCondition,
  DesignDomainPreset,
  ActiveTool,
  ProtectedFace,
  ObstacleZone
} from '../types';
import {
  Layers,
  Eye,
  Maximize2,
  Minimize2,
  RotateCcw,
  Compass,
  Box,
  SplitSquareVertical,
  Sliders,
  ShieldCheck,
  Ban,
  ArrowDownCircle
} from 'lucide-react';

interface Viewport3DProps {
  meshData: SurfaceMeshData | null;
  dimensions: DomainDimensions;
  preset: DesignDomainPreset;
  field: ScalarField;
  showWireframe: boolean;
  showBounds: boolean;
  showGlyphs: boolean;
  clipPlaneRatio: number; // 0.1 to 1.0
  densityThreshold: number;
  onClipPlaneChange: (val: number) => void;
  onThresholdChange: (val: number) => void;
  onFieldChange: (field: ScalarField) => void;
  activeTool?: ActiveTool;
  loadMagnitude?: number;
  loadDirection?: [number, number, number];
  protectedFaces?: ProtectedFace[];
  obstacleZones?: ObstacleZone[];
}

// Turbo / Jet colormap function for FEA stress and scalar visualization
function getColormapRgb(t: number): [number, number, number] {
  // Clamped 0..1
  const s = Math.max(0, Math.min(1, t));
  // Smooth rainbow: Blue (0) -> Cyan (0.25) -> Green (0.5) -> Yellow (0.75) -> Red (1.0)
  let r = 0, g = 0, b = 0;
  if (s < 0.25) {
    const f = s / 0.25;
    r = 0.1;
    g = 0.2 + 0.6 * f;
    b = 0.8 + 0.2 * (1 - f);
  } else if (s < 0.5) {
    const f = (s - 0.25) / 0.25;
    r = 0.1 + 0.2 * f;
    g = 0.8 + 0.2 * f;
    b = 0.8 * (1 - f);
  } else if (s < 0.75) {
    const f = (s - 0.5) / 0.25;
    r = 0.3 + 0.7 * f;
    g = 0.95 * (1 - f * 0.3);
    b = 0.05;
  } else {
    const f = (s - 0.75) / 0.25;
    r = 1.0;
    g = 0.65 * (1 - f);
    b = 0.05;
  }
  return [r, g, b];
}

export const Viewport3D: React.FC<Viewport3DProps> = ({
  meshData,
  dimensions,
  preset,
  field,
  showWireframe,
  showBounds,
  showGlyphs,
  clipPlaneRatio,
  densityThreshold,
  onClipPlaneChange,
  onThresholdChange,
  onFieldChange,
  activeTool,
  loadMagnitude,
  loadDirection,
  protectedFaces,
  obstacleZones
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const meshObjectRef = useRef<THREE.Mesh | null>(null);
  const wireframeMeshRef = useRef<THREE.LineSegments | null>(null);
  const glyphsGroupRef = useRef<THREE.Group | null>(null);
  const boundsBoxRef = useRef<THREE.LineSegments | null>(null);
  const clipPlaneRef = useRef<THREE.Plane | null>(null);

  const [isFullscreen, setIsFullscreen] = useState(false);
  const isDraggingRef = useRef(false);
  const previousMousePosition = useRef({ x: 0, y: 0 });
  const cameraTarget = useRef(new THREE.Vector3(0, 0, 0));

  // Initialize Three.js Scene
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0c0f17); // Sleek modern dark engineering background
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 3000);
    camera.position.set(160, 110, 180);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.localClippingEnabled = true;
    rendererRef.current = renderer;

    container.appendChild(renderer.domElement);

    // Subtle technical grid
    const grid = new THREE.GridHelper(300, 30, 0x1e293b, 0x0f172a);
    grid.position.y = -dimensions.height / 2 - 2;
    scene.add(grid);

    // Clipping plane setup
    const clipPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), dimensions.length / 2);
    clipPlaneRef.current = clipPlane;

    // Ambient and directional lighting for PBR depth
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.3);
    keyLight.position.set(150, 200, 150);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x90cdf4, 0.7);
    fillLight.position.set(-150, -100, -150);
    scene.add(fillLight);

    const topLight = new THREE.DirectionalLight(0xffedd5, 0.5);
    topLight.position.set(0, 250, 0);
    scene.add(topLight);

    // Resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width === 0 || height === 0) return;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
      }
    });
    resizeObserver.observe(container);

    // Animation render loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      if (renderer.domElement.parentElement) {
        renderer.domElement.parentElement.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update Geometry & Colors when meshData or field changes
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !meshData || meshData.positions.length === 0) return;

    // Remove old mesh
    if (meshObjectRef.current) {
      scene.remove(meshObjectRef.current);
      meshObjectRef.current.geometry.dispose();
      (meshObjectRef.current.material as THREE.Material).dispose();
      meshObjectRef.current = null;
    }
    if (wireframeMeshRef.current) {
      scene.remove(wireframeMeshRef.current);
      wireframeMeshRef.current.geometry.dispose();
      wireframeMeshRef.current = null;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(meshData.positions, 3));
    geometry.setIndex(new THREE.BufferAttribute(meshData.indices, 1));
    geometry.computeVertexNormals();

    // Compute vertex colors from scalar field
    const numVertices = meshData.positions.length / 3;
    const colors = new Float32Array(numVertices * 3);
    const minVal = meshData.minVal ?? 0;
    const maxVal = meshData.maxVal ?? 1;
    const range = Math.max(1e-6, maxVal - minVal);

    for (let i = 0; i < numVertices; i++) {
      let normVal = 0.5;
      if (meshData.values && meshData.values.length > i) {
        normVal = (meshData.values[i] - minVal) / range;
      }

      if (field === 'none') {
        // Metallic CAD engineering finish
        colors[i * 3] = 0.76;
        colors[i * 3 + 1] = 0.82;
        colors[i * 3 + 2] = 0.88;
      } else {
        const [r, g, b] = getColormapRgb(normVal);
        colors[i * 3] = r;
        colors[i * 3 + 1] = g;
        colors[i * 3 + 2] = b;
      }
    }
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Material with smooth shading and clipping plane support
    const material = new THREE.MeshStandardMaterial({
      vertexColors: true,
      metalness: field === 'none' ? 0.65 : 0.25,
      roughness: field === 'none' ? 0.35 : 0.45,
      side: THREE.DoubleSide,
      clippingPlanes: clipPlaneRatio < 0.99 && clipPlaneRef.current ? [clipPlaneRef.current] : [],
      clipShadows: true
    });

    const mesh = new THREE.Mesh(geometry, material);
    meshObjectRef.current = mesh;
    scene.add(mesh);

    // Wireframe overlay
    if (showWireframe) {
      const wireGeometry = new THREE.WireframeGeometry(geometry);
      const wireMaterial = new THREE.LineBasicMaterial({
        color: 0x334155,
        transparent: true,
        opacity: 0.35
      });
      const wireframe = new THREE.LineSegments(wireGeometry, wireMaterial);
      wireframeMeshRef.current = wireframe;
      scene.add(wireframe);
    }
  }, [meshData, field, showWireframe, clipPlaneRatio]);

  // Update Clipping Plane position
  useEffect(() => {
    if (!clipPlaneRef.current) return;
    const halfL = dimensions.length / 2;
    // Map ratio 0.1..1.0 to plane constant -halfL..halfL
    const cutPos = -halfL + dimensions.length * clipPlaneRatio;
    clipPlaneRef.current.constant = cutPos;

    if (meshObjectRef.current) {
      const mat = meshObjectRef.current.material as THREE.MeshStandardMaterial;
      if (clipPlaneRatio < 0.99) {
        mat.clippingPlanes = [clipPlaneRef.current];
      } else {
        mat.clippingPlanes = [];
      }
      mat.needsUpdate = true;
    }
  }, [clipPlaneRatio, dimensions.length]);

  // Update Bounding Box and Glyphs (Supports & Loads)
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    // Bounds box
    if (boundsBoxRef.current) {
      scene.remove(boundsBoxRef.current);
      boundsBoxRef.current.geometry.dispose();
      boundsBoxRef.current = null;
    }

    if (showBounds) {
      const boxGeo = new THREE.BoxGeometry(dimensions.length, dimensions.height, dimensions.width);
      const edges = new THREE.EdgesGeometry(boxGeo);
      const line = new THREE.LineSegments(
        edges,
        new THREE.LineDashedMaterial({
          color: 0x0ea5e9,
          dashSize: 3,
          gapSize: 2,
          transparent: true,
          opacity: 0.4
        })
      );
      line.computeLineDistances();
      boundsBoxRef.current = line;
      scene.add(line);
    }

    // Glyphs (Supports & Loads)
    if (glyphsGroupRef.current) {
      scene.remove(glyphsGroupRef.current);
      glyphsGroupRef.current = null;
    }

    if (showGlyphs) {
      const glyphGroup = new THREE.Group();
      const halfX = dimensions.length / 2;
      const halfY = dimensions.height / 2;
      const halfZ = dimensions.width / 2;

      // 1. Supports (Green Cones / Triangles)
      const supportMat = new THREE.MeshStandardMaterial({
        color: 0x10b981,
        metalness: 0.3,
        roughness: 0.3
      });

      if (preset === 'cantilever') {
        // Fixed left wall: 4 cones along X = -halfX
        for (let y of [-halfY * 0.7, 0, halfY * 0.7]) {
          for (let z of [-halfZ * 0.6, halfZ * 0.6]) {
            const cone = new THREE.Mesh(new THREE.ConeGeometry(3.5, 9, 8), supportMat);
            cone.position.set(-halfX - 4.5, y, z);
            cone.rotation.z = -Math.PI / 2;
            glyphGroup.add(cone);
          }
        }
      } else if (preset === 'mbb_beam' || preset === 'bridge') {
        // Bottom supports
        for (let x of [-halfX + 4, halfX - 4]) {
          for (let z of [-halfZ * 0.5, halfZ * 0.5]) {
            const cone = new THREE.Mesh(new THREE.ConeGeometry(3.5, 9, 8), supportMat);
            cone.position.set(x, -halfY - 4.5, z);
            cone.rotation.z = Math.PI;
            glyphGroup.add(cone);
          }
        }
      } else if (preset === 'l_bracket') {
        // Top edge support
        for (let x of [-halfX * 0.8, -halfX * 0.3]) {
          const cone = new THREE.Mesh(new THREE.ConeGeometry(3.5, 9, 8), supportMat);
          cone.position.set(x, halfY + 4.5, 0);
          glyphGroup.add(cone);
        }
      }

      // 2. Applied Force / Load (Vibrant Red Arrow)
      let arrowPos = new THREE.Vector3(halfX, -halfY + 3, 0);
      let arrowDir = new THREE.Vector3(0, -1, 0);

      if (preset === 'mbb_beam') {
        arrowPos = new THREE.Vector3(0, halfY + 14, 0);
        arrowDir = new THREE.Vector3(0, -1, 0);
      } else if (preset === 'l_bracket') {
        arrowPos = new THREE.Vector3(halfX, -halfY * 0.5, 0);
        arrowDir = new THREE.Vector3(0, -1, 0);
      }

      if (loadDirection) {
        arrowDir = new THREE.Vector3(loadDirection[0], loadDirection[1], loadDirection[2]).normalize();
      }

      const arrowLength = Math.max(16, Math.min(32, 16 + ((loadMagnitude || 10000) / 50000) * 14));
      const arrowColor = activeTool === 'carga' ? 0xff0055 : 0xef4444;
      const arrowHelper = new THREE.ArrowHelper(arrowDir, arrowPos, arrowLength, arrowColor, 7, 5);
      glyphGroup.add(arrowHelper);

      // 3. Protected Faces (Caras Protegidas - Non-design solid boundaries)
      if (protectedFaces) {
        protectedFaces.filter(f => f.enabled).forEach(face => {
          const [xMin, yMin, zMin, xMax, yMax, zMax] = face.bounds;
          const boxW = Math.max(1, (xMax - xMin) * dimensions.length);
          const boxH = Math.max(1, (yMax - yMin) * dimensions.height);
          const boxD = Math.max(1, (zMax - zMin) * dimensions.width);

          const posX = -halfX + (xMin + xMax) * 0.5 * dimensions.length;
          const posY = -halfY + (yMin + yMax) * 0.5 * dimensions.height;
          const posZ = -halfZ + (zMin + zMax) * 0.5 * dimensions.width;

          const isToolActive = activeTool === 'protegida';
          const faceGeo = new THREE.BoxGeometry(boxW, boxH, boxD);
          const faceMat = new THREE.MeshStandardMaterial({
            color: isToolActive ? 0x10b981 : 0x059669,
            transparent: true,
            opacity: isToolActive ? 0.75 : 0.45,
            metalness: 0.5,
            roughness: 0.3
          });
          const faceMesh = new THREE.Mesh(faceGeo, faceMat);
          faceMesh.position.set(posX, posY, posZ);
          glyphGroup.add(faceMesh);

          // Add glowing green wireframe boundary
          const wireEdges = new THREE.EdgesGeometry(faceGeo);
          const wireLine = new THREE.LineSegments(
            wireEdges,
            new THREE.LineBasicMaterial({ color: 0x34d399, linewidth: 2 })
          );
          wireLine.position.set(posX, posY, posZ);
          glyphGroup.add(wireLine);
        });
      }

      // 4. Obstacle Zones (Zonas de Obstrucción - Keep-out exclusion voids)
      if (obstacleZones) {
        obstacleZones.filter(o => o.enabled).forEach(obs => {
          const [xMin, yMin, zMin, xMax, yMax, zMax] = obs.bounds;
          const boxW = Math.max(1, (xMax - xMin) * dimensions.length);
          const boxH = Math.max(1, (yMax - yMin) * dimensions.height);
          const boxD = Math.max(1, (zMax - zMin) * dimensions.width);

          const posX = -halfX + (xMin + xMax) * 0.5 * dimensions.length;
          const posY = -halfY + (yMin + yMax) * 0.5 * dimensions.height;
          const posZ = -halfZ + (zMin + zMax) * 0.5 * dimensions.width;

          const isToolActive = activeTool === 'obstrucciones';
          let obsMesh: THREE.Mesh;

          if (obs.shape === 'cylinder') {
            const radius = Math.min(boxW, boxH) * 0.5;
            const cylGeo = new THREE.CylinderGeometry(radius, radius, boxD, 16);
            cylGeo.rotateX(Math.PI / 2);
            const cylMat = new THREE.MeshStandardMaterial({
              color: isToolActive ? 0xf59e0b : 0xd97706,
              transparent: true,
              opacity: isToolActive ? 0.7 : 0.4,
              metalness: 0.3,
              roughness: 0.6
            });
            obsMesh = new THREE.Mesh(cylGeo, cylMat);
          } else {
            const boxGeo = new THREE.BoxGeometry(boxW, boxH, boxD);
            const boxMat = new THREE.MeshStandardMaterial({
              color: isToolActive ? 0xf59e0b : 0xd97706,
              transparent: true,
              opacity: isToolActive ? 0.65 : 0.35,
              metalness: 0.3,
              roughness: 0.6
            });
            obsMesh = new THREE.Mesh(boxGeo, boxMat);
          }

          obsMesh.position.set(posX, posY, posZ);
          glyphGroup.add(obsMesh);

          // Add warning edge outline
          const obsEdges = new THREE.EdgesGeometry(obsMesh.geometry);
          const obsWire = new THREE.LineSegments(
            obsEdges,
            new THREE.LineBasicMaterial({ color: 0xfbbf24 })
          );
          obsWire.position.set(posX, posY, posZ);
          glyphGroup.add(obsWire);
        });
      }

      glyphsGroupRef.current = glyphGroup;
      scene.add(glyphGroup);
    }
  }, [showBounds, showGlyphs, dimensions, preset, activeTool, loadMagnitude, loadDirection, protectedFaces, obstacleZones]);

  // Mouse Orbit, Pan, and Zoom interaction
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    previousMousePosition.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current || !cameraRef.current) return;
    const deltaX = e.clientX - previousMousePosition.current.x;
    const deltaY = e.clientY - previousMousePosition.current.y;
    previousMousePosition.current = { x: e.clientX, y: e.clientY };

    const camera = cameraRef.current;

    // Right-click or Shift+Left-click: PAN
    if (e.buttons === 2 || e.shiftKey) {
      const panSpeed = 0.25;
      const right = new THREE.Vector3();
      const up = new THREE.Vector3();
      camera.matrix.extractBasis(right, up, new THREE.Vector3());

      camera.position.addScaledVector(right, -deltaX * panSpeed);
      camera.position.addScaledVector(up, deltaY * panSpeed);
      cameraTarget.current.addScaledVector(right, -deltaX * panSpeed);
      cameraTarget.current.addScaledVector(up, deltaY * panSpeed);
      camera.lookAt(cameraTarget.current);
    } else {
      // Left-click: ORBIT around target
      const spherical = new THREE.Spherical();
      const offset = new THREE.Vector3().subVectors(camera.position, cameraTarget.current);
      spherical.setFromVector3(offset);

      spherical.theta -= deltaX * 0.008;
      spherical.phi = Math.max(0.05, Math.min(Math.PI - 0.05, spherical.phi - deltaY * 0.008));

      offset.setFromSpherical(spherical);
      camera.position.copy(cameraTarget.current).add(offset);
      camera.lookAt(cameraTarget.current);
    }
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (!cameraRef.current) return;
    const camera = cameraRef.current;
    const zoomFactor = e.deltaY > 0 ? 1.08 : 0.92;

    const offset = new THREE.Vector3().subVectors(camera.position, cameraTarget.current);
    offset.multiplyScalar(zoomFactor);
    if (offset.length() > 20 && offset.length() < 1200) {
      camera.position.copy(cameraTarget.current).add(offset);
      camera.lookAt(cameraTarget.current);
    }
  };

  const setViewOrientation = (type: 'iso' | 'front' | 'top' | 'right') => {
    if (!cameraRef.current) return;
    const camera = cameraRef.current;
    const dist = 220;
    cameraTarget.current.set(0, 0, 0);

    if (type === 'iso') {
      camera.position.set(dist * 0.7, dist * 0.6, dist * 0.8);
    } else if (type === 'front') {
      camera.position.set(0, 0, dist);
    } else if (type === 'top') {
      camera.position.set(0, dist, 0.001);
    } else if (type === 'right') {
      camera.position.set(dist, 0, 0);
    }
    camera.lookAt(cameraTarget.current);
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch((err) => console.error(err));
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch((err) => console.error(err));
      setIsFullscreen(false);
    }
  };

  // Min / Max display values for legend
  const minLegend = meshData?.minVal !== undefined ? meshData.minVal.toFixed(1) : '0.0';
  const maxLegend = meshData?.maxVal !== undefined ? meshData.maxVal.toFixed(1) : '1.0';
  const unitLabel = field === 'vonmises' ? 'MPa' : field === 'displacement' ? 'mm' : 'ρ (0..1)';

  return (
    <div
      ref={containerRef}
      id="viewport-3d-container"
      className="relative w-full h-full min-h-[420px] bg-slate-950 overflow-hidden select-none cursor-grab active:cursor-grabbing border border-slate-800 rounded-lg shadow-inner"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
      onContextMenu={(e) => e.preventDefault()}
    >
      {/* Top Viewport Toolbar */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-1.5 bg-slate-900/85 backdrop-blur-md px-2.5 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-300 shadow-md">
        <span className="font-semibold text-sky-400 mr-1 flex items-center gap-1">
          <Compass className="w-3.5 h-3.5" /> Vistas:
        </span>
        <button
          onClick={() => setViewOrientation('iso')}
          className="px-2 py-0.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors cursor-pointer"
          title="Vista Isométrica 3D"
        >
          ISO
        </button>
        <button
          onClick={() => setViewOrientation('front')}
          className="px-2 py-0.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors cursor-pointer"
          title="Vista Frontal (XY)"
        >
          Frontal
        </button>
        <button
          onClick={() => setViewOrientation('top')}
          className="px-2 py-0.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors cursor-pointer"
          title="Vista Superior (XZ)"
        >
          Superior
        </button>
        <button
          onClick={() => setViewOrientation('right')}
          className="px-2 py-0.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors cursor-pointer"
          title="Vista Lateral (YZ)"
        >
          Lateral
        </button>
        <div className="w-px h-4 bg-slate-700 mx-1" />
        <button
          onClick={() => setViewOrientation('iso')}
          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
          title="Centrar y reajustar cámara"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Top Right Controls & Field Switcher */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
        {/* Field Selector */}
        <div className="flex bg-slate-900/90 backdrop-blur-md p-1 rounded-lg border border-slate-800 text-xs shadow-md">
          <button
            onClick={() => onFieldChange('density')}
            className={`px-2.5 py-1 rounded transition-colors font-medium cursor-pointer ${
              field === 'density' ? 'bg-sky-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Densidad ρ
          </button>
          <button
            onClick={() => onFieldChange('vonmises')}
            className={`px-2.5 py-1 rounded transition-colors font-medium cursor-pointer ${
              field === 'vonmises' ? 'bg-amber-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Von Mises
          </button>
          <button
            onClick={() => onFieldChange('displacement')}
            className={`px-2.5 py-1 rounded transition-colors font-medium cursor-pointer ${
              field === 'displacement' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Desplazamiento
          </button>
          <button
            onClick={() => onFieldChange('none')}
            className={`px-2.5 py-1 rounded transition-colors font-medium cursor-pointer ${
              field === 'none' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Sólido CAD
          </button>
        </div>

        {/* Fullscreen */}
        <button
          onClick={toggleFullscreen}
          className="p-2 bg-slate-900/90 backdrop-blur-md rounded-lg border border-slate-800 text-slate-300 hover:text-white transition-colors cursor-pointer shadow-md"
          title="Pantalla Completa"
        >
          {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>
      </div>

      {/* Scalar Legend (Right side when scalar field is active) */}
      {field !== 'none' && (
        <div className="absolute right-3 top-16 z-10 flex flex-col items-center bg-slate-900/85 backdrop-blur-md p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-300 shadow-lg">
          <span className="font-semibold text-slate-200 mb-1">{field === 'vonmises' ? 'Tensión' : field === 'displacement' ? 'Desp.' : 'Densidad'}</span>
          <span className="text-[10px] text-slate-400 mb-1.5">{unitLabel}</span>
          <span className="text-red-400 font-mono font-bold mb-1">{maxLegend}</span>
          {/* Color gradient bar */}
          <div
            className="w-4 h-32 rounded border border-slate-700 shadow-inner"
            style={{
              background: 'linear-gradient(to bottom, #ef4444, #f59e0b, #10b981, #06b6d4, #3b82f6)'
            }}
          />
          <span className="text-blue-400 font-mono font-bold mt-1">{minLegend}</span>
        </div>
      )}

      {/* Bottom Interactive Sliders: Density Iso-Cut and Cross-Section Cut Plane */}
      <div className="absolute bottom-3 left-3 right-3 z-10 flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 backdrop-blur-md px-4 py-2.5 rounded-lg border border-slate-800 text-xs text-slate-300 shadow-lg">
        {/* Left: Density Threshold Iso-surface */}
        <div className="flex items-center gap-2.5">
          <span className="font-medium text-slate-300 flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-sky-400" />
            Umbral de Densidad (ρ):
          </span>
          <input
            type="range"
            min="0.10"
            max="0.80"
            step="0.02"
            value={densityThreshold}
            onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
            className="w-28 accent-sky-500 cursor-pointer"
          />
          <span className="font-mono text-sky-400 font-semibold w-9 text-right">
            {(densityThreshold * 100).toFixed(0)}%
          </span>
        </div>

        {/* Center: Cross-Section Cutting Plane */}
        <div className="flex items-center gap-2.5">
          <span className="font-medium text-slate-300 flex items-center gap-1.5">
            <SplitSquareVertical className="w-3.5 h-3.5 text-amber-400" />
            Corte Transversal (Plano X):
          </span>
          <input
            type="range"
            min="0.2"
            max="1.0"
            step="0.02"
            value={clipPlaneRatio}
            onChange={(e) => onClipPlaneChange(parseFloat(e.target.value))}
            className="w-28 accent-amber-500 cursor-pointer"
          />
          <span className="font-mono text-amber-400 font-semibold w-9 text-right">
            {(clipPlaneRatio * 100).toFixed(0)}%
          </span>
        </div>

        {/* Right: Quick Instructions */}
        <div className="text-[11px] text-slate-400 hidden md:block">
          <span className="text-slate-300 font-medium">Arrastrar:</span> Orbitar • <span className="text-slate-300 font-medium">Rueda:</span> Zoom • <span className="text-slate-300 font-medium">Shift + Click:</span> Panorámica
        </div>
      </div>
    </div>
  );
};
