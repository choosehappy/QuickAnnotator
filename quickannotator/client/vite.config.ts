import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { SERVER_URL } from './src/helpers/config' // Import SERVER_URL

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: SERVER_URL, // Use SERVER_URL from config.ts
        changeOrigin: true,
      }
    }
  },
  cacheDir: '/opt/node_modules/.vite',
})

