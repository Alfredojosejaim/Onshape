// Tabla de perfiles de navegación — espejo de core/navigation.py (NavigationManager).
// No inventar mapeos: cualquier cambio debe reflejar el original Python.

export type NavProfileName = 'autocad' | 'onshape' | 'fusion360' | 'blender';

export type NavAction = 'orbit' | 'pan' | 'zoom' | 'select' | 'fit' | 'rotate' | 'menu' | 'none';

export interface NavProfileDef {
  name: NavProfileName;
  displayName: string;
  /** Botón izquierdo: 'select' en los 4 perfiles (nunca orbita directo). */
  left: 'select';
  /** Botón central sin modificador. */
  middle: 'pan' | 'orbit';
  /** Botón central con Shift. */
  shiftMiddle: 'orbit' | 'pan';
  /** Botón derecho (arrastrar). */
  right: 'orbit' | 'pan' | 'menu';
  /** Teclas que disparan fit en este perfil. */
  fitKeys: string[];
  /** Doble-clic izquierdo = fit (todos). */
  dblclickFit: true;
}

export const NAV_PROFILES: Record<NavProfileName, NavProfileDef> = {
  // AutoCADProfile: LEFT select (dblclick=fit), MIDDLE pan, shift+MIDDLE orbit,
  // wheel zoom, RIGHT context_menu, keys n=fit r=rotate.
  autocad: {
    name: 'autocad',
    displayName: 'AutoCAD',
    left: 'select',
    middle: 'pan',
    shiftMiddle: 'orbit',
    right: 'menu',
    fitKeys: ['n'],
    dblclickFit: true,
  },
  // OnshapeProfile: LEFT select, MIDDLE pan, RIGHT-drag orbit, wheel zoom, f=fit.
  onshape: {
    name: 'onshape',
    displayName: 'Onshape',
    left: 'select',
    middle: 'pan',
    shiftMiddle: 'pan',
    right: 'orbit',
    fitKeys: ['f'],
    dblclickFit: true,
  },
  // Fusion360Profile: LEFT select, MIDDLE pan, shift+MIDDLE orbit, wheel zoom, f=fit.
  fusion360: {
    name: 'fusion360',
    displayName: 'Fusion 360',
    left: 'select',
    middle: 'pan',
    shiftMiddle: 'orbit',
    right: 'menu',
    fitKeys: ['f'],
    dblclickFit: true,
  },
  // BlenderProfile: MIDDLE orbit, shift+MIDDLE pan, wheel zoom, LEFT select, '.'=fit.
  blender: {
    name: 'blender',
    displayName: 'Blender',
    left: 'select',
    middle: 'orbit',
    shiftMiddle: 'pan',
    right: 'menu',
    fitKeys: ['.'],
    dblclickFit: true,
  },
};

export const NAV_PROFILE_NAMES: NavProfileName[] = ['autocad', 'onshape', 'fusion360', 'blender'];

export const NAV_STORAGE_KEY = 'topoopt.nav';
export const DEFAULT_NAV_PROFILE: NavProfileName = 'autocad';

export function isNavProfileName(v: unknown): v is NavProfileName {
  return typeof v === 'string' && (NAV_PROFILE_NAMES as string[]).includes(v);
}

export function readStoredNavProfile(): NavProfileName {
  try {
    const raw = localStorage.getItem(NAV_STORAGE_KEY);
    if (isNavProfileName(raw)) return raw;
  } catch {
    /* sin localStorage */
  }
  return DEFAULT_NAV_PROFILE;
}

/** Tecla de fit del perfil (para hints de UI). */
export function fitKeyFor(profile: NavProfileName): string {
  return NAV_PROFILES[profile]?.fitKeys[0] ?? 'f';
}
