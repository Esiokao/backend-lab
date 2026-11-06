# Backend Lab

Full-stack e-commerce demo — session-based auth, transactional outbox, real-time notifications, three-layer test suite.

```
backend/    FastAPI · SQLAlchemy · PostgreSQL · Redis · RQ
frontend/   Vue 3 · TypeScript · Vite · Zod · pnpm
e2e/        Playwright (independent deliverable)
docs/       ADRs (0001 same-origin gateway · 0002 sessions over JWT)
```

## Quick Start

Prereqs: Docker, uv, Node 22 + pnpm, openssl.

```bash
# one-shot setup: .env with random secrets, self-signed certs,
# deps, full compose stack, migrations, frontend deps
./scripts/setup-dev.sh          # Windows: .\scripts\setup-dev.ps1

cd frontend && pnpm run dev     # app: http://localhost:5173 (API: :8000)
```

Secrets in `.env` are random local values (never commit yours);
`.env.example` documents every variable.

## Testing

```bash
uv run pytest                               # backend (needs postgres+redis)
cd frontend && pnpm test                    # unit
cd e2e && pnpm i && pnpm test               # e2e (needs full stack)
```

## CI

code-check → testing → docker-build → publish (GHCR) → deploy + smoke test.
