"""Print only whether Resend vars exist. Never print values."""
import os
from pathlib import Path

print("process RESEND_API_KEY set:", bool(os.getenv("RESEND_API_KEY")))
print("process RESEND_FROM set:", bool(os.getenv("RESEND_FROM")))

roots = [
    Path(__file__).resolve().parents[2],
    Path(__file__).resolve().parents[1],
]
for root in roots:
    for name in (".env", ".env.local"):
        path = root / name
        if not path.exists():
            print(f"{name} in {root.name}: missing")
            continue
        key_ok = False
        from_ok = False
        from_is_onboarding = False
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("RESEND_API_KEY="):
                value = stripped.split("=", 1)[1].strip().strip("\"'")
                key_ok = bool(value)
            if stripped.startswith("RESEND_FROM="):
                value = stripped.split("=", 1)[1].strip().strip("\"'")
                from_ok = bool(value)
                from_is_onboarding = "onboarding@resend.dev" in value
        print(
            f"{name} in {root.name}: key_set={key_ok} from_set={from_ok} "
            f"from_is_onboarding={from_is_onboarding}"
        )
