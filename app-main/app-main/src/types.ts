export type OptimizationMode = 'generativa' | 'estructural';

export type ActiveTool = 'carga' | 'materiales' | 'elasticidad' | 'obstrucciones' | 'protegida' | 'optimizar' | 'analisis';

export interface ProtectedFace {
  id: string;
  name: string;
  description: string;
  type: 'support_anchor' | 'load_bearing' | 'mounting_flange' | 'bore_interface' | 'custom';
  enabled: boolean;
  color?: string;
  // Normalized bounding box within domain [minX, minY, minZ, maxX, maxY, maxZ] (0..1)
  bounds: [number, number, number, number, number, number];
}

export interface ObstacleZone {
  id: string;
  name: string;
  description: string;
  shape: 'box' | 'cylinder' | 'quadrant';
  enabled: boolean;
  color?: string;
  // Normalized bounding box or cylinder center and radius [minX, minY, minZ, maxX, maxY, maxZ]
  bounds: [number, number, number, number, number, number];
}

export interface Material {
  id: string;
  name: string;
  youngModulus: number; // in GPa
  poissonRatio: number;
  density: number; // in kg/m^3
  yieldStrength: number; // in MPa
  color: string;
  isCustom?: boolean;
  description?: string;
}

export type DesignDomainPreset = 'cantilever' | 'mbb_beam' | 'l_bracket' | 'bridge' | 'custom_step';

export interface DomainDimensions {
  length: number; // mm
  height: number; // mm
  width: number; // mm
  resolutionX: number;
  resolutionY: number;
  resolutionZ: number;
}

export interface BoundaryCondition {
  id: string;
  type: 'fixed' | 'pinned' | 'roller';
  location: 'left' | 'bottom' | 'corners' | 'custom';
  description: string;
}

export interface LoadCondition {
  id: string;
  direction: [number, number, number]; // normalized [fx, fy, fz]
  magnitude: number; // in Newtons
  position: 'center_bottom' | 'right_bottom' | 'top_edge' | 'custom';
  description: string;
}

export interface SimpConfig {
  mode: OptimizationMode; // 'generativa' | 'estructural'
  volumeFraction: number; // e.g. 0.35 (35% retained)
  penaltyExponent: number; // typically 3.0
  filterRadius: number; // filter radius in elements
  maxIterations: number;
  convergenceTolerance: number;
}

export interface IterationData {
  iteration: number;
  compliance: number; // strain energy / objective
  volumeFraction: number;
  change: number;
}

export type ScalarField = 'density' | 'vonmises' | 'displacement' | 'none';

export interface OptimizationMetrics {
  initialMassKg: number;
  optimizedMassKg: number;
  massReductionPercent: number;
  finalCompliance: number;
  maxVonMisesMpa: number;
  maxDisplacementMm: number;
  safetyFactor: number;
  iterationsCompleted: number;
  converged: boolean;
  computationTimeSec: number;
}

export interface SurfaceMeshData {
  positions: Float32Array;
  indices: Uint32Array;
  normals?: Float32Array;
  values?: Float32Array;
  minVal?: number;
  maxVal?: number;
  field?: ScalarField;
}

