"""Payload-free application events on the existing Python logging transport.

Never pass exception messages, request/response bodies, URLs, emails or tokens.
Only the allowlisted correlation fields and exception class are recorded. No
external error-reporting transport is implied or configured by this module.
"""
from contextvars import ContextVar
import json
import logging
import re

request_id_context = ContextVar("request_id", default=None)
_ID = re.compile(r"^[a-zA-Z0-9_.:-]{1,128}$")


def _identifier(value):
    text = str(value) if value is not None else ""
    return text if _ID.fullmatch(text) else None


def log_event(logger, event, *, error=None, level=logging.WARNING,
              request_id=None, tenant_id=None, actor_id=None, job_id=None):
    """Emit a stable event and structured IDs, without payload/traceback dumps."""
    fields = {
        "event": _identifier(event) or "application_event",
        "request_id": _identifier(request_id or request_id_context.get()),
        "tenant_id": _identifier(tenant_id),
        "actor_id": _identifier(actor_id),
        "job_id": _identifier(job_id),
        "error_type": _identifier(type(error).__name__) if error is not None else None,
    }
    # JSON message keeps correlation visible with the default console handler;
    # extra fields also support collectors that already consume LogRecord data.
    logger.log(level, json.dumps(fields, separators=(",", ":")), extra=fields)
