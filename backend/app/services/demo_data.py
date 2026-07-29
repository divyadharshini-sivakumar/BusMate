"""Official Chennai MTC route data service for BusMate."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
ROUTES_FILE = DATA_DIR / "mtc_routes.json"


# ---------------------------------------------------------------------------
# Route-data loading
# ---------------------------------------------------------------------------

def _load_mtc_routes() -> List[Dict[str, Any]]:
    """Load imported Chennai MTC route data."""

    if not ROUTES_FILE.exists():
        raise RuntimeError(
            f"MTC route file not found: {ROUTES_FILE}. "
            "Run python scripts/import_mtc_routes.py first."
        )

    with ROUTES_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    routes = payload.get("routes", [])

    if not isinstance(routes, list):
        raise RuntimeError(
            "Invalid mtc_routes.json format: "
            "'routes' must be a list."
        )

    valid_routes: List[Dict[str, Any]] = []

    for route in routes:
        if not isinstance(route, dict):
            continue

        stops = route.get("stops", [])

        if not isinstance(stops, list):
            continue

        cleaned_stops = [
            str(stop).strip()
            for stop in stops
            if str(stop).strip()
        ]

        if len(cleaned_stops) < 2:
            continue

        valid_routes.append(
            {
                **route,
                "stops": cleaned_stops,
            }
        )

    return valid_routes


MTC_ROUTES: List[Dict[str, Any]] = _load_mtc_routes()


# ---------------------------------------------------------------------------
# In-memory demo storage
# ---------------------------------------------------------------------------

DEMO_BOOKINGS: Dict[str, Dict[str, Any]] = {}
DEMO_SESSIONS: Dict[str, List[Dict[str, Any]]] = {}
DEMO_COMPLAINTS: List[Dict[str, Any]] = []
DEMO_FEEDBACK: List[Dict[str, Any]] = []
DEMO_OTP: Dict[str, str] = {}

# Search-generated trips are cached for seat booking,
# ticket generation, PDF generation and tracking.
DEMO_TRIPS: Dict[str, Dict[str, Any]] = {}


DEMO_USERS: Dict[str, Dict[str, Any]] = {
    "user-passenger-demo": {
        "id": "user-passenger-demo",
        "email": "passenger@demo.busmate",
        "full_name": "Demo Passenger",
        "role": "passenger",
        "phone": "+919876543210",
    },
    "user-admin-demo": {
        "id": "user-admin-demo",
        "email": "admin@demo.busmate",
        "full_name": "Demo Admin",
        "role": "admin",
        "phone": "+919876543211",
    },
}


# ---------------------------------------------------------------------------
# Universal stop-name matching
# ---------------------------------------------------------------------------

def _normalize(value: str) -> str:
    """
    Normalize all stop names consistently.

    Handles:
    - uppercase and lowercase differences
    - dots
    - commas
    - hyphens
    - brackets
    - apostrophes
    - repeated spaces
    - compact abbreviations

    Examples:
        SIRUSERI I.T.PARK
        SIRUSERI I.T PARK
        Siruseri IT Park

    All normalize to:
        siruseri it park
    """

    text = str(value).casefold().strip()

    # Convert punctuation into spaces.
    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    words = text.split()

    if not words:
        return ""

    # Combine consecutive one-letter abbreviation tokens.
    #
    # Examples:
    # M G R KOYAMBEDU -> MGR KOYAMBEDU
    # I T PARK        -> IT PARK
    combined_words: List[str] = []
    abbreviation_buffer: List[str] = []

    for word in words:
        if len(word) == 1 and word.isalpha():
            abbreviation_buffer.append(word)
            continue

        if abbreviation_buffer:
            combined_words.append(
                "".join(abbreviation_buffer)
            )
            abbreviation_buffer = []

        combined_words.append(word)

    if abbreviation_buffer:
        combined_words.append(
            "".join(abbreviation_buffer)
        )

    return " ".join(combined_words)


def _stop_tokens(value: str) -> List[str]:
    """Return normalized stop-name tokens."""

    normalized = _normalize(value)

    if not normalized:
        return []

    return normalized.split()


def _stop_match_score(
    dataset_stop: str,
    searched_stop: str,
) -> int:
    """
    Score how closely a dataset stop matches a selected stop.

    Higher score means a better match.

    Rules:
    100 – exact normalized match
     95 – one side contains only an added short official prefix
     90 – same words with abbreviation formatting differences
      0 – unrelated stop

    This avoids blindly matching unrelated places.
    """

    dataset_normalized = _normalize(
        dataset_stop
    )

    searched_normalized = _normalize(
        searched_stop
    )

    if (
        not dataset_normalized
        or not searched_normalized
    ):
        return 0

    # Exact normalized match.
    if dataset_normalized == searched_normalized:
        return 100

    dataset_tokens = dataset_normalized.split()
    searched_tokens = searched_normalized.split()

    if not dataset_tokens or not searched_tokens:
        return 0

    # Example:
    # Dataset:  MGR KOYAMBEDU
    # Selected: KOYAMBEDU
    #
    # The additional prefix must consist only of short
    # abbreviation-like tokens, not arbitrary place words.
    if len(dataset_tokens) > len(searched_tokens):
        suffix = dataset_tokens[
            -len(searched_tokens):
        ]

        prefix = dataset_tokens[
            :-len(searched_tokens)
        ]

        if suffix == searched_tokens and all(
            len(token) <= 4
            for token in prefix
        ):
            return 95

    # Reverse variation:
    # Dataset may omit a short official prefix that appears
    # in the selected dropdown value.
    if len(searched_tokens) > len(dataset_tokens):
        suffix = searched_tokens[
            -len(dataset_tokens):
        ]

        prefix = searched_tokens[
            :-len(dataset_tokens)
        ]

        if suffix == dataset_tokens and all(
            len(token) <= 4
            for token in prefix
        ):
            return 94

    # Same meaningful tokens in the same order.
    if (
        len(dataset_tokens) == len(searched_tokens)
        and dataset_tokens == searched_tokens
    ):
        return 90

    return 0


def _find_stop_indexes(
    stops: List[str],
    searched_stop: str,
) -> List[int]:
    """
    Find the best stop indexes for one selected stop.

    Exact matches are preferred. Less precise matches are
    used only when no exact normalized match exists.
    """

    scored_indexes: List[tuple[int, int]] = []

    for index, stop in enumerate(stops):
        score = _stop_match_score(
            dataset_stop=stop,
            searched_stop=searched_stop,
        )

        if score > 0:
            scored_indexes.append(
                (index, score)
            )

    if not scored_indexes:
        return []

    highest_score = max(
        score
        for _, score in scored_indexes
    )

    return [
        index
        for index, score in scored_indexes
        if score == highest_score
    ]


def _same_selected_stop(
    origin: str,
    destination: str,
) -> bool:
    """Check whether both selected names represent the same stop."""

    origin_normalized = _normalize(origin)
    destination_normalized = _normalize(
        destination
    )

    if not origin_normalized or not destination_normalized:
        return True

    if origin_normalized == destination_normalized:
        return True

    return (
        _stop_match_score(
            origin,
            destination,
        )
        >= 94
        and _stop_match_score(
            destination,
            origin,
        )
        >= 94
    )


# ---------------------------------------------------------------------------
# Date and trip helpers
# ---------------------------------------------------------------------------

def _parse_travel_date(
    travel_date: str,
) -> datetime:
    """Create a base departure datetime from the selected date."""

    try:
        parsed_date = datetime.strptime(
            travel_date,
            "%Y-%m-%d",
        )

        now = datetime.now()

        return parsed_date.replace(
            hour=now.hour,
            minute=now.minute,
            second=0,
            microsecond=0,
        )

    except (TypeError, ValueError):
        return datetime.now().replace(
            second=0,
            microsecond=0,
        )


def _safe_route_id(
    route_number: str,
) -> str:
    """Create a URL-safe route-number segment."""

    cleaned = re.sub(
        r"[^A-Za-z0-9]+",
        "-",
        route_number.strip(),
    ).strip("-")

    return cleaned or "MTC"


def _stable_bus_number(
    trip_id: str,
) -> str:
    """Create a stable simulated bus registration number."""

    digest = hashlib.sha256(
        trip_id.encode("utf-8")
    ).hexdigest()

    number = (
        int(digest[:8], 16)
        % 9000
        + 1000
    )

    return f"TN-01-N-{number}"

def calculate_quality_score(
    duration_minutes: int,
    segment_count: int,
    fare: float,
    available_seats: int,
    amenities: List[str],
) -> Dict[str, Any]:
    """
    Calculate a deterministic demo journey-quality score.

    This is an estimated app score based on:
    - journey duration
    - number of stops
    - fare
    - available seats
    - amenities

    It is not an official MTC service rating.
    """

    score = 100
    reasons: List[str] = []

    # Journey duration: maximum deduction of 15 points.
    if duration_minutes <= 45:
        reasons.append("Short journey duration")
    elif duration_minutes <= 90:
        score -= 4
        reasons.append("Moderate journey duration")
    elif duration_minutes <= 150:
        score -= 9
        reasons.append("Longer journey duration")
    else:
        score -= 15
        reasons.append("Extended journey duration")

    # Number of route segments: maximum deduction of 12 points.
    if segment_count <= 6:
        reasons.append("Few intermediate stops")
    elif segment_count <= 12:
        score -= 3
        reasons.append("Moderate number of stops")
    elif segment_count <= 20:
        score -= 7
        reasons.append("Several intermediate stops")
    else:
        score -= 12
        reasons.append("Many intermediate stops")

    # Fare affordability: maximum deduction of 8 points.
    if fare <= 15:
        reasons.append("Highly affordable fare")
    elif fare <= 30:
        score -= 2
        reasons.append("Affordable fare")
    elif fare <= 40:
        score -= 5
        reasons.append("Moderate fare")
    else:
        score -= 8
        reasons.append("Higher route fare")

    # Seat availability: maximum deduction of 10 points.
    if available_seats >= 25:
        reasons.append("Good seat availability")
    elif available_seats >= 15:
        score -= 3
        reasons.append("Moderate seat availability")
    elif available_seats >= 5:
        score -= 7
        reasons.append("Limited seat availability")
    else:
        score -= 10
        reasons.append("Very limited seat availability")

    # Amenities: maximum deduction of 5 points.
    amenity_count = len(amenities)

    if amenity_count >= 3:
        reasons.append("Useful passenger features")
    elif amenity_count == 2:
        score -= 2
    elif amenity_count == 1:
        score -= 3
    else:
        score -= 5

    # Keep scores within a realistic display range.
    score = max(60, min(98, int(score)))

    if score >= 90:
        label = "Excellent"
    elif score >= 80:
        label = "Very Good"
    elif score >= 70:
        label = "Good"
    else:
        label = "Average"

    return {
        "score": score,
        "label": label,
        "reasons": reasons[:4],
        "disclaimer": (
            "Estimated by BusMate from journey details; "
            "not an official MTC service rating."
        ),
    }

def _create_trip_from_route(
    route: Dict[str, Any],
    route_index: int,
    origin_index: int,
    destination_index: int,
    result_index: int,
    travel_date: str = "",
    selected_origin: Optional[str] = None,
    selected_destination: Optional[str] = None,
) -> Dict[str, Any]:
    """Create one searchable and bookable MTC journey."""

    stops = route.get("stops", [])

    if not isinstance(stops, list):
        raise ValueError("Route stops must be a list.")

    if (
        origin_index < 0
        or destination_index < 0
        or origin_index >= len(stops)
        or destination_index >= len(stops)
        or origin_index == destination_index
    ):
        raise ValueError("Invalid route segment indexes.")

    # Forward journey.
    if destination_index > origin_index:
        selected_stops = [
            str(stop)
            for stop in stops[
                origin_index : destination_index + 1
            ]
        ]

    # Reverse journey.
    else:
        selected_stops = [
            str(stop)
            for stop in reversed(
                stops[
                    destination_index : origin_index + 1
                ]
            )
        ]

    segment_count = max(
        abs(destination_index - origin_index),
        1,
    )

    duration_minutes = max(
        10,
        segment_count * 7,
    )

    fare = max(
        5.0,
        min(
            50.0,
            round(
                (5 + segment_count * 2.5) / 5
            )
            * 5,
        ),
    )

    base_datetime = _parse_travel_date(
        travel_date
    )

    departure_time = base_datetime + timedelta(
        minutes=15 + result_index * 12
    )

    arrival_time = departure_time + timedelta(
        minutes=duration_minutes
    )

    route_number = str(
        route.get(
            "route_number",
            "MTC",
        )
    ).strip()

    route_id = _safe_route_id(
        route_number
    )

    trip_id = (
        f"mtc-{route_id}-"
        f"{route_index}-"
        f"{origin_index}-"
        f"{destination_index}"
    )

    actual_origin = str(
        stops[origin_index]
    )

    actual_destination = str(
        stops[destination_index]
    )

    display_origin = (
        selected_origin.strip().upper()
        if selected_origin
        else actual_origin
    )

    display_destination = (
        selected_destination.strip().upper()
        if selected_destination
        else actual_destination
    )

    available_seats = 34

    amenities = [
        "Official MTC Route",
        "Digital Ticket",
        "Simulated GPS",
    ]

    quality = calculate_quality_score(
        duration_minutes=duration_minutes,
        segment_count=segment_count,
        fare=float(fare),
        available_seats=available_seats,
        amenities=amenities,
    )

    trip: Dict[str, Any] = {
        "id": trip_id,
        "route_number": route_number,
        "bus_number": _stable_bus_number(
            trip_id
        ),
        "operator": "MTC Chennai",
        "origin": display_origin,
        "destination": display_destination,
        "actual_origin_stop": actual_origin,
        "actual_destination_stop": actual_destination,
        "departure_time": departure_time.isoformat(),
        "arrival_time": arrival_time.isoformat(),
        "duration_minutes": duration_minutes,
        "fare": fare,
        "available_seats": available_seats,
        "amenities": amenities,
        "bus_type": "MTC Local Bus",
        "stops": selected_stops,
        "full_route_stops": [
            str(stop)
            for stop in stops
        ],
        "travel_date": (
            departure_time.date().isoformat()
        ),
        "route_index": route_index,
        "origin_index": origin_index,
        "destination_index": destination_index,
        "direction": (
            "forward"
            if destination_index > origin_index
            else "reverse"
        ),

        # BusMate estimated journey quality.
        "quality_score": quality["score"],
        "quality_label": quality["label"],
        "quality_reasons": quality["reasons"],
        "quality_disclaimer": quality["disclaimer"],

        "source": route.get(
            "source",
            (
                "Metropolitan Transport "
                "Corporation Chennai"
            ),
        ),
        "source_url": route.get(
            "source_url",
            "https://mtcbus.tn.gov.in/",
        ),
    }

    DEMO_TRIPS[trip_id] = trip

    return trip

def search_trips(
    origin: str,
    destination: str,
    travel_date: str = "",
) -> List[Dict[str, Any]]:
    """
    Search direct MTC routes in both forward and reverse directions.
    """

    origin_text = str(origin).strip()
    destination_text = str(destination).strip()

    if not origin_text or not destination_text:
        return []

    if _same_selected_stop(
        origin_text,
        destination_text,
    ):
        return []

    matching_trips: List[Dict[str, Any]] = []

    for route_index, route in enumerate(MTC_ROUTES):
        stops = route.get("stops", [])

        if not isinstance(stops, list):
            continue

        route_stops = [
            str(stop).strip()
            for stop in stops
            if str(stop).strip()
        ]

        origin_indexes = _find_stop_indexes(
            stops=route_stops,
            searched_stop=origin_text,
        )

        destination_indexes = _find_stop_indexes(
            stops=route_stops,
            searched_stop=destination_text,
        )

        if not origin_indexes or not destination_indexes:
            continue

        # Both directions are valid.
        possible_pairs = [
            (origin_index, destination_index)
            for origin_index in origin_indexes
            for destination_index in destination_indexes
            if origin_index != destination_index
        ]

        if not possible_pairs:
            continue

        # Choose the shortest matching segment.
        origin_index, destination_index = min(
            possible_pairs,
            key=lambda pair: (
                abs(pair[1] - pair[0]),
                pair[0],
            ),
        )

        try:
            trip = _create_trip_from_route(
                route=route,
                route_index=route_index,
                origin_index=origin_index,
                destination_index=destination_index,
                result_index=len(matching_trips),
                travel_date=travel_date,
                selected_origin=origin_text,
                selected_destination=destination_text,
            )

            matching_trips.append(trip)

        except ValueError:
            continue

    matching_trips.sort(
        key=lambda trip: (
            trip["duration_minutes"],
            float(trip["fare"]),
            str(trip["route_number"]),
        )
    )

    # Recalculate departure times after sorting.
    base_datetime = _parse_travel_date(travel_date)

    for result_index, trip in enumerate(matching_trips):
        departure_time = base_datetime + timedelta(
            minutes=15 + result_index * 12
        )

        arrival_time = departure_time + timedelta(
            minutes=trip["duration_minutes"]
        )

        trip["departure_time"] = departure_time.isoformat()
        trip["arrival_time"] = arrival_time.isoformat()

        DEMO_TRIPS[trip["id"]] = trip

    return matching_trips[:50]

# ---------------------------------------------------------------------------
# Trip lookup
# ---------------------------------------------------------------------------

def _rebuild_trip_from_id(
    trip_id: str,
) -> Optional[Dict[str, Any]]:
    """Rebuild a generated trip after an application restart."""

    match = re.fullmatch(
        r"mtc-(.+)-(\d+)-(\d+)-(\d+)",
        trip_id,
    )

    if not match:
        return None

    route_index = int(
        match.group(2)
    )

    origin_index = int(
        match.group(3)
    )

    destination_index = int(
        match.group(4)
    )

    if (
        route_index < 0
        or route_index >= len(MTC_ROUTES)
    ):
        return None

    route = MTC_ROUTES[
        route_index
    ]

    stops = route.get(
        "stops",
        [],
    )

    if not isinstance(stops, list):
        return None

    if (
        origin_index < 0
        or destination_index >= len(stops)
        or destination_index <= origin_index
    ):
        return None

    try:
        return _create_trip_from_route(
            route=route,
            route_index=route_index,
            origin_index=origin_index,
            destination_index=destination_index,
            result_index=0,
        )

    except ValueError:
        return None


def get_trip(
    trip_id: str,
) -> Optional[Dict[str, Any]]:
    """Return a cached trip or rebuild it from its identifier."""

    cached_trip = DEMO_TRIPS.get(
        trip_id
    )

    if cached_trip:
        return cached_trip

    return _rebuild_trip_from_id(
        trip_id
    )


def get_route_stops(
    route_number: str,
) -> List[Dict[str, Any]]:
    """Return imported records for one route number."""

    query = _normalize(
        route_number
    )

    return [
        route
        for route in MTC_ROUTES
        if _normalize(
            str(
                route.get(
                    "route_number",
                    "",
                )
            )
        )
        == query
    ]


def get_all_stops() -> List[str]:
    """Return every unique imported MTC stop."""

    stops = {
        str(stop).strip()
        for route in MTC_ROUTES
        for stop in route.get(
            "stops",
            [],
        )
        if str(stop).strip()
    }

    return sorted(
        stops,
        key=lambda value: (
            _normalize(value),
            value.casefold(),
        ),
    )


# ---------------------------------------------------------------------------
# Booking storage
# ---------------------------------------------------------------------------

def create_booking(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Create and store a complete demo booking."""

    booking_id = str(
        uuid4()
    )

    pnr = (
        f"BM{booking_id[:8].upper()}"
    )

    created_at = datetime.now().replace(
        microsecond=0
    )

    booking: Dict[str, Any] = {
        "id": booking_id,
        "pnr": pnr,
        "status": "confirmed",
        "payment_ref": (
            f"PAY-{uuid4().hex[:10].upper()}"
        ),
        "created_at": (
            created_at.isoformat()
        ),
        "operator": "MTC Chennai",
        "bus_type": "MTC Local Bus",
        **payload,
    }

    booking.setdefault(
        "passenger_names",
        [],
    )

    booking.setdefault(
        "passenger_ages",
        [],
    )

    booking.setdefault(
        "seats",
        [],
    )

    booking.setdefault(
        "contact_phone",
        None,
    )

    booking.setdefault(
        "contact_email",
        None,
    )

    booking.setdefault(
        "route_number",
        None,
    )

    booking.setdefault(
        "bus_number",
        None,
    )

    booking.setdefault(
        "origin",
        None,
    )

    booking.setdefault(
        "destination",
        None,
    )

    booking.setdefault(
        "departure_time",
        None,
    )

    booking.setdefault(
        "arrival_time",
        None,
    )

    booking.setdefault(
        "duration_minutes",
        None,
    )

    booking.setdefault(
        "stops",
        [],
    )

    booking.setdefault(
        "full_route_stops",
        [],
    )

    DEMO_BOOKINGS[
        booking_id
    ] = booking

    return booking


def get_booking(
    booking_id: str,
) -> Optional[Dict[str, Any]]:
    """Return one stored booking."""

    return DEMO_BOOKINGS.get(
        booking_id
    )


def list_user_bookings(
    user_id: str,
) -> List[Dict[str, Any]]:
    """Return one passenger's bookings, newest first."""

    bookings = [
        booking
        for booking in DEMO_BOOKINGS.values()
        if booking.get(
            "user_id"
        )
        == user_id
    ]

    return sorted(
        bookings,
        key=lambda booking: booking.get(
            "created_at",
            "",
        ),
        reverse=True,
    )