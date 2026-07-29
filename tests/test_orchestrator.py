"""Agent orchestrator – scope guard & routing via LangGraph path."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.agents.orchestrator import run_agent
from app.models.schemas import Intent


def test_out_of_scope_no_ai():
    result = asyncio.get_event_loop().run_until_complete(
        run_agent("Write a poem about cats")
    )
    assert result.intent == Intent.OUT_OF_SCOPE
    assert result.ai_used is False
    assert "BusMate" in result.reply


def test_greeting():
    result = asyncio.get_event_loop().run_until_complete(run_agent("Hello"))
    assert result.intent == Intent.GREETING
    assert result.agent == "GreetingAgent"


def test_booking_path():
    result = asyncio.get_event_loop().run_until_complete(
        run_agent("Search buses from Chennai to Madurai")
    )
    assert result.intent == Intent.BOOKING
    assert result.agent == "BookingAgent"
