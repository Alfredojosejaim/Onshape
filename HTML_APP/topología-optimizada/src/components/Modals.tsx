import React, { useEffect, useState } from 'react';
import { BoundaryCondition, CadModelPreset, Material, OptimizationState } from '../types';

interface ModalsProps {
  showImport: boolean;
  onCloseImport: () => void;
  models: CadModelPreset[];
  // UI-CLEAN (reversible): null = sin pieza de referencia.
  currentModel: CadModelPreset | null;
  onSelectModel: (m: CadModelPreset) => void;
  onCustomFileUpload: (file: File) => void;

  showExport: boolean;
  onCloseExport: () => void;
  selectedMaterial: Material;
  optimizationState: OptimizationState;

  showHelp: boolean;
  onCloseHelp: () => void;

  editingCondition: BoundaryCondition | null;
  onCloseEditCondition: () => void;
  onSaveCondition: (condition: BoundaryCondition) => void;
}

export const Modals: React.FC<ModalsProps> = ({
  showImport,
  onCloseImport,
  models,
  currentModel,
  onSelectModel,
  onCustomFileUpload,

  showExport,
  onCloseExport,
  selectedMaterial,
  optimizationState,

  showHelp,
  onCloseHelp,

  editingCondition,
  onCloseEditCondition,
  onSaveCondition,
}) => {
  const [loadX, setLoadX] = useState('0');
  const [loadY, setLoadY] = useState('-4500');
  const [loadZ, setLoadZ] = useState('1200');
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  // TREE-RENAME (reversible): nombre editable de la condicion (identificar
  // varias del mismo tipo en el arbol). Para volver atras: quitar campo.
  const [condName, setCondName] = useState('');
  useEffect(() => {
    setCondName(editingCondition?.name ?? '');
    const v = editingCondition?.value;
    if (v && v.length === 3) {
      setLoadX(String(v[0]));
      setLoadY(String(v[1]));
      setLoadZ(String(v[2]));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingCondition?.id]);

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onCustomFileUpload(e.dataTransfer.files[0]);
      onCloseImport();
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onCustomFileUpload(e.target.files[0]);
      onCloseImport();
    }
  };

  const triggerExport = (format: string) => {
    setExportNotice(`Generando archivo ${format}...`);
    setTimeout(() => {
      // Simulate downloadable artifact
      const element = document.createElement('a');
      // UI-CLEAN (reversible): nombre generico sin modelo.
      const baseName = (currentModel?.filename ?? 'modelo').replace('.step', '');
      const file = new Blob(
        [
          `# TOPOLOGÍA OPTIMIZADA CAE EXPORT\n# Pieza: ${currentModel?.filename ?? 'sin modelo'}\n# Material: ${selectedMaterial.name}\n# Iteración: ${optimizationState.currentIteration}\n# Masa Optimizada: ${optimizationState.currentMassKg.toFixed(3)} kg\n`,
        ],
        { type: 'text/plain' }
      );
      element.href = URL.createObjectURL(file);
      element.download = `${baseName}_optimizado.${format.toLowerCase()}`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      setExportNotice(`¡Archivo ${format} descargado con éxito!`);
      setTimeout(() => setExportNotice(null), 2500);
    }, 600);
  };

  return (
    <>
      {/* Import CAD Modal */}
      {showImport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-surface-container-low border border-border-subtle rounded-xl shadow-2xl p-6 flex flex-col gap-4 text-text-primary">
            <div className="flex items-center justify-between border-b border-border-subtle/50 pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary text-[22px]">upload_file</span>
                <h3 className="font-semibold text-[16px]">Importar Geometría CAD (STEP / STL / IGES)</h3>
              </div>
              <button
                onClick={onCloseImport}
                className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-elevated text-text-muted hover:text-text-primary"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            {/* Drag and Drop Zone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              className="border-2 border-dashed border-border-subtle hover:border-secondary/60 rounded-xl p-6 flex flex-col items-center justify-center gap-2 text-center bg-surface-elevated/30 transition-colors cursor-pointer"
              onClick={() => document.getElementById('cad-file-input')?.click()}
            >
              <input
                id="cad-file-input"
                type="file"
                accept=".step,.stp,.iges,.igs,.stl,.brep,.vtk"
                className="hidden"
                onChange={handleFileInput}
              />
              <span className="material-symbols-outlined text-[36px] text-secondary">cloud_upload</span>
              <p className="text-[13px] font-medium text-text-primary">
                Arrastra tu archivo CAD aquí o haz clic para examinar
              </p>
              <p className="text-[11px] font-mono text-text-muted">
                Formatos soportados: STEP (.stp, .step), IGES, STL (binario/ASCII), Gmsh (.msh)
              </p>
            </div>

            {/* Presets List */}
            <div className="flex flex-col gap-2">
              <span className="text-[11px] font-mono text-text-muted uppercase">O selecciona un modelo estándar aeroespacial:</span>
              <div className="flex flex-col gap-1.5">
                {/* UI-CLEAN (reversible): lista vacia sin piezas de referencia. */}
                {models.length === 0 ? (
                  <div className="text-[11px] text-text-muted text-center py-2">Sin piezas cargadas</div>
                ) : (
                models.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      onSelectModel(m);
                      onCloseImport();
                    }}
                    className={`flex items-center justify-between p-2.5 rounded-lg border text-left transition-all ${
                      // UI-CLEAN (reversible): guard sin modelo.
                      m.id === currentModel?.id
                        ? 'bg-secondary/15 border-secondary/50 text-text-primary'
                        : 'bg-surface-elevated/40 border-border-subtle/40 hover:bg-surface-elevated text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="material-symbols-outlined text-[20px] text-primary">deployed_code</span>
                      <div>
                        <div className="font-semibold text-[12px]">{m.displayName}</div>
                        <div className="text-[10px] font-mono text-text-muted">{m.filename}</div>
                      </div>
                    </div>
                    <div className="text-right text-[10px] font-mono">
                      <div className="text-secondary">{m.elementsTet4.toLocaleString()} tets</div>
                      <div className="text-text-muted">{m.volumeCm3} cm³</div>
                    </div>
                  </button>
                )))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={onCloseImport}
                className="px-4 py-1.5 rounded-lg bg-surface-elevated hover:bg-surface-container-high text-text-primary text-[12px] font-medium border border-border-subtle"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-surface-container-low border border-border-subtle rounded-xl shadow-2xl p-6 flex flex-col gap-4 text-text-primary">
            <div className="flex items-center justify-between border-b border-border-subtle/50 pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary text-[22px]">download</span>
                <h3 className="font-semibold text-[16px]">Exportar Resultados y Malla Optimizada</h3>
              </div>
              <button
                onClick={onCloseExport}
                className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-elevated text-text-muted hover:text-text-primary"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            {exportNotice && (
              <div className="p-2.5 rounded-lg bg-fea-stress-optimal/15 border border-fea-stress-optimal/40 text-fea-stress-optimal text-[12px] font-mono flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px]">check_circle</span>
                <span>{exportNotice}</span>
              </div>
            )}

            <div className="flex flex-col gap-2 font-mono text-[11px]">
              <div className="p-3 bg-surface-elevated/40 rounded-lg border border-border-subtle/30 flex justify-between items-center">
                <div>
                  <div className="font-bold text-text-primary text-[12px]">Malla STL para Fabricación Aditiva</div>
                  <div className="text-text-muted text-[10px]">Superficie isosuperficie suavizada lista para DMLS / SLS</div>
                </div>
                <button
                  onClick={() => triggerExport('STL')}
                  className="px-3 py-1.5 rounded bg-primary-container hover:bg-secondary text-on-primary font-semibold text-[11px]"
                >
                  .STL
                </button>
              </div>

              <div className="p-3 bg-surface-elevated/40 rounded-lg border border-border-subtle/30 flex justify-between items-center">
                <div>
                  <div className="font-bold text-text-primary text-[12px]">Sólido B-Rep STEP</div>
                  <div className="text-text-muted text-[10px]">Geometría reconstruida para integración CAD (CATIA, NX)</div>
                </div>
                <button
                  onClick={() => triggerExport('STEP')}
                  className="px-3 py-1.5 rounded bg-surface-elevated hover:bg-surface-container-high border border-border-subtle text-text-primary font-semibold text-[11px]"
                >
                  .STEP
                </button>
              </div>

              <div className="p-3 bg-surface-elevated/40 rounded-lg border border-border-subtle/30 flex justify-between items-center">
                <div>
                  <div className="font-bold text-text-primary text-[12px]">Archivo de Resultados VTK</div>
                  <div className="text-text-muted text-[10px]">Campo de densidades y tensiones para ParaView</div>
                </div>
                <button
                  onClick={() => triggerExport('VTK')}
                  className="px-3 py-1.5 rounded bg-surface-elevated hover:bg-surface-container-high border border-border-subtle text-text-primary font-semibold text-[11px]"
                >
                  .VTK
                </button>
              </div>

              <div className="p-3 bg-surface-elevated/40 rounded-lg border border-border-subtle/30 flex justify-between items-center">
                <div>
                  <div className="font-bold text-text-primary text-[12px]">Informe Técnico Certificado (PDF)</div>
                  <div className="text-text-muted text-[10px]">Cálculo de masa, cumplimiento, tensiones y factor de seguridad</div>
                </div>
                <button
                  onClick={() => triggerExport('PDF')}
                  className="px-3 py-1.5 rounded bg-secondary/20 hover:bg-secondary/30 text-secondary border border-secondary/40 font-semibold text-[11px]"
                >
                  .PDF
                </button>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={onCloseExport}
                className="px-4 py-1.5 rounded-lg bg-surface-elevated hover:bg-surface-container-high text-text-primary text-[12px] font-medium border border-border-subtle"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Help Modal */}
      {showHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl bg-surface-container-low border border-border-subtle rounded-xl shadow-2xl p-6 flex flex-col gap-4 text-text-primary max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-border-subtle/50 pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary text-[22px]">help</span>
                <h3 className="font-semibold text-[16px]">Guía de Uso y Atajos de Teclado (F1)</h3>
              </div>
              <button
                onClick={onCloseHelp}
                className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-elevated text-text-muted hover:text-text-primary"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            <div className="flex flex-col gap-3 text-[12px]">
              <div className="bg-surface-elevated/40 p-3 rounded-lg border border-border-subtle/30">
                <h4 className="font-semibold text-secondary text-[13px] mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">3d_rotation</span>
                  Navegación en el Viewport 3D
                </h4>
                <div className="grid grid-cols-2 gap-2 font-mono text-[11px] text-text-secondary">
                  <div>
                    <strong className="text-text-primary">Click Izquierdo + Arrastrar:</strong> Rotación Orbital CAD
                  </div>
                  <div>
                    <strong className="text-text-primary">Shift + Click Izq / Botón Central:</strong> Desplazamiento Pan
                  </div>
                  <div>
                    <strong className="text-text-primary">Rueda del Ratón:</strong> Zoom In / Zoom Out
                  </div>
                  <div>
                    <strong className="text-text-primary">Click en ViewCube:</strong> Vistas Ortogonales (Top, Front, Right)
                  </div>
                </div>
              </div>

              <div className="bg-surface-elevated/40 p-3 rounded-lg border border-border-subtle/30">
                <h4 className="font-semibold text-tertiary text-[13px] mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">functions</span>
                  Formulación Matemática SIMP
                </h4>
                <p className="text-text-secondary text-[11px] leading-relaxed mb-2">
                  El método SIMP (Solid Isotropic Material with Penalization) interpola la rigidez del material según:
                </p>
                <div className="bg-surface-container-lowest p-2 rounded font-mono text-[12px] text-secondary text-center">
                  E_e(ρ_e) = E_min + ρ_e^p · (E_0 - E_min), con p = 3.0
                </div>
                <p className="text-text-muted text-[10px] mt-2">
                  La penalización $p=3.0$ fuerza a las densidades intermedias hacia $0$ (vacío) o $1$ (sólido),
                  evitando soluciones porosas no fabricables.
                </p>
              </div>

              <div className="bg-surface-elevated/40 p-3 rounded-lg border border-border-subtle/30">
                <h4 className="font-semibold text-fea-stress-optimal text-[13px] mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">shield</span>
                  Condiciones de Contorno
                </h4>
                <div className="flex flex-col gap-1 text-[11px] text-text-secondary">
                  <div>
                    <span className="text-fea-stress-optimal font-semibold">SAFE (Región Preservada):</span> Fija la densidad ρ=1.0 para taladros de pernos, roscas y alojamientos de rodamientos.
                  </div>
                  <div>
                    <span className="text-fea-stress-critical font-semibold">VOID (Keep-out):</span> Fija la densidad ρ=0.0 para garantizar el paso libre de tornillería o componentes móviles.
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={onCloseHelp}
                className="px-4 py-1.5 rounded-lg bg-primary-container hover:bg-secondary text-on-primary text-[12px] font-semibold"
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Boundary Condition Modal */}
      {editingCondition && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-surface-container-low border border-border-subtle rounded-xl shadow-2xl p-5 flex flex-col gap-3 text-text-primary">
            <div className="flex items-center justify-between border-b border-border-subtle/50 pb-2">
              <h3 className="font-semibold text-[14px] flex items-center gap-1.5">
                <span className="material-symbols-outlined text-secondary text-[18px]">edit</span>
                Editar {editingCondition.name}
              </h3>
              <button
                onClick={onCloseEditCondition}
                className="text-text-muted hover:text-text-primary"
              >
                <span className="material-symbols-outlined text-[16px]">close</span>
              </button>
            </div>

            {editingCondition.type === 'carga' ? (
              <div className="flex flex-col gap-2 font-mono text-[11px]">
                <span className="text-text-muted">Nombre en el árbol:</span>
                <input
                  type="text"
                  value={condName}
                  onChange={(e) => setCondName(e.target.value)}
                  className="bg-surface-elevated border border-border-subtle rounded px-2 py-1 text-text-primary font-sans text-[12px] outline-none focus:border-secondary/60"
                />
                <span className="text-text-muted">Componentes del Vector Fuerza [N]:</span>
                <div className="flex items-center gap-2">
                  <span className="text-fea-stress-critical font-bold">Fx:</span>
                  <input
                    type="number"
                    value={loadX}
                    onChange={(e) => setLoadX(e.target.value)}
                    className="flex-1 bg-surface-elevated border border-border-subtle rounded px-2 py-1 text-text-primary"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-fea-stress-optimal font-bold">Fy:</span>
                  <input
                    type="number"
                    value={loadY}
                    onChange={(e) => setLoadY(e.target.value)}
                    className="flex-1 bg-surface-elevated border border-border-subtle rounded px-2 py-1 text-text-primary"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-secondary font-bold">Fz:</span>
                  <input
                    type="number"
                    value={loadZ}
                    onChange={(e) => setLoadZ(e.target.value)}
                    className="flex-1 bg-surface-elevated border border-border-subtle rounded px-2 py-1 text-text-primary"
                  />
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-2 text-[12px] text-text-secondary">
                <span className="font-mono text-[11px] text-text-muted">Nombre en el árbol:</span>
                <input
                  type="text"
                  value={condName}
                  onChange={(e) => setCondName(e.target.value)}
                  className="bg-surface-elevated border border-border-subtle rounded px-2 py-1 text-text-primary text-[12px] outline-none focus:border-secondary/60"
                />
                <div>
                  Configuración de condición: <strong className="text-text-primary">{editingCondition.details}</strong>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={onCloseEditCondition}
                className="px-3 py-1 rounded bg-surface-elevated hover:bg-surface-container-high text-text-primary text-[11px]"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  const fx = parseFloat(loadX) || 0;
                  const fy = parseFloat(loadY) || 0;
                  const fz = parseFloat(loadZ) || 0;
                  const mag = Math.sqrt(fx * fx + fy * fy + fz * fz);
                  onSaveCondition({
                    ...editingCondition,
                    // TREE-RENAME: el nombre del arbol se edita aqui.
                    name: condName.trim() || editingCondition.name,
                    // Solo carga toca el vector: antes se sobrescribia
                    // details (caras) tambien en otros tipos al renombrar.
                    ...(editingCondition.type === 'carga'
                      ? {
                          value: [fx, fy, fz] as [number, number, number],
                          magnitude: mag,
                          details: `[${fx}, ${fy}, ${fz}] N`,
                        }
                      : {}),
                  });
                  onCloseEditCondition();
                }}
                className="px-3 py-1 rounded bg-primary-container hover:bg-secondary text-on-primary font-semibold text-[11px]"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
