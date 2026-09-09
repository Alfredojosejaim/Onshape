import React from 'react';
import { ScreenId } from '../types';

interface SidebarProps {
  currentScreen: ScreenId;
  onSelectScreen: (screen: ScreenId) => void;
  snapshot?: Record<string, unknown> | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentScreen, onSelectScreen, snapshot }) => {
  const navItems: {
    path: ScreenId;
    title: string;
    badge: string;
    badgeColor?: string;
  }[] = [
    {
      path: 'modelo-cad-y-pre-proceso',
      title: 'Geometría Base (STEP)',
      badge: 'Sólido',
      badgeColor: 'text-[#64748b]',
    },
    {
      path: 'mallado-y-condiciones',
      title: 'Malla Tetraédrica',
      badge: 'Gmsh v4',
      badgeColor: 'text-[#10b981]',
    },
    {
      path: 'solver-fea-y-tensiones',
      title: 'Condiciones de Borde & FEA',
      badge: '3 Cargas',
      badgeColor: 'text-[#64748b]',
    },
    {
      path: 'optimizacion-topologica-simp',
      title: 'Filtro de Densidad & SIMP',
      badge: 'p=3.0',
      badgeColor: 'text-[#ffb95f]',
    },
    {
      path: 'generativo-y-b-rep-export',
      title: 'NURBS & B-Rep Isosuperficie',
      badge: 'STEP',
      badgeColor: 'text-[#64748b]',
    },
  ];

  return (
    <aside className="fixed left-0 top-20 bottom-7 w-64 bg-[#181b24] border-r border-[#2e3646] z-30 flex flex-col justify-between overflow-y-auto">
      <div className="p-2 flex flex-col gap-2">
        <div className="flex items-center justify-between px-1 py-1 border-b border-[#2e3646]">
          <span className="font-label-sm text-[10px] uppercase tracking-wider text-[#64748b]">
            Árbol de Operaciones
          </span>
          <span className="material-symbols-outlined text-[#64748b] text-[16px]">
            account_tree
          </span>
        </div>

        <nav className="flex flex-col gap-0.5">
          {navItems.map((item) => {
            const isActive = currentScreen === item.path;
            return (
              <button
                key={item.path}
                onClick={() => onSelectScreen(item.path)}
                className={`flex items-center justify-between px-2.5 py-1.5 rounded-r text-left font-body-sm text-[11px] transition-all ${
                  isActive
                    ? 'bg-[#1f2430] text-[#7bd0ff] font-medium border-l-2 border-[#0ea5e9]'
                    : 'text-[#94a3b8] hover:bg-[#272a33] hover:text-[#e0e2ef]'
                }`}
              >
                <span className="truncate pr-2">{item.title}</span>
                <span className={`font-label-sm text-[10px] shrink-0 ${item.badgeColor || 'text-[#64748b]'}`}>
                  {item.badge}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="p-2.5 border-t border-[#2e3646] bg-[#0b0e17]">
        <div className="text-[#64748b] font-label-sm text-[10px] flex items-center justify-between">
          <span>Precisión Solver:</span>
          <span className="text-[#f1f5f9] font-label-sm text-[10px]">Float64 / CG</span>
        </div>
        <div className="text-[#64748b] font-label-sm text-[10px] flex items-center justify-between mt-1">
          <span>Convergencia:</span>
          <span className="text-[#10b981] font-label-sm text-[10px]">1e-6 Tol</span>
        </div>
        {snapshot && typeof snapshot.model_name === 'string' && (
          <div className="text-[#64748b] font-label-sm text-[10px] flex items-center justify-between mt-1">
            <span>Modelo:</span>
            <span className="text-[#7bd0ff] font-label-sm text-[10px] truncate max-w-[120px]">{snapshot.model_name as string}</span>
          </div>
        )}
      </div>
    </aside>
  );
};
