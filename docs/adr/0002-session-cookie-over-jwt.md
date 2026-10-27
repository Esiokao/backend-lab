# 0002 — 網頁認證採伺服器端 Cookie Session，不採用 JWT 作為主要機制

- **日期**：2026-10-26
- **狀態**：Accepted
- **決策者**：backend-lab 團隊
- **相關**：[0001 — 同源閘道](./0001-same-origin-gateway-over-api-subdomain.md)

## 背景

認證需要在兩種主流機制中選擇：

1. **伺服器端 Cookie Session**：登入後發一組不透明亂數 id（cookie 載具），狀態存伺服器（Redis）。
2. **JWT（Bearer Token）**：簽名過的自帶資料票券，客戶端保管，伺服器無狀態驗證。

產品的硬性需求：**登出與「改密碼撤銷所有裝置」必須立即生效**（這是 demo 的核心安全敘事）。客戶端目前只有瀏覽器 SPA；Redis 已是架構核心（限流、佇列、訪客計數）。

## 決策

採用**伺服器端 Cookie Session**，實作於 `app/core/session.py`：

- 不透明亂數 sid（`secrets.token_urlsafe(32)`，128-bit entropy）為 cookie 載具，`HttpOnly` + `Secure` + `SameSite=strict` + host-only。
- Redis 存 `session:{sid} → user_id`（滑動過期 7 天），並以 `user:{uid}:sessions` 集合作為**該使用者所有 sid 的索引** — 供「撤銷全部裝置」使用。
- JWT 僅保留為**過渡期相容路徑**：`app/core/dependencies.py` 的 `get_current_user()` 同時接受 cookie（瀏覽器，優先）與 Bearer（非瀏覽器客戶端），兩條路匯流到同一個 DB 查詢。

## 理由

| 面向 | Cookie Session | JWT |
|---|---|---|
| 登出 / 撤銷 | `DEL` key，**立即生效**（`delete_session()`） | 有效期限內無法收回；要收回就得建黑名單 = 變相做出有狀態的 session |
| 改密碼踢全部裝置 | 索引 `SMEMBERS` + 逐一 `DEL`（`revoke_all_user_sessions()`），一行 | 每張票獨立有效，做不到 |
| XSS 偷取面 | cookie `HttpOnly` — JS 拿到的是「無資料的編號」，且讀不到 | token 存哪都會被 JS 讀（localStorage 常見反模式）|
| 每請求成本 | 1 次 Redis GET（含滑動續期） | 0 次儲存查詢（本機驗簽） |
| 跨服務共享 | 需共享 session store（本專案單一服務，不成立） | 天生無狀態，多服務友善 |

決定性的一條：**JWT 把真相交給客戶端，session 把真相留在伺服器**。撤銷要立即生效的產品，session 是天生的，JWT 是後天勉強的（黑名單模式 = 重新發明 session，還少了滑動過期與索引的整潔）。

## 後果

- 正面：真登出、全裝置撤銷一行完成、cookie 不暴露任何資料、無簽名密鑰管理。
- 負面：每請求多 1 次 Redis GET（本專案量級可忽略）；未來多服務共享認證需共享 Redis 或改 token（見觸發條件）。
- 已知妥協：`SameSite=strict` 使從外部連結進來的第一個請求未帶 cookie（使用者需站內一鍵恢復）— 見 [0001](./0001-same-origin-gateway-over-api-subdomain.md)。

## 觸發重新評估的條件

1. 出現行動 App 或第三方 API 消費者 → 啟用既有 Bearer 相容路徑（或 `api.` 子網域，見 0001）。
2. API 拆分為多個獨立服務、無法共享 session store。
3. 對延遲極度敏感、需要省去每請求 Redis GET（屆時考慮短期 JWT + refresh 輪換，並接受撤銷複雜度）。
