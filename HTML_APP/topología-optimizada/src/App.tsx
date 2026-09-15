/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  ActiveTab,
  ActiveTool,
  BoundaryCondition,
  CadModelPreset,
  DensityField,
  FeaResults,
  Material,
  MeshOpResult,
  MeshToolAction,
  OptimizationState,
  OptimizationType,
  SimpParameters,
  ViewBody,
} from './types';import { MATERIALS } from './data/materials';
import { CAD_PRESETS, INITIAL_CONDITIONS } from './data/models';
import { Header } from './components/Header';
import { SecondaryNav } from './components/SecondaryNav';
import { Toolbar } from './components/Toolbar';
import { LeftPanel } from './components/LeftPanel';
import { RightPanel } from './components/RightPanel';
// EXT-RAIL (reversible: borrar import + uso para volver atras).
import { ExtensionsRail } from './components/ExtensionsRail';
// CHUNK-SPLIT (reversible): el viewport arrastra three.js (~600KB);
// con lazy() va a un chunk async separado en vez del bundle inicial.
// Para volver atras: restaurar `import { CadViewport } from './components/CadViewport';`
const CadViewport = React.lazy(() =>
  import('./components/CadViewport').then((m) => ({ default: m.CadViewport }))
);
import { Footer } from './components/Footer';
import { Modals } from './components/Modals';
import { ErrorBoundary } from './components/ErrorBoundary';
import { backend } from './lib/bridge';
import { useJobPoll } from './lib/jobs';
// V2-NEW-START (reversible: borrar estas 2 lineas + bloque V2-NEW-ABAJO)
import { V2_ENABLED } from './lib/v2flags';
import { V2Panel } from './components/v2/V2Panel';
// V2-NEW-END
import {
  decodeCleanArray,
  mapFeaResult,
  mapLoadToBoundaries,
  mapMaterials,
  mapSimpResult,
  mapSnapshotToModel,
  prettyName,
  type ApiSnapshot,
} from './lib/realdata';
// FACES-START (reversible: quitar import + estado faceSelByFile + handleToggleFace
// + prop al viewport). Copia del flujo del desktop: viewport -> CadEntityRef/
// SelectionSet -> condicion reutilizable (core/conditions.py) via createCondition.
import {
  buildConditionJson,
  bodyKey,
  facesLabel,
  toggleFace,
  type FaceTool as FaceCondTool,
} from './lib/faces';
// FACES-END
// SOLIDS-START (reversible): cuerpos del STEP, uno por objeto.
import { mapSolids } from './lib/realdata';
import type { SolidInfo } from './types';
// SOLIDS-END
// NAV-VIEW-START (reversible: quitar import + estado surface + fetchSurface + prop)
import { mapMeshPreview, placeholderSurface, type RealSurface } from './lib/realdata';
// NAV-VIEW-END

