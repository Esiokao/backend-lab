# Backend Lab — 產品需求文件（PRD）

> 版本：1.0　|　狀態：Active　|　用途：面試 Demo 的產品規格、E2E 測試依據、後端功能藍圖

---

## 1. 產品概述

**Backend Lab** 是一個展示全棧工程能力的面試 Demo：一個帶完整認證體系、背景任務、CI/CD 的 API 服務，配上 Vue 3 管理後台。

### 1.1 技術棧

| 層 | 技術 |
|---|---|
| 後端 | FastAPI、SQLAlchemy、Alembic、PostgreSQL、Redis（rate limit + session store）、RQ（背景任務）|
| 前端 | Vue 3 + TypeScript、Vite、vue-router 4、pnpm、純 CSS 設計系統 |
| 測試 | pytest（單元 + 整合，52+ 案例）|
| 基礎設施 | Docker Compose、nginx（TLS）、GitHub Actions（CI：test-build-publish → GHCR；CD：deploy-to-production + 部署後 smoke test）|
| 認證 | Session cookie（HttpOnly、Secure、SameSite=strict、7 天滑動過期、真登出、改密碼全裝置撤銷）|

### 1.2 面試展示亮點

1. 安全的 session 認證（vs 常見的 localStorage JWT 反模式）—— 可講述「為什麼」
2. 真實的登出與撤銷（JWT 做不到的事）
3. RQ 背景任務管線（訂單建立 → 通知 worker）
4. CI/CD：測試 → 建置 → GHCR → SSH 部署 → 部署後驗證
5. 測試文化：單元/整合/部署三層 + 本 PRD 驅動的 E2E

---

## 2. 角色與權限

| 角色 | 定義 | 能做什麼 |
|---|---|---|
| Visitor | 未登入 | 註冊、登入；不得存取任何業務資料 |
| User | 已註冊並登入 | 看儀表板、建訂單、看自己的訂單、改自己資料 |
| Admin | `role = "admin"` 的 User | 額外：看所有使用者與其訂單統計（`/users-with-orders`）|

**目標權限矩陣**（現狀見 §5 已知問題）：

| 端點 | Visitor | User | Admin |
|---|---|---|---|
| `POST /users`（註冊）| ✅ | ✅ | ✅ |
| `POST /login` / `POST /logout` | ✅ | ✅ | ✅ |
| `GET /users/me` | ❌ 401 | ✅ | ✅ |
| `GET /orders` | ❌ 401 | ✅ | ✅ |
| `POST /orders` | ❌ 401 | ✅ | ✅ |
| `GET /users`（列表）| ❌ 401 | ❌ 403 | ✅ |
| `PUT/PATCH/DELETE /users/{id}` | ❌ 401 | 僅自己 | ✅ 任何人 |
| `GET /users-with-orders` | ❌ 401 | ❌ 403 | ✅ |

---

## 3. 前端頁面與路由

| 路由 | 頁面 | 認證 | 對應後端 |
|---|---|---|---|
| `/login` | 登入頁 | guestOnly | `POST /login` |
| `/`（Overview）| 儀表板：metric 卡 + 最近訂單 | requiresAuth | `GET /orders` |
| `/orders` | 訂單列表：分頁/排序/搜尋/新增 | requiresAuth | `GET/POST /orders` |
| `/users` | 使用者列表 | requiresAuth | `GET /users` |
| `/api-health` | API 健康監控（10 秒輪詢）| requiresAuth | `GET /health`、`GET /ready` |

守衛行為：未登入訪問受保護頁 → `302 /login?redirect=<原路徑>`；登入後回到原路徑。已登入訪問 `/login` → 送回 `/`。

---

## 4. 功能需求與驗收標準

### F1 註冊
- **描述**：訪客以 email + 密碼建立帳號（`POST /users`，目前無前端頁面，API 直呼）。
- **驗收**：
  - Given 未存在的 email，When 註冊（name/email/password ≥ 8 字元），Then 200 回傳 User 且可登入
  - Given 已存在的 email，Then 409

