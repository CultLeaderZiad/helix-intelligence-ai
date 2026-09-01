import json
import urllib.request
import urllib.parse
import os

token = "EAATtZCPK8xY4BSSvOOtBEvBvO8akJ50iqrZCjmRBCcGZCGuWdzFEGyHmanv1KS0lQwVuJZBHPQnPFJFjk9oefeongX3hK28u3XPX2VbzJzFlRZAltVZCNRBc2YyqZCXBCVtZAGKbxltwkfZADz2N1UjDbH8cxZB7GRPcY1UUyoWEfUd6ziHSpyHGdCzNN2L7Ng"

def call(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Helix/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return 0, str(e)

print(f"Token: {token[:20]}...{token[-10:]}")

# 1. Inspect /me
status, body = call(f"https://graph.facebook.com/v22.0/me?access_token={token}")
print("\n--- GET /me ---")
print("Status:", status)
print("Response:", body)

# 2. Inspect /me/permissions
status, body = call(f"https://graph.facebook.com/v22.0/me/permissions?access_token={token}")
print("\n--- GET /me/permissions ---")
print("Status:", status)
print("Response:", body)

# 3. Inspect /ads_archive (Ad Library API)
params = urllib.parse.urlencode({
    "access_token": token,
    "search_terms": "nike",
    "ad_reached_countries": "['US']",
    "ad_type": "ALL",
    "limit": "1"
})
status, body = call(f"https://graph.facebook.com/v22.0/ads_archive?{params}")
print("\n--- GET /ads_archive (Ad Library API) ---")
print("Status:", status)
print("Response:", body)
