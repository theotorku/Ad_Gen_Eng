FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=8000 \
    AD_ENGINE_DB_BACKEND=sqlite \
    AD_ENGINE_SQLITE_PATH=/app/data/ad_engine.db \
    OPENAI_IMAGE_OUTPUT_DIR=/app/data/generated_assets

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py sample_brief.json ./
COPY src ./src
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data/generated_assets \
    && chown -R appuser:appuser /app \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "main.py", "serve"]
