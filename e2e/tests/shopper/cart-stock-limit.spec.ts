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
    // TODO 1a：查種子商品 id（你已經會了：GET /api/products?q=E2E Widget A）
    //   方法：const products = await (await page.request.get('/api/products?q=???')).json()
    // TODO 1b：加入購物車（數量 1）
    //   方法：await page.request.post('/api/cart/items', {
    //           data: { product_id: products[0].id, quantity: 1 },
    //         })
    //   ⚠️ 不確定路徑/body 的話：grep app/routers/cart.py 的 @router.post
    //     或直接看 CartView.vue 呼叫的 api.post 路徑

    // ── ② 動作：開購物車頁，把數量改成 99 ──
    await page.goto('/cart')

    // TODO 2a：鎖定數量 input（偵察 Q1 的答案決定用哪個）
    //   候選：page.getByLabel('???') 或 page.getByRole('spinbutton', { name: '???' })
    const row = page.locator('tr', { has: page.getByText(productName) })
    const quantityInput = row.getByRole('spinbutton', {
      name: `${productName} quantity`
    })

    // TODO 2b：填 99 並觸發（CartView 監聽什麼事件就觸發什麼）
    //   await quantityInput.fill('99')
    //   await quantityInput.press('Enter')     // 或 .blur()——偵察時讀代碼決定
    await quantityInput.fill('99')
    await quantityInput.press('Enter')
    // ── ③ 驗證 ──
    // TODO 3a：錯誤訊息可見（偵察 Q2 的答案——精確文字或 regex）
    //   await expect(page.getByText('???')).toBeVisible()
    await expect(page.getByText(/Only \d+ in stock\./i)).toBeVisible()
    // TODO 3b（反向）：reload 後數量還是 1——「什麼都沒發生」的硬證據
    await page.reload()
    await expect(quantityInput).toHaveValue('1')
  })
})
