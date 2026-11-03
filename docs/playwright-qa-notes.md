# Playwright 學習筆記 — QA 問答集

> 以本 repo（backend-lab，Vue SPA + FastAPI + session cookie）的實際代碼為例。
> 產出日期：2026-10-29。

---

## 目錄

1. [核心心法與三個觀念](#1-核心心法與三個觀念)
2. [page 與 fixtures 的本質](#2-page-與-fixtures-的本質)
3. [選擇器：getByRole / getByText / getByLabel / aria-label](#3-選擇器getbyrole--gettext--getbylabel--aria-label)
4. [斷言與 waitForTimeout](#4-斷言與-waitfortimeout)
5. [locator 鏈式作用域與 expect 重試原理](#5-locator-鏈式作用域與-expect-重試原理)
6. [非同步到底非同步在哪裡](#6-非同步到底非同步在哪裡)
7. [storageState：砍登入成本](#7-storagestate砍登入成本)
8. [request：API 測試](#8-requestapi-測試)
9. [session 機制：重複登入會怎樣](#9-session-機制重複登入會怎樣)
10. [多分頁 / 多身份複雜測試](#10-多分頁--多身份複雜測試)
11. [自訂 fixture（test.extend）](#11-自訂-fixturetestextend)
12. [config 與環境變數](#12-config-與環境變數)
13. [測試分層與白箱/黑箱界線](#13-測試分層與白箱黑箱界線)
14. [五條軍規](#14-五條軍規)

---

## 1. 核心心法與三個觀念

> **測試寫的是「使用者看得到什麼」，不是「DOM 長什麼樣」。**
> 所有 flaky、維護地獄，都是因為違反這句話。

### ① Auto-waiting — 不要寫 sleep

Playwright 每個 action 自動等元素「存在 + 可見 + 可點」：

```ts
// ❌ flaky 萬惡之源
await page.waitForTimeout(2000);
await page.click('button');

// ✅ 永遠不需要 sleep
await page.getByRole('button', { name: 'Sign in' }).click();
await expect(page.getByRole('button', { name: 'Account menu' })).toBeVisible();
```

### ② Locator ≠ Element — Locator 是「查詢」，不是「指標」

```ts
const btn = page.getByRole('button', { name: 'Add to cart' });
// 此刻什麼都還沒發生！它只是描述「去找這個按鈕」
// 每次 .click() / .innerText() 都重新查詢 → 天生抗 DOM 重建 / 重渲染
```

### ③ 嚴格模式 — 多個匹配直接報錯

Strict mode violation 代表選擇器太模糊。修選擇器優先；
只有「多個命中都代表測試目的成立」時才用 `.first()`（知情選擇）。

### 選擇器優先序

```
getByRole > getByLabel > getByText > getByPlaceholder > getByTestId > CSS/XPath
```

role-first 同時是免費的 a11y 測試：`getByRole` 找不到，代表螢幕閱讀器也找不到。

---

## 2. page 與 fixtures 的本質

### `test('xxx', async ({ page }) => ...)` 為什麼帶 page

`{ page }` 是**解構**。完整等價寫法：

```ts
test('signup', async (fixtures) => {
  const page = fixtures.page;   // 跟 { page } 完全等價
});
```

**fixtures = Playwright 幫你準備好的「測試設備」**。點名制，用完即丟：

| fixture | 是什麼 |
|---|---|
| `page` | 一個專屬瀏覽器分頁（遙控器） |
| `request` | API 測試用 HTTP client（不開瀏覽器） |
| `browser` | 瀏覽器實體，要開第二個 context 才需要 |

### 為什麼用 fixtures 而不是全域變數

1. **隔離**：平行 worker 各拿自己的 page，互不干擾。
2. **自動清理**：每條測試結束 page（含 cookie、localStorage）銷毀，
   每條測試都是乾淨未登入狀態 → store.spec.ts 每條重新 signup 是設計不是 bug。
3. **要什麼才造什麼**：只點名 `{ request }` 就不啟動瀏覽器，測試更快。

### page 上有什麼

```ts
await page.goto('/login');   // 網址列輸入 + Enter
await page.goBack();         // 上一頁
await page.reload();         // F5
await page.getByRole(...);   // 「幫我找元素」→ 回傳 locator
await page.title();          // 分頁標題
```

兩段式心智模型：**page 幫我找 → 拿到 locator → 對 locator 動作**。

---

## 3. 選擇器：getByRole / getByText / getByLabel / aria-label

### getByRole 對應「無障礙樹」

瀏覽器為每個元素維護 accessibility tree，每個節點有 role / name / state。
`getByRole('button', { name: 'Sign in' })` = 找「role 是 button、朗讀出來是 Sign in」的節點。

| HTML | role |
|---|---|
| `<button>` | `button` |
| `<a href>` | `link` |
| `<input type="checkbox">` | `checkbox` |
| `<input type="text/email">` | `textbox` |
| `<h1>` | `heading` |
| `<select>` | `combobox` |

### name（可及名稱）的優先序

```
1. aria-label          ← 有就贏，蓋掉一切
2. aria-labelledby
3. <label for=id>      ← 表單欄位
4. label 包住 input    ← 表單欄位
5. 元素自身文字內容     ← 按鈕/連結最常見
```

### aria-label 是什麼

「這個元素的視覺內容不夠（或沒有文字）時，明確指定它朗讀出來是什麼」：

```html
<a href="/cart" aria-label="Cart">🛒</a>
<!-- 畫面是 emoji，但可及名稱是 "Cart" -->
```

### getByRole('textbox', { name: 'Email' }) ≡ getByLabel('Email')？

```html
<label>Email <input type="email"></label>
```

兩層效果：
1. 渲染層：使用者看到「Email」字樣、點文字可聚焦 input
2. 無障礙層：「Email」登記為 input 的可及名稱

`getByLabel` 底層就是 getByRole 的表單特化版，查同一棵樹、同一套 name 規則。
差別：getByLabel 只查表單欄位；`aria-label` 寫在非表單元素上只能用 getByRole。

**實用結論**：表單用 `getByLabel`；其他用 `getByRole`。
除錯工具：DevTools → Elements → Accessibility tab（那棵樹就是 Playwright 在查的）。

### getByText

**找「畫面上看得見的那段文字」**，不管包什麼標籤。

```
找「訊息」用 getByText（斷言出現/消失）
找「控件」用 getByRole（點擊、填寫）
```

`exact: true`：完全匹配（預設是子字串、不分大小寫）。
helpers 全加 `exact: true` 是防「Email」誤中「Email address」→ strict mode 爆炸。

---

## 4. 斷言與 waitForTimeout

### 斷言用 `expect`，輪詢到 timeout

```ts
await expect(locator).toBeVisible();        // 可見
await expect(locator).toBeHidden();         // 消失（也涵蓋「根本不存在」）
await expect(locator).toHaveText('確切全文');
await expect(locator).toContainText('部分');
await expect(locator).toHaveValue('a@b.c');
await expect(page).toHaveURL(/\/orders$/);
await expect(page).toHaveTitle(/Store/);
```

關鍵差別：

```ts
// ❌ await 在 expect 外 → 死值 → 只比一次，立刻可能錯
expect(await page.getByText('hi').innerText()).toBe('hi');

// ✅ 傳 locator 給 expect → 活查詢 → 自動重試
await expect(page.getByText('hi')).toHaveText('hi');
```

口訣：**見到 `expect(await ...)` 結構就要皺眉。**

### waitForTimeout 為什麼是毒藥

- 太短 → CI 慢就 flaky；太長 → 每次白等。
- 本質是把「我等的是什麼」這個資訊丟掉了。

**連動畫都有正解**——等「動畫結束」這個可觀察狀態：

```ts
// ✅ 等狀態，不等時間
await expect(sidebar).toBeInViewport();
await expect(sidebar).toHaveCSS('transform', 'matrix(1, 0, 0, 1, 0, 0)');
```

已知慢的場景（如 fulfillment worker 延遲）→ 拉長單條斷言的 timeout：

```ts
await expect(page.getByText('Completed')).toBeVisible({ timeout: 15_000 });
// 快就早過，慢才等滿；失敗訊息是「等不到 Completed」
```

---

## 5. locator 鏈式作用域與 expect 重試原理

### `page.getX` vs `locator.getX`：查詢起點不同

```ts
// 從整頁找 → 多張卡多個命中 → strict mode 爆炸
page.getByRole('button', { name: 'Add to cart' });

// 從卡片內部找 → 相對查詢
const card = page.locator('.product-card').first();
card.getByRole('button', { name: 'Add to cart' });
```

三種「相對」寫法：

```ts
// 1. 鏈式：B 在 A 內部找
card.getByRole('button', { name: 'Buy' })

// 2. filter：按文字/子元素過濾集合
page.locator('.product-card').filter({ hasText: '頭戴耳機' })
page.locator('tr').filter({ has: page.getByText('pending') })

// 3. nth/first：按位置（最後手段）
page.locator('.product-card').first()
```

`has:` 範圍收窄：只保留「內部包含該元素」的卡片；`has` 裡的 locator 必須以 page 開頭（自動相對化）。

### expect 重試的輪詢迴圈（pseudo code）

```
deadline = now + 5000ms
loop:
    inject JS：查 selector 匹配的元素 → 存在？display≠none？可見？佔面積>0？
    matched → 通過
    now > deadline → AssertionError（含實際狀態 diff）
    else sleep ~100ms → 再查
```

三個推論：

1. **抗 flaky**：每輪重試重新執行整條 locator 鏈，不是抓著舊元素。
2. **操作（click）不重試**：只有 auto-wait + 一次執行 →「操作後第一行寫 expect」的底層原因。
3. **死值沒有重試**：`expect(await ...)` 只剩一次比對機會。

---

## 6. 非同步到底非同步在哪裡

### await 確實是「等」——但它暫停的是函式，不是整個程式

```ts
const res = await request.get('/cart');   // 等 response 的 200ms 裡，
// 同一個 CPU 正在跑其他 worker 的 click、expect 輪詢、其他回應的處理……
```

> **「非同步」精確的意思：「發起」和「結果」之間的時間，程式沒有被佔死。**
> 不是「不等待」，是「等待期間不浪費」。平行 worker 就是靠這個存在的。

### 忘記 await 會怎樣

JavaScript 用 `Promise`（兌換券）連接「發起」和「結果」兩個時間點：

```ts
const p = request.get('/cart');   // 請求已在網路上跑；p 是兌換券，不是回應
const res = await p;              // await = 拿券兌換，到了才繼續
```

忘記 await → 在「結果還沒到」的時間點去「讀結果」：

```ts
const res = request.get('/cart'); // res = Promise 兌換券
res.status()                       // 💥 兌換券上沒有 status → undefined / TypeError

// 陰險版：
expect(res.ok()).toBe(true)        // res.ok() 回傳 undefined → 立刻 fail
                                   // 而真回應 200ms 後才回來，其實是 200！
```

> **await 同步的不是程式，是你這段代碼和那個結果的時序。**

### 為什麼 res.status() 同步、res.json() 要 await

```ts
const res = await request.get('/cart');  // 這裡的 await 已確保「回應到了」

res.status()  // headers 早就拿到了 → 純屬性讀取，同步
res.json()    // body 是另一趟傳輸（可能分很多 packet）→ 回傳 Promise，再 await
```

HTTP API 慣例：**headers 同步給你，body 用 Promise 給你**。

判斷法則：**呼叫一個方法，如果它可能要「再等任何東西」（網路、磁碟、下一個 packet），就回傳 Promise，就要 await。** TypeScript 會提示忘記 await 的值是 `Promise<...>`。

---

## 7. storageState：砍登入成本

### 原理

後端是 session cookie 認證 →「登入完成」的物理證據只是一顆 cookie。
**登入一次，把 cookie 存成檔案，之後每台分頁開機自帶。**

```json
{ "cookies": [session cookie...], "origins": [localStorage...] }
```

### 標準做法：Setup Project

```ts
// e2e/tests/auth.setup.ts
import { expect, test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  /* UI 登入一次 */
  await page.context().storageState({ path: 'e2e/.auth/shopper.json' });  // ← 關鍵
});
```

```ts
// playwright.config.ts
projects: [
  { name: 'setup', testMatch: /auth\.setup\.ts/ },
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/shopper.json' },
    dependencies: ['setup'],   // 先 setup 再跑主測試
  },
],
```

### 本 repo 的特殊坑：session 30 分鐘過期

- storageState 存的是死的 cookie 快照，不會滑動續期。
- CI 沒問題（setup 和主測試同 run 連續執行）。
- `dependencies` 的設計讓每次 run 重新登入重產檔，不依賴殘留檔案。
- `.auth/` 目錄要進 `.gitignore`（內含有效憑證）。

### 多角色

admin / shopper 各存一份 `.json`，config 各開一個 project 綁定；
同測試切身份 → `browser.newContext({ storageState: ... })`。

### 哪些測試「不該」用 storageState

| 類型 | 用？ | 原因 |
|---|---|---|
| 購物車、訂單列表、會員中心 | ✅ | 登入只是前置條件 |
| 登入/登出/註冊/記住我 | ❌ | 登入是被測行為 |
| 404 | 皆可 | 根本不需要登入 |

`auth.spec.ts` 的真實 UI 旅程要留著——它是 storageState 的地基驗證
（UI 登入壞了，setup 第一個紅，而不是 30 條測試一起莫名 401）。

### 「只帶認證，不帶資料」的本質

```
你是誰（認證）   → session cookie + Redis
你做過什麼（資料）→ PostgreSQL（cart_items / orders / notifications）
```

storageState 是「你是誰」的證件，不是「你做過什麼」的記錄。
帶 shopper cookie 開機，DB 裡他的購物車照樣是空的。

```ts
// 身份用 storageState 帶，資料在測試內現場造：
await page.request.post('/cart/items', { data: { product_id: 1, quantity: 2 } });
```

| | 存在哪 | storageState 帶得走嗎 | 測試怎麼準備 |
|---|---|---|---|
| 身份（session） | cookie + Redis | ✅ | setup project 產檔 |
| 購物車/訂單 | PostgreSQL | ❌ | 測試內 `page.request.post` 造 |
| 商品目錄 | PostgreSQL | ❌ | seed.sql / API 造 |

---

## 8. request：API 測試

### 三種取得方式

| | `{ request }` fixture | `page.request` | `request.newContext()` |
|---|---|---|---|
| 造的時機 | 自動 | 自動（跟 page 同 context） | 手動 |
| cookie jar | 自己一份 | **和分頁共用** | 造幾個有幾份 |
| 需要瀏覽器 | 否 | 是 | 否 |
| 用途 | 一般 API 斷言 | UI+API 混合 | 多角色 API 測試 |

```ts
// 獨立多身份（注意要自己 dispose）
const adminClient = await request.newContext({ baseURL: 'http://localhost:8000' });
const shopperClient = await request.newContext({ baseURL: 'http://localhost:8000' });
try { /* ... */ } finally { await adminClient.dispose(); await shopperClient.dispose(); }
```

### 動詞表

```ts
await request.get('/health');
await request.post('/cart/items',  { data: { product_id: 1, quantity: 2 } });
await request.patch('/orders/42',  { data: { status: 'completed' } });
await request.delete('/cart/items/1');

res.status()      // 同步（headers 已到手）
res.ok()          // 2xx？同步
await res.json()  // body 要 await
await res.text()
```

### 本 repo 特別注意：request 不走 vite proxy / nginx

```
前端 fetch('/api/cart') → vite proxy / nginx 剝掉 /api → FastAPI 收到 /cart
page.request.get('/cart')                          ← 直連後端，沒有 /api
```

推論：**前端發的 `/api` 路徑接不接得通，只有瀏覽器測試驗得到**
（只有它真的走翻譯層）——這就是 e2e 不能全被 API 測試取代的原因。

### 混合測試（cookie 共用）

```ts
test('signup → cart via api → verify', async ({ page }) => {
  await signupViaUi(page, 'E2E', email);   // UI 登入 → 分頁有 session cookie
  await page.request.post('/cart/items', { data: { product_id: 1, quantity: 1 } });
  const cart = await (await page.request.get('/cart')).json();  // 同 cookie！
  expect(cart.items).toHaveLength(1);
});
```

---

## 9. session 機制：重複登入會怎樣

**每次成功的 /login 都是「發一張新票」**：全新 session id + 全新 TTL，不是舊票續時間。

為什麼必須換新 id —— **session fixation 防禦**：若登入只是延長舊票，
攻擊者可先偷塞一張他知道 id 的票，等你登入後那張票變合法登入態。
換新 id，預置票自動作廢。

| 動作 | session id | TTL |
|---|---|---|
| 同一票的後續請求（滑動） | 不變 | 往後延 |
| 重新登入 | **全新** | 全新 30 分 |
| 改密碼 | 全部作廢 | — |

（本 repo：session 存 Redis，`SESSION_TTL_SECONDS=30 分鐘`滑動過期；改密碼撤銷 = PRD 的「A 改密碼，B 下一個請求 401」。）

---

## 10. 多分頁 / 多身份複雜測試

fixtures 分層：

```
browser（最貴，每 worker 開一次）
 └─ context（輕量：一份獨立 cookie jar）  ← storageState 掛這層
     └─ page（最輕：一個分頁）
```

- 第二個**分頁、同一身份** → `page.context().newPage()`（不需要 browser）
- 第二個**身份** → `{ browser }` 進來，`browser.newContext({ storageState })`

```ts
test('shopper buys, admin fulfills', async ({ browser, page }) => {
  const adminPage = await (await browser.newContext()).newPage();
  // adminPage 自己登入，與 page 完全隔離

  // shopper 下單
  await page.getByRole('button', { name: 'Checkout' }).click();
  await expect(page.getByText('Order placed')).toBeVisible();   // ← 同步點

  // admin 看到、處理訂單
  await adminPage.goto('/admin/orders');
  await adminPage.getByRole('button', { name: 'Mark paid' }).click();

  // shopper 的鈴鐺亮起（SSE 通知！）
  await expect(page.getByRole('button', { name: /notification/ })).toBeVisible();
});
```

核心規則：**每次切換 actor 後，第一件事寫該 actor 的 `await expect`**。
斷言的重試機制就是「同步器」，不需要 sleep 或 wait for event。

---

## 11. 自訂 fixture（test.extend）

```ts
// e2e/fixtures.ts
import { test as base, expect, type Page } from '@playwright/test';

export const test = base.extend<{
  shopperPage: Page;
  seedProduct: { id: number; name: string };
}>({
  seedProduct: async ({ request }, use) => {
    // setup
    const res = await request.post('/products', { data: { name: `Seed-${Date.now()}`, stock: 10 } });
    const product = await res.json();

    await use(product);   // ← 交給測試本體

    // teardown（成功失敗都會跑）
  },
});

export { expect };
```

```ts
// 測試檔 import「你的」test，不是 Playwright 的！
import { test, expect } from '../fixtures';

test('checkout', async ({ page, seedProduct }) => { /* seedProduct 已造好 */ });
```

| | pytest | Playwright |
|---|---|---|
| 宣告 | 參數名 = fixture 名 | 解構 `{ seedProduct }` |
| teardown | yield 之後 | `await use(x)` 之後 |
| 查找 | conftest 逐層往外 | 匯入哪個 test 就用哪套 |

時機：helpers 被五個檔案 import 時升級成 fixture。
**helpers 是函式庫，fixtures 是能自動管理生命週期的設備清單。**

---

## 12. config 與環境變數

### `use` 不是語法要求，是 fixtures 的設定面板（作用域容器）

```ts
export default defineConfig({
  use: { baseURL: 'http://localhost:5173', trace: 'retain-on-failure' },  // 全域
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], storageState: '...' } },  // 蓋全域
  ],
});
```

判準：「設定測試流程」（timeout、retries）寫外面；「設定設備」（baseURL、storageState、viewport）進 `use`。

### env 三層注入

```ts
// ① process.env 直接讀
retries: process.env.CI ? 2 : 0,
baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',

// ② .env 檔（新版本 Playwright 原生支援 loadEnv）

// ③ 測試內 skipif 同款
test.skip(!process.env.DEPLOY_BASE_URL, 'deployment-only');
```

判準：**會隨環境變的 → env；所有環境都一樣的 → config 寫死。**

安全：secrets 不進 `.env`（防 commit）；CI 用 GitHub Secrets 注入；
config 印出關鍵非敏感 env 值，避免測試默默打到別的環境。

---

## 13. 測試分層與白箱/黑箱界線

e2e 裡用 API 斷言驗後端狀態**不算白箱**——打的是 HTTP API，和前端同一扇門。

```
白箱                灰箱                    黑箱
─────               ─────                   ─────
import app 直接呼叫   透過 HTTP，但偷看狀態     只看使用者的畫面
(pytest 單元測試)    (Playwright + API 斷言)  (純 UI 斷言)
```

混合寫法（操作走 UI，驗證先 API 後 UI）能直接定位 bug 在前端還是後端：

```ts
await page.getByRole('button', { name: 'Add to cart' }).click();

const cart = await (await page.request.get('/cart')).json();
expect(cart.items).toHaveLength(1);        // 掛這裡 → 後端問題
await expect(page.getByText(productName)).toBeVisible();  // 過了才掛 → 前端問題
```

紅線：**別讓驗證全部退化成 API 斷言**——使用者看得到的東西才是 e2e 的存在理由。

三層分工：

| 層 | 工具 | 測什麼 |
|---|---|---|
| 使用者旅程 | `page` + getByRole | 點了 Add to cart，購物車頁看得到 |
| 中間態驗證 | `page.request` | 伺服器視角：車裡到底有沒有商品 |
| 後端契約 | `request` fixture | /health、權限、409、422 邊界 |

（pytest 測商業邏輯/狀態機/outbox；Playwright request 補的是
「部署後整條鏈子」：路由、proxy 前綴、cookie 屬性、同源。）

---

## 14. 五條軍規

1. **永不 `waitForTimeout`** — 等「狀態」，不等「時間」。
2. **role-first 選擇器** — 找不到通常是 UI 的 a11y bug，順便修掉。
3. **斷言吸收延遲** — 操作後第一行寫 `await expect`；多 actor 就每個 actor 各寫。
4. **資料自足** — 每條測試自己造資料（unique email / API seeding），不依賴測試順序。
5. **UI 只測旅程，API 造萬物** — signup 用 UI 測一次；
   之後要登入的測試用 storageState（setup project）+ `page.request` 造資料。

> 收尾：Playwright 的 flaky 十之八九不是工具問題，是測試在等錯東西。
> 把「等什麼」寫清楚，它就比任何人都穩。
