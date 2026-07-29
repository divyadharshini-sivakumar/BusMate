"""
LangGraph workflow for the BusMate Chennai MTC assistant.

The assistant supports:
- Chennai MTC route search
- Fare and journey guidance
- Ticket information
- Live-tracking guidance
- Policies
- Complaints
- Feedback
- Graceful rule-based fallback when AI services are unavailable
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, TypedDict

from app.agents.crew_team import (
    run_booking_crew,
    run_complaint_crew,
)
from app.agents.intent import classify_intent
from app.agents.llm import (
    OUT_OF_SCOPE_REPLY,
    POLICY_SYSTEM,
    chat_completion_sync,
)
from app.agents.rag import keyword_retrieve
from app.models.schemas import Intent
from app.services import demo_data


class GraphState(TypedDict, total=False):
    message: str
    session_id: str
    user_id: Optional[str]
    intent: str
    reply: str
    agent: str
    ai_used: bool
    escalated: bool
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------


def _normalize(value: str) -> str:
    """Normalize text for reliable matching."""

    cleaned = re.sub(
        r"[^a-z0-9\s.]",
        " ",
        str(value).casefold(),
    )

    return " ".join(cleaned.split())


def _format_duration(minutes: int) -> str:
    """Convert minutes into a readable duration."""

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours == 0:
        return f"{remaining_minutes} minutes"

    if remaining_minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"

    return (
        f"{hours} hour{'s' if hours != 1 else ''} "
        f"{remaining_minutes} minutes"
    )


def _format_time(value: Any) -> str:
    """Format an ISO datetime value for assistant replies."""

    if not value:
        return "Not available"

    try:
        from datetime import datetime

        parsed = datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        )

        return parsed.strftime("%I:%M %p")
    except (TypeError, ValueError):
        return str(value)


def _all_official_stops() -> List[str]:
    """Return all official stops ordered longest-first."""

    stops = demo_data.get_all_stops()

    return sorted(
        stops,
        key=lambda stop: len(_normalize(stop)),
        reverse=True,
    )


def _stop_aliases(stop: str) -> List[str]:
    """Produce useful matching aliases for an official stop."""

    normalized = _normalize(stop)

    aliases = {
        normalized,
        normalized.replace(".", ""),
    }

    replacements = {
        "m.g.r.": "mgr",
        "m.g.r": "mgr",
        "i.t.": "it",
        "i.t": "it",
        "b.s.": "bus stand",
        "b.s": "bus stand",
        "rly.": "railway",
        "rly": "railway",
        "stn.": "station",
        "stn": "station",
    }

    for source, replacement in replacements.items():
        if source in normalized:
            aliases.add(
                normalized.replace(
                    source,
                    replacement,
                )
            )

    aliases.add(
        normalized
        .replace(".", "")
        .replace("  ", " ")
    )

    return [
        alias.strip()
        for alias in aliases
        if alias.strip()
    ]


def _find_stop_mentions(
    message: str,
) -> List[str]:
    """
    Detect official MTC stops mentioned in a user message.

    The result follows the order in which stops occur in the
    sentence.
    """

    normalized_message = _normalize(message)
    simplified_message = normalized_message.replace(
        ".",
        "",
    )

    matches: List[tuple[int, str]] = []
    matched_stops: set[str] = set()

    for stop in _all_official_stops():
        if stop in matched_stops:
            continue

        best_position: Optional[int] = None

        for alias in _stop_aliases(stop):
            candidates = {
                alias,
                alias.replace(".", ""),
            }

            for candidate in candidates:
                if len(candidate) < 3:
                    continue

                position = normalized_message.find(candidate)

                if position < 0:
                    position = simplified_message.find(
                        candidate.replace(".", "")
                    )

                if position >= 0:
                    if (
                        best_position is None
                        or position < best_position
                    ):
                        best_position = position

        if best_position is not None:
            matches.append(
                (
                    best_position,
                    stop,
                )
            )
            matched_stops.add(stop)

    matches.sort(
        key=lambda item: item[0]
    )

    # Remove shorter duplicate stop names that occur at the same
    # location inside a longer official stop name.
    final_stops: List[str] = []

    for _, stop in matches:
        normalized_stop = _normalize(stop)

        duplicate = any(
            normalized_stop
            in _normalize(existing_stop)
            or _normalize(existing_stop)
            in normalized_stop
            for existing_stop in final_stops
        )

        if not duplicate:
            final_stops.append(stop)

    return final_stops


def _extract_route_request(
    message: str,
) -> tuple[Optional[str], Optional[str]]:
    """Extract boarding and destination stops from a message."""

    stops = _find_stop_mentions(message)

    if len(stops) >= 2:
        return stops[0], stops[1]

    if len(stops) == 1:
        normalized_message = _normalize(message)

        destination_phrases = (
            "reach",
            "go to",
            "going to",
            "get to",
            "travel to",
            "bus to",
            "towards",
        )

        if any(
            phrase in normalized_message
            for phrase in destination_phrases
        ):
            return None, stops[0]

        return stops[0], None

    return None, None


def _route_reply(
    message: str,
) -> Optional[Dict[str, Any]]:
    """
    Build a deterministic route answer using imported MTC data.

    Returns None when the message does not contain enough stop
    information.
    """

    origin, destination = _extract_route_request(
        message
    )

    if not origin and not destination:
        return None

    if destination and not origin:
        return {
            "reply": (
                f"I found the destination **{destination}**, but I "
                "also need your boarding stop.\n\n"
                "For example:\n"
                f'“Which bus goes from Avadi to {destination}?”'
            ),
            "data": {
                "origin": None,
                "destination": destination,
                "routes": [],
            },
        }

    if origin and not destination:
        return {
            "reply": (
                f"I found your boarding stop as **{origin}**. "
                "Please tell me where you want to go."
            ),
            "data": {
                "origin": origin,
                "destination": None,
                "routes": [],
            },
        }

    if not origin or not destination:
        return None

    trips = demo_data.search_trips(
        origin=origin,
        destination=destination,
    )

    if not trips:
        reverse_trips = demo_data.search_trips(
            origin=destination,
            destination=origin,
        )

        if reverse_trips:
            return {
                "reply": (
                    f"I found route data in the opposite direction, "
                    f"from **{destination}** to **{origin}**, but no "
                    "direct route in your requested direction.\n\n"
                    "Try a nearby official stop or use the Search page."
                ),
                "data": {
                    "origin": origin,
                    "destination": destination,
                    "routes": [],
                },
            }

        return {
            "reply": (
                f"I could not find a direct imported MTC route from "
                f"**{origin}** to **{destination}**.\n\n"
                "Try selecting a nearby official stop name from the "
                "Search page. A transfer may also be required."
            ),
            "data": {
                "origin": origin,
                "destination": destination,
                "routes": [],
            },
        }

    best_trips = trips[:3]

    reply_lines = [
        f"I found {len(trips)} direct MTC route"
        f"{'s' if len(trips) != 1 else ''} from "
        f"**{origin}** to **{destination}**.",
        "",
        "Best options:",
    ]

    route_data: List[Dict[str, Any]] = []

    for index, trip in enumerate(
        best_trips,
        start=1,
    ):
        route_number = trip.get(
            "route_number",
            "MTC",
        )

        fare = float(
            trip.get(
                "fare",
                0,
            )
        )

        duration = int(
            trip.get(
                "duration_minutes",
                0,
            )
        )

        departure = _format_time(
            trip.get("departure_time")
        )

        available_seats = int(
            trip.get(
                "available_seats",
                0,
            )
        )

        reply_lines.extend(
            [
                "",
                f"{index}. **Route {route_number}**",
                f"   - Board at: {origin}",
                f"   - Get down at: {destination}",
                f"   - Estimated fare: ₹{fare:.0f}",
                f"   - Duration: {_format_duration(duration)}",
                f"   - Next simulated departure: {departure}",
                f"   - Seats shown available: {available_seats}",
            ]
        )

        route_data.append(
            {
                "id": trip.get("id"),
                "route_number": route_number,
                "bus_number": trip.get(
                    "bus_number"
                ),
                "origin": origin,
                "destination": destination,
                "fare": fare,
                "duration_minutes": duration,
                "departure_time": trip.get(
                    "departure_time"
                ),
                "arrival_time": trip.get(
                    "arrival_time"
                ),
                "available_seats": available_seats,
                "stops": trip.get(
                    "stops",
                    [],
                ),
            }
        )

    reply_lines.extend(
        [
            "",
            "Open **Search** to view the full route and select seats.",
        ]
    )

    return {
        "reply": "\n".join(reply_lines),
        "data": {
            "origin": origin,
            "destination": destination,
            "routes": route_data,
            "total_routes": len(trips),
        },
    }


def _latest_booking(
    user_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Return the user's most recent demo booking."""

    resolved_user_id = (
        user_id
        or "user-passenger-demo"
    )

    bookings = demo_data.list_user_bookings(
        resolved_user_id
    )

    if not bookings:
        return None

    return bookings[0]


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


