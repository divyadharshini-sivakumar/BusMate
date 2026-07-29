# Testing

## Backend unit tests

```bash
cd BusMate
export PYTHONPATH=backend DEMO_MODE=true
pytest tests/ -q --tb=short
```

Coverage includes:

- Intent classification (scope lock)
- Demo search + booking seat lock
- Orchestrator out-of-scope / greeting / booking tool path

## Manual smoke

1. Start backend + frontend.
2. Search Chennai → Madurai.
3. Select seats → pay (simulated).
4. My Tickets → PDF / OTP 123456 / Track map.
5. Assistant: “cancellation policy”, “tell me a joke” (must refuse).

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs backend pytest and frontend install/build.
