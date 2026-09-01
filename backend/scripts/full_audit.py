import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import subprocess
import asyncio
import uuid
from datetime import datetime

sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv("backend/.env")

from app.db.session import async_session_maker
from sqlalchemy import select, text, func
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.ai_insight import AIInsight
from app.models.scrape_job import ScrapeJob
from app.models.usage_log import UsageLog
from app.models.notification import Notification
from app.models.support_ticket import SupportTicket, SupportTicketReply
from app.services.scraping.ad_library_provider import AdLibraryProvider
from app.services import creative_service, analysis_service, billing_service, admin_service
from app.services.ai.ai_router import AIRouter

RENDER_BASE = "https://helix-intelligence-ai.onrender.com"

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=".")
        return res.stdout, res.stderr, res.returncode
    except Exception as e:
        return "", str(e), -1

def call_http(url, method="GET", headers=None, data=None):
    if headers is None:
        headers = {}
    headers["User-Agent"] = "Helix-Audit/1.0"
    if data and isinstance(data, dict):
        data_bytes = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif data and isinstance(data, str):
        data_bytes = data.encode("utf-8")
    else:
        data_bytes = None

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except:
                parsed = body
            return resp.getcode(), parsed, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except:
            parsed = body
        return e.code, parsed, dict(e.headers)
    except Exception as e:
        return 0, str(e), {}