def node_classify(
    state: GraphState,
) -> GraphState:
    """Classify the user's intent with route-query safeguards."""

    message = state["message"]
    normalized = _normalize(message)

    route_keywords = (
        "which bus",
        "bus goes",
        "how do i reach",
        "how to reach",
        "how can i reach",
        "route from",
        "bus from",
        "travel from",
        "go from",
        "fare from",
        "fare to",
        "bus to",
    )

    route_stops = _find_stop_mentions(
        message
    )

    if (
        any(
            keyword in normalized
            for keyword in route_keywords
        )
        or len(route_stops) >= 2
    ):
        intent = Intent.BOOKING

    elif any(
        keyword in normalized
        for keyword in (
            "my ticket",
            "latest ticket",
            "show ticket",
            "pnr",
            "booking details",
            "my booking",
        )
    ):
        intent = Intent.TICKET

    elif any(
        keyword in normalized
        for keyword in (
            "track",
            "where is my bus",
            "bus location",
            "live location",
            "eta",
            "next stop",
        )
    ):
        intent = Intent.TRACKING

    elif any(
        keyword in normalized
        for keyword in (
            "complaint",
            "bus is late",
            "driver issue",
            "conductor issue",
            "lost item",
            "unsafe",
            "overcrowded",
        )
    ):
        intent = Intent.COMPLAINT

    else:
        intent = classify_intent(
            message
        )

    return {
        **state,
        "intent": intent.value,
    }


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


