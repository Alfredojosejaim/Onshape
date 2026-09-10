// UI-CLEAN (reversible): datos de referencia del diseño de la interfaz.
// NO se importan en ningun componente: la app arranca vacia y solo muestra
// datos reales (backend STEP) o subidos por el usuario.
// Para volver atras: copiar estos arrays a src/data/models.ts
// (ver marcas UI-CLEAN-START/END alli).
import { CadModelPreset, BoundaryCondition } from '../types';

export const MOCK_CAD_PRESETS: CadModelPreset[] = [
  {
    id: 'cono_soporte',
    filename: 'cono_soporte.step',
    displayName: 'Soporte Cónico de Carga',
    faces: 12,
    edges: 18,
    solids: 1,
    volumeCm3: 505.3,
    elementsTet4: 184920,
    nodes: 38412,
  },
  {
    id: 'brazo_suspension',
    filename: 'brazo_suspension.step',
    displayName: 'Horquilla de Suspensión F1',
    faces: 24,
    edges: 36,
    solids: 1,
    volumeCm3: 412.0,
    elementsTet4: 215300,
    nodes: 44210,
  },
  {
    id: 'puente_cantilever',
    filename: 'soporte_satelite_mbb.step',
    displayName: 'Ménsula MBB Satelital',
    faces: 16,
    edges: 28,
    solids: 1,
    volumeCm3: 630.7,
    elementsTet4: 162400,
    nodes: 33950,
  },
];

export const MOCK_INITIAL_CONDITIONS: BoundaryCondition[] = [
  {
    id: 'bc_fijacion',
    name: 'Encastre Soporte',
    type: 'fijacion',
    details: '3 Caras | Ux=Uy=Uz=0',
    faces: 3,
    active: true,
    statusTag: 'FIX',
    colorTag: 'text-secondary',
  },
  {
    id: 'bc_carga',
    name: 'Tracción Cilíndrica',
    type: 'carga',
    details: '[0, -4500, 1200] N',
    value: [0, -4500, 1200],
    magnitude: 4657.25,
    faces: 2,
    active: true,
    statusTag: 'LOAD',
    colorTag: 'text-tertiary',
  },
  {
    id: 'bc_safe',
    name: 'Región Preservada',
    type: 'preservada',
    details: 'Pernos y Bujes (8 mm)',
    faces: 4,
    active: true,
    statusTag: 'SAFE',
    colorTag: 'bg-fea-stress-optimal text-[#0b0e17]',
  },
  {
    id: 'bc_keepout',
    name: 'Obstáculo (Keep-Out)',
    type: 'keepout',
    details: 'Cilindro Paso Tornillo',
    faces: 2,
    active: true,
    statusTag: 'VOID',
    colorTag: 'bg-fea-stress-critical text-[#0b0e17]',
  },
];
