import httpx
import json

r = httpx.get('https://api.github.com/repos/CultLeaderZiad/helix-intelligence-ai/pulls?state=all&per_page=20')
print('Status:', r.status_code)
if r.status_code == 200:
    for pr in r.json():
        num = pr["number"]
        state = pr["state"]
        title = pr["title"]
        branch = pr["head"]["ref"]
        base = pr["base"]["ref"]
        merged = pr.get("merged_at")
        user = pr["user"]["login"]
        print(f"PR #{num} [{state}]: {title} ({branch} -> {base}) by {user}")
        if merged:
            print(f"   Merged at: {merged}")
        print(f"   URL: {pr['html_url']}")
else:
    print(r.text[:500])
