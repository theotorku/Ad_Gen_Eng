FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=8000 \
    AD_ENGINE_DB_BACKEND=sqlite \
    AD_ENGINE_SQLITE_PATH=/app/data/ad_engine.db \
    OPENAI_IMAGE_OUTPUT_DIR=/app/data/generated_assets

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py sample_brief.json ./
COPY src ./src

RUN mkdir -p /app/data/generated_assets \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["python", "main.py", "serve"]
