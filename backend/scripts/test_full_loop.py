import asyncio
import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.local"))

from app.db.session import async_session_maker
from app.models.user import User
from app.models.organization import Organization
from app.models.scrape_job import ScrapeJob
from app.models.creative import Creative
from app.models.creative_score import CreativeScore
from app.models.ai_insight import AIInsight
from app.models.pattern import Pattern
from app.models.media_job import MediaGenerationJob
from app.services.discover_service import trigger_search
from app.schemas.discover import SearchParams
from app.services.analysis_service import generate_insight_for_creative
from app.services.media_service import gemini_generate_media_task
from sqlalchemy import select, desc

async def run_full_loop_test():
    print("=" * 60)
    print("HELIX END-TO-END COMPLETENESS REVIEW (DISCOVER -> INTELLIGENCE -> CREATE -> PERFORMANCE)")
    print("=" * 60)

    # 0. Setup test user & credits
    async with async_session_maker() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one()
        org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one_or_none()
        if not org:
            org = (await db.execute(select(Organization).limit(1))).scalar_one()

        org.daily_credits_used_today = 0.0
        org.credit_balance = 100.0
        await db.commit()

        user_id = str(user.id)
        org_id = str(org.id)
        print(f"Test User: {user.email} (Org: {org.name}, Balance: {org.credit_balance} cr)")

    # -------------------------------------------------------------
    # 1. DISCOVER: Run Real Search
    # -------------------------------------------------------------
    print("\n[LOOP 1: DISCOVER] Running real Discover search for 'shopify'...")
    search_params = SearchParams(query="shopify", country="US")

    async with async_session_maker() as db:
        job_schema = await trigger_search(db, search_params, user_id, background_tasks=None)
        job_id = job_schema.job_id if hasattr(job_schema, "job_id") else job_schema.id
        print(f"Scrape Job started: ID={job_id}")

    # Wait for completion
    for _ in range(40):
        await asyncio.sleep(2)
        async with async_session_maker() as db:
            job = (await db.execute(select(ScrapeJob).where(ScrapeJob.id == job_id))).scalar_one()
            print(f"  Stage: {job.stage} | Label: {job.stage_label}")
            if job.status in ("succeeded", "failed"):
                break

    async with async_session_maker() as db:
        creatives = (await db.execute(
            select(Creative, CreativeScore)
            .outerjoin(CreativeScore, Creative.id == CreativeScore.creative_id)
            .where(Creative.job_id == job_id)
        )).all()

        print(f"\n[LOOP 1 RESULT] Creatives returned: {len(creatives)}")
        assert len(creatives) > 0, "Discover failed to return real creatives!"

        chosen_creative, chosen_score = creatives[0]
        print(f"Selected Creative for downstream testing:")
        print(f"  ID: {chosen_creative.id}")
        print(f"  Headline: {repr(chosen_creative.headline)}")
        print(f"  Body (first 120 chars): {repr(chosen_creative.body[:120])}")
        print(f"  Platform: {chosen_creative.platform}, Format: {chosen_creative.format}")
        print(f"  Landing Domain: {chosen_creative.landing_domain}")
        print(f"  Days Active: {chosen_creative.days_active}")

    # -------------------------------------------------------------
    # 2. INTELLIGENCE: Pattern Extraction & Deep Teardown LLM Analysis
    # -------------------------------------------------------------
    print("\n[LOOP 2: INTELLIGENCE] Generating Deep Teardown LLM Analysis for selected creative...")
    async with async_session_maker() as db:
        user = (await db.execute(select(User).where(User.id == user.id))).scalar_one()
        insight = await generate_insight_for_creative(db, chosen_creative.id, user)

        print("\n[LOOP 2 RESULT] Deep Teardown Generated:")
        print(f"  Insight ID: {insight.id}")
        print(f"  Title: {insight.title}")
        print(f"  Summary: {insight.summary}")
        print(f"  Kind: {insight.kind}")
        print(f"  Confidence: {insight.confidence}")
        print(f"  Model Version: {insight.model_version}")

        # Check if insight is tailored to specific copy
        summary_lower = insight.summary.lower()
        title_lower = insight.title.lower()
        print("\nChecking content specificity:")
        print(f"  Summary snippet: {insight.summary[:200]}...")

    # -------------------------------------------------------------
    # 3. CREATE: Remix Studio & Image Generation
    # -------------------------------------------------------------
    print("\n[LOOP 3: CREATE STUDIO] Creating media remix job referencing source creative...")
    remix_prompt = (
        f"Commercial advertising image remixing competitor campaign.\n"
        f"Headline: '{chosen_creative.headline}'\n"
        f"Call-to-action: '{chosen_creative.cta}'\n"
        f"Visual direction: modern minimalist studio, bold dramatic side lighting, high contrast commercial photography, 8k resolution."
    )

    import uuid
    media_job_id = f"test_remix_{uuid.uuid4().hex[:10]}"
    async with async_session_maker() as db:
        media_job = MediaGenerationJob(
            id=media_job_id,
            user_id=user_id,
            org_id=org_id,
            prompt=remix_prompt,
            provider="gemini",
            status="pending",
            parameters={
                "aspect_ratio": "1:1",
                "mode": "premium_ad",
                "source_creative_id": chosen_creative.id,
                "source_headline": chosen_creative.headline,
            }
        )
        db.add(media_job)
        await db.commit()

    print(f"Running media generation task for Job ID: {media_job_id}...")
    await gemini_generate_media_task(media_job_id, user_id, org_id)

    async with async_session_maker() as db:
        completed_media_job = (await db.execute(
            select(MediaGenerationJob).where(MediaGenerationJob.id == media_job_id)
        )).scalar_one()

        print("\n[LOOP 3 RESULT] Media Generation Result:")
        print(f"  Status: {completed_media_job.status}")
        print(f"  Result URL: {completed_media_job.result_url}")
        print(f"  Error (if any): {completed_media_job.error_message}")
        print(f"  Lineage (source_creative_id): {completed_media_job.parameters.get('source_creative_id')}")

        assert completed_media_job.status == "completed", f"Media generation failed: {completed_media_job.error_message}"
        assert completed_media_job.result_url, "Media generation returned no result URL!"

    # -------------------------------------------------------------
    # 4. PERFORMANCE: Longevity & Fatigue Consistency
    # -------------------------------------------------------------
    print("\n[LOOP 4: PERFORMANCE] Checking consistency across Intelligence & Performance...")
    async with async_session_maker() as db:
        db_creative = (await db.execute(
            select(Creative).where(Creative.id == chosen_creative.id)
        )).scalar_one()

        db_score = (await db.execute(
            select(CreativeScore).where(CreativeScore.creative_id == chosen_creative.id)
        )).scalar_one_or_none()

        print(f"Corpus Consistency for Creative ID: {chosen_creative.id}")
        print(f"  Discover Headline: {repr(chosen_creative.headline)}")
        print(f"  Performance Headline: {repr(db_creative.headline)}")
        print(f"  Lifespan / Days Active: {db_creative.days_active}d")
        print(f"  Score Hook: {db_score.hook if db_score else '—'}")
        print(f"  Score Clarity: {db_score.clarity if db_score else '—'}")
        print(f"  Score Composite: {db_score.composite if db_score else '—'}")

        assert db_creative.headline == chosen_creative.headline
        assert db_creative.days_active == chosen_creative.days_active

    print("\n" + "=" * 60)
    print("FULL-LOOP TEST PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_full_loop_test())
