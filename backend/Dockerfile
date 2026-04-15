FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY uv.lock pyproject.toml ./

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev

COPY . .

RUN chmod +x /app/scripts/docker-backend.sh

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000
