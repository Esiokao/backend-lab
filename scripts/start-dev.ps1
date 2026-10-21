$repo = Split-Path $PSScriptRoot -Parent

Start-Process uv -WorkingDirectory $repo -ArgumentList @(
    "run", "uvicorn", "app.main:app", "--reload"
)

Start-Process uv -WorkingDirectory $repo -ArgumentList @(
    "run", "python", "-m", "app.core.outbox_dispatcher"
)

Start-Process uv -WorkingDirectory $repo -ArgumentList @(
    "run", "rq", "worker", "--worker-class", "rq.worker.SimpleWorker", "notifications"
)

Write-Host "Started API, Outbox Dispatcher, and notifications Worker."
