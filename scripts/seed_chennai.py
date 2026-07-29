#!/usr/bin/env python3
"""Seed Chennai-region demo data into Supabase (or print SQL if offline)."""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def build_trips():
    base = datetime.utcnow()
    return [
        {
            "bus_number": "TN-01-AB-1234",
            "operator": "SETC",
            "origin": "Chennai",
            "destination": "Madurai",
            "departure_time": (base + timedelta(hours=4)).isoformat(),
            "arrival_time": (base + timedelta(hours=12)).isoformat(),
            "duration_minutes": 480,
            "fare": 650.0,
            "available_seats": 28,
            "amenities": ["AC", "Water", "Charging", "WiFi"],
            "bus_type": "AC Seater",
        },
        {
            "bus_number": "TN-02-CD-5678",
            "operator": "KPN Travels",
            "origin": "Chennai",
            "destination": "Coimbatore",
            "departure_time": (base + timedelta(hours=6)).isoformat(),
            "arrival_time": (base + timedelta(hours=14)).isoformat(),
            "duration_minutes": 480,
            "fare": 720.0,
            "available_seats": 18,
            "amenities": ["AC", "Sleeper", "Blanket", "Charging"],
            "bus_type": "AC Sleeper",
        },
        {
            "bus_number": "TN-03-EF-9012",
            "operator": "SRS Travels",
            "origin": "Chennai",
            "destination": "Trichy",
            "departure_time": (base + timedelta(hours=3)).isoformat(),
            "arrival_time": (base + timedelta(hours=9)).isoformat(),
            "duration_minutes": 360,
            "fare": 480.0,
            "available_seats": 22,
            "amenities": ["Non-AC", "Water"],
            "bus_type": "Non-AC Seater",
        },
    ]


def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    trips = build_trips()

    if not url or not key:
        print("SUPABASE_URL / SERVICE_ROLE_KEY not set – printing seed payload only.")
        print(json.dumps(trips, indent=2))
        print("\nIn-memory demo data is always available via backend DEMO_MODE=true.")
        return

    try:
        from supabase import create_client

        sb = create_client(url, key)
        for t in trips:
            sb.table("trips").upsert(t, on_conflict="bus_number").execute()
        print(f"Seeded {len(trips)} trips into Supabase.")
    except Exception as e:
        print(f"Seed failed (non-blocking): {e}")
        print(json.dumps(trips, indent=2))


if __name__ == "__main__":
    main()
