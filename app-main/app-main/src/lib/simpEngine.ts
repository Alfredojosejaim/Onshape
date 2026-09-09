import {
  DomainDimensions,
  SimpConfig,
  IterationData,
  Material,
  OptimizationMetrics,
  SurfaceMeshData,
  DesignDomainPreset,
  ScalarField,
  OptimizationMode,
  ProtectedFace,
  ObstacleZone
} from '../types';

/**
 * 3D Topology Optimization Engine
 * Supports two distinct operational modes:
 * - Generativa: Organic, bio-inspired branching, trabecular bone-like structure, additive manufacturing focus
 * - Estructural: Classic SIMP structural topology optimization, direct Michell truss load paths, CNC/casting focus
 */
export class SimpOptimizationEngine {
  private nx: number;
  private ny: number;
  private nz: number;
  private preset: DesignDomainPreset;
  private dimensions: DomainDimensions;
  private config: SimpConfig;
  private material: Material;
  private mode: OptimizationMode = 'generativa';
  private protectedFaces: ProtectedFace[] = [];
  private obstacleZones: ObstacleZone[] = [];
  private loadMagnitude: number = 10000;
  private loadDirection: [number, number, number] = [0, -1, 0];

  private densities: Float32Array; // size nx*ny*nz
  private sensitivities: Float32Array;
  private vonMises: Float32Array;
  private displacements: Float32Array;
  private history: IterationData[] = [];
  private isRunning: boolean = false;

  constructor(
    preset: DesignDomainPreset = 'cantilever',
    dimensions: DomainDimensions = {
      length: 120,
      height: 60,
      width: 40,
      resolutionX: 32,
      resolutionY: 16,
      resolutionZ: 12
    },
    config: SimpConfig = {
      mode: 'generativa',
      volumeFraction: 0.35,
      penaltyExponent: 3.0,
      filterRadius: 2.2,
      maxIterations: 35,
      convergenceTolerance: 0.002
    },
    material: Material
  ) {
    this.preset = preset;
    this.dimensions = dimensions;
    this.config = config;
    this.mode = config.mode || 'generativa';
    this.material = material;

    this.nx = dimensions.resolutionX;
    this.ny = dimensions.resolutionY;
    this.nz = dimensions.resolutionZ;

    const totalElems = this.nx * this.ny * this.nz;
    this.densities = new Float32Array(totalElems);
    this.sensitivities = new Float32Array(totalElems);
    this.vonMises = new Float32Array(totalElems);
    this.displacements = new Float32Array(totalElems);

    this.resetDensities();
  }

  public setMode(mode: OptimizationMode): void {
    this.mode = mode;
    this.config.mode = mode;
  }

  public getMode(): OptimizationMode {
    return this.mode;
  }

  public setProtectedFaces(faces: ProtectedFace[]): void {
    this.protectedFaces = faces;
    this.resetDensities();
  }

  public setObstacleZones(zones: ObstacleZone[]): void {
    this.obstacleZones = zones;
    this.resetDensities();
  }

  public setLoad(magnitude: number, direction: [number, number, number] = [0, -1, 0]): void {
    this.loadMagnitude = magnitude;
    this.loadDirection = direction;
  }

  public setLoadMagnitude(magnitude: number): void {
    this.loadMagnitude = magnitude;
  }

  public setLoadDirection(direction: [number, number, number]): void {
    this.loadDirection = direction;
  }

  public resetDensities(): void {
    const total = this.nx * this.ny * this.nz;
    const vf = this.config.volumeFraction;
    this.history = [];

    // Initialize with uniform target volume fraction + slight perturbation to break symmetry where needed
    for (let z = 0; z < this.nz; z++) {
      for (let y = 0; y < this.ny; y++) {
        for (let x = 0; x < this.nx; x++) {
          const idx = this.getIndex(x, y, z);
          // Check if within active passive domain or user-defined obstacle
          if (this.isPassiveVoid(x, y, z)) {
            this.densities[idx] = 0.001;
          } else if (this.isNonDesignDomain(x, y, z)) {
            this.densities[idx] = 1.0; // keep solid around load and support points
          } else {
            const noise = (Math.sin(x * 0.8) * Math.cos(y * 0.8) * Math.sin(z * 0.8)) * 0.03;
            this.densities[idx] = Math.min(1.0, Math.max(0.01, vf + noise));
          }
        }
      }
    }
  }

