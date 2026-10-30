import { expect, test } from '@playwright/test'

import { signupViaUi, uniqueEmail } from './helpers'

// 旅程 2：逛店 → 加購物車 → 購物車頁看得到商品。
// 點「第一張有 Add to cart 的卡片」是合法的模糊——任何在庫商品都符合目的。

test.describe('Store cart journey', () => {
  // 收集階段執行一次：造一個隨機 email。
  // 注意這是「這個 describe 只跑一次」的層級——不是每條測試新的一個
  // （之前教過的陷阱：想每條新的要放 beforeEach 裡）。
  // 這裡只有一條測試，所以無所謂。

  test.beforeEach(async ({ page }) => {
    await signupViaUi(page, 'E2E Cart', uniqueEmail('e2e-cart'))
  })
  // hook：這個 describe 裡的「每一條」測試跑之前，先執行這個。
  // 效果：測試一開始就已經是「剛註冊好的新帳號」登入狀態，
  // 購物車保證是空的——這就是「先註冊一個新帳號，避免購物車有舊資料」的意思。

  test('add to cart shows the product in the cart', async ({ page }) => {
    await page.goto('/')
    // 動作 ①：開店面

    const card = page
      .locator('.product-card', {
        has: page.getByRole('button', { name: 'Add to cart' })
      })
      .first()
    // 動作 ② 的準備：定義查詢——
    //   「class 是 product-card、而且卡片『內部』有一顆 Add to cart 按鈕」的卡片
    // has 的作用：缺貨卡（E2E Widget B）的按鈕是 notify me，不含 Add to cart
    //   → 自動被排除，永遠只會選到有庫存的卡
    // .first()：符合的卡片可能多張（E2E Widget A + 其他商品），取第一張

    const productName = await card.locator('.product-name').innerText()
    // 從選中的卡裡讀商品名 → 存起來，最後拿來斷言（先記住加了什麼，等等驗它出現）

    await card.getByRole('button', { name: 'Add to cart' }).click()
    // 動作 ②：點那張卡「裡面」的按鈕（鏈式作用域——不會誤點別張卡的）

    await page.locator('a[aria-label="Cart"]').click()
    // 動作 ③：點 header 的購物車圖示進購物車頁
    // 為什麼用 aria-label 不用 getByRole('link', { name: 'Cart' })？
    //   因為 footer 也有一個文字連結叫 Cart → 會撞兩個 → strict mode 爆炸
    //   aria-label="Cart" 只有 header 那顆有 → 精準

    await expect(page.getByText(productName).first()).toBeVisible()
    // 驗證 ①：剛加的商品名出現在購物車頁
    // .first()：商品名可能出現兩次（縮圖 alt、明細），任何一個出現都算成立

    await expect(page.getByText('Your cart is empty')).toBeHidden()
  })
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
