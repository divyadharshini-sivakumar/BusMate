# Architecture

## Overview

```
Next.js UI  -->  FastAPI API  -->  Supabase (optional)
Tailwind         Agents/RAG       Postgres + pgvector
Leaflet          Demo store       Auth / Storage
                      |
                 OpenRouter / LangSmith (optional)
```

## Roles

- **Passenger** – search, book, tickets, track, complain, feedback, assistant.
- **Admin** – stats, trips, bookings, complaints (backend `require_admin`).

## Intent gate (critical)

Every assistant message is classified with **deterministic rules** (`app/agents/intent.py`) **before** any LLM, agent, or RAG call.

Supported intents only:

Booking | Ticket | Journey | Tracking | Policy | Complaint | Feedback | Greeting | Out-of-Scope

Out-of-scope requests receive a fixed refusal. BusMate is **not** a general chatbot.

## Agents

| Agent | Responsibility |
|-------|----------------|
| ScopeGuard | Out-of-scope refusal |
| GreetingAgent | Welcome |
| BookingAgent | Search tool + optional LLM |
| TicketAgent | PNR / My Tickets pointer |
| JourneyAgent | Tracking / timeline guidance |
| KnowledgeAgent | RAG over knowledge_base/ |
| ComplaintAgent | Empathy + escalation |
| FeedbackAgent | Rating prompt |

Patterns demonstrated:

- Zero-shot tool use (bus search)
- Few-shot prompt examples (booking)
- ReAct-style tools
- Reflection (repeat complaints escalate)
- Prompt templates
- Isolated session memory
- Conditional routing (intent to handler)
- Crew-style collaboration plan stub
- Keyword RAG fallback when embeddings unavailable

## Security

- Secrets only via environment variables; .env gitignored.
- QR payload = BMVERIFY: + hash fragment – no OTP, PII, or secrets.
- OTP is in-app only (demo: 123456).
- Supabase RLS on profiles, bookings, tickets, complaints, feedback, knowledge.
- Backend admin routes require role=admin.
- CORS limited to frontend origin.

## Graceful degradation

| Component missing | Behavior |
|-------------------|----------|
| OpenRouter key | Rule-based agent replies; policy keyword RAG |
| Supabase | In-memory Chennai demo data |
| LangSmith | Tracing off |

Authentication, booking, tickets, tracking, complaints, feedback, and admin continue to work.
