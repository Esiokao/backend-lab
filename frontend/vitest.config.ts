import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";

// 單元測試（純邏輯，無瀏覽器）：stores / lib。
// E2E 另議（PRD §6）。別名與 vite.config 對齊。
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    include: ["src/**/__tests__/*.test.ts"],
    environment: "node",
  },
});
