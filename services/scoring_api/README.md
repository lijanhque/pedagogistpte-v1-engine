# PTE Scoring API (Level 1 scaffold)

This directory contains a scaffold FastAPI service that exposes a basic `/score` endpoint and a minimal CRUD for `assessments`.

Key points:
- Uses FastAPI + Uvicorn
- Placeholder scoring logic (synthetic demo). Replace this with calls to Vercel AI Gateway v5, Google GenAI, or local NLP models.
- Local dev via `docker compose up` (service is on port 8000)

Environment variables (see `.env.example`):
- `VERCEL_AI_GATEWAY_KEY` — Vercel AI Gateway key for the frontend / server to call the gateway.
- `GOOGLE_GENAI_KEY` — (optional) Google GenAI key.
- `REDIS_URL` — Redis connection string for future background jobs.

Quick start:

```bash
cp services/scoring_api/.env.example .env
docker compose up --build
# then visit http://localhost:8000/docs
```

Next steps to integrate Vercel AI Gateway v5:
- Add an adapter module that calls the Vercel AI Gateway REST API or SDK v5 from `services/scoring_api/app/`.
- Add model selection, prompt templates and a small cache (Redis) to store model outputs for auditing.
