# Backend Lab 補充學習軸 — SDD, TDD, DevOps, CI/CD

這份文件是原本 **Backend Lab — 7-Day Roadmap** 的補充，不取代它。你的主線仍然是完整後端能力：Docker、PostgreSQL、SQL、FastAPI、API design、authentication、authorization、security、migration、testing 與 deployment。

SDD、TDD、DevOps、CI/CD 是貫穿主線的工程方法：它們讓每一個 backend 功能更容易設計、驗證與交付。

```text
Backend 功能
  ├─ SDD：先定義 API / DB contract
  ├─ TDD：用測試保護 contract
  ├─ DevOps：讓服務與資料庫可重現地執行
  └─ CI/CD：自動驗證，安全地交付
```

## 如何嵌入原本的 Backend Roadmap

| 原本 Phase | 主線後端學習 | 同步加入的補充能力 |
| --- | --- | --- |
| Phase 1 | Docker + PostgreSQL environment | DevOps 基礎：environment、volume、network、logs、healthcheck |
| Phase 2 | schema、SQL、index | SDD 基礎：先寫 schema contract、constraint 與 migration plan |
| Phase 3 | FastAPI + CRUD | SDD + TDD：每個 endpoint 先有 contract，再有 API tests |
| Phase 4 | auth、RBAC、security、migration | TDD 主戰場：auth/ownership/error cases/regression tests |
| Phase 5 | deployment、monitoring | DevOps + CI/CD：container、CI、staging、rollback、observability |

你現在位於 Phase 4，所以後面的兩週安排是「在原本 Phase 4 進度中同步練習」；不是要求你放下其他 backend 主題只學測試或 DevOps。

## 優化後的 Phase 4 — API 品質、契約與測試

Phase 4 的目標不應只是「加完 JWT、RBAC、pytest」。完成時，你應該能安全地改一個 endpoint，並由測試知道有沒有破壞既有行為。

### Phase 4.1 — API contract 與 SDD

每個重要 endpoint 先有一張短 spec，再寫 code。優先補齊：

- `POST /users`：201、422、409，且絕不回傳 password/hash。
- `POST /login`：成功 token、錯帳密 401、過期／錯誤 token 401。
- `GET /orders/{id}`：本人、他人、不存在 order 的行為。
- `GET /orders`：明確決定「本人自己的列表」或「admin 可看全部」；不能保留模糊行為。

**Definition of Done：** 每個 endpoint 都能寫出 success、validation、authentication、authorization、not-found/conflict 與 non-goal。

### Phase 4.2 — TDD 與測試邊界

建立三層測試，但不要一開始過度建模：

| 類型 | 本 lab 必須有的內容 | 不必現在做 |
| --- | --- | --- |
| Unit | password verify、JWT decode、role decision | 為每個 ORM getter 寫 unit test |
| Integration | users/login/orders 的 HTTP + PostgreSQL contract | 每個框架內部行為都 mock |
| Smoke | `/health`、`/ready`、一條登入後 API | 全端 E2E framework |

測試 DB 與開發 DB 分離。每個 test 都能獨立執行，並且不依賴執行順序或手動建立的資料。

**Definition of Done：** 先讓新測試失敗（Red），做最小實作通過（Green），再重構；完整 suite 可連跑兩次且結果一致。

### Phase 4.3 — 資料庫 migration 與錯誤契約

- 所有 schema change 都由 Alembic migration 管理；不在 app import 時呼叫 `create_all()`。
- 每個 migration 寫清楚：upgrade、downgrade、既有資料如何處理。
- 對 unique/FK conflict 做 rollback，轉成一致 HTTP error；不回傳原始 DB error。
- Model、Pydantic response schema、真實 DB constraint 要一致。

**Definition of Done：** 從空資料庫可 `alembic upgrade head`；一個 migration failure 或 constraint error 有測試覆蓋，且 API 不洩漏內部資訊。

### Phase 4.4 — 安全與可維護 API 基線

