import { expect, test } from '@playwright/test'

test.describe('Checkout journey', () => {
  test('from storefront to a paid order', async ({ page }) => {
    const productName = 'E2E Widget A'
    const prodPrice = '$10.00'
    // ── ① 店面：加 E2E Widget A（$10.00——種子契約，金額斷言需要確定價格）──
    await page.goto('/')
    await page
      .getByRole('searchbox', { name: 'Search products' })
      .fill(productName)
    await page
      .getByRole('searchbox', { name: 'Search products' })
      .press('Enter')
    const card = page.locator('.product-card', { hasText: 'E2E Widget A' })
    await card.getByRole('button', { name: 'Add to cart' }).click()

    // ── ③ 結帳頁：驗金額 + 按 Pay ──
    await page.getByLabel('Cart').click()
    await expect(page).toHaveURL(/\/cart$/)

    await expect(page.locator('.cart-total')).toHaveText(prodPrice)

    await page.getByRole('button', { name: /Checkout \(\d+\)/i }).click()

    await expect(page).toHaveURL(/\/checkout/)
    await expect(page.getByRole('button', { name: 'Pay $' })).toBeVisible()
    await page.getByRole('button', { name: 'Pay $' }).click()

    // ── ④ 結果頁：三個終點證據之一 ──
    await expect(page).toHaveURL(/checkout\/result\?.+/)
    await expect(
      page.getByRole('heading', { name: 'Payment complete' })
    ).toBeVisible()
    await expect(page.getByRole('status')).toContainText(prodPrice)

    const orderId = new URL(page.url()).searchParams.get('order')
    // ── ⑤ 購物車清空 ──
    await page.locator('a[aria-label="Cart"]').click()
    await expect(page.getByText('Your cart is empty')).toBeVisible()

    // ── ⑥ 訂單列表：badge = paid ──
    await page.goto('/app/orders')
    const row = page.locator('tr', { has: page.getByText(`#${orderId}`) })
    await expect(row.locator('.status-badge')).toHaveText('paid')
  })
})
