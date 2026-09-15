# Backend Lab — 7-Day Roadmap

## 最終目標

一週後完成：

```text
Client
  │
  ▼
FastAPI
  │
  ▼
PostgreSQL
```

整套環境由：

```text
Docker Compose
```

管理，並且具備：

```text
Database Migration
Automated Tests
GitHub Actions CI
Basic Monitoring
```

最終架構：

```text
                 ┌─────────────┐
                 │   Client    │
                 └──────┬──────┘
                        │ HTTP
                        ▼
                 ┌─────────────┐
                 │   FastAPI   │
                 │  Container  │
                 └──────┬──────┘
                        │
              Docker Network
                        │
                        ▼
                 ┌─────────────┐
                 │ PostgreSQL  │
                 │  Container  │
                 └──────┬──────┘
                        │
                        ▼
                 Docker Volume


Git Push
   │
   ▼
GitHub Actions
   │
   ├── Test
   └── Docker Build
```

---

# Phase 1 — Docker + PostgreSQL Environment

## Goal

先不寫 API。

目標是：

```text
docker compose up
        ↓
PostgreSQL 啟動
        ↓
psql 可以連線
        ↓
Windows 可以連 PostgreSQL
        ↓
資料寫入
        ↓
Container 刪除 / 重建
        ↓
資料仍然存在
```

## 1.1 Compose

建立：

```text
backend-lab/
│
├── compose.yaml
├── .env
├── .env.example
├── .gitignore
└── postgres/
```

TODO：

- [ ] 建立 `compose.yaml`
- [ ] 加入 PostgreSQL service
- [ ] 使用 `postgres:17`
- [ ] `docker compose up`
- [ ] `docker compose up -d`
- [ ] `docker compose ps`
- [ ] `docker compose stop`
- [ ] `docker compose start`
- [ ] `docker compose down`

必須理解：

```text
Image
Container
Service
Project
```

並能解釋：

```text
postgres:17
        ↓
Image

services:
  postgres:
        ↓
Service

backend-lab-postgres-1
        ↓
Container
```

---

## 1.2 Container 操作

TODO：

- [ ] `docker ps`
- [ ] `docker compose exec postgres bash`
- [ ] `docker compose logs postgres`
- [ ] `docker inspect`
- [ ] `docker stats`

理解：

```text
docker compose exec postgres bash
```

中的 `postgres` 是：

```text
Service Name
```

而：

```text
docker exec -it backend-lab-postgres-1 bash
```

使用的是：

```text
Container Name
```

---

## 1.3 PostgreSQL Environment Variables

設定：

```text
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
```

TODO：

- [ ] 建立 PostgreSQL user
- [ ] 建立 database
- [ ] 使用 `psql -U <user>`
- [ ] 使用 `psql -U <user> -d <database>`
- [ ] 理解 Linux user != PostgreSQL role
- [ ] 把設定移到 `.env`
- [ ] 建立 `.env.example`
- [ ] `.env` 加入 `.gitignore`

必須理解：

```text
Environment Variable
        ↓
Container Configuration
```

以及：

> PostgreSQL image 的初始化環境變數主要在第一次初始化 data directory 時生效。

---

## 1.4 Port Mapping

加入：

```text
HOST:CONTAINER
5432:5432
```

TODO：

- [ ] expose PostgreSQL port
- [ ] 從 Windows host 連 PostgreSQL
- [ ] 改成 `5433:5432`
- [ ] 驗證 localhost:5433
- [ ] 理解 container port 沒有改

必須能解釋：

```text
Windows
localhost:5433
      │
      ▼
Docker
      │
      ▼
PostgreSQL Container
5432
```

---

## 1.5 Volume

這是 Phase 1 最重要的實驗之一。

TODO：

- [ ] 建立一個 table
- [ ] INSERT 一筆資料
- [ ] `docker compose down`
- [ ] `docker compose up`
- [ ] 檢查資料
- [ ] 加入 named volume
- [ ] 重做實驗
- [ ] `docker compose down -v`
- [ ] 觀察差異

必須理解：

```text
Container Lifecycle
        !=
Data Lifecycle
```

以及：

```text
Container
    │
    ▼
Named Volume
    │
    ▼
PostgreSQL Data
```

---

## 1.6 Docker Network

TODO：

- [ ] `docker network ls`
- [ ] 找到 Compose 自動建立的 network
- [ ] inspect network
- [ ] 找到 PostgreSQL container IP
- [ ] 理解 Docker DNS
- [ ] 理解 service name 可以當 hostname

之後 API 不會使用：

```text
localhost:5432
```

而是：

```text
postgres:5432
```

因為：

```text
API Container
     │
     │ postgres:5432
     ▼
Docker DNS
     │
     ▼
PostgreSQL Container
```

