import { expect, test } from '@playwright/test'

import { createOrder, payOrder } from '../../api/orders'

// 旅程 3：owner 取消自己的訂單 → 狀態變 cancelled（PRD F8）。
// 身份：shopper（shopper/ 目錄的 storageState）。
// 資料：createOrder + payOrder 走到真實流程的終點 pending——取消不可逆，絕不碰別的測試的訂單。
test.describe('Cancel order journey', () => {
  test('owner cancels their own paid order and sees it cancelled', async ({
    page
  }) => {
    // ── ① 造資料：走到真實 UI 流程會停留的狀態 ──
    // 真實結帳 = 建單 + 付款，終點是 pending（已付款待出貨）；
    // 只 create 不 pay 的 created 是「按了結帳沒按 Pay」的過渡態，
    // 真實使用者幾乎不會停留——造資料要貼近真實流程的終點，不是中間點。
    const order = await createOrder(page.request)
    await payOrder(page.request, order.id)

    // ── ② 動作：打開列表，確認訂單在，然後取消 ──
    await page.goto('/app/orders')

    const row = page.locator('tr', { has: page.getByText(`#${order.id}`) })
    await expect(row).toBeVisible()
    await expect(row.locator('.status-badge')).toHaveText('pending')

    // 原生 window.confirm：不是 DOM 元素，locator 系武器全部無效，
    // 只能用 dialog 事件 API。Playwright 預設「dismiss（取消）」——
    // 不掛 accept 的話，cancelOrder 在 confirm 就 return，什麼都不會發生。
    // once：這個頁面只有一次 confirm，掛一次就好。
    page.once('dialog', (dialog) => dialog.accept())

    // Cancel 按鈕有 v-if="status === 'created' || 'pending'"——
    // cancelled 訂單的列不會有這顆按鈕（aria-label 精準鎖這筆訂單的那顆）。
    await page.getByLabel(`Cancel order ${order.id}`).click()

    // ── ③ 驗證 ──
    // cancelOrder 成功後 loadOrders() 重撈：badge 從 pending 變 cancelled。
    // 斷言「狀態」而不是 toast 文字——toast 幾秒後消失，狀態是永久的。
    await expect(row.locator('.status-badge')).toHaveText('cancelled')

    // 反向：取消後 Cancel 按鈕消失（cancelled 不在 v-if 條件裡）——
    // 驗「不能再取消一次」，狀態機的 UI 端出口。
    await expect(page.getByLabel(`Cancel order ${order.id}`)).toBeHidden()
  })
})
