/**
 * Vite 构建配置。
 *
 * DEC-015: 开发环境通过 Vite Proxy 代理 /api 到后端，规避 CORS。
 * 后端地址: http://127.0.0.1:8000（见 backend/.env.example）。
 */
import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    // DEC-015: 代理 /api 到后端，开发环境无 CORS 问题
    // SSE 流式响应需要特殊配置，避免代理缓冲导致 net::ERR_ABORTED
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // SSE: 不自动处理响应，让流式数据直接透传
        selfHandleResponse: false,
        // 代理错误日志，便于排查
        configure: (proxy) => {
          proxy.on('error', (err, req, res) => {
            console.error('[vite-proxy] error:', err.message, req?.url);
          });
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // 第三方依赖单独打包，优化缓存
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          'element-plus': ['element-plus', '@element-plus/icons-vue'],
          markdown: ['marked', 'dompurify', 'highlight.js'],
        },
      },
    },
  },
});
