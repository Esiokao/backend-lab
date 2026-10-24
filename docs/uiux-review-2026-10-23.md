# UI/UX 審查報告 — Backend Lab（2026-10-23）

> 審查方式：以瀏覽器實際走訪 `http://localhost:5173/`（訪客 / 一般 user `a@a.com` / admin `user@dev.com`），
> 桌機 1280×720 與手機 390×844，並對照 `docs/PRD.md` v1.4 與前端原始碼定位根因。
> 本文只記錄問題與建議，未修改任何程式碼。

## ✅ 修復狀態（2026-10-24 更新）

**已修復並驗證**（vue-tsc build 通過、後端 202 tests 全綠、瀏覽器實測通過）：

| 項目 | 修法 | 驗證 |
|---|---|---|
| P0-1/2 卡片溢出 | `.product-media img` 改 `position:absolute; inset:0`（design.css） | img 169px、foot 幾何正確、admin Edit 按鈕 hit-test 命中 |
| P0-3 user filter TypeError | input 改 `type="text" inputmode="numeric"` + `@change`（AdminOrdersView） | 過濾 user 11 → 1 筆（#57）、無錯誤 |
| P1-4 View all orders 連結 | `to` 補上 `:` 綁定（DashboardView） | href = `/app/orders` |
| P1-5 Total orders 假數 | fetch 帶 `page_size=100`；假卡加「Demo data」標註；Last updated 真時間戳 | Total orders 顯示真實 13 |
| P1-6 頭像直接登出 | 加 `window.confirm` 確認 | confirm 對話框出現、接受後回 /login |
| P1-7 無回店面入口 | sidebar 新增 Storefront 項目；brand 與麵包屑「Backend Lab」可點 | 導覽首項 Storefront、href=/ |
| P1-8 通知面板跨頁不關 | route change 時收起面板（ShellLayout） | 切頁後面板自動關閉 |
| P1-9 非法狀態轉移 | 前端鏡像 `ALLOWED_TRANSITIONS`，非法選項 disable | created 只剩 pending/cancelled 可選 |
| P1-10 訂單欄位過少 | OrdersView 加 Items / Total / Status / Created 欄；移除死的 Open 箭頭 | 列顯示 `a × 2`、`$200.00`、徽章、日期 |
| P1-11 列表排序 | 後端 `GET /users` 加 `ORDER BY id`（已重建 api/worker 容器） | API 回 [1,3,5,6,7,8,9,11] |
| P1-12 庫存錯誤文案 | qty max=min(stock,100)、客端先擋、409 轉商品名 | toast `Only 10 left in stock for "b".` |
| P1-13 手機版 | `.mobile-nav` 選擇器改 `a`（原樣式寫給 button 但標記是 link）、按鈕 nowrap、`.sr-only` 補座標錨定（修水平溢出） | nav 有樣式、文件無水平捲軸 |
| P1-14 登入後文案 | 店面副標依登入狀態分流 | 登入後顯示 workspace 文案 |
| P2-17/18/22 | follow toast 依庫存分流、搜尋/過濾支援 blur、New product stock 改 placeholder | 瀏覽器實測 |
| P2-23 PRD 漂移 | PRD 升 v1.5：狀態機、items 契約、notification body、mark_all_read、products 公開、admin orders 契約 | 文件同步 |

**未修（需產品/後端決策，不在本次範圍）**：

- P1-15 Follow 狀態重整消失 —— 需後端補「查詢我是否已關注」端點（列表帶 `following` 欄位最省）。
- P1-11 刪除使用者 UI —— 後端沒有 `DELETE /admin/users/{id}` 端點，屬功能開發。
- P2-16 通知中文 seed 文案 —— 資料清理。
- P2-19 Environment 假下拉、「All systems operational」寫死 pill —— 設計去留待定。
- P2-20 店面分頁無總數 —— 需後端 products 回 total。
- P2-21 訂單當頁搜尋 —— PRD 明載的行為，改 server-side 需契約調整。
- P2-24 孤兒通知 —— 刪除策略待定。

