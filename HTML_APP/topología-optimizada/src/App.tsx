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
  FeaResults,
  Material,
  OptimizationState,
  SimpParameters,
  ViewBody,
} from './types';import { MATERIALS } from './data/materials';
import { CAD_PRESETS, INITIAL_CONDITIONS } from './data/models';
import { Header } from './components/Header';
import { SecondaryNav } from './components/SecondaryNav';
import { Toolbar } from './components/Toolbar';
import { LeftPanel } from './components/LeftPanel';
import { RightPanel } from './components/RightPanel';
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
        ? { value: src?.value, magnitude: src?.magnitude, loadNormal: src?.loadNormal }
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
    const condJson = buildConditionJson(
      cond.type as FaceCondTool,
      cond.name,
      cond.faceIndices ?? [],
      cur?.filename ?? null,
      surface?.faces ?? undefined,
      cond.type === 'carga' ? (cond.magnitude ?? null) : null,
      cond.loadNormal ?? null,
    );
    (condJson as Record<string, unknown>).id = cond.id;
    void backend.createCondition(JSON.stringify(condJson)).catch(() => undefined);
  };

  // SIMP Topology Optimization Parameters
  const [simpParams, setSimpParams] = useState<SimpParameters>({
    volfrac: 0.35,
    penalization: 3.0,
    filterRadius: 2.5,
    tolerance: 0.001,
    maxIterations: 100,
  });

  // Optimization Runtime State
  // UI-CLEAN (reversible): masa 0 sin modelo real.
  const initialMass = ((currentModel?.volumeCm3 ?? 0) * selectedMaterial.density) / 1000;
  const [optimizationState, setOptimizationState] = useState<OptimizationState>({
    isRunning: false,
    isPaused: false,
    currentIteration: 0,
    totalIterations: 100,
    currentCompliance: 148.5,
    currentVolume: 1.0,
    convergenceDelta: 0.015,
    initialMassKg: initialMass,
    currentMassKg: initialMass,
    complianceHistory: [148.5],
    volumeHistory: [1.0],
  });

  // FEA Analysis Results
  const [feaResults, setFeaResults] = useState<FeaResults>({
    maxVonMisesMpa: 342.4,
    minSafetyFactor: 1.47,
    maxDisplacementMm: 0.421,
    modalFreqHz: 428,
    strainEnergyJ: 1.84,
    meshQualityPercent: 98.4,
  });

  // Viewport & Mesh toggles
  const [showMesh, setShowMesh] = useState(false);
  const [showSection, setShowSection] = useState(false);
  const [meshElementSize, setMeshElementSize] = useState(1.8);
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
  const snapRef = useRef<ApiSnapshot | null>(null);
  const stateRef = useRef({ boundaryConditions, selectedMaterial, simpParams, currentModel, activeTool });
  stateRef.current = { boundaryConditions, selectedMaterial, simpParams, currentModel, activeTool };

  const applySnapshotToModel = (snap: ApiSnapshot, filename: string, displayName: string) => {
    snapRef.current = snap;
    // UI-CLEAN2 (reversible): fila Malla solo con malla real.
    setHasMesh(!!snap.has_mesh);
    // MULTI (reversible): malla por archivo para el arbol acumulativo.
    setMeshByFile((prev) => ({ ...prev, [filename]: !!snap.has_mesh }));
    const mapped = mapSnapshotToModel(snap, filename, displayName);
    setModels((prev) => {
      const i = prev.findIndex((m) => m.filename === filename);
      if (i >= 0) {
        const next = [...prev];
        next[i] = mapped;
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
          setModels(skeletons);
          const first = fx.fixtures[0];
          const imp = await backend.importStep(first.filename);
          const snap = (imp as unknown as { snapshot?: ApiSnapshot }).snapshot;
          if (imp.ok && snap) {
            applySnapshotToModel(snap, first.filename, prettyName(first.filename));
            // NAV-VIEW (reversible): mostrar el STEP real en el viewport.
            void fetchSurface(first.filename);
            // SOLIDS (reversible): detectar cuerpos del STEP.
            void fetchSolids(first.filename);
          }
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
    setOptimizationState((prev) => {
      const st = stateRef.current;
      // UI-CLEAN (reversible): guard sin modelo.
      const baseMass = ((st.currentModel?.volumeCm3 ?? 0) * st.selectedMaterial.density) / 1000;
      return mapSimpResult(result, prev, parseFloat(baseMass.toFixed(2))) ?? { ...prev, isRunning: false };
    });
    setSimpJobId(null);
  });

  // Si un job real falla, se libera para reintentar (sin tocar la UI).
  useEffect(() => {
    if (feaPoll.error && feaJobId) setFeaJobId(null);
  }, [feaPoll.error, feaJobId]);
  useEffect(() => {
    if (simpPoll.error && simpJobId) {
      setSimpJobId(null);
      setOptimizationState((prev) => ({ ...prev, isRunning: false }));
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
    // Sin bridge: simulacion local de siempre.
    if (!backend.hasBridge()) {
      setOptimizationState((prev) => ({
        ...prev,
        isRunning: true,
        isPaused: false,
      }));
      return;
    }
    // Con bridge: SIMP real del core en background (requiere malla).
    if (!snapRef.current?.has_mesh || simpJobId) return;
    setOptimizationState((prev) => ({
      ...prev,
      isRunning: true,
      isPaused: false,
      totalIterations: stateRef.current.simpParams.maxIterations,
    }));
    void (async () => {
      await pushBoundaries();
      const st = stateRef.current;
      try {
        const r = await backend.runOptimization({
          volume_fraction: st.simpParams.volfrac,
          max_iterations: st.simpParams.maxIterations,
          penalization: st.simpParams.penalization,
          filter_radius: st.simpParams.filterRadius,
          tolerance: st.simpParams.tolerance,
        });
        if (r.ok && r.jobId) {
          setSimpJobId(r.jobId);
        } else {
          setOptimizationState((prev) => ({ ...prev, isRunning: false }));
        }
      } catch {
        setOptimizationState((prev) => ({ ...prev, isRunning: false }));
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
        currentCompliance: 148.5,
        currentVolume: 1.0,
        convergenceDelta: 0.015,
        initialMassKg: parseFloat(baseMass.toFixed(2)),
        currentMassKg: parseFloat(baseMass.toFixed(2)),
        complianceHistory: [148.5],
        volumeHistory: [1.0],
      });
      return;
    }
    resetOptimizationState();
  };

  // Run iterations smoothly (SOLO simulacion local: con bridge manda el core).
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

          // Compliance decreases and converges
          const newCompliance = 148.5 - (148.5 - 41.2) * Math.pow(ratio, 0.65) + (Math.random() - 0.5) * 0.4;
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
          // UI-CLEAN2 (reversible): remallado real genera la fila Malla.
          if (r.ok) setHasMesh(true);
        }
      } catch {
        /* se conservan los datos anteriores */
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
        const imp = await backend.importStep(m.filename);
        const snap = (imp as unknown as { snapshot?: ApiSnapshot }).snapshot;
        if (imp.ok && snap) {
          applySnapshotToModel(snap, m.filename, m.displayName);
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
  // Para volver atras: devolver onSelectTool={setActiveTool} en el Toolbar.
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
  const handleSelectTool = (t: ActiveTool) => {
    if (
      currentModel &&
      (t === 'carga' || t === 'fijacion' || t === 'preservada' || t === 'keepout')
    ) {
      createFaceCondition(t);
    }
    setActiveTool(t);
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

  // Enter/Escape confirman la herramienta abierta (como Aceptar del panel).
  // No interfiere con modales abiertos ni con botones/areas de texto.
  useEffect(() => {
    if (activeTool === 'seleccionar') return;
    const onKey = (e: KeyboardEvent) => {
      if (showImport || showExport || showHelp || editingCondition) return;
      if (e.key !== 'Enter' && e.key !== 'Escape') return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'BUTTON' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      e.preventDefault();
      setActiveTool('seleccionar');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [activeTool, showImport, showExport, showHelp, editingCondition]);
  // TOOL-LIFECYCLE-END

  // Handle custom file upload
  // UPLOAD-STEP (reversible): con bridge, el archivo real se envia al
  // backend (teselado + solidos + viewport reales). Sin bridge, preset
  // local como antes. Para volver atras: dejar solo el preset local.
  const handleCustomFileUpload = (file: File) => {
    if (backend.hasBridge()) {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = String(reader.result ?? '');
        const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl;
        void (async () => {
          try {
            const imp = (await backend.importStepBytes({
              filename: file.name,
              base64,
            })) as { ok: boolean; snapshot?: ApiSnapshot; error?: unknown };
            const snap = imp.snapshot;
            if (imp.ok && snap) {
              applySnapshotToModel(snap, file.name, prettyName(file.name));
              setFeaJobId(null);
              setSimpJobId(null);
              resetOptimizationState();
              void fetchSurface(file.name);
              void fetchSolids(file.name);
            }
          } catch {
            /* se conserva el modelo anterior */
          }
        })();
      };
      reader.readAsDataURL(file);
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
          activeTool={activeTool}
          onSelectTool={setActiveTool}
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
        <div className="w-full flex-1 flex flex-col xl:flex-row gap-space-sm p-space-sm bg-viewport-bg min-h-[calc(100vh-8.5rem)]">
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
          />

          {/* CENTRAL 3D CAD VIEWPORT */}
          {/* BLACKSCREEN-FIX: el viewport nunca deja la app en negro. */}
          <ErrorBoundary label="el viewport 3D">
          <React.Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center rounded-lg bg-surface-container-lowest min-h-[580px] text-[11px] font-mono text-text-muted">
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
            optimizationState={optimizationState}
            onStartOptimization={startOptimization}
            onPauseOptimization={pauseOptimization}
            onResetOptimization={resetOptimization}
            feaResults={feaResults}
            deformationScale={deformationScale}
            onChangeDeformationScale={setDeformationScale}
            onExportReport={() => setShowExport(true)}
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
