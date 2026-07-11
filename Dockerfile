# syntax=docker/dockerfile:1
FROM python:3.12.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN python -m venv /opt/venv

COPY pyproject.toml requirements.lock README.md ./
COPY app ./app
RUN /opt/venv/bin/pip install --no-cache-dir --constraint requirements.lock .

FROM python:3.12.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./

USER app

STOPSIGNAL SIGTERM

CMD ["python", "-m", "app.main"]
