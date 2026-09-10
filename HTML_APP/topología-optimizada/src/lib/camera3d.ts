// NAV-VIEW (reversible): port a three.js del CameraController validado de la
// predecesora (desktop/viewport/camera.py) + signos de docs/NAVIGATION_CONVENTION.md.
// - NavigationManager decide QUE accion; estas funciones deciden COMO.
// - Orbita trackball libre alrededor del target (sin bloqueo a ejes).
// - Pan en espacio de camara (mueve camara + target).
// - Dolly a lo largo de la direccion de vista.
// - Vistas y fit son reposicionamientos puntuales, nunca restringen despues.
// Adaptacion documentada: en VTK dy>0 = arrastrar ARRIBA (flip de Qt); en el
// navegador dy>0 = arrastrar ABAJO, por eso aqui drag = right*(-dx) + up*(+dy)
// (equivale a pasar dy_vtk = -dy_pantalla a la formula original).
// Para volver atras: borrar este archivo + bloques NAV-VIEW en CadViewport.tsx.
import * as THREE from 'three';

export const ORBIT_SENSITIVITY = 0.008;
export const PAN_SENSITIVITY = 0.002;
export const DOLLY_SENSITIVITY = 0.8;

function basis(camera: THREE.PerspectiveCamera, target: THREE.Vector3) {
  const forward = target.clone().sub(camera.position);
  const dist = Math.max(forward.length(), 1e-12);
  forward.divideScalar(dist);
  let right = new THREE.Vector3().crossVectors(forward, camera.up);
  if (right.length() < 1e-9) {
    right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0));
    if (right.length() < 1e-9) {
      right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(1, 0, 0));
    }
  }
  right.normalize();
  const up = new THREE.Vector3().crossVectors(right, forward).normalize();
  return { forward, right, up, dist };
}

/** Orbita libre: el modelo sigue al cursor (dx, dy en px, dy>0 = abajo). */
export function orbitCamera(
  camera: THREE.PerspectiveCamera,
  target: THREE.Vector3,
  dx: number,
  dy: number,
  sensitivity = ORBIT_SENSITIVITY,
): void {
  const { forward, right, up, dist } = basis(camera, target);
  const drag = right.clone().multiplyScalar(-dx).add(up.clone().multiplyScalar(dy));
  if (drag.length() < 1e-12) return;
  drag.normalize();
  const axis = new THREE.Vector3().crossVectors(drag, forward);
  if (axis.length() < 1e-12) return;
  axis.normalize();
  const mag = Math.sqrt(dx * dx + dy * dy) * sensitivity;
  const q = new THREE.Quaternion().setFromAxisAngle(axis, mag);
  const offset = camera.position.clone().sub(target).applyQuaternion(q);
  camera.position.copy(target).add(offset);
  camera.up.copy(up.applyQuaternion(q));
  camera.lookAt(target);
}

/** Pan: modelo sigue al cursor; mueve camara + target juntos. */
export function panCamera(
  camera: THREE.PerspectiveCamera,
  target: THREE.Vector3,
  dx: number,
  dy: number,
  sensitivity = PAN_SENSITIVITY,
): void {
  const { forward, right, up, dist } = basis(camera, target);
  void forward;
  const scale = dist * sensitivity;
  const delta = right.clone().multiplyScalar(-dx * scale).add(up.clone().multiplyScalar(dy * scale));
  target.add(delta);
  camera.position.add(delta);
  camera.lookAt(target);
}

/** Dolly: steps>0 acerca (como CameraController.dolly). */
export function dollyCamera(
  camera: THREE.PerspectiveCamera,
  target: THREE.Vector3,
  steps: number,
  sensitivity = DOLLY_SENSITIVITY,
): void {
  const forward = target.clone().sub(camera.position);
  const dist = Math.max(forward.length(), 1e-12);
  forward.divideScalar(dist);
  const next = Math.min(1e6, Math.max(0.05, dist * Math.exp(-steps * sensitivity)));
  camera.position.copy(target).addScaledVector(forward, -next);
  camera.lookAt(target);
}

export type StdView = 'iso' | 'top' | 'front' | 'right' | 'back' | 'left' | 'bottom';

/** Vista estandar (Y-up de three.js): reposiciona sin restringir despues. */
export function viewCamera(
  camera: THREE.PerspectiveCamera,
  target: THREE.Vector3,
  view: StdView,
): void {
  const dist = Math.max(camera.position.distanceTo(target), 1e-6);
  const dirs: Record<StdView, THREE.Vector3> = {
    iso: new THREE.Vector3(1, 1, 1).normalize(),
    top: new THREE.Vector3(0, 1, 0),
    bottom: new THREE.Vector3(0, -1, 0),
    front: new THREE.Vector3(0, 0, 1),
    back: new THREE.Vector3(0, 0, -1),
    right: new THREE.Vector3(1, 0, 0),
    left: new THREE.Vector3(-1, 0, 0),
  };
  camera.position.copy(target).addScaledVector(dirs[view], dist);
  camera.up.set(0, view === 'top' || view === 'bottom' ? 0 : 1, 0);
  if (view === 'top') camera.up.set(0, 0, -1);
  if (view === 'bottom') camera.up.set(0, 0, 1);
  camera.lookAt(target);
}

/** Fit a la esfera del modelo (como set_target: centro + radio*1.2). */
export function fitCamera(
  camera: THREE.PerspectiveCamera,
  target: THREE.Vector3,
  center: THREE.Vector3,
  radius: number,
): void {
  const dist = Math.max(radius * 1.2, 1e-6);
  const dir = camera.position.clone().sub(target);
  if (dir.length() < 1e-9) dir.set(1, 1, 1);
  dir.normalize();
  target.copy(center);
  camera.position.copy(center).addScaledVector(dir, dist);
  camera.near = Math.max(dist / 100, 1e-3);
  camera.far = dist * 100;
  camera.updateProjectionMatrix();
  camera.lookAt(target);
}
