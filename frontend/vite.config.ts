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
    // 進場綁定：Windows 本機開發預設 localhost；Compose 容器設 VITE_DEV_host=0.0.0.0，
    // 讓 docker port 轉得進來。CLI 傳 --host 經 pnpm run 前後 "--" 處理很容易掉，不值得賭。
    host: process.env.VITE_DEV_HOST,
    // Bind mount 環境（Docker Desktop / WSL）inotify 不傳主機事件，無 polling 則
    // HMR 收不到主機側檔案變更、transform cache 停留舊版。repo 小，polling 成本可忽略。
    watch: { usePolling: true, ignored: ["**/.pnpm-store/**"] },
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
