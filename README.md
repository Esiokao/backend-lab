# Backend Lab

Full-stack e-commerce demo — session-based auth, transactional outbox, real-time notifications, three-layer test suite.

```
backend/    FastAPI · SQLAlchemy · PostgreSQL · Redis · RQ
frontend/   Vue 3 · TypeScript · Vite · Zod · pnpm
e2e/        Playwright (independent deliverable)
docs/       ADRs (0001 same-origin gateway · 0002 sessions over JWT)
```

## Quick Start

```bash
docker compose up -d postgres redis
uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --port 8000     # workers: scripts/start-dev.ps1
cd frontend && pnpm install && pnpm dev     # :5173 proxies /api
```

## Testing

```bash
uv run pytest                               # backend (needs postgres+redis)
cd frontend && pnpm test                    # unit
cd e2e && pnpm i && pnpm test               # e2e (needs full stack)
```

## CI

code-check → testing → docker-build → publish (GHCR) → deploy + smoke test.
