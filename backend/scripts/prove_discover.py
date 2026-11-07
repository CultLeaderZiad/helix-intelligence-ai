"""Prove Discover end to end on a non-production database: success, cancel, timeout.

Drives a locally running API and jobs worker over HTTP, exactly as the browser
does, and writes evidence to docs/w8/discover-proof/. It never prints or stores
tokens, passwords, provider keys or connection strings.

Prerequisites (see docs/w8/discover-proof/README.md):
  1. API on 127.0.0.1:8000 and `python workers/jobs/worker.py`, both started with
     backend/.env.local pointing at the Neon dev branch (dev-w8) and with ONE
     authorized non-production provider key in their environment, e.g.
     METAPI_API_KEY, or ADYNTEL_API_KEY + ADYNTEL_EMAIL, or APIFY_API_TOKEN
     (+ APIFY_ENABLED=true), or META_ACCESS_TOKEN.
  2. For the timeout scenario, start both with DISCOVER_JOB_DEADLINE_S=20.
  3. A test account on dev-w8 whose workspace is granted `discover`.

Environment for this script:
  HELIX_PROOF_EMAIL, HELIX_PROOF_PASSWORD   the granted test account
  HELIX_PROOF_PROVIDER                      which key the servers were started with
                                            (metapi | adyntel | apify | meta_official)
  HELIX_PROOF_QUERY                         optional, default "nike.com"

Usage:
  python scripts/prove_discover.py --scenario success|cancel|timeout
Exit codes: 0 = expectation met, 1 = expectation failed, 2 = not configured.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

PROVIDERS = {"metapi", "adyntel", "apify", "meta_official"}
TERMINAL = {"succeeded", "failed", "cancelled", "timed_out"}
EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "docs" / "w8" / "discover-proof"


def _require_env() -> dict:
    missing = [name for name in ("HELIX_PROOF_EMAIL", "HELIX_PROOF_PASSWORD", "HELIX_PROOF_PROVIDER") if not os.getenv(name)]
    if missing:
        print("NOT CONFIGURED: set " + ", ".join(missing) + " (see docs/w8/discover-proof/README.md)", file=sys.stderr)
        sys.exit(2)
    provider = os.environ["HELIX_PROOF_PROVIDER"].strip().lower()
    if provider not in PROVIDERS:
        print(f"NOT CONFIGURED: HELIX_PROOF_PROVIDER must be one of {sorted(PROVIDERS)}", file=sys.stderr)
        sys.exit(2)
    return {
        "email": os.environ["HELIX_PROOF_EMAIL"],
        "password": os.environ["HELIX_PROOF_PASSWORD"],
        "provider": provider,
        "query": os.getenv("HELIX_PROOF_QUERY", "nike.com"),
    }


def _require_loopback(api: str) -> None:
    host = urlsplit(api).hostname or ""
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("REFUSED: the proof only drives a local API (127.0.0.1); never a hosted environment.", file=sys.stderr)
        sys.exit(2)


class Proof:
    def __init__(self, api: str, cfg: dict):
        self.api = api.rstrip("/")
        self.cfg = cfg
        self.client = httpx.Client(timeout=60)
        self.timeline: list[dict] = []
        self.token = None

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def sign_in(self) -> dict:
        r = self.client.post(f"{self.api}/auth/sign-in", json={"email": self.cfg["email"], "password": self.cfg["password"]})
        if r.status_code != 200:
            raise SystemExit(f"sign-in failed: HTTP {r.status_code}")
        session = r.json()
        self.token = session["access_token"]
        if not (session.get("feature_flags") or {}).get("discover"):
            raise SystemExit("the proof account's workspace is not granted `discover`")
        return {"credit_balance": session.get("credit_balance"), "access_status": session.get("access_status")}

    def credits(self) -> float | None:
        return self.client.get(f"{self.api}/auth/session", headers=self._headers()).json().get("credit_balance")

    def start(self) -> str:
        r = self.client.post(f"{self.api}/discovery/jobs", headers=self._headers(), json={"query": self.cfg["query"], "filters": {}})
        if r.status_code != 200:
            raise SystemExit(f"search was not accepted: HTTP {r.status_code} {r.json().get('detail')}")
        job = r.json()
        self._record(job)
        return job["job_id"]

    def _record(self, job: dict) -> None:
        self.timeline.append({
            "at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": job.get("status"),
            "stage": job.get("stage"),
            "records_found": job.get("records_found"),
            "failure_kind": job.get("failure_kind"),
        })

    def poll(self, job_id: str, *, until_running: bool = False, limit_s: int = 900) -> dict:
        started = time.monotonic()
        while True:
            job = self.client.get(f"{self.api}/discovery/jobs/{job_id}", headers=self._headers()).json()
            if not self.timeline or self.timeline[-1]["status"] != job.get("status") or self.timeline[-1]["stage"] != job.get("stage"):
                self._record(job)
            if job.get("status") in TERMINAL or (until_running and job.get("status") == "running"):
                return job
            if time.monotonic() - started > limit_s:
                return job
            time.sleep(3)

    def results(self, job_id: str) -> dict:
        page = self.client.get(f"{self.api}/discovery/jobs/{job_id}/results", headers=self._headers(), params={"page": 1}).json()
        items = page.get("items") or []
        return {
            "total": page.get("total"),
            "first_page": len(items),
            "with_days_active": sum(1 for c in items if c.get("days_active") is not None),
            "with_meta_reach": sum(1 for c in items if (c.get("metrics") or {}).get("impressions_est") is not None),
            "platforms": sorted({c.get("platform") for c in items if c.get("platform")}),
        }


def run(scenario: str, api: str) -> int:
    cfg = _require_env()
    _require_loopback(api)
    proof = Proof(api, cfg)
    session = proof.sign_in()
    before = session["credit_balance"]
    job_id = proof.start()
    outcome: dict = {}
    if scenario == "success":
        job = proof.poll(job_id)
        outcome["results"] = proof.results(job_id) if job.get("status") == "succeeded" else None
        expected = job.get("status") == "succeeded" and (outcome["results"] or {}).get("total", 0) > 0
    elif scenario == "cancel":
        proof.poll(job_id, until_running=True, limit_s=120)
        r = proof.client.post(f"{proof.api}/discovery/jobs/{job_id}/cancel", headers=proof._headers())
        outcome["cancel_http"] = r.status_code
        job = proof.poll(job_id, limit_s=180)
        expected = job.get("status") == "cancelled"
    else:  # timeout
        job = proof.poll(job_id, limit_s=900)
        expected = job.get("status") == "timed_out"
    after = proof.credits()
    evidence = {
        "scenario": scenario,
        "passed": bool(expected),
        "provider_configured": cfg["provider"],
        "query": cfg["query"],
        "job_id": job_id,
        "final_status": job.get("status"),
        "failure_kind": job.get("failure_kind"),
        "deadline_at": job.get("deadline_at"),
        "credits_before": before,
        "credits_after": after,
        "timeline": proof.timeline,
        **outcome,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = EVIDENCE_DIR / f"{stamp}-{scenario}.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"{scenario}: {'PASS' if expected else 'FAIL'} (status={job.get('status')}) -> {path.relative_to(EVIDENCE_DIR.parents[2])}")
    return 0 if expected else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", choices=["success", "cancel", "timeout"], required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8000/api")
    args = parser.parse_args()
    sys.exit(run(args.scenario, args.api))


if __name__ == "__main__":
    main()
