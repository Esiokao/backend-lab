# Backend Lab — 本地開發環境一鍵設置（Windows PowerShell）
# 用法：在 repo 根目錄執行  .\scripts\setup-dev.ps1
# 做什麼：.env 生成（隨機 secrets）→ 自簽憑證 → 後端依賴 → docker compose 全套
#         → migrations → 前端依賴。跑完後：pnpm run dev（frontend/）即可開發。

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function New-RandomHex([int]$bytes = 32) {
    -join ((1..($bytes * 2)) | ForEach-Object { "{0:x}" -f (Get-Random -Max 16) })
}

# ── 1. .env ──
if (Test-Path .env) {
    Write-Host ".env 已存在——跳過生成（要重建請先刪除 .env）" -ForegroundColor Yellow
} else {
    $pg  = New-RandomHex 16
    $app = New-RandomHex 16
    $jwt = New-RandomHex 32
    (Get-Content .env.example -Raw) `
        -replace "CHANGE_ME", $pg `
        -replace "app_user:CHANGE_ME", "app_user:$app" `
        -replace "JWT_SECRET=CHANGE_ME", "JWT_SECRET=$jwt" |
        Set-Content .env -NoNewline
    # API_DB_PASSWORD 與 admin 密碼不同：上面第一個 replace 會把 app_user:CHANGE_ME
    # 蓋成 admin 密碼——再修正成獨立的 app 密碼。
    (Get-Content .env -Raw) -replace "API_DB_PASSWORD=$pg", "API_DB_PASSWORD=$app" |
        Set-Content .env -NoNewline
    Write-Host ".env 生成 ✓（secrets 為隨機值，僅保護本機容器）" -ForegroundColor Green
}

# ── 2. 本地自簽憑證（nginx 443 用；正式憑證由 CD 注入，不經過這裡）──
if (-not (Test-Path certs/server.key)) {
    openssl req -x509 -newkey rsa:2048 -nodes -days 365 `
        -keyout certs/server.key -out certs/server.crt `
        -subj "/CN=localhost" 2>$null
    Write-Host "自簽憑證生成 ✓" -ForegroundColor Green
} else {
    Write-Host "憑證已存在——跳過" -ForegroundColor Yellow
}

# ── 3. 後端依賴 ──
uv sync --all-groups
Write-Host "python deps ✓" -ForegroundColor Green

# ── 4. docker compose 全套（首建會 build 幾分鐘）──
docker compose up -d --build
Write-Host "compose stack ✓" -ForegroundColor Green

# ── 5. migrations（讀 .env 的 MIGRATION_DATABASE_URL）──
uv run alembic upgrade head
Write-Host "migrations ✓" -ForegroundColor Green

# ── 6. 前端依賴 ──
Push-Location frontend
pnpm install --frozen-lockfile
Pop-Location
Write-Host "frontend deps ✓" -ForegroundColor Green

Write-Host ""
Write-Host "完成！開發方式：" -ForegroundColor Cyan
Write-Host "  後端 API   docker compose 已起（localhost:8000/health）"
Write-Host "  前端       cd frontend ; pnpm run dev → localhost:5173"
Write-Host "  測試       uv run pytest -q -m 'not deployment'"
Write-Host "  e2e        cd e2e ; pnpm exec playwright test"
