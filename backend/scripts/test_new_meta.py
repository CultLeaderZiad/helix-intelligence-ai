"""Explicit, import-safe Meta diagnostic. Never print credentials or bodies."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request


def main():
    token = os.environ.get("META_ACCESS_TOKEN", "")
    if not token:
        print("Error: META_ACCESS_TOKEN environment variable is not set.")
        return 1

    params = urllib.parse.urlencode({
        "search_terms": "shopify",
        "ad_reached_countries": "['US']",
        "ad_type": "ALL",
        "limit": "2",
    })
    req = urllib.request.Request(
        f"https://graph.facebook.com/v22.0/ads_archive?{params}",
        headers={"User-Agent": "Helix/1.0", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            print("SUCCESS! Status:", resp.getcode())
            print("Ad records returned:", len(data.get("data", [])))
            return 0
    except urllib.error.HTTPError as exc:
        print("FAILED! Status:", exc.code)
    except (urllib.error.URLError, TimeoutError, ValueError):
        print("FAILED! Meta diagnostic could not complete.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
