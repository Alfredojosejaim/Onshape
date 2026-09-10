import React from 'react';
import { ActiveTab } from '../types';

interface SecondaryNavProps {
  activeTab: ActiveTab;
  onChangeTab: (tab: ActiveTab) => void;
}

export const SecondaryNav: React.FC<SecondaryNavProps> = ({ activeTab, onChangeTab }) => {
  return (
    <nav className="h-8 px-space-md flex items-center gap-space-xs bg-surface-container-lowest border-b border-border-subtle/40 select-none">
      <button
        id="tab-optimizacion"
        type="button"
        onClick={() => onChangeTab('optimizacion')}
        className={`h-full flex items-center px-space-md border-b-2 text-body-sm font-medium transition-colors ${
          activeTab === 'optimizacion'
            ? 'border-primary-container text-secondary font-semibold bg-surface-panel/40'
            : 'border-transparent text-text-secondary hover:text-on-surface'
        }`}
      >
        <span className="material-symbols-outlined text-[15px] mr-1.5 opacity-80">
          shape_line
        </span>
        Optimizacion
      </button>

      <button
        id="tab-analizis"
        type="button"
        onClick={() => onChangeTab('analizis')}
        className={`h-full flex items-center px-space-md border-b-2 text-body-sm font-medium transition-colors ${
          activeTab === 'analizis'
            ? 'border-primary-container text-secondary font-semibold bg-surface-panel/40'
            : 'border-transparent text-text-secondary hover:text-on-surface'
        }`}
      >
        <span className="material-symbols-outlined text-[15px] mr-1.5 opacity-80">
          analytics
        </span>
        Analizis
      </button>
    </nav>
  );
};
