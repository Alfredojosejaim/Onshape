// ADV-OPT (reversible): panel colapsable de motores y restricciones avanzadas
// del core (MMA/GCMMA/ESO/Level-Set, simetría, espesor mínimo, overhang,
// objetivo, térmico). Antes solo accesible vía Qt desktop; el backend
// (api.runOptimization) ya valida todo y rechaza explícito — el aviso de
// error del backend llega por onDone/error existente, nunca silencioso.
// Para revertir: borrar este archivo + bloque ADV-OPT en types.ts +
// render en RightPanel.tsx + spread en App.tsx.
import React, { useState } from 'react';
import { SimpParameters } from '../types';

interface Props {
  simpParams: SimpParameters;
  onChangeSimpParams: (params: SimpParameters) => void;
  disabled: boolean;
}

const numCls =
  'w-20 bg-surface-container-lowest border border-border-subtle/40 rounded px-1 py-0.5 text-text-primary text-right';
const selCls =
  'bg-surface-container-lowest border border-border-subtle/40 rounded px-1 py-0.5 text-text-primary';

function Row({ label, title, children }: { label: string; title?: string; children: React.ReactNode }) {
  return (
    <label className="flex items-center justify-between pl-2 gap-2" title={title}>
      <span className="text-text-secondary">{label}</span>
      <span className="flex items-center gap-1">{children}</span>
    </label>
  );
}

