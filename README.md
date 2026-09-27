# Backend Lab

FastAPI、PostgreSQL、Alembic 與 Docker Compose 的可重現後端練習。

## Run

1. Copy `.env.example` to `.env` and choose a local `JWT_SECRET`.
2. Start the full stack:

   ```powershell
   docker compose up --build
   ```

3. Verify the two probes:

   ```powershell
   Invoke-RestMethod http://localhost:8000/health
   Invoke-RestMethod http://localhost:8000/ready
   ```

`/health` means the API process responds. `/ready` also verifies that the API can execute `SELECT 1` against PostgreSQL.

## Development checks

```powershell
uv sync --all-groups
uv run pytest -q
uv run alembic upgrade head
```

The CI workflow repeats migration, tests, and Docker build on every push and pull request. PostgreSQL schema changes must be Alembic migrations; the application does not call `Base.metadata.create_all()`.
