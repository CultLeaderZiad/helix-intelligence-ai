from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class MediaGenerationRequest(BaseModel):
    prompt: str
    provider: str = "higgsfield"
    mode: Optional[str] = "premium_ad"
    parameters: Optional[Dict[str, Any]] = None

class MediaGenerationJobResponse(BaseModel):
    id: str
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
