import { expect } from '@playwright/test'

import { test } from '../../fixtures/auth'

test.describe('Checkout journey', () => {
  test('from storefront to a paid order', async ({ freshShopperPage }) => {
    const productName = 'E2E Widget A'
    const prodPrice = '$10.00'
    // ── ① 店面：加 E2E Widget A（$10.00——種子契約，金額斷言需要確定價格）──
    await freshShopperPage.goto('/')
    await freshShopperPage
      .getByRole('searchbox', { name: 'Search products' })
      .fill(productName)
    await freshShopperPage
      .getByRole('searchbox', { name: 'Search products' })
      .press('Enter')
    const card = freshShopperPage.locator('.product-card', {
      hasText: 'E2E Widget A'
    })
    await card.getByRole('button', { name: 'Add to cart' }).click()

    // ── ③ 結帳頁：驗金額 + 按 Pay ──
    await freshShopperPage.getByLabel('Cart').click()
    await expect(freshShopperPage).toHaveURL(/\/cart$/)

    await expect(freshShopperPage.locator('.cart-total')).toHaveText(prodPrice)

    await freshShopperPage
      .getByRole('button', { name: /Checkout \(\d+\)/i })
      .click()

    await expect(freshShopperPage).toHaveURL(/\/checkout/)
    await expect(
      freshShopperPage.getByRole('button', { name: 'Pay $' })
    ).toBeVisible()
    await freshShopperPage.getByRole('button', { name: 'Pay $' }).click()

    // ── ④ 結果頁：三個終點證據之一 ──
    await expect(freshShopperPage).toHaveURL(/checkout\/result\?.+/)
    await expect(
      freshShopperPage.getByRole('heading', { name: 'Payment complete' })
    ).toBeVisible()
    // getByRole('status') 會撞到還沒消失的 toast（它也是 role=status）——
    // scope 到結果頁自己的容器
    await expect(freshShopperPage.locator('.result-hero')).toContainText(
      prodPrice
    )

    const orderId = new URL(freshShopperPage.url()).searchParams.get('order')
    // ── ⑤ 購物車清空 ──
    await freshShopperPage.locator('a[aria-label="Cart"]').click()
    await expect(freshShopperPage.getByText('Your cart is empty')).toBeVisible()

    // ── ⑥ 訂單列表：badge = paid ──
    await freshShopperPage.goto('/app/orders')
    const row = freshShopperPage.locator('tr', {
      has: freshShopperPage.getByText(`#${orderId}`)
    })
    await expect(row.locator('.status-badge')).toHaveText('paid')
  })
})
