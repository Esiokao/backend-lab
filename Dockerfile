FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Create a non-root user and install uv.
RUN adduser --disabled-password --gecos "" appuser \
    && pip install --no-cache-dir uv

# Install locked production dependencies.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy Alembic configuration and migrations.
COPY alembic.ini ./
COPY alembic ./alembic

# Copy application code.
COPY app ./app

# Copy startup and database-role provisioning scripts.
COPY scripts/start.sh ./scripts/start.sh
COPY scripts/provision_roles.py ./scripts/provision_roles.py

RUN chmod 755 ./scripts/start.sh

# Run the API container as a non-root user.
USER appuser

CMD ["./scripts/start.sh"]
