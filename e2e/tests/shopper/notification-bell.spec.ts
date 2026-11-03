import { expect, Page } from '@playwright/test'

import { createOrder } from '../../api/orders'
import { test } from '../../fixtures/auth'

test.describe('Notification bell journey', () => {
  test("bell lights up when admin touches shopper's order", async ({
    freshShopperPage,
    browser
  }) => {
    const getBadgeCount = async (page: Page) => {
      const bell = page.getByRole('button', { name: 'Notifications' })
      const badge = bell.locator('.bell-badge')
      return (await badge.isVisible()) ? parseInt(await badge.innerText()) : 0
    }

    // ① shopper（page）造訂單：unpaid 是穩定地板（worker 不碰）
    const order = await createOrder(freshShopperPage.request)

    // ② admin 分頁（第二身份——你練習 1.5 的技術）
    const adminContext = await browser.newContext({
      storageState: '.auth/admin.json'
    })
    const adminPage = await adminContext.newPage()

    // ③ shopper 停在頁面，admin 去改狀態（actor 切換，各自驗自己的前提）
    await freshShopperPage.goto('/app/orders')
    await adminPage.goto('/admin/orders')

    // ── shopper 半邊：SSE → 鈴鐺 ──
    // 陷阱：createOrder 的「訂單已建立」通知也會讓 badge 亮——
    // 所以不能斷言「badge 出現」（建單通知會讓它 trivially 過）。
    // 正解：記住 admin 動作「之前」的未讀數，斷言「之後」變多了。

    // PREVIOUS BADGE COUNT
    const previousBadgeCount = await getBadgeCount(freshShopperPage)
    // find the row and change the status
    await adminPage
      .getByLabel('Filter by user ID')
      .fill(order.user_id.toString())
    await adminPage.getByLabel('Filter by user ID').press('Enter')
    const adminRow = await adminPage.locator('tr', {
      has: adminPage.getByText(`#${order.id}`)
    })
    await expect(adminRow).toBeVisible({ timeout: 10_000 })
    await adminRow
      .getByLabel(`Change status for order ${order.id}`)
      .selectOption('cancelled')
    await expect(adminRow.locator('.status-badge')).toHaveText('cancelled')

    // positive assertion
    await expect(async () => {
      const newBadgeCount = await getBadgeCount(freshShopperPage)
      expect(newBadgeCount).toBeGreaterThan(previousBadgeCount)
    }).toPass({ timeout: 20_000 })
    // close admin context
    await adminContext.close()
  })
})