## 📦 追加需求（2026-10-24，依使用者預期同步實作）

| 需求 | 實作 | 驗證 |
|---|---|---|
| 訂單可點入詳情 | `/app/orders/:id` 新頁面；`GET /orders/{id}` 放寬為擁有者或 admin；Orders / Dashboard / Admin user detail 的訂單 ID 都可點 | admin 與本人詳情正常；他人訂單 404 畫面 |
| 使用者可點入詳情 | `/admin/users/:id` 新頁面 + 新端點 `GET /admin/users/{id}`（user + orders[]）；Admin orders / Admin users / Dashboard 的使用者皆可點 | a@a.com 詳情顯示 profile + 訂單歷史 |
| Admin 通知管理 | `/admin/notifications` 頁：定向發送（Outbox → worker 異步）、廣播發布/刪除、歷史表；鈴鐺面板分 **General / Broadcast 兩個可切換分頁**（各帶筆數徽章；Mark all read 僅作用於 General） | admin 發定向給 a@a.com → worker 投遞 → General 分頁 +1；廣播全角色可見於 Broadcast 分頁 |
| Overview 真數據 | 新端點 `GET /stats`（admin 全站 / user 個人範圍）；四張卡全接真資料（users/orders/orders today/DB readiness 探測），假 hero 數字全數移除 | admin 8 users / 13 orders / 9 ms 探測；user 個人卡與鈴鐺徽章一致 |

新增測試 12 條（訂單詳情權限 5、admin user detail 4、stats 3），全套 214 passed。

**追加（同日第二批）**：訂單詳情頁新增下單者 **user info 區塊**（頭像／姓名／email／角色徽章／id 代碼；admin 可點姓名進使用者詳情，一般使用者顯示自己）；`/app/orders` 的 User 欄從 `usr_XXXX` 代碼改為顯示**姓名**（一般使用者取 session 自己的名字，admin 以 `GET /users` 對照全部）；User 欄（admin 視角）為可點連結。

**追加（同日第三批：UI 分角色 + 會員中心）**：

| 需求 | 實作 | 驗證 |
|---|---|---|
| UI 分 admin / user | Workspace（Overview、API Health、側欄 Workspace 區）僅 admin 可見；一般使用者側欄變 **Member** 區（My Orders / Account），守衛把非 admin 一律導回 `/app/account` | a@a.com 直訪 dashboard/api-health → 落在 /app/account |
| 頭像下拉選單（會員資料 list） | 右上角頭像展開：問候語「Hi, {name}!」+ My orders / Account settings / Change password + Sign out（admin 額外 Administration 快捷區）；點外部或切頁自動收起 | 兩種角色的選單項目實測正確 |
| 會員資料修改 | 新頁 `/app/account`：資料卡 + name/email 表單（PATCH /users/{id} 本人），儲存後側欄/下拉即時同步 | 改名 a→a2→a，sidebar 與下拉即時更新 |
| 修改密碼 | `/app/account` 密碼表單（8–128 字元 + 確認欄）；PATCH 帶 password → 後端撤銷全部 session → 自動登出回 /login | 改密碼後自動登出；admin API 重置後新密碼登入驗證 |

---

## P0 — 功能實際壞掉（面試 demo 前必修）

### 1. 商品卡片的名稱／價格／庫存全部被圖片蓋住（你看到的「price 跟 qty 不見了」）
- **現象**：所有商品卡只看得到圖片；商品名、描述、`In stock · N`、`$xx.xx` 在 DOM 裡存在（截圖工具/aria tree 看得到文字、座標正確、顏色正常），但畫面上被圖片蓋住，滑鼠也點不到下方任何東西。
- **根因**（`frontend/src/assets/design.css:154-157`）：
  - `.product-media` 是 `display: grid; place-items: center; height: 170px; position: relative`。
  - `.product-media img` 設 `width:100%; height:100%`，但 grid 的 implicit row 是 auto 高度，百分比高度循環解析 → 回退成「依內容（寬度×比例）」，圖片算出 **282.5px 高**（卡片寬 282.5px，圖 240×240 等比放大），溢出 170px 的媒體區。
  - `.product-media` 因為 `position: relative`，整層疊在後面非定位的 `.product-foot` 之上 → 文字被蓋住；同時 hit-test 停在 `<img>`，下方元素滑鼠點不到。
