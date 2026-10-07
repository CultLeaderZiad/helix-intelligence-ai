import urllib.request
import urllib.parse
import os

token = os.environ.get("META_ACCESS_TOKEN", "")
if not token:
    print("Error: META_ACCESS_TOKEN environment variable is not set.")
    exit(1)

params = urllib.parse.urlencode({
    "access_token": token,
    "search_terms": "shopify",
    "ad_reached_countries": "['US']",
    "ad_type": "ALL",
    "limit": "2"
})

url = f"https://graph.facebook.com/v22.0/ads_archive?{params}"
req = urllib.request.Request(url, headers={"User-Agent": "Helix/1.0"})

try:
    with urllib.request.urlopen(req) as resp:
        print("SUCCESS! Status:", resp.getcode())
        data = json.loads(resp.read().decode())
        print("Ad records returned:", len(data.get("data", [])))
        if data.get("data"):
            print("Sample ad ID:", data["data"][0].get("id"))
            print("Sample page name:", data["data"][0].get("page_name"))
except urllib.error.HTTPError as e:
    print("FAILED! Status:", e.code)
    print("Body:", e.read().decode())
