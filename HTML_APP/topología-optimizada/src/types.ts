export type ActiveTab = 'optimizacion' | 'analizis';

export type ActiveTool =
  | 'seleccionar'
  | 'medir'
  | 'carga'
  | 'fijacion'
  | 'preservada'
  | 'keepout'
  | 'malla'
  | 'seccion';

export interface Material {
  id: string;
  name: string;
  category: string;
  youngModulus: number; // GPa
  poissonRatio: number;
  yieldStrength: number; // MPa
  density: number; // g/cm³
  tensileStrength?: number; // MPa (ausente si el core no lo expone -> "—")
  color: string;
  description: string;
}

export interface BoundaryCondition {
  id: string;
  name: string;
  type: 'fijacion' | 'carga' | 'preservada' | 'keepout';
  details: string;
  value?: [number, number, number]; // [Fx, Fy, Fz] in N for loads
  magnitude?: number;
  faces: number;
  active: boolean;
  statusTag?: string;
  colorTag?: string;
}

export interface SimpParameters {
  volfrac: number; // 0.10 to 0.80
  penalization: number; // p = 3.0
  filterRadius: number; // r_min in mm
  tolerance: number; // Δρ (1e-3)
  maxIterations: number;
}

export interface OptimizationState {
  isRunning: boolean;
  isPaused: boolean;
  currentIteration: number;
  totalIterations: number;
  currentCompliance: number;
  currentVolume: number;
  convergenceDelta: number;
  initialMassKg: number;
  currentMassKg: number;
  complianceHistory: number[];
  volumeHistory: number[];
}

export interface FeaResults {
  maxVonMisesMpa: number;
  minSafetyFactor: number;
  maxDisplacementMm: number;
  modalFreqHz?: number; // ausente si no hay analisis modal -> "—"
  strainEnergyJ: number;
  meshQualityPercent: number;
}

export interface CadModelPreset {
  id: string;
  filename: string;
  displayName: string;
  faces: number;
  edges: number;
  solids: number;
  volumeCm3: number;
  elementsTet4: number;
  nodes: number;
}

// SOLIDS (reversible): cuerpo del STEP segun core list_solids.
export interface SolidInfo {
  solid_id: string;
  index: number;
  name: string;
  volume?: number | null; // mm3 (core) — puede venir null
  faces_count: number;
  center?: [number, number, number] | null;
}
