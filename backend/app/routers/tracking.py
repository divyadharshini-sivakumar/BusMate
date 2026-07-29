"""Simulated Chennai MTC live tracking, ETA, timeline, and alerts."""

from __future__ import annotations

import hashlib
import math
from datetime import datetime
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    JourneyTrackingOut,
    TrackingPoint,
)
from app.services import demo_data

router = APIRouter()


# Chennai city centre. Stop coordinates are generated
# deterministically around this point for the project demo.
CHENNAI_LAT = 13.0827
CHENNAI_LNG = 80.2707


def _stop_coordinates(
    stop_name: str,
) -> Tuple[float, float]:
    """
    Generate stable demo coordinates for an MTC stop.

    The same stop name always receives the same coordinates.
    Coordinates remain inside the wider Chennai region.
    """

    digest = hashlib.sha256(
        stop_name.encode("utf-8")
    ).hexdigest()

    latitude_seed = int(
        digest[:8],
        16,
    )

    longitude_seed = int(
        digest[8:16],
        16,
    )

    latitude_offset = (
        latitude_seed % 2400
    ) / 10000 - 0.12

    longitude_offset = (
        longitude_seed % 3200
    ) / 10000 - 0.16

    return (
        CHENNAI_LAT + latitude_offset,
        CHENNAI_LNG + longitude_offset,
    )


def _interpolate(
    start: Tuple[float, float],
    end: Tuple[float, float],
    progress: float,
) -> Tuple[float, float]:
    """Interpolate a point between two coordinates."""

    safe_progress = max(
        0.0,
        min(
            1.0,
            progress,
        ),
    )

    latitude = (
        start[0]
        + (
            end[0] - start[0]
        )
        * safe_progress
    )

    longitude = (
        start[1]
        + (
            end[1] - start[1]
        )
        * safe_progress
    )

    return latitude, longitude


def _booking_progress(
    booking: Dict[str, Any],
) -> float:
    """
    Return changing demo progress for a booking.

    Progress advances continuously and loops before reaching
    the end, allowing the tracking page to visibly update.
    """

    created_at_value = booking.get(
        "created_at"
    )

    try:
        created_at = datetime.fromisoformat(
            str(created_at_value)
        )
    except (TypeError, ValueError):
        created_at = datetime.now()

    elapsed_seconds = max(
        0.0,
        (
            datetime.now() - created_at
        ).total_seconds(),
    )

    # Start at 12% and progress by about 1% every 8 seconds.
    progress = (
        0.12
        + (
            elapsed_seconds / 800
        )
    )

    return min(
        0.98,
        progress,
    )


def _route_stops(
    booking: Dict[str, Any],
) -> List[str]:
    """Return the journey stops stored with the booking."""

    stops = booking.get(
        "stops",
        [],
    )

    if isinstance(stops, list):
        cleaned_stops = [
            str(stop).strip()
            for stop in stops
            if str(stop).strip()
        ]

        if len(cleaned_stops) >= 2:
            return cleaned_stops

    origin = str(
        booking.get(
            "origin",
            "Boarding stop",
        )
    )

    destination = str(
        booking.get(
            "destination",
            "Destination",
        )
    )

    return [
        origin,
        destination,
    ]


def _position_on_route(
    stops: List[str],
    progress: float,
) -> Tuple[
    float,
    float,
    int,
    float,
]:
    """
    Calculate the current position across the route stops.

    Returns:
    - latitude
    - longitude
    - current segment index
    - progress inside the current segment
    """

    if len(stops) < 2:
        latitude, longitude = _stop_coordinates(
            stops[0]
            if stops
            else "Chennai"
        )

        return (
            latitude,
            longitude,
            0,
            0.0,
        )

    segment_count = len(stops) - 1

    route_position = (
        max(
            0.0,
            min(
                0.999,
                progress,
            ),
        )
        * segment_count
    )

    segment_index = min(
        int(route_position),
        segment_count - 1,
    )

    segment_progress = (
        route_position
        - segment_index
    )

    start_coordinates = _stop_coordinates(
        stops[segment_index]
    )

    end_coordinates = _stop_coordinates(
        stops[segment_index + 1]
    )

    latitude, longitude = _interpolate(
        start_coordinates,
        end_coordinates,
        segment_progress,
    )

    return (
        latitude,
        longitude,
        segment_index,
        segment_progress,
    )


