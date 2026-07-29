# BusMate Setup Guide

## Prerequisites

- Node.js 18+ / npm
- Python 3.11+
- (Optional) Supabase project
- (Optional) OpenRouter API key for AI features

## 1. Environment

```bash
cp .env.example .env
```

Set at minimum:

```
DEMO_MODE=true
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

Supabase and OpenRouter keys are **optional**. Without them:

- Auth, booking, tickets, tracking, complaints, feedback work via in-memory demo data.
- AI assistant uses rule-based replies + keyword RAG; shows friendly message when LLM is needed but unavailable.

## 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/health  
Docs: http://localhost:8000/docs

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## 4. Supabase (optional)

1. Create a project on supabase.com (free tier).
2. Run SQL from `supabase/migrations/001_initial_schema.sql` in the SQL editor.
3. Copy URL + anon key + service role key into `.env`.
4. `python scripts/seed_chennai.py`

RLS is enabled on all tables. Backend uses the **service role** key only server-side.

## 5. Demo accounts

| Email | Role |
|-------|------|
| passenger@demo.busmate | passenger |
| admin@demo.busmate | admin |

In pure demo mode, sign-in accepts any email and creates a passenger profile.

OTP for tickets: **123456**

## 6. Tests

```bash
export PYTHONPATH=backend DEMO_MODE=true
pytest tests/ -q
```

## 7. Production builds

```bash
# Frontend
cd frontend && npm run build && npm start

# Backend
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Deploy frontend → Vercel, backend → Railway (see DEPLOYMENT.md).
