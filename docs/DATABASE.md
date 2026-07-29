# Database

Migration: `supabase/migrations/001_initial_schema.sql`

## Tables

| Table | Purpose |
|-------|---------|
| profiles | User profile + role (passenger/admin) |
| trips | Bus services / seat_map JSON |
| bookings | Reservations + PNR |
| tickets | Per-seat ticket + qr_token |
| complaints | Issues + sentiment |
| feedback | Ratings |
| knowledge_chunks | RAG embeddings (vector 384) |

## RLS summary

- Passengers: own profile, own bookings/tickets/complaints/feedback.
- Authenticated: read active trips; read knowledge chunks.
- Admin: full manage via role check on profiles.
- Service role: backend operations.

## RPC

`match_knowledge(query_embedding vector(384), match_count int)` – cosine similarity for RAG.

## Demo without Supabase

`DEMO_MODE=true` (default when keys missing) uses `app/services/demo_data.py` in-memory store with Chennai routes.
