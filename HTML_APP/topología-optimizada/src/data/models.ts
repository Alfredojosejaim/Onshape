import { CadModelPreset, BoundaryCondition } from '../types';

// UI-CLEAN-START (reversible): estado inicial vacio, sin modelos de
// referencia. Los mocks viven en ./models.mock.ts (no importado).
// Para volver atras: `import { MOCK_CAD_PRESETS as CAD_PRESETS, ... }`
// o copiar los arrays desde models.mock.ts.
export const CAD_PRESETS: CadModelPreset[] = [];

export const INITIAL_CONDITIONS: BoundaryCondition[] = [];
// UI-CLEAN-END
