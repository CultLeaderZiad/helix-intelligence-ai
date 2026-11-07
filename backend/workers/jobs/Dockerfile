# Helix jobs worker (Discover and Monitor work items, job reconciliation).
# Build from the backend/ directory:
#   docker build -f workers/jobs/Dockerfile -t helix-jobs-worker .
# No browser and no scraping framework: the same Python dependencies as the API.
FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER nobody
CMD ["python", "workers/jobs/worker.py"]
