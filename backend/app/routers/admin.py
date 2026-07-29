"""Demo admin dashboard endpoints for BusMate."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from app.models.schemas import AdminStats
from app.services import demo_data

router = APIRouter()


def _booking_values() -> List[Dict[str, Any]]:
    """Return all current in-memory bookings."""

    return list(
        demo_data.DEMO_BOOKINGS.values()
    )


def _trip_values() -> List[Dict[str, Any]]:
    """Return all currently generated searchable trips."""

    trips = demo_data.DEMO_TRIPS

    if isinstance(trips, dict):
        return list(trips.values())

    if isinstance(trips, list):
        return trips

    return []


def _open_complaint_count() -> int:
    """Count complaints that are not resolved or closed."""

    return sum(
        1
        for complaint in demo_data.DEMO_COMPLAINTS
        if str(
            complaint.get(
                "status",
                "open",
            )
        ).casefold()
        not in {
            "resolved",
            "closed",
            "completed",
        }
    )


def _occupancy_rate(
    bookings: List[Dict[str, Any]],
    trips: List[Dict[str, Any]],
) -> float:
    """
    Calculate a simple demo occupancy percentage.

    Each generated trip represents a 40-seat MTC bus.
    """

    booked_seats = sum(
        len(
            booking.get(
                "seats",
                [],
            )
        )
        for booking in bookings
    )

    if trips:
        total_capacity = (
            len(trips) * 40
        )
    elif bookings:
        # Keep the metric meaningful when the backend has
        # restarted and the trip cache is empty.
        unique_trip_ids = {
            booking.get("trip_id")
            for booking in bookings
            if booking.get("trip_id")
        }

        total_capacity = max(
            len(unique_trip_ids),
            1,
        ) * 40
    else:
        total_capacity = 0

    if total_capacity <= 0:
        return 0.0

    return round(
        min(
            100.0,
            booked_seats
            / total_capacity
            * 100,
        ),
        1,
    )


@router.get(
    "/stats",
    response_model=AdminStats,
)
async def stats():
    """
    Return dashboard metrics for the current demo session.

    Login is not required in this project demo.
    """

    bookings = _booking_values()
    trips = _trip_values()

    total_revenue = sum(
        float(
            booking.get(
                "total_fare",
                0,
            )
            or 0
        )
        for booking in bookings
    )

    return AdminStats(
        total_bookings=len(bookings),
        active_trips=(
            len(trips)
            if trips
            else len(
                demo_data.MTC_ROUTES
            )
        ),
        open_complaints=(
            _open_complaint_count()
        ),
        revenue_today=round(
            total_revenue,
            2,
        ),
        occupancy_rate=_occupancy_rate(
            bookings,
            trips,
        ),
    )


@router.get(
    "/trips"
)
async def list_trips():
    """
    Return current generated trips.

    When no search has been performed after a backend restart,
    return a lightweight summary of imported MTC routes so the
    admin page still shows route availability.
    """

    trips = _trip_values()

    if trips:
        return trips

    route_summaries: List[
        Dict[str, Any]
    ] = []

    for route_index, route in enumerate(
        demo_data.MTC_ROUTES
    ):
        stops = route.get(
            "stops",
            [],
        )

        if not isinstance(
            stops,
            list,
        ):
            continue

        if len(stops) < 2:
            continue

        route_number = str(
            route.get(
                "route_number",
                "MTC",
            )
        ).strip()

        route_summaries.append(
            {
                "id": (
                    f"route-summary-"
                    f"{route_index}"
                ),
                "route_number": route_number,
                "bus_number": (
                    "Generated when searched"
                ),
                "origin": str(
                    stops[0]
                ),
                "destination": str(
                    stops[-1]
                ),
                "available_seats": 40,
                "fare": None,
                "stop_count": len(
                    stops
                ),
                "status": "available",
            }
        )

    return route_summaries


@router.get(
    "/bookings"
)
async def list_bookings():
    """
    Return all current demo bookings, newest first.
    """

    return sorted(
        _booking_values(),
        key=lambda booking: str(
            booking.get(
                "created_at",
                "",
            )
        ),
        reverse=True,
    )


@router.get(
    "/complaints"
)
async def list_complaints():
    """
    Return submitted passenger complaints, newest first.
    """

    return sorted(
        demo_data.DEMO_COMPLAINTS,
        key=lambda complaint: str(
            complaint.get(
                "created_at",
                "",
            )
        ),
        reverse=True,
    )


@router.get(
    "/feedback"
)
async def list_feedback():
    """
    Return submitted passenger feedback, newest first.
    """

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


@router.get(
    "/health"
)
async def admin_health():
    """
    Return a compact service-status summary for the dashboard.
    """

    return {
        "status": "operational",
        "route_engine": {
            "status": "operational",
            "imported_routes": len(
                demo_data.MTC_ROUTES
            ),
            "generated_trips": len(
                _trip_values()
            ),
        },
        "booking_store": {
            "status": "operational",
            "bookings": len(
                _booking_values()
            ),
        },
        "complaints": {
            "status": "operational",
            "count": len(
                demo_data.DEMO_COMPLAINTS
            ),
        },
        "feedback": {
            "status": "operational",
            "count": len(
                demo_data.DEMO_FEEDBACK
            ),
        },
        "storage": "in-memory demo storage",
    }