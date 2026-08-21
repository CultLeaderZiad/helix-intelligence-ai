import asyncio
from typing import List
from datetime import datetime, timedelta
import random

from app.services.scraping.base import ScraperProvider, RawCreative

class AdLibraryProvider(ScraperProvider):
    """
    Mock integration for an Ad Library (e.g. Meta Ad Library or TikTok Creative Center).
    If a real API is connected in the future, this class will make httpx calls.
    """

    async def search(self, query: str) -> List[RawCreative]:
        # Simulate network latency (between 1.5 to 3 seconds)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        if not query or len(query.strip()) < 2:
            return []
            
        now = datetime.utcnow()
        query_safe = query.strip().title()

        # Generate realistic mocked ads
        creatives = []
        
        num_results = random.randint(3, 8)
        
        for i in range(num_results):
            days_ago_first = random.randint(10, 60)
            days_ago_last = random.randint(0, 5)
            
            first_seen = (now - timedelta(days=days_ago_first)).isoformat() + "Z"
            last_seen = (now - timedelta(days=days_ago_last)).isoformat() + "Z"
            days_active = days_ago_first - days_ago_last
            
            creatives.append(
                RawCreative(
                    platform=random.choice(["meta", "tiktok", "youtube", "linkedin"]),
                    format=random.choice(["video", "image", "carousel"]),
                    brand_name=query_safe,
                    headline=f"Discover the new {query_safe} collection!",
                    body=f"Join thousands of happy customers. Upgrade your life with {query_safe} today. Limited time offer.",
                    cta=random.choice(["Shop Now", "Learn More", "Get Offer", "Sign Up"]),
                    landing_domain=f"{query.strip().lower().replace(' ', '')}.com",
                    landing_url=f"https://{query.strip().lower().replace(' ', '')}.com/offer/{i}",
                    duration_seconds=random.choice([15, 30, 60, None]),
                    thumbnail_ratio=random.choice(["1:1", "9:16", "16:9"]),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    days_active=max(1, days_active),
                    variant_count=random.randint(1, 5),
                    impressions_est=random.randint(10000, 500000),
                    spend_band=random.choice(["low", "mid", "high", "very_high"])
                )
            )

        return creatives
