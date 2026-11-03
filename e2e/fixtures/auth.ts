// Role fixtures：身份的「水電」——點名就有，用完自動收。
// shopperApi = 每條測試全新的 shopper 身份（API client），
// 取代「共用 shopper.json」或「測試裡手寫註冊登入樣板」。
// freshShopperPage = 每條測試全新的 shopper 身份（瀏覽器分頁）——
// 並行測試不再共用購物車/通知歷史（共用身份的寫入污染在 CI 並行下實錄）。
import {
  request,
  test as base,
  type APIRequestContext,
  type Page
} from '@playwright/test'

import { PASSWORD, uniqueEmail } from '../tests/helpers'

export const test = base.extend<{
  shopperApi: APIRequestContext
  freshShopperPage: Page
}>({
  shopperApi: async ({ baseURL }, use) => {
    // ⚠️ 這裡的 request 是「工廠」（APIRequest），不是測試簽名裡的 fixture（成品）。
    // 工廠造的 client 不繼承 config 的 baseURL，所以自己接（fixture 有帶）。
    const client = await request.newContext({
      baseURL: baseURL ?? 'http://localhost:5173'
    })

    // 開戶 + 登入：Set-Cookie 自動進這個 client 的 jar，之後的請求都是登入態
    const email = uniqueEmail('shopper')
    await client.post('/api/users', {
      data: { name: 'E2E Shopper', email, password: PASSWORD }
    })
    await client.post('/api/login', { data: { email, password: PASSWORD } })

    await use(client)

    await client.dispose() // 手動造的要手動收
  },

  freshShopperPage: async ({ browser, baseURL }, use) => {
    // 開全新 context（乾淨 cookie jar）→ API 開戶 + 登入 → cookie 進 jar
    // → 這個 context 的分頁天生是「全新 shopper」的登入態
    const ctx = await browser.newContext({
      baseURL: baseURL ?? 'http://localhost:5173'
    })

    const email = uniqueEmail('fresh-shopper')
    await ctx.request.post('/api/users', {
      data: { name: 'Fresh Shopper', email, password: PASSWORD }
    })
    await ctx.request.post('/api/login', {
      data: { email, password: PASSWORD }
    })

    await use(await ctx.newPage())

    await ctx.close() // 身份用完即丟——購物車/通知天然 per-test
  }
})
