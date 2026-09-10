/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { CadPreprocesoScreen } from './components/screens/CadPreprocesoScreen';
import { MalladoCondicionesScreen } from './components/screens/MalladoCondicionesScreen';
import { SolverFeaScreen } from './components/screens/SolverFeaScreen';
import { OptimizacionSimpScreen } from './components/screens/OptimizacionSimpScreen';
import { GenerativoExportScreen } from './components/screens/GenerativoExportScreen';
import { ImportModal, ExportModal, HelpModal, SettingsModal } from './components/Modals';

import {
  TabId,
  MaterialProperties,
  MeshingSettings,
  CadFeature,
  BoundaryCondition,
  FeaResults,
  SimpOptimizationState,
  GenerativeExportState,
} from './types';

import {
  MATERIALS_LIBRARY,
  INITIAL_CAD_FEATURES,
  INITIAL_BOUNDARY_CONDITIONS,
  INITIAL_MESHING,
  INITIAL_FEA,
  INITIAL_SIMP_STATE,
  INITIAL_GENERATIVE_EXPORT,
} from './data';

export default function App() {
  // Current active stage / workspace tab
  const [activeTab, setActiveTab] = useState<TabId>('cad-preproceso');
  const [projectName, setProjectName] = useState<string>('Brazo_Soporte_Aero_v2.cad');

  // Engineering study state
  const [materials] = useState<MaterialProperties[]>(MATERIALS_LIBRARY);
  const [selectedMaterial, setSelectedMaterial] = useState<MaterialProperties>(MATERIALS_LIBRARY[0]);
  const [cadFeatures, setCadFeatures] = useState<CadFeature[]>(INITIAL_CAD_FEATURES);
  const [boundaryConditions, setBoundaryConditions] = useState<BoundaryCondition[]>(INITIAL_BOUNDARY_CONDITIONS);
  const [meshing, setMeshing] = useState<MeshingSettings>(INITIAL_MESHING);
  const [isRemeshing, setIsRemeshing] = useState<boolean>(false);
  const [forceMagnitude, setForceMagnitude] = useState<number>(4500);
  const [selectedFace, setSelectedFace] = useState<number | null>(7);

  // FEA State
  const [fea, setFea] = useState<FeaResults>(INITIAL_FEA);

  // SIMP Topology State
  const [simpState, setSimpState] = useState<SimpOptimizationState>(INITIAL_SIMP_STATE);

  // Generative / Export State
  const [exportState, setExportState] = useState<GenerativeExportState>(INITIAL_GENERATIVE_EXPORT);

  // Modal dialog states
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Handler for remeshing geometry
  const handleRemesh = () => {
    setIsRemeshing(true);
    setTimeout(() => {
      const factor = 1.5 / meshing.hMin;
      const newElemCount = Math.round(215410 * factor);
      const newNodes = Math.round(48290 * factor);
      setMeshing((prev) => ({
        ...prev,
        elementsCount: newElemCount,
        nodesCount: newNodes,
        jacobianQuality: Math.min(0.92, Math.max(0.75, 0.84 + (Math.random() * 0.06 - 0.03))),
      }));
      setIsRemeshing(false);
    }, 900);
  };

  // Handler for toggling feature visibility in tree
  const handleToggleFeatureVisibility = (id: string) => {
    setCadFeatures((prev) =>
      prev.map((item) => (item.id === id ? { ...item, visible: !item.visible } : item))
    );
  };

  // Handler for boundary condition toggle
  const handleToggleBc = (id: string) => {
    setBoundaryConditions((prev) =>
      prev.map((item) => (item.id === id ? { ...item, active: !item.active } : item))
    );
  };

  // Handler for updating meshing settings
  const handleUpdateMeshing = (newSettings: Partial<MeshingSettings>) => {
    setMeshing((prev) => ({ ...prev, ...newSettings }));
  };

  // Handler for running FEA solver
  const handleSolveFea = () => {
    setFea((prev) => ({ ...prev, isSolving: true }));
    setTimeout(() => {
      // Recompute stress based on force and material
      const stressRatio = forceMagnitude / 4500;
      const newMaxStress = Math.round(482.4 * stressRatio * 10) / 10;
      const newSafetyFactor = Math.round((selectedMaterial.yieldStrength / newMaxStress) * 100) / 100;
      setFea((prev) => ({
        ...prev,
        isSolving: false,
        isSolved: true,
        maxVonMises: newMaxStress,
        safetyFactor: newSafetyFactor,
        maxDisplacement: Math.round(0.42 * stressRatio * 100) / 100,
      }));
    }, 1200);
  };

  // Handler for importing new CAD model
  const handleImportModel = (newModelName: string) => {
    setProjectName(newModelName);
    setCadFeatures((prev) =>
      prev.map((f) => (f.type === 'solid' ? { ...f, name: newModelName } : f))
    );
    setActiveTab('cad-preproceso');
  };

  return (
    <div className="min-h-screen bg-[#0f1117] text-[#e0e2ef] flex flex-col select-none font-sans">
      {/* 1. Single Unified Top Bar */}
      <Header
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        onOpenImport={() => setIsImportOpen(true)}
        onOpenExport={() => setIsExportOpen(true)}
        onOpenHelp={() => setIsHelpOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        projectName={projectName}
      />

      {/* 2. Main Workspace Screen according to active tab */}
      <main className="w-full pb-7 pt-[5.25rem] min-h-screen flex-1 bg-[#0f1117] flex flex-col">
        {activeTab === 'cad-preproceso' && (
          <CadPreprocesoScreen
            materials={materials}
            selectedMaterial={selectedMaterial}
            onSelectMaterial={setSelectedMaterial}
            meshing={meshing}
            onUpdateMeshing={handleUpdateMeshing}
            onRemesh={handleRemesh}
            isRemeshing={isRemeshing}
            cadFeatures={cadFeatures}
            onToggleFeatureVisibility={handleToggleFeatureVisibility}
            onProceedToNextStep={() => setActiveTab('mallado-condiciones')}
            forceMagnitude={forceMagnitude}
            onUpdateForce={setForceMagnitude}
            selectedFace={selectedFace}
            onSelectFace={setSelectedFace}
          />
        )}

        {activeTab === 'mallado-condiciones' && (
          <MalladoCondicionesScreen
            meshing={meshing}
            onUpdateMeshing={handleUpdateMeshing}
            boundaryConditions={boundaryConditions}
            onToggleBc={handleToggleBc}
            onProceedToFea={() => setActiveTab('solver-fea')}
            forceMagnitude={forceMagnitude}
          />
        )}

        {activeTab === 'solver-fea' && (
          <SolverFeaScreen
            fea={fea}
            material={selectedMaterial}
            onUpdateDeformedScale={(scale) => setFea((prev) => ({ ...prev, deformedScale: scale }))}
            onSolveFea={handleSolveFea}
            onProceedToSimp={() => setActiveTab('optimizacion-simp')}
            forceMagnitude={forceMagnitude}
          />
        )}

        {activeTab === 'optimizacion-simp' && (
          <OptimizacionSimpScreen
            simpState={simpState}
            onUpdateSimpState={setSimpState}
            onProceedToExport={() => setActiveTab('generativo-export')}
            forceMagnitude={forceMagnitude}
          />
        )}

        {activeTab === 'generativo-export' && (
          <GenerativoExportScreen
            exportState={exportState}
            onUpdateExportState={setExportState}
            material={selectedMaterial}
            forceMagnitude={forceMagnitude}
            onOpenExportModal={() => setIsExportOpen(true)}
          />
        )}
      </main>

      {/* 3. Global Precision Engineering Status Bar */}
      <Footer
        elementsCount={meshing.elementsCount}
        nodesCount={meshing.nodesCount}
      />

      {/* Dialog Modals */}
      <ImportModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onImportModel={handleImportModel}
      />

      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        projectName={projectName}
      />

      <HelpModal
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
}
