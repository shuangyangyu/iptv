import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // 监听所有网络接口
    port: 5173, // 改为 Chrome 允许的安全端口（6000 被 Chrome 视为不安全端口）
    strictPort: false, // 如果端口被占用，尝试其他端口
    proxy: {
      '/api': {
        target: 'http://192.168.1.241:8088',
        changeOrigin: true,
      },
      '/out': {
        target: 'http://192.168.1.241:8088',
        changeOrigin: true,
      },
      '/catchup': {
        target: 'http://192.168.1.241:8088',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})

