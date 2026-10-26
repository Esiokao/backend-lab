import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

// 開發期把 /api 代理到 FastAPI（同源，cookie 自動帶，零 CORS）。
// 主機上跑預設 localhost:8000；Compose 容器內用 VITE_API_PROXY_TARGET 指 api:8000。
// 正式環境由 nginx 同源服務靜態檔 + /api 轉發。
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
