// Mapeo de datos REALES del backend (Topologia_Optimizada) a los tipos de la UI.
// Solo transforma numeros; no toca componentes ni estilos. Si un dato no
// existe en el core, se devuelve undefined y la UI muestra "—".

import {
  BoundaryCondition,
  CadModelPreset,
  FeaResults,
  Material,
  OptimizationState,
} from '../types';

const PALETTE = ['#89ceff', '#94a3b8', '#cbd5e1', '#f59e0b', '#7bd0ff'];

function num(v: unknown): number | undefined {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return typeof n === 'number' && Number.isFinite(n) ? n : undefined;
}

export interface ApiMaterial {
  name: string;
  young_modulus: number; // Pa
  poisson_ratio: number;
  density: number; // kg/m3
  yield_strength: number; // Pa
  source?: string;
}

/** Materiales reales del core (Pa, kg/m3) -> UI (GPa, g/cm3, MPa). */
export function mapMaterials(apiMats: unknown[]): Material[] {
  const out: Material[] = [];
  (apiMats ?? []).forEach((m, i) => {
    const r = m as ApiMaterial;
    const E = num(r?.young_modulus);
    const nu = num(r?.poisson_ratio);
    const rho = num(r?.density);
    const sy = num(r?.yield_strength);
    if (!r?.name || E === undefined || nu === undefined || rho === undefined || sy === undefined) return;
    out.push({
      id: r.name.toLowerCase().replace(/[^a-z0-9]+/g, '_'),
      name: r.name,
      category: r.source ?? 'Core Topologia_Optimizada',
      youngModulus: E / 1e9,
      poissonRatio: nu,
      yieldStrength: sy / 1e6,
      density: rho / 1000,
      // El core no expone resistencia a traccion: se deja ausente ("—" en UI).
      tensileStrength: undefined,
      color: PALETTE[i % PALETTE.length],
      description: r.source ?? 'Material del core',
    });
  });
  return out;
}

export interface ApiSnapshot {
  model_name?: string | null;
  has_mesh?: boolean;
  has_result?: boolean;
  material?: string | null;
  num_faces?: number;
  num_triangles?: number;
  num_vertices?: number;
  num_nodes?: number;
  num_elements?: number;
  num_solids?: number; // SOLIDS (reversible): cuerpos reales del STEP
  volume_cm3?: number;
}

/** Snapshot real -> preset de modelo para el arbol (sin inventar cifras). */
export function mapSnapshotToModel(
  snap: ApiSnapshot,
  filename: string,
  displayName: string,
): CadModelPreset {
  return {
    id: `real_${filename}`,
    filename,
    displayName,
    faces: Math.round(num(snap?.num_faces) ?? 0),
    edges: 0, // la teselacion no expone aristas B-Rep
    // SOLIDS (reversible): conteo real de cuerpos en vez del 1 fijo.
    solids: Math.round(num(snap?.num_solids) ?? (snap?.model_name ? 1 : 0)),
    volumeCm3: num(snap?.volume_cm3) ?? 0,
    elementsTet4: Math.round(num(snap?.num_elements) ?? 0),
    nodes: Math.round(num(snap?.num_nodes) ?? 0),
  };
}

/** Resultado FEA real (unidades SI del core) -> panel de analisis. */
export function mapFeaResult(res: unknown, yieldMpa: number): FeaResults | null {
  const r = (res ?? {}) as Record<string, unknown>;
  const nodal = Array.isArray(r.nodal_von_mises) ? (r.nodal_von_mises as number[]) : [];
  const maxVmPa = nodal.length ? Math.max(...nodal.filter((v) => Number.isFinite(v))) : num(r.max_von_mises);
  const maxDisp = num(r.max_displacement);
  const strain = num(r.total_strain_energy);
  if (maxVmPa === undefined || maxDisp === undefined || strain === undefined) return null;
  const maxVmMpa = maxVmPa / 1e6;
  return {
    maxVonMisesMpa: maxVmMpa,
    minSafetyFactor: maxVmMpa > 0 ? yieldMpa / maxVmMpa : 0,
    maxDisplacementMm: maxDisp,
    modalFreqHz: undefined, // sin analisis modal cableado
    strainEnergyJ: strain,
    meshQualityPercent: num(r.mesh_quality_percent) ?? 0,
  };
}

