import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.config import settings
from app.database import async_session, engine
from app.models import Base
from app.routers import auth, channels, preferences, videos, websub

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (consider using Alembic migrations for production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start scheduler
    from app.tasks.scheduler import start_scheduler

    scheduler = start_scheduler()
    logger.info("Application started")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("Application shut down")


app = FastAPI(
    title="YouTube Subscription Manager",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(videos.router, prefix="/api/v1/videos", tags=["videos"])
app.include_router(channels.router, prefix="/api/v1/channels", tags=["channels"])
app.include_router(preferences.router, prefix="/api/v1/preferences", tags=["preferences"])
app.include_router(websub.router, prefix="/api/v1/websub", tags=["websub"])


@app.get("/health")
async def health_check():
    checks = {"api": "ok"}

    # Database check
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Firebase check
    try:
        import firebase_admin

        firebase_admin.get_app()
        checks["firebase"] = "ok"
    except Exception:
        checks["firebase"] = "not_configured"

    overall = "ok" if checks.get("database") == "ok" else "degraded"
    return {"status": overall, "checks": checks}
