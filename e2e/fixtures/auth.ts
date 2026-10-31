// Role fixtures：身份的「水電」——點名就有，用完自動收。
// shopperApi = 每條測試全新的 shopper 身份（API client），
// 取代「共用 shopper.json」或「測試裡手寫註冊登入樣板」。
import { request, test as base, type APIRequestContext } from '@playwright/test'

import { PASSWORD, uniqueEmail } from '../tests/helpers'

export const test = base.extend<{ shopperApi: APIRequestContext }>({
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
  }
})
