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
// FACES-START (reversible: quitar import + props selectedFaces/onToggleFace/
// facePickEnabled + refs/efectos marcados FACES)
// Copia del picking del desktop: raycast -> triangulo -> cara B-Rep via
// rangos face_triangles (viewport_3d.resolve_pick_entity + scene), toggle
// como software_viewport y resaltado naranja como highlight.py.
import { rangesCover, solidTriangles, triangleToFace } from '../lib/faces';
// MULTI-VIEW-START (reversible: quitar import + props surfaces/bodies/
// activeFilename/hiddenBodies/meshByFile + efecto multi-cuerpo).
// Todos los cuerpos importados en un solo viewport, con ver/ocultar por
// cuerpo (split de la malla por solido via face_indices del core).
import type { ViewBody } from '../types';
// MULTI-VIEW-END
// FACES-END
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
  // MULTI-VIEW (reversible): todas las superficies + cuerpos del viewport
  // unico. null/vacio = escena vacia. Para volver atras: prop surface unica.
  surfaces: Record<string, RealSurface>;
  bodies: ViewBody[];
  activeFilename: string | null;
  hiddenBodies: Record<string, boolean>;
  meshByFile: Record<string, boolean>;
  // FACES (reversible): caras seleccionadas + picking por cara.
  selectedFaces: number[];
  onToggleFace: (faceIndex: number) => void;
  facePickEnabled: boolean;
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
  // MULTI-VIEW (reversible)
  surfaces,
  bodies,
  activeFilename,
  hiddenBodies,
  meshByFile,
  // FACES (reversible)
  selectedFaces,
  onToggleFace,
  facePickEnabled,
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
  // PLANES-VIS (reversible): refs a los 4 planos en el 0 absoluto para
  // ver/ocultar uno por uno o todos. Para volver atras: borrar ref + estado
  // + efecto + panel.
  const planesRef = useRef<{
    xy: THREE.GridHelper | null;
    xz: THREE.GridHelper | null;
    yz: THREE.GridHelper | null;
  }>({ xy: null, xz: null, yz: null });
  // MULTI-VIEW (reversible): mallas por cuerpo (raycast solo en el activo).
  // userData: {key, filename, triMap: nº triangulo global por triangulo local}.
  const bodyMeshesRef = useRef<THREE.Mesh[]>([]);
  const highlightRef = useRef<THREE.Mesh | null>(null);
  // STABILITY-FIX (reversible): firma de los cuerpos encuadrados. El efecto
  // reconstruye por material/malla/visibilidad sin mover la camara; solo se
  // reencuadra si cambia el conjunto de cuerpos o el modelo activo.
  // Para volver atras: borrar ref + bloque FIT-ONCE y restaurar fitToAll().
  const fitKeysRef = useRef<string>('');

  const [isOrbiting, setIsOrbiting] = useState(false);
  const [isPanning, setIsPanning] = useState(false);
  const [isOrthographic, setIsOrthographic] = useState(false);
  const [measurePoint, setMeasurePoint] = useState<string | null>(null);
  // PLANES-VIS (reversible): visibilidad por plano + todos.
  const [visiblePlanes, setVisiblePlanes] = useState({ xy: true, xz: true, yz: true });
  // BLACKSCREEN-FIX: si WebGL no esta disponible, se muestra el motivo en
  // vez de un viewport negro silencioso.
  const [webglError, setWebglError] = useState<string | null>(null);

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

  // MULTI-VIEW (reversible): encuadra TODAS las superficies visibles del
  // viewport unico (antes: solo la del modelo activo). Para volver atras:
  // restaurar fitToSurface de una superficie.
  const fitToAll = useCallback(() => {
    if (!cameraRef.current) return;
    const box = new THREE.Box3();
    const v = new THREE.Vector3();
    let found = false;
    for (const [filename, surf] of Object.entries(surfaces) as [string, RealSurface][]) {
      const anyVisible = bodies.some(
        (b) => b.filename === filename && !hiddenBodies[b.key],
      );
      if (!anyVisible || surf.positions.length < 9) continue;
      for (let i = 0; i + 2 < surf.positions.length; i += 3) {
        // BLACKSCREEN-GUARD: ignora coordenadas no finitas (NaN/Infinity del
        // backend) para no contaminar el bounding box y ennegrecer la escena.
        const x = surf.positions[i];
        const y = surf.positions[i + 2];
        const z = -surf.positions[i + 1];
        if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) continue;
        // ORIENT (reversible): misma rotacion Z-up->Y-up que el render.
        v.set(x, y, z);
        box.expandByPoint(v);
      }
      found = true;
    }
    if (found && !box.isEmpty()) {
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      if (!Number.isFinite(sphere.center.x) || !Number.isFinite(sphere.center.y) ||
          !Number.isFinite(sphere.center.z) || !Number.isFinite(sphere.radius)) {
        return;
      }
      fitCamera(cameraRef.current, targetRef.current, sphere.center, Math.max(sphere.radius, 1e-6));
    } else {
      targetRef.current.set(0, 0, 0);
      cameraRef.current.position.set(160, 160, 160);
      cameraRef.current.up.set(0, 1, 0);
      cameraRef.current.lookAt(targetRef.current);
    }
  }, [surfaces, bodies, hiddenBodies]);

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
      if (Object.keys(surfaces).length > 0) fitToAll();
      else applyNamedView('iso');
    }
  }, [resetViewTrigger, applyNamedView, fitToAll, surfaces]);
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
    // ZERO-PLANES (reversible): corte en el 0 absoluto (z=0). Antes constant=10
    // (plano en z=10). Para volver atras: constant 10.
    const clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);
    clipPlaneRef.current = clipPlane;

    // Main Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 2000);
    cameraRef.current = camera;

    // Main Renderer
    // BLACKSCREEN-FIX: si la creacion del contexto WebGL falla (drivers,
    // WebView2 sin GPU), antes el efecto lanzaba y el canvas quedaba negro.
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error('[viewport] WebGL no disponible:', msg);
      setWebglError(msg);
      return;
    }
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.localClippingEnabled = true;
    rendererRef.current = renderer;
    container.appendChild(renderer.domElement);

    // GRID-REMOVED (reversible): rejilla de proyecto eliminada — los 3
    // planos ya aportan el estilo rejilla en el 0. Para volver atras:
    // restaurar el bloque GridHelper(260, 26) en y=0.
    // Coordinate Planes visualizers (los 3 en el 0 absoluto: XY z=0, XZ y=0,
    // YZ x=0). ZERO-PLANES: antes solo existia el XY. Para volver atras:
    // borrar planeXZ y planeYZ.
    const planeXY = new THREE.GridHelper(120, 12, 0xef4444, 0x272a33);
    planeXY.rotation.x = Math.PI / 2;
    planeXY.position.set(0, 0, 0);
    (planeXY.material as THREE.Material).opacity = 0.15;
    (planeXY.material as THREE.Material).transparent = true;
    scene.add(planeXY);
    planesRef.current.xy = planeXY;

    const planeXZ = new THREE.GridHelper(120, 12, 0x10b981, 0x272a33);
    planeXZ.position.set(0, 0, 0);
    (planeXZ.material as THREE.Material).opacity = 0.15;
    (planeXZ.material as THREE.Material).transparent = true;
    scene.add(planeXZ);
    planesRef.current.xz = planeXZ;

    const planeYZ = new THREE.GridHelper(120, 12, 0x7bd0ff, 0x272a33);
    planeYZ.rotation.z = Math.PI / 2;
    planeYZ.position.set(0, 0, 0);
    (planeYZ.material as THREE.Material).opacity = 0.15;
    (planeYZ.material as THREE.Material).transparent = true;
    scene.add(planeYZ);
    planesRef.current.yz = planeYZ;

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

  // PLANES-VIS (reversible): aplica la visibilidad a los 3 planos del 0.
  useEffect(() => {
    const p = planesRef.current;
    if (p.xy) p.xy.visible = visiblePlanes.xy;
    if (p.xz) p.xz.visible = visiblePlanes.xz;
    if (p.yz) p.yz.visible = visiblePlanes.yz;
  }, [visiblePlanes]);

  const togglePlane = (key: keyof typeof visiblePlanes) =>
    setVisiblePlanes((p) => ({ ...p, [key]: !p[key] }));
  const toggleAllPlanes = () =>
    setVisiblePlanes((p) => {
      const anyVisible = p.xy || p.xz || p.yz;
      return { ...p, xy: !anyVisible, xz: !anyVisible, yz: !anyVisible };
    });

  // MULTI-VIEW-START (reversible): un mesh por cuerpo de cada archivo en el
  // viewport unico. Split por solido via face_indices (solidTriangles); sin
  // split posible, el archivo va entero. userData.triMap: triangulo global
  // por triangulo local (picking). Para volver atras: efecto single-surface.
  useEffect(() => {
    if (!modelGroupRef.current) return;
    const modelGroup = modelGroupRef.current;

    const disposeObj = (obj: THREE.Object3D) => {
      const mesh = obj as THREE.Mesh;
      if (mesh.geometry) (mesh.geometry as THREE.BufferGeometry).dispose();
      const mat = (mesh as THREE.Mesh).material as THREE.Material | THREE.Material[] | undefined;
      if (Array.isArray(mat)) mat.forEach((mm) => mm.dispose());
      else if (mat) mat.dispose();
    };

    if (!isModelVisible) {
      // Modelo oculto: vaciado intencional (unico caso que vacia a proposito).
      while (modelGroup.children.length > 0) {
        const obj = modelGroup.children[0];
        modelGroup.remove(obj);
        disposeObj(obj);
      }
      bodyMeshesRef.current = [];
      highlightRef.current = null;
      return;
    }

    // BLACKSCREEN-GUARD: si hay cuerpos pero NINGUNO es renderizable
    // (superficie corrupta o aun sin teselado), se conserva la escena
    // anterior en vez de vaciarla: vaciar dejaba el viewport en negro.
    if (bodies.length > 0) {
      const anyRenderable = bodies.some((b) => {
        const s = surfaces[b.filename];
        return !!s && s.positions.length >= 9 && s.indices.length >= 3;
      });
      if (!anyRenderable) {
        console.warn('[viewport] superficie no renderizable, se conserva la escena anterior');
        return;
      }
    }

    // BLACKSCREEN-GUARD: construccion ATOMICA. Antes se vaciaba el grupo y
    // luego se construia: si algo lanzaba a mitad del loop (un cuerpo con
    // datos raros), la escena quedaba vacia = viewport negro. Ahora se
    // construye en un grupo temporal y solo se intercambia si todo salio
    // bien; ante cualquier error se conserva la escena anterior.
    const next = new THREE.Group();
    const nextMeshes: THREE.Mesh[] = [];
    try {

    const baseColor = new THREE.Color(selectedMaterial.color);
    // MULTI-COLOR (reversible): un tono por cuerpo para que 2+ solidos no se
    // vean como "uno solo" aunque compartan material. Para volver atras:
    // usar siempre baseColor / baseColor*0.75.
    const perFileIdx = new Map<string, number>();
    const bodyColor = (body: { filename: string }) => {
      const n = perFileIdx.get(body.filename) ?? 0;
      perFileIdx.set(body.filename, n + 1);
      const c = baseColor.clone();
      if (n > 0) c.offsetHSL((n * 0.09) % 1, 0, n % 2 === 0 ? 0.12 : -0.12);
      // Activo a pleno color, resto atenuado (comportamiento anterior).
      return body.filename === activeFilename ? c : c.multiplyScalar(0.75);
    };
    for (const body of bodies) {
      const surf = surfaces[body.filename];
      if (!surf || surf.positions.length < 9) continue;
      // BLACKSCREEN-GUARD: valida la superficie antes de crear geometria
      // (indices fuera de rango o NaN => se omite ESE cuerpo, no toda la escena).
      const nv = Math.floor(surf.positions.length / 3);
      let valid = true;
      for (let i = 0; i + 2 < surf.positions.length; i += 3) {
        if (!Number.isFinite(surf.positions[i]) || !Number.isFinite(surf.positions[i + 1]) ||
            !Number.isFinite(surf.positions[i + 2])) { valid = false; break; }
      }
      if (valid) {
        for (let i = 0; i < surf.indices.length; i += 1) {
          const idx = surf.indices[i];
          if (!Number.isInteger(idx) || idx < 0 || idx >= nv) { valid = false; break; }
        }
      }
      if (!valid) {
        console.warn(`[viewport] cuerpo omitido por geometria invalida: ${body.key}`);
        continue;
      }
      const tris = solidTriangles(body.faceIndices, surf.ranges, surf.numTriangles);
      if (!tris && bodies.filter((o) => o.filename === body.filename).length > 1) {
        console.warn(
          `[viewport] split por cuerpo no disponible para ${body.key} ` +
          `(rangos incompletos o sin face_indices): se muestra la pieza completa. ` +
          `Solidos backend: ${bodies.filter((o) => o.filename === body.filename).length}`,
        );
      }
      // triMap: triangulo global por triangulo local (identidad si va entero).
      // Los vertices salen de surf.indices (el teselado no es identidad).
      const useTris = tris ?? Array.from({ length: surf.numTriangles }, (_, k) => k);
      const triMap: number[] = useTris;
      const subIndex: number[] = [];
      for (const t of useTris) subIndex.push(surf.indices[t * 3], surf.indices[t * 3 + 1], surf.indices[t * 3 + 2]);
      const positions = new Float32Array(surf.positions);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geo.setIndex(subIndex);
      // ORIENT (reversible): el core CAD es Z-up; three.js es Y-up.
      geo.rotateX(-Math.PI / 2);
      geo.computeVertexNormals();

      const isActive = body.filename === activeFilename;
      const mat = new THREE.MeshStandardMaterial({
        color: bodyColor(body),
        metalness: 0.55,
        roughness: 0.4,
        side: THREE.DoubleSide,
      });
      if (showSection && clipPlaneRef.current) {
        mat.clippingPlanes = [clipPlaneRef.current];
      }
      const mesh = new THREE.Mesh(geo, mat);
      mesh.visible = !hiddenBodies[body.key];
      mesh.userData = { key: body.key, filename: body.filename, triMap };
      next.add(mesh);
      nextMeshes.push(mesh);

      // Fila MALLA del arbol: wireframe del archivo (solo con malla real).
      const meshKey = `${body.filename}::mesh_tet4`;
      if (showMesh && meshByFile[body.filename] && !hiddenBodies[meshKey]) {
        const wireGeo = new THREE.WireframeGeometry(geo);
        const wireMat = new THREE.LineBasicMaterial({
          color: 0x7bd0ff,
          transparent: true,
          opacity: 0.35,
        });
        const wire = new THREE.LineSegments(wireGeo, wireMat);
        wire.visible = mesh.visible;
        next.add(wire);
      }
    }
    } catch (err) {
      console.error('[viewport] fallo construyendo cuerpos, se conserva la escena anterior', err);
      next.traverse((o) => disposeObj(o));
      return;
    }

    // Swap: solo ahora se retira la escena anterior (incluye el overlay
    // naranja viejo, cuya referencia se invalida aqui y no antes).
    while (modelGroup.children.length > 0) {
      const obj = modelGroup.children[0];
      modelGroup.remove(obj);
      disposeObj(obj);
    }
    highlightRef.current = null;
    while (next.children.length > 0) {
      modelGroup.add(next.children[0]);
    }
    bodyMeshesRef.current = nextMeshes;

    // FIT-ONCE (ver STABILITY-FIX arriba): reencuadrar solo si el conjunto
    // de cuerpos o el modelo activo cambio (importar/cambiar de pieza).
    // Cambios de material, malla, seccion o visibilidad reconstruyen sin
    // tocar la camara: antes el fit incondicional devolvia el zoom y
    // hacia parpadear la seleccion (el efecto corria hasta por mousemove).
    const fitSig = `${activeFilename ?? ''}::${bodies.map((b) => b.key).join('|')}`;
    if (fitSig !== fitKeysRef.current) {
      fitKeysRef.current = fitSig;
      fitToAll();
    }
  }, [surfaces, bodies, activeFilename, hiddenBodies, meshByFile, isModelVisible, selectedMaterial, showMesh, showSection, fitToAll]);
  // MULTI-VIEW-END

  // FACES-START (reversible): overlay naranja con las caras seleccionadas
  // del modelo ACTIVO. Para volver atras: borrar el efecto.
  useEffect(() => {
    const group = modelGroupRef.current;
    const activeSurf = activeFilename ? surfaces[activeFilename] : undefined;
    if (!group || !activeSurf) return;
    if (highlightRef.current) {
      group.remove(highlightRef.current);
      highlightRef.current.geometry.dispose();
      highlightRef.current = null;
    }
    if (selectedFaces.length === 0 || !rangesCover(activeSurf.ranges, activeSurf.numTriangles)) return;
    const wanted = new Set(selectedFaces);
    const sub: number[] = [];
    for (const r of activeSurf.ranges) {
      if (!wanted.has(r.face_index)) continue;
      for (let t = r.start; t < r.start + r.count; t += 1) {
        sub.push(activeSurf.indices[t * 3], activeSurf.indices[t * 3 + 1], activeSurf.indices[t * 3 + 2]);
      }
    }
    if (sub.length === 0) return;
    const positions = new Float32Array(activeSurf.positions);
    const hgeo = new THREE.BufferGeometry();
    hgeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    hgeo.setIndex(sub);
    hgeo.rotateX(-Math.PI / 2);
    const hmat = new THREE.MeshBasicMaterial({
      color: 0xffa500, // naranja del highlight del desktop
      transparent: true,
      opacity: 0.55,
      side: THREE.DoubleSide,
      depthTest: true,
      polygonOffset: true,
      polygonOffsetFactor: -2,
    });
    const overlay = new THREE.Mesh(hgeo, hmat);
    overlay.raycast = () => undefined; // el overlay no intercepta picks
    group.add(overlay);
    highlightRef.current = overlay;
    return () => {
      if (highlightRef.current) {
        group.remove(highlightRef.current);
        highlightRef.current.geometry.dispose();
        highlightRef.current = null;
      }
    };
  }, [surfaces, activeFilename, selectedFaces]);
  // FACES-END

  // Handle Mouse / Pointer Events for Orbiting, Panning, and Coordinate Inspection
  // (UI-CLEAN: aqui habia ~200 lineas de geometria demo + glifos + el
  // cierre del efecto viejo; eliminadas. Ver git para restaurar.)

  // NAV-VIEW-START (reversible): input por perfiles como NavigationManager.
  // left/middle/right (+shift) -> orbit/pan segun perfil; wheel = dolly
  // (arriba acerca); doble-clic y f/n/. = fit. Para volver atras: restaurar
  // handlers viejos (ver git).
  const dragState = useRef({ dragging: false, lastX: 0, lastY: 0 });
  // FACES + MULTI-VIEW (reversible): pick en los cuerpos VISIBLES del modelo
  // ACTIVO (raycast -> triangulo local -> global via triMap -> cara B-Rep).
  const downPosRef = useRef<{ x: number; y: number; button: number } | null>(null);
  const pickFace = useCallback(
    (clientX: number, clientY: number) => {
      const container = containerRef.current;
      const camera = cameraRef.current;
      const activeSurf = activeFilename ? surfaces[activeFilename] : undefined;
      if (!container || !camera || !activeSurf) return;
      if (!rangesCover(activeSurf.ranges, activeSurf.numTriangles)) return;
      const targets = bodyMeshesRef.current.filter(
        (m) => m.visible && m.userData.filename === activeFilename,
      );
      if (targets.length === 0) return;
      const rect = container.getBoundingClientRect();
      const ndc = new THREE.Vector2(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        -(((clientY - rect.top) / rect.height) * 2 - 1),
      );
      const ray = new THREE.Raycaster();
      ray.setFromCamera(ndc, camera);
      const hits = ray.intersectObjects(targets, false);
      if (hits.length === 0) return; // vacio: conserva la seleccion
      const hit = hits[0];
      const triMap = (hit.object.userData.triMap ?? []) as number[];
      const localTri = hit.faceIndex;
      if (localTri === undefined || localTri >= triMap.length) return;
      const face = triangleToFace(triMap[localTri], activeSurf.ranges);
      if (face === null) return; // hueco sin cara: conserva la seleccion
      onToggleFace(face);
    },
    [surfaces, activeFilename, onToggleFace],
  );

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
    // FACES (reversible): origen del clic para distinguir pick de arrastre.
    downPosRef.current = { x: e.clientX, y: e.clientY, button: e.button };
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

  const handleMouseUp = (e: React.MouseEvent<HTMLDivElement>) => {
    // FACES-START (reversible): pick por cara con boton izquierdo sin arrastre
    // (como el click del desktop: resolve_pick_entity). Solo con herramienta
    // de entidad y rangos completos; clic en vacio/hueco conserva la seleccion.
    const down = downPosRef.current;
    downPosRef.current = null;
    if (
      down &&
      down.button === 0 &&
      facePickEnabled &&
      Math.hypot(e.clientX - down.x, e.clientY - down.y) < 5
    ) {
      pickFace(e.clientX, e.clientY);
    }
    // FACES-END
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
    fitToAll();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const k = e.key.toLowerCase();
    if (NAV_PROFILES[navProfile].fitKeys.includes(k)) fitToAll();
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
      className="flex-1 min-w-0 flex flex-col relative rounded-lg bg-surface-container-lowest overflow-hidden shadow-2xl min-h-[52dvh] xl:min-h-[580px] cursor-crosshair select-none"
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
                fitToAll();
              }}
              className="hover:text-secondary cursor-pointer"
            >
              FIT
            </span>
            {/* PLANES-VIS (reversible): el selector de perfil vivia en la
                barra de acciones eliminada; se conserva aqui. Para volver
                atras: borrar este select. */}
            <select
              aria-label="Perfil de navegación"
              title="Perfil de navegación"
              value={navProfile}
              onChange={(e) => {
                const v = e.target.value;
                if (isNavProfileName(v)) changeNavProfile(v);
              }}
              onClick={(e) => e.stopPropagation()}
              onMouseDown={(e) => e.stopPropagation()}
              className="bg-transparent hover:text-secondary cursor-pointer text-[9px] font-mono outline-none [&>option]:bg-surface-elevated"
            >
              {(Object.keys(NAV_PROFILES) as NavProfileName[]).map((n) => (
                <option key={n} value={n} title={NAV_PROFILES[n].displayName}>
                  {NAV_PROFILES[n].displayName.slice(0, 2).toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* PLANES-VIS-START (reversible): ver/ocultar planos del 0 absoluto,
            uno por uno y todos. Reemplaza la barra de acciones de camara
            (Fit/orbita/centrar/ortho). Para volver atras: restaurar el bloque
            "Camera Tool Floating Stack" desde git. */}
        <div className="flex flex-col items-stretch gap-0.5 bg-surface-elevated/90 backdrop-blur-md p-1.5 rounded-lg shadow-md border border-border-subtle/50">
          <span className="px-1 text-center text-[9px] font-mono font-semibold text-text-muted">PLANOS</span>
          {(
            [
              ['xy', 'XY', '#ef4444'],
              ['xz', 'XZ', '#10b981'],
              ['yz', 'YZ', '#7bd0ff'],
            ] as ['xy' | 'xz' | 'yz', string, string][]
          ).map(([key, label, color]) => (
            <button
              key={key}
              onClick={() => togglePlane(key)}
              title={`Ver / ocultar plano ${label}`}
              type="button"
              className="px-1.5 py-0.5 rounded text-[11px] font-mono font-bold transition-colors hover:bg-surface-container-high"
              style={{ color, opacity: visiblePlanes[key] ? 1 : 0.3 }}
            >
              {label}
            </button>
          ))}
          <button
            onClick={toggleAllPlanes}
            title="Ver / ocultar todos los planos"
            type="button"
            className="flex items-center justify-center px-1 py-0.5 rounded text-secondary hover:bg-surface-container-high transition-colors"
          >
            <span className="material-symbols-outlined text-[14px]">
              {visiblePlanes.xy || visiblePlanes.xz || visiblePlanes.yz ? 'hide_source' : 'select_all'}
            </span>
          </button>
        </div>
        {/* PLANES-VIS-END */}
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
      {/* BLACKSCREEN-FIX: mensaje visible si WebGL fallo (antes: negro). */}
      {webglError && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-2 bg-surface-container-lowest/95 p-6 text-center">
          <span className="material-symbols-outlined text-[36px] text-fea-stress-yield">warning</span>
          <p className="text-[13px] font-semibold text-text-primary">Vista 3D no disponible (WebGL)</p>
          <p className="text-[11px] font-mono text-text-muted max-w-md break-all">{webglError}</p>
          <p className="text-[11px] text-text-secondary">Actualiza los drivers de GPU o el runtime WebView2. El resto de la app sigue funcionando.</p>
        </div>
      )}
      {/* UI-CLEAN2-START (reversible): badge MODO eliminado; el selector de
          perfil se movio al stack de camara. Para volver atras: restaurar
          este bloque desde git. */}
      <div className="absolute top-space-sm left-space-sm z-20 flex items-center gap-2 pointer-events-none">
        {/* FACES-START (reversible): estado de la seleccion de caras. */}
        {facePickEnabled && activeFilename && surfaces[activeFilename] && (
          <span className="px-2 py-1 rounded-lg bg-surface-elevated/85 backdrop-blur-md border border-border-subtle/40 font-mono text-[10px] text-text-secondary">
            {(() => {
              const surf = surfaces[activeFilename as string];
              if (!rangesCover(surf.ranges, surf.numTriangles)) return 'Caras no disponibles (teselado diezmado)';
              return selectedFaces.length > 0
                ? `Caras: ${[...selectedFaces].sort((a, b) => a - b).map((f) => `face_${f}`).join(', ')}`
                : `Clic en una cara (${surf.faces.length} disponibles)`;
            })()}
          </span>
        )}
        {/* FACES-END */}
      </div>
      {/* UI-CLEAN2-END */}
    </main>
  );
};
