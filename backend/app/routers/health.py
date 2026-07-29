"""Health & readiness checks."""

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "healthy",
        "environment": settings.environment,
        "ai_available": settings.ai_available,
        "supabase_configured": settings.supabase_configured,
        "demo_mode": settings.demo_mode,
    }


@router.get("/health/ready")
async def readiness():
    settings = get_settings()
    checks = {
        "config": True,
        "supabase": settings.supabase_configured,
        "ai": settings.ai_available,
    }
    ready = checks["config"]  # AI is optional
    return {"ready": ready, "checks": checks}
