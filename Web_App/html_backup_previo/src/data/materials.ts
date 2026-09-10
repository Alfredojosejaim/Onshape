import { MaterialProperty } from '../types';

export const MATERIALS: MaterialProperty[] = [
  {
    id: 'al7075',
    name: 'Aluminio 7075-T6 (Aeroespacial)',
    category: 'Aleación Ligera',
    youngModulusGpa: 71.7,
    poissonRatio: 0.33,
    yieldStrengthMpa: 503.0,
    densityGcm3: 2.81,
    tensileStrengthMpa: 572.0,
  },
  {
    id: 'ti6al4v',
    name: 'Titanio Ti-6Al-4V (Grado 5)',
    category: 'Titanio Aeroespacial',
    youngModulusGpa: 114.0,
    poissonRatio: 0.34,
    yieldStrengthMpa: 880.0,
    densityGcm3: 4.43,
    tensileStrengthMpa: 950.0,
  },
  {
    id: 'ss316l',
    name: 'Acero Inoxidable 316L (Estructural)',
    category: 'Acero Austenílico',
    youngModulusGpa: 193.0,
    poissonRatio: 0.30,
    yieldStrengthMpa: 290.0,
    densityGcm3: 8.00,
    tensileStrengthMpa: 580.0,
  },
  {
    id: 'pa12',
    name: 'Poliamida PA12 (SLS Impresión 3D)',
    category: 'Polímero Aditivo',
    youngModulusGpa: 1.7,
    poissonRatio: 0.40,
    yieldStrengthMpa: 48.0,
    densityGcm3: 1.01,
    tensileStrengthMpa: 50.0,
  },
];
