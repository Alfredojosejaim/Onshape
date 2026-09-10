import React, { useState } from 'react';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportModel: (modelName: string) => void;
}

export const ImportModal: React.FC<ImportModalProps> = ({ isOpen, onClose, onImportModel }) => {
  if (!isOpen) return null;

  const samples = [
    { name: 'Brazo_Soporte_Aero_v2.cad', format: 'CAD B-Rep', size: '4.8 MB', faces: 12 },
    { name: 'Soporte_Pivote_Titanio_Ti6Al4V.step', format: 'STEP AP242', size: '7.2 MB', faces: 28 },
    { name: 'Brazo_Suspension_Formula1.iges', format: 'IGES 5.3', size: '12.4 MB', faces: 45 },
    { name: 'Chasis_Dron_Generativo.step', format: 'STEP AP214', size: '3.1 MB', faces: 16 },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#181b24] border border-[#2e3646] rounded-xl shadow-2xl w-full max-w-md overflow-hidden text-[#e0e2ef]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#2e3646] bg-[#1f2430]">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">upload_file</span>
            <span className="font-semibold text-sm text-[#f1f5f9]">Importar Geometría CAD / CAE</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="material-symbols-outlined text-[#94a3b8] hover:text-[#f1f5f9] text-[18px] cursor-pointer"
          >
            close
          </button>
        </div>

        <div className="p-4 flex flex-col gap-3 text-xs">
          {/* File dropzone */}
          <div
            onClick={() => {
              const name = prompt('Nombre del archivo STEP/CAD a importar:', 'Soporte_Mecanizado_Custom.step');
              if (name) {
                onImportModel(name);
                onClose();
              }
            }}
            className="border-2 border-dashed border-[#2e3646] hover:border-[#0ea5e9] rounded-lg p-6 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors bg-[#0b0e17]/50"
          >
            <span className="material-symbols-outlined text-[32px] text-[#0ea5e9]">cloud_upload</span>
            <span className="font-medium text-[#f1f5f9]">Arrastra o haz clic para subir archivo CAD</span>
            <span className="text-[10px] text-[#64748b]">Soporta .STEP, .STP, .IGES, .IGS, .BREP, .STL, .CAD</span>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex-1 h-px bg-[#2e3646]"></div>
            <span className="text-[10px] text-[#64748b] uppercase font-mono">O selecciona un modelo aeroespacial</span>
            <div className="flex-1 h-px bg-[#2e3646]"></div>
          </div>

          {/* Sample models */}
          <div className="flex flex-col gap-1.5 max-h-44 overflow-y-auto">
            {samples.map((item) => (
              <div
                key={item.name}
                onClick={() => {
                  onImportModel(item.name);
                  onClose();
                }}
                className="p-2 rounded bg-[#1f2430]/60 hover:bg-[#272a33] border border-[#2e3646] flex items-center justify-between cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-[#7bd0ff]">deployed_code</span>
                  <div>
                    <span className="font-medium text-[#f1f5f9] block">{item.name}</span>
                    <span className="text-[10px] font-mono text-[#64748b]">
                      {item.format} • {item.size} • {item.faces} Caras
                    </span>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-[#0ea5e9] font-bold">Cargar</span>
              </div>
            ))}
          </div>
        </div>

        <div className="px-4 py-3 bg-[#1f2430]/60 border-t border-[#2e3646] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-[#272a33] hover:bg-[#32343e] text-xs text-[#e0e2ef] cursor-pointer"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectName: string;
}

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose, projectName }) => {
  const [selectedFormat, setSelectedFormat] = useState('STEP AP242 (.step)');
  const [includePmi, setIncludePmi] = useState(true);
  const [includeFeaReport, setIncludeFeaReport] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  if (!isOpen) return null;

  const handleDownload = () => {
    setIsExporting(true);
    setTimeout(() => {
      // Create synthetic downloadable file
      const content = `TOPOLOGIA OPTIMIZADA - EXPORTACION MODELO\nProyecto: ${projectName}\nFormato: ${selectedFormat}\nFecha: ${new Date().toISOString()}\nReduccion de masa: 65.5%\nFactor de Seguridad: 1.06\nCertificado FEA: Validado`;
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Optimizado_${projectName.replace(/\.[^/.]+$/, '')}_SIMP.step`;
      link.click();
      URL.revokeObjectURL(url);
      setIsExporting(false);
      onClose();
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#181b24] border border-[#2e3646] rounded-xl shadow-2xl w-full max-w-md overflow-hidden text-[#e0e2ef]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#2e3646] bg-[#1f2430]">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">download_for_offline</span>
            <span className="font-semibold text-sm text-[#f1f5f9]">Centro de Exportación CAD / CAE</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="material-symbols-outlined text-[#94a3b8] hover:text-[#f1f5f9] text-[18px] cursor-pointer"
          >
            close
          </button>
        </div>

        <div className="p-4 flex flex-col gap-3 text-xs">
          <div className="flex flex-col gap-1">
            <label className="font-mono text-[10px] text-[#64748b]">Formato de Destino:</label>
            <select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              className="w-full bg-[#1f2430] border border-[#2e3646] rounded p-2 text-xs text-[#f1f5f9] font-medium"
            >
              <option value="STEP AP242 (.step)">STEP AP242 (.step) - Sólido B-Rep con PMI</option>
              <option value="STL Binario (.stl)">STL Binario (.stl) - Alta Resolución para Impresión 3D</option>
              <option value="IGES 5.3 (.iges)">IGES 5.3 (.iges) - Superficies NURBS</option>
              <option value="Nastran Bulk Data (.bdf)">Nastran Bulk Data (.bdf) - Modelo Malla FEA</option>
              <option value="Certificado CAE (.pdf)">Certificado CAE (.pdf) - Reporte de Homologación</option>
            </select>
          </div>

          {/* Options */}
          <div className="bg-[#1f2430]/50 p-2.5 rounded border border-[#2e3646]/50 flex flex-col gap-2 font-mono text-[11px]">
            <label className="flex items-center gap-2 cursor-pointer text-[#f1f5f9]">
              <input
                type="checkbox"
                checked={includePmi}
                onChange={(e) => setIncludePmi(e.target.checked)}
                className="accent-[#0ea5e9]"
              />
              <span>Incrustar metadatos de fabricación (PMI & Tolerancias)</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer text-[#f1f5f9]">
              <input
                type="checkbox"
                checked={includeFeaReport}
                onChange={(e) => setIncludeFeaReport(e.target.checked)}
                className="accent-[#0ea5e9]"
              />
              <span>Generar certificado de tensiones FEA con mapa de calor</span>
            </label>
          </div>

          {/* Verification check */}
          <div className="p-2 rounded bg-[#10b981]/15 border border-[#10b981]/30 text-[#10b981] font-mono text-[10px] flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">check_circle</span>
            <span>Geometría validada: 0 aristas no-manifold • Watertight hermético</span>
          </div>
        </div>

        <div className="px-4 py-3 bg-[#1f2430]/60 border-t border-[#2e3646] flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-[#272a33] hover:bg-[#32343e] text-xs text-[#e0e2ef] cursor-pointer"
          >
            Cerrar
          </button>

          <button
            type="button"
            onClick={handleDownload}
            disabled={isExporting}
            className="px-4 py-1.5 rounded bg-[#0ea5e9] hover:bg-[#7bd0ff] text-[#003751] font-semibold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-md disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[16px]">download</span>
            <span>{isExporting ? 'Empaquetando...' : 'Descargar Archivo'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#181b24] border border-[#2e3646] rounded-xl shadow-2xl w-full max-w-lg overflow-hidden text-[#e0e2ef]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#2e3646] bg-[#1f2430]">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">help_center</span>
            <span className="font-semibold text-sm text-[#f1f5f9]">Manual de Atajos y Flujo de Trabajo CAE</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="material-symbols-outlined text-[#94a3b8] hover:text-[#f1f5f9] text-[18px] cursor-pointer"
          >
            close
          </button>
        </div>

        <div className="p-4 flex flex-col gap-4 text-xs max-h-[70vh] overflow-y-auto">
          <div>
            <h4 className="font-bold text-[#f1f5f9] mb-1.5 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-[#0ea5e9]">mouse</span>
              Controles de Ratón y Navegación 3D
            </h4>
            <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
              <div className="p-1.5 rounded bg-[#1f2430]/60 border border-[#2e3646]">
                <span className="text-[#7bd0ff] block font-bold">LMB (Arrastrar):</span>
                <span className="text-[#94a3b8]">Rotación de órbita 3D</span>
              </div>
              <div className="p-1.5 rounded bg-[#1f2430]/60 border border-[#2e3646]">
                <span className="text-[#7bd0ff] block font-bold">Shift + LMB / MMB:</span>
                <span className="text-[#94a3b8]">Desplazamiento horizontal/vertical (Pan)</span>
              </div>
              <div className="p-1.5 rounded bg-[#1f2430]/60 border border-[#2e3646]">
                <span className="text-[#7bd0ff] block font-bold">Rueda de Ratón:</span>
                <span className="text-[#94a3b8]">Zoom continuo (+ / -)</span>
              </div>
              <div className="p-1.5 rounded bg-[#1f2430]/60 border border-[#2e3646]">
                <span className="text-[#7bd0ff] block font-bold">Clic en ViewCube:</span>
                <span className="text-[#94a3b8]">Vistas ortogonales TOP, FRONT, ISO</span>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-bold text-[#f1f5f9] mb-1.5 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-[#10b981]">alt_route</span>
              Flujo de Trabajo de Optimización Topológica (5 Etapas)
            </h4>
            <ol className="list-decimal pl-4 flex flex-col gap-1 text-[#94a3b8] leading-relaxed">
              <li>
                <strong className="text-[#f1f5f9]">Modelo CAD & Pre-proceso:</strong> Define el espacio de diseño, fija los bujes y aplica las cargas de tracción.
              </li>
              <li>
                <strong className="text-[#f1f5f9]">Mallado & Condiciones:</strong> Discretiza la geometría con elementos tetraédricos Tet4/Tet10 y verifica la calidad jacobiana.
              </li>
              <li>
                <strong className="text-[#f1f5f9]">Solver FEA & Tensiones:</strong> Resuelve el campo de tensiones elásticas de Von Mises y calcula el factor de seguridad.
              </li>
              <li>
                <strong className="text-[#f1f5f9]">Optimización Topológica (SIMP):</strong> Ejecuta el algoritmo SIMP para remover material pasivo con un objetivo de reducción del 65%.
              </li>
              <li>
                <strong className="text-[#f1f5f9]">Generativo & B-Rep Export:</strong> Reconstruye superficies NURBS suaves y exporta directamente a STEP o STL para fabricación aditiva.
              </li>
            </ol>
          </div>
        </div>

        <div className="px-4 py-3 bg-[#1f2430]/60 border-t border-[#2e3646] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-[#0ea5e9] text-[#003751] font-semibold text-xs cursor-pointer"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#181b24] border border-[#2e3646] rounded-xl shadow-2xl w-full max-w-md overflow-hidden text-[#e0e2ef]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#2e3646] bg-[#1f2430]">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#7bd0ff] text-[18px]">settings</span>
            <span className="font-semibold text-sm text-[#f1f5f9]">Configuración General del Sistema</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="material-symbols-outlined text-[#94a3b8] hover:text-[#f1f5f9] text-[18px] cursor-pointer"
          >
            close
          </button>
        </div>

        <div className="p-4 flex flex-col gap-3 text-xs">
          <div className="flex justify-between items-center py-1 border-b border-[#2e3646]/40">
            <div>
              <span className="text-[#f1f5f9] font-medium block">Sistema de Unidades:</span>
              <span className="text-[10px] text-[#64748b]">Fuerza en N, Longitud en mm, Masa en kg</span>
            </div>
            <span className="font-mono text-[#7bd0ff]">SI Técnico [mm-N-s]</span>
          </div>

          <div className="flex justify-between items-center py-1 border-b border-[#2e3646]/40">
            <div>
              <span className="text-[#f1f5f9] font-medium block">Aceleración por GPU (VTK WebGL):</span>
              <span className="text-[10px] text-[#64748b]">Shader pipeline OpenGL 2.0</span>
            </div>
            <span className="text-[#10b981] font-mono font-bold">Activo (60 FPS)</span>
          </div>

          <div className="flex justify-between items-center py-1 border-b border-[#2e3646]/40">
            <div>
              <span className="text-[#f1f5f9] font-medium block">Tolerancia Residual Solver:</span>
              <span className="text-[10px] text-[#64748b]">Convergencia matricial</span>
            </div>
            <span className="font-mono text-[#f1f5f9]">1.0e-7</span>
          </div>

          <div className="flex justify-between items-center py-1">
            <div>
              <span className="text-[#f1f5f9] font-medium block">Paleta de Tensión FEA:</span>
              <span className="text-[10px] text-[#64748b]">Gradiente térmico</span>
            </div>
            <div className="w-20 h-4 rounded bg-gradient-to-r from-blue-600 via-green-500 via-yellow-500 to-red-600 border border-[#2e3646]" />
          </div>
        </div>

        <div className="px-4 py-3 bg-[#1f2430]/60 border-t border-[#2e3646] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-[#0ea5e9] text-[#003751] font-semibold text-xs cursor-pointer"
          >
            Guardar y Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
