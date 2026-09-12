import json, os, secrets, time, urllib.error, urllib.request

BASE = "https://helix-intelligence-ai.onrender.com/api"
EMAIL = f"livesim_{int(time.time())}_{secrets.token_hex(2)}@example.com"
PASSWORD = secrets.token_urlsafe(16)
CREATIVE = "e1235cef-afcf-4b52-aea7-a3d2000a15f2"
OUT = os.path.join(os.path.dirname(__file__), "_tmp_live_sim.json")
SEGS = ["price_sensitive_skeptic", "trend_driven_gen_z", "cautious_first_time_buyer"]


def req(method, path, body=None, token=None, timeout=180):
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


def main():
    ev = {"email": EMAIL, "creative_id": CREATIVE}
    code, session = req("POST", "/auth/sign-up", {"email": EMAIL, "password": PASSWORD, "name": "Live Sim"})
    token = session.get("access_token")
    ev["signup"] = {"http": code, "user_id": session.get("user_id"), "credits": session.get("credit_balance")}
    print("signup", ev["signup"])
    if not token:
        json.dump(ev, open(OUT, "w"), indent=2)
        return

    def bal():
        _, s = req("GET", "/auth/session", token=token)
        return s.get("credit_balance")

    before = bal()
    print("credits before success attempt", before)
    t0 = time.time()
    code, report = req(
        "POST",
        f"/simulation/creatives/{CREATIVE}/simulate",
        {"segment_ids": SEGS},
        token=token,
        timeout=180,
    )
    after = bal()
    ev["success"] = {
        "http": code,
        "elapsed_s": round(time.time() - t0, 1),
        "credits_before": before,
        "credits_after": after,
        "credit_delta": None if before is None or after is None else round(after - before, 2),
        "model_version": report.get("model_version") if isinstance(report, dict) else None,
        "data_source": report.get("data_source") if isinstance(report, dict) else None,
        "detail": report.get("detail") if isinstance(report, dict) else None,
        "reactions": [
            {
                "segment_id": r.get("segment_id"),
                "segment_label": r.get("segment_label"),
                "appeal_score": r.get("appeal_score"),
                "objections": r.get("objections"),
                "confusing_claims": r.get("confusing_claims"),
                "credibility_assessment": r.get("credibility_assessment"),
                "compliance_risks": r.get("compliance_risks"),
            }
            for r in (report.get("segment_reactions") or [])
        ] if code == 200 else None,
        "recommended_angles": report.get("recommended_angles") if code == 200 else None,
    }
    print("success http", ev["success"]["http"], "delta", ev["success"]["credit_delta"], "model", ev["success"]["model_version"])

    # Forced failure: bogus BYOK should fail the provider path.
    before2 = bal()
    code2, fail = req(
        "POST",
        f"/simulation/creatives/{CREATIVE}/simulate",
        {
            "segment_ids": SEGS,
            "byok_key": "sk-this-key-is-intentionally-invalid",
            "byok_provider": "groq",
        },
        token=token,
        timeout=90,
    )
    after2 = bal()
    ev["forced_failure"] = {
        "http": code2,
        "detail": fail.get("detail") if isinstance(fail, dict) else fail,
        "credits_before": before2,
        "credits_after": after2,
        "credit_delta": None if before2 is None or after2 is None else round(after2 - before2, 2),
    }
    print("forced_failure", json.dumps(ev["forced_failure"], indent=2, ensure_ascii=False)[:2000])

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(ev, f, indent=2, ensure_ascii=False)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
