from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class AdminOverviewStats(BaseModel):
    organizations: int
    active_scrape_jobs: int
    system_health: str
    api_error_rate: float
    window_label: str
    total_credits_consumed: float = 0.0
    total_provider_cost_usd: float = 0.0
    active_trials: int = 0
    today_api_calls: int = 0
    today_api_spend: float = 0.0

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

# --- Plans Schemas ---
class PlanSchema(BaseModel):
    id: str
    name: str
    type: str # 'trial' | 'pay_as_you_go' | 'custom'
    credit_allowance: int
    price_per_credit: Optional[float] = None
    feature_flags: Dict[str, bool]
    created_by_admin_id: Optional[str] = None
    created_at: Optional[str] = None

class PlanCreate(BaseModel):
    name: str
    type: str = "custom"
    credit_allowance: int = 100
    price_per_credit: Optional[float] = 0.01
    feature_flags: Dict[str, bool] = {
        "discover": True,
        "intelligence": True,
        "create": True,
        "performance": True,
        "swipe_files": True,
        "team_accounts": True,
        "public_api": False
    }

# --- Organization Schemas ---
class AdminOrganizationRow(BaseModel):
    id: str
    name: str
    owner_id: str
    owner_email: str
    plan_id: str
    plan_name: str
    plan_type: str
    credit_balance: float
    credits_used: float
    custom_feature_flags: Dict[str, bool]
    effective_feature_flags: Dict[str, bool]
    status: str
    trial_expires_at: Optional[str] = None
    total_jobs: int = 0

class GrantCreditsRequest(BaseModel):
    amount: float
    reason: Optional[str] = "Admin manual grant"

class SwitchPlanRequest(BaseModel):
    plan_id: str
    reset_credits: bool = False

class UpdateFeatureFlagsRequest(BaseModel):
    feature_flags: Dict[str, bool]

# --- Usage & Metering Schemas ---
class ProviderUsageBreakdown(BaseModel):
    provider: str
    operation: str
    total_units: float
    total_cost_usd: float
    total_credits_deducted: float
    total_requests: int

class AdminUsageRow(BaseModel):
    id: str
    org_id: Optional[str] = None
    org_name: Optional[str] = None
    user_email: Optional[str] = None
    job_id: Optional[str] = None
    provider: str
    operation: str
    units: float
    cost_usd: float
    credits_deducted: float
    created_at: str

class AdminUsageSummary(BaseModel):
    total_cost_usd: float
    total_credits_deducted: float
    total_requests: int
    by_provider: List[ProviderUsageBreakdown]
    recent_logs: List[AdminUsageRow]

# --- User Management & Impersonation ---
class AdminUserRow(BaseModel):
    id: str
    email: str
    role: str
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    trial_started_at: Optional[str] = None
    trial_expires_at: Optional[str] = None
    created_at: str
    status: str = "active"

class UserStatusUpdate(BaseModel):
    status: str # 'active' | 'suspended'

class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
