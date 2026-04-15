# syntax=docker/dockerfile:1
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# BuildKit pip cache: packages are cached between rebuilds (~30s after first build)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["uvicorn", "market_insights.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