- **建議修法**（擇一）：img 改 `position:absolute; inset:0` 並在 `.product-media` 加 `overflow:hidden`；或 grid 改 `align-items: stretch`／img 高度用 `object-fit: cover` 配固定容器 + `min-height: 0`。
- **影響**：訪客、一般 user、admin 三種角色全部受影響；手機版（單欄 358px 寬卡）圖片溢出更誇張。

### 2. Admin 的商品管理按鈕（Edit / Archive / Delete）被同一個 bug 蓋住 → 完全點不到
- **現象**：DOM 裡有 `Edit`、`Archive`、`Delete a` 按鈕（`.product-admin-row`，位於 y≈515），但 `elementFromPoint` 回傳 `IMG` —— 按鈕被溢出圖片蓋住，**滑鼠無法點擊**。截圖上完全看不到。
- **後果**：admin 對「現有商品」什麼都不能做（只剩頁首的 New product / Archived 可用），等於：
  - 無法改庫存 → **F12-5 到貨通知（0→>0 補庫存）的流程在 UI 上根本無法演示**（E2E-21 做不了）；
  - 無法 archive、無法刪除商品（F12-1 的 U/D 缺一半）。
- **修好 #1 即可一併解決**；另外建議 admin 控件不要疊在圖片下方，改成卡片右上 icon 或 hover 浮層，避免再被媒體區蓋住。

### 3. Admin 訂單頁「Filter by user ID」過濾器完全壞掉（靜默 JS 錯誤）
- **現象**：輸入 `11` 按 Enter，表格不變、無 toast、無任何反應。console 出現
  `Uncaught TypeError: userIdFilter.value.trim is not a function`。
- **根因**（`frontend/src/views/AdminOrdersView.vue:99` 與 `:66`）：`<input v-model="userIdFilter" type="number">` —— Vue 對 `type=number` 的 v-model 會把值轉成 **number**，對 number 呼叫 `.trim()` 直接拋 TypeError。`applyFilters()` 在驗證前就炸，`loadOrders()`（`:66`）也一樣，所以**打過濾條件後翻頁也會炸**（watch page → loadOrders）。
- **建議**：input 改 `type="text" inputmode="numeric"`，或 v-model 修飾子／改用字串 state；錯誤也應顯示 toast 而非静默。
- **附帶 UX**：此過濾器要求輸入「數字 user id」，對 admin 不友善 —— 應支援 name/email 搜尋。

---

## P1 — 明顯 UX / 正確性問題

### 4. 儀表板「View all orders」連結是壞的
`DashboardView.vue:86`：`<router-link to="{ name: 'orders' }">` 少了 `:`，傳成**字串** `"/app/{ name: 'orders' }"` → 撞 catch-all 被導回店面。實測該連結 href 就是字面量。（同檔 row 內的 `:to="{ name: 'orders' }"` 是對的。）

### 5. 儀表板 metric 卡全是假數據，且「Total orders」是錯的
- `Total users 2,849`、`+12.4%`、`312 joined this month`、`API uptime 99.99%`、`24 ms`、`Database Connected` 全部寫死（`DashboardView.vue:48-76`，註解自承「裝飾數字」）。
- `Total orders` 標注「Live from the API」但：fetch `/orders` **不帶 page_size**（後端預設 10）→ admin 實際 13 筆卻顯示「10」；一般 user 又只算自己的。數字錯、語意混亂。
- 面試 demo 場景，面試官一定會戳這幾張卡。建議：要嘛接 `GET /stats`（roadmap P2），要嘛改文案明示 placeholder。

