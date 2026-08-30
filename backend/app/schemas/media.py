from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class MediaGenerationRequest(BaseModel):
    prompt: str
    provider: str = "higgsfield"
    mode: Optional[str] = "premium_ad"
    parameters: Optional[Dict[str, Any]] = None

class MediaGenerationJobResponse(BaseModel):
    id: str
    job_id: Optional[str] = None
    status: str
    prompt: str
    provider: str
    provider_job_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    parameters: Optional[Dict[str, Any]] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

    def __init__(self, **data):
        if "id" in data and "job_id" not in data:
            data["job_id"] = data["id"]
        super().__init__(**data)
