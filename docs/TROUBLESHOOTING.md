# Troubleshooting

| Symptom | Fix |
|---------|-----|
| CORS errors | Ensure `FRONTEND_URL` matches the browser origin; restart backend. |
| 401 on API | Demo mode should not require JWT. Confirm `DEMO_MODE=true`. |
| Admin 403 | Use admin@demo.busmate or temporarily set demo user role to admin in `demo_data.DEMO_USERS`. |
| Map blank | Leaflet CSS loaded; allow unpkg marker icons or self-host icons. |
| AI always “unavailable” | Expected without `OPENROUTER_API_KEY`. Core features still work. |
| PDF 503 | Install `reportlab` from requirements.txt. |
| pytest import errors | `export PYTHONPATH=backend` from repo root. |
| Heavy pip install | sentence-transformers pulls torch – use a machine with enough disk or comment ML deps for pure API demo. |
