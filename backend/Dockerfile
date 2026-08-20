# Build context is the REPO ROOT (not backend/), because this image needs
# the sibling packages/afm_core and packages/ml libraries too:
#   docker build -f backend/Dockerfile -t afm-backend .
# docker-compose.yml sets `context: .` / `dockerfile: backend/Dockerfile`
# for you, so you normally don't need to invoke this by hand.

FROM python:3.11-slim

WORKDIR /app

# afm_core and ml are small pure-Python packages; installing them first
# (before the rest of backend requirements) means Docker layer caching
# still works if only backend/app changes.
COPY packages/afm_core /app/packages/afm_core
COPY packages/ml /app/packages/ml
COPY backend/requirements-docker.txt /app/backend/requirements-docker.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e /app/packages/afm_core -e /app/packages/ml \
    && pip install --no-cache-dir -r /app/backend/requirements-docker.txt

COPY backend/app /app/backend/app
WORKDIR /app/backend

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/backend/data \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    AFM_DATA_DIR=/app/backend/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