- 密碼只存 Argon2 hash；JWT secret 不進 Git。
- CORS 只允許明確 frontend origin；它不被當作 authentication。
- pagination/filter/sort 都設定 allow-list 或最大值。
- request error format 一致；server-side log 記錄診斷資訊。

**Phase 4 最終驗收：** 從一張 SDD card 開始，完成一個受 auth/RBAC 保護的 endpoint；測試包含 success、422、401、403/404、409（適用時）；migration 和 test DB 都可從空環境建立。

## Phase 4.5 — Redis：快取與短期狀態

Redis 不是先加進來「讓架構看起來完整」，而是在你能量測或明確說出資料庫讀取、rate limiting、token revocation 的需求後才加入。

### 學習順序

1. 用 Docker Compose 加入 Redis；理解它和 PostgreSQL 的差別：Redis 是可失效的快取／短期狀態，不是唯一真實資料來源。
2. 實作一個 read-through cache，例如熱門商品列表或公開 user summary：cache miss 查 PostgreSQL，再設定 TTL。
3. 實作 cache invalidation：相關資料被更新時刪除或更新 cache key。
4. 選一個安全用途：rate limiting、短效 session state，或 token deny-list；不要同時做三種。
5. 做 failure mode：Redis 無法連線時，read API 要安全地 fallback 到 PostgreSQL，或對 rate limit 明確採 fail-open / fail-closed。

### 測試與驗收

- cache hit 不查 DB、cache miss 會回填，兩者都有測試。
- 資料更新後不會讀到過期 cache。
- Redis 停止時，行為符合你的 SDD contract，不會讓 API 500。
- 所有 key 都有 prefix 與 TTL；不把 password、JWT 本體、長期商業資料當作 Redis 的唯一副本。

**Definition of Done：** 你能畫出「client → API → Redis → PostgreSQL」的 hit/miss/fallback 路徑，並用測試證明 invalidation 與 Redis outage 行為。

## 優化後的 Phase 5 — DevOps、CI、CD 分階段交付

Phase 5 不把「能 docker build」和「安全部署 production」混成同一件事。依序完成以下四個 milestone；前一個沒驗收，不進下一個。

### Phase 5A — Reproducible runtime（Docker / DevOps 基線）

- Dockerfile、`.dockerignore`、non-root API container。
- Compose 包含 API、PostgreSQL、named volume、network、環境變數。
- DB healthcheck；API 分開 `/health` 與 `/ready`。
- 啟動流程明確執行 migration，API 不搶在 DB 可用前啟動。
- `.env` 不 commit，`.env.example` 可讓新開發者建立本機環境。

**Definition of Done：** 在乾淨 clone 執行 `docker compose up --build`，migration、`/health`、`/ready` 都成功；重建 container 後能解釋資料是否因 volume 保留。

### Phase 5B — CI（每次變更的自動品質門檻）

CI pipeline 順序固定為：

```text
checkout → install → format/lint → test PostgreSQL service
→ alembic upgrade head → pytest → Docker build
```

- pull request 和 push 都執行。
- CI environment 使用自己的 DB URL / JWT secret，不讀你的 `.env`。
- 至少故意製造一次 test failure 與一次 migration failure，學會讀 log 並在本機重現。
- branch protection 在 repository 設定中要求 CI pass 才能 merge。

**Definition of Done：** 每個 PR 都看得到 CI；任何一個 test、migration 或 image build 失敗都會阻擋合併。

### Phase 5C — CD 到 staging（先不是 production）

只有 CI 穩定後才選一個 deployment target（單台 VM、Render、Fly.io 或雲端 container service）。流程：

```text
merge main → build Git-SHA image → push registry
→ deploy staging → migrate → smoke test → inspect logs
```

- secret 由平台 secret manager／environment secret 提供。
- migration 採 backward-compatible 變更；先 deploy 相容 code，再移除舊欄位。
- staging smoke test 至少包含 health、ready、登入、授權 API。

**Definition of Done：** 能從 Git SHA 找回目前 staging image，且能在 staging 完整跑 smoke test。

### Phase 5D — Rollback 與最小 observability

