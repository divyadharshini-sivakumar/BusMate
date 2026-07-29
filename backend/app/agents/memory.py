"""Isolated per-user session memory (in-process for demo)."""

from typing import Any, Dict, List
from uuid import uuid4

from app.services.demo_data import DEMO_SESSIONS


def get_or_create_session(session_id: str | None, user_id: str | None) -> str:
    sid = session_id or f"sess-{uuid4().hex[:12]}"
    if sid not in DEMO_SESSIONS:
        DEMO_SESSIONS[sid] = []
    return sid


def append_message(session_id: str, role: str, content: str, meta: Dict[str, Any] | None = None):
    DEMO_SESSIONS.setdefault(session_id, []).append(
        {"role": role, "content": content, "meta": meta or {}}
    )


def get_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    return DEMO_SESSIONS.get(session_id, [])[-limit:]


def clear_session(session_id: str):
    DEMO_SESSIONS.pop(session_id, None)
