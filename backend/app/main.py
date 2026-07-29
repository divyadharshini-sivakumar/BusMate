"""BusMate FastAPI entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

try:
    import structlog

    logger = structlog.get_logger()
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("busmate")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    admin,
    agents,
    auth,
    bookings,
    complaints,
    feedback,
    health,
    tickets,
    tracking,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    try:
        logger.info(
            "startup",
            environment=settings.environment,
            ai_available=settings.ai_available,
            supabase_configured=settings.supabase_configured,
            demo_mode=settings.demo_mode,
        )
    except TypeError:
        logger.info(
            "startup env=%s ai=%s supabase=%s demo=%s",
            settings.environment,
            settings.ai_available,
            settings.supabase_configured,
            settings.demo_mode,
        )
    yield
    logger.info("shutdown")


app = FastAPI(
    title="BusMate API",
    description="AI-assisted bus booking & journey companion – scoped to bus travel only.",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(tracking.router, prefix="/api/tracking", tags=["Tracking"])
app.include_router(complaints.router, prefix="/api/complaints", tags=["Complaints"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])


@app.get("/")
async def root():
    return {
        "service": "BusMate",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }
