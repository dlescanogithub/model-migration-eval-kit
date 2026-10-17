FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV LIVE_MODE=0

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY config ./config
COPY data ./data

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "migration_eval"]
CMD ["compare", "--old", "fake-old", "--new", "fake-new", "--runs", "5", "--today", "2026-10-17"]
