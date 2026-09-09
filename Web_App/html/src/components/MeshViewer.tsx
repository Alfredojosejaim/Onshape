import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { NAV_PROFILES, type NavProfileName } from '../lib/navigation';

export interface PreviewMesh {
  vertices: number[];
  indices: number[];
  normals?: number[] | null;
  bbox?: { xmin: number; xmax: number; ymin: number; ymax: number; zmin: number; zmax: number } | null;
  num_vertices?: number;
  num_triangles?: number;
}

export type MeshViewDir = 'front' | 'back' | 'left' | 'right' | 'top' | 'bottom' | 'iso';

export interface MeshViewerHandle {
  setView: (dir: MeshViewDir) => void;
  reset: () => void;
}

export interface MeshSelection {
  point: [number, number, number];
  faceIndex: number | null;
  triangle: [[number, number, number], [number, number, number], [number, number, number]] | null;
}

interface MeshViewerProps {
  mesh?: PreviewMesh | null;
  wireframe?: boolean;
  color?: string;
  height?: number;
  emptyMessage?: string;
  values?: number[] | null;
  colorMin?: number;
  colorMax?: number;
  colorbarLabel?: string;
  clip?: boolean;
  profile?: NavProfileName | string;
  onSelect?: (sel: MeshSelection | null) => void;
}

/** Normaliza t en [0,1] a rampa azul->cian->verde->amarillo->rojo. */
function colormap(t: number): [number, number, number] {
  const c = Math.min(1, Math.max(0, t));
  const stops: [number, number, number][] = [
    [0.10, 0.25, 0.90], // azul
    [0.00, 0.85, 1.00], // cian
    [0.15, 0.75, 0.35], // verde
    [0.98, 0.85, 0.20], // amarillo
    [0.90, 0.15, 0.15], // rojo
  ];
  const seg = Math.min(stops.length - 2, Math.floor(c * (stops.length - 1)));
  const f = c * (stops.length - 1) - seg;
  const a = stops[seg];
  const b = stops[seg + 1];
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}

/** Mapea etiquetas del ViewCube (mayúsculas) a direcciones del visor. */
export function mapCubeFace(face: string): MeshViewDir | 'reset' {
  const f = face.trim().toUpperCase();
  if (f === 'FRONT') return 'front';
  if (f === 'BACK') return 'back';
  if (f === 'LEFT') return 'left';
  if (f === 'RIGHT') return 'right';
  if (f === 'TOP') return 'top';
  if (f === 'BOTTOM') return 'bottom';
  if (f === 'ISO') return 'iso';
  if (f === 'FIT' || f === 'PERSP' || f === 'RESET') return 'reset';
  return 'iso';
}

/**
 * Visor 3D real (three pelado, sin fiber/drei). Cámara Z-up como el original
 * (camera.py): FRONT=(0,-1,0) BACK=(0,1,0) TOP=(0,0,1) BOTTOM=(0,0,-1)
 * LEFT=(-1,0,0) RIGHT=(1,0,0) ISO=(1,1,1), up=(0,0,1) salvo top/bottom up=(0,1,0).
 */
