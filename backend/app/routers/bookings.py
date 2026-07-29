"""Bus search, official stop list, booking, and simulated payment routes."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    BookingCreate,
    BookingOut,
    BookingStatus,
    BusSearchRequest,
    BusTripOut,
    PaymentMethod,
    PaymentSimulateRequest,
    SeatInfo,
)
from app.services import demo_data


router = APIRouter()


def generate_trip_seats(
    trip: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate a simulated 40-seat MTC bus layout."""

    fare = float(
        trip.get(
            "fare",
            10,
        )
    )

    seats: List[Dict[str, Any]] = []

    for index in range(1, 41):
        row = (index - 1) // 4 + 1
        column = "ABCD"[(index - 1) % 4]

        seat_number = f"{row}{column}"

        seats.append(
            {
                "seat_number": seat_number,
                "is_available": index % 6 != 0,
                "gender_preference": (
                    "female"
                    if index % 7 == 0
                    else "any"
                ),
                "price": fare,
            }
        )

    return seats


def booking_to_output(
    booking: Dict[str, Any],
) -> BookingOut:
    """Convert a stored booking into the API response model."""

    return BookingOut(
        id=booking["id"],
        trip_id=booking["trip_id"],
        user_id=booking["user_id"],
        pnr=booking["pnr"],
        status=BookingStatus(
            booking.get(
                "status",
                "confirmed",
            )
        ),
        seats=booking.get(
            "seats",
            [],
        ),
        passenger_names=booking.get(
            "passenger_names",
            [],
        ),
        passenger_ages=booking.get(
            "passenger_ages",
            [],
        ),
        contact_phone=booking.get(
            "contact_phone",
        ),
        contact_email=booking.get(
            "contact_email",
        ),
        total_fare=float(
            booking.get(
                "total_fare",
                0,
            )
        ),
        payment_method=PaymentMethod(
            booking.get(
                "payment_method",
                "upi",
            )
        ),
        payment_ref=booking.get(
            "payment_ref",
        ),
        route_number=booking.get(
            "route_number",
        ),
        bus_number=booking.get(
            "bus_number",
        ),
        operator=booking.get(
            "operator",
            "MTC Chennai",
        ),
        bus_type=booking.get(
            "bus_type",
            "MTC Local Bus",
        ),
        origin=booking.get(
            "origin",
        ),
        destination=booking.get(
            "destination",
        ),
        departure_time=booking.get(
            "departure_time",
        ),
        arrival_time=booking.get(
            "arrival_time",
        ),
        duration_minutes=booking.get(
            "duration_minutes",
        ),
        created_at=booking["created_at"],
    )


@router.get(
    "/stops",
    response_model=List[str],
)
async def get_stops():
    """
    Return all imported Chennai MTC stop names.

    Login is not required.
    """

    return demo_data.get_all_stops()


@router.post(
    "/search",
    response_model=List[BusTripOut],
)
async def search_buses(
    body: BusSearchRequest,
):
    """
    Search imported Chennai MTC routes.

    Login is not required.
    """

    trips = demo_data.search_trips(
        body.origin,
        body.destination,
        body.travel_date.isoformat(),
    )

    return [
        BusTripOut(
            id=trip["id"],
            route_number=trip["route_number"],
            bus_number=trip["bus_number"],
            operator=trip["operator"],
            origin=trip["origin"],
            destination=trip["destination"],
            departure_time=trip["departure_time"],
            arrival_time=trip["arrival_time"],
            duration_minutes=trip["duration_minutes"],
            fare=trip["fare"],
            available_seats=trip["available_seats"],
            amenities=trip.get(
                "amenities",
                [],
            ),
            bus_type=trip.get(
                "bus_type",
                "MTC Local Bus",
            ),
            stops=trip.get(
                "stops",
                [],
            ),
            quality_score=trip.get(
                "quality_score",
            ),
            quality_label=trip.get(
                "quality_label",
            ),
            quality_reasons=trip.get(
                "quality_reasons",
                [],
            ),
            quality_disclaimer=trip.get(
                "quality_disclaimer",
            ),
        )
        for trip in trips
    ]


