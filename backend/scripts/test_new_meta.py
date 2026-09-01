import urllib.request
import urllib.parse
import json

token = "EAATtZCPK8xY4BSTWcW8Oqk0v4pYvG03ONkpY7BiqyUfmEAPcb8Vfy0OjEY8yqVGMvA2gjjpsVItjzDiQdtRLjoZCvtxVEKup0DiGhG3lxJEfmvGWMYGDtQbd16ZBUgZBHfhfmOTDnqbISRDZBHr0rqLydnWMNWAtGstXwfPXmzgQK5ES9myxaXMMM5MYERSRIn2GtZA9IU3fry4GZBKL9IsrBYxXakZBrYXSC89PDFi5LRQURbBXXuxpJ3577kqaBU6D97BeHhGVDWJSTV45p4rA"

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