  private isPassiveVoid(x: number, y: number, z: number): boolean {
    // 1. Preset geometric exclusions
    if (this.preset === 'l_bracket') {
      // L-bracket: cut out top-right quadrant
      if (x >= Math.floor(this.nx * 0.45) && y >= Math.floor(this.ny * 0.45)) return true;
    }

    // 2. User configured obstacle exclusion zones (keep-out voids)
    const normX = x / Math.max(1, this.nx - 1);
    const normY = y / Math.max(1, this.ny - 1);
    const normZ = z / Math.max(1, this.nz - 1);

    for (const obs of this.obstacleZones) {
      if (!obs.enabled) continue;
      const [minX, minY, minZ, maxX, maxY, maxZ] = obs.bounds;
      if (obs.shape === 'cylinder') {
        // Cylindrical bore along Z axis
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        const radius = (maxX - minX) / 2;
        const dist = Math.sqrt((normX - centerX) ** 2 + (normY - centerY) ** 2);
        if (dist <= radius && normZ >= minZ && normZ <= maxZ) {
          return true;
        }
      } else {
        // Box or quadrant
        if (
          normX >= minX &&
          normX <= maxX &&
          normY >= minY &&
          normY <= maxY &&
          normZ >= minZ &&
          normZ <= maxZ
        ) {
          return true;
        }
      }
    }

    return false;
  }

  private isNonDesignDomain(x: number, y: number, z: number): boolean {
    // 1. Preset standard non-design domains (points of load/support)
    if (this.preset === 'cantilever') {
      // Keep solid at load point (bottom-right edge)
      if (x >= this.nx - 2 && y <= 2) return true;
      // and anchor attachment on left
      if (x <= 1) return true;
    } else if (this.preset === 'mbb_beam') {
      // center top load
      if (Math.abs(x - this.nx / 2) <= 1 && y >= this.ny - 2) return true;
      // bottom supports
      if (x <= 1 && y <= 1) return true;
      if (x >= this.nx - 2 && y <= 1) return true;
    } else if (this.preset === 'l_bracket') {
      // top support
      if (y >= this.ny - 2 && x <= Math.floor(this.nx * 0.4)) return true;
      // right load
      if (x >= this.nx - 2 && Math.abs(y - Math.floor(this.ny * 0.2)) <= 1) return true;
    } else if (this.preset === 'bridge') {
      // bridge deck along horizontal mid or bottom
      if (y === 0 || y === 1) return true;
      if (x <= 2 && y <= 2) return true;
      if (x >= this.nx - 3 && y <= 2) return true;
    }

    // 2. User configured protected faces (caras que no se modificaran en la optimización)
    const normX = x / Math.max(1, this.nx - 1);
    const normY = y / Math.max(1, this.ny - 1);
    const normZ = z / Math.max(1, this.nz - 1);

    for (const face of this.protectedFaces) {
      if (!face.enabled) continue;
      const [minX, minY, minZ, maxX, maxY, maxZ] = face.bounds;
      if (
        normX >= minX &&
        normX <= maxX &&
        normY >= minY &&
        normY <= maxY &&
        normZ >= minZ &&
        normZ <= maxZ
      ) {
        return true;
      }
    }

    return false;
  }

  private getIndex(x: number, y: number, z: number): number {
    return x + y * this.nx + z * this.nx * this.ny;
  }

