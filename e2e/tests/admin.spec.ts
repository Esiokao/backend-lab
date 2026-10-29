import {
  expect,
  test,
  type APIRequestContext,
  type Page
} from '@playwright/test'

// 旅程 4：shopper 下單（API）→ admin 在後台看到 → 推進狀態機。
// 這條是 admin project 存在的理由：admin.json 終於有旅程用它。
//
// 分工：
//   page            ← admin project 的 storageState（config 注入 admin cookie）
//   shopperContext  ← browser.newContext() 掛 shopper.json，第二身份並存
// （兩個 context = 兩份 cookie jar，見 playbook 的「多身份」章）

const ADMIN_ORDERS_URL = '/admin/orders'

/** 用 shopper 身份透過 API 下一筆單，回傳 { id, user_id }。 */
async function createOrderAsShopper(
  shopper: APIRequestContext
): Promise<{ id: number; user_id: number }> {
  // 種子商品（auth.setup.ts 種的 E2E Widget A，在庫 50）。
  const products = await (
    await shopper.get('/api/products?q=E2E Widget A')
  ).json()
  expect(products.length, 'seeded product should exist').toBeGreaterThan(0)
  const productId = products[0].id

  const res = await shopper.post('/api/orders', {
    data: { items: [{ product_id: productId, quantity: 1 }] }
  })
  expect(res.status(), await res.text()).toBe(200)

  const order = await res.json()
  return { id: order.id, user_id: order.user_id }
}

async function filterByUserId(page: Page, userId: number): Promise<void> {
  // input 有 @change="applyFilters"：fill 後 blur（點別處）即觸發。
  await page.getByLabel('Filter by user ID').fill(String(userId))
  await page.getByLabel('Filter by user ID').blur()
  await expect(page.getByText('1 orders')).toBeVisible()
}

test.describe('Admin orders journey', () => {
  test('admin sees a fresh shopper order and advances created to pending', async ({
    page,
    browser
  }) => {
    // ① shopper 身份（API 造資料，不開 UI——UI 只留給被測的 admin）
    const shopperContext = await browser.newContext({
      storageState: '.auth/shopper.json'
    })
    const order = await createOrderAsShopper(shopperContext.request)
    await shopperContext.close()

    // ② admin 開後台，用 user ID 篩出這筆（訂單列表按 id 正序，
    //    dev DB 可能累積大量舊單，不篩會翻不到頁）。
    await page.goto(ADMIN_ORDERS_URL)
    await filterByUserId(page, order.user_id)

    const row = page.locator('tr', { has: page.getByText(`#${order.id}`) })
    await expect(row).toBeVisible()
    await expect(row.locator('.status-badge')).toHaveText('created')

    // ③ 推進狀態機：created → pending（ALLOWED_TRANSITIONS 的合法第一步）。
    const select = page.getByLabel(`Change status for order ${order.id}`)
    await select.selectOption('pending')

    // PATCH 後 loadOrders() 重撈：badge 和 dropdown 都該變成 pending。
    await expect(row.locator('.status-badge')).toHaveText('pending')
    await expect(select).toHaveValue('pending')
  })
})
