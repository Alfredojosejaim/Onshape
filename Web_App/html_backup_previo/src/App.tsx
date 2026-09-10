import React, { useState, useEffect, useCallback } from 'react';
import { ScreenId, FeaBackend, MaterialProperty, SimpConfig } from './types';
import { MATERIALS } from './data/materials';
import { backend } from './lib/bridge';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Footer } from './components/Footer';
import { Screen1CadPreProcess } from './components/Screens/Screen1CadPreProcess';
import { Screen2MeshingConditions } from './components/Screens/Screen2MeshingConditions';
import { Screen3FeaSolver } from './components/Screens/Screen3FeaSolver';
import { Screen4TopologyOptimization } from './components/Screens/Screen4TopologyOptimization';
import { Screen5GenerativeBRepExport } from './components/Screens/Screen5GenerativeBRepExport';
import { ImportStepModal } from './components/Modals/ImportStepModal';
import { HelpModal } from './components/Modals/HelpModal';
import { CreateStudyModal } from './components/Modals/CreateStudyModal';

export interface BackendSnapshot {
  model_name?: string;
  has_mesh?: boolean;
  has_result?: boolean;
  num_elements?: number;
  num_nodes?: number;
  elements_count?: number;
  nodes_count?: number;
  elementsCount?: number;
  nodesCount?: number;
  [k: string]: unknown;
}

