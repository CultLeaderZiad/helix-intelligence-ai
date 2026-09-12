"""Inspect the live Vercel JS for API vs mock. No secrets."""
import re
import urllib.request

html = urllib.request.urlopen("https://helix-intelligence-ai-six.vercel.app/discover", timeout=30).read().decode(
    "utf-8", "replace"
)
srcs = re.findall(r'src="(/assets/[^"]+)"', html)
print("script_count", len(srcs))
print("scripts", srcs[:8])
for src in srcs[:6]:
    js = urllib.request.urlopen("https://helix-intelligence-ai-six.vercel.app" + src, timeout=30).read().decode(
        "utf-8", "replace"
    )
    print("---", src, "len", len(js))
    for needle in (
        "helix-intelligence-ai.onrender.com",
        "mock fixtures",
        "VITE_DATA_SOURCE",
        "useApi",
        "nike.com",
    ):
        print(" ", needle, needle in js)
    urls = sorted({u for u in re.findall(r"https://[a-zA-Z0-9._/-]+", js) if "helix" in u or "onrender" in u})
    print("  helix_urls", urls[:12])
