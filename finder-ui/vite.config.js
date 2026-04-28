import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  // Dev server
  server: {
    port: 3000,
    proxy: {
      // Local dev: proxy /api to Flask on :5000.
      // Production uses VITE_API_URL directly in src/api.js.
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },

  // Production build
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        // Split large vendor chunks so first load is faster
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('react')) return 'react'
          if (id.includes('recharts')) return 'recharts'
          if (id.includes('lucide-react')) return 'lucide'
          return 'vendor'
        },
      },
    },
  },
})
