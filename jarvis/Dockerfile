FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    gnupg \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[dev]"

COPY jarvis ./jarvis
COPY config ./config
COPY goldens ./goldens
COPY migrations ./migrations

RUN useradd -m -u 1001 jarvis && chown -R jarvis:jarvis /app
USER jarvis

EXPOSE 8080

CMD ["python", "-m", "jarvis"]