export const MeshViewer = forwardRef<MeshViewerHandle, MeshViewerProps>(function MeshViewer(
  {
    mesh,
    wireframe = false,
    color = '#7bd0ff',
    height = 460,
    emptyMessage = 'Sin malla — importa un STEP y genera la malla para previsualizar.',
    values = null,
    colorMin,
    colorMax,
    colorbarLabel,
    clip = false,
    profile = 'autocad',
    onSelect,
  }: MeshViewerProps,
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const meshRef = useRef<THREE.Mesh | null>(null);
  const markerRef = useRef<THREE.Mesh | null>(null);
  const materialRef = useRef<THREE.MeshStandardMaterial | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const clipPlaneRef = useRef<THREE.Plane | null>(null);
  const profileRef = useRef<string>(typeof profile === 'string' ? profile : 'autocad');
  const onSelectRef = useRef<MeshViewerProps['onSelect']>(onSelect);
  const hoverRef = useRef(false);
  const fitRef = useRef<{ center: THREE.Vector3; radius: number }>({ center: new THREE.Vector3(), radius: 100 });
  const [selInfo, setSelInfo] = useState<string | null>(null);

  profileRef.current = typeof profile === 'string' ? profile : 'autocad';
  onSelectRef.current = onSelect;

  const profOf = (): NavProfileName =>
    profileRef.current === 'onshape' || profileRef.current === 'fusion360' || profileRef.current === 'blender'
      ? profileRef.current
      : 'autocad';

  const applyView = (dir: MeshViewDir) => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;
    const { center, radius } = fitRef.current;
    const dist = Math.max(radius * 2.2, 1);
    const t = center.clone();
    // Direcciones Z-up exactas del original.
    if (dir === 'front') { camera.position.set(t.x, t.y - dist, t.z); camera.up.set(0, 0, 1); }
    else if (dir === 'back') { camera.position.set(t.x, t.y + dist, t.z); camera.up.set(0, 0, 1); }
    else if (dir === 'left') { camera.position.set(t.x - dist, t.y, t.z); camera.up.set(0, 0, 1); }
    else if (dir === 'right') { camera.position.set(t.x + dist, t.y, t.z); camera.up.set(0, 0, 1); }
    else if (dir === 'top') { camera.position.set(t.x, t.y, t.z + dist); camera.up.set(0, 1, 0); }
    else if (dir === 'bottom') { camera.position.set(t.x, t.y, t.z - dist); camera.up.set(0, 1, 0); }
    else { camera.position.set(t.x + dist * 0.577, t.y + dist * 0.577, t.z + dist * 0.577); camera.up.set(0, 0, 1); }
    controls.target.copy(t);
    controls.update();
  };

  const frameByBbox = () => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;
    const { center, radius } = fitRef.current;
    const dist = Math.max(radius * 2.2, 1);
    camera.up.set(0, 0, 1);
    camera.position.set(center.x + dist * 0.577, center.y + dist * 0.577, center.z + dist * 0.577);
    camera.near = Math.max(dist / 1000, 0.01);
    camera.far = dist * 100;
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    controls.update();
  };

  const rotateStep = () => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;
    const off = camera.position.clone().sub(controls.target);
    off.applyAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI / 6);
    camera.position.copy(controls.target).add(off);
    controls.update();
  };

  useImperativeHandle(ref, () => ({ setView: applyView, reset: frameByBbox }), []);

  // Configura OrbitControls.mouseButtons según perfil (LEFT siempre libre para select).
  const applyProfileButtons = (controls: OrbitControls) => {
    const p = NAV_PROFILES[profOf()];
    const R = p.right === 'orbit' ? THREE.MOUSE.ROTATE : p.right === 'pan' ? THREE.MOUSE.PAN : -1;
    controls.mouseButtons = {
      LEFT: -1 as unknown as THREE.MOUSE,
      MIDDLE: p.middle === 'orbit' ? THREE.MOUSE.ROTATE : THREE.MOUSE.PAN,
      RIGHT: R as unknown as THREE.MOUSE,
    };
  };

  useEffect(() => {
    const c = controlsRef.current;
    if (c) applyProfileButtons(c);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  // Montaje único: escena, luces, controles, resize, dispose.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, height);
    renderer.localClippingEnabled = true;
    renderer.domElement.tabIndex = 0;
    renderer.domElement.style.outline = 'none';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / height,
      0.1,
      100000,
    );
    camera.up.set(0, 0, 1);
    camera.position.set(120, -120, 120);
    cameraRef.current = camera;

    const hemi = new THREE.HemisphereLight(0xf1f5f9, 0x0b0e17, 0.9);
    const dir = new THREE.DirectionalLight(0xffffff, 1.6);
    dir.position.set(150, -150, 220);
    scene.add(hemi, dir);

    // Rejilla en plano XY (Z-up).
    const grid = new THREE.GridHelper(400, 20, 0x2e3646, 0x1f2430);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -80;
    scene.add(grid);

    // Marcador de selección (pequeña esfera).
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(2, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0xfbbf24, depthTest: false }),
    );
    marker.visible = false;
    marker.renderOrder = 999;
    scene.add(marker);
    markerRef.current = marker;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controlsRef.current = controls;
    applyProfileButtons(controls);

    const raycaster = new THREE.Raycaster();
    let downX = 0;
    let downY = 0;
    let downButton = -1;
    let savedMiddle: THREE.MOUSE | -1 | null = null;

    const pickSelect = (ev: PointerEvent) => {
      const m = meshRef.current;
      if (!m) return;
      const rect = renderer.domElement.getBoundingClientRect();
      const nx = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      const ny = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(new THREE.Vector2(nx, ny), camera);
      const hits = raycaster.intersectObject(m, false);
      if (hits.length === 0) {
        marker.visible = false;
        setSelInfo(null);
        onSelectRef.current?.(null);
        return;
      }
      const h = hits[0];
      const pt: [number, number, number] = [h.point.x, h.point.y, h.point.z];
      marker.position.copy(h.point);
      marker.scale.setScalar(Math.max(fitRef.current.radius / 80, 0.5));
      marker.visible = true;
      let tri: MeshSelection['triangle'] = null;
      let faceIndex: number | null = null;
      if (h.face && m.geometry instanceof THREE.BufferGeometry) {
        const pos = m.geometry.getAttribute('position') as THREE.BufferAttribute;
        faceIndex = h.faceIndex ?? null;
        const get = (i: number): [number, number, number] => [pos.getX(i), pos.getY(i), pos.getZ(i)];
        tri = [get(h.face.a), get(h.face.b), get(h.face.c)];
      }
      const sel: MeshSelection = { point: pt, faceIndex, triangle: tri };
      setSelInfo(`sel [${pt[0].toFixed(1)}, ${pt[1].toFixed(1)}, ${pt[2].toFixed(1)}]${faceIndex !== null ? ` · tri ${faceIndex}` : ''}`);
      onSelectRef.current?.(sel);
    };

    // shift+medio=orbit temporal (autocad/fusion360) sin pelear con OrbitControls.
    const onPointerDown = (ev: PointerEvent) => {
      downX = ev.clientX;
      downY = ev.clientY;
      downButton = ev.button;
      const p = NAV_PROFILES[profOf()];
      if (ev.button === 1 && ev.shiftKey && p.shiftMiddle === 'orbit' && p.middle !== 'orbit') {
        savedMiddle = controls.mouseButtons.MIDDLE as unknown as THREE.MOUSE;
        controls.mouseButtons.MIDDLE = THREE.MOUSE.ROTATE;
      } else if (ev.button === 1 && ev.shiftKey && p.shiftMiddle === 'pan' && p.middle !== 'pan') {
        savedMiddle = controls.mouseButtons.MIDDLE as unknown as THREE.MOUSE;
        controls.mouseButtons.MIDDLE = THREE.MOUSE.PAN;
      }
    };
    const onPointerUp = (ev: PointerEvent) => {
      if (savedMiddle !== null) {
        controls.mouseButtons.MIDDLE = savedMiddle as unknown as THREE.MOUSE;
        savedMiddle = null;
      }
      // Clic sin drag con botón izquierdo = select (los 4 perfiles: izq=select).
      const moved = Math.hypot(ev.clientX - downX, ev.clientY - downY);
      if (downButton === 0 && ev.button === 0 && moved < 5) pickSelect(ev);
      downButton = -1;
    };
    const onDblClick = () => frameByBbox();
    const onContextMenu = (ev: Event) => {
      // Solo suprimir menú cuando el botón derecho orbita/panea.
      const p = NAV_PROFILES[profOf()];
      if (p.right !== 'menu') ev.preventDefault();
    };
    // Teclas de fit por perfil (solo con foco o hover, sin robar inputs).
    const onKeyDown = (ev: KeyboardEvent) => {
      const t = ev.target as HTMLElement | null;
      if (t && ['INPUT', 'SELECT', 'TEXTAREA'].includes(t.tagName)) return;
      if (!hoverRef.current && document.activeElement !== renderer.domElement) return;
      const k = ev.key.toLowerCase();
      const p = profOf();
      if (p === 'autocad') {
        if (k === 'n') { ev.preventDefault(); frameByBbox(); }
        else if (k === 'r') { ev.preventDefault(); rotateStep(); }
      } else if (p === 'onshape' || p === 'fusion360') {
        if (k === 'f') { ev.preventDefault(); frameByBbox(); }
      } else if (p === 'blender') {
        if (ev.key === '.') { ev.preventDefault(); frameByBbox(); }
      }
      // shift+izq en onshape = rotate (espejo del original ROTATE_LEFT).
      if (p === 'onshape' && ev.shiftKey && k === 'arrowleft') { ev.preventDefault(); rotateStep(); }
    };
    const onEnter = () => { hoverRef.current = true; };
    const onLeave = () => { hoverRef.current = false; };

    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointerup', onPointerUp);
    renderer.domElement.addEventListener('dblclick', onDblClick);
    renderer.domElement.addEventListener('contextmenu', onContextMenu);
    window.addEventListener('keydown', onKeyDown);
    renderer.domElement.addEventListener('mouseenter', onEnter);
    renderer.domElement.addEventListener('mouseleave', onLeave);

    let raf = 0;
    const loop = () => {
      raf = requestAnimationFrame(loop);
      controls.update();
      renderer.render(scene, camera);
    };
    loop();

    const ro = new ResizeObserver(() => {
      if (!container) return;
      const w = container.clientWidth;
      if (w === 0) return;
      camera.aspect = w / height;
      camera.updateProjectionMatrix();
      renderer.setSize(w, height);
    });
    ro.observe(container);

    // Stash scene for mesh-effect via container userData
    (container as unknown as { __scene: THREE.Scene }).__scene = scene;

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointerup', onPointerUp);
      renderer.domElement.removeEventListener('dblclick', onDblClick);
      renderer.domElement.removeEventListener('contextmenu', onContextMenu);
      window.removeEventListener('keydown', onKeyDown);
      renderer.domElement.removeEventListener('mouseenter', onEnter);
      renderer.domElement.removeEventListener('mouseleave', onLeave);
      controls.dispose();
      // dispose de la malla si existe
      if (meshRef.current) {
        meshRef.current.geometry.dispose();
        meshRef.current = null;
      }
      if (materialRef.current) {
        materialRef.current.dispose();
        materialRef.current = null;
      }
      grid.geometry.dispose();
      (grid.material as THREE.Material).dispose();
      marker.geometry.dispose();
      (marker.material as THREE.Material).dispose();
      hemi.dispose();
      dir.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      rendererRef.current = null;
      controlsRef.current = null;
      cameraRef.current = null;
      markerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reconstruir geometría cuando cambia la malla o el campo de colores.
  useEffect(() => {
    const container = containerRef.current;
    const scene = container
      ? (container as unknown as { __scene?: THREE.Scene }).__scene
      : undefined;
    if (!scene) return;

    // Limpiar malla anterior
    if (meshRef.current) {
      scene.remove(meshRef.current);
      meshRef.current.geometry.dispose();
      meshRef.current = null;
    }
    if (materialRef.current) {
      materialRef.current.dispose();
      materialRef.current = null;
    }
    if (markerRef.current) markerRef.current.visible = false;
    setSelInfo(null);
    if (!mesh || mesh.vertices.length === 0 || mesh.indices.length === 0) return;

    const positions = new Float32Array(mesh.vertices);
    const vertCount = Math.floor(positions.length / 3);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setIndex(mesh.indices);
    if (mesh.normals && mesh.normals.length === positions.length) {
      geometry.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(mesh.normals), 3));
    } else {
      geometry.computeVertexNormals();
    }

    const hasValues = !!values && values.length === vertCount && vertCount > 0;
    let lo = colorMin ?? 0;
    let hi = colorMax ?? 1;
    if (hasValues && colorMin === undefined && colorMax === undefined) {
      lo = Infinity;
      hi = -Infinity;
      for (const v of values!) {
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
      if (!isFinite(lo) || !isFinite(hi)) { lo = 0; hi = 1; }
    }
    if (hi - lo < 1e-12) hi = lo + 1e-12;
    if (hasValues) {
      const colors = new Float32Array(vertCount * 3);
      for (let i = 0; i < vertCount; i++) {
        const t = (values![i] - lo) / (hi - lo);
        const [r, g, b] = colormap(t);
        colors[i * 3] = r;
        colors[i * 3 + 1] = g;
        colors[i * 3 + 2] = b;
      }
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    }
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();

    const material = new THREE.MeshStandardMaterial({
      color: hasValues ? new THREE.Color('#ffffff') : new THREE.Color(color),
      vertexColors: hasValues,
      side: THREE.DoubleSide,
      wireframe,
      metalness: 0.35,
      roughness: 0.55,
    });
    if (clip && clipPlaneRef.current) {
      material.clippingPlanes = [clipPlaneRef.current];
    }
    materialRef.current = material;

    const m = new THREE.Mesh(geometry, material);
    meshRef.current = m;
    scene.add(m);

    // Auto-fit a bbox (o a la geometría si no hay bbox)
    const box = geometry.boundingBox!;
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const radius = Math.max(size.x, size.y, size.z, 1);
    fitRef.current = { center: center.clone(), radius };
    if (clipPlaneRef.current) {
      clipPlaneRef.current.constant = center.x;
    }
    frameByBbox();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mesh, values, colorMin, colorMax]);

  // wireframe / color en caliente sin reconstruir geometría
  useEffect(() => {
    if (materialRef.current) materialRef.current.wireframe = wireframe;
  }, [wireframe]);
  useEffect(() => {
    if (materialRef.current && !(values && values.length > 0)) materialRef.current.color.set(color);
  }, [color, values]);

  // Plano de corte X en el centro del bbox.
  useEffect(() => {
    const renderer = rendererRef.current;
    if (renderer) renderer.localClippingEnabled = true;
    if (clip) {
      if (!clipPlaneRef.current) {
        clipPlaneRef.current = new THREE.Plane(new THREE.Vector3(-1, 0, 0), fitRef.current.center.x);
      } else {
        clipPlaneRef.current.normal.set(-1, 0, 0);
        clipPlaneRef.current.constant = fitRef.current.center.x;
      }
      if (materialRef.current) {
        materialRef.current.clippingPlanes = [clipPlaneRef.current];
        materialRef.current.needsUpdate = true;
      }
    } else {
      if (materialRef.current) {
        materialRef.current.clippingPlanes = null;
        materialRef.current.needsUpdate = true;
      }
    }
  }, [clip]);

  const vertCount = mesh?.num_vertices ?? (mesh ? Math.floor(mesh.vertices.length / 3) : 0);
  const triCount = mesh?.num_triangles ?? (mesh ? Math.floor(mesh.indices.length / 3) : 0);
  const showLegend = !!values && values.length > 0 && !!mesh;
  const legendMin = colorMin ?? (values && values.length > 0 ? Math.min(...values.slice(0, 200000)) : 0);
  const legendMax = colorMax ?? (values && values.length > 0 ? Math.max(...values.slice(0, 200000)) : 1);

  return (
    <div className="relative w-full" style={{ height }}>
      <div ref={containerRef} className="absolute inset-0 w-full h-full" />
      {!mesh && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center pointer-events-none px-6">
          <span className="material-symbols-outlined text-[#2e3646] text-[48px]">view_in_ar</span>
          <p className="text-[#94a3b8] text-[12px] max-w-[320px]">{emptyMessage}</p>
          <p className="text-[#64748b] text-[10px] font-mono">getMeshPreview() sin mesh (mock / sin STEP)</p>
        </div>
      )}
      {mesh && (
        <div className="absolute bottom-1 left-1 z-10 px-2 py-0.5 rounded bg-[#0b0e17]/85 border border-[#2e3646]/50 font-mono text-[10px] text-[#94a3b8] pointer-events-none">
          {vertCount} vértices · {triCount} triángulos{selInfo ? ` · ${selInfo}` : ''}
        </div>
      )}
      {showLegend && (
        <div className="absolute bottom-1 right-1 z-10 px-2 py-1 rounded bg-[#0b0e17]/85 border border-[#2e3646]/50 pointer-events-none">
          {colorbarLabel && <div className="font-mono text-[9px] text-[#7bd0ff] mb-0.5">{colorbarLabel}</div>}
          <div
            className="w-28 h-2 rounded-sm"
            style={{ background: 'linear-gradient(to right, #1a40e6, #00d9ff, #26bf59, #fad933, #e62626)' }}
          />
          <div className="flex justify-between font-mono text-[9px] text-[#94a3b8] mt-0.5">
            <span>{Number(legendMin).toPrecision(4)}</span>
            <span>{Number(legendMax).toPrecision(4)}</span>
          </div>
        </div>
      )}
    </div>
  );
});
