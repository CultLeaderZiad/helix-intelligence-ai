"""Shared deadline, retry, token, and usage policy for model calls.

No provider is treated as successful when the call fails. Token counts and
cost stay null when the provider does not report them.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

from app.core.config import settings
from app.services.billing_service import ESTIMATED_PROVIDER_COSTS


class RetryableProviderError(RuntimeError):
    """A timeout or 429 that a worker may try again."""


@dataclass
class ChatResult:
    text: str
    provider: str
    model: str
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    latency_ms: int
    cost_usd: Optional[float]
    tokens_observed: bool


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def cost_from_tokens(provider: str, total_tokens: Optional[int]) -> Optional[float]:
    if total_tokens is None:
        return None
    rate = ESTIMATED_PROVIDER_COSTS.get("groq_tokens", 0.0)
    if provider.startswith("gemini"):
        rate = ESTIMATED_PROVIDER_COSTS.get("groq_tokens", 0.0)
    return float(total_tokens) * float(rate)


def usage_metadata(result: Optional[ChatResult], *, prompt_version: str = "") -> dict:
    if result is None:
        return {
            "tokens_observed": False,
            "prompt_tokens": None,
            "completion_tokens": None,
            "latency_ms": None,
            "cost_usd": None,
            "prompt_version": prompt_version,
        }
    return {
        "tokens_observed": result.tokens_observed,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "latency_ms": result.latency_ms,
        "cost_usd": result.cost_usd,
        "model": result.model,
        "provider": result.provider,
        "prompt_version": prompt_version,
    }


async def complete_chat(
    *,
    provider_name: str,
    url: str,
    api_key: str,
    model: str,
    messages: list,
    fallback_models: Optional[list] = None,
    allowed_hosts: Optional[set] = None,
    response_format: Optional[dict] = None,
    extra_headers: Optional[dict] = None,
    max_output_tokens: Optional[int] = None,
    timeout_s: Optional[float] = None,
    deadline_s: Optional[float] = None,
    max_retries: Optional[int] = None,
    backoff_s: float = 0.25,
    max_output_bytes: int = 65536,
) -> ChatResult:
    """OpenAI-compatible chat call with a hard deadline and bounded retries."""
    from app.services.safe_fetch import UnsafeFetch, safe_request_async

    if not api_key:
        raise RuntimeError(f"Missing required integration key for {provider_name}")

    token_cap = max_output_tokens or int(getattr(settings, "AI_MAX_OUTPUT_TOKENS", 1024) or 1024)
    timeout = float(timeout_s or getattr(settings, "AI_CALL_TIMEOUT_S", 20) or 20)
    deadline = time.monotonic() + float(deadline_s or getattr(settings, "AI_CALL_DEADLINE_S", 45) or 45)
    retries = int(max_retries if max_retries is not None else getattr(settings, "AI_MAX_RETRIES", 2) or 0)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    models = [model] + [item for item in (fallback_models or []) if item and item != model]
    last_error: Exception = RuntimeError(f"{provider_name} did not return a response")

    for chosen in models:
        attempt = 0
        while attempt <= retries:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RetryableProviderError(f"{provider_name} exceeded the call deadline")
            payload = {
                "model": chosen,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": token_cap,
            }
            if response_format is not None:
                payload["response_format"] = response_format
            started = time.monotonic()
            try:
                response = await safe_request_async(
                    "POST",
                    url,
                    headers=headers,
                    json=payload,
                    timeout=min(timeout, remaining),
                    allowed_hosts=allowed_hosts,
                    max_bytes=max_output_bytes,
                )
            except UnsafeFetch:
                raise
            except Exception as exc:
                last_error = exc
                attempt += 1
                if attempt > retries:
                    break
                await asyncio.sleep(min(backoff_s * (2 ** (attempt - 1)), max(0.0, deadline - time.monotonic())))
                continue

            latency_ms = int((time.monotonic() - started) * 1000)
            status = int(getattr(response, "status_code", 0) or 0)
            if status == 200:
                body = response.json()
                usage = body.get("usage") if isinstance(body, dict) else None
                text = (
                    ((body.get("choices") or [{}])[0].get("message") or {}).get("content")
                    if isinstance(body, dict) else ""
                ) or ""
                if len(text.encode("utf-8")) > max_output_bytes:
                    raise InvalidOutputSize(f"{provider_name} output exceeded {max_output_bytes} bytes")
                prompt_tokens = _int_or_none((usage or {}).get("prompt_tokens"))
                completion_tokens = _int_or_none((usage or {}).get("completion_tokens"))
                total_tokens = _int_or_none((usage or {}).get("total_tokens"))
                if total_tokens is None and (prompt_tokens is not None or completion_tokens is not None):
                    total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
                observed = usage is not None and total_tokens is not None
                return ChatResult(
                    text=text,
                    provider=provider_name,
                    model=chosen,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost_from_tokens(provider_name, total_tokens) if observed else None,
                    tokens_observed=observed,
                )
            if status == 429 or status >= 500:
                last_error = RetryableProviderError(f"{provider_name} HTTP {status}")
                attempt += 1
                if attempt > retries:
                    break
                await asyncio.sleep(min(backoff_s * (2 ** (attempt - 1)), max(0.0, deadline - time.monotonic())))
                continue
            last_error = RuntimeError(f"{provider_name} HTTP {status}")
            break

    if isinstance(last_error, RetryableProviderError):
        raise last_error
    raise last_error


class InvalidOutputSize(ValueError):
    pass


def remember(provider: Any, result: ChatResult) -> ChatResult:
    provider.last_usage = result
    provider.model = result.model
    return result