- 寫 runbook：失敗時看哪個 log、如何回到前一個 image tag、migration 哪些情況不能 downgrade。
- 結構化 request log 至少含 request ID、method、path、status、latency，不含 password/token。
- 先做 health/readiness 與 error log；有實際 metrics 問題再加 Prometheus/Grafana。
- production deployment 保留人工核准，不讓每次 push 自動直接上 production。

**Phase 5 最終驗收：** 能從乾淨 clone → CI → staging deploy → smoke test；能模擬失敗並用 runbook rollback。Kubernetes、Terraform、完整 observability stack 只在這個流程穩定後再加入。

## Phase 6 — Background Jobs 與 MQ

MQ（RabbitMQ、Redis Streams、或雲端 queue）只在有明確非同步需求時加入，例如寄 email、產報表、匯入資料、付款後處理。HTTP request 不應等待這類長工作完成。

### 學習順序

1. 先寫 SDD：誰發 event、worker 做什麼、使用者何時知道任務完成、失敗怎麼看。
2. 實作一條最小流程：API 寫入 DB → 發送 job → worker 消費 → 更新 job status。
3. 處理 retry 與 idempotency：同一個 message 被投遞兩次，結果不能重複寄信或重複扣款。
4. 設定 dead-letter queue（DLQ）：多次失敗後不無限重試，保留訊息供診斷。
5. 學 outbox pattern：如果「DB commit 成功但 publish 失敗」，不能悄悄遺失訊息。
6. 在 Compose 和 CI 加 worker/MQ；staging 驗證 worker logs、retry、DLQ。

### 測試與驗收

- API 回傳的 job ID 可查詢 status。
- consumer 重複收到同一 job，side effect 只發生一次。
- worker 暫停／重啟後，未完成 job 不遺失。
- 故意讓 worker 失敗，確認 retry 次數與 DLQ 行為。
- migration、API、worker 使用相同的 schema 版本與 deploy runbook。

**Definition of Done：** 能解釋 queue 與 database 的責任差異、at-least-once delivery 為何需要 idempotency，以及 outbox pattern 解決哪個資料一致性風險。

## 可穿插的兩週實作衝刺（目前 Phase 4 適用）

### Week 1 — SDD + TDD：讓現有 API 有明確契約與測試

**目標：** 不再是「endpoint 能跑」，而是每個重要行為都有明確 contract 與可重複執行的測試。

### Day 1 — SDD 規格卡

針對既有功能寫兩張規格卡：

1. `POST /users`
2. `GET /orders/{order_id}`

每張卡都要有：

```md
Goal: 使用者要完成什麼？
Input: 欄位、型別、限制。
Success: status code 與 response。
Failure: 422 / 401 / 403 或 404 / 409 的選擇。
Authorization: 誰可以操作這筆資料？
Persistence: 寫入或讀取哪些 table？
Acceptance: 最少哪些案例要通過？
Non-goal: 這次刻意不做什麼？
```

**驗收：** 不看程式也能說清楚「一般 user 能否看別人的 order」與理由。

### Day 2 — Red：先寫 API integration tests

先替 `POST /users` 寫三個失敗測試：

- 成功建立 user：201，回傳不得含 password/hash。
- 重複 email：409。
- 不合法 email 或短密碼：422。

測試使用獨立 test database，不能讀寫你的開發 DB。

**驗收：** 可以指出每個測試保護的 acceptance criterion。

### Day 3 — Green：最小實作與資料庫一致性

只改足以讓 Day 2 測試通過的程式。檢查：

- 密碼只儲存 hash。
- `IntegrityError` 後有 rollback。
- response model 不會洩漏 `password_hash`。
- schema 變更只透過 Alembic migration。

**驗收：** 測試全綠；從空 test DB 可 `alembic upgrade head`。

### Day 4 — Auth / ownership 的 TDD

針對 order 寫四個案例：

- 沒有 Bearer token：401。
- 有效 token 讀自己的 order：200。
- 有效 token 讀別人的 order：依 Day 1 contract 回 403 或 404。
- 不存在的 order：404。

