import { expect } from '@playwright/test'

import { test } from '../../fixtures/auth'
import { createOrder } from '../../api/orders'

// 旅程 2：shopper 下單 → 訂單列表看得到。
// 身份：freshShopperPage（fixtures/auth 的每測全新 shopper——會造訂單的測試
// 不用共用 storageState，避免歷史累積影響斷言）。
// 造資料走 api/orders.ts 的 wrapper——查商品、驗 200 的契約知識集中一處。
test.describe('Shopper orders journey', () => {
  test('shopper sees their order in the orders list', async ({
    freshShopperPage: page
  }) => {
    // ── ① 造資料：page.request 自動帶 shopper cookie（身份 = page 身份，一致）──
    const order = await createOrder(page.request)

    // ── ② 動作 ──
    await page.goto('/app/orders')

    // ── ③ 驗證：自己造的那筆出現在列表 ──
    const row = page.locator('tr', { has: page.getByText(`#${order.id}`) })
    await expect(row).toBeVisible()
    await expect(row.getByText(/unpaid/i)).toBeVisible()
  })
})
