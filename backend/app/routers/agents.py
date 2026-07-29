"""Agent chat endpoint for BusMate demo mode."""

from fastapi import APIRouter

from app.agents.orchestrator import run_agent
from app.models.schemas import (
    AgentChatRequest,
    AgentChatResponse,
)

router = APIRouter()


@router.post(
    "/chat",
    response_model=AgentChatResponse,
)
async def agent_chat(
    body: AgentChatRequest,
):
    """
    Run the BusMate assistant without requiring login.

    In demo mode, a fixed passenger user ID is used when the
    frontend does not provide one.
    """

    user_id = (
        body.user_id
        or "user-passenger-demo"
    )

    result = await run_agent(
        message=body.message,
        session_id=body.session_id,
        user_id=user_id,
        context=body.context,
    )

    return result