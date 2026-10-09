import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// /api 的请求会被转发到 FastAPI（8000），前端因此不用操心跨域（CORS）。
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