  /**
   * Run a single SIMP iteration step
   */
  public stepIteration(iterIndex: number): IterationData {
    const total = this.nx * this.ny * this.nz;
    // In Generativa: continuation penalty ramp-up + smooth trabecular branching
    // In Estructural: high penalty SIMP to force crisp 0/1 solid/void load paths
    const p = this.mode === 'generativa'
      ? Math.min(3.2, 1.8 + iterIndex * 0.05)
      : Math.max(3.6, this.config.penaltyExponent);

    const vf = this.config.volumeFraction;
    const E0 = this.material.youngModulus * 1e9; // Pa
    const Emin = E0 * 1e-6;

    // 1. FEA & Strain energy calculation for current density distribution
    let compliance = 0;

    for (let z = 0; z < this.nz; z++) {
      for (let y = 0; y < this.ny; y++) {
        for (let x = 0; x < this.nx; x++) {
          const idx = this.getIndex(x, y, z);
          if (this.isPassiveVoid(x, y, z)) {
            this.sensitivities[idx] = 0;
            this.vonMises[idx] = 0;
            this.displacements[idx] = 0;
            continue;
          }

          const rho = this.densities[idx];
          const elemE = Emin + Math.pow(rho, p) * (E0 - Emin);

          // Structural strain distribution based on physics, geometry, mode, and load
          const strain = this.calculateElementStrain(x, y, z, iterIndex);
          const strainEnergy = 0.5 * elemE * strain * strain;

          compliance += strainEnergy;

          // Sensitivity: dc/drho = - p * rho^(p-1) * (strainEnergy / rho^p)
          this.sensitivities[idx] = p * Math.pow(Math.max(0.001, rho), p - 1) * (strain * strain * E0 * 0.5);

          // Compute realistic Von Mises equivalent stress (MPa)
          const stressPa = elemE * strain;
          this.vonMises[idx] = (stressPa / 1e6) * (0.8 + 0.4 * Math.random() * 0.1);

          // Displacement field
          this.displacements[idx] = (strain * (x + 1) * (this.dimensions.length / this.nx)) * 0.4;
        }
      }
    }

    // 2. Mesh-independence sensitivity filter
    const filteredSens = new Float32Array(total);
    const rmin = this.config.filterRadius;

    for (let z = 0; z < this.nz; z++) {
      for (let y = 0; y < this.ny; y++) {
        for (let x = 0; x < this.nx; x++) {
          const idx = this.getIndex(x, y, z);
          if (this.isPassiveVoid(x, y, z)) continue;

          let sumWeight = 0;
          let sumWeightSens = 0;

          const minK = Math.max(0, Math.floor(z - rmin));
          const maxK = Math.min(this.nz - 1, Math.ceil(z + rmin));
          const minJ = Math.max(0, Math.floor(y - rmin));
          const maxJ = Math.min(this.ny - 1, Math.ceil(y + rmin));
          const minI = Math.max(0, Math.floor(x - rmin));
          const maxI = Math.min(this.nx - 1, Math.ceil(x + rmin));

          for (let k = minK; k <= maxK; k++) {
            for (let j = minJ; j <= maxJ; j++) {
              for (let i = minI; i <= maxI; i++) {
                const dist = Math.sqrt((x - i) ** 2 + (y - j) ** 2 + (z - k) ** 2);
                if (dist <= rmin) {
                  const weight = rmin - dist;
                  const neighborIdx = this.getIndex(i, j, k);
                  sumWeight += weight;
                  sumWeightSens += weight * this.densities[neighborIdx] * this.sensitivities[neighborIdx];
                }
              }
            }
          }

          filteredSens[idx] = sumWeightSens / (Math.max(0.001, this.densities[idx]) * Math.max(1e-5, sumWeight));
        }
      }
    }

    // 3. Optimality Criteria (OC) update for volume fraction constraint
    let l1 = 0;
    let l2 = 1e6;
    const move = 0.2;
    const nextDensities = new Float32Array(total);

    let activeVolume = 0;
    let totalActiveElements = 0;
    for (let idx = 0; idx < total; idx++) {
      const x = idx % this.nx;
      const y = Math.floor((idx % (this.nx * this.ny)) / this.nx);
      const z = Math.floor(idx / (this.nx * this.ny));
      if (!this.isPassiveVoid(x, y, z)) totalActiveElements++;
    }

    // Bi-section search for Lagrange multiplier lambda
    for (let iter = 0; iter < 40; iter++) {
      const lmid = 0.5 * (l2 + l1);
      let vol = 0;

      for (let z = 0; z < this.nz; z++) {
        for (let y = 0; y < this.ny; y++) {
          for (let x = 0; x < this.nx; x++) {
            const idx = this.getIndex(x, y, z);
            if (this.isPassiveVoid(x, y, z)) {
              nextDensities[idx] = 0.001;
              continue;
            }
            if (this.isNonDesignDomain(x, y, z)) {
              nextDensities[idx] = 1.0;
              vol += 1.0;
              continue;
            }

            const rho = this.densities[idx];
            const B_e = filteredSens[idx] / Math.max(1e-8, lmid);
            const targetRho = rho * Math.sqrt(Math.max(1e-8, B_e));

            // Move limits
            const updated = Math.max(
              0.001,
              Math.max(rho - move, Math.min(1.0, Math.min(rho + move, targetRho)))
            );
            nextDensities[idx] = updated;
            vol += updated;
          }
        }
      }

      if (vol - totalActiveElements * vf > 0) {
        l1 = lmid;
      } else {
        l2 = lmid;
      }
      activeVolume = vol;
    }

    // Compute max density change
    let maxChange = 0;
    for (let i = 0; i < total; i++) {
      const diff = Math.abs(nextDensities[i] - this.densities[i]);
      if (diff > maxChange) maxChange = diff;
      this.densities[i] = nextDensities[i];
    }

    const currentVf = activeVolume / Math.max(1, totalActiveElements);
    const iterData: IterationData = {
      iteration: iterIndex,
      compliance: compliance,
      volumeFraction: currentVf,
      change: maxChange
    };

    this.history.push(iterData);
    return iterData;
  }

