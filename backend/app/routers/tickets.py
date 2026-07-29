"""Ticket generation, PDF, secure QR verification, and OTP routes."""

from __future__ import annotations

import hashlib
import io
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import TicketOut
from app.services import demo_data

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _qr_payload(
    booking_id: str,
    pnr: str,
) -> str:
    """
    Generate a deterministic ticket-verification QR token.

    The QR contains:
    - Booking identifier
    - Verification digest

    It contains no OTP, password, API key, phone number,
    email address, passenger name, or other sensitive data.
    """

    raw_value = f"BUSMATE|{booking_id}|{pnr}"

    digest = hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()[:32]

    return (
        f"BMVERIFY:"
        f"{booking_id}:"
        f"{digest}"
    )


def _verify_qr_payload(
    qr_payload: str,
) -> Dict[str, Any]:
    """Validate a BusMate QR payload against stored bookings."""

    if not qr_payload.startswith("BMVERIFY:"):
        raise HTTPException(
            status_code=400,
            detail="Invalid QR format",
        )

    parts = qr_payload.split(":")

    if len(parts) != 3:
        raise HTTPException(
            status_code=400,
            detail="Invalid QR payload",
        )

    _, booking_id, supplied_digest = parts

    booking = demo_data.get_booking(
        booking_id
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    expected_payload = _qr_payload(
        booking_id=booking_id,
        pnr=booking["pnr"],
    )

    expected_digest = expected_payload.split(
        ":"
    )[-1]

    if supplied_digest != expected_digest:
        raise HTTPException(
            status_code=400,
            detail="QR verification failed",
        )

    return booking


def _format_date_time(
    value: Any,
) -> str:
    """Format a datetime value for the PDF ticket."""

    if not value:
        return "Not available"

    try:
        parsed = datetime.fromisoformat(
            str(value)
        )

        return parsed.strftime(
            "%d %b %Y, %I:%M %p"
        )
    except (TypeError, ValueError):
        return str(value)


def _format_date(
    value: Any,
) -> str:
    """Format only the date portion."""

    if not value:
        return "Not available"

    try:
        parsed = datetime.fromisoformat(
            str(value)
        )

        return parsed.strftime(
            "%d %b %Y"
        )
    except (TypeError, ValueError):
        return str(value)


def _format_time(
    value: Any,
) -> str:
    """Format only the time portion."""

    if not value:
        return "Not available"

    try:
        parsed = datetime.fromisoformat(
            str(value)
        )

        return parsed.strftime(
            "%I:%M %p"
        )
    except (TypeError, ValueError):
        return str(value)


def _ticket_from_booking(
    booking: Dict[str, Any],
    seat: str,
    passenger_index: int,
) -> TicketOut:
    """Create one TicketOut response for one booked seat."""

    passenger_names = booking.get(
        "passenger_names",
        [],
    )

    passenger_ages = booking.get(
        "passenger_ages",
        [],
    )

    passenger_name = (
        passenger_names[passenger_index]
        if passenger_index < len(passenger_names)
        else "Passenger"
    )

    passenger_age = (
        passenger_ages[passenger_index]
        if passenger_index < len(passenger_ages)
        else None
    )

    departure = booking.get(
        "departure_time"
    )

    if not departure:
        departure = datetime.now().isoformat()

    return TicketOut(
        id=(
            f"tkt-{booking['id']}-{seat}"
        ),
        booking_id=booking["id"],
        pnr=booking["pnr"],
        qr_payload=_qr_payload(
            booking_id=booking["id"],
            pnr=booking["pnr"],
        ),
        passenger_name=passenger_name,
        passenger_age=passenger_age,
        seat=seat,
        route_number=booking.get(
            "route_number"
        ),
        bus_number=booking.get(
            "bus_number",
            "Not available",
        ),
        origin=booking.get(
            "origin",
            "Not available",
        ),
        destination=booking.get(
            "destination",
            "Not available",
        ),
        departure=departure,
        arrival=booking.get(
            "arrival_time"
        ),
        total_fare=booking.get(
            "total_fare"
        ),
        status=booking.get(
            "status",
            "confirmed",
        ),
    )


# ---------------------------------------------------------------------------
# Ticket data
# ---------------------------------------------------------------------------


@router.get(
    "/booking/{booking_id}",
    response_model=List[TicketOut],
)
async def tickets_for_booking(
    booking_id: str,
):
    """
    Return ticket information for every passenger and seat.

    Login is not required in the current project demo.
    """

    booking = demo_data.get_booking(
        booking_id
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    seats = booking.get(
        "seats",
        [],
    )

    return [
        _ticket_from_booking(
            booking=booking,
            seat=seat,
            passenger_index=index,
        )
        for index, seat in enumerate(seats)
    ]


# ---------------------------------------------------------------------------
# Professional PDF
# ---------------------------------------------------------------------------


@router.get(
    "/booking/{booking_id}/pdf"
)
async def ticket_pdf(
    booking_id: str,
):
    """
    Generate a professional BusMate Chennai MTC e-ticket PDF.

    Login is not required in the current project demo.
    """

    booking = demo_data.get_booking(
        booking_id
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    try:
        from reportlab.graphics import renderPDF
        from reportlab.graphics.barcode.qr import (
            QrCodeWidget,
        )
        from reportlab.graphics.shapes import Drawing
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import (
            ParagraphStyle,
            getSampleStyleSheet,
        )
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            KeepTogether,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "PDF library is not available. "
                "Install it using: pip install reportlab"
            ),
        ) from exc

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=(
            f"BusMate Ticket {booking['pnr']}"
        ),
        author="BusMate",
        subject="Chennai MTC e-ticket",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "BusMateTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.white,
        spaceAfter=0,
    )

    subtitle_style = ParagraphStyle(
        "BusMateSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        tracking=2,
        textColor=colors.HexColor(
            "#DBEAFE"
        ),
        spaceAfter=4,
    )

    label_style = ParagraphStyle(
        "TicketLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor(
            "#64748B"
        ),
        spaceAfter=3,
    )

    value_style = ParagraphStyle(
        "TicketValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor(
            "#0F172A"
        ),
    )

    small_value_style = ParagraphStyle(
        "TicketSmallValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor(
            "#334155"
        ),
    )

    centered_style = ParagraphStyle(
        "TicketCentered",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor(
            "#475569"
        ),
    )

    centered_bold_style = ParagraphStyle(
        "TicketCenteredBold",
        parent=centered_style,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor(
            "#0F172A"
        ),
    )

    elements = []

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    status = str(
        booking.get(
            "status",
            "confirmed",
        )
    ).upper()

    header_left = [
        Paragraph(
            "CHENNAI MTC E-TICKET",
            subtitle_style,
        ),
        Paragraph(
            "BusMate",
            title_style,
        ),
    ]

    header_status = Paragraph(
        f"<b>{status}</b>",
        ParagraphStyle(
            "Status",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.white,
        ),
    )

    header_table = Table(
        [
            [
                header_left,
                header_status,
            ]
        ],
        colWidths=[
            145 * mm,
            30 * mm,
        ],
    )

    header_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#1D4ED8"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (0, 0),
                    8 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (-1, 0),
                    (-1, 0),
                    6 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    colors.HexColor(
                        "#3B82F6"
                    ),
                ),
                (
                    "BOX",
                    (1, 0),
                    (1, 0),
                    0.5,
                    colors.HexColor(
                        "#93C5FD"
                    ),
                ),
            ]
        )
    )

    elements.append(header_table)
    elements.append(
        Spacer(1, 6 * mm)
    )

    # ------------------------------------------------------------------
    # PNR, route, bus and fare
    # ------------------------------------------------------------------

    route_number = (
        booking.get("route_number")
        or "MTC"
    )

    bus_number = (
        booking.get("bus_number")
        or "Not available"
    )

    fare = float(
        booking.get(
            "total_fare",
            0,
        )
    )

    top_details = Table(
        [
            [
                [
                    Paragraph(
                        "PNR",
                        label_style,
                    ),
                    Paragraph(
                        str(booking["pnr"]),
                        value_style,
                    ),
                ],
                [
                    Paragraph(
                        "ROUTE",
                        label_style,
                    ),
                    Paragraph(
                        str(route_number),
                        value_style,
                    ),
                ],
                [
                    Paragraph(
                        "BUS NUMBER",
                        label_style,
                    ),
                    Paragraph(
                        str(bus_number),
                        value_style,
                    ),
                ],
                [
                    Paragraph(
                        "FARE",
                        label_style,
                    ),
                    Paragraph(
                        f"INR {fare:.2f}",
                        value_style,
                    ),
                ],
            ]
        ],
        colWidths=[
            43.75 * mm,
            43.75 * mm,
            43.75 * mm,
            43.75 * mm,
        ],
    )

    top_details.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
            ]
        )
    )

    elements.append(top_details)
    elements.append(
        Spacer(1, 4 * mm)
    )

    # ------------------------------------------------------------------
    # Journey section
    # ------------------------------------------------------------------

    origin = (
        booking.get("origin")
        or "Not available"
    )

    destination = (
        booking.get("destination")
        or "Not available"
    )

    journey_table = Table(
        [
            [
                [
                    Paragraph(
                        "BOARDING",
                        label_style,
                    ),
                    Paragraph(
                        str(origin),
                        value_style,
                    ),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        _format_time(
                            booking.get(
                                "departure_time"
                            )
                        ),
                        small_value_style,
                    ),
                ],
                Paragraph(
                    "<b>&#8594;</b>",
                    ParagraphStyle(
                        "Arrow",
                        parent=value_style,
                        alignment=TA_CENTER,
                        fontSize=16,
                        textColor=colors.HexColor(
                            "#94A3B8"
                        ),
                    ),
                ),
                [
                    Paragraph(
                        "DESTINATION",
                        label_style,
                    ),
                    Paragraph(
                        str(destination),
                        value_style,
                    ),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        _format_time(
                            booking.get(
                                "arrival_time"
                            )
                        ),
                        small_value_style,
                    ),
                ],
            ]
        ],
        colWidths=[
            78 * mm,
            19 * mm,
            78 * mm,
        ],
    )

    journey_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#F8FAFC"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#E2E8F0"
                    ),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
            ]
        )
    )

    elements.append(journey_table)
    elements.append(
        Spacer(1, 5 * mm)
    )

    # ------------------------------------------------------------------
    # Passenger and booking details
    # ------------------------------------------------------------------

    passenger_names = booking.get(
        "passenger_names",
        [],
    )

    passenger_ages = booking.get(
        "passenger_ages",
        [],
    )

    seats = booking.get(
        "seats",
        [],
    )

    passenger_rows = []

    maximum_passengers = max(
        len(seats),
        len(passenger_names),
        1,
    )

    for index in range(
        maximum_passengers
    ):
        passenger_name = (
            passenger_names[index]
            if index < len(passenger_names)
            else "Passenger"
        )

        passenger_age = (
            passenger_ages[index]
            if index < len(passenger_ages)
            else "Not available"
        )

        seat = (
            seats[index]
            if index < len(seats)
            else "Not available"
        )

        passenger_rows.append(
            [
                Paragraph(
                    str(index + 1),
                    small_value_style,
                ),
                Paragraph(
                    str(passenger_name),
                    small_value_style,
                ),
                Paragraph(
                    str(passenger_age),
                    small_value_style,
                ),
                Paragraph(
                    str(seat),
                    small_value_style,
                ),
            ]
        )

    passenger_table_data = [
        [
            Paragraph(
                "<b>#</b>",
                small_value_style,
            ),
            Paragraph(
                "<b>Passenger</b>",
                small_value_style,
            ),
            Paragraph(
                "<b>Age</b>",
                small_value_style,
            ),
            Paragraph(
                "<b>Seat</b>",
                small_value_style,
            ),
        ],
        *passenger_rows,
    ]

    passenger_table = Table(
        passenger_table_data,
        colWidths=[
            12 * mm,
            85 * mm,
            30 * mm,
            30 * mm,
        ],
    )

    passenger_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#EFF6FF"
                    ),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#CBD5E1"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
            ]
        )
    )

    booking_info_table = Table(
        [
            [
                [
                    Paragraph(
                        "TRAVEL DATE",
                        label_style,
                    ),
                    Paragraph(
                        _format_date(
                            booking.get(
                                "departure_time"
                            )
                        ),
                        value_style,
                    ),
                ],
                [
                    Paragraph(
                        "BOOKED ON",
                        label_style,
                    ),
                    Paragraph(
                        _format_date_time(
                            booking.get(
                                "created_at"
                            )
                        ),
                        value_style,
                    ),
                ],
            ],
            [
                [
                    Paragraph(
                        "PHONE",
                        label_style,
                    ),
                    Paragraph(
                        str(
                            booking.get(
                                "contact_phone"
                            )
                            or "Not available"
                        ),
                        small_value_style,
                    ),
                ],
                [
                    Paragraph(
                        "EMAIL",
                        label_style,
                    ),
                    Paragraph(
                        str(
                            booking.get(
                                "contact_email"
                            )
                            or "Not available"
                        ),
                        small_value_style,
                    ),
                ],
            ],
        ],
        colWidths=[
            87.5 * mm,
            87.5 * mm,
        ],
    )

    booking_info_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#E2E8F0"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
            ]
        )
    )

    elements.append(
        Paragraph(
            "Passenger details",
            ParagraphStyle(
                "SectionTitle",
                parent=value_style,
                fontSize=12,
                leading=15,
                spaceAfter=6,
            ),
        )
    )

    elements.append(passenger_table)
    elements.append(
        Spacer(1, 5 * mm)
    )

    elements.append(booking_info_table)
    elements.append(
        Spacer(1, 6 * mm)
    )

    # ------------------------------------------------------------------
    # QR verification block
    # ------------------------------------------------------------------

    qr_payload = _qr_payload(
        booking_id=booking_id,
        pnr=booking["pnr"],
    )

    qr_widget = QrCodeWidget(
        qr_payload
    )

    qr_bounds = qr_widget.getBounds()

    qr_width = (
        qr_bounds[2] - qr_bounds[0]
    )

    qr_height = (
        qr_bounds[3] - qr_bounds[1]
    )

    qr_size = 38 * mm

    qr_drawing = Drawing(
        qr_size,
        qr_size,
        transform=[
            qr_size / qr_width,
            0,
            0,
            qr_size / qr_height,
            0,
            0,
        ],
    )

    qr_drawing.add(qr_widget)

    qr_table = Table(
        [
            [
                qr_drawing,
                [
                    Paragraph(
                        "SCAN TO VERIFY",
                        centered_bold_style,
                    ),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        str(booking["pnr"]),
                        centered_bold_style,
                    ),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        (
                            "Secure ticket-verification QR. "
                            "Contains no OTP, secrets, or "
                            "sensitive passenger data."
                        ),
                        centered_style,
                    ),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        (
                            "Show this ticket during "
                            "boarding."
                        ),
                        centered_style,
                    ),
                ],
            ]
        ],
        colWidths=[
            48 * mm,
            127 * mm,
        ],
    )

    qr_table.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor(
                        "#BFDBFE"
                    ),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#F8FAFC"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (0, 0),
                    "CENTER",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
            ]
        )
    )

    elements.append(
        KeepTogether(
            [
                qr_table,
            ]
        )
    )

    elements.append(
        Spacer(1, 5 * mm)
    )

    # ------------------------------------------------------------------
    # Payment and terms
    # ------------------------------------------------------------------

    payment_method = str(
        booking.get(
            "payment_method",
            "upi",
        )
    ).upper()

    payment_reference = (
        booking.get(
            "payment_ref"
        )
        or "Not available"
    )

    payment_table = Table(
        [
            [
                Paragraph(
                    (
                        f"<b>Payment:</b> "
                        f"{payment_method}"
                    ),
                    small_value_style,
                ),
                Paragraph(
                    (
                        f"<b>Reference:</b> "
                        f"{payment_reference}"
                    ),
                    small_value_style,
                ),
            ]
        ],
        colWidths=[
            87.5 * mm,
            87.5 * mm,
        ],
    )

    payment_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#F8FAFC"
                    ),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#E2E8F0"
                    ),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
            ]
        )
    )

    elements.append(payment_table)
    elements.append(
        Spacer(1, 4 * mm)
    )

    terms = [
        "This is a simulated BusMate project ticket.",
        (
            "Carry a valid identity document if requested "
            "during boarding."
        ),
        (
            "The verification QR does not contain an OTP, "
            "password, secret, phone number, email address, "
            "or passenger name."
        ),
        (
            "Journey timing and vehicle location are "
            "simulated for demonstration purposes."
        ),
    ]

    terms_html = "<br/>".join(
        f"- {term}"
        for term in terms
    )

    elements.append(
        Paragraph(
            terms_html,
            ParagraphStyle(
                "Terms",
                parent=small_value_style,
                fontSize=7,
                leading=10,
                textColor=colors.HexColor(
                    "#64748B"
                ),
            ),
        )
    )

    # ------------------------------------------------------------------
    # Build PDF
    # ------------------------------------------------------------------

    try:
        document.build(
            elements
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate the ticket PDF"
            ),
        ) from exc

    buffer.seek(0)

    filename = (
        f"BusMate-{booking['pnr']}.pdf"
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
            "Cache-Control": "no-store",
        },
    )


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------