def _speed_for_progress(
    progress: float,
) -> float:
    """Return a realistic simulated local-bus speed."""

    if progress >= 0.98:
        return 0.0

    variation = math.sin(
        progress * math.pi * 8
    )

    return round(
        max(
            18.0,
            31.0 + variation * 9,
        ),
        1,
    )


def _build_timeline(
    stops: List[str],
    progress: float,
) -> List[Dict[str, Any]]:
    """Build a route-stop timeline for the frontend."""

    total_stops = len(stops)

    current_stop_position = (
        progress
        * max(
            total_stops - 1,
            1,
        )
    )

    timeline: List[Dict[str, Any]] = []

    for index, stop in enumerate(stops):
        stop_progress = (
            index
            / max(
                total_stops - 1,
                1,
            )
        )

        done = progress >= stop_progress

        if index == 0:
            event = "Boarding stop"
        elif index == total_stops - 1:
            event = "Destination"
        else:
            event = "Route stop"

        event_time = (
            datetime.now().isoformat()
            if done
            else None
        )

        timeline.append(
            {
                "event": event,
                "location": stop,
                "time": event_time,
                "done": done,
                "sequence": index + 1,
                "current": (
                    index
                    == min(
                        int(
                            current_stop_position
                        ),
                        total_stops - 1,
                    )
                ),
            }
        )

    return timeline


def _tracking_data(
    booking_id: str,
) -> JourneyTrackingOut:
    """Create tracking information for one booking."""

    booking = demo_data.get_booking(
        booking_id
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    stops = _route_stops(
        booking
    )

    progress = _booking_progress(
        booking
    )

    (
        latitude,
        longitude,
        segment_index,
        _,
    ) = _position_on_route(
        stops,
        progress,
    )

    next_stop_index = min(
        segment_index + 1,
        len(stops) - 1,
    )

    next_stop = stops[
        next_stop_index
    ]

    duration_minutes = int(
        booking.get(
            "duration_minutes",
            max(
                10,
                (
                    len(stops) - 1
                )
                * 7,
            ),
        )
        or 10
    )

    eta_minutes = max(
        0,
        math.ceil(
            duration_minutes
            * (
                1 - progress
            )
        ),
    )

    speed = _speed_for_progress(
        progress
    )

    timeline = _build_timeline(
        stops,
        progress,
    )

    return JourneyTrackingOut(
        booking_id=booking_id,
        bus_number=str(
            booking.get(
                "bus_number",
                "MTC Bus",
            )
        ),
        current=TrackingPoint(
            lat=round(
                latitude,
                5,
            ),
            lng=round(
                longitude,
                5,
            ),
            timestamp=datetime.now(),
            speed_kmh=speed,
        ),
        eta_minutes=eta_minutes,
        progress_percent=round(
            progress * 100,
            1,
        ),
        next_stop=next_stop,
        timeline=timeline,
    )


@router.get(
    "/{booking_id}",
    response_model=JourneyTrackingOut,
)
async def track_journey(
    booking_id: str,
):
    """
    Return simulated live tracking for a booked MTC journey.

    Login is not required in the current demo version.
    """

    return _tracking_data(
        booking_id
    )


@router.get(
    "/{booking_id}/alerts"
)
async def destination_alerts(
    booking_id: str,
):
    """
    Return journey alerts based on current simulated progress.

    Login is not required in the current demo version.
    """

    tracking = _tracking_data(
        booking_id
    )

    alerts: List[
        Dict[str, Any]
    ] = []

    if tracking.progress_percent >= 90:
        alerts.append(
            {
                "type": "destination",
                "message": (
                    f"You are nearing "
                    f"{tracking.next_stop}. "
                    "Please prepare to alight."
                ),
                "priority": "high",
            }
        )

    elif tracking.progress_percent >= 65:
        alerts.append(
            {
                "type": "info",
                "message": (
                    f"The bus is approaching "
                    f"{tracking.next_stop}. "
                    f"Estimated arrival is "
                    f"{tracking.eta_minutes} minutes."
                ),
                "priority": "medium",
            }
        )

    elif tracking.progress_percent >= 40:
        alerts.append(
            {
                "type": "info",
                "message": (
                    f"Your journey is progressing "
                    f"normally. ETA is approximately "
                    f"{tracking.eta_minutes} minutes."
                ),
                "priority": "low",
            }
        )

    return {
        "booking_id": booking_id,
        "alerts": alerts,
    }