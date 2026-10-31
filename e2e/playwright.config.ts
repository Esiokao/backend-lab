import { defineConfig } from '@playwright/test'

// e2e 針對「已經跑著的開發 stack」：postgres/redis（compose）+ uvicorn:8000 + vite:5173。
// 沒有 webServer 自動啟動——先確認 stack 活著再跑，避免測試等一個起不來的服務。
// CI 接入時：job 先 docker compose up + uvicorn + vite，再 pnpm exec playwright test。
//
// 「測試用什麼身份」由目錄決定（testMatch 白名單，維護成本 O(1)）：
//   tests/setup/   → 種資料 + 產生 storageState（每個身份 project 都先依賴它）
//   tests/guest/   → 未登入旅程
//   tests/shopper/ → shopper 身份（storageState 自動掛載）
//   tests/admin/   → admin 身份
//   tests/all/     → 三個身份都要跑的通用測試（smoke、404）
// 新增 spec 時放對資料夾即可，config 不用再改。
// ⚠️ 白名單的失敗模式是「安靜」：放錯/漏放 = 測試默默不執行——
//    新增旅程時確認該 project 的測試數有增加。
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
    // ① setup project：最先跑，身份 project 都 dependencies 它
    { name: 'setup', testMatch: /[\/]setup[\/]/ },

    // ② 三個身份 + 共通的 all/
    {
      name: 'guest',
      testMatch: [/[\/]guest[\/]/, /[\/]all[\/]/],
      use: { storageState: { cookies: [], origins: [] } },
      dependencies: ['setup']
    },
    {
      name: 'shopper',
      testMatch: [/[\/]shopper[\/]/, /[\/]all[\/]/],
      use: { storageState: '.auth/shopper.json' },
      dependencies: ['setup']
    },
    {
      name: 'admin',
      testMatch: [/[\/]admin[\/]/, /[\/]all[\/]/],
      use: { storageState: '.auth/admin.json' },
      dependencies: ['setup']
    }
  ]
})
