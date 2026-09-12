"""Append RESEND_FROM to the repo .env.local if missing. Never prints values."""
from pathlib import Path

path = Path(__file__).resolve().parents[2] / ".env.local"
if not path.exists():
    raise SystemExit(f"missing {path}")

text = path.read_text(encoding="utf-8")
if "RESEND_FROM=" not in text:
    text = text.rstrip() + "\n\nRESEND_FROM=Helix Intelligence <onboarding@resend.dev>\n"
    path.write_text(text, encoding="utf-8")
    print("appended RESEND_FROM")
else:
    print("RESEND_FROM already present")