### 6. 帳戶功能 = 只能登出，沒有任何 settings/profile UI
- sidebar 底部的頭像/姓名區是一顆**點了立刻登出**的按鈕（`ShellLayout.vue:120`），無確認、無選單，誤觸就登出。
- 全站沒有 profile／settings 頁：改名字、改 email、**改密碼（F7）都沒有 UI**（PRD 也列為 P2 待做）。你說「設定 UX 很差」的根源大概就是這裡 —— 根本沒有設定，唯一入口還是個危險的登出鈕。
- 建議：頭像 → 下拉選單（Profile / Settings / Sign out），登出加確認或至少與導覽分離。

### 7. 工作區沒有回店面的連結
`ShellLayout` 的 brand「Backend Lab」不可點，sidebar 也沒有 Storefront/Catalog 項目。從 `/app/*`、`/admin/*` 想回商品頁只能改網址或瀏覽器返回。麵包屑的「Backend Lab」同樣不可點。

### 8. 通知面板跨頁不關
`panelOpen` 是 store 全域狀態，切換路由後面板還開著，蓋住新頁面內容（實測 Overview → Orders 仍開）。應在 route change 時關閉，或點外部即關。

### 9. Admin 狀態下拉允許選非法轉移
每列下拉列出全部 5 個狀態、只 disable 當前值，但後端狀態機只允許特定轉移（`app/core/enums.py` 的 `ALLOWED_TRANSITIONS`）。例如 `created` 可選 `processing`（非法，會 409）。應該只 enable 合法的下一狀態，把錯誤擋在互動層，而不是事後 toast。（合法轉移本身測過 OK。）

### 10. 訂單列表資訊太少、沒有詳情頁
- 一般 user 的訂單列只有 `#57` 和 `usr_0011`：**沒有商品、數量、金額、狀態、建立時間**；看「自己的 user_id」欄位沒有意義。
- 「Open」箭頭的 aria-label 是 `Open order 57`，點了只是跳到同一個列表（沒有訂單詳情頁；`GET /orders/{id}` 後端有、前端沒接）。對使用者來說下完單看不到自己買了什麼 —— 對電商 demo 是很致命的敘事缺口。
- admin 的 Order Management 同樣看不到訂單明細（items/金額），只有 id/user/status。

### 11. Admin 使用者管理：沒有刪除、列表沒有排序
- `AdminUsersView` 只有 Edit（name/email/role），**沒有 Delete**（PRD F9-4、後端 `DELETE /admin/users/{id}` 在契約內）。
- 後端 `GET /users`（`app/routers/users.py:45`）`select(User)` **無 ORDER BY** → 列表順序隨機（實測 3,5,7,6,1…）。加上排序或 id 欄排序控制。

### 12. 下單的錯誤處理直接吐原始後端訊息
- 庫存不足時 toast：`Create failed: Insufficient product stock: 2` —— 暴露內部 product_id、沒有商品名，使用者不知道是哪個商品、還剩多少。
- 數量上限是寫死的 `1–100`，**與庫存無關**：stock 10 可以填 100，送出才被後端 409。前端可在 picker 上標 max=stock、送出前擋。
- 數量輸入無 `max` 屬性，靠送出後 toast 才知道錯。

### 13. 手機版（390×844）問題
- **mobile nav 完全沒吃樣式**：預設藍色底線連結（1990 年代風），且水平溢出出現橫向捲軸（`ShellLayout.vue:182-199` 的 `.mobile-nav`）。
- 店面卡片在窄版變成「一整面圖片」（同 P0-1 溢出）。
- 按鈕文字換行擠爛：「Sign out」「New product」斷成兩行（header 按鈕缺 `white-space: nowrap`）。

### 14. 登入後文案未更新
登入後（含 admin）店面副標仍顯示「**Sign in to** follow restock alerts or place orders.」—— 對已登入者是錯的引導。