def node_greeting(
    state: GraphState,
) -> GraphState:
    return {
        **state,
        "reply": (
            "Hello! I’m BusMate, your Chennai MTC travel "
            "assistant.\n\n"
            "You can ask me things like:\n"
            "- Which bus goes from Avadi to Koyambedu?\n"
            "- How do I reach Siruseri IT Park?\n"
            "- Show my latest ticket\n"
            "- Track my booked bus\n"
            "- How can I register a complaint?"
        ),
        "agent": "GreetingAgent",
        "ai_used": False,
        "escalated": False,
    }


def node_out_of_scope(
    state: GraphState,
) -> GraphState:
    return {
        **state,
        "reply": OUT_OF_SCOPE_REPLY,
        "agent": "ScopeGuard",
        "ai_used": False,
        "escalated": False,
    }


def node_booking(
    state: GraphState,
) -> GraphState:
    """
    Handle route and booking questions.

    Official imported route data is always checked first.
    CrewAI is only used when the question is not a clear
    origin-to-destination query.
    """

    route_result = _route_reply(
        state["message"]
    )

    if route_result:
        return {
            **state,
            "reply": route_result["reply"],
            "agent": "MTCJourneyAgent",
            "ai_used": False,
            "escalated": False,
            "data": route_result["data"],
        }

    try:
        crew_reply, ai_used = run_booking_crew(
            state["message"]
        )

        if crew_reply:
            return {
                **state,
                "reply": crew_reply,
                "agent": "BookingAgent",
                "ai_used": ai_used,
                "escalated": False,
            }

    except Exception:
        pass

    return {
        **state,
        "reply": (
            "Please include both your boarding stop and "
            "destination.\n\n"
            "Example: **Which bus goes from Avadi to "
            "Koyambedu?**"
        ),
        "agent": "MTCJourneyAgent",
        "ai_used": False,
        "escalated": False,
    }


def node_ticket(
    state: GraphState,
) -> GraphState:
    booking = _latest_booking(
        state.get("user_id")
    )

    if not booking:
        return {
            **state,
            "reply": (
                "You do not have any bookings yet.\n\n"
                "Open **Search**, choose an MTC route, select "
                "a seat, and confirm your booking."
            ),
            "agent": "TicketAgent",
            "ai_used": False,
            "escalated": False,
            "data": {
                "booking": None,
            },
        }

    passenger_names = booking.get(
        "passenger_names",
        [],
    )

    passenger_text = (
        ", ".join(passenger_names)
        if passenger_names
        else "Passenger"
    )

    reply = (
        "Here is your latest ticket:\n\n"
        f"- **PNR:** {booking.get('pnr')}\n"
        f"- **Passenger:** {passenger_text}\n"
        f"- **Route:** {booking.get('route_number', 'MTC')}\n"
        f"- **From:** {booking.get('origin', 'Not available')}\n"
        f"- **To:** {booking.get('destination', 'Not available')}\n"
        f"- **Seats:** {', '.join(booking.get('seats', []))}\n"
        f"- **Fare:** ₹{float(booking.get('total_fare', 0)):.0f}\n"
        f"- **Status:** {str(booking.get('status', 'confirmed')).upper()}\n\n"
        "Open **My Tickets** to view the QR code or download "
        "the PDF."
    )

    return {
        **state,
        "reply": reply,
        "agent": "TicketAgent",
        "ai_used": False,
        "escalated": False,
        "data": {
            "booking": {
                "id": booking.get("id"),
                "pnr": booking.get("pnr"),
                "route_number": booking.get(
                    "route_number"
                ),
                "origin": booking.get("origin"),
                "destination": booking.get(
                    "destination"
                ),
                "seats": booking.get(
                    "seats",
                    [],
                ),
                "status": booking.get(
                    "status"
                ),
            }
        },
    }