---

## Phase 1 Definition of Done

不查資料，可以回答：

- [ ] Image vs Container？
- [ ] Service vs Container？
- [ ] `docker run` vs `docker compose up`？
- [ ] Host port vs Container port？
- [ ] Environment Variable 解決什麼？
- [ ] Volume 解決什麼？
- [ ] `down` vs `down -v`？
- [ ] 為什麼 API 之後可以連 `postgres:5432`？
- [ ] `exec` / `logs` / `inspect` 各做什麼？

最後：

- [ ] 從空資料夾重新建立 PostgreSQL Compose 環境

---

# Phase 2 — PostgreSQL + SQL

## Goal

Container 已經不是重點。

開始真正操作 Database。

建立簡化電商模型：

```text
users
products
orders
order_items
```

關係：

```text
users
  │
  │ 1:N
  ▼
orders
  │
  │ 1:N
  ▼
order_items
  │
  │ N:1
  ▼
products
```

---

## 2.1 Schema

TODO：

- [ ] CREATE DATABASE
- [ ] CREATE TABLE
- [ ] PRIMARY KEY
- [ ] FOREIGN KEY
- [ ] NOT NULL
- [ ] UNIQUE
- [ ] DEFAULT
- [ ] CHECK
- [ ] SERIAL / IDENTITY

理解：

```text
PK
FK
Constraint
Relationship
```

---

## 2.2 CRUD SQL

TODO：

- [ ] INSERT
- [ ] SELECT
- [ ] UPDATE
- [ ] DELETE

熟悉：

```sql
WHERE
ORDER BY
LIMIT
OFFSET
```

---

## 2.3 JOIN

TODO：

- [ ] INNER JOIN
- [ ] LEFT JOIN
- [ ] 多 Table JOIN

練習：

```text
查詢：

使用者
+
訂單
+
商品
+
購買數量
```

---

## 2.4 Aggregation

TODO：

- [ ] COUNT
- [ ] SUM
- [ ] AVG
- [ ] MIN
- [ ] MAX
- [ ] GROUP BY
- [ ] HAVING

練習：

```text
找出消費最高的使用者
```

---

## 2.5 Advanced SQL

時間足夠才深入：

- [ ] Subquery
- [ ] CTE
- [ ] Window Function

至少理解：

```sql
WITH ...
```

以及：

```sql
ROW_NUMBER()
RANK()
SUM() OVER (...)
```

---

## 2.6 Index / Query Performance

TODO：

- [ ] CREATE INDEX
- [ ] EXPLAIN
- [ ] EXPLAIN ANALYZE
- [ ] 比較有 Index / 無 Index

核心問題：

> Database 為什麼不用每次掃完整張 table？

---

## Phase 2 Definition of Done

能自己完成：

```text
User
 ↓
Order
 ↓
OrderItem
 ↓
Product
```

並寫 SQL 找：

- [ ] 某個使用者的所有訂單
- [ ] 每張訂單總金額
- [ ] 銷量最高商品
- [ ] 消費最高使用者
- [ ] 沒買過東西的使用者

---

# Phase 3 — FastAPI + PostgreSQL

## Goal

把：

```text
HTTP
```

接到：

```text
Database
```

變成：

```text
Client
  │
  │ HTTP
  ▼
FastAPI
  │
  │ SQL
  ▼
PostgreSQL
```

---

## 3.1 FastAPI

建立：

```text
api/
├── app/
│   ├── main.py
│   ├── routers/
│   ├── models/
│   ├── schemas/
│   └── database.py
└── Dockerfile
```

TODO：

- [ ] 建立 FastAPI project
- [ ] `/health`
- [ ] GET endpoint
- [ ] POST endpoint
- [ ] Path Parameter
- [ ] Query Parameter
- [ ] Request Body
- [ ] Response Model
- [ ] Validation

---

## 3.2 Database Connection

TODO：

- [ ] SQLAlchemy
- [ ] PostgreSQL driver
- [ ] Connection String
- [ ] Session
- [ ] Dependency Injection

理解：

```text
postgresql://
user:password
@
host:port
/
database
```

---

## 3.3 CRUD API

完成：

```text
GET    /users
GET    /users/{id}
POST   /users

GET    /products
POST   /products

GET    /orders
POST   /orders
```

TODO：

- [ ] Create
- [ ] Read
- [ ] Update
- [ ] Delete
- [ ] HTTP Status Code
- [ ] Error Handling

---

## 3.4 Dockerize API

建立 API Dockerfile。

Compose 變成：

```text
services:

  api:

  postgres:
```

架構：

```text
Windows
   │
   │ localhost:8000
   ▼
API Container
   │
   │ postgres:5432
   ▼
PostgreSQL Container
```