/** Resultado SIMP real (historiales del core) -> estado de optimizacion. */
export function mapSimpResult(
  res: unknown,
  prev: OptimizationState,
  initialMassKg: number,
): OptimizationState | null {
  const r = (res ?? {}) as Record<string, unknown>;
  const compHist = Array.isArray(r.compliance_history) ? (r.compliance_history as number[]) : [];
  const volHist = Array.isArray(r.volume_fraction_history)
    ? (r.volume_fraction_history as number[])
    : [];
  const iters = num(r.iterations) ?? compHist.length;
  const finalVol = num(r.final_volume_fraction) ?? volHist[volHist.length - 1];
  const finalComp = num(r.final_compliance) ?? compHist[compHist.length - 1];
  if (finalVol === undefined || finalComp === undefined || !iters) return null;
  const total = Math.max(1, Math.round(iters));
  const vols = volHist.length ? volHist : [1, finalVol];
  const comps = compHist.length ? compHist : [finalComp];
  return {
    ...prev,
    isRunning: false,
    isPaused: false,
    currentIteration: total,
    totalIterations: total,
    currentCompliance: finalComp,
    currentVolume: finalVol,
    convergenceDelta: num(r.max_density_change) ?? 0,
    initialMassKg,
    currentMassKg: initialMassKg * finalVol,
    complianceHistory: comps,
    volumeHistory: vols,
  };
}

/** Vector de carga de la UI [Fx,Fy,Fz] -> direccion + magnitud para setBoundaries. */
export function mapLoadToBoundaries(bcs: BoundaryCondition[]): {
  load_dir: [number, number, number];
  magnitude: number;
} {
  const load = bcs.find((c) => c.type === 'carga' && c.active);
  const v = load?.value ?? [0, 0, 1000];
  const mag = Math.hypot(v[0], v[1], v[2]) || 1000;
  return { load_dir: [v[0] / mag, v[1] / mag, v[2] / mag], magnitude: mag };
}

export function prettyName(filename: string): string {
  return filename.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').toUpperCase();
}

// SOLIDS-START (reversible): lista de cuerpos del core -> UI.
// Para volver atras: borrar hasta SOLIDS-END + su uso en App/LeftPanel.
import type { SolidInfo } from '../types';

export function mapSolids(apiSolids: unknown): SolidInfo[] {
  const out: SolidInfo[] = [];
  (Array.isArray(apiSolids) ? apiSolids : []).forEach((s) => {
    const r = (s ?? {}) as Record<string, unknown>;
    if (typeof r.solid_id !== 'string') return;
    out.push({
      solid_id: r.solid_id,
      index: typeof r.index === 'number' ? Math.round(r.index) : out.length,
      name: typeof r.name === 'string' ? r.name : r.solid_id,
      volume: num(r.volume) ?? null,
      faces_count: Math.round(num(r.faces_count) ?? 0),
      center: Array.isArray(r.center) ? (r.center as [number, number, number]) : null,
    });
  });
  return out;
}
// SOLIDS-END

// NAV-VIEW-START (reversible): superficie real del backend para el viewport.
// getMeshPreview devuelve la teselacion del core (vertices xyz planos +
// indices). Los arrays grandes viajan diezmados como
// {__ndarray__: true, shape, data}; los chicos como listas planas.
// Para volver atras: borrar hasta NAV-VIEW-END + su uso en App/CadViewport.
export interface RealSurface {
  positions: number[]; // xyz xyz ...
  indices: number[]; // a b c a b c ...
  numVertices: number;
  numTriangles: number;
}

function decodeCleanArray(v: unknown): number[] {
  if (Array.isArray(v)) return (v as unknown[]).filter((x) => typeof x === 'number') as number[];
  if (v && typeof v === 'object') {
    const o = v as { __ndarray__?: boolean; data?: unknown };
    if (o.__ndarray__ && Array.isArray(o.data)) {
      return (o.data as unknown[]).filter((x) => typeof x === 'number') as number[];
    }
  }
  return [];
}

export function mapMeshPreview(mesh: unknown): RealSurface | null {
  const m = (mesh ?? {}) as Record<string, unknown>;
  const positions = decodeCleanArray(m.vertices ?? m.positions);
  const rawIdx = decodeCleanArray(m.indices);
  const indices = rawIdx.map((x) => Math.round(x));
  const numVertices = Math.floor(positions.length / 3);
  const numTriangles = Math.floor(indices.length / 3);
  if (numVertices < 1 || numTriangles < 1) return null;
  if (positions.length < numVertices * 3 || indices.length < numTriangles * 3) return null;
  return {
    positions: positions.slice(0, numVertices * 3),
    indices: indices.slice(0, numTriangles * 3),
    numVertices,
    numTriangles,
  };
}
// NAV-VIEW-END