def node_tracking(
    state: GraphState,
) -> GraphState:
    booking = _latest_booking(
        state.get("user_id")
    )

    if not booking:
        return {
            **state,
            "reply": (
                "You do not have a booking available to track.\n\n"
                "Book a bus first, then open **My Tickets → "
                "Track bus**."
            ),
            "agent": "JourneyAgent",
            "ai_used": False,
            "escalated": False,
            "data": {
                "booking_id": None,
            },
        }

    return {
        **state,
        "reply": (
            "Your latest booked bus is ready for tracking:\n\n"
            f"- **PNR:** {booking.get('pnr')}\n"
            f"- **Bus:** {booking.get('bus_number', 'MTC Bus')}\n"
            f"- **Route:** {booking.get('route_number', 'MTC')}\n"
            f"- **Journey:** {booking.get('origin')} → "
            f"{booking.get('destination')}\n\n"
            "Open **My Tickets**, then select **Track bus** to "
            "view the simulated live map, ETA, speed, next stop, "
            "and route timeline."
        ),
        "agent": "JourneyAgent",
        "ai_used": False,
        "escalated": False,
        "data": {
            "booking_id": booking.get("id"),
            "bus_number": booking.get(
                "bus_number"
            ),
            "route_number": booking.get(
                "route_number"
            ),
        },
    }


def node_policy(
    state: GraphState,
) -> GraphState:
    docs = keyword_retrieve(
        state["message"],
        top_k=4,
    )

    context = (
        "\n\n---\n\n".join(docs)
        if docs
        else "No policy documents loaded."
    )

    try:
        llm_reply = chat_completion_sync(
            [
                {
                    "role": "system",
                    "content": POLICY_SYSTEM,
                },
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context}\n\n"
                        f"Question: {state['message']}"
                    ),
                },
            ]
        )
    except Exception:
        llm_reply = None

    if llm_reply:
        reply = llm_reply
        ai_used = True

    elif docs:
        reply = (
            "Here is the relevant policy information:\n\n"
            + "\n\n".join(docs[:2])
        )
        ai_used = False

    else:
        normalized = _normalize(
            state["message"]
        )

        if "cancel" in normalized:
            reply = (
                "BusMate demo cancellation policy:\n\n"
                "- Confirmed demo tickets can be treated as "
                "non-refundable after departure.\n"
                "- Before departure, cancellation can be "
                "requested through support.\n"
                "- Refund processing is simulated in this "
                "project.\n\n"
                "For the production version, official MTC "
                "rules must be used."
            )
        else:
            reply = (
                "The policy knowledge base is currently "
                "unavailable. Please use the Help section or "
                "contact BusMate support."
            )

        ai_used = False

    return {
        **state,
        "reply": reply,
        "agent": "KnowledgeAgent",
        "ai_used": ai_used,
        "escalated": False,
        "data": {
            "sources": len(docs),
        },
    }


def node_complaint(
    state: GraphState,
) -> GraphState:
    normalized = _normalize(
        state["message"]
    )

    serious_keywords = (
        "unsafe",
        "harassment",
        "accident",
        "threat",
        "emergency",
        "violence",
    )

    escalated = any(
        keyword in normalized
        for keyword in serious_keywords
    )

    try:
        crew_reply, ai_used, crew_escalated = (
            run_complaint_crew(
                state["message"]
            )
        )

        if crew_reply:
            return {
                **state,
                "reply": crew_reply,
                "agent": "ComplaintAgent",
                "ai_used": ai_used,
                "escalated": (
                    escalated
                    or crew_escalated
                ),
            }

    except Exception:
        pass

    reply = (
        "You can register a complaint from the BusMate "
        "complaint section.\n\n"
        "Please include:\n"
        "1. Booking ID or PNR, if available\n"
        "2. Bus or route number\n"
        "3. Complaint category\n"
        "4. Location and approximate time\n"
        "5. A clear description of what happened\n\n"
    )

    if escalated:
        reply += (
            "This appears safety-related and should be treated "
            "as high priority. Contact the relevant emergency "
            "or transport authority immediately when there is "
            "an active danger."
        )
    else:
        reply += (
            "The complaint will be categorized and shown to the "
            "admin for follow-up."
        )

    return {
        **state,
        "reply": reply,
        "agent": "ComplaintAgent",
        "ai_used": False,
        "escalated": escalated,
    }


