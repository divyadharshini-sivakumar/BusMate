"""Demo booking flow without external services."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services import demo_data


def test_search_chennai_madurai():
    trips = demo_data.search_trips("Chennai", "Madurai")
    assert len(trips) >= 1
    assert trips[0]["origin"] == "Chennai"


def test_create_booking_marks_seats():
    trips = demo_data.search_trips("Chennai", "Madurai")
    trip = trips[0]
    avail = [s["seat_number"] for s in trip["seats"] if s["is_available"]]
    assert avail, "need free seats"
    seat = avail[0]
    booking = demo_data.create_booking(
        {
            "trip_id": trip["id"],
            "user_id": "user-passenger-demo",
            "seats": [seat],
            "passenger_names": ["Test"],
            "passenger_ages": [25],
            "payment_method": "upi",
            "contact_phone": "+910000000000",
            "contact_email": "t@demo.busmate",
            "total_fare": trip["fare"],
        }
    )
    assert booking["pnr"].startswith("BM")
    updated = demo_data.get_trip(trip["id"])
    assert updated is not None
    seat_row = next(s for s in updated["seats"] if s["seat_number"] == seat)
    assert seat_row["is_available"] is False
