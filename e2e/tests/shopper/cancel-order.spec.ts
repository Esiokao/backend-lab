import { expect } from '@playwright/test'

import { test } from '../../fixtures/auth'
import { createOrder, payOrder } from '../../api/orders'

// 旅程 3：owner 取消自己的訂單 → 狀態變 cancelled（PRD F8）。
// 身份：freshShopperPage（fixtures/auth 的每測全新 shopper——會改狀態的測試
// 不用共用 storageState，避免訂單/通知歷史跨測試污染）。
// 資料：createOrder + payOrder 走到真實流程的終點 paid——取消不可逆，絕不碰別的測試的訂單。
test.describe('Cancel order journey', () => {
  test('owner cancels their own paid order and sees it cancelled', async ({
    freshShopperPage: page
  }) => {
    // create order
    const order = await createOrder(page.request)
    await payOrder(page.request, order.id)

    // go to order page and cancel
    await page.goto('/app/orders')
    // got order row
    const row = await page.locator('tr', {
      has: page.getByText(`#${order.id}`)
    })

    await expect(row).toBeVisible()
    await expect(row.locator('.status-badge')).toHaveText('paid')
    // handler for cancel confirm
    page.once('dialog', async (dialog) => {
      await dialog.accept()
    })
    // click cancel button
    await row.getByLabel(`Cancel order ${order.id}`).click()
    // positive assertion
    await expect(row.locator('.status-badge')).toHaveText('cancelled')
    // negative assertion
    await expect(row.getByLabel(`Cancel order ${order.id}`)).toBeHidden()
  })
})