export const AdvancedOptPanel: React.FC<Props> = ({ simpParams: sp, onChangeSimpParams: set, disabled }) => {
  const [open, setOpen] = useState(false);
  const setNum = (key: 'evolutionaryRate' | 'lsCfl' | 'overhangAngleDeg' | 'overhangPenalty' | 'thermalAlpha' | 'thermalRefTemp' | 'minThickness',
    v: string, fallback: number) => {
    const n = parseFloat(v);
    set({ ...sp, [key]: Number.isFinite(n) ? n : fallback });
  };
  return (
    <div className="flex flex-col gap-1 bg-surface-elevated/20 p-2 rounded border border-border-subtle/30 font-mono text-[10px]">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-text-muted font-medium flex items-center gap-1 text-left"
        title="Motores y restricciones avanzadas del core (solo rama estructural)"
      >
        <span className="material-symbols-outlined text-[12px] text-secondary">
          {open ? 'expand_less' : 'expand_more'}
        </span>
        Avanzado (motor, simetría, overhang, térmico)
        <span className="opacity-60">(reversible)</span>
      </button>
      {!open ? null : (
        <>
          <Row label="Optimizador" title="oc = SIMP clásico; mma/gcmma = convexos; eso = evolutivo; level_set = curvas de nivel">
            <select
              value={sp.optimizer}
              disabled={disabled}
              onChange={(e) => set({ ...sp, optimizer: e.target.value as SimpParameters['optimizer'] })}
              className={selCls}
            >
              <option value="oc">OC (SIMP)</option>
              <option value="mma">MMA</option>
              <option value="gcmma">GCMMA</option>
              <option value="eso">ESO</option>
              <option value="level_set">Level-Set</option>
            </select>
          </Row>
          {sp.optimizer !== 'eso' ? null : (
            <>
              <Row label="Criterio ESO" title="compliance = rigidez; stress = von Mises por elemento">
                <select
                  value={sp.esoCriterion}
                  disabled={disabled}
                  onChange={(e) => set({ ...sp, esoCriterion: e.target.value as SimpParameters['esoCriterion'] })}
                  className={selCls}
                >
                  <option value="compliance">Compliance</option>
                  <option value="stress">Stress</option>
                </select>
              </Row>
              <Row label="Tasa evolutiva" title="Fracción a remover por iteración (0, 1)">
                <input
                  type="number" min={0.001} max={0.5} step={0.005}
                  value={sp.evolutionaryRate}
                  disabled={disabled}
                  onChange={(e) => setNum('evolutionaryRate', e.target.value, 0.02)}
                  className={numCls}
                />
              </Row>
            </>
          )}
          {sp.optimizer !== 'level_set' ? null : (
            <>
              <Row label="CFL" title="Número CFL del Hamilton-Jacobi (0, 1]">
                <input
                  type="number" min={0.05} max={1} step={0.05}
                  value={sp.lsCfl}
                  disabled={disabled}
                  onChange={(e) => setNum('lsCfl', e.target.value, 0.5)}
                  className={numCls}
                />
              </Row>
              <Row label="Nucleación c/N" title="Agujeros nuevos cada N iteraciones (>= 1)">
                <input
                  type="number" min={1} max={50} step={1}
                  value={sp.lsHolePeriod}
                  disabled={disabled}
                  onChange={(e) => set({ ...sp, lsHolePeriod: Math.max(1, parseInt(e.target.value, 10) || 3) })}
                  className={numCls}
                />
              </Row>
            </>
          )}
          <div className="text-text-muted font-medium pt-1">Simetría (planos, mm)</div>
          {(['X', 'Y', 'Z'] as const).map((ax) => {
            const on = sp[`sym${ax}` as 'symX' | 'symY' | 'symZ'];
            const val = sp[`sym${ax}Val` as 'symXVal' | 'symYVal' | 'symZVal'];
            const key = `sym${ax}Val` as 'symXVal' | 'symYVal' | 'symZVal';
            const onKey = `sym${ax}` as 'symX' | 'symY' | 'symZ';
            return (
              <Row key={ax} label={`Plano ${ax}`} title="Refleja densidades respecto al plano (valor = coordenada)">
                <input
                  type="checkbox"
                  checked={on}
                  disabled={disabled}
                  onChange={(e) => set({ ...sp, [onKey]: e.target.checked })}
                  className="accent-secondary"
                />
                <input
                  type="number" step={0.5}
                  value={val}
                  disabled={disabled || !on}
                  onChange={(e) => set({ ...sp, [key]: parseFloat(e.target.value) || 0 })}
                  className={numCls}
                />
              </Row>
            );
          })}
          <Row label="Espesor mín. (mm)" title="0 = desactivado; > 0 exige miembros de al menos ese grosor">
            <input
              type="number" min={0} step={0.1}
              value={sp.minThickness}
              disabled={disabled}
              onChange={(e) => setNum('minThickness', e.target.value, 0)}
              className={numCls}
            />
          </Row>
          <div className="text-text-muted font-medium pt-1">Overhang (impresión 3D)</div>
          <Row label="Restringir voladizo" title="Penaliza superficies que violan el ángulo respecto a la dirección de construcción">
            <input
              type="checkbox"
              checked={sp.overhangEnabled}
              disabled={disabled}
              onChange={(e) => set({ ...sp, overhangEnabled: e.target.checked })}
              className="accent-secondary"
            />
          </Row>
          <Row label="Dir. construcción" title="Vector de apilado de capas">
            {([0, 1, 2] as const).map((i) => (
              <input
                key={i}
                type="number" step={0.5}
                value={sp.overhangBuildDir[i]}
                disabled={disabled || !sp.overhangEnabled}
                onChange={(e) => {
                  const d: [number, number, number] = [...sp.overhangBuildDir];
                  d[i] = parseFloat(e.target.value) || 0;
                  set({ ...sp, overhangBuildDir: d });
                }}
                className="w-14 bg-surface-container-lowest border border-border-subtle/40 rounded px-1 py-0.5 text-text-primary text-right"
              />
            ))}
          </Row>
          <Row label="Ángulo (grados)" title="Ángulo mínimo autoportante (def. 45)">
            <input
              type="number" min={0} max={90} step={1}
              value={sp.overhangAngleDeg}
              disabled={disabled || !sp.overhangEnabled}
              onChange={(e) => setNum('overhangAngleDeg', e.target.value, 45)}
              className={numCls}
            />
          </Row>
          <Row label="Penalización" title="Peso del término de overhang">
            <input
              type="number" min={0} step={0.1}
              value={sp.overhangPenalty}
              disabled={disabled || !sp.overhangEnabled}
              onChange={(e) => setNum('overhangPenalty', e.target.value, 0.5)}
              className={numCls}
            />
          </Row>
          <div className="text-text-muted font-medium pt-1">Objetivo</div>
          <Row label="Objetivo" title="min_volume usa complianceLimit como restricción">
            <select
              value={sp.objective}
              disabled={disabled}
              onChange={(e) => set({ ...sp, objective: e.target.value as SimpParameters['objective'] })}
              className={selCls}
            >
              <option value="min_compliance">Mín. compliance</option>
              <option value="min_volume">Mín. volumen</option>
            </select>
          </Row>
          {sp.objective !== 'min_volume' ? null : (
            <Row label="Límite compliance" title="Restricción superior (vacío = sin límite)">
              <input
                type="number" min={0} step={1}
                value={sp.complianceLimit ?? ''}
                disabled={disabled}
                onChange={(e) => {
                  const n = parseFloat(e.target.value);
                  set({ ...sp, complianceLimit: Number.isFinite(n) && n > 0 ? n : null });
                }}
                className={numCls}
              />
            </Row>
          )}
          <div className="text-text-muted font-medium pt-1">Térmico (acoplado)</div>
          <Row label="Acoplar térmico" title="Agrega cargas térmicas (CTE × ΔT) al problema">
            <input
              type="checkbox"
              checked={sp.thermalEnabled}
              disabled={disabled}
              onChange={(e) => set({ ...sp, thermalEnabled: e.target.checked })}
              className="accent-secondary"
            />
          </Row>
          <Row label="CTE α (1/K)" title="Coeficiente de expansión térmica">
            <input
              type="number" step={0.000001}
              value={sp.thermalAlpha}
              disabled={disabled || !sp.thermalEnabled}
              onChange={(e) => setNum('thermalAlpha', e.target.value, 0.00001)}
              className={numCls}
            />
          </Row>
          <Row label="Temp. ref (K)" title="Temperatura de referencia (deformación cero)">
            <input
              type="number" step={1}
              value={sp.thermalRefTemp}
              disabled={disabled || !sp.thermalEnabled}
              onChange={(e) => setNum('thermalRefTemp', e.target.value, 293)}
              className={numCls}
            />
          </Row>
          <Row label="Temp. (K, csv)" title="Temperaturas aplicadas, separadas por comas">
            <input
              type="text"
              value={sp.thermalTemperatures}
              disabled={disabled || !sp.thermalEnabled}
              onChange={(e) => set({ ...sp, thermalTemperatures: e.target.value })}
              className="w-28 bg-surface-container-lowest border border-border-subtle/40 rounded px-1 py-0.5 text-text-primary text-right"
            />
          </Row>
        </>
      )}
    </div>
  );
};