@router.get(
    "/trips/{trip_id}/seats",
    response_model=List[SeatInfo],
)
async def get_seats(
    trip_id: str,
):
    """
    Return the simulated seat map for a selected trip.

    Login is not required.
    """

    trip = demo_data.get_trip(
        trip_id
    )

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    seats = generate_trip_seats(
        trip
    )

    return [
        SeatInfo(
            **seat
        )
        for seat in seats
    ]


@router.post(
    "",
    response_model=BookingOut,
)
async def create_booking(
    body: BookingCreate,
):
    """
    Create a simulated booking.

    Login is not required in the current demo version.
    """

    trip = demo_data.get_trip(
        body.trip_id
    )

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    if not body.seat_numbers:
        raise HTTPException(
            status_code=400,
            detail="Select at least one seat",
        )

    if len(body.passenger_names) != len(
        body.seat_numbers
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Each selected seat must have one "
                "passenger name"
            ),
        )

    if len(body.passenger_ages) != len(
        body.seat_numbers
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Each selected seat must have one "
                "passenger age"
            ),
        )

    if len(set(body.seat_numbers)) != len(
        body.seat_numbers
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "The same seat cannot be selected "
                "more than once"
            ),
        )

    generated_seats = generate_trip_seats(
        trip
    )

    available_seats = {
        seat["seat_number"]
        for seat in generated_seats
        if seat["is_available"]
    }

    for seat_number in body.seat_numbers:
        if seat_number not in available_seats:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Seat {seat_number} is not available"
                ),
            )

    for passenger_name in body.passenger_names:
        if not passenger_name.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Passenger name cannot be empty"
                ),
            )

    for age in body.passenger_ages:
        if age < 1 or age > 120:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Passenger age must be between "
                    "1 and 120"
                ),
            )

    total_fare = (
        float(
            trip["fare"]
        )
        * len(
            body.seat_numbers
        )
    )

    demo_user = demo_data.DEMO_USERS[
        "user-passenger-demo"
    ]

    booking = demo_data.create_booking(
        {
            "trip_id": body.trip_id,
            "user_id": demo_user["id"],
            "seats": body.seat_numbers,
            "passenger_names": body.passenger_names,
            "passenger_ages": body.passenger_ages,
            "payment_method": (
                body.payment_method.value
            ),
            "contact_phone": (
                body.contact_phone
            ),
            "contact_email": str(
                body.contact_email
            ),
            "total_fare": total_fare,
            "route_number": trip.get(
                "route_number",
            ),
            "bus_number": trip.get(
                "bus_number",
            ),
            "operator": trip.get(
                "operator",
                "MTC Chennai",
            ),
            "bus_type": trip.get(
                "bus_type",
                "MTC Local Bus",
            ),
            "origin": trip.get(
                "origin",
            ),
            "destination": trip.get(
                "destination",
            ),
            "departure_time": trip.get(
                "departure_time",
            ),
            "arrival_time": trip.get(
                "arrival_time",
            ),
            "duration_minutes": trip.get(
                "duration_minutes",
            ),
            "stops": trip.get(
                "stops",
                [],
            ),
            "full_route_stops": trip.get(
                "full_route_stops",
                [],
            ),
        }
    )

    return booking_to_output(
        booking
    )


@router.post(
    "/pay",
    response_model=BookingOut,
)
async def simulate_payment(
    body: PaymentSimulateRequest,
):
    """
    Simulate payment for an existing booking.

    Login is not required in the demo version.
    """

    booking = demo_data.get_booking(
        body.booking_id
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    booking["status"] = "confirmed"

    booking["payment_method"] = (
        body.method.value
    )

    return booking_to_output(
        booking
    )


@router.get(
    "/mine",
    response_model=List[BookingOut],
)
async def my_bookings():
    """
    Return bookings created by the demo passenger.

    Login is not required in the demo version.
    """

    demo_user_id = (
        "user-passenger-demo"
    )

    bookings = (
        demo_data.list_user_bookings(
            demo_user_id
        )
    )

    return [
        booking_to_output(
            booking
        )
        for booking in bookings
    ]