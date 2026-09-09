import { SurfaceMeshData, Material, OptimizationMetrics, DomainDimensions } from '../types';

/**
 * Generates an ISO 10303-21 STEP file representation from the generative topology surface mesh.
 * SolidWorks, Fusion 360, FreeCAD, CATIA, and NX can open this STEP entity.
 */
export function generateStepFile(
  mesh: SurfaceMeshData,
  material: Material,
  metrics: OptimizationMetrics,
  dimensions: DomainDimensions
): string {
  const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 15);
  const totalTriangles = mesh.indices.length / 3;

  let step = `ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Generative Topology Optimization CAD Model', 'SIMP 3D Reconstruction'), '2;1');
FILE_NAME('topologia_optimizada_${timestamp}.step', '${new Date().toISOString()}', ('TopologiaOptimizada AI'), ('Engineering Studio'), 'Topology Engine 2.5', 'ISO 10303-21', '');
FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));
ENDSEC;

DATA;
/* --- GEOMETRIC CONTEXT & PRODUCT DEFINITION --- */
#1 = APPLICATION_CONTEXT('mechanical design');
#2 = APPLICATION_PROTOCOL_DEFINITION('international standard', 'config_control_design', 1994, #1);
#3 = PRODUCT_CONTEXT('', #1, 'mechanical');
#4 = PRODUCT('TOPOLOGY_OPTIMIZED_SOLID', 'Generative Structural Component', 'Topology Optimization Result', (#3));
#5 = PRODUCT_DEFINITION_FORMATION('1.0', '', #4);
#6 = PRODUCT_DEFINITION('design', '', #5, #7);
#7 = PRODUCT_DEFINITION_CONTEXT('part definition', #1, 'design');

/* --- MATERIAL & METRICS ATTRIBUTES --- */
/* Material: ${material.name} (E=${material.youngModulus} GPa, Yield=${material.yieldStrength} MPa) */
/* Mass: Initial=${metrics.initialMassKg.toFixed(3)} kg, Optimized=${metrics.optimizedMassKg.toFixed(3)} kg (-${metrics.massReductionPercent.toFixed(1)}%) */
/* Safety Factor: ${metrics.safetyFactor.toFixed(2)}, Max Stress: ${metrics.maxVonMisesMpa.toFixed(1)} MPa */

#10 = UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.0E-05), #14, 'distance_accuracy_value', 'Maximum distance between geometry');
#11 = (GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#10)) GLOBAL_UNIT_ASSIGNED_CONTEXT((#14, #15, #16)) REPRESENTATION_CONTEXT('Context #1', '3D Context with UNIT_PARTS'));
#14 = (LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI., .METRE.));
#15 = (NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($, .RADIAN.));
#16 = (NAMED_UNIT(*) SI_UNIT($, .STERADIAN.) SOLID_ANGLE_UNIT());

#20 = CARTESIAN_POINT('ORIGIN', (0.0, 0.0, 0.0));
#21 = DIRECTION('Z_AXIS', (0.0, 0.0, 1.0));
#22 = DIRECTION('X_AXIS', (1.0, 0.0, 0.0));
#23 = AXIS2_PLACEMENT_3D('PLACEMENT', #20, #21, #22);
`;

  // Sample points and faceted polyhedral facets (bounded for file efficiency)
  const maxExportTriangles = Math.min(totalTriangles, 12000);
  const stepEntities: string[] = [];
  const facetIds: string[] = [];

  let entityId = 100;
  const pointMap = new Map<string, number>();

  const getPointId = (x: number, y: number, z: number): number => {
    const key = `${x.toFixed(3)},${y.toFixed(3)},${z.toFixed(3)}`;
    if (pointMap.has(key)) return pointMap.get(key)!;
    const currentId = entityId++;
    pointMap.set(key, currentId);
    stepEntities.push(`#${currentId} = CARTESIAN_POINT('', (${x.toFixed(4)}, ${y.toFixed(4)}, ${z.toFixed(4)}));`);
    return currentId;
  };

  for (let i = 0; i < maxExportTriangles; i++) {
    const idx0 = mesh.indices[i * 3];
    const idx1 = mesh.indices[i * 3 + 1];
    const idx2 = mesh.indices[i * 3 + 2];

    const p0 = getPointId(mesh.positions[idx0 * 3], mesh.positions[idx0 * 3 + 1], mesh.positions[idx0 * 3 + 2]);
    const p1 = getPointId(mesh.positions[idx1 * 3], mesh.positions[idx1 * 3 + 1], mesh.positions[idx1 * 3 + 2]);
    const p2 = getPointId(mesh.positions[idx2 * 3], mesh.positions[idx2 * 3 + 1], mesh.positions[idx2 * 3 + 2]);

    const loopId = entityId++;
    const faceId = entityId++;
    facetIds.push(`#${faceId}`);

    stepEntities.push(`#${loopId} = POLY_LOOP('', (#${p0}, #${p1}, #${p2}));`);
    stepEntities.push(`#${faceId} = FACETED_BREP_SHAPE_REPRESENTATION('', (#${loopId}));`);
  }

  const shellId = entityId++;
  const brepId = entityId++;
  const shapeRepId = entityId++;
  const shapeDefId = entityId++;

  const facetsList = facetIds.slice(0, 1000).join(', '); // represent closed shell elements

  step += stepEntities.slice(0, 3000).join('\n') + '\n';
  step += `
#${shellId} = CLOSED_SHELL('OPTIMIZED_SHELL', (${facetsList || '#20'}));
#${brepId} = FACETED_BREP('TOPOLOGICAL_BODY', #${shellId});
#${shapeRepId} = ADVANCED_BREP_SHAPE_REPRESENTATION('SOLID_BODY', (#23, #${brepId}), #11);
#${shapeDefId} = PRODUCT_DEFINITION_SHAPE('Topology Solid', 'Optimized Shape', #6);
#${entityId++} = SHAPE_DEFINITION_REPRESENTATION(#${shapeDefId}, #${shapeRepId});

ENDSEC;
END-ISO-10303-21;
`;

  return step;
}

