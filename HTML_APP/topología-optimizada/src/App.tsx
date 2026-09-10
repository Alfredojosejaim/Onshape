/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  ActiveTab,
  ActiveTool,
  BoundaryCondition,
  CadModelPreset,
  FeaResults,
  Material,
  OptimizationState,
  SimpParameters,
} from './types';import { MATERIALS } from './data/materials';
import { CAD_PRESETS, INITIAL_CONDITIONS } from './data/models';
import { Header } from './components/Header';
import { SecondaryNav } from './components/SecondaryNav';
import { Toolbar } from './components/Toolbar';
import { LeftPanel } from './components/LeftPanel';
import { RightPanel } from './components/RightPanel';
import { CadViewport } from './components/CadViewport';
import { Footer } from './components/Footer';
import { Modals } from './components/Modals';
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
// SOLIDS-START (reversible): cuerpos del STEP, uno por objeto.
import { mapSolids } from './lib/realdata';
import type { SolidInfo } from './types';
// SOLIDS-END
// NAV-VIEW-START (reversible: quitar import + estado surface + fetchSurface + prop)
import { mapMeshPreview, type RealSurface } from './lib/realdata';
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
  // NAV-VIEW-START (reversible): superficie real del STEP para el viewport.
  const [surface, setSurface] = useState<RealSurface | null>(null);
  const fetchSurface = async () => {
    if (!backend.hasBridge()) {
      setSurface(null);
      return;
    }
    try {
      const r = (await backend.getMeshPreview()) as {
        ok: boolean;
        mesh?: unknown;
      };
      setSurface(r.ok && r.mesh ? mapMeshPreview(r.mesh) : null);
    } catch {
      setSurface(null);
    }
  };
  // NAV-VIEW-END
  // SOLIDS-START (reversible): cuerpos reales del STEP (uno por objeto).
  const [solids, setSolids] = useState<SolidInfo[]>([]);
  const fetchSolids = async () => {
    if (!backend.hasBridge()) {
      setSolids([]);
      return;
    }
    try {
      const r = (await backend.getSolids()) as { ok: boolean; solids?: unknown[] };
      const list = r.ok && Array.isArray(r.solids) ? mapSolids(r.solids) : [];
      setSolids(list);
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
  const snapRef = useRef<ApiSnapshot | null>(null);
  const stateRef = useRef({ boundaryConditions, selectedMaterial, simpParams, currentModel });
  stateRef.current = { boundaryConditions, selectedMaterial, simpParams, currentModel };

  const applySnapshotToModel = (snap: ApiSnapshot, filename: string, displayName: string) => {
    snapRef.current = snap;
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
            void fetchSurface();
            // SOLIDS (reversible): detectar cuerpos del STEP.
            void fetchSolids();
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
  const handleSelectModelReal = (m: CadModelPreset) => {
    if (!backend.hasBridge()) {
      setCurrentModel(m);
      return;
    }
    setCurrentModel(m);
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
          void fetchSurface();
          // SOLIDS (reversible): detectar cuerpos del STEP.
          void fetchSolids();
        }
      } catch {
        /* se conserva el modelo anterior */
      }
    })();
  };

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

  // Handle custom file upload
  const handleCustomFileUpload = (file: File) => {
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
    // NAV-VIEW (reversible): sin teselado real para subidas locales.
    setSurface(null);
    // SOLIDS (reversible): sin cuerpos reales para subidas locales.
    setSolids([]);
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
            // SOLIDS (reversible): cuerpos del STEP, uno por objeto.
            solids={solids}
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
          />

          {/* CENTRAL 3D CAD VIEWPORT */}
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
            // NAV-VIEW (reversible): superficie real del STEP.
            surface={surface}
          />

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