def node_feedback(
    state: GraphState,
) -> GraphState:
    return {
        **state,
        "reply": (
            "Thank you for sharing your feedback.\n\n"
            "Please provide:\n"
            "- A rating from 1 to 5\n"
            "- Your booking ID, if relevant\n"
            "- A short comment about the bus, route, booking, "
            "or tracking experience"
        ),
        "agent": "FeedbackAgent",
        "ai_used": False,
        "escalated": False,
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def route_by_intent(
    state: GraphState,
) -> Literal[
    "greeting",
    "out_of_scope",
    "booking",
    "ticket",
    "tracking",
    "policy",
    "complaint",
    "feedback",
]:
    mapping = {
        Intent.GREETING.value: "greeting",
        Intent.OUT_OF_SCOPE.value: "out_of_scope",
        Intent.BOOKING.value: "booking",
        Intent.TICKET.value: "ticket",
        Intent.TRACKING.value: "tracking",
        Intent.JOURNEY.value: "tracking",
        Intent.POLICY.value: "policy",
        Intent.COMPLAINT.value: "complaint",
        Intent.FEEDBACK.value: "feedback",
    }

    return mapping.get(
        state.get(
            "intent",
            "",
        ),
        "out_of_scope",
    )  # type: ignore[return-value]


def build_graph():
    """Compile the LangGraph workflow."""

    try:
        from langgraph.graph import (
            END,
            StateGraph,
        )
    except ImportError:
        return None

    graph = StateGraph(
        GraphState
    )

    graph.add_node(
        "classify",
        node_classify,
    )
    graph.add_node(
        "greeting",
        node_greeting,
    )
    graph.add_node(
        "out_of_scope",
        node_out_of_scope,
    )
    graph.add_node(
        "booking",
        node_booking,
    )
    graph.add_node(
        "ticket",
        node_ticket,
    )
    graph.add_node(
        "tracking",
        node_tracking,
    )
    graph.add_node(
        "policy",
        node_policy,
    )
    graph.add_node(
        "complaint",
        node_complaint,
    )
    graph.add_node(
        "feedback",
        node_feedback,
    )

    graph.set_entry_point(
        "classify"
    )

    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "greeting": "greeting",
            "out_of_scope": "out_of_scope",
            "booking": "booking",
            "ticket": "ticket",
            "tracking": "tracking",
            "policy": "policy",
            "complaint": "complaint",
            "feedback": "feedback",
        },
    )

    for node_name in (
        "greeting",
        "out_of_scope",
        "booking",
        "ticket",
        "tracking",
        "policy",
        "complaint",
        "feedback",
    ):
        graph.add_edge(
            node_name,
            END,
        )

    return graph.compile()


_COMPILED = None


def get_graph():
    """Return the cached compiled graph."""

    global _COMPILED

    if _COMPILED is None:
        _COMPILED = build_graph()

    return _COMPILED


def run_graph(
    message: str,
    session_id: str,
    user_id: Optional[str] = None,
) -> GraphState:
    """Run the assistant graph or its manual fallback."""

    graph = get_graph()

    initial: GraphState = {
        "message": message,
        "session_id": session_id,
        "user_id": (
            user_id
            or "user-passenger-demo"
        ),
        "ai_used": False,
        "escalated": False,
        "data": {},
    }

    if graph is None:
        state = node_classify(
            initial
        )

        route = route_by_intent(
            state
        )

        handlers = {
            "greeting": node_greeting,
            "out_of_scope": node_out_of_scope,
            "booking": node_booking,
            "ticket": node_ticket,
            "tracking": node_tracking,
            "policy": node_policy,
            "complaint": node_complaint,
            "feedback": node_feedback,
        }

        return handlers[route](
            state
        )

    return graph.invoke(
        initial
    )  # type: ignore[return-value]