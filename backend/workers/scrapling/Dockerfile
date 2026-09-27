# Build from the backend/ directory:
#   docker build -f workers/scrapling/Dockerfile -t helix-leadgen-worker .
# Base: official Scrapling image (ships the library + browser tooling).
ARG SCRAPLING_IMAGE=ghcr.io/d4vinci/scrapling:latest
FROM ${SCRAPLING_IMAGE}

WORKDIR /app

# Python deps for the Helix backend app (worker imports app.*)
COPY requirements.txt ./
COPY workers/scrapling/requirements.txt ./worker-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r worker-requirements.txt \
    && (scrapling install || echo "WARN: scrapling install failed — stealth/dynamic engines need browsers")

# Full backend tree (models, services, config). No frontend code here.
COPY . .

ENV PYTHONPATH=/app \
    SCRAPLING_WORKER_ENABLED=true \
    SCRAPLING_ROBOTS_OBEY=true

CMD ["python", "workers/scrapling/worker.py"]
