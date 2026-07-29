# API Reference

Base URL: `http://localhost:8000`

## Health

- `GET /health` – liveness + feature flags
- `GET /health/ready` – readiness

## Auth

- `POST /api/auth/signup` – body: email, password, full_name, phone?, role?
- `POST /api/auth/signin` – body: email, password
- `GET /api/auth/me` – current user

## Bookings

- `POST /api/bookings/search` – origin, destination, travel_date, passengers
- `GET /api/bookings/trips/{trip_id}/seats`
- `POST /api/bookings` – create booking
- `POST /api/bookings/pay` – simulate payment
- `GET /api/bookings/mine`

## Tickets

- `GET /api/tickets/booking/{booking_id}`
- `GET /api/tickets/booking/{booking_id}/pdf`
- `POST /api/tickets/send-otp?booking_id=`
- `POST /api/tickets/verify-otp?booking_id=&otp=`
- `POST /api/tickets/verify-qr` – body qr_payload

## Tracking

- `GET /api/tracking/{booking_id}`
- `GET /api/tracking/{booking_id}/alerts`

## Complaints / Feedback

- `POST /api/complaints`
- `GET /api/complaints/mine`
- `POST /api/feedback`
- `GET /api/feedback/mine`

## Agents

- `POST /api/agents/chat` – message, session_id?, user_id?, context?

## Admin (role=admin)

- `GET /api/admin/stats`
- `GET /api/admin/trips`
- `GET /api/admin/bookings`
- `GET /api/admin/complaints`
- `GET /api/admin/feedback`

Interactive docs: `/docs` (Swagger) and `/redoc`.