@router.post(
    "/send-otp"
)
async def send_otp(
    booking_id: str,
):
    """
    Generate and simulate sending a verification OTP.

    The OTP is never included in the ticket QR code.
    """

    booking = demo_data.get_booking(
        booking_id
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    otp = "123456"

    demo_data.DEMO_OTP[
        booking_id
    ] = otp

    return {
        "sent": True,
        "message": (
            "OTP sent to the registered phone."
        ),
        "demo_otp": otp,
    }


@router.post(
    "/verify-otp"
)
async def verify_otp(
    booking_id: str,
    otp: str,
):
    """
    Verify the simulated ticket OTP.

    The OTP is separate from the QR verification token.
    """

    booking = demo_data.get_booking(
        booking_id
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    expected_otp = demo_data.DEMO_OTP.get(
        booking_id
    )

    if not expected_otp:
        raise HTTPException(
            status_code=400,
            detail=(
                "Generate an OTP before verification"
            ),
        )

    if otp != expected_otp:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP",
        )

    return {
        "verified": True,
        "booking_id": booking_id,
        "pnr": booking["pnr"],
        "message": "OTP verified successfully",
    }


# ---------------------------------------------------------------------------
# QR verification
# ---------------------------------------------------------------------------


@router.post(
    "/verify-qr"
)
async def verify_qr(
    qr_payload: str,
):
    """
    Verify a BusMate ticket-verification QR token.

    The QR token contains no OTP or sensitive passenger data.
    """

    booking = _verify_qr_payload(
        qr_payload
    )

    return {
        "valid": True,
        "booking_id": booking["id"],
        "pnr": booking["pnr"],
        "status": booking.get(
            "status",
            "confirmed",
        ),
        "route_number": booking.get(
            "route_number",
        ),
        "bus_number": booking.get(
            "bus_number",
        ),
        "seats": booking.get(
            "seats",
            [],
        ),
        "message": (
            "Ticket QR verified successfully"
        ),
    }