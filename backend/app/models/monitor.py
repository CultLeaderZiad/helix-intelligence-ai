from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON, Index
from app.db.base import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class Monitor(Base):
    """A saved Discover query that re-runs on a schedule and reports what changed."""

    __tablename__ = "monitors"

    id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    # The owner is who gets billed and whose plan/trial gates the run. Runs are
    # unattended, so this has to be resolved from the row rather than a request.
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    query = Column(String, nullable=False)
    filters = Column(JSON, default=dict)

    # 'every_6h' | 'every_12h' | 'daily' | 'weekly'
    cadence = Column(String, nullable=False, default="daily")
    # 'active' | 'paused'
    status = Column(String, nullable=False, default="active")
    paused_reason = Column(String, nullable=True)

    notify_in_app = Column(Boolean, default=True, nullable=False)
    notify_email = Column(Boolean, default=False, nullable=False)

    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_job_id = Column(String, nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)

    # Until the first run completes there is nothing to compare against, so the
    # first run only records a baseline and deliberately emits no events.
    baseline_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class MonitorRun(Base):
    """One execution of a monitor, and what the diff concluded."""

    __tablename__ = "monitor_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    monitor_id = Column(String, ForeignKey("monitors.id"), nullable=False)
    job_id = Column(String, nullable=True)

    # 'running' | 'succeeded' | 'failed' | 'skipped'
    status = Column(String, nullable=False, default="running")
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    creatives_seen = Column(Integer, default=0, nullable=False)
    new_count = Column(Integer, default=0, nullable=False)
    killed_count = Column(Integer, default=0, nullable=False)
    changed_count = Column(Integer, default=0, nullable=False)

    is_baseline = Column(Boolean, default=False, nullable=False)
    # Set when the run produced no usable comparison — e.g. the scrape returned
    # nothing, so "every ad disappeared" would be a lie rather than a finding.
    skipped_reason = Column(String, nullable=True)
    error = Column(String, nullable=True)
    credits_charged = Column(String, nullable=True)


class MonitorCreative(Base):
    """Per-monitor memory of one ad identity across runs.

    This is the state the diff compares against. It is scoped to the monitor
    because ad identity is derived from content, not from a provider ID, so it
    is only meaningful within a single recurring query.
    """

    __tablename__ = "monitor_creatives"

    id = Column(String, primary_key=True, default=generate_uuid)
    monitor_id = Column(String, ForeignKey("monitors.id"), nullable=False)

    identity_hash = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)

    # 'active' | 'gone'
    status = Column(String, nullable=False, default="active")
    # Consecutive runs this identity was absent. A single absence is usually a
    # flaky scrape rather than a paused ad, so killed_ad waits for this to
    # cross a threshold.
    missed_runs = Column(Integer, default=0, nullable=False)

    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)

    creative_id = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    format = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    body = Column(String, nullable=True)
    cta = Column(String, nullable=True)
    landing_domain = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_monitor_creatives_identity", "monitor_id", "identity_hash", unique=True),
    )


class MonitorEvent(Base):
    """A single reportable change. This is what the user actually reads."""

    __tablename__ = "monitor_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    monitor_id = Column(String, ForeignKey("monitors.id"), nullable=False)
    run_id = Column(String, ForeignKey("monitor_runs.id"), nullable=False)

    # 'new_ad' | 'killed_ad' | 'copy_changed'
    type = Column(String, nullable=False)
    identity_hash = Column(String, nullable=False)
    creative_id = Column(String, nullable=True)

    headline = Column(String, nullable=True)
    body = Column(String, nullable=True)
    cta = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    landing_domain = Column(String, nullable=True)

    # For copy_changed: the previous headline/body/cta, so the UI can show a diff.
    previous = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_monitor_events_monitor_created", "monitor_id", "created_at"),
    )
