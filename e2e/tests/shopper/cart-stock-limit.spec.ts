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

    //   候選：page.getByLabel('???') 或 page.getByRole('spinbutton', { name: '???' })
    const row = page.locator('tr', { has: page.getByText(productName) })
    const quantityInput = row.getByRole('spinbutton', {
      name: `${productName} quantity`
    })
    await quantityInput.fill('99')
    await quantityInput.press('Enter')
    // ── ③ 驗證 ──
    // postive assertion
    const toastReg = new RegExp(`Only \\d+ of "${productName}" in stock\\.`)
    await expect(page.getByText(toastReg)).toBeVisible()
    // negative assertion
    await page.reload()
    await expect(quantityInput).toHaveValue('1')
  })
})
