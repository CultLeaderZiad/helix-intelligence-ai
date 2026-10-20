import importlib
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, cors_origins
from app.db.session import engine
from app.core.observability import log_event, request_id_context
from app.middleware.rate_limit import RateLimitMiddleware
importlib.import_module("app.models")  # register ORM tables before startup validation

from app.api.routers import (
    auth,
    discover,
    creatives,
    analysis,
    admin,
    health,
    account,
    notifications,
    media,
    updates,
    providers,
    support,
    playbooks,
    dashboard,
    simulation,
    uploads,
    monitors,
    scout,
    leadgen,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.rls_role import assert_rls_role
    async with engine.begin() as conn:
        await assert_rls_role(conn)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
# Rate limiting: shields credential + expensive AI/scrape endpoints from
# brute-force and credit-burn bursts. Added after CORS so preflight OPTIONS
# requests are never throttled.
app.add_middleware(RateLimitMiddleware)

# Enterprise Security Headers Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    context_token = request_id_context.set(request_id)
    try:
        response: Response = await call_next(request)
    except Exception as exc:
        log_event(logger, "request_failed", error=exc, level=logging.ERROR)
        response = JSONResponse(status_code=500, content={"detail": {
            "code": "internal_error",
            "message": "The request could not be completed. Please retry.",
            "request_id": request_id,
        }})
    finally:
        request_id_context.reset(context_token)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(account.router, prefix=f"{settings.API_V1_STR}/account", tags=["account"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
app.include_router(discover.router, prefix=f"{settings.API_V1_STR}/discovery", tags=["discovery"])
app.include_router(creatives.router, prefix=f"{settings.API_V1_STR}/creatives", tags=["creatives"])
app.include_router(creatives.brands_router, prefix=f"{settings.API_V1_STR}/brands", tags=["brands"])
app.include_router(creatives.patterns_router, prefix=f"{settings.API_V1_STR}/patterns", tags=["patterns"])
app.include_router(analysis.insights_router, prefix=f"{settings.API_V1_STR}/insights", tags=["insights"])
app.include_router(media.router, prefix=f"{settings.API_V1_STR}/media", tags=["media"])
app.include_router(providers.router, prefix=f"{settings.API_V1_STR}", tags=["providers"])
app.include_router(updates.router, prefix=f"{settings.API_V1_STR}/updates", tags=["updates"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(support.router, prefix=f"{settings.API_V1_STR}/support", tags=["support"])
app.include_router(playbooks.router, prefix=f"{settings.API_V1_STR}/playbooks", tags=["playbooks"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(simulation.router, prefix=f"{settings.API_V1_STR}/simulation", tags=["simulation"])
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])
app.include_router(monitors.router, prefix=f"{settings.API_V1_STR}/monitors", tags=["monitors"])
app.include_router(scout.router, prefix=f"{settings.API_V1_STR}/scout", tags=["scout"])
app.include_router(scout.router, prefix="/api/v1/scout", tags=["scout"])
# Scout · Lead Generation (scrapling_engine worker) — separate router so Social/Atlas stays untouched
app.include_router(leadgen.router, prefix=f"{settings.API_V1_STR}/scout/leadgen", tags=["leadgen"])

# Locally stored media. This is served by a router rather than a StaticFiles
# mount so that access is checked: the old mount handed any file to anyone who
# could guess its name. Only reachable when R2 is unconfigured; see
# storage_service.
app.include_router(uploads.router, prefix="/uploads", tags=["uploads"])

@app.get("/")
@app.get("/api")
@app.get("/health")
@app.get("/api/health")
def root():
    return {
        "status": "ok",
        "service": "helix-backend",
        "message": "Welcome to Helix API. Service is online.",
    }
