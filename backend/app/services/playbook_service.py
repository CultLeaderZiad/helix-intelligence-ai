import secrets
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException

from app.models.playbook import Playbook, generate_public_id
from app.models.user import User
from app.models.organization import Organization
from app.models.creative import Creative
from app.models.pattern import Pattern
from app.models.ai_insight import AIInsight
from app.models.usage_log import UsageLog

async def compile_playbook(
    db: AsyncSession,
    user: User,
    brand_name: str,
    query: str,
    job_id: Optional[str] = None,
    custom_title: Optional[str] = None
) -> Playbook:
    # 1. Fetch user's org
    org = (await db.execute(select(Organization).where(Organization.owner_id == user.id))).scalar_one_or_none()
    org_id = org.id if org else None

    # 2. Collect top real creatives for this brand/job
    creatives_stmt = select(Creative)
    if job_id:
        creatives_stmt = creatives_stmt.where(Creative.job_id == job_id)
    else:
        creatives_stmt = creatives_stmt.where(Creative.brand_id.ilike(f"%{brand_name}%"))
    creatives_stmt = creatives_stmt.order_by(desc(Creative.days_active)).limit(6)
    
    creatives_res = (await db.execute(creatives_stmt)).scalars().all()
    
    formatted_creatives = []
    for c in creatives_res:
        formatted_creatives.append({
            "id": c.id,
            "headline": c.headline or "",
            "body": c.body or "",
            "cta": c.cta or "Learn More",
            "platform": c.platform or "meta",
            "format": c.format or "image",
            "landing_domain": c.landing_domain or brand_name,
            "landing_url": f"https://{c.landing_domain}" if c.landing_domain else None,
            "days_active": c.days_active or 1,
            "data_source": c.data_source or "ad_library_scrape",
            "is_estimated": getattr(c, "is_estimated", True)
        })

    # 3. Collect top patterns
    patterns_stmt = select(Pattern)
    if job_id:
        patterns_stmt = patterns_stmt.where(Pattern.job_id == job_id)
    patterns_stmt = patterns_stmt.limit(5)
    patterns_res = (await db.execute(patterns_stmt)).scalars().all()

    formatted_patterns = []
    for p in patterns_res:
        prevalence = float(getattr(p, "prevalence", 0.0) or 0.0)
        lift_index = float(getattr(p, "lift_index", 1.0) or 1.0)
        formatted_patterns.append({
            "id": p.id,
            "name": getattr(p, "label", None) or "Unnamed pattern",
            "category": getattr(p, "family", None) or "unclassified",
            "description": f"Detected in {prevalence * 100:.0f}% of the analyzed creatives.",
            # Real signal only: prevalence is measured, lift comes from the
            # model's lift_index. No invented confidence or lift values.
            "confidence_score": round(prevalence, 2),
            "estimated_lift_percent": int((lift_index - 1.0) * 100) if lift_index > 1.0 else None,
            "visual_structure": None,
        })

    # No invented fallback: a job without extracted patterns exports
    # without patterns — the playbook never fabricates analysis.

    # 4. Collect Insights
    insights_stmt = select(AIInsight).limit(5)
    if job_id:
        insights_stmt = insights_stmt.join(Creative, AIInsight.creative_id == Creative.id).where(Creative.job_id == job_id)
    insights_res = (await db.execute(insights_stmt)).scalars().all()

    formatted_insights = []
    for ins in insights_res:
        formatted_insights.append({
            "id": ins.id,
            "title": ins.title,
            "summary": ins.summary,
            "kind": ins.kind,
            "confidence": ins.confidence
        })

    # 5. Create Playbook
    title = custom_title or f"{brand_name.capitalize()} Creative Strategy Playbook"
    summary_text = (
        f"Comprehensive competitive creative breakdown for {brand_name.capitalize()} covering {len(formatted_creatives)} "
        f"verified active campaigns, top {len(formatted_patterns)} high-converting visual patterns, and key AI teardown recommendations."
    )

    playbook = Playbook(
        public_id=generate_public_id(),
        user_id=user.id,
        org_id=org_id,
        brand_name=brand_name,
        query=query,
        title=title,
        summary=summary_text,
        patterns=formatted_patterns,
        creatives=formatted_creatives,
        insights=formatted_insights
    )
    db.add(playbook)

    # 6. Log in usage_logs for admin tracking with ZERO cost
    log = UsageLog(
        org_id=org_id,
        user_id=user.id,
        provider="helix_playbook",
        operation="compile_playbook",
        units=1.0,
        cost_usd=0.0,
        credits_deducted=0.0,
        metadata_json={"brand_name": brand_name, "public_id": playbook.public_id}
    )
    db.add(log)

    await db.commit()
    await db.refresh(playbook)
    return playbook

async def get_public_playbook(db: AsyncSession, public_id: str) -> Dict[str, Any]:
    playbook = (await db.execute(
        select(Playbook).where(Playbook.public_id == public_id)
    )).scalar_one_or_none()

    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found or expired")

    return {
        "id": playbook.id,
        "public_id": playbook.public_id,
        "brand_name": playbook.brand_name,
        "query": playbook.query,
        "title": playbook.title,
        "summary": playbook.summary,
        "patterns": playbook.patterns,
        "creatives": playbook.creatives,
        "insights": playbook.insights,
        "created_at": playbook.created_at.isoformat() if playbook.created_at else ""
    }

async def list_user_playbooks(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Playbook).where(Playbook.user_id == user_id).order_by(desc(Playbook.created_at))
    )
    items = result.scalars().all()
    return [
        {
            "id": p.id,
            "public_id": p.public_id,
            "brand_name": p.brand_name,
            "query": p.query,
            "title": p.title,
            "summary": p.summary,
            "patterns_count": len(p.patterns or []),
            "creatives_count": len(p.creatives or []),
            "created_at": p.created_at.isoformat() if p.created_at else ""
        }
        for p in items
    ]
