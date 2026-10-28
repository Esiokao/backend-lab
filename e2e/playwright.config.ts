import { defineConfig } from '@playwright/test'

// e2e 針對「已經跑著的開發 stack」：postgres/redis（compose）+ uvicorn:8000 + vite:5173。
// 沒有 webServer 自動啟動——先確認 stack 活著再跑，避免測試等一個起不來的服務。
// CI 接入時：job 先 docker compose up + uvicorn + vite，再 npx playwright test。
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    // staging 用自簽憑證時也跑得動
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure'
  }
})
