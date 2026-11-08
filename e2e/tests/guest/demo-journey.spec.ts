// demo 探索旅程：免帳密一鍵進入唯讀 admin workspace。
// 驗證矩陣：demo 按鈕 → admin 頁可看 → 寫入被後端 403 擋下（唯讀 session）。
import { test, expect } from '@playwright/test'

test.describe('demo journey (view-only admin)', () => {
  test('demo button enters admin workspace without credentials', async ({
    page
  }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: /explore demo/i }).click()

    await page.waitForURL(/\/admin\/orders/)
    await expect(
      page.getByRole('heading', { name: 'Order Management' })
    ).toBeVisible()

    // demo 帳號身分可見（header 帳戶區）。
    await expect(page.getByText('Demo Viewer').first()).toBeVisible()
  })

  test('demo session is read-only: backend rejects mutations with 403', async ({
    page
  }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: /explore demo/i }).click()
    await page.waitForURL(/\/admin\/orders/)

    // 走頁面 context 的 cookie 打寫入 API——後端 require_admin 必須擋。
    const response = await page.request.patch('/api/products/1', {
      data: { price: '999.00' }
    })
    expect(response.status()).toBe(403)
  })

  test('demo session survives reload (state lives server-side)', async ({
    page
  }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: /explore demo/i }).click()
    await page.waitForURL(/\/admin\/orders/)

    await page.reload()
    await expect(
      page.getByRole('heading', { name: 'Order Management' })
    ).toBeVisible()
    await expect(page.getByText('Demo Viewer').first()).toBeVisible()
  })
})
