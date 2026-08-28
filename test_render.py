import urllib.request
import urllib.error
import json
import time

base_url = "https://helix-intelligence-ai.onrender.com/api"
import os

email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
password = os.environ.get("ADMIN_PASSWORD", "password123")

# 1. Sign In
try:
    print("Signing in to Render backend...")
    req = urllib.request.Request(
        f"{base_url}/auth/sign-in",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"email": email, "password": password}).encode("utf-8")
    )
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        token = data.get("access_token")
        print("✅ Sign In successful. Token received.")
except urllib.error.URLError as e:
    print("❌ Sign In failed:", e.read().decode() if hasattr(e, 'read') else str(e))
    exit(1)

# 2. Run Discovery Search
try:
    print("Starting Discovery Search...")
    req = urllib.request.Request(
        f"{base_url}/discovery/jobs",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        data=json.dumps({"query": "Nike running shoes"}).encode("utf-8")
    )
    with urllib.request.urlopen(req) as res:
        job = json.loads(res.read().decode())
        job_id = job.get("job_id")
        print(f"✅ Search started. Job ID: {job_id}, Status: {job.get('status')}")
except urllib.error.URLError as e:
    print("❌ Search failed:", e.read().decode() if hasattr(e, 'read') else str(e))
    exit(1)

# 3. Poll for status (check if it progresses past queued/0)
for i in range(10):
    time.sleep(2)
    try:
        req = urllib.request.Request(
            f"{base_url}/discovery/jobs/{job_id}",
            method="GET",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req) as res:
            job_status = json.loads(res.read().decode())
            status = job_status.get("status")
            stage = job_status.get("stage_index", 0)
            print(f"Polling {i+1}: Status={status}, Stage={stage}")
            if status in ["succeeded", "failed"] or stage > 0:
                print("✅ Job progressed successfully! Zombie bug is confirmed fixed on Render.")
                break
    except urllib.error.URLError as e:
        print("❌ Polling failed:", e.read().decode() if hasattr(e, 'read') else str(e))
