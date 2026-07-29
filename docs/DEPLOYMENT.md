# Deployment

## Frontend → Vercel

1. Import the `frontend/` directory (or monorepo with root as frontend).
2. Env: `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
3. Build command: `npm run build`.

## Backend → Railway

1. Root directory: `backend/`.
2. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Env: copy from `.env.example` (Supabase service role, OpenRouter, `FRONTEND_URL`, `API_SECRET_KEY`).

## Supabase

- Free tier is sufficient for demo.
- Apply migration SQL once.
- Enable Email auth provider.

## Checklist

- [ ] No secrets in git
- [ ] CORS = production frontend URL
- [ ] DEMO_MODE=false when using real Auth
- [ ] RLS verified in Supabase dashboard
- [ ] Health endpoint monitored
