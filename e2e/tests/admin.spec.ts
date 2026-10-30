// ═══════════════════════════════════════════════════════════════════
// 教學註解版：每個 Playwright API 呼叫都標了「它在幹嘛」。
// 想自己練習改「自建 shopper」時，看 【練習標記】 處。
// ═══════════════════════════════════════════════════════════════════

// expect / test：Playwright 的斷言器與測試註冊器（從套件 import）。
// type APIRequestContext / Page：TypeScript 型別標註用——
//   APIRequestContext = 「能發 HTTP 請求的 client」的型別（page.request、
//   request.newContext() 造出來的東西都是這個型別）
//   Page = 一個瀏覽器分頁的型別
import {
  expect,
  test,
  request,
  type APIRequestContext,
  type Page
} from '@playwright/test'
import { uniqueEmail, PASSWORD } from './helpers'

// 旅程 4：shopper 下單（API）→ admin 在後台看到 → 推進狀態機。
// 這條是 admin project 存在的理由：admin.json 終於有旅程用它。
//
// 分工：
//   page            ← admin project 的 storageState（config 注入 admin cookie）
//   shopperContext  ← 第二身份（練習 1.5 要改成自建，見下方【練習標記】）

const ADMIN_ORDERS_URL = '/admin/orders'

/**
 * 用 shopper 身份透過 API 下一筆單，回傳 { id, user_id }。
 *
 * @param shopper — 一個「已登入的 API client」。
 *   傳誰進來，訂單就掛在誰名下——這個參數是「身份」的注入點。
 */
async function createOrderAsShopper(
  shopper: APIRequestContext
): Promise<{ id: number; user_id: number }> {
  // ── shopper.get(...) ──────────────────────────────────────────
  // 發 HTTP GET 請求。shopper 這個 client 身上的 cookie 會自動附上
  // （它登入過的話）。回傳的是 Response 物件，不是資料本身。
  const products = await (
    await shopper.get('/api/products?q=E2E Widget A')
  ).json()
  //     ↑ 外層 await：真的去讀 response body（body 是另一趟傳輸）
  //     內層 await：等回應抵達
  // 兩層都要——少一層就是在「兌換券」上叫 .json()

  // expect 的第二個參數 = 自訂失敗訊息：紅燈時會顯示這句話，
  // 让你不用猜「是空陣列還是別的」。
  expect(products.length, 'seeded product should exist').toBeGreaterThan(0)
  const productId = products[0].id

  // ── shopper.post(path, { data }) ──────────────────────────────
  // 發 HTTP POST。{ data: ... } 會被自動 JSON.stringify 並加上
  // Content-Type: application/json——不用自己手動序列化。
  const res = await shopper.post('/api/orders', {
    data: { items: [{ product_id: productId, quantity: 1 }] }
  })

  // res.status() 是同步的（headers 已到手）；res.text() 要 await（讀 body）。
  // 把 body 塞進失敗訊息：紅燈時直接看到後端說了什麼（如 400 的 detail）。
  expect(res.status(), await res.text()).toBe(200)

  const order = await res.json()
  return { id: order.id, user_id: order.user_id }
}

/**
 * 在 admin 訂單頁填入「Filter by user ID」並等列表刷新。
 * ⚠️ 這個 helper 綁定 AdminOrdersView 的 DOM——換頁面不能直接搬。
 */
async function filterByUserId(page: Page, userId: number): Promise<void> {
  // ── page.getByLabel('...') ────────────────────────────────────
  // 在無障礙樹上找「label 是這個字」的表單欄位。
  // 對應 AdminOrdersView 裡的 <input aria-label="Filter by user ID">。
  // getByLabel 回傳 Locator（查詢條件），此時還沒碰頁面。

  // ── .fill(String(userId)) ─────────────────────────────────────
  // 清空輸入框 → 打字填入。只改「值」，不觸發 @change
  // （瀏覽器規則：文字框的 change 要等 blur 才發）。

  // ── .blur() ───────────────────────────────────────────────────
  // 讓焦點離開這個欄位 = 模擬「使用者點了別處」。
  // 這一瞬間瀏覽器發出 change 事件 → Vue 的 @change="applyFilters"
  // → 列表重撈。沒有這行，列表永遠不會刷新。
  await page.getByLabel('Filter by user ID').fill(String(userId))
  await page.getByLabel('Filter by user ID').blur()

  // （原版斷言已被移除——它寫死「這個 user 只有 1 筆訂單」，
  //  别的測試幫同一個 shopper 下單就會炸。改驗 row：呼叫端做。）
}