TODO：

- [ ] API Dockerfile
- [ ] Build API image
- [ ] API 加入 Compose
- [ ] API → PostgreSQL
- [ ] Port mapping
- [ ] Environment Variables
- [ ] `depends_on`
- [ ] PostgreSQL healthcheck
- [ ] API healthcheck

---

## Phase 3 Definition of Done

只需要：

```bash
docker compose up --build
```

就能得到：

```text
PostgreSQL
+
FastAPI
```

並成功：

```text
POST /users
      ↓
PostgreSQL INSERT

GET /users
      ↓
PostgreSQL SELECT
```

---

# Phase 4 — Backend / API Fundamentals

## Goal

從「能跑」進入安全、可維護、可測試的 Backend API。

## 4.1 HTTP / REST

- [ ] HTTP methods、status codes、headers
- [ ] REST resource design
- [ ] Idempotency
- [ ] Request / response contract

## 4.2 Authentication

- [ ] Password hashing（Argon2 / bcrypt）
- [ ] JWT / Session
- [ ] Access token / refresh token
- [ ] Token expiration
- [ ] Login / logout flow

## 4.3 Authorization

- [ ] Resource ownership
- [ ] Permission checking
- [ ] Role-based access control（RBAC）
- [ ] User / Admin 權限區分

## 4.4 API Security

- [ ] Input validation
- [ ] SQL Injection 防禦（SQLAlchemy / parameterized query）
- [ ] Rate limiting
- [ ] Request limits（request size、file size、JSON size）
- [ ] Pagination / query limits
- [ ] CORS

## 4.5 Middleware

- [ ] Request logging middleware
- [ ] CORS middleware
- [ ] Authentication / request context middleware
- [ ] Middleware execution order

## 4.6 Error Handling

- [ ] Consistent error response format
- [ ] HTTP exception handling
- [ ] 不洩漏內部錯誤與敏感資訊
- [ ] Logging server-side details

## 4.7 Pagination / Filtering / Sorting

- [ ] Page / limit pagination
- [ ] 最大 page size
- [ ] Filtering query parameters
- [ ] Sorting query parameters
- [ ] 防止無限制資料查詢

## 4.8 API Testing

- [ ] pytest
- [ ] API endpoint tests
- [ ] Authentication / authorization tests
- [ ] Validation / error tests
- [ ] Database fixture

## 4.9 Backend Project Structure

- [ ] `main.py`
- [ ] `routers/`
- [ ] `models/`
- [ ] `schemas/`
- [ ] `services/`
- [ ] `dependencies/`
- [ ] `database.py`
- [ ] `tests/`

## 4.10 Alembic Migration

不要再手動修改 Production Schema。

- [ ] 安裝 Alembic
- [ ] Initial migration
- [ ] Upgrade
- [ ] 新增 column
- [ ] 產生 migration
- [ ] Downgrade

理解：

`	ext
Application Version
        +
Database Schema Version
` 

## Phase 4 Definition of Done

可以完成一個具備 authentication、authorization、validation、error handling、pagination、filtering / sorting 與測試的 FastAPI API。

---

# Phase 5 — Security / CI/CD / Deployment

## Goal

讓應用程式可以安全、可重現地建置、部署與監控。

## 5.1 Secrets Management

- [ ] Environment variables
- [ ] `.env` 不提交到 Git
- [ ] `.env.example`
- [ ] Production secrets manager
- [ ] Secret rotation

## 5.2 HTTPS / TLS

- [ ] TLS certificate
- [ ] HTTPS-only production traffic
- [ ] Reverse proxy / TLS termination
- [ ] HTTP to HTTPS redirect

## 5.3 Database Least Privilege

- [ ] 建立專用 application database user
- [ ] 只授予必要的 SELECT / INSERT / UPDATE / DELETE 權限
- [ ] 不使用 PostgreSQL superuser 執行 API
- [ ] Migration user 與 runtime user 分離

## 5.4 Security Headers

- [ ] `Content-Security-Policy`
- [ ] `X-Content-Type-Options`
- [ ] `Strict-Transport-Security`
- [ ] `Referrer-Policy`
- [ ] 依需求設定 `X-Frame-Options`

## 5.5 Logging / Monitoring

- [ ] Structured request logging
- [ ] Error logging
- [ ] Metrics
- [ ] Request count / latency
- [ ] Health checks
- [ ] Alerts
- [ ] Audit log

## 5.6 Dockerize FastAPI

- [ ] Production Dockerfile
- [ ] `.dockerignore`
- [ ] Non-root container user
- [ ] Environment-specific configuration
- [ ] Healthcheck
- [ ] Image tagging
- [ ] Build production image

