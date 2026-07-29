"""OpenRouter / OpenAI-compatible LLM helpers for LangChain and CrewAI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import get_settings

BOOKING_SYSTEM = """You are BusMate Booking Agent. Help only with bus search, seats, fares, and booking for Chennai-region routes.
Never discuss unrelated topics. Be concise. If user asks outside scope, refuse politely."""

POLICY_SYSTEM = """You are BusMate Knowledge Agent. Answer ONLY using the provided policy context.
If context is insufficient, say you don't have that policy detail. Do not invent rules."""

COMPLAINT_SYSTEM = """You are BusMate Complaint Agent. Acknowledge issues empathetically, collect category and details,
and offer to escalate to human support when needed. Stay on bus-travel complaints only."""

OUT_OF_SCOPE_REPLY = (
    "I'm BusMate – I only help with bus booking, tickets, tracking, policies, "
    "complaints, and feedback for our routes. How can I assist with your journey?"
)


def get_openrouter_client():
    """Sync OpenAI client pointed at OpenRouter (or None if no key)."""
    settings = get_settings()
    if not settings.ai_available:
        return None
    try:
        from openai import OpenAI

        return OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": settings.frontend_url,
                "X-Title": "BusMate",
            },
        )
    except Exception:
        return None


def get_langchain_chat_model():
    """LangChain ChatOpenAI bound to OpenRouter, or None."""
    settings = get_settings()
    if not settings.ai_available:
        return None
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=0.3,
            max_tokens=512,
            default_headers={
                "HTTP-Referer": settings.frontend_url,
                "X-Title": "BusMate",
            },
        )
    except Exception:
        return None


def get_crewai_llm():
    """
    CrewAI LLM using native OpenAI provider pointed at OpenRouter.
    Avoids LiteLLM entirely (no Rust build on Windows).
    """
    settings = get_settings()
    if not settings.ai_available:
        return None
    try:
        from crewai import LLM

        model = settings.openrouter_model
        if not model.startswith(("openai/", "openrouter/")):
            model = f"openai/{model}" if "/" not in model else model

        return LLM(
            model=model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=0.3,
            max_tokens=512,
        )
    except Exception:
        return None


async def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> Optional[str]:
    """Async chat via OpenRouter; returns None on any failure."""
    settings = get_settings()
    if not settings.ai_available:
        return None
    try:
        import httpx

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.frontend_url,
            "X-Title": "BusMate",
        }
        payload: Dict[str, Any] = {
            "model": settings.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def chat_completion_sync(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> Optional[str]:
    """Sync variant for CrewAI / LangGraph nodes."""
    client = get_openrouter_client()
    if client is None:
        return None
    settings = get_settings()
    try:
        resp = client.chat.completions.create(
            model=settings.openrouter_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception:
        return None
