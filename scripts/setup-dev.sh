#!/usr/bin/env bash
# Backend Lab — 本地開發環境一鍵設置（macOS / Linux / WSL）
# 用法：bash scripts/setup-dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."

random_hex() { openssl rand -hex "$1"; }

# ── 1. .env ──
if [ -f .env ]; then
  echo ".env 已存在——跳過生成（要重建請先刪除 .env）"
else
  PG="$(random_hex 16)"
  APP="$(random_hex 16)"
  JWT="$(random_hex 32)"
  sed -e "s/CHANGE_ME/$PG/g" \
      -e "s/app_user:CHANGE_ME/app_user:$APP/" \
      -e "s/API_DB_PASSWORD=$PG/API_DB_PASSWORD=$APP/" \
      -e "s/JWT_SECRET=CHANGE_ME/JWT_SECRET=$JWT/" \
      .env.example > .env
  echo ".env 生成 ✓（secrets 為隨機值，僅保護本機容器）"
fi

# ── 2. 本地自簽憑證（nginx 443 用）──
if [ ! -f certs/server.key ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -keyout certs/server.key -out certs/server.crt \
    -subj "/CN=localhost" 2>/dev/null
  echo "自簽憑證生成 ✓"
else
  echo "憑證已存在——跳過"
fi

# ── 3. 後端依賴 ──
uv sync --all-groups
echo "python deps ✓"

# ── 4. docker compose 全套（首建會 build 幾分鐘）──
docker compose up -d --build
echo "compose stack ✓"

# ── 5. migrations ──
uv run alembic upgrade head
echo "migrations ✓"

# ── 6. 前端依賴 ──
(cd frontend && pnpm install --frozen-lockfile)
echo "frontend deps ✓"

echo ""
echo "完成！開發方式："
echo "  後端 API   docker compose 已起（localhost:8000/health）"
echo "  前端       cd frontend && pnpm run dev → localhost:5173"
echo "  測試       uv run pytest -q -m 'not deployment'"
echo "  e2e        cd e2e && pnpm exec playwright test"
