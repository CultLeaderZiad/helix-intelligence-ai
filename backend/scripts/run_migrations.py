import asyncio
from sqlalchemy import text
from app.db.session import engine
from app.db.base import Base
import app.models

async def migrate():
    print("Connecting to database and running table / column migrations...")
    async with engine.begin() as conn:
        # Create all tables (e.g. workspace_provider_credentials)
        await conn.run_sync(Base.metadata.create_all)
        print("Ensured all tables exist.")

        migrations = [
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS images_generated_today FLOAT DEFAULT 0.0;",
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS images_today_date VARCHAR(32) DEFAULT '';",
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS images_trial_total FLOAT DEFAULT 0.0;",
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS custom_feature_flags JSON DEFAULT '{}'::json;",
            "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status VARCHAR(64) DEFAULT 'active';",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_started_at TIMESTAMPTZ;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMPTZ;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS has_completed_onboarding BOOLEAN DEFAULT FALSE;",
        ]

        for query in migrations:
            try:
                await conn.execute(text(query))
                print("Executed:", query)
            except Exception as e:
                print("Failed query:", query, e)

    print("Migrations complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
