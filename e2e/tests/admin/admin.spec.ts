// 旅程 4：shopper 下單（API）→ admin 在後台看到 → 推進狀態機。
// 身份：page = admin（project 的 storageState）；shopperApi = 全新 shopper（fixtures/auth.ts）。
// 造資料：api/orders.ts 的 createOrder（契約知識集中一處）。
import { expect, type Page } from '@playwright/test'

import { createOrder } from '../../api/orders'
import { test } from '../../fixtures/auth'

const ADMIN_ORDERS_URL = '/admin/orders'

/** 填入「Filter by user ID」並觸發列表刷新。⚠️ 綁定 AdminOrdersView 的 DOM，換頁面不能搬。 */
async function filterByUserId(page: Page, userId: number): Promise<void> {
  // input 有 @change="applyFilters"：文字框的 change 在 blur 時才發，fill 後要 blur。
  await page.getByLabel('Filter by user ID').fill(String(userId))
  await page.getByLabel('Filter by user ID').blur()
}

test.describe('Admin orders journey', () => {
  // page = admin project 的分頁；shopperApi = fixtures 給的全新 shopper client。
  // 不需要 browser——身份不再靠開瀏覽器造。
  test('admin sees a fresh shopper order and advances unpaid to paid', async ({
    page,
    shopperApi
  }) => {
    // ① shopper 身份（fixture 封裝）+ 造資料（API wrapper）——測試只說「我要一筆訂單」
    const order = await createOrder(shopperApi)

    // ② admin 開後台，用 user ID 篩出這筆（列表 id 正序，不篩會翻不到頁）
    await page.goto(ADMIN_ORDERS_URL)
    await filterByUserId(page, order.user_id)

    const row = page.locator('tr', { has: page.getByText(`#${order.id}`) })
    await expect(row).toBeVisible()
    await expect(row.locator('.status-badge')).toHaveText('unpaid')

    // ③ 推進狀態機：unpaid → paid（ALLOWED_TRANSITIONS 的合法第一步）
    const select = page.getByLabel(`Change status for order ${order.id}`)
    await select.selectOption('paid')

    await expect(row.locator('.status-badge')).toHaveText('paid')
    await expect(select).toHaveValue('paid')
  })
})
