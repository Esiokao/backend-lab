import { expect, test } from '@playwright/test'

test.describe('Shopper orders journey', () => {
  test('shopper sees their order in the orders list', async ({ page }) => {
    // ── seed種的product ──
    const products = await (
      await page.request.get('/api/products?q=E2E Widget A')
    ).json()
    expect(products.length, 'seeded product should exist').toBeGreaterThan(0)

    const productId = products[0].id // 位置 A:商品 id(查表)
    const res = await page.request.post('/api/orders', {
      data: { items: [{ product_id: productId, quantity: 1 }] }
    })
    expect(res.status(), await res.text()).toBe(200)

    const order = await res.json()
    const orderId = order.id // 位置 B:訂單 id(回應)

    // ── ② 動作 ──
    await page.goto('/app/orders')

    // ── ③ 驗證:用 位置B 的 id 看畫面 ──
    const row = page.locator('tr', { has: page.getByText(`#${orderId}`) })
    await expect(row).toBeVisible()
    await expect(row.getByText(/created/i)).toBeVisible()
  })
})
