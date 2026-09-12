"""Live production Discover probe via a disposable account. No secrets printed."""
import json
import time
import uuid
import urllib.error
import urllib.request

BASE = "https://helix-intelligence-ai.onrender.com/api"
QUERY = "Real madrid"


def req(method, path, body=None, token=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw[:400]}
        return e.code, parsed


def main():
    email = f"probe-{uuid.uuid4().hex[:10]}@example.com"
    password = "ProbeTest123!"
    status, payload = req(
        "POST",
        "/auth/sign-up",
        {"email": email, "password": password, "name": "Discover Probe"},
    )
    print("signup", status, list(payload.keys()))
    token = payload.get("access_token")
    if not token:
        status, payload = req("POST", "/auth/sign-in", {"email": email, "password": password})
        print("signin", status, list(payload.keys()))
        token = payload.get("access_token")
    if not token:
        print("NO_TOKEN", payload)
        return

    status, session = req("GET", "/auth/session", token=token)
    print("session", status, session.get("email"), session.get("role"))

    status, job = req("POST", "/discovery/jobs", {"query": QUERY, "filters": {}}, token=token)
    print("search", status, {k: job.get(k) for k in ("id", "status", "stage", "stage_label", "error", "error_msg")})
    job_id = job.get("id") or job.get("job_id")
    if not job_id:
        print("NO_JOB", job)
        return

    last = {}
    for i in range(40):
        time.sleep(3)
        status, last = req("GET", f"/discovery/jobs/{job_id}", token=token)
        print(
            f"poll {i+1}",
            last.get("status"),
            last.get("stage"),
            (last.get("stage_label") or "")[:120],
            "records",
            last.get("record_count"),
        )
        if last.get("status") in ("succeeded", "failed", "complete"):
            break

    status, results = req("GET", f"/discovery/jobs/{job_id}/results", token=token)
    items = results.get("items") or results.get("creatives") or results.get("results") or []
    if isinstance(results, list):
        items = results
    print("results_status", status, "n", len(items) if isinstance(items, list) else type(results))
    if isinstance(items, list) and items:
        first = items[0]
        print(
            "first",
            {
                "headline": (first.get("headline") or "")[:90],
                "brand": first.get("brand_name"),
                "domain": first.get("landing_domain"),
                "source": first.get("data_source"),
            },
        )
    else:
        print("results_keys", list(results.keys()) if isinstance(results, dict) else results)


if __name__ == "__main__":
    main()
