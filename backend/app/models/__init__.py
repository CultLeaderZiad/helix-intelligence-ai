from app.db.base import Base
from .user import User
from .organization import Organization
from .scrape_job import ScrapeJob
from .creative import Creative
from .creative_score import CreativeScore
from .pattern import Pattern
from .ai_insight import AIInsight
from .usage_log import UsageLog

# This file imports all models so Alembic can discover them
