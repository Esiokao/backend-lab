import { expect, test } from '@playwright/test'

import { signupViaUi, uniqueEmail } from './helpers'

// 旅程 2：逛店 → 加購物車 → 購物車頁看得到商品。
// 點「第一張有 Add to cart 的卡片」是合法的模糊——任何在庫商品都符合目的。

test.describe('Store cart journey', () => {
  let email: string = uniqueEmail('e2e-cart')
  ;(test.beforeEach(async ({ page }) => {
    // 先註冊一個新帳號，避免購物車有舊資料。

    await signupViaUi(page, 'E2E Cart', email)
  }),
    test('add to cart shows the product in the cart', async ({ page }) => {
      await page.goto('/')

      // 挑一張有「Add to cart」的卡片（缺貨卡是 Out of stock — notify me，不會被選到）。
      const card = page
        .locator('.product-card', {
          has: page.getByRole('button', { name: 'Add to cart' })
        })
        .first()
      const productName = await card.locator('.product-name').innerText()

      await card.getByRole('button', { name: 'Add to cart' }).click()

      // header 的購物車連結進購物車頁（footer 也有一個「Cart」文字連結，
      // 用 aria-label 鎖定 header 那顆）。
      await page.locator('a[aria-label="Cart"]').click()

      await expect(page.getByText(productName).first()).toBeVisible()
      await expect(page.getByText('Your cart is empty')).toBeHidden()
    }))
})

// 旅程 2b：搜尋 + 排序。種子商品 E2E Widget A（$10）/ B（$20，缺貨），
// 先用搜尋縮到只剩這兩張卡，再選價格降冪——順序斷言才不受 dev DB 其他商品干擾。
test.describe('Store sorting journey', () => {
  test('price high to low reorders the product cards', async ({ page }) => {
    await page.goto('/')

    // 搜尋 "E2E Widget"：@change 在 blur 觸發，fill 後按 Enter（@keydown.enter）更直接。
    await page.getByLabel('Search products').fill('E2E Widget')
    await page.getByLabel('Search products').press('Enter')

    // 排序前（id 遞增）：A 先 B 後。
    await expect(page.locator('.product-name').first()).toHaveText(
      'E2E Widget A'
    )

    await page.getByLabel('Sort products').selectOption('price_desc')

    // 切排序 → 重撈 → 第一張卡變成貴的那個（B，$20）。斷言吸收重撈的延遲。
    await expect(page.locator('.product-name').first()).toHaveText(
      'E2E Widget B'
    )

    // 反向再驗一次：升冪第一張回到 A。
    await page.getByLabel('Sort products').selectOption('price_asc')
    await expect(page.locator('.product-name').first()).toHaveText(
      'E2E Widget A'
    )
  })
})
