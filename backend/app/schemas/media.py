from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional, Dict, Any
from datetime import datetime

_SECRET_EXACT = {
    "custom_api_key",
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "password",
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "authorization",
    "cookie",
    "hunter_api_key",
    "linkedin_cookie",
    "linkedin_byok_cookie",
    "private_key",
    "client_secret",
}


def is_secret_field(name: str) -> bool:
    lowered = str(name or "").lower().replace("-", "_")
    if lowered in _SECRET_EXACT:
        return True
    return lowered.endswith("_api_key") or lowered.endswith("_secret") or lowered.endswith("_token") or lowered.endswith("_password") or "api_key" in lowered


def strip_secret_fields(value: Any) -> Any:
    """Drop legacy secret fields from response payloads, including nested objects."""
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if is_secret_field(key):
                continue
            cleaned[key] = strip_secret_fields(item)
        return cleaned
    if isinstance(value, list):
        return [strip_secret_fields(item) for item in value]
    return value


def _secret_values(value: Any) -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if is_secret_field(key) and isinstance(item, str) and len(item) >= 6:
                found.append(item)
            else:
                found.extend(_secret_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_secret_values(item))
    return found


class MediaGenerationRequest(BaseModel):
    prompt: str
    provider: str = "gemini"
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
    # See Job.failure_kind in schemas/discover.py.
    failure_kind: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _public_dto(cls, data):
        if isinstance(data, dict):
            payload = dict(data)
            raw_parameters = payload.get("parameters")
        else:
            raw_parameters = getattr(data, "parameters", None)
            payload = {
                "id": getattr(data, "id", None),
                "job_id": getattr(data, "job_id", None) or getattr(data, "id", None),
                "status": getattr(data, "status", None),
                "prompt": getattr(data, "prompt", None),
                "provider": getattr(data, "provider", None),
                "provider_job_id": getattr(data, "provider_job_id", None),
                "created_at": getattr(data, "created_at", None),
                "updated_at": getattr(data, "updated_at", None),
                "parameters": raw_parameters,
                "result_url": getattr(data, "result_url", None),
                "error_message": getattr(data, "error_message", None),
                "failure_kind": getattr(data, "failure_kind", None),
            }
        secrets = _secret_values(raw_parameters)
        error = payload.get("error_message")
        if isinstance(error, str):
            for secret in secrets:
                error = error.replace(secret, "[REDACTED]")
            payload["error_message"] = error
        payload["parameters"] = strip_secret_fields(raw_parameters) if raw_parameters else raw_parameters
        if payload.get("id") and not payload.get("job_id"):
            payload["job_id"] = payload["id"]
        return payload

    def __init__(self, **data):
        if "id" in data and "job_id" not in data:
            data["job_id"] = data["id"]
        super().__init__(**data)
