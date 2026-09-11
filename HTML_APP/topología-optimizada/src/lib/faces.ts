// FACES-START (reversible): seleccion de caras B-Rep en el viewport web.
//
// Copia adaptada de Topologia_Optimizada (SOLO LECTURA, no se modifica):
// - parseFaceId         <- core/boundary.py::_FACE_ID_UNIFIED_RE + parse_face_id
//                         ("face_3", "face:3", "face3", "face-3", "3" -> 3)
// - triangleToFace      <- desktop/viewport/scene.py::face_index_for_cell
//                         (triangulo del teselado -> cara B-Rep via rangos)
// - toggleFace          <- desktop/viewport/software_viewport.py (click alterna:
//                         si la cara esta, se quita; si no, se añade)
// - faceEntityRef       <- core/cad_entity.py::CadEntityRef.from_face().to_dict()
// - selectionSet        <- core/cad_entity.py::SelectionSet.to_dict()
// - buildConditionJson  <- core/conditions.py::to_dict() de LoadCondition,
//                         ElasticityCondition y ProtectedRegion (mismas claves
//                         que espera condition_from_dict en el backend).
// Para volver atras: borrar este archivo + su uso en CadViewport/App/realdata.

export interface FaceMeta {
  face_index: number;
  id: string;
  area?: number | null;
  center?: [number, number, number] | null;
  normal?: [number, number, number] | null;
}

/** Rango de triangulos del teselado que pertenecen a una cara B-Rep.
 *  Copia de `face_triangles` del core: {face_index, start, count}. */
export interface FaceRange {
  face_index: number;
  start: number;
  count: number;
}

// core/boundary.py::_FACE_ID_UNIFIED_RE
const FACE_ID_RE = /^(?:face[_:\-\s]?)?(\d+)$/i;

/** "face_3" | "face:3" | "face3" | "3" -> 3; null si no es identificable. */
export function parseFaceId(faceId: unknown): number | null {
  if (faceId === null || faceId === undefined) return null;
  const m = FACE_ID_RE.exec(String(faceId).trim());
  return m ? parseInt(m[1], 10) : null;
}

/** Indice de triangulo del teselado -> indice de cara B-Rep.
 *  Equivale a Scene.face_index_for_cell del desktop: el core ordena los
 *  triangulos por cara y `face_triangles` da los rangos [start, start+count).
 *  Fuera de rango -> null (como celda sin cara: se conserva la seleccion). */
export function triangleToFace(triIndex: number, ranges: FaceRange[]): number | null {
  if (!Number.isInteger(triIndex) || triIndex < 0) return null;
  for (const r of ranges) {
    if (triIndex >= r.start && triIndex < r.start + r.count) return r.face_index;
  }
  return null;
}

/** Alterna una cara en la seleccion (click añade / re-click quita). */
export function toggleFace(selected: number[], faceIndex: number): number[] {
  return selected.includes(faceIndex)
    ? selected.filter((f) => f !== faceIndex)
    : [...selected, faceIndex];
}

/** Referencia estable a una cara, formato CadEntityRef serializado. */
export function faceEntityRef(
  faceIndex: number,
  modelId?: string | null,
  meta?: FaceMeta | null,
): Record<string, unknown> {
  const d: Record<string, unknown> = {
    entity_type: 'face',
    face_index: faceIndex,
  };
  if (modelId) d.model_id = modelId;
  if (meta?.center) d.coordinates = [...meta.center];
  const metadata: Record<string, unknown> = {};
  if (meta?.normal) metadata.normal = [...meta.normal];
  if (typeof meta?.area === 'number') metadata.area = meta.area;
  if (Object.keys(metadata).length > 0) d.metadata = metadata;
  return d;
}

/** Grupo de caras, formato SelectionSet serializado ({id, name, entities, mode}). */
export function selectionSet(
  name: string,
  faceIndices: number[],
  modelId?: string | null,
  metas?: FaceMeta[] | null,
): Record<string, unknown> {
  const byIndex = new Map((metas ?? []).map((m) => [m.face_index, m]));
  return {
    name,
    entities: faceIndices.map((f) => faceEntityRef(f, modelId, byIndex.get(f) ?? null)),
    mode: 'multi',
  };
}

