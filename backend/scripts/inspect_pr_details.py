import sys
sys.stdout.reconfigure(encoding='utf-8')
import httpx
import json

for pr_num in [11, 12, 13, 14]:
    r = httpx.get(f"https://api.github.com/repos/CultLeaderZiad/helix-intelligence-ai/pulls/{pr_num}")
    if r.status_code == 200:
        pr = r.json()
        print("="*80)
        print(f"PR #{pr_num}: {pr['title']}")
        print(f"State: {pr['state']} | Merged: {pr.get('merged_at')} | Base: {pr['base']['ref']} | Head: {pr['head']['ref']}")
        print(f"Author: {pr['user']['login']}")
        print("Files changed:", pr.get("changed_files"), "Commits:", pr.get("commits"))
        print(f"Description / Body:\n{pr.get('body')}\n")
    else:
        print(f"Error fetching PR #{pr_num}: {r.status_code}")