### F2 登入 / 登出
- **驗收（F2-1 登入成功）**：Given 已註冊使用者，When 在 `/login` 輸入正確帳密，Then 進入 `/` 且 sidebar 顯示其姓名
- **驗收（F2-2 登入失敗）**：Given 錯誤密碼，Then 顯示 "Invalid email or password"（不洩露帳號是否存在）；連續 6 次觸發 429
- **驗收（F2-3 未登入保護）**：Given 未登入，When 直訪 `/orders`，Then 被 redirect 到 `/login?redirect=/orders`，登入後回到 `/orders`
- **驗收（F2-4 登出）**：Given 已登入，When 點 profile 登出，Then 回 `/login`；同 session cookie 再打 API → 401
- **驗收（F2-5 已登入訪問 /login）**：Then redirect 回 `/`

### F3 訂單列表
- **描述**：`GET /orders` 資料，伺服器端分頁（page_size=10）、id 排序切換、當頁搜尋。
- **驗收（F3-1 分頁）**：Given 超過 10 筆訂單，When 開 `/orders`，Then 顯示第 1 頁 10 筆；Next 可翻頁；最後一頁 Next disabled
- **驗收（F3-2 排序）**：When 切換 Order ID Newest/Oldest，Then 首筆 id 為最大/最小
- **驗收（F3-3 搜尋）**：When 輸入存在的 id，Then 表格只剩匹配列；無匹配顯示空狀態
- **附註**：目前僅能顯示 `id` / `user_id`；customer 名稱與 email 需後端 JOIN（見 §8）

### F4 建立訂單
- **驗收（F4-1）**：Given 已登入，When 點 New order，Then `POST /orders` 成功、toast 顯示 "Order #N created"、列表首列出現新訂單
- **驗收（F4-2）**：新訂單的 `user_id` = 當前登入者（後端由 session 決定）

### F5 使用者列表
- **驗收（F5-1）**：Given 已登入，When 開 `/users`，Then 顯示所有使用者（avatar 縮寫、name、email、id code chip）
- **附註**：目標權限矩陣此頁應限 Admin（現狀任何登入者可見）

### F6 API 健康監控
- **驗收（F6-1）**：Given 後端正常，When 開 `/api-health`，Then Liveness 與 Readiness 顯示綠色 Operational、顯示最後檢查時間
- **驗收（F6-2）**：Given 10 秒過後，Then 自動刷新時間戳
- **驗收（F6-3）**：Given 後端停止，Then 顯示紅色 Down（不白屏）

### F7 改密碼撤銷全部 session
- **描述**：`PATCH /users/{id}` 帶 `password`（8–128 字元）→ commit 成功後撤銷該使用者所有 session。
- **驗收（F7-1）**：Given 使用者在兩台裝置登入，When 裝置 A 改密碼，Then 裝置 B 的下一個請求 401
- **驗收（F7-2）**：Given PATCH 帶錯誤內容失敗，Then 不撤銷任何 session
- **驗收（F7-3）**：Given PATCH 只改 name，Then session 保持有效
- **附註**：目前無前端 UI（API 直呼）；安全上還應要求輸入「目前密碼」—— 見 §8

---

## 5. API 契約

Base URL：開發 `http://localhost:8000`（前端經 Vite proxy `/api` 前綴）；認證走 session cookie（`credentials: include`）。

**通用行為**：JSON in/out；錯誤格式 `{"detail": "..."}`；401=未認證、403=無權限、409=衝突、429=限流。

### 5.1 現有端點

