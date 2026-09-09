import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Material,
  SimpConfig,
  DomainDimensions,
  DesignDomainPreset,
  ScalarField,
  SurfaceMeshData,
  OptimizationMetrics,
  IterationData,
  ActiveTool,
  OptimizationMode,
  ProtectedFace,
  ObstacleZone
} from './types';
import { STANDARD_MATERIALS } from './lib/materials';
import { SimpOptimizationEngine } from './lib/simpEngine';
import { generateStepFile, generateStlFile, triggerDownload } from './lib/cadExporter';

import { Header } from './components/Header';
import { BackendBar } from './components/BackendBar';
import { Viewport3D } from './components/Viewport3D';
import { CargaPanel } from './components/tools/CargaPanel';
import { MaterialesPanel } from './components/tools/MaterialesPanel';
import { ElasticidadPanel } from './components/tools/ElasticidadPanel';
import { ObstruccionesPanel } from './components/tools/ObstruccionesPanel';
import { ProtegidaPanel } from './components/tools/ProtegidaPanel';
import { OptimizarPanel } from './components/tools/OptimizarPanel';
import { AnalisisPanel } from './components/tools/AnalisisPanel';

import {
  Sparkles,
  Layers,
  ChevronRight,
  Maximize2,
  Minimize2,
  Box,
  Compass
} from 'lucide-react';

