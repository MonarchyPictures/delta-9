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
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 300000, // 5 minutes
        proxyTimeout: 300000,
      },
      '/leads': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/notifications': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/agents': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/success': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/search': { target: 'http://127.0.0.1:8000', timeout: 300000, proxyTimeout: 300000 },
      '/scrapers': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/pipeline': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/outreach': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/settings': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/health': { target: 'http://127.0.0.1:8000', timeout: 300000 },
      '/ready': { target: 'http://127.0.0.1:8000', timeout: 300000 }
    }
  },
  preview: {
    port: 4173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/leads': 'http://127.0.0.1:8000',
      '/notifications': 'http://127.0.0.1:8000',
      '/agents': 'http://127.0.0.1:8000',
      '/success': 'http://127.0.0.1:8000',
      '/search': 'http://127.0.0.1:8000',
      '/scrapers': 'http://127.0.0.1:8000',
      '/pipeline': 'http://127.0.0.1:8000',
      '/outreach': 'http://127.0.0.1:8000',
      '/settings': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/ready': 'http://127.0.0.1:8000'
    }
  }
})