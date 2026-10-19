# Build from the backend/ directory:
#   docker build -f workers/scrapling/Dockerfile -t helix-leadgen-worker .
# Official multi-arch Scrapling image (library + browser tooling).
# Verified against Docker Hub's public tag API; immutable manifest index.
ARG SCRAPLING_IMAGE=pyd4vinci/scrapling@sha256:1d876879813759959bc4ba6fbb1ce8247ebbc2b67eee77b140baf7c80af6ae6b
FROM ${SCRAPLING_IMAGE}

WORKDIR /app

# Python deps for the Helix backend app (worker imports app.*)
COPY requirements.txt ./
COPY workers/scrapling/requirements.txt ./worker-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r worker-requirements.txt \
    && scrapling install

# Full backend tree (models, services, config). No frontend code here.
COPY . .

ENV PYTHONPATH=/app \
    SCRAPLING_WORKER_ENABLED=true \
    SCRAPLING_ROBOTS_OBEY=true

CMD ["python", "workers/scrapling/worker.py"]
