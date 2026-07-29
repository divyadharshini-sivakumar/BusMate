"""Complaint creation and complaint history for BusMate demo mode."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ComplaintCreate,
    ComplaintOut,
)
from app.services import demo_data

router = APIRouter()


def _simple_sentiment(
    text: str,
) -> str:
    """Classify complaint sentiment without external AI."""

    normalized = text.casefold()

    negative_words = (
        "bad",
        "worst",
        "delay",
        "late",
        "rude",
        "dirty",
        "cancel",
        "refund",
        "poor",
        "unsafe",
        "danger",
        "harassment",
        "overcrowded",
        "lost",
        "angry",
        "uncomfortable",
    )

    positive_words = (
        "good",
        "great",
        "thanks",
        "excellent",
        "clean",
        "helpful",
        "polite",
    )

    negative_score = sum(
        1
        for word in negative_words
        if word in normalized
    )

    positive_score = sum(
        1
        for word in positive_words
        if word in normalized
    )

    if negative_score > positive_score:
        return "negative"

    if positive_score > negative_score:
        return "positive"

    return "neutral"


def _analyse_complaint(
    category: str,
    priority: str,
    description: str,
) -> Dict[str, Any]:
    """Apply deterministic complaint classification."""

    normalized = description.casefold()

    safety_keywords = (
        "unsafe",
        "danger",
        "accident",
        "harassment",
        "threat",
        "violence",
        "emergency",
        "injury",
        "driver drunk",
        "reckless",
    )

    high_priority_keywords = (
        "40 minutes late",
        "one hour late",
        "very late",
        "stranded",
        "cancelled",
        "lost child",
        "lost luggage",
        "ticket charged twice",
        "overcharged",
    )

    escalated = any(
        keyword in normalized
        for keyword in safety_keywords
    )

    analysed_priority = priority

    if escalated:
        analysed_priority = "high"
    elif any(
        keyword in normalized
        for keyword in high_priority_keywords
    ):
        analysed_priority = "high"

    analysed_category = category

    if any(
        keyword in normalized
        for keyword in (
            "late",
            "delay",
            "waiting",
        )
    ):
        analysed_category = "Bus delay"

    elif any(
        keyword in normalized
        for keyword in (
            "driver",
            "conductor",
            "rude",
            "behaviour",
        )
    ):
        analysed_category = (
            "Driver or conductor behaviour"
        )

    elif any(
        keyword in normalized
        for keyword in (
            "crowd",
            "overcrowded",
            "packed",
        )
    ):
        analysed_category = "Overcrowding"

    elif any(
        keyword in normalized
        for keyword in (
            "dirty",
            "unclean",
            "cleanliness",
        )
    ):
        analysed_category = "Cleanliness"

    elif any(
        keyword in normalized
        for keyword in (
            "lost",
            "missing item",
            "forgot",
        )
    ):
        analysed_category = "Lost item"

    elif any(
        keyword in normalized
        for keyword in (
            "ticket",
            "fare",
            "charged",
            "payment",
        )
    ):
        analysed_category = "Ticket issue"

    elif escalated:
        analysed_category = "Safety concern"

    return {
        "category": analysed_category,
        "priority": analysed_priority,
        "sentiment": _simple_sentiment(
            description
        ),
        "escalated": escalated,
    }


def _complaint_to_output(
    complaint: Dict[str, Any],
) -> ComplaintOut:
    """Convert an in-memory complaint into the response model."""

    return ComplaintOut(
        id=complaint["id"],
        user_id=complaint["user_id"],
        category=complaint["category"],
        description=complaint["description"],
        status=complaint["status"],
        sentiment=complaint.get(
            "sentiment"
        ),
        created_at=complaint["created_at"],
    )


@router.post(
    "",
    response_model=ComplaintOut,
)
async def create_complaint(
    body: ComplaintCreate,
):
    """
    Create a complaint without requiring login in demo mode.
    """

    description = body.description.strip()

    if not description:
        raise HTTPException(
            status_code=400,
            detail=(
                "Complaint description cannot be empty"
            ),
        )

    if len(description) < 10:
        raise HTTPException(
            status_code=400,
            detail=(
                "Please provide a more detailed complaint description"
            ),
        )

    analysis = _analyse_complaint(
        category=body.category,
        priority=body.priority,
        description=description,
    )

    complaint = {
        "id": str(
            uuid4()
        ),
        "user_id": "user-passenger-demo",
        "booking_id": body.booking_id,
        "category": analysis["category"],
        "description": description,
        "priority": analysis["priority"],
        "status": (
            "escalated"
            if analysis["escalated"]
            else "open"
        ),
        "sentiment": analysis["sentiment"],
        "escalated": analysis["escalated"],
        "ai_category": analysis["category"],
        "ai_priority": analysis["priority"],
        "ai_used": False,
        "created_at": datetime.now().replace(
            microsecond=0
        ).isoformat(),
    }

    demo_data.DEMO_COMPLAINTS.append(
        complaint
    )

    return _complaint_to_output(
        complaint
    )


@router.get(
    "/mine",
    response_model=List[ComplaintOut],
)
async def my_complaints():
    """
    Return complaints created by the demo passenger.
    """

    complaints = [
        complaint
        for complaint in demo_data.DEMO_COMPLAINTS
        if complaint.get(
            "user_id"
        )
        == "user-passenger-demo"
    ]

    complaints.sort(
        key=lambda complaint: complaint.get(
            "created_at",
            "",
        ),
        reverse=True,
    )

    return [
        _complaint_to_output(
            complaint
        )
        for complaint in complaints
    ]