import urllib.request
import urllib.error

url = "https://helix-intelligence-ai.onrender.com/api/auth/sign-in"
req = urllib.request.Request(url, method="OPTIONS")
req.add_header("Origin", "https://helix-intelligence-ai-six.vercel.app")
req.add_header("Access-Control-Request-Method", "POST")

try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")
except urllib.error.URLError as e:
    print("Error:", getattr(e, 'code', str(e)))
    if hasattr(e, 'headers'):
        for k, v in e.headers.items():
            print(f"  {k}: {v}")
