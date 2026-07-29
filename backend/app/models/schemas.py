"""Pydantic schemas for BusMate API."""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    PASSENGER = "passenger"
    ADMIN = "admin"


class Intent(str, Enum):
    BOOKING = "Booking"
    TICKET = "Ticket"
    JOURNEY = "Journey"
    TRACKING = "Tracking"
    POLICY = "Policy"
    COMPLAINT = "Complaint"
    FEEDBACK = "Feedback"
    GREETING = "Greeting"
    OUT_OF_SCOPE = "Out-of-Scope"


class PaymentMethod(str, Enum):
    UPI = "upi"
    CARD = "card"
    WALLET = "wallet"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class SeatGender(str, Enum):
    ANY = "any"
    MALE = "male"
    FEMALE = "female"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.PASSENGER


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None


# ---------------------------------------------------------------------------
# Bus search and seats
# ---------------------------------------------------------------------------


class BusSearchRequest(BaseModel):
    origin: str
    destination: str
    travel_date: date
    passengers: int = Field(
        default=1,
        ge=1,
        le=6,
    )


class SeatInfo(BaseModel):
    seat_number: str
    is_available: bool
    gender_preference: SeatGender = SeatGender.ANY
    price: float


class BusTripOut(BaseModel):
    id: str
    route_number: str
    bus_number: str
    operator: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    fare: float
    available_seats: int

    amenities: List[str] = Field(
        default_factory=list
    )

    bus_type: str = "MTC Local Bus"

    stops: List[str] = Field(
        default_factory=list
    )

    quality_score: Optional[int] = None
    quality_label: Optional[str] = None

    quality_reasons: List[str] = Field(
        default_factory=list
    )

    quality_disclaimer: Optional[str] = None


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------


class BookingCreate(BaseModel):
    trip_id: str
    seat_numbers: List[str]
    passenger_names: List[str]
    passenger_ages: List[int]
    payment_method: PaymentMethod
    contact_phone: str
    contact_email: EmailStr


class BookingOut(BaseModel):
    id: str
    trip_id: str
    user_id: str

    pnr: str
    status: BookingStatus

    seats: List[str] = Field(
        default_factory=list
    )

    passenger_names: List[str] = Field(
        default_factory=list
    )

    passenger_ages: List[int] = Field(
        default_factory=list
    )

    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None

    total_fare: float

    payment_method: PaymentMethod
    payment_ref: Optional[str] = None

    route_number: Optional[str] = None
    bus_number: Optional[str] = None
    operator: Optional[str] = "MTC Chennai"
    bus_type: Optional[str] = "MTC Local Bus"

    origin: Optional[str] = None
    destination: Optional[str] = None

    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None

    duration_minutes: Optional[int] = None

    created_at: datetime


class PaymentSimulateRequest(BaseModel):
    booking_id: str
    method: PaymentMethod
    upi_id: Optional[str] = None
    card_last4: Optional[str] = None


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------


class TicketOut(BaseModel):
    id: str
    booking_id: str
    pnr: str

    qr_payload: str

    passenger_name: str
    passenger_age: Optional[int] = None

    seat: str

    route_number: Optional[str] = None
    bus_number: str

    origin: str
    destination: str

    departure: datetime
    arrival: Optional[datetime] = None

    total_fare: Optional[float] = None

    status: str


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------


class TrackingPoint(BaseModel):
    lat: float
    lng: float
    timestamp: datetime
    speed_kmh: Optional[float] = None


class JourneyTrackingOut(BaseModel):
    booking_id: str
    bus_number: str
    current: TrackingPoint
    eta_minutes: int
    progress_percent: float
    next_stop: Optional[str] = None
    timeline: List[Dict[str, Any]] = Field(
        default_factory=list
    )


# ---------------------------------------------------------------------------
# Complaints and feedback
# ---------------------------------------------------------------------------


class ComplaintCreate(BaseModel):
    booking_id: Optional[str] = None
    category: str
    description: str
    priority: str = "medium"


class ComplaintOut(BaseModel):
    id: str
    user_id: str
    category: str
    description: str
    status: str
    sentiment: Optional[str] = None
    created_at: datetime


class FeedbackCreate(BaseModel):
    booking_id: Optional[str] = None
    rating: int = Field(
        ge=1,
        le=5,
    )
    comment: Optional[str] = None


# ---------------------------------------------------------------------------
# AI agents
# ---------------------------------------------------------------------------


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AgentChatResponse(BaseModel):
    intent: Intent
    reply: str
    agent: str
    data: Optional[Dict[str, Any]] = None
    escalated: bool = False
    ai_used: bool = False
    session_id: str


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class AdminStats(BaseModel):
    total_bookings: int
    active_trips: int
    open_complaints: int
    revenue_today: float
    occupancy_rate: float