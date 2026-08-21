from pydantic import BaseModel
from typing import Optional

class TrialStatusResponse(BaseModel):
    active: bool
    days_remaining: int
    requests_used: int
    requests_limit: int