**驗收：** 能解釋 401、403、404 的不同，以及為什麼你的 contract 選擇其中一種。

### Day 5 — Regression 與 review

選一個真實曾經卡住的 bug，例如 migration 與 model nullable 不一致、沒有 DB 時 `/ready` 的行為、或 order list 的授權不一致。

1. 先寫能重現問題的 failing test。
2. 修正最小程式。
3. 請 AI 只做 review，不寫 code。

**Week 1 驗收：** `pytest` 可重複跑；你能從 SDD 卡一路說明某一個 endpoint 的測試和實作。

### Week 2 — Container、DevOps、CI：讓驗證自動且可重現

**目標：** 任何人從乾淨 clone 都能啟動同一套 API + DB；每次 push 都自動驗證。

### Day 6 — Compose 與 migration boot flow

確認 Compose 有：

- PostgreSQL named volume。
- DB healthcheck。
- API 使用 `postgres:5432`，不是 `localhost`。
- migration 在 API ready 前完成。
- `/health`（process alive）與 `/ready`（DB 可查詢）分開。

**驗收：** 從空 database 執行 `docker compose up --build` 後，`/health` 和 `/ready` 都成功。

### Day 7 — Container security 與操作

理解並驗證：

- `.env` 不進 Git；`.env.example` 只放安全範例。
- `.dockerignore` 排除 `.env`、`.venv`、tests、Git metadata。
- API image 以 non-root user 執行。
- production 不輸出 SQL echo。
- 用 `compose ps`、`logs`、`exec` 找出 DB／API 啟動失敗原因。

**驗收：** 故意讓 DB URL 錯誤，能從 log 和 `/ready` 定位問題。

### Day 8 — 最小 CI

建立 GitHub Actions：

```text
push / pull request
  → checkout
  → install dependencies
  → start PostgreSQL service
  → alembic upgrade head
  → pytest
  → Docker build
```

**驗收：** 將一個 assertion 故意改錯，確認 CI 失敗；再還原並確認成功。

### Day 9 — CI 品質門檻

加入 format/lint gate，並理解它與 test 的差別：

- format/lint：一致性、常見錯誤、未使用 imports。
- tests：API contract、權限、DB 行為。
- Docker build：image 可以被建出來。

**驗收：** Pull request 合併前必須通過全部 CI checks。

### Day 10 — Release rehearsal 與 CD 設計

先不急著上 production。完成一份 runbook：

```text
build image with Git SHA
  → deploy staging
  → alembic upgrade head
  → smoke test (/health, /ready, login)
  → inspect logs
  → rollback to previous image tag if needed
```

選定一個 staging target（單台 VM、Render、Fly.io 或雲端 container service）後，才開始真正的 CD。

**Week 2 驗收：** 你能解釋 CI、CD、migration、smoke test、rollback 各自保護什麼風險。

## 與 AI agent 的固定協作流程

每一項功能都用以下順序：

1. 你先寫 SDD card。
2. 請 AI 只找 edge cases、權限與 migration 風險。
3. 請 AI 只寫 failing tests。
4. 請 AI 做最小實作，並回報 test command/results。
5. 用新的 prompt 請 AI 只 review diff。
6. 你自己讀 diff、跑 tests、決定是否合併。

可複用 prompt：

```text
Context: FastAPI + SQLAlchemy + PostgreSQL。
Task: 只完成 <endpoint / migration / bug>。
Contract: <貼上 SDD card>。
Constraints: 不增加 dependency；不可修改無關檔案；schema 只用 Alembic。
Done when: <列出具體 pytest / compose / migration 驗收命令>。
先列計畫與風險；完成後列檔案、實際結果、未驗證假設。
```

## 暫時不要加入的主題

Kubernetes、Terraform、Ansible、Kafka、RabbitMQ、microservices、service mesh、Helm、ArgoCD、完整 Prometheus/Grafana stack。

先完成這份 roadmap；當你能穩定完成「規格 → 測試 → container → CI → staging rehearsal」，再依實際部署需求挑一個深入。