export default function App() {
  // Navigation & Active Tool State
  const [activeTool, setActiveTool] = useState<ActiveTool>('optimizar');
  const [mode, setMode] = useState<OptimizationMode>('generativa');

  // Physical & Domain Properties
  const [materialsList, setMaterialsList] = useState<Material[]>(STANDARD_MATERIALS);
  const [material, setMaterial] = useState<Material>(STANDARD_MATERIALS[0]);
  const [preset, setPreset] = useState<DesignDomainPreset>('cantilever');
  const [dimensions, setDimensions] = useState<DomainDimensions>({
    length: 120,
    height: 60,
    width: 36,
    resolutionX: 32,
    resolutionY: 16,
    resolutionZ: 10
  });

  // Algorithm Configuration
  const [config, setConfig] = useState<SimpConfig>({
    volumeFraction: 0.35,
    penaltyExponent: 3.0,
    filterRadius: 2.2,
    maxIterations: 35,
    convergenceTolerance: 0.002
  });

  // Load Parameters
  const [loadMagnitude, setLoadMagnitude] = useState<number>(10000); // 10 kN
  const [loadDirection, setLoadDirection] = useState<[number, number, number]>([0, -1, 0]);
  const [loadPosition, setLoadPosition] = useState<string>('right_bottom');

  // Protected Faces (Caras protegidas que no se modifican en la optimización)
  const [protectedFaces, setProtectedFaces] = useState<ProtectedFace[]>([
    {
      id: 'anchor_wall',
      name: 'Cara de Fijación Posterior (Empotramiento)',
      description: 'Superficie de contacto con la bancada portante (X = 0)',
      type: 'support_anchor',
      enabled: true,
      color: '#10b981',
      bounds: [0.0, 0.0, 0.0, 0.08, 1.0, 1.0]
    },
    {
      id: 'load_pad',
      name: 'Almohadilla de Contacto de Carga',
      description: 'Zona de aplicación y distribución de fuerza mecánica (X = L)',
      type: 'load_bearing',
      enabled: true,
      color: '#38bdf8',
      bounds: [0.88, 0.0, 0.3, 1.0, 0.15, 0.7]
    }
  ]);

  // Obstacle Zones (Zonas de exclusión - Keep-out)
  const [obstacleZones, setObstacleZones] = useState<ObstacleZone[]>([
    {
      id: 'central_bore',
      name: 'Taladro Pasante de Despeje Mecánico',
      description: 'Zona cilíndrica reservada para paso de eje o perno',
      shape: 'cylinder',
      enabled: true,
      color: '#f59e0b',
      bounds: [0.38, 0.35, 0.0, 0.62, 0.65, 1.0]
    }
  ]);

  // Viewport display parameters
  const [field, setField] = useState<ScalarField>('density');
  const [densityThreshold, setDensityThreshold] = useState<number>(0.38);
  const [clipPlaneRatio, setClipPlaneRatio] = useState<number>(1.0);
  const [showWireframe, setShowWireframe] = useState<boolean>(false);
  const [showBounds, setShowBounds] = useState<boolean>(true);
  const [showGlyphs, setShowGlyphs] = useState<boolean>(true);

  // Engine & Optimization execution
  const engineRef = useRef<SimpOptimizationEngine | null>(null);
  const [meshData, setMeshData] = useState<SurfaceMeshData | null>(null);
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false);
  const [currentIteration, setCurrentIteration] = useState<number>(0);
  const [history, setHistory] = useState<IterationData[]>([]);
  const [metrics, setMetrics] = useState<OptimizationMetrics | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const animationTimerRef = useRef<number | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Show temporary toast notification
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  // Initialize engine
  useEffect(() => {
    const engine = new SimpOptimizationEngine(preset, dimensions, config, material);
    engine.setMode(mode);
    engine.setProtectedFaces(protectedFaces);
    engine.setObstacleZones(obstacleZones);
    engine.setLoadMagnitude(loadMagnitude);
    engineRef.current = engine;

    const initialMesh = engine.generateSurfaceMesh(field, densityThreshold, clipPlaneRatio);
    setMeshData(initialMesh);
  }, []);

  // Sync state changes with engine
  useEffect(() => {
    if (engineRef.current) {
      engineRef.current.setMode(mode);
      engineRef.current.setProtectedFaces(protectedFaces);
      engineRef.current.setObstacleZones(obstacleZones);
      engineRef.current.setLoadMagnitude(loadMagnitude);
    }
  }, [mode, protectedFaces, obstacleZones, loadMagnitude]);

  // Update mesh whenever threshold, field, or clipping changes
  const refreshSurfaceMesh = useCallback(() => {
    if (!engineRef.current) return;
    const mesh = engineRef.current.generateSurfaceMesh(field, densityThreshold, clipPlaneRatio);
    setMeshData(mesh);
  }, [field, densityThreshold, clipPlaneRatio]);

  useEffect(() => {
    refreshSurfaceMesh();
  }, [field, densityThreshold, clipPlaneRatio, refreshSurfaceMesh]);

  // Handle Preset change
  const handlePresetChange = (newPreset: DesignDomainPreset) => {
    if (isOptimizing) return;
    setPreset(newPreset);
    if (!engineRef.current) return;

    engineRef.current.setPreset(newPreset);
    setHistory([]);
    setMetrics(null);
    setCurrentIteration(0);
    refreshSurfaceMesh();
    showToast(`Dominio cambiado a: ${newPreset.toUpperCase()}`);
  };

  // Handle Material change & custom materials
  const handleMaterialChange = (newMat: Material) => {
    setMaterial(newMat);
    if (engineRef.current) {
      engineRef.current.setMaterial(newMat);
    }
  };

  const handleSelectMaterial = (m: Material) => {
    setMaterial(m);
    if (engineRef.current) {
      engineRef.current.setMaterial(m);
    }
    showToast(`Material activo: ${m.name}`);
  };

  const handleAddCustomMaterial = (newMat: Material) => {
    setMaterialsList((prev) => [newMat, ...prev]);
    setMaterial(newMat);
    if (engineRef.current) {
      engineRef.current.setMaterial(newMat);
    }
    showToast(`Material personalizado creado: ${newMat.name}`);
  };

  const handleRemoveCustomMaterial = (id: string) => {
    setMaterialsList((prev) => {
      const updated = prev.filter((m) => m.id !== id);
      if (material.id === id) {
        const fallback = updated[0] || STANDARD_MATERIALS[0];
        setMaterial(fallback);
        if (engineRef.current) {
          engineRef.current.setMaterial(fallback);
        }
      }
      return updated;
    });
    showToast('Material personalizado eliminado');
  };

  // Handle Config change
  const handleConfigChange = (newCfg: Partial<SimpConfig>) => {
    const updated = { ...config, ...newCfg };
    setConfig(updated);
    if (engineRef.current) {
      engineRef.current.setConfig(updated);
    }
  };

  // Handle Mode change (Generativa vs Estructural)
  const handleModeChange = (newMode: OptimizationMode) => {
    setMode(newMode);
    if (engineRef.current) {
      engineRef.current.setMode(newMode);
    }
    showToast(`Modo cambiado a: ${newMode === 'generativa' ? 'Generativa (Bio-Orgánica)' : 'Estructural (SIMP Michell)'}`);
  };

  // Protected Faces Handlers
  const handleToggleProtectedFace = (id: string) => {
    setProtectedFaces((prev) =>
      prev.map((f) => (f.id === id ? { ...f, enabled: !f.enabled } : f))
    );
  };

  const handleAddProtectedFace = (face: ProtectedFace) => {
    setProtectedFaces((prev) => [...prev, face]);
    showToast(`Cara protegida añadida: ${face.name}`);
  };

  const handleRemoveProtectedFace = (id: string) => {
    setProtectedFaces((prev) => prev.filter((f) => f.id !== id));
  };

  // Obstacle Zones Handlers
  const handleToggleObstacle = (id: string) => {
    setObstacleZones((prev) =>
      prev.map((o) => (o.id === id ? { ...o, enabled: !o.enabled } : o))
    );
  };

  const handleAddObstacle = (obstacle: ObstacleZone) => {
    setObstacleZones((prev) => [...prev, obstacle]);
    showToast(`Zona de obstrucción añadida: ${obstacle.name}`);
  };

  const handleRemoveObstacle = (id: string) => {
    setObstacleZones((prev) => prev.filter((o) => o.id !== id));
  };

  // Start Optimization Loop
  const handleStartOptimization = () => {
    if (!engineRef.current) return;
    setIsOptimizing(true);
    startTimeRef.current = Date.now();
    setCurrentIteration(0);
    setHistory([]);

    let iter = 1;
    const maxIter = config.maxIterations;

    const runStep = () => {
      if (!engineRef.current) return;

      const iterData = engineRef.current.stepIteration(iter);
      setCurrentIteration(iter);
      setHistory([...engineRef.current.getHistory()]);

      // Update 3D mesh live
      const currentMesh = engineRef.current.generateSurfaceMesh(field, densityThreshold, clipPlaneRatio);
      setMeshData(currentMesh);

      // Check stopping criteria
      if (iter >= maxIter || iterData.change < config.convergenceTolerance) {
        setIsOptimizing(false);
        const finalMetrics = engineRef.current.getMetrics(startTimeRef.current);
        setMetrics(finalMetrics);
        showToast(`¡Optimización ${mode === 'generativa' ? 'Generativa' : 'Estructural'} finalizada!`);
      } else {
        iter++;
        animationTimerRef.current = window.setTimeout(runStep, 50);
      }
    };

    runStep();
  };

  // Stop Optimization
  const handleStopOptimization = () => {
    if (animationTimerRef.current) {
      clearTimeout(animationTimerRef.current);
      animationTimerRef.current = null;
    }
    setIsOptimizing(false);
    if (engineRef.current) {
      const finalMetrics = engineRef.current.getMetrics(startTimeRef.current);
      setMetrics(finalMetrics);
    }
    showToast('Cálculo detenido');
  };

  // Reset Domain
  const handleReset = () => {
    if (animationTimerRef.current) {
      clearTimeout(animationTimerRef.current);
    }
    setIsOptimizing(false);
    setCurrentIteration(0);
    setHistory([]);
    setMetrics(null);

    if (engineRef.current) {
      engineRef.current.resetDensities();
      refreshSurfaceMesh();
    }
    showToast('Dominio de diseño reiniciado a sólido homogéneo');
  };

  // Export STEP CAD file
  const handleExportStep = () => {
    if (!meshData || !engineRef.current) return;
    const currentMetrics = metrics || engineRef.current.getMetrics(Date.now() - 5000);
    const stepContent = generateStepFile(meshData, material, currentMetrics, dimensions);
    const filename = `topologia_optimizada_${mode}_${preset}_${(config.volumeFraction * 100).toFixed(0)}pct.step`;
    triggerDownload(stepContent, filename, 'application/step');
    showToast(`Archivo CAD STEP descargado: ${filename}`);
  };

  // Export STL file
  const handleExportStl = () => {
    if (!meshData) return;
    const stlContent = generateStlFile(meshData);
    const filename = `topologia_optimizada_${mode}_${preset}.stl`;
    triggerDownload(stlContent, filename, 'model/stl');
    showToast(`Archivo STL descargado: ${filename}`);
  };

  // Export Calculation Technical Report
  const handleExportReport = () => {
    if (!engineRef.current) return;
    const currentMetrics = metrics || engineRef.current.getMetrics(Date.now() - 5000);
    const report = {
      title: 'Reporte de Cálculo - Topologia Optimizada',
      date: new Date().toISOString(),
      mode: mode,
      preset: preset,
      material: {
        name: material.name,
        youngModulusGPa: material.youngModulus,
        yieldStrengthMPa: material.yieldStrength,
        densityKgM3: material.density
      },
      loadConditions: {
        magnitudeN: loadMagnitude,
        direction: loadDirection,
        position: loadPosition
      },
      protectedFaces: protectedFaces.filter((f) => f.enabled),
      obstacleZones: obstacleZones.filter((o) => o.enabled),
      algorithm: {
        type: mode === 'generativa' ? 'Optimización Generativa Bio-Inspirada' : 'Optimización Estructural SIMP Michell',
        targetVolumeFraction: config.volumeFraction,
        filterRadiusElements: config.filterRadius,
        iterationsExecuted: currentMetrics.iterationsCompleted,
        converged: currentMetrics.converged
      },
      results: {
        initialMassKg: currentMetrics.initialMassKg.toFixed(3),
        optimizedMassKg: currentMetrics.optimizedMassKg.toFixed(3),
        massReductionPercent: currentMetrics.massReductionPercent.toFixed(1) + '%',
        maxVonMisesMPa: currentMetrics.maxVonMisesMpa.toFixed(1),
        safetyFactor: currentMetrics.safetyFactor.toFixed(2),
        finalComplianceJoules: currentMetrics.finalCompliance.toFixed(1)
      }
    };
    triggerDownload(
      JSON.stringify(report, null, 2),
      `reporte_topologia_optimizada_${preset}.json`,
      'application/json'
    );
    showToast('Reporte técnico descargado (JSON)');
  };

  return (
    <div className="flex flex-col w-full h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Header con solo el nombre "Topologia Optimizada" y los botones de herramientas */}
      <Header
        activeTool={activeTool}
        onSelectTool={setActiveTool}
        mode={mode}
        onModeChange={handleModeChange}
        isOptimizing={isOptimizing}
        loadMagnitude={loadMagnitude}
        protectedCount={protectedFaces.filter((f) => f.enabled).length}
        obstacleCount={obstacleZones.filter((o) => o.enabled).length}
        currentMaterialName={material.name}
        onStartOptimization={handleStartOptimization}
        onStopOptimization={handleStopOptimization}
      />
      {/* Backend real (pywebview + core vendorizado). Si no hay bridge, muestra preview local. */}
      <BackendBar
        loadMagnitude={loadMagnitude}
        volumeFraction={config.volumeFraction}
        maxIterations={config.maxIterations}
        notify={showToast}
        onMesh={(mesh, source) => {
          setMeshData(mesh);
          setField(source === 'fea' ? 'vonmises' : 'density');
        }}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
        {/* Left Side: Panel de la Herramienta Activa */}
        <aside className="w-full lg:w-[390px] xl:w-[430px] bg-slate-950/95 border-r border-slate-800 p-3 overflow-y-auto flex flex-col gap-3 shrink-0 shadow-xl z-10">
          {/* Renderizado de la herramienta seleccionada en la barra superior */}
          {activeTool === 'carga' && (
            <CargaPanel
              loadMagnitude={loadMagnitude}
              onLoadMagnitudeChange={setLoadMagnitude}
              loadDirection={loadDirection}
              onLoadDirectionChange={setLoadDirection}
              loadPosition={loadPosition}
              onLoadPositionChange={setLoadPosition}
              onStartOptimization={handleStartOptimization}
              isOptimizing={isOptimizing}
            />
          )}

          {activeTool === 'materiales' && (
            <MaterialesPanel
              currentMaterial={material}
              materialsList={materialsList}
              onSelectMaterial={handleSelectMaterial}
              onAddCustomMaterial={handleAddCustomMaterial}
              onRemoveCustomMaterial={handleRemoveCustomMaterial}
              isOptimizing={isOptimizing}
            />
          )}

          {activeTool === 'elasticidad' && (
            <ElasticidadPanel
              material={material}
              materialsList={materialsList}
              onMaterialChange={handleMaterialChange}
              onOpenMaterialsWindow={() => setActiveTool('materiales')}
              isOptimizing={isOptimizing}
            />
          )}

          {activeTool === 'obstrucciones' && (
            <ObstruccionesPanel
              obstacles={obstacleZones}
              onToggleObstacle={handleToggleObstacle}
              onAddObstacle={handleAddObstacle}
              onRemoveObstacle={handleRemoveObstacle}
              isOptimizing={isOptimizing}
            />
          )}

          {activeTool === 'protegida' && (
            <ProtegidaPanel
              protectedFaces={protectedFaces}
              onToggleProtectedFace={handleToggleProtectedFace}
              onAddProtectedFace={handleAddProtectedFace}
              onRemoveProtectedFace={handleRemoveProtectedFace}
              isOptimizing={isOptimizing}
            />
          )}

          {activeTool === 'optimizar' && (
            <OptimizarPanel
              mode={mode}
              onModeChange={handleModeChange}
              config={config}
              onConfigChange={handleConfigChange}
              dimensions={dimensions}
              isOptimizing={isOptimizing}
              currentIteration={currentIteration}
              maxIterations={config.maxIterations}
              onStartOptimization={handleStartOptimization}
              onStopOptimization={handleStopOptimization}
              onReset={handleReset}
            />
          )}

          {activeTool === 'analisis' && (
            <AnalisisPanel
              field={field}
              onFieldChange={setField}
              densityThreshold={densityThreshold}
              onThresholdChange={setDensityThreshold}
              clipPlaneRatio={clipPlaneRatio}
              onClipPlaneChange={setClipPlaneRatio}
              metrics={metrics}
              history={history}
              material={material}
              onExportStep={handleExportStep}
              onExportStl={handleExportStl}
              onExportReport={handleExportReport}
            />
          )}
        </aside>

        {/* Center / Right: Viewport 3D Principal */}
        <main className="flex-1 flex flex-col min-h-0 p-3 gap-3 overflow-hidden relative">
          <div className="flex-1 w-full h-full relative rounded-2xl overflow-hidden border border-slate-800 bg-slate-950">
            <Viewport3D
              meshData={meshData}
              dimensions={dimensions}
              preset={preset}
              field={field}
              showWireframe={showWireframe}
              showBounds={showBounds}
              showGlyphs={showGlyphs}
              clipPlaneRatio={clipPlaneRatio}
              densityThreshold={densityThreshold}
              onClipPlaneChange={setClipPlaneRatio}
              onThresholdChange={setDensityThreshold}
              onFieldChange={setField}
              activeTool={activeTool}
              loadMagnitude={loadMagnitude}
              loadDirection={loadDirection}
              protectedFaces={protectedFaces}
              obstacleZones={obstacleZones}
            />

            {/* Badges de estado en tiempo real en la esquina superior del viewport */}
            <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2 pointer-events-none">
              <div className="bg-slate-900/90 backdrop-blur border border-slate-700/80 px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-200 flex items-center gap-1.5 shadow-md">
                {mode === 'generativa' ? (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                    <span>Modo Generativo</span>
                  </>
                ) : (
                  <>
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Modo Estructural SIMP</span>
                  </>
                )}
              </div>

              {isOptimizing && (
                <div className="bg-amber-500/20 backdrop-blur border border-amber-500/50 px-2.5 py-1 rounded-lg text-xs font-mono font-bold text-amber-300 flex items-center gap-1.5 animate-pulse shadow-md">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  <span>Iteración {currentIteration} / {config.maxIterations}</span>
                </div>
              )}

              {metrics && !isOptimizing && (
                <div className="bg-emerald-500/20 backdrop-blur border border-emerald-500/40 px-2.5 py-1 rounded-lg text-xs font-mono font-bold text-emerald-300 flex items-center gap-1.5 shadow-md">
                  <span>Masa: -{metrics.massReductionPercent.toFixed(1)}%</span>
                  <span className="text-slate-400">|</span>
                  <span>FS: {metrics.safetyFactor.toFixed(2)}×</span>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Floating Notification Toast */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-slate-900/95 border border-sky-500/50 text-sky-200 px-4 py-2.5 rounded-xl shadow-2xl backdrop-blur-md text-xs font-medium flex items-center gap-2 animate-in fade-in slide-in-from-bottom-3">
          <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
          {toastMessage}
        </div>
      )}
    </div>
  );
}
