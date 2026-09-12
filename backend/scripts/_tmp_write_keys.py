"""Update named keys in repo .env.local from process env. Never prints values."""
from pathlib import Path
import os
import re

PATH = Path(__file__).resolve().parents[2] / ".env.local"
KEYS = (
    "RESEND_API_KEY",
    "RESEND_FROM",
    "SCRAPEGRAPH_API_KEY",
    "BRIGHTDATA_API_KEY",
    "METAPI_API_KEY",
)


def upsert(text: str, key: str, value: str) -> str:
    line = f'{key}="{value}"'
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    return text.rstrip() + "\n" + line + "\n"


def main() -> None:
    text = PATH.read_text(encoding="utf-8") if PATH.exists() else ""
    updated = []
    for key in KEYS:
        value = os.environ.get(key)
        if value is None or value == "":
            continue
        text = upsert(text, key, value)
        updated.append(key)
    PATH.write_text(text, encoding="utf-8")
    print("updated:", ",".join(updated) if updated else "(none)")


if __name__ == "__main__":
    main()
