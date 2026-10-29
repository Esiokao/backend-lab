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
  },
  projects: [
    // ① setup project：最先跑 — 種商品 + 產生兩份 storageState（testMatch 鎖定自己）
    { name: 'setup', testMatch: /auth\.setup\.ts/ },

    // ② 三個身份：dependencies 確保 setup 先完成；
    //    testIgnore 防止身份 project 重跑 setup 檔；
    //    storageState = 開新瀏覽器時預先貼上的 cookie（三部手機的概念）
    {
      name: 'guest',
      testIgnore: [/auth\.setup\.ts/, /admin\.spec\.ts/],
      use: { storageState: { cookies: [], origins: [] } },
      dependencies: ['setup']
    },
    {
      name: 'shopper',
      // guest 旅程（UI 登入/註冊）不適用已登入身份：/login 是 guestOnly 會被彈走
      testIgnore: [
        /auth\.setup\.ts/,
        /auth\.spec\.ts/,
        /store\.spec\.ts/,
        /admin\.spec\.ts/
      ],
      use: { storageState: '.auth/shopper.json' },
      dependencies: ['setup']
    },
    {
      name: 'admin',
      testIgnore: [/auth\.setup\.ts/, /auth\.spec\.ts/, /store\.spec\.ts/],
      use: { storageState: '.auth/admin.json' },
      dependencies: ['setup']
    }
  ]
})
