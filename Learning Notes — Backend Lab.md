# Backend Lab 學習筆記

> 依目前 working tree（FastAPI、SQLAlchemy、Alembic、JWT/RBAC、CORS）整理。每次卡住時，先更新「問題 → 假設 → 證據 → 結論」，讓問題變成可重複使用的除錯知識。

## 現在已經串起來的重點

```text
Request → FastAPI router + Pydantic validation
        → Depends(get_db) 建立 request-scoped SQLAlchemy Session
        → ORM model / SQL → PostgreSQL

Login → verify_password(password, password_hash) → JWT access token
      → get_current_user → order ownership / require_admin
```

- `Pydantic schema` 是 API contract；它決定 client 可以送什麼、會收到什麼。`UserResponse` 不含 `password_hash` 是安全邊界。
- `SQLAlchemy model` 是 Python 對 table 的描述；`Base.metadata` 收集 models，但不是 schema version history。
- `engine` 管理 DB connections；`SessionLocal()` 才建立 Session。`get_db()` 的 `yield` 讓每個 request 使用後能關閉 session。
- `select()` 查資料；`scalar_one_or_none()` 讓「沒有資料」成為明確的 `None` 分支；寫入後要 `commit()`，出錯要 `rollback()`。
- `IntegrityError` 是資料庫 constraint 的最後防線；API 要轉成一致的 409，不能把原始 DB error 回給 client。
- Order 的 `user_id` 必須從 JWT current user 取得，不能信任 request body；這是 resource ownership 的核心。
- `selectinload(User.orders)` 避免列出多位 user 時的 N+1 queries；用 SQL log 或測試確認，不憑感覺加入。
- CORS 是 browser 對跨 origin request 的規則，不是 authentication；server-to-server request 不受它保護。

## 最近問題點與應釐清的答案

| 問題點 | 正確心智模型 | 下一個小實驗 |
| --- | --- | --- |
| `create_all()` 和 Alembic 可以一起用嗎？ | 兩者都管理 schema 會讓 migration history 與真實 DB 漂移。採 Alembic 後只用 `alembic upgrade head`。 | 用空 DB 跑 migration，確認 `alembic current` 是 head；移除 import-time `create_all()` 後再跑 API。 |
| `password_hash` migration 為何 nullable，但 model 是 `nullable=False`？ | 新增欄位時既有 rows 沒值，migration 必須處理舊資料；model 與 DB constraint 最終要一致。 | 決定 backfill／reset lab DB；再新增 migration 設為 non-null。 |
| ORM 的 `default="user"` 為何不一定保護 SQL/其他 client？ | Python default 只在 ORM 建 object 時套用；DB 要有 `server_default` 或 NOT NULL 才保護所有寫入路徑。 | 直接用 psql INSERT 測 DB 行為。 |
| 401、403、404 怎麼選？ | 未登入／token 無效是 401；已登入但禁止是 403；資源不存在，或避免洩漏 ownership 時統一 404。 | 為無 token、他人 order、不存在 order 各寫 API test。 |
| `depends_on` 為何不夠？ | 通常只控制啟動順序，不代表 PostgreSQL 已可連線；需要 DB healthcheck 與 `service_healthy`。 | 加 healthcheck，刻意慢啟動 DB 驗證 API。 |
| 為何 test 不能共用開發 DB？ | 測試會建立、刪除、rollback 資料；共用會汙染手動資料，也因順序而不穩。 | 做 `DATABASE_URL` test override，完整測試跑兩次。 |
| 為何不能把 secret 放 `.env.example`？ | example 只能有變數名與無效 placeholder，不能有真實可登入值；git history 也是曝光面。 | 確認 `.env` 在 `.gitignore`，建立安全 `.env.example`。 |

## 目前程式的下一步學習任務（按順序）

1. 建立 `/health` 與 `/ready`：前者是 process 活著，後者實際 probe DB。
2. 加 pytest 與 test database：先涵蓋 `POST /users` 的 201、409、422，以及 `/login` 的成功、錯密碼、未知帳號。
3. 將 users 與 orders 的 response models 明確化：目前部分 endpoint 直接回 ORM object，contract 容易隨 model 漂移。
4. 為 `GET /orders` 決定授權規格：目前它列出所有 orders 卻不要求登入，和 ownership 規則不一致；選「只看自己的」或「admin 才能看全部」，再用測試鎖住。
5. 修正 migration 與 model 一致性，並停止 `Base.metadata.create_all()` 的 schema 管理責任。
6. 建立 CI：先跑 format/lint、tests、Docker build；通過後再談 publish/deploy。

## 除錯決策樹

```text
API 失敗
 ├─ 422 → Pydantic request schema、欄位名稱、型別、validation
 ├─ 401/403 → Authorization header、JWT decode、current user、ownership rule
 ├─ 404 → path id、select 條件、是否刻意隱藏未授權資源
 ├─ 409 → unique/FK constraint；rollback 後 session 有沒有被重用
 ├─ 500 → server log；區分 import/config、DB connection、SQL、serialization
 └─ DB 連不上
     ├─ host 上跑 API → localhost:<mapped port>
     ├─ compose 內 API → postgres:5432
     └─ compose ps、healthcheck、DATABASE_URL、logs
```

## 每次實作前的 5 分鐘清單

- [ ] 一句話說出這個 endpoint／migration 的 Goal？
- [ ] success、validation failure、authorization failure 各是什麼 status？
- [ ] 需要 migration 嗎？既有資料怎麼辦？
- [ ] 最小失敗測試是什麼？
- [ ] 用什麼命令證明乾淨環境可重現？