function snapshotCounts(s: BackendSnapshot | null): { elements: number; nodes: number } | null {
  if (!s) return null;
  const rawE = s.num_elements ?? s.elements_count ?? s.elementsCount;
  const rawN = s.num_nodes ?? s.nodes_count ?? s.nodesCount;
  if (typeof rawE === 'number' && typeof rawN === 'number') return { elements: rawE, nodes: rawN };
  if (typeof rawE === 'number') return { elements: rawE, nodes: 38412 };
  if (typeof rawN === 'number') return { elements: 184920, nodes: rawN };
  return null;
}

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenId>('modelo-cad-y-pre-proceso');
  const [materials, setMaterials] = useState<MaterialProperty[]>(MATERIALS);
  const [selectedMaterial, setSelectedMaterial] = useState<MaterialProperty>(MATERIALS[0]);
  const [activeBackend, setActiveBackend] = useState<FeaBackend>('numpy');
  const [activeFilename, setActiveFilename] = useState<string>('cono_soporte_aero.step');
  const [snapshot, setSnapshot] = useState<BackendSnapshot | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);

  const [simpConfig, setSimpConfig] = useState<SimpConfig>({
    penaltyExponent: 3.0,
    targetVolumeFraction: 0.35,
    filterRadiusMm: 6.0,
    maxIterations: 50,
    algorithm: 'OC',
    minDensity: 0.001,
  });

  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState<boolean>(false);
  const [isCreateStudyModalOpen, setIsCreateStudyModalOpen] = useState<boolean>(false);

  const refreshSnapshot = useCallback(async () => {
    try {
      const r = (await backend.getSnapshot()) as { ok: boolean; snapshot?: BackendSnapshot };
      if (r.ok && r.snapshot) {
        setSnapshot(r.snapshot);
        if (typeof r.snapshot.model_name === 'string' && r.snapshot.model_name) {
          setActiveFilename(r.snapshot.model_name);
        }
      }
    } catch (e) {
      setBackendError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  // Carga inicial: materiales + snapshot
  useEffect(() => {
    (async () => {
      try {
        const r = (await backend.getMaterials()) as {
          ok: boolean;
          materials?: MaterialProperty[];
          names?: string[];
        };
        if (r.ok && r.materials && r.materials.length > 0) {
          setMaterials(r.materials);
          setSelectedMaterial((prev) => r.materials!.find((m) => m.id === prev.id) ?? r.materials![0]);
        } else {
          setMaterials(MATERIALS);
        }
      } catch (e) {
        setBackendError(e instanceof Error ? e.message : String(e));
        setMaterials(MATERIALS);
      }
      await refreshSnapshot();
    })();
  }, [refreshSnapshot]);

  // Keyboard navigation shortcuts for engineers: 1-5 to navigate screens, ? for help
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore when typing inside input elements
      if (['INPUT', 'SELECT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
        return;
      }

      if (e.key === '1') {
        setCurrentScreen('modelo-cad-y-pre-proceso');
      } else if (e.key === '2') {
        setCurrentScreen('mallado-y-condiciones');
      } else if (e.key === '3') {
        setCurrentScreen('solver-fea-y-tensiones');
      } else if (e.key === '4') {
        setCurrentScreen('optimizacion-topologica-simp');
      } else if (e.key === '5') {
        setCurrentScreen('generativo-y-b-rep-export');
      } else if (e.key === '?' || (e.key === 'h' && !e.ctrlKey && !e.metaKey)) {
        setIsHelpModalOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleUpdateSimpConfig = (cfg: Partial<SimpConfig>) => {
    setSimpConfig((prev) => ({ ...prev, ...cfg }));
  };

  const handleSelectMaterial = async (m: MaterialProperty) => {
    setSelectedMaterial(m);
    try {
      await backend.setMaterial(m.name);
    } catch (e) {
      setBackendError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleModelSelected = (filename: string) => {
    setActiveFilename(filename);
    setCurrentScreen('modelo-cad-y-pre-proceso');
    void refreshSnapshot();
  };

  const handleCreateStudy = (config: any) => {
    if (config.selectedMaterialId) {
      const mat = materials.find((m) => m.id === config.selectedMaterialId);
      if (mat) void handleSelectMaterial(mat);
    }
    setCurrentScreen('modelo-cad-y-pre-proceso');
  };

  const counts = snapshotCounts(snapshot);

  return (
    <div className="min-h-screen bg-[#0f1117] text-[#e0e2ef] font-body flex flex-col selection:bg-[#0ea5e9]/30 selection:text-[#7bd0ff]">
      {/* Top Application Header */}
      <Header
        currentScreen={currentScreen}
        onSelectScreen={setCurrentScreen}
        activeFilename={activeFilename}
        backend={activeBackend}
        onToggleBackend={() =>
          setActiveBackend((b) => (b === 'numpy' ? 'kratos' : 'numpy'))
        }
        onOpenImportModal={() => setIsImportModalOpen(true)}
        onOpenHelpModal={() => setIsHelpModalOpen(true)}
        onOpenCreateStudyModal={() => setIsCreateStudyModalOpen(true)}
      />

      {backendError && (
        <div className="mx-2 mt-20 mb-0 rounded border border-[#ef4444]/40 bg-[#ef4444]/10 px-3 py-1.5 text-[11px] text-[#fca5a5]">
          Error de backend: {backendError}
          <button onClick={() => setBackendError(null)} className="ml-2 underline">
            ocultar
          </button>
        </div>
      )}

      {/* Main Structural Area with Left Sidebar and Content Area */}
      <div className="flex-1 flex pt-20 pb-7">
        {/* Persistent Left Operations Tree & Solver Status Sidebar */}
        <Sidebar currentScreen={currentScreen} onSelectScreen={setCurrentScreen} snapshot={snapshot} />

        {/* Dynamic Screen Viewport Area */}
        <div className="flex-1 ml-64 min-h-[calc(100vh-6.75rem)] overflow-x-hidden">
          {currentScreen === 'modelo-cad-y-pre-proceso' && (
            <Screen1CadPreProcess
              onAdvanceToMesh={() => setCurrentScreen('mallado-y-condiciones')}
              selectedMaterial={selectedMaterial}
              onSelectMaterial={handleSelectMaterial}
              activeFilename={activeFilename}
              materials={materials}
            />
          )}

          {currentScreen === 'mallado-y-condiciones' && (
            <Screen2MeshingConditions
              onAdvanceToFea={() => setCurrentScreen('solver-fea-y-tensiones')}
              activeFilename={activeFilename}
            />
          )}

          {currentScreen === 'solver-fea-y-tensiones' && (
            <Screen3FeaSolver
              onAdvanceToSimp={() => setCurrentScreen('optimizacion-topologica-simp')}
              backend={activeBackend}
              onSetBackend={setActiveBackend}
              material={selectedMaterial}
            />
          )}

          {currentScreen === 'optimizacion-topologica-simp' && (
            <Screen4TopologyOptimization
              onAdvanceToBRep={() => setCurrentScreen('generativo-y-b-rep-export')}
              simpConfig={simpConfig}
              onUpdateSimpConfig={handleUpdateSimpConfig}
            />
          )}

          {currentScreen === 'generativo-y-b-rep-export' && (
            <Screen5GenerativeBRepExport
              material={selectedMaterial}
              onRestartStudy={() => setCurrentScreen('modelo-cad-y-pre-proceso')}
              activeFilename={activeFilename}
            />
          )}
        </div>
      </div>

      {/* Fixed Bottom Telemetry Footer */}
      <Footer elementsCount={counts?.elements ?? 184920} nodesCount={counts?.nodes ?? 38412} />

      {/* Modal Dialogs */}
      <ImportStepModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onModelSelected={handleModelSelected}
      />

      <HelpModal isOpen={isHelpModalOpen} onClose={() => setIsHelpModalOpen(false)} />

      <CreateStudyModal
        isOpen={isCreateStudyModalOpen}
        onClose={() => setIsCreateStudyModalOpen(false)}
        onCreateStudy={handleCreateStudy}
      />
    </div>
  );
}
