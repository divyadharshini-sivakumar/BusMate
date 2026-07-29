"""Supabase client factory – uses service role on backend only."""

from typing import Any, Optional

from app.config import get_settings

_client: Any = None


def get_supabase():
    """Return a Supabase client or None if not configured (demo mode)."""
    global _client
    settings = get_settings()
    if not settings.supabase_configured:
        return None
    if _client is None:
        from supabase import create_client

        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client


def is_demo() -> bool:
    settings = get_settings()
    return settings.demo_mode or not settings.supabase_configured
