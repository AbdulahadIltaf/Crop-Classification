import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // In dev, proxy all /predict requests to the FastAPI backend
    // so we can use relative URLs (/predict/...) in the frontend code
    proxy: {
      '/predict': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