| # | Method | Path | 認證（現狀）| 請求 | 成功回應 | 錯誤 |
|---|---|---|---|---|---|---|
| 1 | POST | `/users` | 公開 | `{name, email, password}` | 200 `User{id,name,email}` | 409 email 重複 |
| 2 | POST | `/login` | 公開（限流 5/60s、body ≤100KB）| `{email, password}` | 200 `{access_token, token_type}` **＋ Set-Cookie session** | 401 帳密錯、429 |
| 3 | POST | `/logout` | 公開（無 cookie 也可）| — | 200 `{status:"ok"}`，cookie 清除 | — |
| 4 | GET | `/users/me` | 🔒 session/Bearer | — | 200 `User` | 401 |
| 5 | GET | `/users` | ⚠️ 公開（應限 Admin）| — | 200 `User[]` | — |
| 6 | GET | `/users/{id}` | ⚠️ 公開（應要求登入）| — | 200 `User` | 404 |
| 7 | PUT | `/users/{id}` | ⚠️ **公開（嚴重：無認證）** | `{name, email}` | 200 `User` | 409 |
| 8 | PATCH | `/users/{id}` | ⚠️ **公開（嚴重：無認證）** | `{name?, email?, password?}` | 200 `User`（帶 password 時撤銷全部 session）| 400 無欄位、409 |
| 9 | DELETE | `/users/{id}` | ⚠️ **公開（嚴重：無認證）** | — | 200 `{message}` | 404、409 有訂單 |
| 10 | POST | `/orders` | 🔒 session | `{}`（空）| 200 `Order{id,user_id}` | 401 |
| 11 | GET | `/orders` | ⚠️ 公開（應要求登入）| query：`page≥1`、`page_size≤100`、`user_id`、`sort_by=id\|user_id`、`order=asc\|desc` | 200 `Order[]` | 422 參數錯 |
| 12 | GET | `/orders/{id}` | 🔒 僅訂單擁有者 | — | 200 `Order` | 401、404 |
| 13 | GET | `/users/{id}/orders` | 🔒 僅本人 | — | 200 `Order[]` | 401、403 |
| 14 | GET | `/users-with-orders` | 🔒 admin | — | 200 `{users:[{name, order_count}]}` | 401、403 |
| 15 | GET | `/health`、`/ready` | 公開 | — | 200 `{status:"ok"}`（ready 503 當 DB 斷線）| 503 |

### 5.2 已知問題（修復提案，見 §8）

- **SEC-1（嚴重）**：#7/#8/#9 無認證 —— 任何人可改/刪任何使用者（含改 admin 密碼）
- **SEC-2（中）**：#5/#6/#11 公開暴露全部使用者與訂單資料
- **SEC-3（低）**：#8 改密碼不要求驗證「目前密碼」
- **GAP-1**：#11 不回傳訂單擁有者姓名/email、無總數（前端分頁無法顯示 N of M）

### 5.3 規劃中的端點（後端功能藍圖）

| 提案 | 規格草案 | 對應 PRD 需求 |
|---|---|---|
| SEC 修復 | #7/#8/#9 加 `get_current_user` + 「僅本人或 admin」；#5 加 admin；#6/#11 加登入 | §2 矩陣 |
| `GET /orders` 強化 | 每筆附加 `user: {name, email}`（JOIN）；回應包裝 `{items, total, page, page_size}` | F3 分頁顯示 "X of N" |
| `GET /orders/{id}` 詳情 | 已存在但缺前端詳情頁 | 訂單詳情頁 |
| `DELETE /orders/{id}` | 僅擁有者或 admin | 訂單管理 |
| `GET /stats` | `{total_users, total_orders, orders_today}`（Redis 快取 60s）| Dashboard 真實 metric 卡 |
| 改密碼驗證舊密碼 | PATCH 帶 password 時要求 `current_password` 欄位 | F7 安全強化 |

---

## 6. E2E 測試指南（給撰寫者）

### 6.1 建議配置

- 工具：Playwright（TS），放在 `frontend/e2e/` 或 `tests/e2e/`（與 pytest 分離）
- `baseURL: http://localhost:5173`；webServer 啟動 `pnpm dev`；後端起 docker compose（api+postgres+redis）
- 認證：兩個 storageState —— `user.json`（一般帳號）、`admin.json`（admin 帳號），`test.use({ storageState })` 分組
- 測試資料：seed 腳本先經 API 建立 `admin@lab.test` / `user@lab.test`（密碼 `testpassword`）+ 15 筆訂單（觸發分頁）
- 隔離：每測試建立獨立資料（uuid email），避免互相汙染；或平行 worker 各自建帳號

