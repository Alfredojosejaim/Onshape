import { MaterialProperties, CadFeature, BoundaryCondition, MeshingSettings, FeaResults, SimpOptimizationState, GenerativeExportState } from './types';

export const MATERIALS_LIBRARY: MaterialProperties[] = [
  {
    id: 'al7075',
    name: 'Aluminio 7075-T6 (Aeroespacial)',
    category: 'Aleaciones de Aluminio',
    youngsModulus: 71.7,
    poissonRatio: 0.33,
    yieldStrength: 503.0,
    density: 2.81,
    tensileStrength: 572.0,
    thermalConductivity: 130,
    costIndex: '$$$',
  },
  {
    id: 'ti6al4v',
    name: 'Titanio Ti-6Al-4V (Grado 5)',
    category: 'Aleaciones de Titanio',
    youngsModulus: 113.8,
    poissonRatio: 0.34,
    yieldStrength: 880.0,
    density: 4.43,
    tensileStrength: 950.0,
    thermalConductivity: 6.7,
    costIndex: '$$$$$',
  },
  {
    id: 'ss316l',
    name: 'Acero Inoxidable 316L (Estructural)',
    category: 'Aceros Inoxidables',
    youngsModulus: 193.0,
    poissonRatio: 0.30,
    yieldStrength: 290.0,
    density: 8.00,
    tensileStrength: 580.0,
    thermalConductivity: 16.3,
    costIndex: '$$',
  },
  {
    id: 'pa12',
    name: 'Poliamida PA12 (SLS Impresión 3D)',
    category: 'Polímeros Termoplásticos',
    youngsModulus: 1.7,
    poissonRatio: 0.40,
    yieldStrength: 48.0,
    density: 1.01,
    tensileStrength: 50.0,
    thermalConductivity: 0.22,
    costIndex: '$',
  },
];

export const INITIAL_CAD_FEATURES: CadFeature[] = [
  {
    id: 'origin',
    name: 'Sist. Coordenado Global',
    type: 'origin',
    visible: true,
    details: 'Planos XY, XZ, YZ (WCS)',
  },
  {
    id: 'solid-1',
    name: 'cono_soporte.step',
    type: 'solid',
    visible: true,
    details: '12 Caras • 18 Aristas • 1 Sólido',
    facesCount: 12,
  },
  {
    id: 'bc-fixed',
    name: 'Encastre Soporte',
    type: 'boundary',
    visible: true,
    status: 'ok',
    details: '3 Caras | Ux=Uy=Uz=0',
  },
  {
    id: 'bc-load',
    name: 'Tracción Cilíndrica',
    type: 'load',
    visible: true,
    status: 'active',
    details: '[0, -4500, 1200] N',
  },
  {
    id: 'safe-region',
    name: 'Región Preservada',
    type: 'preserved',
    visible: true,
    status: 'safe',
    details: 'Pernos y Bujes (8 mm)',
  },
  {
    id: 'keepout-region',
    name: 'Obstáculo (Keep-Out)',
    type: 'keepout',
    visible: true,
    status: 'void',
    details: 'Cilindro Paso Tornillo Ø20',
  },
];

export const INITIAL_BOUNDARY_CONDITIONS: BoundaryCondition[] = [
  {
    id: 'bc-fix-1',
    name: 'Fijación Encastre Base (Lug 1 & 2)',
    type: 'fixed',
    location: 'Bujes de Anclaje Inferiores',
    values: { x: 0, y: 0, z: 0, unit: 'mm' },
    faces: [1, 2],
    active: true,
  },
  {
    id: 'bc-force-1',
    name: 'Carga de Tracción Cilíndrica',
    type: 'force',
    location: 'Ojo Superior del Brazo',
    values: { x: 0, y: -4500, z: 1200, magnitude: 4657, unit: 'N' },
    faces: [7],
    active: true,
  },
  {
    id: 'bc-sym-1',
    name: 'Condición de Simetría Planar XZ',
    type: 'displacement',
    location: 'Plano Central Y=0',
    values: { y: 0, unit: 'mm' },
    faces: [5],
    active: true,
  },
];

export const INITIAL_MESHING: MeshingSettings = {
  algorithm: 'Frontal 3D (Delaunay)',
  hMin: 1.5,
  hMax: 6.0,
  jacobianQuality: 0.84,
  nodesCount: 48290,
  elementsCount: 215410,
  elementType: 'Tet4',
  angularTolerance: 12.5,
  chordalDeflection: 0.02,
  growthRate: 1.25,
};

export const INITIAL_FEA: FeaResults = {
  isSolved: true,
  isSolving: false,
  solveTimeSeconds: 4.82,
  maxVonMises: 482.4, // Below 503 MPa yield of 7075-T6
  minVonMises: 12.1,
  maxDisplacement: 0.42, // mm
  safetyFactor: 1.04, // 503 / 482.4 = 1.04
  strainEnergy: 148.6,
  dofCount: 289740,
  deformedScale: 5,
  stressType: 'vonMises',
};

export const SIMP_CONVERGENCE_PRESET = [
  { iteration: 0, compliance: 185.4, volumeFraction: 1.0, change: 0.0 },
  { iteration: 5, compliance: 162.1, volumeFraction: 0.82, change: 0.18 },
  { iteration: 10, compliance: 144.3, volumeFraction: 0.67, change: 0.09 },
  { iteration: 15, compliance: 128.5, volumeFraction: 0.54, change: 0.045 },
  { iteration: 20, compliance: 119.2, volumeFraction: 0.46, change: 0.022 },
  { iteration: 25, compliance: 114.8, volumeFraction: 0.41, change: 0.012 },
  { iteration: 30, compliance: 111.4, volumeFraction: 0.38, change: 0.007 },
  { iteration: 35, compliance: 109.1, volumeFraction: 0.36, change: 0.004 },
  { iteration: 40, compliance: 108.2, volumeFraction: 0.352, change: 0.002 },
  { iteration: 45, compliance: 107.8, volumeFraction: 0.35, change: 0.0009 },
  { iteration: 50, compliance: 107.6, volumeFraction: 0.35, change: 0.0004 },
];

export const INITIAL_SIMP_STATE: SimpOptimizationState = {
  penaltyFactor: 3.0,
  filterRadius: 4.5,
  targetVolumeFraction: 0.35,
  currentIteration: 50,
  maxIterations: 50,
  isRunning: false,
  isCompleted: true,
  currentCompliance: 107.6,
  initialCompliance: 185.4,
  currentVolumeFraction: 0.35,
  densityCutoff: 0.45,
  history: SIMP_CONVERGENCE_PRESET,
};

export const INITIAL_GENERATIVE_EXPORT: GenerativeExportState = {
  reconstructionMethod: 'Marching Cubes + QuadRemesh',
  surfaceSmoothing: 85,
  originalMassKg: 3.42,
  optimizedMassKg: 1.18, // -65.5%
  stiffnessRetentionPct: 82.4,
  manufacturingConstraint: 'Additive (3D Printing)',
  overhangMaxAngle: 45,
  amBuildDirection: 'Z+',
  amSupportsNeeded: false,
  brepFaceCount: 1420,
  exportFormat: 'STEP AP242',
};
