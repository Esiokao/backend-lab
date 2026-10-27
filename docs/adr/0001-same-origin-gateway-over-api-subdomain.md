# 0001 — 網頁產品採同源閘道（`/api` 路徑分流），不使用 `api.` 子網域

- **日期**：2026-10-26
- **狀態**：Accepted
- **決策者**：backend-lab 團隊

## 背景

前端（Vue 3 SPA）與後端（FastAPI）需要對話。常見的兩種拓撲：

1. **同源閘道**：網站與 API 同一個 origin，由反向代理按路徑分流（`/api/*` → API、其餘 → 前端靜態檔）。
2. **API 子網域**：前端 `xxx.com`、API `api.xxx.com`，瀏覽器跨源請求。

本專案的認證是 **cookie session**（`app/core/session.py`；HttpOnly + Secure + SameSite=strict + host-only domain），且客戶端目前只有瀏覽器 SPA。

## 決策

採用**同源閘道**：

- 正式環境：`nginx.prod.conf` — `/api/` → FastAPI、`/` → 前端靜態站（immutable image）。
- 開發環境：Vite proxy `/api` → `localhost:8000`（dev-only，契約與正式一致）。
- Cookie 維持 **host-only**（不設 `Domain`）+ `SameSite=strict`。

## 理由

| 面向 | 同源閘道 | `api.` 子網域 |
|---|---|---|
| CORS | 不存在（同源零設定） | 必須設定 `Allow-Origin`（精確釘死）+ `Allow-Credentials`；非簡單請求多 preflight 來回 |
| Cookie 作用域 | host-only（最小暴露） | 須放寬為 `Domain=.xxx.com` → 所有子網域可攜 |
| CSRF | `SameSite=strict` 全效，源頭斷水 | 子網域仍 same-site，SameSite 仍有效，但 cookie 暴露面變寬 |
| 部署面積 | 一份 nginx 設定 | 兩份 TLS/代理設定 + 環境變數 + 本地 dev 流程重弄 |
| 安全敘事 | 「同源 + HttpOnly + SameSite=strict + host-only」一句話講完 | 敘事變複雜（CORS credentials 設定本身就是攻擊面） |

SPA + cookie session 的組合下，同源閘道**沒有**功能損失；`api.` 子網域的優勢（獨立擴縮、第三方客戶端）在本專案不存在。

## 後果

- 正面：零 CORS 設定、cookie 暴露面最小、CSRF 在 cookie 屬性層結束（不需 CSRF token）、部署簡單。
- 負面：API 無法被「非同源網頁」直接呼叫（這正是目的）；API 與前端共用一個 deploy 單位。
- 注意：`app/core/dependencies.py` 的 `get_current_user()` 保留了 Bearer JWT 相容路徑 — 未來若有非瀏覽器客戶端，可走 `api.` 子網域 + token，網頁前端維持同源 cookie（混合模式），屆時不需改動本決策的網頁部分。

## 觸發重新評估的條件

1. 出現行動 App 或第三方 API 消費者。
2. API 需要獨立擴縮或獨立部署節奏。
3. 前端搬到不同的 registrable domain（same-site 關係破裂）。
