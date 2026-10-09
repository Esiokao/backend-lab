#!/bin/sh
set -eu

# Apply database migrations before starting the API.
alembic upgrade head

# Replace the shell process with Uvicorn.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
