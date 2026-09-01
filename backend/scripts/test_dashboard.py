import asyncio
from app.db.session import async_session_maker
from app.services.dashboard_service import get_dashboard_metrics

async def test():
    async with async_session_maker() as db:
        metrics = await get_dashboard_metrics(db)
        print("Top Performers:", len(metrics["top_performers"]))
        print("Reach Leaderboard:", len(metrics["reach_leaderboard"]))
        print("Timeline:", metrics["timeline"])
        print("Cross Brand:", metrics["cross_brand"])

if __name__ == "__main__":
    asyncio.run(test())
