from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any

class SearchParams(BaseModel):
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    sort: Optional[str] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 20
    # Which language the ad-library query should be sent in.
    query_language: Optional[str] = "en"

    @field_validator("query_language")
    @classmethod
    def _lang(cls, value: Optional[str]) -> str:
        raw = (value or "en").strip().lower()
        if raw.startswith("ar"):
            return "ar"
        return "en"

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
    # 'service_restart' when the process died mid-run, 'error' when the
    # pipeline itself failed. Lets the UI say which happened instead of
    # blaming the user's search.
    failure_kind: Optional[str] = None