### 15. Follow 狀態重整即消失（已知限制，但對使用者無聲）
`StorefrontView.vue` 註解自承：後端沒有「查我是否已關注」端點，星星是 session 內樂觀 UI。使用者重整後星星熄滅，不知道自己的關注其實還在（後端有記）。建議後端補 `GET /products/{id}/follow` 或列表帶 `following` 欄位；至少在 UI 標示「未同步」。

---

## P2 — 小問題 / 一致性 / 文案

16. **通知內容中英混雜**：UI 全英文，通知卻是「訂單已建立／恭喜你 被通知到了」（worker 與 seed 的文案）；「test」「恭喜你 被通知到了」這種 seed 在 demo 裡觀感差。建議統一語言、清 seed。
17. **Follow toast 文案誤導**：商品還有庫存也說「we'll notify you when it's back in stock」—— 只有 0→>0 才會通知。有庫存時應說不同文案。
18. **搜尋/過濾只認 Enter**：店面商品搜尋、admin user filter 都是 `@keydown.enter`，沒有按鈕、blur 也不觸發；輸入完點別處 = 沒反應。建議加 `@change` 或搜尋按鈕。
19. **死的裝飾控件**：sidebar「Environment: Production」下拉無任何行為；topbar「All systems operational」綠 pill 寫死（API 掛了也會說 operational）；Dashboard「Last updated just now」是靜態字。面試被點到會尷尬，建議接真資料或拿掉。
20. **店面分頁資訊弱**：只顯示「Page 1」、無總數；`hasMore` 用「回滿頁」推測 —— 商品數剛好是 12 的倍數時會多出一個可翻的空頁。
21. **Orders 搜尋是當頁客戶端過濾**（PRD 有明載，但使用者易誤以為全庫搜尋）——建議 server-side 或加「僅過濾當頁」提示。
22. **New product 表單**：Stock 預填 `"0"`（其他欄位是 placeholder），不一致且容易不小心建出零庫存商品；建議統一 placeholder。
23. **PRD 與實作漂移**（面試前建議同步）：
    - 狀態機：PRD F8 寫 `pending → processing → shipped`；實作是 `created → pending → processing → completed`（+cancelled），`enums.py` 是真相來源。
    - Notification 欄位：PRD §5.3 寫 `message`，前後端實作都是 `body`。
    - 全部已讀：PRD 寫 `POST /notifications/read-all`，實作是 `PATCH /notifications/mark_all_read`（前後端一致）。
    - F3 內有兩條矛盾的 v1.1 語意變更（一條「已實作」一條「待實作」）。
    - Admin orders 契約：PRD 寫 items 含 `user:{name,email}`；實作 items 只回 `user_id`，前端另外用 `GET /users` 對照。
24. **孤兒通知**：訂單刪除後，其「訂單已建立」通知仍在（實測 a@a.com 收過 #24–#44 的通知、那些訂單已不存在）。通知本來就可能引用已刪實體，建議文案帶不掉的資訊或點擊時容錯。
25. 正面觀察（保持下去）：登入錯誤不洩露帳號存在、未登入守衛 `?redirect=` 正常、登入限流、通知徽章 10s 輪詢正常、商品骨架屏與圖片 fallback、下單後庫存即時更新、admin 批次刪除/restore 有 confirm。

---

## 修復優先序建議

| 順序 | 項目 | 為什麼 |
|---|---|---|
| 1 | P0-1/2 卡片溢出（一個 CSS fix 解兩個 P0） | 首頁第一眼就壞；admin 商品管理全殘 |
| 2 | P0-3 user filter TypeError | 靜默壞掉，面試 demo 一用就穿幫 |
| 3 | P1-4 View all orders 連結 | 一行 fix |
| 4 | P1-5/19 假數據處理 | 面試官必戳 |
| 5 | P1-6 頭像登出 + settings 缺口 | 你點名的「設定 UX」 |
| 6 | P1-7/8 導覽與面板行為 | 日常使用卡卡的要因 |
| 7 | 其餘 P1/P2 | 依 demo 腳本需要 |