export default function App() {
  // Navigation & Tools
  const [activeTab, setActiveTab] = useState<ActiveTab>('optimizacion');
  const [activeTool, setActiveTool] = useState<ActiveTool>('seleccionar');

  // CAD Models & Preset
  // UI-CLEAN-START (reversible): arranque vacio, sin presets de referencia.
  // Antes: useState(CAD_PRESETS[0]). Para volver: restaurar esa linea.
  const [models, setModels] = useState<CadModelPreset[]>([]);
  const [currentModel, setCurrentModel] = useState<CadModelPreset | null>(null);
  // UI-CLEAN-END
  const [isModelVisible, setIsModelVisible] = useState(true);

  // Material Selection (reales del backend cuando hay bridge, fallback local)
  const [materials, setMaterials] = useState<Material[]>(MATERIALS);
  const [selectedMaterial, setSelectedMaterial] = useState<Material>(MATERIALS[0]);

  // Boundary Conditions
  const [boundaryConditions, setBoundaryConditions] = useState<BoundaryCondition[]>(INITIAL_CONDITIONS);
  const [editingCondition, setEditingCondition] = useState<BoundaryCondition | null>(null);
  // FACES-START (reversible): caras B-Rep seleccionadas por ARCHIVO,
  // HERRAMIENTA y CONDICION (face_index del core). Cada herramienta tiene su
  // cubeta y cada condicion aplicada (Carga 1, Carga 2...) la suya: al
  // cambiar de herramienta/condicion se ven sus caras, no las de otra.
  // FORMA: { [filename]: { [conditionId]: number[] } } ('seleccionar' usa la
  // pseudo-condicion 'faces_seleccionar', solo resalta).
  // MULTI-COND (reversible): varias condiciones del mismo tipo + condicion
  // destino por herramienta (la que recibe los picks y edita el panel).
  // Para volver atras: cubeta unica por (archivo,herramienta) + faces_<tool>.
  const [faceSelByFile, setFaceSelByFile] = useState<Record<string, Record<string, number[]>>>({});
  const [targetCondByTool, setTargetCondByTool] = useState<
    Partial<Record<FaceCondTool | 'keepout', string>>
  >({});

  const toolBaseName = (tool: FaceCondTool | 'keepout'): string =>
    tool === 'carga' ? 'Carga en caras'
    : tool === 'fijacion' ? 'Fijación en caras'
    : tool === 'preservada' ? 'Región preservada' : 'Zona keep-out';

  // Condicion destino de la herramienta activa: la elegida (panel/arbol) si
  // sigue existiendo, si no la legada faces_<tool> o la primera de su tipo.
  const activeTargetId = useMemo(() => {
    if (!currentModel) return null;
    if (activeTool !== 'carga' && activeTool !== 'fijacion' && activeTool !== 'preservada' && activeTool !== 'keepout') {
      return 'faces_seleccionar';
    }
    const t = targetCondByTool[activeTool];
    if (t && boundaryConditions.some((c) => c.id === t)) return t;
    const legacy =
      boundaryConditions.find((c) => c.id === `faces_${activeTool}`) ??
      boundaryConditions.find((c) => c.type === activeTool);
    return legacy?.id ?? null;
  }, [currentModel, activeTool, boundaryConditions, targetCondByTool]);
  // STABILITY-FIX: identidad estable para no redisparar el overlay de caras.
  const selectedFaces = useMemo(
    () => (currentModel && activeTargetId ? faceSelByFile[currentModel.filename]?.[activeTargetId] ?? [] : []),
    [currentModel, activeTargetId, faceSelByFile],
  );

  const handleToggleFace = (faceIndex: number) => {
    const file = stateRef.current.currentModel?.filename;
    if (!file) return;
    // La condicion destino es duena de su cubeta: picar con otra
    // herramienta/condicion no toca (ni suma a) la seleccion anterior.
    const tool = stateRef.current.activeTool;
    if (tool !== 'carga' && tool !== 'fijacion' && tool !== 'preservada' && tool !== 'keepout' && tool !== 'seleccionar') return;
    const condKey = tool === 'seleccionar' ? 'faces_seleccionar' : (activeTargetId ?? `faces_${tool}`);
    const prevSel = faceSelByFile[file]?.[condKey] ?? [];
    const next = toggleFace(prevSel, faceIndex);
    setFaceSelByFile((p) => ({ ...p, [file]: { ...p[file], [condKey]: next } }));
    // Con 'seleccionar' solo resalta.
    if (tool === 'seleccionar') return;
    if (!activeTargetId) setTargetCondByTool((p) => ({ ...p, [tool]: condKey }));
    const list = stateRef.current.boundaryConditions;
    const prevCond = list.find((c) => c.id === condKey);
    setBoundaryConditions((prev) => {
      const i = prev.findIndex((c) => c.id === condKey);
      const base: BoundaryCondition = prev[i] ?? {
        id: condKey,
        name: toolBaseName(tool),
        type: tool,
        details: '',
        faces: 0,
        active: true,
      };
      const updated: BoundaryCondition = {
        ...base,
        details: facesLabel(next),
        faces: next.length,
        faceIndices: next,
        active: next.length > 0,
      };
      if (i >= 0) {
        const copy = [...prev];
        copy[i] = updated;
        return copy;
      }
      return [...prev, updated];
    });
    // Condicion reutilizable en el backend (mismo id = sobrescribe, no duplica).
    // keepout queda local: en el core la obstruccion referencia CUERPOS, no caras.
    if (backend.hasBridge() && tool !== 'keepout' && next.length > 0) {
      const cur = stateRef.current.currentModel;
      const mag = tool === 'carga'
        ? (prevCond?.magnitude ?? list.find((c) => c.type === 'carga')?.magnitude ?? null)
        : null;
      const condJson = buildConditionJson(
        tool as FaceCondTool,
        prevCond?.name ?? toolBaseName(tool),
        next,
        cur?.filename ?? null,
        surface?.faces ?? undefined,
        mag,
        prevCond?.loadNormal ?? null,
        prevCond?.loadCaseId ?? null,
        prevCond?.loadWeight ?? null,
      );
      (condJson as Record<string, unknown>).id = condKey;
      void backend.createCondition(JSON.stringify(condJson)).catch(() => undefined);
    }
  };
  // FACES-END

  // MULTI-COND-START (reversible): "+ Nueva" del panel — otra condicion del
  // mismo tipo (Carga 2...) con vector/normal heredados si es carga. Pasa a
  // ser la destino de su herramienta. Para volver atras: borrar + boton.
  const createFaceCondition = (tool: FaceCondTool | 'keepout') => {
    const prev = boundaryConditions;
    const same = prev.filter((c) => c.type === tool);
    let n = same.length + 1;
    let id = n <= 1 ? `faces_${tool}` : `faces_${tool}_${n}`;
    while (prev.some((c) => c.id === id)) {
      n += 1;
      id = `faces_${tool}_${n}`;
    }
    const src = prev.find((c) => c.id === targetCondByTool[tool]) ?? same[0];
    const cond: BoundaryCondition = {
      id,
      name: n <= 1 ? toolBaseName(tool) : `${toolBaseName(tool)} ${n}`,
      type: tool,
      details: facesLabel([]),
      faces: 0,
      faceIndices: [],
      active: false,
      ...(tool === 'carga'
        ? { value: src?.value, magnitude: src?.magnitude, loadNormal: src?.loadNormal, loadCaseId: src?.loadCaseId, loadWeight: src?.loadWeight }
        : {}),
    };
    setBoundaryConditions((p) => (p.some((c) => c.id === cond.id) ? p : [...p, cond]));
    setTargetCondByTool((p) => ({ ...p, [tool]: id }));
  };
  // MULTI-COND-END

  // Reenvia una condicion editada en el panel al backend (vector/normal de
  // carga). Las caras ya se sincronizan al picar (handleToggleFace).
  const pushFaceCondition = (cond: BoundaryCondition) => {
    if (!backend.hasBridge()) return;
    if (cond.type !== 'carga' && cond.type !== 'fijacion' && cond.type !== 'preservada') return;
    const cur = stateRef.current.currentModel;
    // LOAD-DIR2 (reversible): vector unitario final (sentido aplicado).
    let dirVec: [number, number, number] | null = null;
    if (cond.type === 'carga' && cond.value) {
      const m = Math.hypot(cond.value[0], cond.value[1], cond.value[2]);
      if (m > 0) dirVec = [cond.value[0] / m, cond.value[1] / m, cond.value[2] / m];
    }
    const condJson = buildConditionJson(
      cond.type as FaceCondTool,
      cond.name,
      cond.faceIndices ?? [],
      cur?.filename ?? null,
      surface?.faces ?? undefined,
      cond.type === 'carga' ? (cond.magnitude ?? null) : null,
      cond.loadNormal ?? null,
      cond.loadCaseId ?? null,
      cond.loadWeight ?? null,
      cond.loadMode ?? null,
      cond.loadPlane ?? null,
      cond.loadAngleDeg ?? null,
      cond.loadSense ?? null,
      dirVec,
    );
    (condJson as Record<string, unknown>).id = cond.id;
    return backend.createCondition(JSON.stringify(condJson)).catch(() => undefined);
  };

  // COND-SYNC (reversible): re-envía al backend todas las condiciones
  // activas con caras (sobrescribe por id) y devuelve sus ids para
  // condition_ids. Sin esto la generativa corría sin condiciones.
  const syncConditionsForRun = async (): Promise<string[]> => {
    if (!backend.hasBridge()) return [];
    const actives = stateRef.current.boundaryConditions.filter(
      (c) => (c.type === 'carga' || c.type === 'fijacion' || c.type === 'preservada') &&
        (c.faceIndices?.length ?? 0) > 0,
    );
    const ids: string[] = [];
    for (const c of actives) {
      const r = (await pushFaceCondition(c)) as unknown as { ok?: boolean; id?: string };
      if (r && r.ok !== false) ids.push(c.id);
    }
    return ids;
  };

  // SIMP Topology Optimization Parameters
  const [simpParams, setSimpParams] = useState<SimpParameters>({
    volfrac: 0.35,
    penalization: 3.0,
    filterRadius: 2.5,
    tolerance: 0.001,
    // PERF-DEFAULT (reversible): 100 iteraciones era un default caro (con
    // malla fina, minutos). 50 alcanza la convergencia típica de SIMP.
    maxIterations: 50,
  });
  // OPT-TYPE (reversible): estructural (SIMP) vs generativa (escenario A).
  const [optType, setOptType] = useState<OptimizationType>('estructural');
  // OPT-NOTICE (reversible): aviso visible de pre-vuelo/errores de
  // optimización (antes fallaba en silencio: sin malla quedaba en
  // "Pausar" sin correr nada). actionLabel/onAction lo hacen accionable
  // (p. ej. "Generar malla ahora"). null = sin aviso.
  const [optNotice, setOptNotice] = useState<{
    text: string; actionLabel?: string; onAction?: () => void;
  } | null>(null);

  // Optimization Runtime State
  // UI-CLEAN (reversible): masa 0 sin modelo real.
  // PROMPT-FIX (reversible): sin resultados iniciales (igual que
  // resetOptimizationState): compliance 0 + historiales vacios para que el
  // panel muestre "sin resultados" en vez de 148.5 ficticio.
  const initialMass = ((currentModel?.volumeCm3 ?? 0) * selectedMaterial.density) / 1000;
  const [optimizationState, setOptimizationState] = useState<OptimizationState>({
    isRunning: false,
    isPaused: false,
    currentIteration: 0,
    totalIterations: 100,
    currentCompliance: 0,
    currentVolume: 1.0,
    convergenceDelta: 0,
    initialMassKg: initialMass,
    currentMassKg: initialMass,
    complianceHistory: [],
    volumeHistory: [1.0],
  });

  // FEA Analysis Results
  // PROMPT-FIX (reversible): null = "sin resultados" (RightPanel muestra
  // "—"). Antes habia cifras ficticias (342.4 MPa, 1.47, 0.421 mm...).
  const [feaResults, setFeaResults] = useState<FeaResults>({
    maxVonMisesMpa: null,
    minSafetyFactor: null,
    maxDisplacementMm: null,
    modalFreqHz: undefined,
    strainEnergyJ: null,
    meshQualityPercent: null,
  });

  // Viewport & Mesh toggles
  const [showMesh, setShowMesh] = useState(false);
  const [showSection, setShowSection] = useState(false);
  const [meshElementSize, setMeshElementSize] = useState(2.5);
  const [isRemeshing, setIsRemeshing] = useState(false);
  const [deformationScale, setDeformationScale] = useState(1);
  const [coords, setCoords] = useState({ x: 124.5, y: 45.2, z: 0.0 });

  // Camera preset triggers
  const [resetViewTrigger, setResetViewTrigger] = useState(0);
  const [selectedViewTrigger, setSelectedViewTrigger] = useState<{
    view: 'iso' | 'top' | 'front' | 'right';
    count: number;
  }>({ view: 'iso', count: 0 });

  // Modals
  const [showImport, setShowImport] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // Undo / Redo history
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Jobs reales del backend (solo con bridge; sin bridge sigue la simulacion)
  const [feaJobId, setFeaJobId] = useState<string | null>(null);
  const [simpJobId, setSimpJobId] = useState<string | null>(null);
  // DENSITY-VIEW (reversible): campo nodal de densidades del último SIMP
  // estructural para colorear la malla (solo visual). null = sin campo.
  // Para volver atrás: borrar estado + usos en simpPoll/CadViewport/RightPanel.
  const [densityField, setDensityField] = useState<DensityField | null>(null);
  const [showDensity, setShowDensity] = useState(true);
  // GEN-SHOW (reversible): jobId generativo pendiente de registro.
  const genJobRef = useRef<string | null>(null);
  // NAV-VIEW-START (reversible): superficies reales por archivo para el
  // viewport UNICO (todos los cuerpos a la vez). La teselacion es
  // determinista por archivo: el cache vale aunque el core cambie de modelo
  // activo al re-importar. `surface` deriva del modelo actual.
  const [surfaceByFile, setSurfaceByFile] = useState<Record<string, RealSurface>>({});
  const surface = currentModel ? surfaceByFile[currentModel.filename] ?? null : null;
  const fetchSurface = async (filename?: string) => {
    if (!backend.hasBridge()) {
      return;
    }
    try {
      const r = (await backend.getMeshPreview()) as {
        ok: boolean;
        mesh?: unknown;
      };
      const mapped = r.ok && r.mesh ? mapMeshPreview(r.mesh) : null;
      const key = filename ?? stateRef.current.currentModel?.filename;
      // MULTI-VIEW (reversible): cache por archivo, todos al viewport.
      if (key && mapped) setSurfaceByFile((prev) => ({ ...prev, [key]: mapped }));
    } catch {
      /* se conserva el cache anterior */
    }
  };
  // NAV-VIEW-END
  // MULTI-VIEW-START (reversible): ver/ocultar por cuerpo del arbol.
  // Clave bodyKey(filename, solid_id); ausente = visible. Para volver atras:
  // borrar estado + props hiddenBodies/onToggleBodyVisibility.
  // TDZ-FIX: solidsByFile/meshByFile/solids van ANTES de viewBodies, que los
  // lee durante el render (flatMap). Declararlos despues lanzaba
  // "Cannot access 'solidsByFile' before initialization" al importar el
  // primer modelo (con models=[] el flatMap no se ejecutaba y no se veia).
  // SOLIDS-START (reversible): cuerpos reales del STEP (uno por objeto).
  const [solids, setSolids] = useState<SolidInfo[]>([]);
  // MULTI-START (reversible): arbol acumulativo — solidos y malla por archivo.
  // El core mantiene UN modelo activo; aqui se cachea lo ya importado para
  // listar todos los modelos sin re-importar. Clave: filename.
  const [solidsByFile, setSolidsByFile] = useState<Record<string, SolidInfo[]>>({});
  const [meshByFile, setMeshByFile] = useState<Record<string, boolean>>({});
  // MULTI-END
  const [hiddenBodies, setHiddenBodies] = useState<Record<string, boolean>>({});
  const handleToggleBodyVisibility = (key: string) => {
    setHiddenBodies((prev) => ({ ...prev, [key]: !prev[key] }));
  };
  // Cuerpos del viewport unico: un ViewBody por solido con superficie en
  // cache (sin superficie no hay geometria que mostrar).
  // STABILITY-FIX (reversible): useMemo para identidad estable. Antes se
  // creaba un array nuevo en CADA render (p. ej. cada mousemove via
  // onUpdateCoords) y el efecto del viewport lo veia como "todo cambio":
  // reconstruia la escena y hacia fitToAll(), devolviendo el zoom y
  // parpadeando el resaltado de caras. Para volver atras: quitar useMemo.
  const viewBodies: ViewBody[] = useMemo(() => models.flatMap((m) => {
    if (!surfaceByFile[m.filename]) return [];
    const solids = solidsByFile[m.filename];
    if (solids && solids.length > 0) {
      return solids.map((s) => ({
        key: bodyKey(m.filename, s.solid_id),
        filename: m.filename,
        solidId: s.solid_id,
        faceIndices: s.face_indices ?? null,
      }));
    }
    return [{
      key: bodyKey(m.filename, 'solid_0'),
      filename: m.filename,
      solidId: 'solid_0',
      faceIndices: null,
    }];
  }), [models, surfaceByFile, solidsByFile]);
  // MULTI-VIEW-END
  // (TDZ-FIX: estados solids/solidsByFile/meshByFile movidos arriba de
  // viewBodies; ver comentario en MULTI-VIEW-START.)
  const fetchSolids = async (filename?: string) => {
    if (!backend.hasBridge()) {
      setSolids([]);
      return;
    }
    try {
      const r = (await backend.getSolids()) as { ok: boolean; solids?: unknown[] };
      const list = r.ok && Array.isArray(r.solids) ? mapSolids(r.solids) : [];
      setSolids(list);
      // MULTI (reversible): cache por archivo para el arbol acumulativo.
      const key = filename ?? stateRef.current.currentModel?.filename;
      if (key) setSolidsByFile((prev) => ({ ...prev, [key]: list }));
      if (list.length > 0) {
        setCurrentModel((prev) =>
          prev ? { ...prev, solids: list.length } : prev
        );
      }
    } catch {
      setSolids([]);
    }
  };
  // SOLIDS-END
  // UI-CLEAN2-START (reversible): malla volumetrica real presente.
  const [hasMesh, setHasMesh] = useState(false);
  // UI-CLEAN2-END
  // MALLA-IMPORT-START (reversible): modelo MESH (STL/OBJ/PLY/3MF, sin
  // B-Rep) -> panel de herramientas de malla. Para volver atras: quitar
  // estado + set en applySnapshotToModel + props RightPanel.
  const [isMeshModel, setIsMeshModel] = useState(false);
  const [meshFormat, setMeshFormat] = useState<string | null>(null);
  // MALLA-IMPORT-END
  const snapRef = useRef<ApiSnapshot | null>(null);
  const stateRef = useRef({ boundaryConditions, selectedMaterial, simpParams, currentModel, activeTool, optType });
  stateRef.current = { boundaryConditions, selectedMaterial, simpParams, currentModel, activeTool, optType };

  const applySnapshotToModel = (snap: ApiSnapshot, filename: string, displayName: string, key?: string) => {
    snapRef.current = snap;
    // DENSITY-VIEW (reversible): el campo es de otra malla/resultado.
    setDensityField(null);
    // UI-CLEAN2 (reversible): fila Malla solo con malla real.
    setHasMesh(!!snap.has_mesh);
    // MALLA-IMPORT (reversible): marca modelo MESH para el panel.
    setIsMeshModel(!!snap.is_mesh);
    setMeshFormat(snap.mesh_format ?? null);
    // MULTI (reversible): malla por archivo para el arbol acumulativo.
    setMeshByFile((prev) => ({ ...prev, [filename]: !!snap.has_mesh }));
    const mapped = mapSnapshotToModel(snap, filename, displayName);
    // MULTI-KEY (reversible): conservar la clave de librería del backend.
    if (key) mapped.key = key;
    setModels((prev) => {
      const i = prev.findIndex((m) => m.filename === filename);
      if (i >= 0) {
        const next = [...prev];
        next[i] = { ...mapped, key: key ?? prev[i].key };
        return next;
      }
      return [mapped, ...prev];
    });
    setCurrentModel(mapped);
  };

  // Carga inicial real: materiales + fixtures STEP del backend + auto-import.
  // Sin bridge no hace nada (queda el fallback local intacto).
  useEffect(() => {
    if (!backend.hasBridge()) return;
    (async () => {
      try {
        const mats = await backend.getMaterials();
        if (mats.ok && Array.isArray(mats.materials) && mats.materials.length > 0) {
          const real = mapMaterials(mats.materials);
          if (real.length > 0) {
            setMaterials(real);
            setSelectedMaterial(real[0]);
            void backend.setMaterial(real[0].name).catch(() => undefined);
          }
        }
      } catch {
        /* fallback local */
      }
      try {
        const fx = await backend.listFixtures();
        if (fx.ok && Array.isArray(fx.fixtures) && fx.fixtures.length > 0) {
          const skeletons: CadModelPreset[] = fx.fixtures.map((f) => ({
            id: `real_${f.filename}`,
            filename: f.filename,
            displayName: prettyName(f.filename),
            faces: 0,
            edges: 0,
            solids: 0,
            volumeCm3: 0,
            elementsTet4: 0,
            nodes: 0,
          }));
          // STARTUP-NOIMPORT (reversible): antes se auto-importaba el primer
          // fixture (cono.step) en cada arranque, pisando el modelo que el
          // usuario tuviera cargado y haciendo que los estudios corrieran
          // sobre geometría que no era la de la app. Ahora solo se listan los
          // fixtures; el usuario elige cuál importar (o sube el suyo). Para
          // volver atras: re-importar fx.fixtures[0] con backend.importStep.
          setModels(skeletons);
        }
      } catch {
        /* fallback local */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pushBoundaries = async () => {
    const { load_dir, magnitude } = mapLoadToBoundaries(stateRef.current.boundaryConditions);
    try {
      await backend.setBoundaries({ bottom_axis: 2, load_dir, magnitude });
    } catch {
      /* el solve reportara el error */
    }
  };

  // FEA real al entrar a la pestana de analisis (usa el control existente).
  const handleTabChange = (tab: ActiveTab) => {
    setActiveTab(tab);
    // MALLA-TOOLS (reversible): al entrar a Malla, herramienta de malla por
    // defecto (si la activa no es de malla).
    if (tab === 'malla' && !activeTool.startsWith('malla-') && activeTool !== 'malla') {
      setActiveTool('malla-diagnosticar');
    }
    if (tab !== 'analizis' || !backend.hasBridge() || feaJobId) return;
    if (!snapRef.current?.has_mesh) return;
    void (async () => {
      await pushBoundaries();
      try {
        const r = await backend.runFea({ backend: 'local' });
        if (r.ok && r.jobId) setFeaJobId(r.jobId);
      } catch {
        /* se conservan los ultimos resultados */
      }
    })();
  };

  const feaPoll = useJobPoll(feaJobId, (result) => {
    const mapped = mapFeaResult(result, stateRef.current.selectedMaterial.yieldStrength);
    if (mapped) setFeaResults(mapped);
    setFeaJobId(null);
    void backend.getSnapshot().then((s) => {
      const snap = (s as unknown as { snapshot?: ApiSnapshot }).snapshot;
      if (s.ok && snap) {
        snapRef.current = snap;
        const cur = stateRef.current.currentModel;
        // UI-CLEAN (reversible): guard sin modelo.
        if (cur) setCurrentModel({ ...cur, elementsTet4: Math.round(snap.num_elements ?? cur.elementsTet4) });
      }
    }).catch(() => undefined);
  });

  const simpPoll = useJobPoll(simpJobId, (result) => {
    // UNSUPPORTED-SURFACE (reversible): condiciones degradadas/no mapeadas
    // que el backend marcó (fallbacks bbox/base-Z). Se muestran en vez de
    // quedar solo en el log. Para volver atrás: borrar helper + usos.
    const unsOf = (res: unknown): string[] => {
      const u = (res as { _unsupported_conditions?: unknown })._unsupported_conditions;
      return Array.isArray(u) ? u.map(String) : [];
    };
    const unsText = (res: unknown): string | null => {
      const list = unsOf(res);
      return list.length ? `Condiciones degradadas: ${list.join(', ')}.` : null;
    };
    setOptimizationState((prev) => {
      const st = stateRef.current;
      // UI-CLEAN (reversible): guard sin modelo.
      const baseMass = ((st.currentModel?.volumeCm3 ?? 0) * st.selectedMaterial.density) / 1000;
      // JOB-NULL (reversible): si el resultado no mapea, avisar en vez de
      // parar en silencio.
      const mapped = mapSimpResult(result, prev, parseFloat(baseMass.toFixed(2)));
      if (!mapped) {
        setOptNotice({ text: 'El cálculo terminó pero sin resultados utilizables (revisa malla y condiciones).' });
      }
      return mapped ?? { ...prev, isRunning: false };
    });
    // DENSITY-VIEW (reversible): tras un SIMP estructural, traer el campo
    // nodal de densidades para colorear la malla (solo visual). El camino
    // generativo registra geometría propia (GEN-SHOW); aquí no se toca.
    const genPending = genJobRef.current;
    if (!genPending && backend.hasBridge()) {
      void (async () => {
        try {
          const r = await backend.getSurfaceMesh({ field: 'density' });
          const vals = (r as unknown as { values?: unknown }).values;
          const pos = (r as unknown as { positions?: unknown }).positions;
          const idx = (r as unknown as { indices?: unknown }).indices;
          // Los arrays viajan como listas planas o {__ndarray__: true, data}
          // (ver decodeCleanArray): Array.isArray solo no alcanza.
          const values = decodeCleanArray(vals);
          const positions = decodeCleanArray(pos);
          const rawIdx = decodeCleanArray(idx);
          if (r.ok && values.length > 0) {
            const indices = rawIdx.map((x) => Math.round(x));
            const dmin = (r as unknown as { min?: unknown }).min;
            const dmax = (r as unknown as { max?: unknown }).max;
            if (values.length > 0 && positions.length >= 9 && indices.length >= 3) {
              setDensityField({
                positions, indices, values,
                min: typeof dmin === 'number' ? dmin : Math.min(...values),
                max: typeof dmax === 'number' ? dmax : Math.max(...values),
              });
              setShowDensity(true);
              const uns = unsText(result);
              if (uns) setOptNotice({ text: `${uns} Se muestra el campo igual, pero revisa compliance/volumen.` });
            }
          } else {
            const parts = ['SIMP calculado, pero sin campo de densidades para visualizar.'];
            const uns = unsText(result);
            if (uns) parts.push(uns);
            setOptNotice({ text: parts.join(' ') });
          }
        } catch {
          setOptNotice({ text: 'SIMP calculado, pero falló la lectura del campo de densidades.' });
        }
      })();
    }
    // GEN-SHOW (reversible): tras un job generativo, registrar la
    // reconstrucción como modelo activo para que la pieza cambie en el
    // viewport (antes el resultado quedaba solo en números).
    const gj = genJobRef.current;
    genJobRef.current = null;
    setSimpJobId(null);
    if (gj) {
      void (async () => {
        try {
          const rr = (await backend.registerReconstruction(gj)) as unknown as {
            ok: boolean; registered?: { model_id?: string; model_name?: string };
            snapshot?: ApiSnapshot; error?: string; reason?: unknown;
          };
          const reg = rr.ok ? rr.registered : undefined;
          if (reg && (reg.model_id || reg.model_name) && rr.snapshot) {
            const nm = reg.model_name || 'Pieza generada';
            applySnapshotToModel(rr.snapshot, nm, nm);
            void fetchSurface(nm);
            void fetchSolids(nm);
            const parts = [`Diseño generativo listo: "${nm}" cargada como modelo activo.`];
            const uns = unsText(result);
            if (uns) parts.push(uns);
            setOptNotice({ text: parts.join(' ') });
          } else {
            const parts = ['Generativa calculada, pero sin geometría registrable.'];
            const reason = typeof rr.reason === 'string' && rr.reason ? rr.reason
              : (typeof (rr as { error?: unknown }).error === 'string' ? String((rr as { error?: unknown }).error) : null);
            if (reason) parts.push(`Motivo: ${reason}.`);
            const uns = unsText(result);
            if (uns) parts.push(uns);
            parts.push('(mira compliance/volumen).');
            setOptNotice({ text: parts.join(' ') });
          }
        } catch {
          setOptNotice({ text: 'Generativa calculada, pero falló el registro de la geometría.' });
        }
      })();
    }
  });

  // JOB-PROGRESS (reversible): iteración en vivo desde el poll (el backend
  // actualiza progress por iteración; antes solo se veía al final).
  useEffect(() => {
    if (simpJobId && simpPoll.progress !== null && simpPoll.progress > 0) {
      const it = Math.max(1, Math.round(simpPoll.progress * (stateRef.current.simpParams.maxIterations || 1)));
      setOptimizationState((prev) => (prev.isRunning ? { ...prev, currentIteration: it } : prev));
    }
  }, [simpPoll.progress, simpJobId]);

  // Si un job real falla, se libera para reintentar (sin tocar la UI).
  useEffect(() => {
    if (feaPoll.error && feaJobId) setFeaJobId(null);
  }, [feaPoll.error, feaJobId]);
  useEffect(() => {
    if (simpPoll.error && simpJobId) {
      setSimpJobId(null);
      setOptimizationState((prev) => ({ ...prev, isRunning: false }));
      setOptNotice({ text: `La optimización terminó con error: ${simpPoll.error}` });
    }
  }, [simpPoll.error, simpJobId]);

  // Recalculate masses when material or model changes
  // Integracion real: material seleccionado -> backend (fire-and-forget).
  // Sin backend, solo estado local (simulacion intacta).
  const handleSelectMaterial = (m: Material) => {
    setSelectedMaterial(m);
    if (backend.hasBridge()) void backend.setMaterial(m.name).catch(() => undefined);
  };
  useEffect(() => {
    // UI-CLEAN (reversible): guard sin modelo.
    const newMass = ((currentModel?.volumeCm3 ?? 0) * selectedMaterial.density) / 1000;
    setOptimizationState((prev) => ({
      ...prev,
      initialMassKg: parseFloat(newMass.toFixed(2)),
      currentMassKg: parseFloat((newMass * (prev.currentIteration > 0 ? prev.currentVolume : 1)).toFixed(2)),
    }));
  }, [selectedMaterial, currentModel]);

  // SIMP Iterative Simulation Timer Loop
  const timerRef = useRef<number | null>(null);

  const startOptimization = () => {
    setOptNotice(null);
    // DENSITY-VIEW (reversible): la corrida nueva invalida el campo anterior.
    setDensityField(null);
    // Sin bridge: simulacion local de siempre.
    if (!backend.hasBridge()) {
      setOptimizationState((prev) => ({
        ...prev,
        isRunning: true,
        isPaused: false,
      }));
      return;
    }
    void (async () => {
      // OPT-REFRESH (reversible): re-leer el snapshot por si la malla se
      // generó fuera de este flujo (evita falsos "sin malla" por caché).
      if (!snapRef.current?.has_mesh) {
        try {
          const s = await backend.getSnapshot();
          const snap = (s as unknown as { snapshot?: ApiSnapshot }).snapshot;
          if (s.ok && snap) {
            snapRef.current = snap;
            setHasMesh(!!snap.has_mesh);
          }
        } catch {
          /* se intenta generar abajo */
        }
      }
      // OPT-AUTO (reversible): sin malla se genera sola (mismo flujo que
      // Remallar) y se sigue sin pedir clics. Solo fallos reales avisan.
      if (!snapRef.current?.has_mesh) {
        setIsRemeshing(true);
        try {
          const r = await backend.generateMesh({ target_element_size: meshElementSize });
          const snap = (r as unknown as { snapshot?: ApiSnapshot }).snapshot;
          if (r.ok && snap) {
            const cur = stateRef.current.currentModel;
            if (cur) applySnapshotToModel(snap, cur.filename, cur.displayName);
            else {
              // Sin modelo en el estado (flujo fixture): igual refrescar.
              snapRef.current = snap;
              setHasMesh(!!snap.has_mesh);
            }
            setHasMesh(!!snap.has_mesh);
            setFeaJobId(null);
          } else {
            setOptNotice({
              text: typeof (r as { error?: unknown }).error === 'string'
                ? `No se pudo generar la malla automáticamente: ${String((r as { error?: unknown }).error)}`
                : 'No se pudo generar la malla automáticamente.',
            });
            return;
          }
        } catch {
          setOptNotice({ text: 'No se pudo generar la malla automáticamente (backend).' });
          return;
        } finally {
          setIsRemeshing(false);
          setShowMesh(true);
        }
        if (!snapRef.current?.has_mesh) {
          setOptNotice({ text: 'La malla no quedó registrada: el modelo puede ser solo superficie (la volumétrica Tet4 requiere sólido STEP).' });
          return;
        }
      }
      if (simpJobId) return;
      const bcs = stateRef.current.boundaryConditions;
      if (!bcs.some((c) => c.type === 'carga' && c.active)) {
      setOptNotice({ text: 'Sin carga activa: abre Carga en la barra, pica caras y Acepta.' });
      return;
    }
    if (!bcs.some((c) => c.type === 'fijacion' && c.active)) {
      setOptNotice({ text: 'Sin fijación activa: abre Fijación en la barra, pica caras y Acepta.' });
      return;
    }
    setOptimizationState((prev) => ({
      ...prev,
      isRunning: true,
      isPaused: false,
      totalIterations: stateRef.current.simpParams.maxIterations,
    }));
      // COND-SYNC (reversible): condiciones reales al backend (la
      // generativa las necesita por id; la estructural las usa si existen
      // y si no cae al legacy de setBoundaries).
      let condIds: string[] = [];
      try {
        condIds = await syncConditionsForRun();
      } catch {
        setOptimizationState((prev) => ({ ...prev, isRunning: false }));
        setOptNotice({ text: 'No se pudieron sincronizar las condiciones con el backend.' });
        return;
      }
      await pushBoundaries();
      const st = stateRef.current;
      try {
        // OPT-TYPE (reversible): generativa = escenario A (pieza existente)
        // con los mismos parámetros SIMP; el job se sondea igual.
        const r = st.optType === 'generativa'
          ? await backend.runGenerativeDesign({
              scenario: 'A',
              condition_ids: condIds,
              volume_fraction: st.simpParams.volfrac,
              max_iterations: st.simpParams.maxIterations,
              penalization: st.simpParams.penalization,
              filter_radius: st.simpParams.filterRadius,
              convergence_tolerance: st.simpParams.tolerance,
            })
          : await backend.runOptimization({
              condition_ids: condIds.length > 0 ? condIds : undefined,
              volume_fraction: st.simpParams.volfrac,
              max_iterations: st.simpParams.maxIterations,
              penalization: st.simpParams.penalization,
              filter_radius: st.simpParams.filterRadius,
              tolerance: st.simpParams.tolerance,
            });
        if (r.ok && r.jobId) {
          setSimpJobId(r.jobId);
          // GEN-SHOW (reversible): marcar jobs generativos para registrar
          // su geometría al terminar.
          genJobRef.current = st.optType === 'generativa' ? r.jobId : null;
        } else {
          setOptimizationState((prev) => ({ ...prev, isRunning: false }));
          setOptNotice({
            text: typeof (r as { error?: unknown }).error === 'string'
              ? String((r as { error?: unknown }).error)
              : 'El backend rechazó la optimización (revisa malla y condiciones).',
          });
        }
      } catch {
        setOptimizationState((prev) => ({ ...prev, isRunning: false }));
        setOptNotice({ text: 'Error de comunicación con el backend.' });
      }
    })();
  };

  const pauseOptimization = () => {
    setOptimizationState((prev) => ({
      ...prev,
      isRunning: false,
      isPaused: true,
    }));
  };

  const resetOptimization = () => {
    setFeaJobId(null);
    setSimpJobId(null);
    if (!backend.hasBridge()) {
      if (timerRef.current) clearInterval(timerRef.current);
      // UI-CLEAN (reversible): guard sin modelo.
      const baseMass = ((currentModel?.volumeCm3 ?? 0) * selectedMaterial.density) / 1000;
      setOptimizationState({
        isRunning: false,
        isPaused: false,
        currentIteration: 0,
        totalIterations: simpParams.maxIterations,
        currentCompliance: 0,
        currentVolume: 1.0,
        convergenceDelta: 0,
        initialMassKg: parseFloat(baseMass.toFixed(2)),
        currentMassKg: parseFloat(baseMass.toFixed(2)),
        complianceHistory: [],
        volumeHistory: [1.0],
      });
      return;
    }
    resetOptimizationState();
  };

  // Run iterations smoothly (SOLO simulacion local: con bridge manda el core).
  // MOCK-FALLBACK (reversible): sin bridge (demo dev) este tick es un
  // fallback tecnico controlado, nunca un resultado. Regla: sin estudio
  // real -> estado vacio ("sin resultados", ya aplicado al inicial); con
  // estudio real -> solo mapSimpResult del core; el mock solo anima tras
  // pulsar Iniciar sin backend, anclado a su propio estado (history[0])
  // para no saltar. Para volver atras: restaurar la formula con 148.5/41.2.
  const MOCK_BASE_COMPLIANCE = 148.5;
  const MOCK_TARGET_RATIO = 41.2 / 148.5;
  useEffect(() => {
    if (optimizationState.isRunning && !backend.hasBridge()) {
      timerRef.current = window.setInterval(() => {
        setOptimizationState((prev) => {
          if (prev.currentIteration >= prev.totalIterations) {
            if (timerRef.current) clearInterval(timerRef.current);
            return { ...prev, isRunning: false, isPaused: false };
          }

          const nextIter = prev.currentIteration + 1;
          const ratio = nextIter / prev.totalIterations;

          // Target volume fraction exponential decay
          const targetVol = simpParams.volfrac;
          const newVol = 1.0 - (1.0 - targetVol) * Math.pow(ratio, 0.8);
          const newMass = prev.initialMassKg * newVol;

          // Compliance decreases and converges (mock anclado a estado
          // propio: base = primer valor de la serie, no constante fija).
          const base = prev.complianceHistory.length > 0
            ? prev.complianceHistory[0]
            : (prev.currentCompliance > 0 ? prev.currentCompliance : MOCK_BASE_COMPLIANCE);
          const target = base * MOCK_TARGET_RATIO;
          const newCompliance = base - (base - target) * Math.pow(ratio, 0.65) + (Math.random() - 0.5) * 0.4;
          const delta = Math.abs(0.015 * (1 - ratio));

          return {
            ...prev,
            currentIteration: nextIter,
            currentVolume: parseFloat(newVol.toFixed(3)),
            currentMassKg: parseFloat(newMass.toFixed(2)),
            currentCompliance: parseFloat(newCompliance.toFixed(2)),
            convergenceDelta: parseFloat(delta.toFixed(4)),
            complianceHistory: [...prev.complianceHistory, newCompliance],
            volumeHistory: [...prev.volumeHistory, newVol],
          };
        });
      }, 90);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [optimizationState.isRunning, simpParams.volfrac, simpParams.maxIterations]);

  // Remesh Domain Action (real con bridge: Gmsh via backend).
  const handleRemesh = () => {
    if (!backend.hasBridge()) {
      setIsRemeshing(true);
      setTimeout(() => {
        setIsRemeshing(false);
        setShowMesh(true);
      }, 700);
      return;
    }
    setIsRemeshing(true);
    void (async () => {
      try {
        const r = await backend.generateMesh({ target_element_size: meshElementSize });
        const snap = (r as unknown as { snapshot?: ApiSnapshot }).snapshot;
        if (r.ok && snap) {
          const cur = stateRef.current.currentModel;
          // UI-CLEAN (reversible): guard sin modelo.
          if (cur) applySnapshotToModel(snap, cur.filename, cur.displayName);
          setFeaJobId(null);
          // DENSITY-VIEW (reversible): la malla cambió, el campo es obsoleto.
          setDensityField(null);
          // UI-CLEAN2 (reversible): remallado real genera la fila Malla.
          if (r.ok) setHasMesh(true);
          // MESH-ERR (reversible): si el snapshot sigue sin malla, avisar
          // (p. ej. modelo de superficie sin sólido para volumétrica).
          if (!snap.has_mesh) {
            setOptNotice({ text: 'La malla no quedó registrada: el modelo puede ser solo superficie (la volumétrica Tet4 requiere sólido STEP).' });
          }
        } else {
          // MESH-ERR (reversible): antes este fallo era silencioso y el
          // usuario solo veía "sin malla" al optimizar.
          setOptNotice({
            text: typeof (r as { error?: unknown }).error === 'string'
              ? `No se pudo generar la malla: ${String((r as { error?: unknown }).error)}`
              : 'No se pudo generar la malla (error del backend).',
          });
        }
      } catch {
        setOptNotice({ text: 'No se pudo generar la malla (error de comunicación con el backend).' });
      } finally {
        setIsRemeshing(false);
        setShowMesh(true);
      }
    })();
  };

  // Seleccion de modelo: con bridge importa el STEP real del backend.
  // MULTI (reversible): cada modelo importado queda en `models` (arbol
  // acumulativo); seleccionar re-importa del disco y restaura su cache.
  const handleSelectModelReal = (m: CadModelPreset) => {
    if (!backend.hasBridge()) {
      setCurrentModel(m);
      return;
    }
    setCurrentModel(m);
    // MULTI: restaura cache inmediata mientras re-importa el STEP.
    const cached = solidsByFile[m.filename];
    if (cached) setSolids(cached);
    setHasMesh(meshByFile[m.filename] ?? false);
    void (async () => {
      try {
        // MULTI-KEY (reversible): si el modelo tiene clave de librería, activar
        // ese mismo modelo con switchModel (ruta real en disco). Antes se
        // re-importaba por `filename`, que falla para archivos subidos (no
        // están en las carpetas de fixtures) y dejaba el modelo equivocado.
        const imp = m.key
          ? await backend.switchModel(m.key)
          : await backend.importStep(m.filename);
        const snap = (imp as unknown as { snapshot?: ApiSnapshot }).snapshot;
        if (imp.ok && snap) {
          applySnapshotToModel(snap, m.filename, m.displayName, m.key);
          setFeaJobId(null);
          setSimpJobId(null);
          resetOptimizationState();
          // NAV-VIEW (reversible): mostrar el STEP real en el viewport.
          void fetchSurface(m.filename);
          // SOLIDS (reversible): detectar cuerpos del STEP.
          void fetchSolids(m.filename);
        }
      } catch {
        /* se conserva el modelo anterior */
      }
    })();
  };

  // MULTI-END (nota: sin boton de baja; el arbol solo lista cuerpos)

  const resetOptimizationState = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    // DENSITY-VIEW (reversible): sin resultado no hay campo que mostrar.
    setDensityField(null);
    const st = stateRef.current;
    // UI-CLEAN (reversible): guard sin modelo.
    const baseMass = ((st.currentModel?.volumeCm3 ?? 0) * st.selectedMaterial.density) / 1000;
    setOptimizationState({
      isRunning: false,
      isPaused: false,
      currentIteration: 0,
      totalIterations: st.simpParams.maxIterations,
      currentCompliance: 0,
      currentVolume: 1.0,
      convergenceDelta: 0,
      initialMassKg: parseFloat(baseMass.toFixed(2)),
      currentMassKg: parseFloat(baseMass.toFixed(2)),
      complianceHistory: [],
      volumeHistory: [1.0],
    });
  };

  // Toggle boundary condition
  const handleToggleCondition = (id: string) => {
    setBoundaryConditions((prev) =>
      prev.map((c) => (c.id === id ? { ...c, active: !c.active } : c))
    );
  };

  // Save edited condition
  const handleSaveCondition = (updated: BoundaryCondition) => {
    setBoundaryConditions((prev) =>
      prev.map((c) => (c.id === updated.id ? updated : c))
    );
  };

  // TOOL-NEW-ALWAYS (reversible): cada clic en la barra abre una herramienta
  // NUEVA del mismo tipo (Carga 1, Carga 2...), nunca modifica la existente.
  // La existente solo se retoma desde su fila del arbol (clic/doble clic).
  // Sin modelo no se crea nada (evita condiciones huerfanas): solo se activa.
  // El Toolbar usa este handler (no setActiveTool directo).
  // Para volver atras: pasar onSelectTool={setActiveTool} en el Toolbar.
  const handleSelectTool = (t: ActiveTool) => {
    if (
      currentModel &&
      (t === 'carga' || t === 'fijacion' || t === 'preservada' || t === 'keepout')
    ) {
      createFaceCondition(t);
    }
    setActiveTool(t);
  };

  // TOOL-LIFECYCLE: Aceptar/Enter/Escape cierra la herramienta abierta,
  // volviendo a 'seleccionar' (cerrada). Ver confirmTool/efecto abajo.
  const confirmTool = () => {
    setActiveTool('seleccionar');
  };

  // Reabrir la herramienta de una condicion aplicada (clic/doble clic en su
  // fila del arbol): activa la herramienta, la marca como destino de picks y
  // muestra sus parametros en el panel. Cierra el modal si estaba abierto.
  const activateToolCondition = (bc: BoundaryCondition) => {
    const t = bc.type;
    if (t === 'carga' || t === 'fijacion' || t === 'preservada' || t === 'keepout') {
      setEditingCondition(null);
      // MULTI-COND: la fila picada pasa a ser la destino de su herramienta.
      setTargetCondByTool((p) => ({ ...p, [t]: bc.id }));
      setActiveTool(t);
    } else {
      setEditingCondition(bc);
    }
  };

  // Enter confirma la herramienta abierta (como Aceptar del panel).
  // Escape desmarca: con herramienta abierta la cierra; sin herramienta
  // abierta limpia las caras resaltadas (faces_seleccionar).
  // No interfiere con modales abiertos ni con botones/areas de texto.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (showImport || showExport || showHelp || editingCondition) return;
      if (e.key !== 'Enter' && e.key !== 'Escape') return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'BUTTON' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.key === 'Enter') {
        if (activeTool === 'seleccionar') return;
        e.preventDefault();
        setActiveTool('seleccionar');
        return;
      }
      e.preventDefault();
      if (activeTool !== 'seleccionar') {
        setActiveTool('seleccionar');
        return;
      }
      const file = stateRef.current.currentModel?.filename;
      if (!file) return;
      setFaceSelByFile((p) => ({ ...p, [file]: { ...p[file], faces_seleccionar: [] } }));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [activeTool, showImport, showExport, showHelp, editingCondition]);
  // TOOL-LIFECYCLE-END

  // MALLA-TOOLS (reversible): tras operar (repair/smooth/decimate/remesh)
  // refresca superficie + solidos + snapshot (volumen/area cambian).
  const refreshMeshView = () => {
    const m = currentModel;
    if (!m || !backend.hasBridge()) return;
    void (async () => {
      try {
        const s = (await backend.getSnapshot()) as { ok: boolean; snapshot?: ApiSnapshot };
        if (s.ok && s.snapshot) applySnapshotToModel(s.snapshot, m.filename, m.displayName);
      } catch {
        /* se conserva la vista anterior */
      }
      void fetchSurface(m.filename);
      void fetchSolids(m.filename);
    })();
  };

  // MALLA-TOOLS-START (reversible): resultado publicado por las
  // herramientas de malla (solo lectura en panel derecho) + accion en
  // curso. Para volver atras: quitar estado + handleMeshTool + props.
  const [meshResult, setMeshResult] = useState<MeshOpResult>({
    report: null, op: null, stats: null, error: null,
  });
  const [meshBusy, setMeshBusy] = useState<string | null>(null);

  const handleMeshTool = (action: MeshToolAction, params: Record<string, number>) => {
    if (!backend.hasBridge() || meshBusy) return;
    setMeshBusy(action);
    setMeshResult((prev) => ({ ...prev, error: null }));
    void (async () => {
      try {
        if (action === 'diagnosticar') {
          const r = (await backend.meshQualityReport(params)) as {
            ok: boolean; report?: Record<string, unknown>; error?: unknown;
          };
          if (!r.ok) setMeshResult((prev) => ({ ...prev, error: String(r.error ?? 'falló') }));
          else setMeshResult({ report: r.report ?? null, op: 'diagnosticar', stats: null, error: null });
          return;
        }
        const calls: Record<Exclude<MeshToolAction, 'diagnosticar'>, () => Promise<unknown>> = {
          reparar: () => backend.repairMesh(params),
          suavizar: () => backend.smoothMesh(params),
          reducir: () => backend.decimateMesh(params),
          remallar: () => backend.remeshMesh(params),
        };
        const r = (await calls[action]()) as {
          ok: boolean; stats?: Record<string, unknown>; error?: unknown;
        };
        if (!r.ok) {
          setMeshResult((prev) => ({ ...prev, op: action, error: String(r.error ?? 'falló') }));
          return;
        }
        const q = (await backend.meshQualityReport({})) as {
          ok: boolean; report?: Record<string, unknown>;
        };
        setMeshResult({
          report: q.ok ? (q.report ?? null) : null,
          op: action, stats: r.stats ?? null, error: null,
        });
        refreshMeshView();
      } catch (e) {
        setMeshResult((prev) => ({ ...prev, op: action, error: String(e) }));
      } finally {
        setMeshBusy(null);
      }
    })();
  };
  // MALLA-TOOLS-END

  // Handle custom file upload
  // UPLOAD-STEP (reversible): con bridge, el archivo real se envia al
  // backend (teselado + solidos + viewport reales). Sin bridge, preset
  // local como antes. Para volver atras: dejar solo el preset local.
  // UPLOAD-CHUNKED (reversible, MALLA-C): >8 MB por partes de 4 MB
  // (beginUpload/uploadChunk) para no cargar cientos de MB en un base64.
  const CHUNKED_THRESHOLD = 8 * 1024 * 1024;
  const UPLOAD_SLICE = 4 * 1024 * 1024;
  const blobToBase64 = (blob: Blob): Promise<string> =>
    new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => {
        const s = String(r.result ?? '');
        resolve(s.includes(',') ? s.split(',')[1] : s);
      };
      r.onerror = () => reject(r.error);
      r.readAsDataURL(blob);
    });
  const applyImportResult = (
    imp: { ok: boolean; snapshot?: ApiSnapshot; key?: string },
    filename: string,
  ) => {
    const snap = imp.snapshot;
    if (imp.ok && snap) {
      // MULTI-KEY (reversible): guardar la clave de librería del backend.
      applySnapshotToModel(snap, filename, prettyName(filename), imp.key);
      setFeaJobId(null);
      setSimpJobId(null);
      resetOptimizationState();
      void fetchSurface(filename);
      void fetchSolids(filename);
    }
  };
  const uploadFileChunked = async (file: File) => {
    const beg = (await backend.beginUpload(file.name)) as {
      ok: boolean; upload_id?: string; error?: unknown;
    };
    if (!beg.ok || !beg.upload_id) throw new Error(String(beg.error ?? 'beginUpload falló'));
    const total = file.size;
    let offset = 0;
    let last: { ok: boolean; snapshot?: ApiSnapshot; key?: string } = { ok: false };
    while (offset < total) {
      const end = Math.min(offset + UPLOAD_SLICE, total);
      const base64 = await blobToBase64(file.slice(offset, end));
      const r = (await backend.uploadChunk({
        upload_id: beg.upload_id,
        base64,
        last: end >= total,
      })) as { ok: boolean; snapshot?: ApiSnapshot; key?: string; received?: number; error?: unknown };
      if (!r.ok) throw new Error(String(r.error ?? 'uploadChunk falló'));
      if (end >= total) last = r;
      offset = end;
    }
    return last;
  };
  const handleCustomFileUpload = (file: File) => {
    if (backend.hasBridge()) {
      void (async () => {
        try {
          if (file.size > CHUNKED_THRESHOLD) {
            applyImportResult(await uploadFileChunked(file), file.name);
            return;
          }
          const base64 = await blobToBase64(file);
          const imp = (await backend.importStepBytes({
            filename: file.name,
            base64,
          })) as { ok: boolean; snapshot?: ApiSnapshot; key?: string; error?: unknown };
          applyImportResult(imp, file.name);
        } catch {
          /* se conserva el modelo anterior */
        }
      })();
      return;
    }
    const newPreset: CadModelPreset = {
      id: `custom_${Date.now()}`,
      filename: file.name,
      displayName: file.name.replace(/\.[^/.]+$/, '').toUpperCase(),
      faces: 28,
      edges: 42,
      solids: 1,
      volumeCm3: 480.0,
      elementsTet4: 195400,
      nodes: 41200,
    };
    setModels((prev) => [newPreset, ...prev]);
    setCurrentModel(newPreset);
    // NAV-VIEW (reversible): sin teselado real para subidas locales: caja
    // provisional para que el viewport muestre algo en vez de quedar negro.
    setSurfaceByFile((prev) => ({ ...prev, [newPreset.filename]: placeholderSurface() }));
    // SOLIDS (reversible): un cuerpo provisional para el arbol acumulativo.
    setSolids([{ solid_id: 'solid_0', index: 0, name: 'solid_0', faces_count: 6, face_indices: [0, 1, 2, 3, 4, 5] }]);
    // MULTI (reversible): el modelo local tambien entra al arbol acumulativo.
    setSolidsByFile((prev) => ({ ...prev, [newPreset.filename]: [{ solid_id: 'solid_0', index: 0, name: 'solid_0', faces_count: 6, face_indices: [0, 1, 2, 3, 4, 5] }] }));
    setMeshByFile((prev) => ({ ...prev, [newPreset.filename]: false }));
    // UI-CLEAN2 (reversible): sin malla real para subidas locales.
    setHasMesh(false);
  };

  // Undo / Redo helpers
  const handleUndo = () => {
    if (optimizationState.currentIteration > 0) {
      setOptimizationState((prev) => ({
        ...prev,
        currentIteration: Math.max(0, prev.currentIteration - 5),
      }));
    }
  };

  const handleRedo = () => {
    if (optimizationState.currentIteration < optimizationState.totalIterations) {
      setOptimizationState((prev) => ({
        ...prev,
        currentIteration: Math.min(prev.totalIterations, prev.currentIteration + 5),
      }));
    }
  };

  return (
    <div className="min-h-screen bg-viewport-bg text-on-surface font-sans select-none flex flex-col">
      {/* 1. TOP FIXED HEADER */}
      <Header
        onOpenImport={() => setShowImport(true)}
        onOpenExport={() => setShowExport(true)}
        onOpenHelp={() => setShowHelp(true)}
        onResetView={() => setResetViewTrigger((c) => c + 1)}
        onToggleMesh={() => setShowMesh((m) => !m)}
        showMesh={showMesh}
        onSelectView={(view) =>
          setSelectedViewTrigger((prev) => ({ view, count: prev.count + 1 }))
        }
      />

      {/* 2. SECONDARY MODE NAV TABS */}
      <div className="fixed top-[76px] left-0 right-0 z-40">
        <SecondaryNav activeTab={activeTab} onChangeTab={handleTabChange} />
        {/* 3. CAD TOOLBAR */}
        <Toolbar
          activeTab={activeTab}
          activeTool={activeTool}
          onSelectTool={handleSelectTool}
          showMesh={showMesh}
          onToggleMesh={() => setShowMesh((m) => !m)}
          showSection={showSection}
          onToggleSection={() => setShowSection((s) => !s)}
          onUndo={handleUndo}
          onRedo={handleRedo}
        />
      </div>

      {/* 4. MAIN ENGINEERING STAGE */}
      <div className="pt-[146px] pb-7 flex-1 w-full flex flex-col bg-viewport-bg">
        {/* OPT-NOTICE (reversible): aviso de pre-vuelo/errores. */}
        {optNotice && (
          <div className="mx-space-sm mt-space-sm flex items-center gap-2 rounded-lg border border-fea-stress-yield/50 bg-fea-stress-yield/10 px-3 py-2 text-[11px] text-text-primary" role="alert">
            <span className="material-symbols-outlined text-[16px] text-fea-stress-yield shrink-0">warning</span>
            <span className="flex-1 min-w-0">{optNotice.text}</span>
            {optNotice.actionLabel && optNotice.onAction && (
              <button type="button" onClick={optNotice.onAction}
                className="shrink-0 rounded bg-secondary/15 border border-secondary/40 px-2 py-1 font-semibold text-secondary hover:bg-secondary hover:text-on-primary transition-colors">
                {optNotice.actionLabel}
              </button>
            )}
            <button type="button" onClick={() => setOptNotice(null)} aria-label="Cerrar aviso"
              className="shrink-0 rounded hover:bg-surface-elevated px-1 text-text-secondary hover:text-text-primary">
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        )}
        <div className="w-full flex-1 flex flex-col xl:flex-row gap-space-sm p-space-sm bg-viewport-bg min-h-[calc(100dvh-8.5rem)]">
          {/* EXT-RAIL (reversible): riel delgado entre el marco y el arbol.
              Borrar esta linea para volver atras. */}
          <ExtensionsRail />
          {/* LEFT PANEL: CAD Tree & Gmsh Mesher */}
          <LeftPanel
            currentModel={currentModel}
            models={models}
            onSelectModel={handleSelectModelReal}
            // MULTI (reversible): arbol acumulativo por archivo.
            solidsByFile={solidsByFile}
            meshByFile={meshByFile}
            // MULTI-VIEW (reversible): ojo ver/ocultar por cuerpo.
            hiddenBodies={hiddenBodies}
            onToggleBodyVisibility={handleToggleBodyVisibility}
            boundaryConditions={boundaryConditions}
            onToggleCondition={handleToggleCondition}
            onEditCondition={setEditingCondition}
            isModelVisible={isModelVisible}
            onToggleModelVisibility={() => setIsModelVisible(!isModelVisible)}
            onOpenImport={() => setShowImport(true)}
            meshElementSize={meshElementSize}
            onChangeMeshSize={setMeshElementSize}
            onRemesh={handleRemesh}
            isRemeshing={isRemeshing}
            // TOOLPARAMS + TOOL-LIFECYCLE + MULTI-COND (reversible)
            activeTool={activeTool}
            onConfirmTool={confirmTool}
            onSaveCondition={handleSaveCondition}
            onActivateTool={activateToolCondition}
            targetCondId={activeTargetId}
            onNewCondition={() => {
              const t = activeTool;
              if (t === 'carga' || t === 'fijacion' || t === 'preservada' || t === 'keepout') {
                createFaceCondition(t);
              }
            }}
            onPushCondition={pushFaceCondition}
            onMeshTool={handleMeshTool}
            meshBusy={meshBusy}
          />

          {/* CENTRAL 3D CAD VIEWPORT */}
          {/* BLACKSCREEN-FIX: el viewport nunca deja la app en negro. */}
          <ErrorBoundary label="el viewport 3D">
          <React.Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center rounded-lg bg-surface-container-lowest min-h-[52dvh] xl:min-h-[580px] text-[11px] font-mono text-text-muted">
                Cargando viewport 3D…
              </div>
            }
          >
          <CadViewport
            activeTab={activeTab}
            activeTool={activeTool}
            selectedMaterial={selectedMaterial}
            optimizationState={optimizationState}
            boundaryConditions={boundaryConditions}
            showMesh={showMesh}
            showSection={showSection}
            isModelVisible={isModelVisible}
            deformationScale={deformationScale}
            onUpdateCoords={setCoords}
            resetViewTrigger={resetViewTrigger}
            selectedViewTrigger={selectedViewTrigger}
            // NAV-VIEW (reversible): superficies de todos los archivos.
            surfaces={surfaceByFile}
            bodies={viewBodies}
            activeFilename={currentModel?.filename ?? null}
            // MULTI-VIEW (reversible): ver/ocultar por cuerpo + malla.
            hiddenBodies={hiddenBodies}
            meshByFile={meshByFile}
            // FACES (reversible): picking + resaltado de caras B-Rep.
            selectedFaces={selectedFaces}
            onToggleFace={handleToggleFace}
            // DENSITY-VIEW (reversible): overlay de densidades SIMP.
            densityField={densityField}
            showDensity={showDensity}
            facePickEnabled={
              activeTool === 'seleccionar' ||
              activeTool === 'carga' ||
              activeTool === 'fijacion' ||
              activeTool === 'preservada' ||
              activeTool === 'keepout'
            }
          />
          </React.Suspense>
          </ErrorBoundary>

          {/* RIGHT PANEL: Materials, SIMP Parameters, and FEA Results */}
          <RightPanel
            activeTab={activeTab}
            materials={materials}
            selectedMaterial={selectedMaterial}
            onSelectMaterial={handleSelectMaterial}
            simpParams={simpParams}
            onChangeSimpParams={setSimpParams}
            optType={optType}
            onChangeOptType={setOptType}
            optimizationState={optimizationState}
            onStartOptimization={startOptimization}
            onPauseOptimization={pauseOptimization}
            onResetOptimization={resetOptimization}
            feaResults={feaResults}
            deformationScale={deformationScale}
            onChangeDeformationScale={setDeformationScale}
            onExportReport={() => setShowExport(true)}
            isMeshModel={isMeshModel}
            meshFormat={meshFormat}
            meshResult={meshResult}
            // DENSITY-VIEW (reversible): toggle + leyenda del overlay.
            densityAvailable={densityField !== null}
            densityMin={densityField?.min ?? null}
            densityMax={densityField?.max ?? null}
            showDensity={showDensity}
            onToggleDensity={() => setShowDensity((v) => !v)}
          />
        </div>
      </div>

      {/* 5. BOTTOM FIXED STATUS BAR */}
      {/* V2-NEW-START (reversible: borrar hasta V2-NEW-END para volver a la interfaz anterior) */}
      {V2_ENABLED && <V2Panel />}
      {/* V2-NEW-END */}
      <Footer
        coords={coords}
        // UI-CLEAN (reversible): 0 sin modelo real.
        elementsCount={
          currentModel
            ? backend.hasBridge()
              ? currentModel.elementsTet4
              : Math.round(currentModel.elementsTet4 * (1.8 / meshElementSize))
            : 0
        }
        nodesCount={
          currentModel
            ? backend.hasBridge()
              ? currentModel.nodes
              : Math.round(currentModel.nodes * (1.8 / meshElementSize))
            : 0
        }
      />

      {/* 6. MODALS (IMPORT, EXPORT, HELP, EDIT) */}
      <Modals
        showImport={showImport}
        onCloseImport={() => setShowImport(false)}
        models={models}
        currentModel={currentModel}
        onSelectModel={handleSelectModelReal}
        onCustomFileUpload={handleCustomFileUpload}
        showExport={showExport}
        onCloseExport={() => setShowExport(false)}
        selectedMaterial={selectedMaterial}
        optimizationState={optimizationState}
        showHelp={showHelp}
        onCloseHelp={() => setShowHelp(false)}
        editingCondition={editingCondition}
        onCloseEditCondition={() => setEditingCondition(null)}
        onSaveCondition={handleSaveCondition}
      />
    </div>
  );
}
