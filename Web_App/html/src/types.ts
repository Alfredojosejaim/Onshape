export type TabId =
  | 'cad-preproceso'
  | 'mallado-condiciones'
  | 'solver-fea'
  | 'optimizacion-simp'
  | 'generativo-export';

export interface MaterialProperties {
  id: string;
  name: string;
  category: string;
  youngsModulus: number; // GPa
  poissonRatio: number;
  yieldStrength: number; // MPa
  density: number; // g/cm³
  tensileStrength: number; // MPa
  thermalConductivity?: number; // W/m·K
  costIndex?: string;
}

export interface CadFeature {
  id: string;
  name: string;
  type: 'origin' | 'solid' | 'boundary' | 'load' | 'preserved' | 'keepout';
  visible: boolean;
  status?: 'ok' | 'safe' | 'void' | 'active';
  details: string;
  facesCount?: number;
}

export interface MeshingSettings {
  algorithm: 'Frontal 3D (Delaunay)' | 'Netgen 3D' | 'HXT Parallel 3D';
  hMin: number; // mm
  hMax: number; // mm
  jacobianQuality: number; // 0..1
  nodesCount: number;
  elementsCount: number;
  elementType: 'Tet4' | 'Tet10' | 'Hex8';
  angularTolerance: number; // deg
  chordalDeflection: number; // mm
  growthRate: number;
}

export interface BoundaryCondition {
  id: string;
  name: string;
  type: 'fixed' | 'pinned' | 'displacement' | 'force' | 'pressure' | 'torque';
  location: string;
  values: {
    x?: number | string;
    y?: number | string;
    z?: number | string;
    magnitude?: number;
    unit?: string;
  };
  faces: number[];
  active: boolean;
}

export interface FeaResults {
  isSolved: boolean;
  isSolving: boolean;
  solveTimeSeconds: number;
  maxVonMises: number; // MPa
  minVonMises: number; // MPa
  maxDisplacement: number; // mm
  safetyFactor: number;
  strainEnergy: number; // mJ
  dofCount: number;
  deformedScale: number; // 1x, 5x, 20x, 50x
  stressType: 'vonMises' | 'tresca' | 'principal1' | 'displacement';
}

export interface SimpOptimizationState {
  penaltyFactor: number; // p = 3.0
  filterRadius: number; // r_min = 4.5 mm
  targetVolumeFraction: number; // 0.35 (-65%)
  currentIteration: number;
  maxIterations: number;
  isRunning: boolean;
  isCompleted: boolean;
  currentCompliance: number;
  initialCompliance: number;
  currentVolumeFraction: number;
  densityCutoff: number; // 0..1
  history: Array<{
    iteration: number;
    compliance: number;
    volumeFraction: number;
    change: number;
  }>;
}

export interface GenerativeExportState {
  reconstructionMethod: 'Marching Cubes + QuadRemesh' | 'Dual Contouring' | 'NURBS B-Rep';
  surfaceSmoothing: number; // 0..100
  originalMassKg: number;
  optimizedMassKg: number;
  stiffnessRetentionPct: number;
  manufacturingConstraint: 'Additive (3D Printing)' | 'CNC 3-Axis' | 'CNC 5-Axis' | 'Investment Casting';
  overhangMaxAngle: number; // 45 deg
  amBuildDirection: 'Z+' | 'Z-' | 'Y+' | 'X+';
  amSupportsNeeded: boolean;
  brepFaceCount: number;
  exportFormat: 'STEP AP242' | 'STL Binary' | 'IGES' | 'Nastran BDF' | 'PDF Certificate';
}
