export type ScreenId =
  | 'modelo-cad-y-pre-proceso'
  | 'mallado-y-condiciones'
  | 'solver-fea-y-tensiones'
  | 'optimizacion-topologica-simp'
  | 'generativo-y-b-rep-export';

export type FeaBackend = 'numpy' | 'kratos';

export interface MaterialProperty {
  id: string;
  name: string;
  category: string;
  youngModulusGpa: number;
  poissonRatio: number;
  yieldStrengthMpa: number;
  densityGcm3: number;
  tensileStrengthMpa: number;
}

export interface CadModelInfo {
  filename: string;
  filesize: string;
  solidName: string;
  facesCount: number;
  edgesCount: number;
  solidsCount: number;
  initialMassKg: number;
  initialVolumeCm3: number;
}

export interface GmshConfig {
  algorithm: string;
  hMin: number;
  hMax: number;
  jacobianQuality: number;
  nodesCount: number;
  tet4ElementsCount: number;
}

export interface FeaResults {
  maxVonMisesMpa: number;
  criticalNodeId: number;
  maxDisplacementMm: number;
  displacementNodeId: number;
  complianceJoules: number;
  safetyFactor: number;
  solveTimeSeconds: number;
  assemblyTimeSeconds: number;
  factorizationTimeSeconds: number;
  postProcessTimeSeconds: number;
  residualError: string;
  convergedIterations: number;
  conditionNumber: string;
}

export interface SimpConfig {
  targetVolumeFraction: number; // e.g. 0.35
  penaltyExponent: number; // e.g. 3.0 (usado por App/Screen4)
  filterRadiusMm: number; // e.g. 3.5
  currentIteration: number;
  maxIterations: number;
  convergencePercent: number;
  isRunning: boolean;
  activeCells: number;
  prunedElements: number;
  finalMassKg: number;
  massReductionPercent: number;
  specificStiffnessGainPercent: number;
  currentCompliance: number;
  maxDensityChange: number;
}

export interface BRepReconstructionStatus {
  marchingTetrahedraCompleted: boolean;
  laplacianSmoothingCompleted: boolean;
  geometricSewingCompleted: boolean;
  booleanReunionCompleted: boolean;
  triangularFacetsCount: number;
  nonManifoldEdges: number;
  eulerCharacteristic: number;
  nurbsFacesCount: number;
  reconstructionTimeSeconds: number;
  solidVolumeCm3: number;
  volumeReductionPercent: number;
  uuid: string;
}
