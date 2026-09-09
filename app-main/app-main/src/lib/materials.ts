import { Material } from '../types';

export const STANDARD_MATERIALS: Material[] = [
  {
    id: 'structural_steel',
    name: 'Acero Estructural (S355 / A36)',
    youngModulus: 210,
    poissonRatio: 0.30,
    density: 7850,
    yieldStrength: 355,
    color: '#94a3b8'
  },
  {
    id: 'aluminum_6061',
    name: 'Aluminio 6061-T6 (Aeronáutico)',
    youngModulus: 68.9,
    poissonRatio: 0.33,
    density: 2700,
    yieldStrength: 276,
    color: '#38bdf8'
  },
  {
    id: 'titanium_ti6al4v',
    name: 'Titanio Ti-6Al-4V (Grado 5 / Impresión 3D)',
    youngModulus: 114,
    poissonRatio: 0.34,
    density: 4430,
    yieldStrength: 880,
    color: '#a78bfa'
  },
  {
    id: 'inconel_718',
    name: 'Superaleación Inconel 718',
    youngModulus: 205,
    poissonRatio: 0.28,
    density: 8190,
    yieldStrength: 1100,
    color: '#f59e0b'
  },
  {
    id: 'cf_pa12',
    name: 'PA12-CF (Polímero reforzado con fibra de carbono)',
    youngModulus: 8.5,
    poissonRatio: 0.38,
    density: 1250,
    yieldStrength: 120,
    color: '#10b981'
  }
];
