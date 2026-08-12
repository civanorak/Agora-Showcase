import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/ingest': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
      '/events': { target: 'http://localhost:8000', changeOrigin: true },
      '/stats': { target: 'http://localhost:8000', changeOrigin: true },
      '/report': { target: 'http://localhost:8000', changeOrigin: true },
      '/sites': { target: 'http://localhost:8000', changeOrigin: true },
      '/llms.txt': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