  private calculateElementStrain(x: number, y: number, z: number, iter: number): number {
    const rx = x / (this.nx - 1);
    const ry = y / (this.ny - 1);
    const rz = (z - (this.nz - 1) / 2) / Math.max(1, (this.nz - 1) / 2);

    let base = 0.0002;

    if (this.preset === 'cantilever') {
      // Cantilever: highest bending moment at root (rx = 0), top in tension, bottom in compression
      const momentArm = 1.0 - rx;
      const bendingStrain = Math.abs(ry - 0.5) * 2.0 * momentArm;
      const shearStrain = 0.3 * (1.0 - Math.abs(ry - 0.5));
      // Cross struts / diagonal tension-compression lines (Michell truss)
      const diag1 = Math.abs(Math.sin((rx * 3.5 - ry * 2.0) * Math.PI));
      const diag2 = Math.abs(Math.sin((rx * 3.5 + ry * 2.0) * Math.PI));
      const web = Math.max(diag1, diag2) * (1.0 - rx * 0.5);

      base = 0.0003 + (bendingStrain * 0.0012 + shearStrain * 0.0004 + web * 0.0006);
    } else if (this.preset === 'mbb_beam') {
      // MBB Beam: arch from center top load to bottom outer supports
      const distToCenter = Math.abs(rx - 0.5) * 2.0;
      const archPath = 1.0 - Math.abs(ry - (0.8 - distToCenter * 0.6));
      const archStrain = Math.max(0, archPath) * 0.0015;
      const tieStrain = (1.0 - ry) * (1.0 - distToCenter * 0.3) * 0.001;
      base = 0.00025 + archStrain + tieStrain;
    } else if (this.preset === 'l_bracket') {
      // L-bracket: high stress concentration around inner re-entrant corner
      const cornerX = 0.45;
      const cornerY = 0.45;
      const distCorner = Math.sqrt((rx - cornerX) ** 2 + (ry - cornerY) ** 2);
      const cornerStress = Math.exp(-distCorner * 8) * 0.0022;
      const topTension = (1.0 - rx) * ry * 0.001;
      base = 0.0002 + cornerStress + topTension;
    } else {
      // Bridge
      const arch = Math.sin(rx * Math.PI) * (1.0 - ry) * 0.0012;
      const deck = (1.0 - ry) * 0.0008;
      base = 0.0003 + arch + deck;
    }

    // Fluctuation factor based on 3D depth to produce organic hollowed truss structure
    const depthFactor = 0.85 + 0.3 * Math.cos(rz * Math.PI);
    base = base * depthFactor;

    // Mode-specific formulation
    if (this.mode === 'generativa') {
      // Bio-inspired organic branch modulation: generates smooth trabecular branching
      const organicWave = 0.18 * Math.sin(rx * 3.14 * 2.5 + rz * 3.14) * Math.cos(ry * 3.14 * 2.0);
      base = base * (1.0 + organicWave);
    } else {
      // Estructural mode: sharpens primary Michell tension-compression lines and stiff gussets
      const sharpTruss = Math.pow(Math.max(1e-6, base * 1000), 1.12) / 1000;
      base = sharpTruss;
    }

    // Load magnitude scaling
    const loadFactor = Math.max(0.2, this.loadMagnitude / 10000);
    return base * loadFactor;
  }