test.describe('Admin orders journey', () => {
  // ── test('名字', async ({ page, browser }) => {...}) ───────────
  // 大括號 = 解構 fixtures。點名 page → Playwright 給你一台分頁；
  // 點名 browser → 給你瀏覽器實體（只有要「再開一個 context」才需要它）。
  test('admin sees a fresh shopper order and advances created to pending', async ({
    page
  }) => {
    // ── browser.newContext({ storageState }) ─────────────────────
    // 開一個全新的 browser context = 一份全新的 cookie jar。
    // storageState: '.auth/shopper.json' = 開機時把這份 cookie 檔
    // 預先倒進 jar → 這個 context 裡的一切天生是 shopper 登入態。
    //
    // 【練習 1.5 標記】這裡整段要換成：
    //   const shopper = await request.newContext({ baseURL: ... })
    //   → 用 API 註冊 + 登入（cookie 自動進 jar）
    //   → 簽名加 request、拿掉 browser（不再需要開瀏覽器造身份）
    const shopper = await request.newContext({
      baseURL: 'http://localhost:5173'
    })

    const email = uniqueEmail('owner')
    await shopper.post('/api/users', {
      data: { name: 'E2E Order Owner', email, password: PASSWORD }
    })

    await shopper.post('/api/login', {
      data: { email, password: PASSWORD }
    })

    const order = await createOrderAsShopper(shopper)

    await shopper.dispose()

    // ── page.goto(path) ───────────────────────────────────────────
    // 導航。相對路徑會補上 config 的 baseURL（http://localhost:5173）。
    // page 是 admin project 的分頁 → cookie 已是 admin → 這頁直接可用。
    await page.goto(ADMIN_ORDERS_URL)
    await filterByUserId(page, order.user_id)

    // ── page.locator('tr', { has: ... }) ──────────────────────────
    // 定義查詢：「所有 <tr>，而且內部含 getByText('#42') 的那個」。
    // has 是範圍收窄——不是全頁找文字，是「只看這列裡面」。
    // 此刻只是存查詢，還沒查頁面。
    const row = page.locator('tr', { has: page.getByText(`#${order.id}`) })

    // ── await expect(...).toBeVisible() ───────────────────────────
    // 把 locator 交給 expect = 開啟輪詢重試（預設 5 秒）：
    // 每幾百毫秒重新執行整條查詢，直到出現或逾時。
    // 這就是「操作後第一行寫 expect」能吸收延遲的原因。
    await expect(row).toBeVisible()

    // ── row.locator('.status-badge') ──────────────────────────────
    // 鏈式：在 row「裡面」找——不是全頁的 status-badge，
    // 是這一列的。作用域跟著鏈走。
    await expect(row.locator('.status-badge')).toHaveText('created')

    // ── page.getByLabel(`Change status for order ${id}`) ──────────
    // 模板字串組出動態 aria-label：每列的下拉都有唯一標籤
    // （AdminOrdersView 用 `Change status for order ${order.id}`），
    // 所以這個 locator 天然精準，不會撞到別列的下拉。

    // ── .selectOption('pending') ──────────────────────────────────
    // 專門操作 <select>：等值為 'pending' 的 <option> 選下去。
    // 會觸發 change → Vue 的 changeStatus → PATCH API → loadOrders()。
    const select = page.getByLabel(`Change status for order ${order.id}`)
    await select.selectOption('pending')

    // PATCH 後 loadOrders() 重撈：badge 和 dropdown 都該變成 pending。
    await expect(row.locator('.status-badge')).toHaveText('pending')
    await expect(select).toHaveValue('pending')
  })
})
