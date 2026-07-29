"""Feedback collection for BusMate demo mode."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.models.schemas import FeedbackCreate
from app.services import demo_data

router = APIRouter()


def _feedback_sentiment(
    rating: int,
    comment: str | None,
) -> str:
    """Estimate feedback sentiment using rating and keywords."""

    text = (comment or "").casefold()

    negative_words = (
        "bad",
        "poor",
        "worst",
        "late",
        "delay",
        "dirty",
        "rude",
        "unsafe",
        "problem",
        "difficult",
        "slow",
    )

    positive_words = (
        "good",
        "great",
        "excellent",
        "clean",
        "helpful",
        "easy",
        "fast",
        "comfortable",
        "polite",
        "smooth",
    )

    negative_score = sum(
        1
        for word in negative_words
        if word in text
    )

    positive_score = sum(
        1
        for word in positive_words
        if word in text
    )

    if rating <= 2:
        return "negative"

    if rating >= 4:
        return "positive"

    if negative_score > positive_score:
        return "negative"

    if positive_score > negative_score:
        return "positive"

    return "neutral"


def _feedback_summary(
    rating: int,
    comment: str | None,
) -> str:
    """Create a compact feedback summary."""

    if rating == 5:
        rating_label = "Excellent experience"
    elif rating == 4:
        rating_label = "Very good experience"
    elif rating == 3:
        rating_label = "Average experience"
    elif rating == 2:
        rating_label = "Needs improvement"
    else:
        rating_label = "Poor experience"

    if comment and comment.strip():
        return f"{rating_label}: {comment.strip()}"

    return rating_label


def _feedback_values() -> List[Dict[str, Any]]:
    """Return demo feedback entries newest first."""

    return sorted(
        demo_data.DEMO_FEEDBACK,
        key=lambda item: str(
            item.get(
                "created_at",
                "",
            )
        ),
        reverse=True,
    )


@router.post("")
async def submit_feedback(
    body: FeedbackCreate,
):
    """
    Submit passenger feedback.

    Login is not required in the current demo version.
    """

    comment = (
        body.comment.strip()
        if body.comment
        else None
    )

    if comment and len(comment) > 1000:
        raise HTTPException(
            status_code=400,
            detail=(
                "Feedback comment cannot exceed "
                "1000 characters"
            ),
        )

    sentiment = _feedback_sentiment(
        rating=body.rating,
        comment=comment,
    )

    entry = {
        "id": str(uuid4()),
        "user_id": "user-passenger-demo",
        "booking_id": body.booking_id,
        "rating": body.rating,
        "comment": comment,
        "sentiment": sentiment,
        "summary": _feedback_summary(
            rating=body.rating,
            comment=comment,
        ),
        "created_at": datetime.now().replace(
            microsecond=0
        ).isoformat(),
    }

    demo_data.DEMO_FEEDBACK.append(
        entry
    )

    return entry


@router.get("/mine")
async def my_feedback():
    """
    Return feedback created by the demo passenger.
    """

    return [
        item
        for item in _feedback_values()
        if item.get(
            "user_id"
        )
        == "user-passenger-demo"
    ]


@router.get("/summary")
async def feedback_summary():
    """
    Return aggregate feedback metrics for the demo session.
    """

    feedback = _feedback_values()

    if not feedback:
        return {
            "total_feedback": 0,
            "average_rating": 0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
        }

    ratings = [
        int(item.get("rating", 0))
        for item in feedback
    ]

    return {
        "total_feedback": len(feedback),
        "average_rating": round(
            sum(ratings) / len(ratings),
            1,
        ),
        "positive": sum(
            1
            for item in feedback
            if item.get("sentiment")
            == "positive"
        ),
        "neutral": sum(
            1
            for item in feedback
            if item.get("sentiment")
            == "neutral"
        ),
        "negative": sum(
            1
            for item in feedback
            if item.get("sentiment")
            == "negative"
        ),
    }