export type FaceTool = 'carga' | 'fijacion' | 'preservada';

/** JSON de condicion con caras, mismas claves que core/conditions.py::to_dict().
 *  El backend lo acepta via createCondition -> condition_from_dict.
 *  keepout NO esta aqui: en el core la obstruccion referencia CUERPOS
 *  (bodies), no caras — su seleccion queda local en la UI (ver App). */
export function buildConditionJson(
  tool: FaceTool,
  name: string,
  faceIndices: number[],
  modelId?: string | null,
  metas?: FaceMeta[] | null,
  magnitude?: number | null,
  // LOAD-DIR (reversible): normal de referencia (core reference_plane_normal,
  // orientacion perpendicular). Por defecto [0,0,1] como antes.
  referenceNormal?: [number, number, number] | null,
): Record<string, unknown> {
  if (tool === 'carga') {
    return {
      type: 'load',
      name,
      faces: selectionSet('Caras de carga', faceIndices, modelId, metas),
      orientation: 'perpendicular',
      reference_plane_normal: referenceNormal ?? [0.0, 0.0, 1.0],
      angle_deg: null,
      sense: 'indeterminate',
      magnitude: typeof magnitude === 'number' ? magnitude : null,
      indeterminate: typeof magnitude !== 'number',
      unit: 'N',
      metadata: {},
    };
  }
  if (tool === 'fijacion') {
    return {
      type: 'elasticity',
      name,
      faces: selectionSet('Caras de elasticidad', faceIndices, modelId, metas),
      flex_range_mm: null,
      metadata: {},
    };
  }
  return {
    type: 'protected_region',
    name,
    faces: selectionSet('Caras protegidas', faceIndices, modelId, metas),
    geometry_refs: [],
    metadata: {},
  };
}

/** Etiqueta corta para el arbol: "3 caras: face_0, face_2, face_5". */
export function facesLabel(faceIndices: number[]): string {
  if (faceIndices.length === 0) return 'sin caras';
  const ids = [...faceIndices].sort((a, b) => a - b).map((f) => `face_${f}`);
  return `${faceIndices.length} cara${faceIndices.length > 1 ? 's' : ''}: ${ids.join(', ')}`;
}
/** Los rangos cubren todo el teselado (sin diezmar)? Solo entonces el
 *  picking triangulo->cara es fiable: el backend diezma arrays grandes
 *  (_clean) y los rangos quedarian desalineados. */
export function rangesCover(ranges: FaceRange[], numTriangles: number): boolean {
  if (ranges.length === 0 || numTriangles < 1) return false;
  const total = ranges.reduce((acc, r) => acc + Math.max(0, r.count), 0);
  return total === numTriangles;
}

/** Clave estable de cuerpo para visibilidad (arbol + viewport). */
export function bodyKey(filename: string, solidId: string): string {
  return `${filename}::${solidId}`;
}

/** Triangulos globales del teselado que pertenecen a un solido, a partir de
 *  sus caras (face_indices del core) y los rangos triangulo->cara.
 *  null si no se puede separar (sin caras o rangos incompletos). */
export function solidTriangles(
  faceIndices: number[] | null | undefined,
  ranges: FaceRange[],
  numTriangles: number,
): number[] | null {
  if (!faceIndices || faceIndices.length === 0) return null;
  if (!rangesCover(ranges, numTriangles)) return null;
  const byFace = new Map(ranges.map((r) => [r.face_index, r]));
  const tris: number[] = [];
  for (const f of [...faceIndices].sort((a, b) => a - b)) {
    const r = byFace.get(f);
    if (!r) return null; // cara sin rango: no separar (evita agujeros)
    for (let t = r.start; t < r.start + r.count; t += 1) tris.push(t);
  }
  return tris.length > 0 ? tris : null;
}
// FACES-END
