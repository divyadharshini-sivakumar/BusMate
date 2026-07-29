"""
BusMate agent entrypoint.

Flow:
  1. Isolated session memory
  2. LangGraph StateGraph (intent classify → conditional route)
  3. Booking / Complaint nodes call real CrewAI crews when AI is available
  4. Policy node uses RAG (+ optional LLM)
  5. Always degrades gracefully without OpenRouter / CrewAI / LangGraph
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.agents import memory
from app.agents.graph import run_graph
from app.models.schemas import AgentChatResponse, Intent


async def run_agent(
    message: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> AgentChatResponse:
    sid = memory.get_or_create_session(session_id, user_id)
    memory.append_message(sid, "user", message)

    state = run_graph(message=message, session_id=sid, user_id=user_id)

    intent_raw = state.get("intent") or Intent.OUT_OF_SCOPE.value
    try:
        intent = Intent(intent_raw)
    except ValueError:
        intent = Intent.OUT_OF_SCOPE

    result = AgentChatResponse(
        intent=intent,
        reply=state.get("reply") or "How can I help with your bus journey?",
        agent=state.get("agent") or "ScopeGuard",
        data=state.get("data"),
        escalated=bool(state.get("escalated")),
        ai_used=bool(state.get("ai_used")),
        session_id=sid,
    )

    memory.append_message(
        sid,
        "assistant",
        result.reply,
        {"intent": result.intent.value, "agent": result.agent},
    )
    return result


async def crew_collaboration_demo(query: str) -> str:
    """Explicit CrewAI path for admin/debug demos."""
    from app.agents.crew_team import run_booking_crew

    reply, ai_used = run_booking_crew(query)
    return f"ai_used={ai_used}\n{reply}"
