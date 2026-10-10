FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser \
    && pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts/start.sh ./scripts/start.sh
COPY scripts/provision_roles.py ./scripts/provision_roles.py

RUN chmod 755 ./scripts/start.sh

USER appuser

# Single healthcheck definition shared by dev and prod Compose:
# compose.prod.yaml gates Nginx on api `service_healthy`.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["./scripts/start.sh"]