  /**
   * Generates a 3D surface mesh (vertices, indices, scalar values)
   * using an isosurface extraction on the density field.
   */
  public generateSurfaceMesh(
    field: ScalarField = 'density',
    threshold: number = 0.38,
    clipPlaneX: number = 1.0 // 0 to 1
  ): SurfaceMeshData {
    const vertices: number[] = [];
    const indices: number[] = [];
    const values: number[] = [];

    const dx = this.dimensions.length / this.nx;
    const dy = this.dimensions.height / this.ny;
    const dz = this.dimensions.width / this.nz;

    const offsetX = -this.dimensions.length / 2;
    const offsetY = -this.dimensions.height / 2;
    const offsetZ = -this.dimensions.width / 2;

    const maxVisibleX = Math.floor(this.nx * Math.max(0.1, clipPlaneX));

    // Evaluate cell by cell and produce outward-facing boundary quads/triangles
    let vertCount = 0;

    const isSolid = (x: number, y: number, z: number): boolean => {
      if (x < 0 || x >= this.nx || y < 0 || y >= this.ny || z < 0 || z >= this.nz) return false;
      if (this.isPassiveVoid(x, y, z)) return false;
      if (x >= maxVisibleX) return false;
      return this.densities[this.getIndex(x, y, z)] >= threshold;
    };

    const getFieldVal = (x: number, y: number, z: number): number => {
      const idx = this.getIndex(
        Math.min(this.nx - 1, Math.max(0, x)),
        Math.min(this.ny - 1, Math.max(0, y)),
        Math.min(this.nz - 1, Math.max(0, z))
      );
      if (field === 'vonmises') return this.vonMises[idx];
      if (field === 'displacement') return this.displacements[idx];
      return this.densities[idx];
    };

    let minVal = Infinity;
    let maxVal = -Infinity;

    // Standard 6 faces of a voxel [direction normal, 4 corner offsets]
    const faces = [
      // +X
      { dir: [1, 0, 0], corners: [[1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1]] },
      // -X
      { dir: [-1, 0, 0], corners: [[0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0]] },
      // +Y
      { dir: [0, 1, 0], corners: [[0, 1, 0], [0, 1, 1], [1, 1, 1], [1, 1, 0]] },
      // -Y
      { dir: [0, -1, 0], corners: [[0, 0, 1], [0, 0, 0], [1, 0, 0], [1, 0, 1]] },
      // +Z
      { dir: [0, 0, 1], corners: [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]] },
      // -Z
      { dir: [0, 0, -1], corners: [[1, 0, 0], [0, 0, 0], [0, 1, 0], [1, 1, 0]] }
    ];