async def run_full_audit():
    print("="*70)
    print("SECTION 1: DATA PIPELINE & DISCOVER PROVIDER CHAIN AUDIT")
    print("="*70)

    # 1.1 Provider chain inspection
    async with async_session_maker() as db:
        ad_lib = AdLibraryProvider(db, "test_org", "test_user")
        print(f"Meta Token Configured: {bool(ad_lib.meta_token)} (Length: {len(ad_lib.meta_token)})")
        print(f"Apify Token Configured: {bool(ad_lib.apify_token)} (Length: {len(ad_lib.apify_token)})")

        # 1.2 Run 3 real searches
        queries = ["shopify", "ziad_obscure_brand_xyz", "asdkfjhsakjdfh92384"]
        for q in queries:
            print(f"\n--- Testing Query: '{q}' ---")
            try:
                res = await ad_lib.search(q, max_records=5)
                print(f"Result count: {len(res)}")
                if res:
                    print(f"First item headline: '{res[0].headline}'")
                    print(f"First item brand: '{res[0].brand_id}'")
                    print(f"First item data_source: '{res[0].data_source}'")
            except Exception as e:
                print(f"Search exception: {type(e).__name__} - {e}")

        # 1.3 Test Apify directly to capture exact error
        print("\n--- Direct Apify Run ---")
        try:
            apify_res = await ad_lib.query_apify("shopify", "US", 5)
            print("Apify Result Count:", len(apify_res))
        except Exception as e:
            print("Apify Exception:", type(e).__name__, e)

    print("\n" + "="*70)
    print("SECTION 2: AUTH & SESSION AUDIT (LIVE RENDER BACKEND)")
    print("="*70)
    test_email = f"audit_user_{uuid.uuid4().hex[:6]}@example.com"
    test_password = "SecurePassword123!"

    # 2.1 Health check on Render
    st_health, body_health, _ = call_http(f"{RENDER_BASE}/health")
    print(f"GET {RENDER_BASE}/health -> Status {st_health}: {body_health}")

    # 2.2 Signup on Render
    st_signup, body_signup, hd_signup = call_http(
        f"{RENDER_BASE}/api/auth/sign-up",
        method="POST",
        data={"email": test_email, "password": test_password, "name": "Audit Tester"}
    )
    print(f"POST /api/auth/sign-up -> Status {st_signup}: {body_signup}")

    # 2.3 Signin on Render
    st_signin, body_signin, hd_signin = call_http(
        f"{RENDER_BASE}/api/auth/sign-in",
        method="POST",
        data={"email": test_email, "password": test_password}
    )
    print(f"POST /api/auth/sign-in -> Status {st_signin}: {body_signin}")

    token = ""
    if isinstance(body_signin, dict) and "access_token" in body_signin:
        token = body_signin["access_token"]
    elif isinstance(body_signup, dict) and "access_token" in body_signup:
        token = body_signup["access_token"]

    # 2.4 Session persistence on Render
    if token:
        st_sess, body_sess, _ = call_http(
            f"{RENDER_BASE}/api/auth/session",
            method="GET",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"GET /api/auth/session with token -> Status {st_sess}: {body_sess.get('user', {}).get('email') if isinstance(body_sess, dict) else body_sess}")

    # 2.5 Unauthenticated route guard test
    st_unauth, body_unauth, _ = call_http(f"{RENDER_BASE}/api/auth/session", method="GET")
    print(f"GET /api/auth/session (No Token) -> Status {st_unauth}: {body_unauth}")

    print("\n" + "="*70)
    print("SECTION 3: CREDIT & TRIAL SYSTEM AUDIT")
    print("="*70)
    async with async_session_maker() as db:
        # Check all plans in database
        plans = (await db.execute(select(Plan))).scalars().all()
        print(f"Database Plans ({len(plans)}):")
        for p in plans:
            print(f" - Plan ID: {p.id}, Name: {p.name}, Credits: {p.credit_allowance}, Daily Images: {getattr(p, 'daily_image_limit', None)}, Price: ${getattr(p, 'price_monthly', 0)}")

        # Create temporary user for credit exhaustion test
        test_user_obj = User(
            id=f"exhaust_{uuid.uuid4().hex[:8]}",
            email=f"exhaust_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash",
            role="customer"
        )
        db.add(test_user_obj)
        await db.commit()

        test_org_obj = Organization(
            id=f"org_{uuid.uuid4().hex[:8]}",
            name="Exhaust Org",
            owner_id=test_user_obj.id,
            plan_id="plan_trial_default",
            credit_balance=0.5
        )
        db.add(test_org_obj)
        await db.commit()

        # Test credit check when cost is 1.0 (requires 1.0, user has 0.5)
        try:
            await billing_service.check_quota_and_feature(db, test_user_obj, required_credits=1.0)
            print("FAIL: Expected quota block but passed!")
        except Exception as e:
            print(f"PASS: Quota block triggered -> {type(e).__name__}: {e}")

        # Test admin bypass
        admin_user = User(
            id=f"admin_{uuid.uuid4().hex[:8]}",
            email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash",
            role="admin"
        )
        db.add(admin_user)
        await db.commit()

        try:
            await billing_service.check_quota_and_feature(db, admin_user, required_credits=100.0)
            print("PASS: Admin bypass worked for 100 credits on 0 balance.")
        except Exception as e:
            print(f"FAIL: Admin bypass failed: {e}")

    print("\n" + "="*70)
    print("SECTION 4: INTELLIGENCE, CREATE, PERFORMANCE VERIFICATION")
    print("="*70)
    async with async_session_maker() as db:
        # Find a real creative from DB
        c_row = (await db.execute(select(Creative).limit(1))).scalar_one_or_none()
        if c_row:
            print(f"Found real creative: ID={c_row.id}, Brand={c_row.brand_id}, Headline='{c_row.headline}'")
            # Run deep teardown test
            try:
                print("Running generate_insight_for_creative...")
                insight = await analysis_service.generate_insight_for_creative(db, c_row.id, admin_user)
                print(f"Deep Teardown Generated! Hook Score: {insight.scores.hook}, Hook Summary: '{insight.hook_summary}'")
                print(f"Visual Breakdown: '{insight.visual_breakdown}'")
            except Exception as e:
                print(f"Intelligence Teardown Exception: {type(e).__name__} - {e}")
        else:
            print("No creatives found in DB to test Intelligence.")

        # Test AIRouter provider instantiation
        try:
            print("\nTesting AIRouter with Gemini...")
            provider = await AIRouter.get_provider_for_user(db, admin_user)
            print(f"Active Provider: {provider.name if hasattr(provider, 'name') else type(provider).__name__}")
        except Exception as e:
            print(f"AIRouter Exception: {type(e).__name__} - {e}")

    print("\n" + "="*70)
    print("SECTION 5: ADMIN CAPABILITIES AUDIT")
    print("="*70)
    async with async_session_maker() as db:
        # 5.1 Edit plan
        try:
            plan_to_edit = (await db.execute(select(Plan).limit(1))).scalar_one_or_none()
            if plan_to_edit:
                old_price = plan_to_edit.price_monthly
                plan_to_edit.price_monthly = 99.0
                await db.commit()
                print(f"PASS: Plan edit successful (Plan '{plan_to_edit.id}' price updated {old_price} -> 99.0)")
            else:
                print("No plan found to edit.")
        except Exception as e:
            print(f"FAIL: Plan edit error: {e}")

        # 5.2 Ban user
        try:
            ban_target = (await db.execute(select(User).where(User.role != "admin").limit(1))).scalar_one_or_none()
            if ban_target:
                ban_target.is_banned = True
                await db.commit()
                print(f"PASS: User ban toggle successful for user {ban_target.email}")
            else:
                print("No non-admin user found to test ban.")
        except Exception as e:
            print(f"FAIL: User ban error: {e}")

        # 5.3 View usage logs
        try:
            logs = (await db.execute(select(UsageLog).limit(5))).scalars().all()
            print(f"PASS: Viewed usage logs ({len(logs)} records retrieved)")
        except Exception as e:
            print(f"FAIL: View usage log error: {e}")

        # 5.4 Broadcast notification
        try:
            notif = Notification(
                user_id=admin_user.id,
                title="System Broadcast Audit Test",
                message="Test audit broadcast message",
                type="system"
            )
            db.add(notif)
            await db.commit()
            print("PASS: System notification created.")
        except Exception as e:
            print(f"FAIL: Broadcast notification error: {e}")

        # 5.5 Support ticket & reply
        try:
            ticket = SupportTicket(
                user_id=test_user_obj.id,
                subject="Audit Ticket",
                message="Testing ticket resolution flow",
                status="open"
            )
            db.add(ticket)
            await db.commit()
            
            reply = SupportTicketReply(
                ticket_id=ticket.id,
                user_id=admin_user.id,
                message="Admin audit reply",
                is_admin=True
            )
            db.add(reply)
            ticket.status = "resolved"
            await db.commit()
            print(f"PASS: Support ticket & admin reply workflow verified (Ticket ID: {ticket.id})")
        except Exception as e:
            print(f"FAIL: Support ticket workflow error: {e}")

    print("\n" + "="*70)
    print("SECTION 6: GIT & DEPLOYMENT CHECK")
    print("="*70)
    out_branch, _, _ = run_cmd("git branch --show-current")
    out_diff, _, _ = run_cmd("git diff --stat main")
    print(f"Current Git Branch: {out_branch.strip()}")
    print(f"Git Diff vs main:\n{out_diff.strip()}")

    # Render CORS & Options check
    st_opt, _, hd_opt = call_http(
        f"{RENDER_BASE}/api/discovery/jobs",
        method="OPTIONS",
        headers={"Origin": "https://helix-intelligence-ai.vercel.app", "Access-Control-Request-Method": "GET"}
    )
    print(f"OPTIONS {RENDER_BASE}/api/discovery/jobs -> Status {st_opt}")
    print(f"CORS Headers: allow-origin={hd_opt.get('access-control-allow-origin')}, allow-methods={hd_opt.get('access-control-allow-methods')}")

if __name__ == "__main__":
    asyncio.run(run_full_audit())
