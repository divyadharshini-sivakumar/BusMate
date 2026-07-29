"""
Real CrewAI multi-agent collaboration for BusMate.

Uses crewai[openai] native LLM (OpenRouter-compatible). When AI is unavailable,
falls back to deterministic string assembly so the API never crashes.
"""

from __future__ import annotations

from typing import Optional

from app.agents.llm import get_crewai_llm
from app.agents.rag import keyword_retrieve
from app.config import get_settings
from app.services import demo_data


def _search_tool_fn(origin: str, destination: str) -> str:
    trips = demo_data.search_trips(origin, destination)
    if not trips:
        return f"No buses from {origin} to {destination}."
    lines = [
        f"- {t['bus_number']} ({t['operator']}) | ₹{t['fare']} | "
        f"{t['available_seats']} seats | {t['bus_type']}"
        for t in trips
    ]
    return "Available buses:\n" + "\n".join(lines)


def run_booking_crew(user_message: str) -> tuple[str, bool]:
    """
    Sequential Crew: Researcher (policy/context) -> Booking specialist.
    Returns (reply, ai_used).
    """
    settings = get_settings()
    llm = get_crewai_llm()
    if llm is None:
        # Deterministic fallback without CrewAI runtime
        lower = user_message.lower()
        cities = ["chennai", "madurai", "coimbatore", "trichy"]
        found = [c for c in cities if c in lower]
        if len(found) >= 2:
            return _search_tool_fn(found[0].title(), found[1].title()), False
        return (
            "I can search Chennai-region buses. Try: "
            "“Search buses from Chennai to Madurai”. "
            "(AI crew temporarily unavailable.)",
            False,
        )

    try:
        from crewai import Agent, Crew, Process, Task
        from crewai.tools import tool

        @tool("search_buses")
        def search_buses(origin: str, destination: str) -> str:
            """Search demo buses between two cities (Chennai region)."""
            return _search_tool_fn(origin, destination)

        researcher = Agent(
            role="Bus Policy Researcher",
            goal="Gather relevant policy snippets and route context for the user query.",
            backstory=(
                "You know BusMate policies and Chennai-region routes. "
                "You only work on bus travel topics."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        booker = Agent(
            role="Booking Specialist",
            goal="Help the user find and book buses using tools when needed.",
            backstory=(
                "You are the BusMate booking expert. Use the search_buses tool "
                "for availability. Never discuss non-bus topics."
            ),
            llm=llm,
            tools=[search_buses],
            verbose=False,
            allow_delegation=False,
        )

        snippets = keyword_retrieve(user_message, top_k=2)
        context = "\n".join(snippets) if snippets else "No extra policy context."

        t1 = Task(
            description=(
                f"Summarize any policy/route notes relevant to: {user_message}\n"
                f"Context:\n{context}"
            ),
            expected_output="Short bullet notes for the booking specialist.",
            agent=researcher,
        )
        t2 = Task(
            description=(
                f"Respond to the passenger request: {user_message}\n"
                "If they want buses between cities, call search_buses. "
                "Stay concise and on-topic."
            ),
            expected_output="A helpful booking-oriented reply for the passenger.",
            agent=booker,
            context=[t1],
        )

        crew = Crew(
            agents=[researcher, booker],
            tasks=[t1, t2],
            process=Process.sequential,
            verbose=False,
        )
        result = crew.kickoff()
        text = str(result).strip() if result else ""
        if not text:
            return (
                "Crew finished without text. Please use the Search page.",
                True,
            )
        return text, True
    except Exception as exc:
        return (
            f"Booking crew could not complete ({type(exc).__name__}). "
            "Use the Search page — core booking still works.",
            False,
        )


def run_complaint_crew(user_message: str) -> tuple[str, bool, bool]:
    """
    Complaint analyst + resolver crew.
    Returns (reply, ai_used, escalated).
    """
    llm = get_crewai_llm()
    if llm is None:
        return (
            "I'm sorry you're facing an issue. Please use the Complaints form "
            "(category + description). Our team will follow up.",
            False,
            True,
        )

    try:
        from crewai import Agent, Crew, Process, Task

        analyst = Agent(
            role="Complaint Analyst",
            goal="Classify the bus-travel complaint and suggest severity.",
            backstory="You triage passenger issues for BusMate support.",
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        resolver = Agent(
            role="Complaint Resolver",
            goal="Empathize and decide if human escalation is needed.",
            backstory="You draft passenger-facing replies and escalate when needed.",
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        t1 = Task(
            description=f"Analyze this complaint: {user_message}",
            expected_output="Category, severity (low/medium/high), short summary.",
            agent=analyst,
        )
        t2 = Task(
            description=(
                "Write an empathetic reply. If severity is high or user is "
                "very upset, say you are escalating to human support."
            ),
            expected_output="Passenger-facing reply text.",
            agent=resolver,
            context=[t1],
        )

        crew = Crew(
            agents=[analyst, resolver],
            tasks=[t1, t2],
            process=Process.sequential,
            verbose=False,
        )
        result = str(crew.kickoff()).strip()
        escalated = any(
            w in result.lower() for w in ("escalat", "human support", "agent will contact")
        )
        return result or "We've logged your complaint.", True, escalated
    except Exception:
        return (
            "We've recorded your issue and flagged it for human support.",
            False,
            True,
        )
