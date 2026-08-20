from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class SearchParams(BaseModel):
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    sort: Optional[str] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 20

class Job(BaseModel):
    job_id: str
    status: str
    progress: float
    stage: str
    stage_label: str
    stage_index: int
    stages_total: int
    records_found: int
    elapsed_ms: int
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