## 5.7 CI/CD

建立：

```text
.github/
└── workflows/
    └── ci.yml
```

Pipeline：

```text
git push
   ↓
CI
   ├── Checkout
   ├── Install dependencies
   ├── Test
   ├── Security checks
   └── Docker Build
   ↓
CD
   └── Deploy
```

TODO：

- [ ] Automated tests
- [ ] Lint / format checks
- [ ] Dependency / security checks
- [ ] Docker build
- [ ] Image publish
- [ ] Staging deployment
- [ ] Production deployment
- [ ] Rollback strategy

## 5.8 Kubernetes

- [ ] Pod / Deployment
- [ ] Service
- [ ] ConfigMap / Secret
- [ ] Readiness / liveness probes
- [ ] Resource requests / limits
- [ ] Ingress
- [ ] Rolling update

## 5.9 Deployment

- [ ] Staging environment
- [ ] Production environment
- [ ] Database migration during deployment
- [ ] HTTPS / TLS verification
- [ ] Logs / metrics verification
- [ ] Rollback procedure

## Phase 5 Definition of Done

完成一條可重現的流程：

```text
git push
    ↓
CI tests
    ↓
Docker build / publish
    ↓
Deploy
    ↓
HTTPS FastAPI + PostgreSQL
    ↓
Logging / Monitoring
```
# 一週時間分配

## Day 1

```text
Phase 1
Docker + PostgreSQL Environment
```

重點：

```text
Compose
Environment
Port
Volume
Network
```

---

## Day 2

```text
Phase 2
PostgreSQL
```

重點：

```text
Schema
CRUD
JOIN
GROUP BY
CTE
Index
EXPLAIN
```

---

## Day 3

```text
Phase 3
FastAPI
```

重點：

```text
REST API
Pydantic
SQLAlchemy
PostgreSQL
```

---

## Day 4

繼續 Phase 3：

```text
Dockerize FastAPI
        +
Docker Compose
```

做到：

```text
docker compose up --build
```

整套服務起來。

---

## Day 5

```text
Phase 4
Alembic + Testing
```

---

## Day 6

```text
Phase 5
GitHub Actions CI
```

---

## Day 7

整合與補洞。

從零測試：

```text
git clone
   ↓
.env
   ↓
docker compose up --build
   ↓
Migration
   ↓
API Ready
   ↓
Tests Pass
```

如果有剩餘時間：

```text
Prometheus
Grafana
```

---

# 這一週刻意不學

先不要碰：

```text
Kubernetes
Terraform
Ansible
Kafka
RabbitMQ
Microservices
AWS Architecture
ELK
Service Mesh
Helm
ArgoCD
```

不是它們不重要。

而是現在加入它們會破壞這一週最重要的目標：

> 把一個 Application 從 Source Code 一路推到可重現、可測試、可自動 Build 的環境。

---

# 一週最終驗收

最後不要看筆記。

從空資料夾開始，確認自己能回答並實作：

### Docker

- [ ] Image / Container
- [ ] Dockerfile
- [ ] Compose
- [ ] Port
- [ ] Volume
- [ ] Network
- [ ] Environment
- [ ] Healthcheck
- [ ] Logs

### PostgreSQL

- [ ] Schema
- [ ] PK / FK
- [ ] JOIN
- [ ] GROUP BY
- [ ] CTE
- [ ] Index
- [ ] EXPLAIN

### Backend

- [ ] REST
- [ ] FastAPI
- [ ] Validation
- [ ] SQLAlchemy
- [ ] CRUD
- [ ] Error Handling

### Engineering

- [ ] Migration
- [ ] Testing
- [ ] Environment separation

### DevOps

- [ ] Docker Build
- [ ] Docker Compose
- [ ] CI Pipeline
- [ ] Automated Test
- [ ] Basic Monitoring

---

# 最終 Repo

```text
backend-lab/
│
├── compose.yaml
├── .env.example
├── .gitignore
├── README.md
│
├── api/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   └── routers/
│   │
│   ├── alembic/
│   └── tests/
│
├── postgres/
│   ├── schema.sql
│   └── seed.sql
│
├── exercises/
│   └── sql/
│
└── .github/
    └── workflows/
        └── ci.yml
```

# 最重要的學習規則

每一個 Phase 都遵守：

```text
先做
 ↓
出錯
 ↓
讀 Error
 ↓
自己提出 Hypothesis
 ↓
驗證
 ↓
真的卡住再問
```

不要：

```text
看完整教學
↓
Copy
↓
Paste
↓
成功
↓
以為自己會了
```

這個 Lab 的成功標準不是「專案跑起來」。

而是：

> **你可以解釋它為什麼跑得起來，也知道它壞掉時要從哪裡查。**