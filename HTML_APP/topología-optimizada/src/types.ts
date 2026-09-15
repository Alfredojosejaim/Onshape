export type ActiveTab = 'optimizacion' | 'analizis' | 'malla';

// OPT-TYPE (reversible): tipo de optimización elegible en parámetros
// (estructural SIMP vs generativa escenario A). Para volver atrás: quitar +
// uso en App/RightPanel.
export type OptimizationType = 'estructural' | 'generativa';

export type ActiveTool =
  | 'seleccionar'
  | 'medir'
  | 'carga'
  | 'fijacion'
  | 'preservada'
  | 'keepout'
  | 'malla'
  | 'seccion'
  // MALLA-TOOLS (reversible): herramientas de la pestana Malla (barra propia,
// parametros en ToolParamsPanel, resultados en RightPanel). Para volver
// atras: quitar + ramas en Toolbar/ToolParamsPanel.
  | 'malla-diagnosticar'
  | 'malla-reparar'
  | 'malla-suavizar'
  | 'malla-reducir'
  | 'malla-remallar'
  | 'malla-volumetrica';

// Accion de herramienta de malla -> metodo del backend.
export type MeshToolAction =
  | 'diagnosticar'
  | 'reparar'
  | 'suavizar'
  | 'reducir'
  | 'remallar';

// Resultado publicado por las herramientas de malla (solo lectura en UI).
export interface MeshOpResult {
  report: Record<string, unknown> | null;
  op: string | null;
  stats: Record<string, unknown> | null;
  error: string | null;
}

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
  // FACES (reversible): caras B-Rep seleccionadas en el viewport (face_index
  // del core). Para volver atras: borrar + uso en App/CadViewport.
  faceIndices?: number[];
  // LOAD-DIR (reversible): normal de referencia de la carga (core
  // LoadCondition.reference_plane_normal, orientacion perpendicular).
  // Para volver atras: borrar + uso en App/ToolParamsPanel/faces.
  loadNormal?: [number, number, number];
  // LOAD-CASE (reversible, Fase 1.3 plan.md): agrupador multicarga +
  // peso relativo. El backend agrupa por metadata["load_case_id"] y pondera
  // con metadata["load_weight"] (generative_engine + controller).
  // Vacío = caso único (__single_...), comportamiento anterior.
  loadCaseId?: string;
  loadWeight?: number;
  // LOAD-DIR2 (reversible): dirección paramétrica de la carga —
  // mode (perpendicular/paralelo al plano), plane (xy/xz/yz), ángulo en el
  // plano (°) y sentido (+1/-1). El vector se deriva como
  // value = mag·dir y loadNormal = normal del plano. Para volver atrás:
  // borrar + uso en ToolParamsPanel.
  loadMode?: 'perpendicular' | 'paralelo';
  loadPlane?: 'xy' | 'xz' | 'yz';
  loadAngleDeg?: number;
  loadSense?: 1 | -1;
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
  heaviside: boolean; // proyección Heaviside (bordes 0/1 nítidos)
  heavisideBeta: number; // agudeza de la proyección
  extrusionAxis: 'off' | 'x' | 'y' | 'z'; // extrusión 2D (densidad constante por eje)
  brepStyle: 'faceted' | 'bspline'; // reconstrucción STEP facetada vs B-spline
  designSpace: 'part' | 'envelope'; // generativa: pieza original vs caja de diseño
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

// DENSITY-VIEW (reversible): campo nodal de densidades SIMP sobre la malla
// de superficie FEA (backend getSurfaceMesh field=density). Solo visual:
// no modifica geometría ni el resultado. Para volver atrás: borrar + uso en
// App/CadViewport/RightPanel.
export interface DensityField {
  positions: number[];
  indices: number[];
  values: number[];
  min: number;
  max: number;
}

export interface FeaResults {
  // PROMPT-FIX (reversible): null = "sin resultados" (la UI muestra "—").
  // mapFeaResult solo asigna numeros reales; el estado inicial es todo null.
  maxVonMisesMpa: number | null;
  minSafetyFactor: number | null;
  maxDisplacementMm: number | null;
  modalFreqHz?: number | null; // ausente o null si no hay analisis modal -> "—"
  strainEnergyJ: number | null;
  meshQualityPercent: number | null;
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
  // MULTI-KEY (reversible): clave de la librería del backend para re-activar
  // el modelo exacto (switchModel) sin re-importar por nombre de archivo
  // (que falla si el archivo no está en las carpetas de fixtures).
  key?: string;
}

// SOLIDS (reversible): cuerpo del STEP segun core list_solids.
export interface SolidInfo {
  solid_id: string;
  index: number;
  name: string;
  volume?: number | null; // mm3 (core) — puede venir null
  faces_count: number;
  center?: [number, number, number] | null;
  // MULTI-VIEW (reversible): face_index globales del solido (para separar la
  // malla por cuerpo). Para volver atras: borrar + uso en realdata/App.
  face_indices?: number[] | null;
}

// MULTI-VIEW (reversible): cuerpo visible en el viewport unico.
// faceIndices null = archivo completo (sin split por solido).
export interface ViewBody {
  key: string; // `${filename}::${solid_id}`
  filename: string;
  solidId: string;
  faceIndices: number[] | null;
}
