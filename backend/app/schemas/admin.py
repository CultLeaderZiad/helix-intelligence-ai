from pydantic import BaseModel
from typing import List, Optional

class AdminOverviewStats(BaseModel):
    organizations: int
    active_scrape_jobs: int
    system_health: str
    api_error_rate: float
    window_label: str

class AdminJobRow(BaseModel):
    job_id: str
    organization: str
    query: str
    status: str
    records: int
    duration_ms: int
    created_at: str

class AdminServiceHealth(BaseModel):
    id: str
    name: str
    status: str
    detail: str
    latency_ms: Optional[int] = None
    last_checked: str

class AdminSystemHealth(BaseModel):
    state: str
    services: List[AdminServiceHealth]
