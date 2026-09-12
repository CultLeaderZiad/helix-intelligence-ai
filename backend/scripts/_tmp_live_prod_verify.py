"""Live production Discover verification. Talks only to the deployed API."""
from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request

BASE = "https://helix-intelligence-ai.onrender.com/api"
EMAIL = f"liveverify_{int(time.time())}_{secrets.token_hex(3)}@example.com"
PASSWORD = secrets.token_urlsafe(16)
OUT = os.path.join(os.path.dirname(__file__), "_tmp_live_prod_verify.json")


def req(method: str, path: str, body=None, token=None, timeout=60):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw[:800]}
        return e.code, parsed


def poll_job(token, job_id, label, seconds=240):
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        status, job = req("GET", f"/discovery/jobs/{job_id}", token=token)
        last = {"http": status, "job": job}
        st = (job or {}).get("status")
        print(f"  [{label}] {st} stage={job.get('stage')} records={job.get('records_found')} progress={job.get('progress')}")
        if st in ("succeeded", "failed"):
            return last
        time.sleep(6)
    return last


def main():
    evidence = {"email": EMAIL, "base": BASE, "steps": {}}

    print("=== signup ===")
    code, session = req("POST", "/auth/sign-up", {"email": EMAIL, "password": PASSWORD, "name": "Live Verify"})
    token = session.get("access_token")
    evidence["steps"]["signup"] = {
        "http": code,
        "user_id": session.get("user_id"),
        "credit_balance": session.get("credit_balance"),
        "role": session.get("role"),
        "has_token": bool(token),
    }
    print(json.dumps(evidence["steps"]["signup"], indent=2))
    if not token:
        json.dump(evidence, open(OUT, "w"), indent=2)
        sys.exit(1)

    def session_balance():
        c, s = req("GET", "/auth/session", token=token)
        return c, s.get("credit_balance")

    searches = [("nike.com", "well_known_domain"), ("shopify.com", "obscure_domain")]
    for query, kind in searches:
        print(f"\n=== discover {kind}: {query} ===")
        _, bal_before = session_balance()
        t0 = time.time()
        code, job = req(
            "POST",
            "/discovery/jobs",
            {"query": query, "platform": "all", "format": "all", "max_records": 10},
            token=token,
            timeout=90,
        )
        print(f"  trigger http={code} job_id={job.get('job_id')} status={job.get('status')} records={job.get('records_found')}")
        polled = poll_job(token, job.get("job_id"), query)
        done = (polled or {}).get("job") or {}
        rcode, results = req("GET", f"/discovery/jobs/{job.get('job_id')}/results?page=1&page_size=8", token=token)
        items = (results or {}).get("items") or []
        slim = []
        for it in items[:5]:
            slim.append({
                "id": it.get("id"),
                "headline": it.get("headline"),
                "body": (it.get("body") or "")[:240],
                "cta": it.get("cta"),
                "platform": it.get("platform"),
                "format": it.get("format"),
                "landing_domain": it.get("landing_domain"),
                "data_source": it.get("data_source"),
                "brand_name": it.get("brand_name"),
            })
        _, bal_after = session_balance()
        evidence["steps"][kind] = {
            "query": query,
            "trigger_http": code,
            "trigger_job": {k: job.get(k) for k in ("job_id", "status", "records_found", "stage", "stage_label")},
            "final_job": {k: done.get(k) for k in ("job_id", "status", "records_found", "stage", "stage_label", "error", "failure_kind", "elapsed_ms")},
            "results_http": rcode,
            "results_total": (results or {}).get("total"),
            "sample": slim,
            "credits_before": bal_before,
            "credits_after": bal_after,
            "credit_delta": None if bal_before is None or bal_after is None else round(bal_after - bal_before, 2),
            "elapsed_s": round(time.time() - t0, 1),
        }
        print(json.dumps({k: evidence["steps"][kind][k] for k in ("final_job", "results_total", "credit_delta", "sample")}, indent=2))

    json.dump(evidence, open(OUT, "w"), indent=2)
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
