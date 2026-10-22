FROM ghcr.io/astral-sh/uv:0.12.3 AS uv

FROM python:3.13-slim
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY app ./app
RUN uv sync --frozen --no-dev
COPY alembic.ini ./
COPY migrations ./migrations
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
