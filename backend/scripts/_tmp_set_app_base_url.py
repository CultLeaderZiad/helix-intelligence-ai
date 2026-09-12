"""Set APP_BASE_URL in repo .env.local. Not a secret."""
from pathlib import Path
import re

PATH = Path(__file__).resolve().parents[2] / ".env.local"
VALUE = "https://helix-intelligence-ai-six.vercel.app"
line = f"APP_BASE_URL={VALUE}"
text = PATH.read_text(encoding="utf-8") if PATH.exists() else ""
pattern = re.compile(r"^APP_BASE_URL=.*$", re.M)
if pattern.search(text):
    text = pattern.sub(line, text, count=1)
    action = "replaced"
else:
    text = text.rstrip() + "\n" + line + "\n"
    action = "appended"
PATH.write_text(text, encoding="utf-8")
print(action, VALUE)