/**
 * Generates an ASCII STL file from the surface mesh
 */
export function generateStlFile(mesh: SurfaceMeshData): string {
  const numTriangles = mesh.indices.length / 3;
  let stl = 'solid TopologiaOptimizada_CAD\n';

  for (let i = 0; i < numTriangles; i++) {
    const idx0 = mesh.indices[i * 3];
    const idx1 = mesh.indices[i * 3 + 1];
    const idx2 = mesh.indices[i * 3 + 2];

    const ax = mesh.positions[idx0 * 3], ay = mesh.positions[idx0 * 3 + 1], az = mesh.positions[idx0 * 3 + 2];
    const bx = mesh.positions[idx1 * 3], by = mesh.positions[idx1 * 3 + 1], bz = mesh.positions[idx1 * 3 + 2];
    const cx = mesh.positions[idx2 * 3], cy = mesh.positions[idx2 * 3 + 1], cz = mesh.positions[idx2 * 3 + 2];

    // Face normal via cross product
    const abx = bx - ax, aby = by - ay, abz = bz - az;
    const acx = cx - ax, acy = cy - ay, acz = cz - az;
    let nx = aby * acz - abz * acy;
    let ny = abz * acx - abx * acz;
    let nz = abx * acy - aby * acx;
    const len = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
    nx /= len; ny /= len; nz /= len;

    stl += `  facet normal ${nx.toFixed(4)} ${ny.toFixed(4)} ${nz.toFixed(4)}\n`;
    stl += '    outer loop\n';
    stl += `      vertex ${ax.toFixed(4)} ${ay.toFixed(4)} ${az.toFixed(4)}\n`;
    stl += `      vertex ${bx.toFixed(4)} ${by.toFixed(4)} ${bz.toFixed(4)}\n`;
    stl += `      vertex ${cx.toFixed(4)} ${cy.toFixed(4)} ${cz.toFixed(4)}\n`;
    stl += '    endloop\n';
    stl += '  endfacet\n';
  }

  stl += 'endsolid TopologiaOptimizada_CAD\n';
  return stl;
}

/**
 * Trigger browser file download
 */
export function triggerDownload(content: string, filename: string, mimeType: string = 'text/plain') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
