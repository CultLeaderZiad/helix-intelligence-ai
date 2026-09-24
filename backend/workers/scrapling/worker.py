"""Scrapling worker - claims LeadGenJob rows from the DB and runs the pipeline.

Run standalone (host dev):
    cd backend && SCRAPLING_WORKER_ENABLED=true python workers/scrapling/worker.py

Run in Docker (preferred):
    docker build -f workers/scrapling/Dockerfile -t helix-leadgen-worker .
    docker run --env-file .env helix-leadgen-worker

Environment required:
    DATABASE_URL, SECRET_KEY        (DB claim + heartbeat token, shared with API)
    SCRAPLING_WORKER_ENABLED=true   (enables POST /jobs enqueue + heartbeat endpoint)
    HELIX_API_BASE_URL              (default http://localhost:8000/api)

The API process never imports Scrapling: only THIS process does.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import signal
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Make the backend package importable when launched as a plain script.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("leadgen.worker")

BOOT_ID = uuid.uuid4().hex[:12]
HEARTBEAT_INTERVAL_S = 30
POLL_INTERVAL_S = 3

_stop = threading.Event()


def _worker_token() -> str:
    return hashlib.sha256(((os.environ.get("SECRET_KEY") or "") + "leadgen-worker").encode("utf-8")).hexdigest()


def _api_base() -> str:
    return (os.environ.get("HELIX_API_BASE_URL") or "http://localhost:8000/api").rstrip("/")


def _scrapling_info() -> dict:
    import importlib.util
    available = importlib.util.find_spec("scrapling") is not None
    version = None
    browsers = False
    if available:
        try:
            import scrapling
            version = getattr(scrapling, "__version__", None) or "unknown"
        except Exception:
            version = "unknown"
        # Browsers come from `scrapling install`; import success is the signal.
        try:
            import scrapling.engine  # noqa: F401
            browsers = True
        except Exception:
            browsers = False
    return {"version": version, "browsers_ready": browsers, "engines": ["http", "stealth", "dynamic"]}


def _heartbeat_once(info: dict) -> None:
    import httpx
    payload = {
        "version": info["version"],
        "engines": info["engines"],
        "browsers_ready": info["browsers_ready"],
        "proxy": "configured" if (os.environ.get("SCRAPLING_PROXY_LIST") or "").strip() else "off",
        "boot_id": BOOT_ID,
    }
    try:
        httpx.post(
            f"{_api_base()}/scout/leadgen/worker/heartbeat",
            json=payload,
            headers={"X-Worker-Token": _worker_token()},
            timeout=5.0,
        ).raise_for_status()
    except Exception as e:
        logger.debug("heartbeat failed: %s", e)


def _heartbeat_loop(info: dict) -> None:
    while not _stop.is_set():
        _heartbeat_once(info)
        _stop.wait(HEARTBEAT_INTERVAL_S)

def _claim_next_job() -> str | None:
    """Atomically claim one queued job: queued -> running + owner_boot_id.
    SKIP LOCKED keeps multiple worker replicas from double-claiming."""
    from sqlalchemy import update
    from app.db.session import async_session_maker
    from app.models.leadgen import LeadGenJob  # noqa: F401 - registers tables

    async def _claim():
        async with async_session_maker() as db:
            from sqlalchemy import select
            job_id = (await db.execute(
                select(LeadGenJob.id)
                .where(LeadGenJob.status == "queued")
                .order_by(LeadGenJob.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )).scalar_one_or_none()
            if not job_id:
                return None
            await db.execute(
                update(LeadGenJob)
                .where(LeadGenJob.id == job_id, LeadGenJob.status == "queued")
                .values(status="running", owner_boot_id=f"claimed:{BOOT_ID}")
            )
            await db.commit()
            return job_id

    return asyncio.run(_claim())


def _serve_health(info: dict) -> None:
    """Tiny /health endpoint so SCRAPLING_WORKER_URL ping works."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.rstrip("/").endswith("/health"):
                body = json.dumps({**info, "boot_id": BOOT_ID, "worker": "online"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass  # silence default access log

    port = int(os.environ.get("SCRAPLING_WORKER_HEALTH_PORT", "8091"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("worker health server on :%d/health", port)


def main() -> None:
    # Fail fast on required config (the worker, not the API, needs these)
    for var in ("DATABASE_URL", "SECRET_KEY"):
        if not os.environ.get(var):
            print(f"FATAL: {var} environment variable is required", file=sys.stderr)
            sys.exit(1)

    os.environ.setdefault("SCRAPLING_WORKER_ENABLED", "true")
    os.environ.setdefault("SCRAPLING_ROBOTS_OBEY", "true")

    # Deferred: app imports happen only here, never in the API boot path.
    from app.services import scrapling_engine as engine
    from app.services.leadgen_pipeline import run_leadgen_job

    info = _scrapling_info()
    if not engine.is_available():
        logger.warning(
            "Scrapling NOT importable - jobs will fail loudly. "
            "Install with: pip install 'scrapling[fetchers]' && scrapling install"
        )
    else:
        logger.info("worker ready - scrapling=%s - browsers_ready=%s", info["version"], info["browsers_ready"])

    _serve_health(info)
    threading.Thread(target=_heartbeat_loop, args=(info,), daemon=True).start()

    signal.signal(signal.SIGTERM, lambda *_: _stop.set())
    signal.signal(signal.SIGINT, lambda *_: _stop.set())

    while not _stop.is_set():
        try:
            job_id = _claim_next_job()
            if job_id:
                logger.info("claimed job %s", job_id)
                asyncio.run(run_leadgen_job(job_id))
            else:
                _stop.wait(POLL_INTERVAL_S)
        except Exception as e:
            logger.exception("worker loop error: %s", e)
            _stop.wait(POLL_INTERVAL_S)

    logger.info("worker stopped")


if __name__ == "__main__":
    main()
