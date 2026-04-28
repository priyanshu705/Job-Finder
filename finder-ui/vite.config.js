import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  // ── Dev server ────────────────────────────────────────────────────────────
  server: {
    port: 3000,
    proxy: {
      // Local dev: proxy /api → Flask running on :5000
      // Production: VITE_API_BASE_URL points directly to Render backend
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },

  // ── Production build ─────────────────────────────────────────────────────
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Generate source maps for production debugging (Vercel strips them from
    // the public bundle — they stay in Vercel's internal storage)
    sourcemap: true,
    rollupOptions: {
      output: {
        // Split large vendor chunks so first load is faster
        manualChunks: {
          react:    ['react', 'react-dom'],
          recharts: ['recharts'],
          lucide:   ['lucide-react'],
        },
      },
    },
  },
})
