import { test, expect } from '@playwright/test'

test.describe('Cart stock limit journey', () => {
  test('changing quantity over stock shows an error and keeps the original value', async ({
    page
  }) => {
    const productName = 'E2E Widget A'
    // ── ① 造資料：用 page.request 直接加商品進購物車（快，UI 留給被測行為）──
    const products = await (
      await page.request.get(`/api/products?q=${productName}`)
    ).json()
    const productId = products[0].id
    await page.request.post('/api/cart/items', {
      data: { product_id: productId, quantity: 1 }
    })

    // ── ② 動作：開購物車頁，把數量改成 99 ──
    await page.goto('/cart')

    const row = page.locator('tr', { has: page.getByText(productName) })
    const quantityInput = row.getByRole('spinbutton', {
      name: `${productName} quantity`
    })

    await quantityInput.fill('99')
    await quantityInput.press('Enter')
    // ── ③ 驗證 ──
    // 文案與 seed 契約耦合：seed.sql 釘 E2E Widget A stock=50,
    // 文案變更(前端或 seed)時此測試要同步更新——這是它的職責。
    await expect(
      page.getByText('Only 50 of "E2E Widget A" in stock.')
    ).toBeVisible()
    await page.reload()
    await expect(quantityInput).toHaveValue('1')
  })
})