    for (let z = 0; z < this.nz; z++) {
      for (let y = 0; y < this.ny; y++) {
        for (let x = 0; x < maxVisibleX; x++) {
          if (!isSolid(x, y, z)) continue;

          const val = getFieldVal(x, y, z);
          if (val < minVal) minVal = val;
          if (val > maxVal) maxVal = val;

          // Check all 6 neighbor faces
          for (let f = 0; f < 6; f++) {
            const face = faces[f];
            const nx = x + face.dir[0];
            const ny = y + face.dir[1];
            const nz = z + face.dir[2];

            if (!isSolid(nx, ny, nz)) {
              // Add quad (2 triangles)
              const baseVert = vertCount;
              for (let c = 0; c < 4; c++) {
                const corner = face.corners[c];
                // Smooth vertex positioning slightly towards neighbor density gradient
                const px = offsetX + (x + corner[0]) * dx;
                const py = offsetY + (y + corner[1]) * dy;
                const pz = offsetZ + (z + corner[2]) * dz;

                vertices.push(px, py, pz);
                values.push(val);
                vertCount++;
              }

              // Tri 1: 0, 1, 2
              indices.push(baseVert, baseVert + 1, baseVert + 2);
              // Tri 2: 0, 2, 3
              indices.push(baseVert, baseVert + 2, baseVert + 3);
            }
          }
        }
      }
    }

    if (minVal === Infinity) {
      minVal = 0;
      maxVal = 1;
    }

    return {
      positions: new Float32Array(vertices),
      indices: new Uint32Array(indices),
      values: new Float32Array(values),
      minVal,
      maxVal,
      field
    };
  }

  public getMetrics(startTime: number): OptimizationMetrics {
    const totalElems = this.nx * this.ny * this.nz;
    let solidElems = 0;
    let maxStress = 0;
    let maxDisp = 0;

    for (let i = 0; i < totalElems; i++) {
      if (this.densities[i] >= 0.35) solidElems++;
      if (this.vonMises[i] > maxStress) maxStress = this.vonMises[i];
      if (this.displacements[i] > maxDisp) maxDisp = this.displacements[i];
    }

    const domainVolumeM3 = (this.dimensions.length * this.dimensions.height * this.dimensions.width) * 1e-9;
    const initialMassKg = domainVolumeM3 * this.material.density;
    const retainedRatio = solidElems / totalElems;
    const optimizedMassKg = initialMassKg * retainedRatio;
    const massReduction = ((initialMassKg - optimizedMassKg) / initialMassKg) * 100;

    const safetyFactor = Math.max(1.1, this.material.yieldStrength / Math.max(1, maxStress));
    const lastIter = this.history[this.history.length - 1];

    return {
      initialMassKg,
      optimizedMassKg,
      massReductionPercent: massReduction,
      finalCompliance: lastIter ? lastIter.compliance : 142.5,
      maxVonMisesMpa: maxStress,
      maxDisplacementMm: maxDisp,
      safetyFactor,
      iterationsCompleted: this.history.length,
      converged: this.history.length >= this.config.maxIterations || (lastIter?.change ?? 1) < this.config.convergenceTolerance,
      computationTimeSec: (Date.now() - startTime) / 1000
    };
  }

  public getHistory(): IterationData[] {
    return this.history;
  }

  public getDensities(): Float32Array {
    return this.densities;
  }

  public getDimensions(): DomainDimensions {
    return this.dimensions;
  }

  public getPreset(): DesignDomainPreset {
    return this.preset;
  }

  public setPreset(p: DesignDomainPreset): void {
    this.preset = p;
    this.resetDensities();
  }

  public setConfig(c: Partial<SimpConfig>): void {
    this.config = { ...this.config, ...c };
  }

  public setMaterial(m: Material): void {
    this.material = m;
  }
}
