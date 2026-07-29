# BusMate

AI-powered bus booking and journey companion platform focused exclusively on bus travel in India (demo: Chennai region).

**Roles:** Passenger · Admin  
**Stack:** Next.js · FastAPI · Supabase · OpenRouter · LangChain/LangGraph/CrewAI · pgvector RAG

> **Scope lock:** BusMate only handles Booking, Ticket, Journey, Tracking, Policy, Complaint, Feedback, Greeting, and Out-of-Scope intents. It never acts as a general-purpose chatbot.

## Quick Start

```bash
# 1. Clone / enter
cd BusMate

# 2. Environment
cp .env.example .env
# Fill SUPABASE_*, OPENROUTER_API_KEY (optional), etc.

# 3. Supabase (local or cloud)
# Apply migrations in supabase/migrations/
# Run seed: python scripts/seed_chennai.py

# 4. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 5. Frontend
cd frontend
npm install
npm run dev
```

See [docs/SETUP.md](docs/SETUP.md) for full instructions.

## Architecture

```
frontend/          Next.js 14 (App Router) + Tailwind + Framer Motion + Leaflet
backend/           FastAPI + agents (LangGraph / CrewAI) + RAG
supabase/          PostgreSQL + Auth + Storage + pgvector + RLS
knowledge_base/    Policy docs for RAG
scripts/           Seed, migrate helpers
tests/             Backend + frontend tests
docs/              Full documentation
.github/workflows/ CI (lint, test, build)
```

## Features

- Auth (Supabase) – Passenger / Admin
- Bus search & interactive seat map
- Simulated UPI / Card / Wallet payments
- PDF tickets + secure QR (no OTP/secrets)
- In-app OTP verification
- My Tickets, simulated live tracking, ETA, journey timeline, destination alerts
- Complaints & feedback + sentiment analysis
- Admin dashboard (routes, buses, bookings, analytics)
- Multi-agent system with deterministic intent classification before any LLM call
- Graceful AI fallback when OpenRouter/LangSmith unavailable

## License

Demo / educational. Not for production without hardening.
