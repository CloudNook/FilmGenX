#!/bin/sh
set -eu

echo "[backend] running database migrations..."
uv run alembic upgrade head

echo "[backend] starting api server..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
