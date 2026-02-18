import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        timeout: 120000, // Increased to 120 seconds for deep discovery
        proxyTimeout: 120000,
      }
    }
  },
  preview: {
    port: 4173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/leads': 'http://127.0.0.1:8001',
      '/notifications': 'http://127.0.0.1:8001',
      '/agents': 'http://127.0.0.1:8001',
      '/success': 'http://127.0.0.1:8001'
    }
  }
})