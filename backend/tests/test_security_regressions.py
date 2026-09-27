"""Security regression tests (static, no DB required).

These lock down the fixes for the CodeRabbit audit of d38a5ae:
  1. impersonation escalation (assistant-admin -> full-admin token)
  2. cross-tenant reads (discovery jobs, creatives, insights)
  3. Scout email-substring billing backdoor + unlocked credit writes
  4. unauthenticated auth webhook
  5. credentials echoed through Dict[str, bool] feature flags
  6. per-request media API keys persisted/echoed
  7. Higgsfield completions never metered

Run:  python tests/test_security_regressions.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def check(condition: bool, label: str, failures: list[str]) -> None:
    if condition:
        print(f"PASS  {label}")
    else:
        failures.append(label)
        print(f"FAIL  {label}")


def main() -> int:
    failures: list[str] = []

    scout = read("app/api/routers/scout.py")
    # 3. No email-substring admin bypass anywhere; central gate in place.
    # (Strip comments first: the fix's own explanatory comments mention the old
    # backdoor, and only executable code should be asserted on.)
    scout_code = "\n".join(
        line for line in scout.splitlines() if not line.strip().startswith("#")
    )
    check(
        '"cultleader" in' not in scout_code
        and 'in (current_user.email or "")' not in scout_code,
        "scout: no email-substring admin bypass",
        failures,
    )
    check(
        scout.count("assert_can_spend(") >= 2 and scout.count("await charge(") >= 2,
        "scout: central row-locked gate + charge() on both job routes",
        failures,
    )
    check(
        "org.credit_balance = 250" not in scout and "org.credit_balance = max(" not in scout,
        "scout: no direct credit_balance writes",
        failures,
    )

    # 1. Impersonation: full-admin only, no upward impersonation, actor audited.
    admin_router = read("app/api/routers/admin.py")
    check(
        "get_current_full_admin" in admin_router
        and "Impersonating an administrator is not permitted" in admin_router
        and "actor=current_admin" in admin_router,
        "admin router: impersonation is full-admin only, upward blocked, actor passed",
        failures,
    )
    admin_service = read("app/services/admin_service.py")
    check(
        'operation="admin_impersonation"' in admin_service,
        "admin service: impersonation writes an audit trail",
        failures,
    )

    # 2. Tenant isolation: scope parameters exist and are wired end to end.
    discover = read("app/services/discover_service.py")
    check(
        "user_org_ids" in discover and "job.org_id not in user_org_ids" in discover,
        "discover: get_job_status enforces org scope",
        failures,
    )
    creatives = read("app/services/creative_service.py")
    check(
        "user_org_ids" in creatives and "ScrapeJob.org_id.in_(user_org_ids)" in creatives,
        "creatives: list/detail scoped through scrape_jobs.org_id",
        failures,
    )
    analysis = read("app/services/analysis_service.py")
    check(
        "scoped_creative_ids" in analysis and "AIInsight.creative_id.in_(allowed)" in analysis,
        "insights: list/detail scoped through creative -> job -> org",
        failures,
    )
    tenancy = ROOT / "app/core/tenancy.py"
    check(tenancy.exists(), "tenancy helper module exists", failures)

    # 4. Auth webhook: real signature comparison, fails closed.
    auth = read("app/api/routers/auth.py")
    check(
        "hmac.compare_digest" in auth
        and 'status_code=503, detail="Auth webhook is not configured"' in auth,
        "auth webhook: HMAC enforced and closed when unconfigured",
        failures,
    )
    check(
        "Expected: {expected_signature}" not in auth,
        "auth webhook: expected digest no longer merely logged",
        failures,
    )

    # 5. Credentials never typed as bools nor echoed.
    admin_schema = read("app/schemas/admin.py")
    check(
        "custom_feature_flags: Dict[str, bool]" not in admin_schema
        and "effective_feature_flags: Dict[str, bool]" not in admin_schema,
        "schemas: org flag dicts accept Any (no Dict[str, bool] 500s)",
        failures,
    )
    check(
        "_redact_flags(" in admin_service,
        "admin service: credentials redacted from org flag responses",
        failures,
    )
    check(
        "_CREDENTIAL_MARKERS" in auth,
        "session: credentials redacted from feature_flags response",
        failures,
    )

    # 6. Media: per-request BYOK key never persisted with the job.
    media = read("app/services/media_service.py")
    check(
        'parameters.pop("custom_api_key", None)' in media,
        "media: custom_api_key stripped before persistence",
        failures,
    )
    check(
        "custom_api_key=request_api_key" in media,
        "media: key handed to the task in memory, not via DB",
        failures,
    )

    # 7. Paid completions are metered on every path.
    check(
        "async def meter_media_success(" in media
        and media.count("await meter_media_success(job.id)") >= 1,
        "media: metering helper exists and runs on polling completion",
        failures,
    )
    webhooks = read("app/api/routers/webhooks.py")
    check(
        "meter_media_success" in webhooks,
        "webhooks: completed Higgsfield jobs are metered",
        failures,
    )

    print(f"\n{len(failures)} failure(s)" if failures else "\nAll security regressions passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
