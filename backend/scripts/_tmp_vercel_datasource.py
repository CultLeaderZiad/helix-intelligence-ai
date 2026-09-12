"""Extract DATA_SOURCE wiring from the live Vercel bundle."""
import re
import urllib.request

html = urllib.request.urlopen("https://helix-intelligence-ai-six.vercel.app/", timeout=30).read().decode("utf-8", "replace")
src = re.findall(r'src="(/assets/[^"]+)"', html)[0]
js = urllib.request.urlopen("https://helix-intelligence-ai-six.vercel.app" + src, timeout=30).read().decode("utf-8", "replace")

for needle in ("mock fixtures", "helix-intelligence-ai.onrender.com/api", '==="api"', '==="mock"', "VITE_DATA_SOURCE"):
    i = js.find(needle)
    print("\n====", needle, "at", i)
    if i >= 0:
        print(js[max(0, i - 180) : i + 220].replace("\n", " "))
