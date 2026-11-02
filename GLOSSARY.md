# GLOSSARY.md

領域詞彙表：這裡的定義是**契約**——代碼、測試、文檔對同一個詞的使用必須與此一致。
發現代碼行為與本表衝突時，先確認是代碼錯了還是表該更新，不要默默各自漂移。

## Order Status（訂單狀態機）

單一真相來源：`app/core/enums.py` 的 `ALLOWED_TRANSITIONS`。

```
unpaid ──付款──→ paid ──fulfillment──→ processing ──fulfillment──→ completed
   │                │                     │
   └────過期────────┴──────admin/owner 取消──┴──→ cancelled
```

| 狀態 | 業務語意 | 進入方式 | 離開方式 |
|---|---|---|---|
| `unpaid` | 已建單，**未付款**。使用者按了結帳但未完成付款時停留在這 | `POST /orders`（購物車結帳 / checkout 內部重用） | 使用者付款（→ `paid`）、使用者/過期取消（→ `cancelled`）、過期 worker（30 分鐘，`order_expiry`） |
| `paid` | **已付款**，待出貨。真實 UI 結帳流程的**終點**（結帳頁的 Pay 按下去就算完成） | `POST /orders/{id}/pay`（demo 模擬付款） | admin 改狀態（→ `processing`/`completed`/`cancelled`）、owner 取消（→ `cancelled`）、fulfillment worker（5 分鐘後 → `processing`） |
| `processing` | 揀貨/出貨處理中。**不可再取消的臨界點已過** | admin 改狀態、fulfillment worker | admin 改狀態、fulfillment worker（→ `completed`） |
| `completed` | 已送達（終態） | fulfillment worker、admin、`POST /orders/{id}/complete` | — |
| `cancelled` | 已取消（終態）。**所有取消路徑皆歸還庫存**（owner cancel、過期 worker、admin——單一真相來源 `app/services/inventory.py`） | 同左 | — |

### 歷史備註（2026-11-01 改名）

原名 `created` / `pending`——日常語意（「剛建立」「還沒處理」）與業務語意
（「未付款」「已付款待出貨」）錯位，多次造成誤解（測試造錯狀態、取消測錯窗口），
故改名為 `unpaid` / `paid`。結構（狀態數量、轉移規則）自始未變。
遷移：`alembic/versions/b5c6d7e8f9a0`。

### 測試/開發注意

- **造資料要走到真實流程會停留的終點**：驗「已付款訂單」的行為時要 `payOrder`，
  不要停在 `unpaid`（那真實使用者幾乎不會停留）
- **未付款訂單會被過期 worker 取消並歸還庫存**——驗「未付款」狀態的測試
  不能依賴一筆舊的 unpaid 訂單還在
- `pending`（**outbox**）與訂單無關：`notification_outbox.status` 有自己的
  pending / dispatched / processed（通知佇列的狀態機），勿混淆

## Fulfillment（模擬倉儲）

`app/workers/fulfillment.py` 以時間壓縮模擬倉儲：paid 5 分鐘 → processing，
自付款起 30 分鐘 → completed。節奏由 env 控制
（`FULFILLMENT_PROCESSING_DELAY_SECONDS` / `FULFILLMENT_COMPLETION_DELAY_SECONDS`，
預設 300/1800；demo 想看快速流程可臨時覆寫為 5/65）。

## Transactional Outbox（交易式發件箱）

「業務資料」與「要發的事件」寫進**同一個交易**（orders 同交易寫
`notification_outbox`）→ dispatcher 輪詢發布 → RQ worker 消費 → 建通知。
保證：事件與業務變更同生共死（at-least-once），消費端以三層冪等防重複。
`notification_outbox.status`（pending/dispatched/processed）是**佇列自己的**
狀態機，與訂單狀態無關。

## Payment Intent / Receipt / Nonce（付款憑證三件套）

付款邊界：**paid 狀態只能由「金流供應商簽發的收據」觸發**，不能由任何人自我宣告
（POST /orders/{id}/pay 不再是開關）。三步流程：

1. `POST /orders/{id}/payment-intent` → 後端計算金額（client 無法報價）、
   生成 nonce、簽出 intent token（HMAC，5 分鐘時效）
2. `POST /mock-provider/pay` → 模擬金流供應商：驗 token → 收錢 → 簽發 receipt
3. `POST /orders/{id}/pay { receipt }` → 驗收據 + 消耗 nonce → 轉 paid

| 詞 | 定義 | 防的攻擊 |
|---|---|---|
| Intent | 「我打算付這筆錢」的 server 簽章憑證，金額由後端計算 | client 竄改金額 |
| Receipt | 供應商確認收款後簽發的收據，綁定單一訂單 | 跨單付款、未授權標記 |
| Nonce | 單次使用的隨機值，DB（payment_intents.used_at）記錄已用 | 收據重放 |

實作：`app/core/payment.py`（HMAC）+ `app/routers/payments.py`（intent/provider）
+ `orders.py` 的 `settle_receipt`（驗章）。測試：`tests/payments/`（八個情境）。
接入真實金流時：mock-provider 換成 Stripe 頁面/SDK，pay 端點改驗供應商
webhook 簽章——三步骨架不變。
