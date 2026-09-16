import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    build: {
      // CHUNK-SPLIT (reversible): three.js (~600KB) y el resto de vendors
      // van a chunks separados en vez de un unico bundle de 843KB.
      // Para volver atras: borrar este bloque build completo.
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-three': ['three'],
            'vendor-react': ['react', 'react-dom'],
          },
        },
      },
    },
  };
});