### 6.2 案例清單（對應 §4 驗收標準）

| ID | 案例 | 關鍵斷言 |
|---|---|---|
| E2E-01 | 登入成功 | URL=/、sidebar 顯示姓名 |
| E2E-02 | 登入失敗 | 錯誤訊息可見、仍在 /login |
| E2E-03 | 未登入保護 | 直訪 /orders → /login?redirect=/orders；登入後回 /orders |
| E2E-04 | guestOnly | 登入狀態訪 /login → 回 / |
| E2E-05 | 登出 | 回 /login；reload 後仍需登入 |
| E2E-06 | 訂單分頁 | 10 筆/頁；Next/Previous；末頁 Next disabled |
| E2E-07 | 排序切換 | 首列 id = 頁內最大/最小 |
| E2E-08 | 搜尋 | 輸入 id → 列表過濾；亂數 → 空狀態文字 |
| E2E-09 | 建立訂單 | toast 出現；第一列 id 遞增；reload 後仍在 |
| E2E-10 | 改密碼撤銷 | 兩個 browser context：A 改密碼，B 下請求 401 |
| E2E-11 | 使用者列表 | 列表含 seed 帳號 name/email |
| E2E-12 | 健康頁 | 兩張卡 Operational；時間戳在 10 秒內變化 |
| E2E-13 | 限流 | 連續 6 次錯誤登入 → 429 訊息 |

### 6.3 建議的 selector 策略

- 優先 `getByRole` / `getByLabel`（模板已加 aria-label：搜尋框、row action、toast dismiss）
- 資料行用 `getByRole("row")` + 文字定位（`#1048`、`usr_0024`）

---

## 7. 非功能需求

- **安全**：session cookie 屬性（HttpOnly/Secure/SameSite=strict/Path=/）；登入限流 5 次/60 秒（Redis Lua 原子化）；請求大小限制（login 100KB）；TLS 由 nginx 終結 + HTTP→HTTPS 301 + HSTS
- **效能**：session 驗證 = 1 次 Redis GET + EXPIRE；滑動過期 7 天閒置失效
- **可靠**：改密碼撤銷在 commit 之後執行（失敗不誤殺）；部署後 smoke test 把關
- **CI/CD**：push → Test/Build/Publish（pytest 52+ → docker build → GHCR）→ Deploy to Production（SSH/Tailscale + smoke test）

---

## 8. 路線圖（優先序）

| 優先 | 項目 | 類型 |
|---|---|---|
| P0 | SEC-1/2/3 修復（users 端點認證 + 權限矩陣落地）| 後端 |
| P0 | E2E 測試套件（§6 案例）| 測試 |
| P1 | `GET /orders` 強化（JOIN + 總數包裝）→ 前端分頁顯示 X of N | 後端+前端 |
| P1 | 訂單詳情頁（`GET /orders/{id}` 已存在）| 前端 |
| P2 | `GET /stats` + Dashboard metric 卡接真資料 | 後端+前端 |
| P2 | 註冊頁 UI（F1 目前只有 API）| 前端 |
| P2 | 改密碼 UI（含 current_password 驗證）| 前端+後端 |
| P3 | `DELETE /orders`、RQ 任務監控頁、i18n | 待討論 |

---

## 9. Demo 腳本建議（面試用）

1. **開場**：GitHub Actions 綠燈 → GHCR image → 部署腳本（CI/CD 一條龍 30 秒講完）
2. **安全深談**：開 DevTools 展示「登入後 JS 拿不到任何 token」（document.cookie 為空）→ 講 session vs JWT 決策
3. **功能流**：登入 → 建訂單（toast）→ 訂單列表 → 開第二個瀏覽器改密碼 → 第一個瀏覽器當場 401（撤銷的活演示，最有記憶點）
4. **測試**：pytest 三層 + 本 PRD 的 E2E
5. **彩蛋**：兩個 AI agent（coder/reviewer）在 Herdr 裡的協作流水線

---

*維護規則：任何功能變更須同步更新 §4/§5；E2E 案例與 §6 對照。*
