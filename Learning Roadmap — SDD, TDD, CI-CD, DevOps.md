# Learning Roadmap — SDD, TDD, CI/CD, DevOps

這不是「把工具全學一遍」的清單，而是一條工程交付鏈：

```text
需求說清楚（SDD）
  → 用測試固定行為（TDD）
  → 在一致環境執行（Container / DevOps）
  → 自動驗證與交付（CI/CD）
```

以目前的 FastAPI + PostgreSQL lab 作為唯一練習專案。這是兩週衝刺版：先完成第一週的規格與測試基礎，再進第二週的 container、CI/CD 與部署演練；不要同時學 Kubernetes、Terraform 或 microservices。

## 先備條件與學習節奏

先能做三件事：建立一個 FastAPI endpoint、用 SQL 查一張 PostgreSQL table、使用 Git commit。其餘都在路線中學。

建議每週 5 次、每次 60–90 分鐘：20 分鐘讀概念、50 分鐘實作、10 分鐘紀錄「假設／證據／結論」。每一次 session 都用一個很小的功能，例如「註冊使用者」或「只讀取自己的訂單」。

## Week 1 — SDD + TDD：把需求變成可驗收、可測試的契約

**目標：** 在寫程式前，能明確說出 API 要做什麼、不能做什麼、如何證明完成。

### 學習順序

1. 認識 user story、API contract、acceptance criteria、non-goal 的差別。
2. 為 `POST /users` 寫一張規格卡。
3. 為 `GET /orders/{id}` 寫一張含 ownership 規則的規格卡。
4. 為「新增 `role` 欄位」寫 migration spec：現有資料、upgrade、downgrade、rollback 風險。

### 規格卡模板

```md
## <METHOD> <PATH>
Goal: 使用者要完成什麼？
Input: 欄位、型別、限制。
Success: status code 與 response contract。
Failure: validation / auth / conflict / not-found 如何回應。
Persistence: 哪些資料會被讀寫；誰擁有資料。
Acceptance: 最少哪些案例必須通過。
Non-goals: 這次刻意不做什麼。
```

### AI 協作方式

```text
以下是我的 SDD 規格。不要寫程式。
請找出模糊處、edge cases、權限與資料一致性風險。
最後只輸出：問題、建議決策、可驗收案例。
```

完成兩張規格卡後，立刻用其中一張進行 TDD。目標是理解 Red → Green → Refactor，並區分 unit、integration、smoke tests。

### 學習順序

1. 建立 pytest、test client、test database；絕不讓測試共用開發資料庫。
2. 對規格卡先寫失敗的 API integration tests。
3. 做最小實作讓測試變綠。
4. 重構但不改行為；每次重構後都跑測試。
5. 補一個真 bug 的 regression test：先重現 bug，再修。

### 測試層級

| 層級 | 要保護什麼 | Backend Lab 例子 |
| --- | --- | --- |
| Unit | 純規則、無 I/O | password hash/verify、JWT expiry、role check |
| Integration | API + DB contract | 重複 email → 409、他人 order 不可讀取 |
| Smoke | 部署後最重要路徑 | `/health`、`/ready`、login 後讀取自己的 order |

### TDD 的 AI prompts

```text
根據這張 spec，只寫會失敗的 pytest tests，不要改 production code。
每個 test 標示它保護的 acceptance criterion。
```

```text
現在只做最小 production code 讓這些測試通過。
不加 dependency、不改無關 endpoint。完成後列出實際測試結果。
```

**Week 1 驗收：** 不看程式也能寫出兩張規格卡；`POST /users` 至少有 success、422、409 三個測試；你能說明每個測試在防什麼 regression。

## Week 2 — Container、DevOps、CI/CD：讓交付流程可重現

**目標：** 不靠你的本機狀態，也能啟動 API、DB、migration 並定位故障。

### 學習順序

1. Dockerfile：image、layer、`.dockerignore`、non-root user、environment variables。
2. Docker Compose：app、PostgreSQL、network、named volume、port mapping。
3. Readiness：DB healthcheck、API `/health` 與 `/ready` 的差別。
4. Database migration：從空 DB 跑 `alembic upgrade head`；理解為何不用 `create_all()`。
5. 操作與除錯：`compose ps`、logs、exec、inspect、rebuild、volume lifecycle。
6. 基本安全：`.env` 不 commit、`.env.example`、runtime DB user、關閉 production SQL echo。

### 練習任務

```text
從乾淨 clone 開始
→ 建立 .env
→ docker compose up --build
→ migration 成功
→ /health 與 /ready 都成功
→ 停止／重建 container，驗證 volume 行為
```

完成 container 基線後，將驗證變成 CI，最後再選一個 staging target 演練 CD。目標是每次 push 都有一致品質門檻；先完成 CI，再進 CD。

### CI 學習順序

1. 讀 GitHub Actions workflow：trigger、job、step、environment、service container、secret。
2. 建立最小 pipeline：checkout → install → migration → tests → Docker build。
3. 故意讓一個測試失敗，讀 CI log 並在本機重現。
4. 加 format/lint gate；理解它和 test gate 保護的東西不同。
5. 設 branch protection：PR 必須通過 CI 才可合併。

### CD 學習順序（CI 穩定後才做）

1. 選**一個** staging target：單台 VM、Render、Fly.io 或雲端 container service；先不要碰 Kubernetes。
2. Build 帶 Git SHA 的 image，推到 registry。
3. 部署到 staging，執行 migration，跑 smoke test。
4. 寫 rollback runbook：上一個 image tag、migration 是否向下相容、怎樣看 logs。
5. production 必須有明確核准點；不要讓未經 review 的 push 直接部署 production。

```text
Pull request
  → CI: format/lint + tests + migration + Docker build
  → merge main
  → build and tag image
  → deploy staging
  → smoke test
  → manual approval
  → production deploy
```

**Week 2 驗收：** 不查筆記，能解釋 `localhost` 和 `postgres`、volume、healthcheck 的差別；能讓 CI 故意失敗並解釋原因；能指出 deployment、migration、smoke test、rollback 各在保護哪個風險。

## Capstone — 完整交付演練

選一個小功能，例如「登入者只能讀取自己的 order」。完整跑一次：

1. 寫 SDD spec 和 non-goal。
2. AI 幫你 review edge cases，但由你決定 contract。
3. 先寫失敗的 401、404/403、成功案例測試。
4. 做最小實作，全部測試通過。
5. 新 migration 時，從空 DB 驗證 upgrade。
6. Compose 啟動服務，跑 smoke test。
7. Push 後確認 CI；最後寫一段 deployment/rollback 模擬紀錄。

完成時，你不是只會背工具名，而是能解釋：**一個需求如何一路被規格、測試、container、CI 與部署流程保護。**

## AI 協作守則

- 先給 spec，再叫 AI 寫程式；沒有 contract 就先叫它提問與找風險。
- 一次只交付一個 endpoint、migration 或 bug；不要說「幫我完成 auth」。
- 要求 AI 每次回報：改了哪些檔、跑了哪些命令、結果、未驗證假設。
- 用第二次獨立 prompt 做 review，避免同一個 agent 同時出題、實作與自評。
- schema、權限、secret、production deployment 的決策由你做；AI 只提供選項與證據。

## 現階段不要學

Kubernetes、Terraform、Ansible、Kafka、RabbitMQ、microservices、service mesh、Helm、ArgoCD、完整 ELK stack。等你已經能穩定完成 Capstone，再以實際需求挑一項往下學。
